import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.auth import require_admin_token
from app.db.session import async_session
from app.models.entities import AgentRun
from app.observability.metrics import snapshot as metrics_snapshot

router = APIRouter(prefix="/runs", tags=["runs"])
TRAJ_DIR = Path(__file__).resolve().parents[2] / "data" / "trajectories"


@router.get("/metrics")
async def runtime_metrics(
    _auth: None = Depends(require_admin_token),
):
    """Per-route request counts and p50/p95 latency since process start."""
    return metrics_snapshot()


def _trajectory_decision(run_id: str | None) -> dict | None:
    if not run_id or not run_id.isalnum():
        return None
    path = TRAJ_DIR / f"{run_id}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload.get("decision")


@router.get("")
@router.get("/")
async def list_runs(
    limit: int = 20,
    _auth: None = Depends(require_admin_token),
):
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
            "decision": _trajectory_decision(r.run_id),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/latest")
async def latest_run(
    _auth: None = Depends(require_admin_token),
):
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
            "decision": _trajectory_decision(r.run_id),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
    }
