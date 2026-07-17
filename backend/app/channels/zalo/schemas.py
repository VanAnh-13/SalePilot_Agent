from pydantic import BaseModel, Field


class ZaloSender(BaseModel):
    id: str = ""


class ZaloMessage(BaseModel):
    text: str = ""
    msg_id: str = Field(default="", alias="msg_id")

    model_config = {"populate_by_name": True}


class ZaloEvent(BaseModel):
    """Subset of Zalo OA webhook payload for demo/stub."""

    event_name: str = "user_send_text"
    app_id: str = ""
    sender: ZaloSender = Field(default_factory=ZaloSender)
    recipient: ZaloSender = Field(default_factory=ZaloSender)
    message: ZaloMessage = Field(default_factory=ZaloMessage)
    timestamp: str = ""

    # allow extra fields from real OA
    model_config = {"extra": "allow", "populate_by_name": True}


class ZaloWebhookResponse(BaseModel):
    ok: bool = True
    event_id: str = ""
    reply: str = ""
    used_tools: list[str] = Field(default_factory=list)
    skipped: bool = False
    reason: str = ""
