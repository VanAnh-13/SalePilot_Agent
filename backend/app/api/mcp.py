"""Local API contract consumed by the SalePilot stdio MCP server."""

from __future__ import annotations

import hmac
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from app.agent.catalog_domain import (
    compare,
    get_by_sku,
    recommendation_need,
    recommend_top3,
    search,
)
from app.config import get_settings
from app.rag.store import search_faq
from app.services.leads import create_lead_record

router = APIRouter(prefix="/mcp", tags=["mcp"])


class PageOut(BaseModel):
    items: list[dict[str, Any]]
    total_count: int
    count: int
    offset: int
    has_more: bool
    next_offset: int | None = None


class ProductComparisonRequest(BaseModel):
    skus: list[str] = Field(min_length=2, max_length=5)

    @field_validator("skus")
    @classmethod
    def normalize_skus(cls, skus: list[str]) -> list[str]:
        normalized = [sku.strip().upper() for sku in skus if sku.strip()]
        if len(normalized) < 2:
            raise ValueError("Cần ít nhất 2 SKU hợp lệ")
        if len(set(normalized)) != len(normalized):
            raise ValueError("SKU không được trùng nhau")
        return normalized


class RecommendationRequest(BaseModel):
    household_size: int | None = Field(default=None, ge=1, le=20)
    capacity_l: int | None = Field(default=None, ge=1, le=2_000)
    budget_vnd: int | None = Field(default=None, ge=0, le=1_000_000_000)
    priorities: list[str] = Field(default_factory=list, max_length=7)
    preferred_styles: list[str] = Field(default_factory=list, max_length=5)
    max_width_cm: float | None = Field(default=None, gt=0, le=500)
    max_height_cm: float | None = Field(default=None, gt=0, le=500)
    max_depth_cm: float | None = Field(default=None, gt=0, le=500)
    force: bool = False
    free_text: str = Field(default="", max_length=500)

    @field_validator("priorities")
    @classmethod
    def validate_priorities(cls, priorities: list[str]) -> list[str]:
        clean = [priority.strip() for priority in priorities if priority.strip()]
        if any(len(priority) > 40 for priority in clean):
            raise ValueError("Mỗi ưu tiên tối đa 40 ký tự")
        return clean


class CreateLeadRequest(BaseModel):
    # The client must collect human confirmation before this write operation.
    confirmed: Literal[True]
    name: str = Field(default="Khách", min_length=1, max_length=128)
    phone: str = Field(min_length=8, max_length=32, pattern=r"^[0-9+(). -]+$")
    interest: str = Field(min_length=1, max_length=1_000)
    budget_vnd: int | None = Field(default=None, ge=0, le=1_000_000_000)
    notes: str = Field(default="", max_length=2_000)
    score: float = Field(default=0.5, ge=0, le=1)


class LeadCreatedOut(BaseModel):
    lead_id: int
    status: str
    score: float
    message: str


def _page(items: list[dict[str, Any]], offset: int, limit: int) -> PageOut:
    selected = items[offset : offset + limit]
    next_offset = offset + len(selected)
    return PageOut(
        items=selected,
        total_count=len(items),
        count=len(selected),
        offset=offset,
        has_more=next_offset < len(items),
        next_offset=next_offset if next_offset < len(items) else None,
    )


def require_mcp_write_token(
    x_salepilot_mcp_token: str | None = Header(default=None),
) -> None:
    configured_token = get_settings().mcp_write_token
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP lead creation is disabled. Set MCP_WRITE_TOKEN on the backend.",
        )
    if not x_salepilot_mcp_token or not hmac.compare_digest(
        x_salepilot_mcp_token.encode("utf-8"), configured_token.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MCP write token is missing or invalid.",
        )


@router.get("/products", response_model=PageOut)
async def list_mcp_products(
    query: str = Query(default="", max_length=200),
    budget_vnd: int | None = Query(default=None, ge=0, le=1_000_000_000),
    household_size: int | None = Query(default=None, ge=1, le=20),
    min_capacity_l: int | None = Query(default=None, ge=1, le=2_000),
    max_width_cm: float | None = Query(default=None, gt=0, le=500),
    max_height_cm: float | None = Query(default=None, gt=0, le=500),
    max_depth_cm: float | None = Query(default=None, gt=0, le=500),
    energy_saving: bool | None = None,
    brand: str = Query(default="", max_length=80),
    style: str = Query(default="", max_length=100),
    priced_only: bool = False,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> PageOut:
    results = search(
        query,
        budget_vnd=budget_vnd,
        household_size=household_size,
        min_capacity_l=min_capacity_l,
        max_width_cm=max_width_cm,
        max_height_cm=max_height_cm,
        max_depth_cm=max_depth_cm,
        energy_saving=energy_saving,
        brand=brand,
        style=style,
        priced_only=priced_only,
        limit=None,
    )
    return _page(results, offset, limit)


@router.get("/products/{sku}")
async def get_mcp_product(sku: str) -> dict[str, Any]:
    product = get_by_sku(sku)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không có SKU {sku}")
    return product


@router.post("/product-comparisons")
async def create_mcp_product_comparison(request: ProductComparisonRequest) -> dict[str, Any]:
    result = compare(request.skus)
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.get("error", "Không thể so sánh các SKU đã chọn"),
        )
    return result


@router.post("/recommendations")
async def create_mcp_recommendation(request: RecommendationRequest) -> dict[str, Any]:
    need = recommendation_need(
        household_size=request.household_size,
        capacity_l=request.capacity_l,
        budget_vnd=request.budget_vnd,
        priorities=request.priorities,
        preferred_styles=request.preferred_styles,
        max_width_cm=request.max_width_cm,
        max_height_cm=request.max_height_cm,
        max_depth_cm=request.max_depth_cm,
        force=request.force,
        free_text=request.free_text,
    )
    return recommend_top3(need)


@router.get("/knowledge/faq", response_model=PageOut)
async def list_mcp_faq(
    query: str = Query(default="", max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> PageOut:
    results = await search_faq(query, k=50)
    return _page(results, offset, limit)


@router.post(
    "/leads",
    response_model=LeadCreatedOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_mcp_write_token)],
)
async def create_mcp_lead(request: CreateLeadRequest) -> LeadCreatedOut:
    lead = await create_lead_record(
        name=request.name,
        phone=request.phone,
        channel="mcp",
        external_id=f"mcp-{uuid.uuid4().hex[:16]}",
        interest=request.interest,
        budget_vnd=request.budget_vnd,
        notes=request.notes,
        score=request.score,
    )
    return LeadCreatedOut(
        lead_id=lead.id,
        status=lead.status,
        score=lead.score,
        message=f"Đã tạo lead #{lead.id}",
    )
