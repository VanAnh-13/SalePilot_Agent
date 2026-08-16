from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.auth import require_admin_token
from app.db.session import async_session
from app.models.entities import OutboxMessage

router = APIRouter(prefix="/outbox", tags=["outbox"])


@router.get("/zalo")
async def list_zalo_outbox(
    limit: int = 50,
    _auth: None = Depends(require_admin_token),
):
    async with async_session() as session:
        rows = (
            await session.execute(
                select(OutboxMessage)
                .where(OutboxMessage.channel == "zalo")
                .order_by(OutboxMessage.id.desc())
                .limit(limit)
            )
        ).scalars().all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "direction": r.direction,
            "content": r.content,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
