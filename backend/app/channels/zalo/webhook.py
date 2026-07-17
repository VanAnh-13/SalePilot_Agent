import hashlib
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select

from app.channels.zalo.client import get_zalo_client
from app.channels.zalo.mapper import event_to_agent_input
from app.channels.zalo.schemas import ZaloEvent, ZaloWebhookResponse
from app.config import get_settings
from app.db.session import async_session
from app.models.entities import Conversation, OutboxMessage, ProcessedEvent
from app.services.gateway import ingest_message

router = APIRouter(prefix="/webhooks/zalo", tags=["zalo"])


def _verify_signature(raw_body: bytes, signature: str | None) -> bool:
    settings = get_settings()
    mode = (settings.zalo_verify_mode or "off").lower()
    if mode == "off":
        return True
    secret = settings.zalo_webhook_secret or settings.zalo_oa_secret
    if not secret:
        return mode != "strict"
    if not signature:
        return mode != "strict"
    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    ok = hmac.compare_digest(digest, signature.replace("sha256=", ""))
    if mode == "soft":
        return True
    return ok


@router.post("", response_model=ZaloWebhookResponse)
@router.post("/", response_model=ZaloWebhookResponse)
async def zalo_webhook(
    request: Request,
    x_zalo_signature: str | None = Header(default=None, alias="X-Zalo-Signature"),
):
    settings = get_settings()
    if not settings.zalo_enabled:
        raise HTTPException(status_code=503, detail="Zalo channel disabled")

    raw = await request.body()
    if not _verify_signature(raw, x_zalo_signature):
        raise HTTPException(status_code=401, detail="Invalid Zalo signature")

    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    # support both flat and nested OA formats
    if "event_name" not in payload and "message" in payload:
        payload.setdefault("event_name", "user_send_text")
    event = ZaloEvent.model_validate(payload)
    mapped = event_to_agent_input(event)
    event_id = mapped["event_id"]

    async with async_session() as session:
        existing = (
            await session.execute(select(ProcessedEvent).where(ProcessedEvent.event_id == event_id))
        ).scalar_one_or_none()
        if existing:
            return ZaloWebhookResponse(ok=True, event_id=event_id, skipped=True, reason="duplicate")

    if event.event_name not in ("user_send_text", "user_send_image", "follow"):
        return ZaloWebhookResponse(ok=True, event_id=event_id, skipped=True, reason=f"ignored:{event.event_name}")

    if event.event_name == "user_send_image":
        reply = "Em nhận ảnh rồi ạ — hiện em hỗ trợ tốt nhất qua tin nhắn chữ. Bạn mô tả giúp em nhu cầu nhé!"
        client = get_zalo_client()
        await client.send_text(mapped["external_id"], reply)
        return ZaloWebhookResponse(ok=True, event_id=event_id, reply=reply)

    if event.event_name == "follow":
        reply = (
            f"Cảm ơn bạn đã follow {settings.shop_name}! "
            "Em là SalePilot — cho em biết số người, ngân sách hoặc kiểu tủ lạnh cần tìm nhé."
        )
        client = get_zalo_client()
        await client.send_text(mapped["external_id"], reply)
        async with async_session() as session:
            session.add(ProcessedEvent(event_id=event_id))
            session.add(
                OutboxMessage(
                    channel="zalo",
                    user_id=mapped["external_id"],
                    direction="inbound",
                    content="[follow]",
                    status="received",
                )
            )
            await session.commit()
        return ZaloWebhookResponse(ok=True, event_id=event_id, reply=reply)

    text = mapped["text"]
    if not text:
        return ZaloWebhookResponse(ok=True, event_id=event_id, skipped=True, reason="empty_text")

    async with async_session() as session:
        session.add(
            OutboxMessage(
                channel="zalo",
                user_id=mapped["external_id"],
                direction="inbound",
                content=text,
                status="received",
            )
        )
        await session.commit()

    # Unified channel bus
    result = await ingest_message(
        channel="zalo",
        external_id=mapped["external_id"],
        text=text,
        customer_name=mapped["customer_name"],
    )
    reply = result["reply"]

    if result.get("needs_human") and result.get("conversation_id"):
        async with async_session() as session:
            c = await session.get(Conversation, result["conversation_id"])
            if c:
                c.needs_human = True
                c.status = "escalated"
                await session.commit()

    client = get_zalo_client()
    await client.send_text(mapped["external_id"], reply)

    async with async_session() as session:
        session.add(ProcessedEvent(event_id=event_id))
        await session.commit()

    return ZaloWebhookResponse(
        ok=True,
        event_id=event_id,
        reply=reply,
        used_tools=result.get("used_tools") or [],
    )
