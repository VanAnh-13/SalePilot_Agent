"""Unit tests for the in-process sliding-window rate limiter."""

import unittest

from app.services.ratelimit import SlidingWindowLimiter


class FakeClock:
    """Deterministic monotonic clock for limiter tests."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


class SlidingWindowLimiterTests(unittest.TestCase):
    def test_burst_rejected_at_cap(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowLimiter(3, 60, now=clock)
        self.assertTrue(limiter.hit("k"))
        self.assertTrue(limiter.hit("k"))
        self.assertTrue(limiter.hit("k"))
        self.assertFalse(limiter.hit("k"))

    def test_window_expiry_frees_slots(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowLimiter(2, 10, now=clock)
        self.assertTrue(limiter.hit("k"))
        self.assertTrue(limiter.hit("k"))
        self.assertFalse(limiter.hit("k"))
        clock.t += 11  # outside the 10s window
        self.assertTrue(limiter.hit("k"))

    def test_zero_limit_disables(self) -> None:
        limiter = SlidingWindowLimiter(0, 60)
        for _ in range(100):
            self.assertTrue(limiter.hit("k"))

    def test_keys_are_isolated(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowLimiter(1, 60, now=clock)
        self.assertTrue(limiter.hit("a"))
        self.assertTrue(limiter.hit("b"))
        self.assertFalse(limiter.hit("a"))
        self.assertFalse(limiter.hit("b"))

    def test_partial_expiry_frees_exactly_aged_out(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowLimiter(2, 30, now=clock)
        self.assertTrue(limiter.hit("k"))   # t=1000
        clock.t += 10
        self.assertTrue(limiter.hit("k"))   # t=1010 -> window full
        clock.t += 10
        self.assertFalse(limiter.hit("k"))  # t=1020: cutoff=990 keeps both hits
        clock.t += 15
        self.assertTrue(limiter.hit("k"))   # t=1035: cutoff=1005 ages out t=1000 only
        self.assertFalse(limiter.hit("k"))  # t=1036: window full again


if __name__ == "__main__":
    unittest.main()
