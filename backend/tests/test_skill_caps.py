"""Single-source skill size caps and safe-by-default sandbox."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import inspect  # noqa: E402

from app.agent.graph import _auto_activate_skills  # noqa: E402
from app.agent.skills import loader, tools as skill_tools  # noqa: E402
from app.agent.skills.tools import activate_skill  # noqa: E402
from app.agent.run_bag import get_run_bag, reset_run_bag  # noqa: E402


class SkillCapTests(unittest.TestCase):
    def test_body_cap_constant_is_the_only_truncation(self):
        """No module truncates a skill body to a different size than the cap."""
        sources = {
            "loader": inspect.getsource(loader),
            "skill_tools": inspect.getsource(skill_tools),
        }
        for name, src in sources.items():
            self.assertNotIn("[:8000]", src, name)
            self.assertNotIn("[:6000]", src, name)
        # The graph must not re-cut what the bag already capped.
        from app.agent import graph

        self.assertNotIn("[:6000]", inspect.getsource(graph))

    def test_activate_skill_uses_shared_cap(self):
        reset_run_bag()
        import asyncio

        raw = asyncio.run(activate_skill.ainvoke({"name": "compare_products"}))
        body = get_run_bag()["skill_bodies"]["compare_products"]
        self.assertLessEqual(len(body), loader.SKILL_BODY_CAP)
        import json

        self.assertTrue(json.loads(raw)["ok"])

    def test_auto_activation_uses_shared_cap(self):
        reset_run_bag()
        _auto_activate_skills("so sánh 2 máy giặt giúp em")
        for body in get_run_bag()["skill_bodies"].values():
            self.assertLessEqual(len(body), loader.SKILL_BODY_CAP)


class SandboxDefaultTests(unittest.TestCase):
    def test_sandbox_disabled_by_default(self):
        from app.config import Settings

        self.assertIs(Settings.model_fields["sandbox_enabled"].default, False)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
