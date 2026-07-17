"""Background poller for scheduled follow-up jobs."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.db.session import async_session
from app.models.entities import Lead, OutboxMessage, ScheduledJob

logger = logging.getLogger("salepilot.scheduler")


async def create_followup_job(
    *,
    channel: str,
    external_id: str,
    lead_id: int | None,
    hours_from_now: int,
    note: str,
) -> int:
    from datetime import timedelta

    run_at = datetime.now(timezone.utc) + timedelta(hours=max(1, hours_from_now))
    async with async_session() as session:
        job = ScheduledJob(
            job_type="follow_up",
            channel=channel,
            external_id=external_id,
            lead_id=lead_id,
            payload_json=json.dumps({"note": note}, ensure_ascii=False),
            run_at=run_at,
            status="pending",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job.id


async def process_due_jobs(limit: int = 20) -> int:
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        rows = (
            await session.execute(
                select(ScheduledJob)
                .where(ScheduledJob.status == "pending", ScheduledJob.run_at <= now)
                .order_by(ScheduledJob.run_at.asc())
                .limit(limit)
            )
        ).scalars().all()
        count = 0
        for job in rows:
            note = ""
            try:
                note = json.loads(job.payload_json or "{}").get("note", "")
            except json.JSONDecodeError:
                pass
            msg = f"[Follow-up] {note or 'Nhắc liên hệ khách'}"
            session.add(
                OutboxMessage(
                    channel=job.channel or "web",
                    user_id=job.external_id or "unknown",
                    direction="outbound",
                    content=msg,
                    status="scheduled_sent",
                    meta_json=json.dumps({"job_id": job.id}),
                )
            )
            if job.lead_id:
                lead = await session.get(Lead, job.lead_id)
                if lead:
                    lead.status = "follow_up"
                    lead.notes = (lead.notes + f"\n[Job#{job.id}] {msg}").strip()
            job.status = "done"
            job.result = msg
            count += 1
        await session.commit()
        return count


async def scheduler_loop(stop: asyncio.Event) -> None:
    if not get_settings().scheduler_enabled:
        return
    while not stop.is_set():
        try:
            n = await process_due_jobs()
            if n:
                logger.info("processed %s scheduled jobs", n)
        except Exception:
            logger.exception("scheduler tick failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            pass


async def list_jobs(limit: int = 50) -> list[dict]:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(ScheduledJob).order_by(ScheduledJob.id.desc()).limit(limit)
            )
        ).scalars().all()
    return [
        {
            "id": j.id,
            "job_type": j.job_type,
            "channel": j.channel,
            "external_id": j.external_id,
            "lead_id": j.lead_id,
            "run_at": j.run_at.isoformat() if j.run_at else None,
            "status": j.status,
            "result": j.result,
            "payload": j.payload_json,
        }
        for j in rows
    ]
