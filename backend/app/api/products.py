from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.agent.catalog_domain import search
from app.catalog import repository
from app.catalog.registry import get_category

router = APIRouter(prefix="/products", tags=["products"])


class ProductOut(BaseModel):
    sku: str
    name: str
    category: str
    category_display: str | None = None
    brand: str | None = None
    style: str | None = None
    type: str | None = None
    price_vnd: int | None
    price_display: str
    stock: int | None = None
    usable_capacity_l: float | None = None
    household_label: str | None = None
    description: str
    source: str | None = None

    model_config = {"from_attributes": True, "extra": "ignore"}


class CategoryOut(BaseModel):
    slug: str
    display: str
    code: int
    total: int
    priced: int


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories():
    counts = repository.category_counts()
    return sorted(counts.values(), key=lambda c: -c["total"])


@router.get("", response_model=list[ProductOut])
@router.get("/", response_model=list[ProductOut])
async def list_products(
    category: str = Query(default="", max_length=40),
    query: str = Query(default="", max_length=200),
    priced_only: bool = False,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    if category and get_category(category) is None:
        raise HTTPException(status_code=422, detail=f"Ngành hàng không hợp lệ: {category}")
    products = search(query, category=category or None, priced_only=priced_only, limit=None)
    return products[offset : offset + limit]
