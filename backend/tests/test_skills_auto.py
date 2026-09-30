"""Auto-activation of matching skills (data-driven matcher, no keyword lists)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.agent.graph import _auto_activate_skills  # noqa: E402
from app.agent.run_bag import get_run_bag, reset_run_bag  # noqa: E402
from app.agent.skills.loader import load_skill_body, list_skills  # noqa: E402
from app.agent.skills.matcher import match_skills  # noqa: E402


class MatcherTests(unittest.TestCase):
    def test_compare_request_matches_compare_skill(self):
        for msg in ("so sánh 2 máy giặt giúp em", "so sanh tu lanh nao tot hon"):
            self.assertIn("compare_products", match_skills(msg), msg)

    def test_escalation_matches_handoff(self):
        self.assertIn("handoff", match_skills("cho em gặp người tư vấn viên"))
        self.assertIn("handoff", match_skills("khieu nai don hang cua em"))

    def test_contact_left_matches_lead_qualify(self):
        self.assertIn("lead_qualify", match_skills("em để lại sđt 0912345678 mua tủ lạnh"))

    def test_plain_recommend_and_greeting_match_nothing(self):
        self.assertEqual(match_skills("gia đình 4 người cần tủ lạnh dưới 15 triệu"), [])
        self.assertEqual(match_skills("xin chào"), [])

    def test_at_most_two_skills_per_turn(self):
        self.assertLessEqual(len(match_skills("so sánh và giải thích thông số giúp em")), 2)


class AutoActivateTests(unittest.TestCase):
    def test_matching_skill_loaded_into_bag_with_trace(self):
        reset_run_bag()
        _auto_activate_skills("so sánh 2 máy giặt giúp em")
        bag = get_run_bag()
        self.assertIn("compare_products", bag["active_skills"])
        self.assertIn("compare_products", bag["skill_bodies"])
        self.assertEqual(bag["skill_bodies"]["compare_products"], load_skill_body("compare_products")[:8000])
        self.assertIn(
            {"agent": "lead", "event": "skill", "detail": "auto:compare_products"},
            bag["trace"],
        )

    def test_unmatched_message_activates_nothing(self):
        reset_run_bag()
        _auto_activate_skills("xin chào")
        self.assertEqual(get_run_bag()["active_skills"], [])

    def test_flag_off_disables_auto_activation(self):
        from app.config import get_settings

        os.environ["AUTO_ACTIVATE_SKILLS"] = "false"
        get_settings.cache_clear()
        try:
            reset_run_bag()
            _auto_activate_skills("so sánh 2 máy giặt giúp em")
            self.assertEqual(get_run_bag()["active_skills"], [])
        finally:
            os.environ.pop("AUTO_ACTIVATE_SKILLS", None)
            get_settings.cache_clear()


if __name__ == "__main__":
    raise SystemExit(unittest.main())
