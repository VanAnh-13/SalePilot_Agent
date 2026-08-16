"""Memory hygiene: GDPR erase endpoint + no duplicate auto-extract notes."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="salepilot_memory_hygiene_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/memory_hygiene.db"
os.environ["ADMIN_API_KEY"] = "hygiene-admin-key"
os.environ["TRAJECTORY_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.agent.memory.store import erase_memory, load_profile, merge_profile  # noqa: E402
from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402

ADMIN_HEADERS = {"X-Admin-Token": "hygiene-admin-key"}


class MemoryHygieneTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        import asyncio

        asyncio.run(init_db())
        cls.client = TestClient(app)

    async def test_repeated_identical_notes_do_not_duplicate(self):
        ch, ext = "web", "hygiene-notes-1"
        await merge_profile(ch, ext, note="auto-extract", interest="tủ lạnh")
        await merge_profile(ch, ext, note="auto-extract", interest="tủ lạnh")
        await merge_profile(ch, ext, note="auto-extract", interest="tủ lạnh")
        profile = await load_profile(ch, ext)
        self.assertEqual(profile["notes"].count("auto-extract"), 1)
        # A different note still appends.
        await merge_profile(ch, ext, note="khách hỏi bảo hành")
        profile = await load_profile(ch, ext)
        self.assertEqual(len(profile["notes"]), 2)

    def test_delete_memory_endpoint_erases_and_404s(self):
        ch, ext = "web", "hygiene-erase-1"

        def _seed():
            import asyncio

            asyncio.run(merge_profile(ch, ext, phone="0912345678", note="seed"))

        _seed()
        before = self.client.get(f"/memory/{ch}/{ext}", headers=ADMIN_HEADERS)
        self.assertEqual(before.status_code, 200)
        self.assertTrue(before.json()["profile"].get("phone"))

        # Fail closed without token.
        no_auth = self.client.delete(f"/memory/{ch}/{ext}")
        self.assertIn(no_auth.status_code, (401, 403))

        deleted = self.client.delete(f"/memory/{ch}/{ext}", headers=ADMIN_HEADERS)
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["ok"])

        after = self.client.get(f"/memory/{ch}/{ext}", headers=ADMIN_HEADERS)
        self.assertEqual(after.json()["profile"].get("phone") or "", "")

        missing = self.client.delete(f"/memory/{ch}/never-existed", headers=ADMIN_HEADERS)
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
