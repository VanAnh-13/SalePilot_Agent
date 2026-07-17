import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.graph import run_agent_stream
from app.services.gateway import ingest_message

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    external_id: str = ""
    customer_name: str = "Khách"
    channel: str = "web"
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int | None = None
    lead_id: int | None = None
    used_agents: list[str] = Field(default_factory=list)
    used_tools: list[str] = Field(default_factory=list)
    trace: list[dict] = Field(default_factory=list)
    needs_human: bool = False
    run_id: str | None = None
    memory: dict | None = None
    memory_summary: str | None = None
    active_skills: list[str] = Field(default_factory=list)


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    external_id = req.external_id or f"web-{uuid.uuid4().hex[:10]}"
    result = await ingest_message(
        channel=req.channel,
        external_id=external_id,
        text=req.message,
        customer_name=req.customer_name,
        conversation_id=req.conversation_id,
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
        memory=result.get("memory"),
        memory_summary=result.get("memory_summary"),
        active_skills=result.get("active_skills") or [],
    )


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    external_id = req.external_id or f"web-{uuid.uuid4().hex[:10]}"
    # stream path still uses graph directly after ensuring conversation via gateway logic
    from app.services.conversation import append_message, get_or_create_conversation, recent_history

    conv = await get_or_create_conversation(
        channel=req.channel,
        external_id=external_id,
        customer_name=req.customer_name,
    )
    conv_id = req.conversation_id or conv.id
    await append_message(conv_id, "user", req.message)
    history = await recent_history(conv_id)

    async def event_gen():
        final_reply = ""
        meta: dict = {}
        async for ev in run_agent_stream(
            req.message,
            history=history[:-1],
            channel=req.channel,
            external_id=external_id,
            conversation_id=conv_id,
            lead_id=conv.lead_id,
            customer_name=req.customer_name,
        ):
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
                }
                ev = {**ev, "conversation_id": conv_id}
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        if final_reply:
            await append_message(conv_id, "assistant", final_reply, meta=meta)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
