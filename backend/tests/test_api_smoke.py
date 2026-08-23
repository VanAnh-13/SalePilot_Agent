"""HTTP smoke tests for the FastAPI surface.

Hermetic: a temp sqlite database and an offline (no LLM key) agent are forced
via environment variables BEFORE app import, so no Postgres or external
service is needed. Trajectory writing is disabled to keep the repo clean.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="salepilot_api_smoke_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/api_smoke.db"
os.environ["ADMIN_API_KEY"] = "smoke-admin-key"
os.environ["TRAJECTORY_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402
from tests.catalog_fixture import installed_catalog_fixture  # noqa: E402

ADMIN_HEADERS = {"X-Admin-Token": "smoke-admin-key"}


class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog_fixture = installed_catalog_fixture()
        cls.catalog_fixture.__enter__()
        import asyncio

        asyncio.run(init_db())
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.catalog_fixture.__exit__(None, None, None)

    def test_root_liveness_probe(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])

    def test_health_reports_catalog_identity(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["ok"])
        self.assertIn("catalog", body)

    def test_chat_offline_returns_reply_and_conversation(self):
        res = self.client.post(
            "/chat",
            json={
                "message": "Gia đình 4 người cần tủ lạnh dưới 15 triệu",
                "external_id": "api-smoke-1",
                "channel": "web",
            },
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIsInstance(body["reply"], str)
        self.assertTrue(body["reply"])
        self.assertIsNotNone(body["conversation_id"])
        # PII guard: public chat response must not echo customer memory.
        self.assertNotIn("memory", body)
        self.assertNotIn("memory_summary", body)

    def test_admin_endpoints_fail_closed_without_token(self):
        for path in ("/leads", "/memory", "/jobs", "/runs/latest"):
            res = self.client.get(path)
            self.assertIn(res.status_code, (401, 403), path)

    def test_admin_endpoints_reject_wrong_token(self):
        res = self.client.get("/leads", headers={"X-Admin-Token": "wrong"})
        self.assertEqual(res.status_code, 403)

    def test_admin_endpoints_accept_valid_token(self):
        res = self.client.get("/leads", headers=ADMIN_HEADERS)
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_runs_metrics_endpoint(self):
        res = self.client.get("/runs/metrics", headers=ADMIN_HEADERS)
        self.assertEqual(res.status_code, 200)

    def test_chat_after_escalation_returns_takeover_notice_without_agent_run(self):
        import asyncio

        from app.services.escalation import is_taken_over, open_escalation

        first = self.client.post(
            "/chat",
            json={"message": "cho em hỏi người dùng tủ lạnh", "external_id": "takeover-1", "channel": "web"},
        )
        self.assertEqual(first.status_code, 200)
        conv_id = first.json()["conversation_id"]
        self.assertIsNotNone(conv_id)

        asyncio.run(
            open_escalation(
                conversation_id=conv_id,
                channel="web",
                external_id="takeover-1",
                reason="Khách yêu cầu gặp người",
            )
        )
        self.assertTrue(asyncio.run(is_taken_over("web", "takeover-1")))

        second = self.client.post(
            "/chat",
            json={"message": "alo còn ai không", "external_id": "takeover-1", "channel": "web"},
        )
        self.assertEqual(second.status_code, 200)
        body = second.json()
        self.assertTrue(body["needs_human"])
        self.assertIn("tư vấn viên", body["reply"])
        events = [step.get("event") for step in body["trace"]]
        self.assertIn("human_takeover", events)
        self.assertFalse(body["used_tools"])

    def test_admin_takeover_and_resolve_endpoints(self):
        chat = self.client.post(
            "/chat",
            json={"message": "máy giặt 9kg", "external_id": "resolve-1", "channel": "web"},
        )
        self.assertEqual(chat.status_code, 200)

        # Without token: fail closed.
        res = self.client.post(
            "/leads/conversations/resolve", json={"channel": "web", "external_id": "resolve-1"}
        )
        self.assertIn(res.status_code, (401, 403))

        take = self.client.post(
            "/leads/conversations/takeover",
            json={"channel": "web", "external_id": "resolve-1"},
            headers=ADMIN_HEADERS,
        )
        self.assertEqual(take.status_code, 200)
        self.assertEqual(take.json()["status"], "escalated")

        # While taken over, the bot stays silent.
        silent = self.client.post(
            "/chat",
            json={"message": "hello?", "external_id": "resolve-1", "channel": "web"},
        )
        self.assertIn("human_takeover", [s.get("event") for s in silent.json()["trace"]])

        resolved = self.client.post(
            "/leads/conversations/resolve",
            json={"channel": "web", "external_id": "resolve-1"},
            headers=ADMIN_HEADERS,
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["status"], "open")

        # After resolve, the agent runs again (no human_takeover event).
        again = self.client.post(
            "/chat",
            json={"message": "máy giặt cửa trước 9kg", "external_id": "resolve-1", "channel": "web"},
        )
        self.assertEqual(again.status_code, 200)
        self.assertNotIn(
            "human_takeover", [s.get("event") for s in again.json()["trace"]]
        )

        missing = self.client.post(
            "/leads/conversations/resolve",
            json={"channel": "web", "external_id": "no-such-user"},
            headers=ADMIN_HEADERS,
        )
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
