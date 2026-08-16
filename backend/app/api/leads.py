from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.auth import require_admin_token
from app.db.session import async_session
from app.models.entities import Conversation, Lead
from app.services.escalation import resolve_takeover

router = APIRouter(prefix="/leads", tags=["leads"])


async def _latest_conversation(channel: str, external_id: str) -> Conversation | None:
    async with async_session() as session:
        return (
            await session.execute(
                select(Conversation)
                .where(Conversation.channel == channel, Conversation.external_id == external_id)
                .order_by(Conversation.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()


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


class TakeoverRequest(BaseModel):
    channel: str
    external_id: str


@router.post("/conversations/takeover")
async def takeover_conversation(
    req: TakeoverRequest,
    _auth: None = Depends(require_admin_token),
):
    """Owner claims the conversation: bot stays silent until resolved."""
    conv = await _latest_conversation(req.channel, req.external_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    async with async_session() as session:
        managed = await session.get(Conversation, conv.id)
        managed.status = "escalated"
        managed.needs_human = True
        await session.commit()
    return {"ok": True, "conversation_id": conv.id, "status": "escalated"}


@router.post("/conversations/resolve")
async def resolve_conversation(
    req: TakeoverRequest,
    _auth: None = Depends(require_admin_token),
):
    """Owner hands the conversation back to the bot."""
    conv = await resolve_takeover(req.channel, req.external_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True, "conversation_id": conv.id, "status": conv.status}
