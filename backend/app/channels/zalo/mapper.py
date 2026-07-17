from app.channels.zalo.schemas import ZaloEvent


def event_to_agent_input(event: ZaloEvent) -> dict:
    user_id = event.sender.id or "zalo-unknown"
    text = (event.message.text or "").strip()
    event_id = event.message.msg_id or f"{user_id}-{event.timestamp}-{event.event_name}"
    return {
        "event_id": event_id,
        "event_name": event.event_name,
        "channel": "zalo",
        "external_id": user_id,
        "text": text,
        "customer_name": f"Zalo:{user_id[-6:]}",
    }
