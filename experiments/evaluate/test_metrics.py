from __future__ import annotations

import unittest

from experiments.evaluate.metrics import (
    action_match,
    aggregate,
    category_correct,
    hard_constraint_violations,
    slot_micro_f1,
)
from experiments.evaluate.runner import score_conditions, score_episode


class MetricTests(unittest.TestCase):
    def test_category_and_action(self):
        self.assertTrue(category_correct("tu_lanh", "tu_lanh"))
        self.assertFalse(category_correct("tu_lanh", "may_lanh"))
        self.assertTrue(action_match("clarify", "clarify"))

    def test_slot_f1(self):
        m = slot_micro_f1({"budget_vnd": 10, "household_size": 4}, {"budget_vnd": 10, "household_size": 3})
        self.assertEqual(m["tp"], 1)
        self.assertGreater(m["f1"], 0)
        self.assertLess(m["f1"], 1)

    def test_slot_f1_counts_unexpected_slots(self):
        m = slot_micro_f1(
            {"budget_vnd": 10},
            {"budget_vnd": 10, "unsupported_slot": "invented", "category": "tu_lanh"},
        )
        self.assertEqual(m["tp"], 1)
        self.assertEqual(m["fp"], 1)
        self.assertEqual(m["fn"], 0)
        self.assertLess(m["f1"], 1.0)

    def test_hard_constraints_unknown_exclude_counts(self):
        top = [
            {
                "price_vnd": 12,
            }
        ]
        res = hard_constraint_violations([], top)
        self.assertEqual(res["violations"], 0)  # empty protocol list short-circuits
        res2 = hard_constraint_violations(
            [{"key": "budget_vnd", "op": "lte", "value": 10, "missing_policy": "exclude"}],
            top,
        )
        self.assertEqual(res2["checked"], 1)
        self.assertEqual(res2["violations"], 1)  # label says 10; item costs 12

    def test_hard_constraints_ignore_untrusted_item_status(self):
        top = [{"price_vnd": 12, "constraints": [{"status": "matched"}]}]
        res = hard_constraint_violations(
            [{"key": "budget_vnd", "op": "lte", "value": 10, "missing_policy": "exclude"}],
            top,
        )
        self.assertEqual(res["violations"], 1)

    def test_range_constraint_uses_catalog_range(self):
        top = [{"area_min": 15, "area_max": 20}]
        res = hard_constraint_violations(
            [{"key": "area_m2", "op": "range_fit", "value": 18, "missing_policy": "clarify"}],
            top,
        )
        self.assertEqual(res["violations"], 0)

    def test_aggregate(self):
        rows = [
            {
                "category_correct": True,
                "action_correct": True,
                "slot_f1": {"tp": 2, "fp": 0, "fn": 0},
                "hard_constraints": {"checked": 2, "violations": 0},
            },
            {
                "category_correct": False,
                "action_correct": True,
                "slot_f1": {"tp": 0, "fp": 2, "fn": 2},
                "hard_constraints": {"checked": 1, "violations": 1},
            },
        ]
        agg = aggregate(rows)
        self.assertEqual(agg["episodes"], 2)
        self.assertEqual(agg["category_accuracy"], 0.5)
        self.assertEqual(agg["action_accuracy"], 1.0)
        self.assertEqual(agg["slot_micro_f1"], 0.5)
        self.assertEqual(agg["hard_constraint_violation_rate"], 0.3333)

    def test_missing_prediction_never_scores_as_correct_abstain(self):
        label = {
            "episode_id": "dev-missing",
            "category": None,
            "expected_action": "abstain",
            "expected_slots": {},
            "hard_constraints": [],
        }
        row = score_episode(label, {})
        self.assertTrue(row["prediction_missing"])
        self.assertFalse(row["category_correct"])
        self.assertFalse(row["action_correct"])

    def test_condition_matrix_rejects_missing_rows(self):
        labels = [{"episode_id": "dev-1", "expected_action": "recommend"}]
        predictions = [
            {"episode_id": "dev-1", "condition": "A", "predicted_action": "recommend"}
        ]
        with self.assertRaisesRegex(ValueError, "missing 1 condition/episode"):
            score_conditions(labels, predictions, ["A", "B"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
