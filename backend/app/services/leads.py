from app.db.session import async_session
from app.models.entities import Lead


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
