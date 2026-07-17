from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.agent.catalog_domain import search

router = APIRouter(prefix="/products", tags=["products"])


class ProductOut(BaseModel):
    sku: str
    name: str
    category: str
    brand: str | None = None
    style: str | None = None
    price_vnd: int | None
    price_display: str
    stock: int | None = None
    usable_capacity_l: int | None = None
    household_size_label: str | None = None
    description: str
    source: str | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ProductOut])
@router.get("/", response_model=list[ProductOut])
async def list_products(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    products = search(limit=None)
    return products[offset : offset + limit]
