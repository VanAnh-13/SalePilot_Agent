from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db.session import async_session
from app.models.entities import AgentRun

TRAJ_DIR = Path(__file__).resolve().parents[3] / "data" / "trajectories"


async def save_trajectory(
    *,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    user_text: str,
    reply: str,
    trace: list,
    agents: list,
    tools: list,
    memory: dict | None = None,
    skills: list | None = None,
) -> str | None:
    if not get_settings().trajectory_enabled:
        return None

    run_id = uuid.uuid4().hex[:16]
    payload: dict[str, Any] = {
        "run_id": run_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "channel": channel,
        "external_id": external_id,
        "conversation_id": conversation_id,
        "user_text": user_text,
        "reply": reply,
        "trace": trace,
        "agents": agents,
        "tools": tools,
        "memory": memory or {},
        "skills": skills or [],
    }

    TRAJ_DIR.mkdir(parents=True, exist_ok=True)
    path = TRAJ_DIR / f"{run_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    async with async_session() as session:
        session.add(
            AgentRun(
                run_id=run_id,
                channel=channel,
                external_id=external_id,
                conversation_id=conversation_id,
                user_text=user_text[:2000],
                reply=reply[:4000],
                trace_json=json.dumps(trace, ensure_ascii=False),
                agents_json=json.dumps(agents, ensure_ascii=False),
                tools_json=json.dumps(tools, ensure_ascii=False),
                memory_json=json.dumps(memory or {}, ensure_ascii=False),
                skills_json=json.dumps(skills or [], ensure_ascii=False),
            )
        )
        await session.commit()
    return run_id
