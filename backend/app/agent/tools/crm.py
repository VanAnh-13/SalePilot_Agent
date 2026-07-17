import json
from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool

from app.agent.tools.runtime import get_ctx, note_tool
from app.db.session import async_session
from app.models.entities import Conversation, Lead
from app.services.leads import create_lead_record


@tool
async def create_lead(
    name: str = "",
    phone: str = "",
    interest: str = "",
    budget_vnd: int = 0,
    notes: str = "",
    score: float = 0.5,
) -> str:
    """Tạo lead CRM khi khách có nhu cầu mua / để lại liên hệ. score 0-1."""
    note_tool("create_lead")
    ctx = get_ctx()
    lead = await create_lead_record(
        name=name or ctx.customer_name or "Khách",
        phone=phone,
        channel=ctx.channel,
        external_id=ctx.external_id,
        interest=interest,
        budget_vnd=budget_vnd or None,
        notes=notes,
        score=score,
    )
    ctx.lead_id = lead.id
    async with async_session() as session:
        if ctx.conversation_id:
            conv = await session.get(Conversation, ctx.conversation_id)
            if conv:
                conv.lead_id = lead.id
                await session.commit()
        return json.dumps(
            {
                "lead_id": lead.id,
                "status": lead.status,
                "score": lead.score,
                "message": f"Đã tạo lead #{lead.id}",
            },
            ensure_ascii=False,
        )


@tool
async def update_lead_status(lead_id: int, status: str, notes: str = "") -> str:
    """Cập nhật trạng thái lead: new | qualified | proposal | won | lost | follow_up."""
    note_tool("update_lead_status")
    allowed = {"new", "qualified", "proposal", "won", "lost", "follow_up"}
    if status not in allowed:
        return json.dumps({"error": f"status phải thuộc {sorted(allowed)}"}, ensure_ascii=False)
    async with async_session() as session:
        lead = await session.get(Lead, lead_id)
        if not lead:
            return json.dumps({"error": f"Không tìm thấy lead {lead_id}"}, ensure_ascii=False)
        lead.status = status
        if notes:
            lead.notes = (lead.notes + "\n" + notes).strip()
        await session.commit()
        return json.dumps({"lead_id": lead.id, "status": lead.status}, ensure_ascii=False)


@tool
async def schedule_followup(lead_id: int = 0, hours_from_now: int = 24, note: str = "") -> str:
    """Lên lịch follow-up thật (ScheduledJob). Mặc định sau 24 giờ."""
    note_tool("schedule_followup")
    from app.services.scheduler import create_followup_job

    ctx = get_ctx()
    lid = lead_id or ctx.lead_id or 0
    when = datetime.now(timezone.utc) + timedelta(hours=max(1, hours_from_now))
    job_id = await create_followup_job(
        channel=ctx.channel,
        external_id=ctx.external_id,
        lead_id=lid or None,
        hours_from_now=hours_from_now,
        note=note or "Gọi lại khách",
    )
    async with async_session() as session:
        if lid:
            lead = await session.get(Lead, lid)
            if lead:
                lead.status = "follow_up"
                stamp = when.strftime("%Y-%m-%d %H:%M UTC")
                lead.notes = (lead.notes + f"\n[Follow-up {stamp} job#{job_id}] {note}").strip()
                await session.commit()
    return json.dumps(
        {
            "scheduled": True,
            "job_id": job_id,
            "lead_id": lid or None,
            "follow_up_at": when.isoformat(),
            "note": note or "Gọi lại khách",
        },
        ensure_ascii=False,
    )


@tool
async def escalate_to_human(reason: str, summary: str = "") -> str:
    """Chuyển hội thoại cho nhân viên thật (khiếu nại, yêu cầu gặp người, deal phức tạp)."""
    note_tool("escalate_to_human")
    ctx = get_ctx()
    ctx.needs_human = True
    async with async_session() as session:
        if ctx.conversation_id:
            conv = await session.get(Conversation, ctx.conversation_id)
            if conv:
                conv.needs_human = True
                conv.status = "escalated"
                conv.summary = summary or reason
                await session.commit()
        if ctx.lead_id:
            lead = await session.get(Lead, ctx.lead_id)
            if lead:
                lead.notes = (lead.notes + f"\n[ESCALATE] {reason}").strip()
                await session.commit()
    return json.dumps(
        {
            "escalated": True,
            "reason": reason,
            "message": "Đã tạo ticket cho team CSKH. Phản hồi trong giờ 9:00–21:00.",
        },
        ensure_ascii=False,
    )
