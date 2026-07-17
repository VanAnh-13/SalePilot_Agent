import json

from fastapi import APIRouter
from sqlalchemy import select

from app.db.session import async_session
from app.models.entities import AgentRun

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
@router.get("/")
async def list_runs(limit: int = 20):
    async with async_session() as session:
        rows = (
            await session.execute(select(AgentRun).order_by(AgentRun.id.desc()).limit(limit))
        ).scalars().all()
    return [
        {
            "id": r.id,
            "run_id": r.run_id,
            "channel": r.channel,
            "external_id": r.external_id,
            "user_text": r.user_text[:200],
            "reply": r.reply[:300],
            "agents": json.loads(r.agents_json or "[]"),
            "tools": json.loads(r.tools_json or "[]"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/latest")
async def latest_run():
    async with async_session() as session:
        r = (
            await session.execute(select(AgentRun).order_by(AgentRun.id.desc()).limit(1))
        ).scalar_one_or_none()
    if not r:
        return {"run": None}
    return {
        "run": {
            "run_id": r.run_id,
            "channel": r.channel,
            "external_id": r.external_id,
            "user_text": r.user_text,
            "reply": r.reply,
            "trace": json.loads(r.trace_json or "[]"),
            "agents": json.loads(r.agents_json or "[]"),
            "tools": json.loads(r.tools_json or "[]"),
            "memory": json.loads(r.memory_json or "{}"),
            "skills": json.loads(r.skills_json or "[]"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
    }
