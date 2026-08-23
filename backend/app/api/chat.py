import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.graph import run_agent_stream
from app.config import get_settings
from app.services.escalation import is_taken_over
from app.services.gateway import TAKEOVER_REPLY, ingest_message
from app.services.ratelimit import enforce_rate_limit

logger = logging.getLogger("salepilot.chat")

router = APIRouter(prefix="/chat", tags=["chat"])

WEB_CHANNEL = "web"


def _validate_message(message: str) -> None:
    cap = get_settings().max_message_chars
    if len(message) > cap:
        raise HTTPException(413, f"Message too long (max {cap} characters)")


class ChatRequest(BaseModel):
    message: str
    external_id: str = ""
    customer_name: str = "Khách"
    channel: str = "web"
    # conversation_id is intentionally NOT accepted from the client.
    # The server always derives it from (channel, external_id) to prevent
    # cross-user session hijacking (IDOR).


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int | None = None
    lead_id: int | None = None
    used_agents: list[str] = Field(default_factory=list)
    used_tools: list[str] = Field(default_factory=list)
    trace: list[dict] = Field(default_factory=list)
    needs_human: bool = False
    run_id: str | None = None
    # memory and memory_summary intentionally excluded from the public
    # chat response to prevent PII leakage (phone, name, interests).
    # Admins can inspect customer memory via the auth-gated /memory endpoint.
    active_skills: list[str] = Field(default_factory=list)
    decision: dict | None = None


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    _validate_message(req.message)
    external_id = req.external_id or f"web-{uuid.uuid4().hex[:10]}"
    # Abuse guard: per-identity sliding window (falls back to client IP).
    await enforce_rate_limit(request, scope="chat", identity=req.external_id or None)
    # The web ingress always speaks the web channel — ignoring a client-supplied
    # channel closes the IDOR path (a web caller impersonating another channel).
    result = await ingest_message(
        channel=WEB_CHANNEL,
        external_id=external_id,
        text=req.message,
        customer_name=req.customer_name,
    )
    return ChatResponse(
        reply=result["reply"],
        conversation_id=result.get("conversation_id"),
        lead_id=result.get("lead_id"),
        used_agents=result.get("used_agents") or [],
        used_tools=result.get("used_tools") or [],
        trace=result.get("trace") or [],
        needs_human=bool(result.get("needs_human")),
        run_id=result.get("run_id"),
        active_skills=result.get("active_skills") or [],
        decision=result.get("decision"),
    )


@router.post("/stream")
async def chat_stream(req: ChatRequest, request: Request):
    _validate_message(req.message)
    channel = WEB_CHANNEL  # web ingress never accepts another channel (IDOR guard)
    external_id = req.external_id or f"web-{uuid.uuid4().hex[:10]}"
    await enforce_rate_limit(request, scope="chat", identity=external_id or None)
    from app.services.conversation import append_message, get_or_create_conversation, recent_history

    conv = await get_or_create_conversation(
        channel=channel,
        external_id=external_id,
        customer_name=req.customer_name,
    )
    conv_id = conv.id
    # Snapshot history BEFORE appending the new user message so we pass the
    # exact prior turns without a fragile [:-1] ordering assumption.
    history = await recent_history(conv_id)
    await append_message(conv_id, "user", req.message)

    async def event_gen():
        # Human takeover: after escalation the bot must stay silent, matching the
        # batch gateway. The stream path previously bypassed this and kept replying.
        if await is_taken_over(channel, external_id):
            await append_message(conv_id, "assistant", TAKEOVER_REPLY, meta={"takeover": True})
            done = {
                "type": "done",
                "reply": TAKEOVER_REPLY,
                "used_tools": [],
                "used_agents": ["lead"],
                "trace": [{"agent": "lead", "event": "human_takeover", "detail": "bot im lặng"}],
                "needs_human": True,
                "lead_id": conv.lead_id,
                "conversation_id": conv_id,
                "run_id": None,
                "active_skills": [],
                "decision": None,
            }
            yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"
            return

        try:
            final_reply = ""
            displayed = ""  # what the client actually saw streamed (tokens)
            meta: dict = {}
            async for ev in run_agent_stream(
                req.message,
                history=history,
                channel=channel,
                external_id=external_id,
                conversation_id=conv_id,
                lead_id=conv.lead_id,
                customer_name=req.customer_name,
            ):
                if ev.get("type") == "token":
                    displayed += ev.get("content") or ""
                if ev.get("type") == "done":
                    final_reply = ev.get("reply") or ""
                    meta = {
                        "used_agents": ev.get("used_agents"),
                        "used_tools": ev.get("used_tools"),
                        "needs_human": ev.get("needs_human"),
                        "trace": ev.get("trace"),
                        "lead_id": ev.get("lead_id"),
                        "run_id": ev.get("run_id"),
                        "conversation_id": conv_id,
                        "decision": ev.get("decision"),
                    }
                    ev = {**ev, "conversation_id": conv_id}
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            # Persist what the user actually saw (the streamed tokens), not just
            # the canonical final reply — otherwise intermediate lead narration
            # shows in the bubble but never reaches stored history.
            persisted = final_reply or displayed
            if persisted:
                await append_message(conv_id, "assistant", persisted, meta=meta)
        except Exception:
            # Never leave the client hanging on a broken pipe: emit a terminal
            # SSE error event (details stay server-side in the logs).
            logger.exception("agent stream failed mid-turn (conv=%s)", conv_id)
            yield (
                "data: "
                + json.dumps(
                    {"type": "error", "detail": "Agent gặp lỗi khi xử lý tin nhắn."},
                    ensure_ascii=False,
                )
                + "\n\n"
            )

    return StreamingResponse(event_gen(), media_type="text/event-stream")
