from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.db.session import async_session
from app.models.entities import Product

router = APIRouter(prefix="/products", tags=["products"])


class ProductOut(BaseModel):
    sku: str
    name: str
    category: str
    price_vnd: int
    stock: int
    description: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ProductOut])
@router.get("/", response_model=list[ProductOut])
async def list_products(limit: int = 100):
    async with async_session() as session:
        rows = (
            await session.execute(select(Product).order_by(Product.sku).limit(limit))
        ).scalars().all()
    return rows
