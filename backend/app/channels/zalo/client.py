import json
from typing import Protocol

import httpx

from app.config import get_settings
from app.db.session import async_session
from app.models.entities import OutboxMessage


class ZaloOAClient(Protocol):
    async def send_text(self, user_id: str, text: str) -> str: ...

    async def send_template(self, user_id: str, template_id: str, data: dict) -> str: ...

    async def get_profile(self, user_id: str) -> dict: ...


class MockZaloOAClient:
    """In-memory/DB outbox — no real Zalo API calls."""

    async def send_text(self, user_id: str, text: str) -> str:
        async with async_session() as session:
            row = OutboxMessage(
                channel="zalo",
                user_id=user_id,
                direction="outbound",
                content=text,
                status="sent_mock",
                meta_json=json.dumps({"via": "mock"}),
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return f"mock-msg-{row.id}"

    async def send_template(self, user_id: str, template_id: str, data: dict) -> str:
        body = f"[template:{template_id}] {json.dumps(data, ensure_ascii=False)}"
        return await self.send_text(user_id, body)

    async def get_profile(self, user_id: str) -> dict:
        return {
            "user_id": user_id,
            "display_name": f"Zalo User {user_id[-4:] if user_id else '0000'}",
            "avatar": "",
            "shared_info": {"phone": "", "address": "Hà Nội"},
        }


class HttpZaloOAClient:
    """Skeleton for real Zalo OA Open API — wire token later."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base = "https://openapi.zalo.me/v3.0/oa"

    async def send_text(self, user_id: str, text: str) -> str:
        if not self.access_token:
            raise RuntimeError("ZALO_OA_ACCESS_TOKEN empty — use ZALO_CLIENT=mock")
        # TODO: real endpoint when OA app is approved
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.base}/message/cs",
                headers={"access_token": self.access_token},
                json={
                    "recipient": {"user_id": user_id},
                    "message": {"text": text},
                },
            )
            # also log outbox
            mock = MockZaloOAClient()
            await mock.send_text(user_id, text)
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("data", {}).get("message_id", "zalo-http"))

    async def send_template(self, user_id: str, template_id: str, data: dict) -> str:
        return await self.send_text(user_id, f"[template {template_id}] {data}")

    async def get_profile(self, user_id: str) -> dict:
        if not self.access_token:
            return await MockZaloOAClient().get_profile(user_id)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.base}/user/detail",
                headers={"access_token": self.access_token},
                params={"data": json.dumps({"user_id": user_id})},
            )
            if resp.status_code >= 400:
                return await MockZaloOAClient().get_profile(user_id)
            return resp.json()


def get_zalo_client() -> ZaloOAClient:
    settings = get_settings()
    if settings.zalo_client.lower() == "http":
        return HttpZaloOAClient(settings.zalo_oa_access_token)
    return MockZaloOAClient()
