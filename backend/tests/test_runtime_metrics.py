from __future__ import annotations

import unittest

from app.observability import metrics


class RuntimeMetricsTests(unittest.TestCase):
    def setUp(self):
        metrics.reset()

    def tearDown(self):
        metrics.reset()

    def test_empty_snapshot(self):
        snap = metrics.snapshot()
        self.assertEqual(snap["total_runs"], 0)
        self.assertEqual(snap["routes"], {})
        self.assertEqual(snap["window_size"], metrics.WINDOW)

    def test_percentiles_counts_and_share(self):
        for ms in range(1, 101):
            metrics.record_run("fast_path", float(ms))
        metrics.record_run("offline", 50.0)
        snap = metrics.snapshot()
        fast = snap["routes"]["fast_path"]
        self.assertEqual(fast["count"], 100)
        self.assertEqual(fast["window"], 100)
        self.assertAlmostEqual(fast["p50_ms"], 50.0, delta=1.0)
        self.assertAlmostEqual(fast["p95_ms"], 95.0, delta=1.0)
        self.assertEqual(fast["max_ms"], 100.0)
        self.assertAlmostEqual(fast["share"], 100 / 101, places=3)
        offline = snap["routes"]["offline"]
        self.assertEqual(offline["count"], 1)
        self.assertEqual(offline["p50_ms"], 50.0)
        self.assertEqual(snap["total_runs"], 101)

    def test_window_keeps_recent_samples_and_total_count(self):
        for ms in range(1000):
            metrics.record_run("llm_graph", float(ms))
        snap = metrics.snapshot()
        stats = snap["routes"]["llm_graph"]
        self.assertEqual(stats["count"], 1000)
        self.assertEqual(stats["window"], metrics.WINDOW)
        self.assertEqual(stats["max_ms"], 999.0)
        # Sliding window holds the most recent WINDOW samples only.
        self.assertGreaterEqual(stats["p50_ms"], 1000 - metrics.WINDOW)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
