from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.api.auth import require_admin_token
from app.db.session import async_session
from app.models.entities import Conversation, Lead

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadOut(BaseModel):
    id: int
    name: str
    phone: str
    channel: str
    interest: str
    budget_vnd: int | None
    status: str
    score: float
    notes: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[LeadOut])
@router.get("/", response_model=list[LeadOut])
async def list_leads(
    limit: int = 50,
    _auth: None = Depends(require_admin_token),
):
    async with async_session() as session:
        rows = (
            await session.execute(select(Lead).order_by(Lead.id.desc()).limit(limit))
        ).scalars().all()
    return rows


@router.get("/conversations")
async def list_conversations(
    limit: int = 30,
    _auth: None = Depends(require_admin_token),
):
    async with async_session() as session:
        rows = (
            await session.execute(
                select(Conversation).order_by(Conversation.id.desc()).limit(limit)
            )
        ).scalars().all()
    return [
        {
            "id": c.id,
            "channel": c.channel,
            "external_id": c.external_id,
            "customer_name": c.customer_name,
            "lead_id": c.lead_id,
            "status": c.status,
            "needs_human": c.needs_human,
            "summary": c.summary,
        }
        for c in rows
    ]
