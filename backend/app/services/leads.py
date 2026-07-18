from sqlalchemy import select

from app.db.session import async_session
from app.models.entities import Conversation, Lead


async def create_lead_record(
    *,
    name: str,
    phone: str,
    channel: str,
    external_id: str,
    interest: str,
    budget_vnd: int | None,
    notes: str,
    score: float = 0.5,
) -> Lead:
    """Persist a lead for API and agent callers without coupling to a tool context."""
    async with async_session() as session:
        lead = Lead(
            name=name or "Khách",
            phone=phone,
            channel=channel,
            external_id=external_id,
            interest=interest,
            budget_vnd=budget_vnd,
            status="new",
            score=max(0.0, min(float(score), 1.0)),
            notes=notes,
        )
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        return lead


async def upsert_lead_record(
    *,
    name: str,
    phone: str,
    channel: str,
    external_id: str,
    interest: str,
    budget_vnd: int | None,
    notes: str,
    score: float = 0.5,
    status: str = "new",
    conversation_id: int | None = None,
) -> Lead:
    """Create or update the lead for (channel, external_id) — idempotent per customer.

    Used to record a completed consultation on the dashboard without spawning a
    duplicate lead on every message. An owner's manual status (won/qualified/…)
    is never downgraded; we only set the status when the lead is still fresh.
    """
    async with async_session() as session:
        lead: Lead | None = None
        if external_id:
            lead = (
                await session.execute(
                    select(Lead)
                    .where(Lead.channel == channel, Lead.external_id == external_id)
                    .order_by(Lead.id.desc())
                )
            ).scalars().first()

        if lead is None:
            lead = Lead(
                name=name or "Khách",
                phone=phone,
                channel=channel,
                external_id=external_id,
                interest=interest,
                budget_vnd=budget_vnd,
                status=status or "new",
                score=max(0.0, min(float(score), 1.0)),
                notes=notes,
            )
            session.add(lead)
        else:
            if name:
                lead.name = name
            if phone:
                lead.phone = phone
            if interest:
                lead.interest = interest
            if budget_vnd is not None:
                lead.budget_vnd = budget_vnd
            if notes:
                lead.notes = notes
            lead.score = max(0.0, min(float(score), 1.0))
            # Only promote status while the lead is still fresh — never overwrite
            # a manually-progressed lead (qualified/proposal/won/lost/follow_up).
            if status and lead.status in ("", "new"):
                lead.status = status

        await session.commit()
        await session.refresh(lead)

        if conversation_id:
            conv = await session.get(Conversation, conversation_id)
            if conv and conv.lead_id != lead.id:
                conv.lead_id = lead.id
                await session.commit()

        return lead
