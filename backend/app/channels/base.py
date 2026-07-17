from typing import Protocol


class ChannelAdapter(Protocol):
    name: str

    async def send_text(self, user_id: str, text: str) -> str: ...
