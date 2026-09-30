"""In-process route/latency recorder for deployment-integration evidence.

Per-route request counters plus a sliding window of durations, from which
p50/p95 are computed on demand. No external dependency so the offline
no-key path stays hermetic; a lock keeps it safe for the threaded callers
(MCP smoke, sync scripts) that share the process with the event loop.
"""

from __future__ import annotations

import threading
import time
from collections import deque

WINDOW = 512

_lock = threading.Lock()
_started_at = time.time()
_samples: dict[str, deque[float]] = {}
_totals: dict[str, int] = {}


def record_run(route: str, duration_ms: float) -> None:
    with _lock:
        _samples.setdefault(route, deque(maxlen=WINDOW)).append(float(duration_ms))
        _totals[route] = _totals.get(route, 0) + 1


def _percentile(sorted_values: list[float], q: float) -> float:
    """Nearest-rank percentile over a non-empty ascending list."""
    idx = max(0, min(len(sorted_values) - 1, round(q * (len(sorted_values) - 1))))
    return sorted_values[idx]


def snapshot() -> dict:
    with _lock:
        totals = dict(_totals)
        windows = {route: sorted(values) for route, values in _samples.items()}
    total = sum(totals.values())
    routes: dict[str, dict] = {}
    for route in sorted(totals):
        window = windows.get(route) or []
        routes[route] = {
            "count": totals[route],
            "share": round(totals[route] / total, 4) if total else 0.0,
            "window": len(window),
            "p50_ms": round(_percentile(window, 0.50), 1) if window else None,
            "p95_ms": round(_percentile(window, 0.95), 1) if window else None,
            "max_ms": round(window[-1], 1) if window else None,
        }
    return {
        "total_runs": total,
        "window_size": WINDOW,
        "uptime_s": round(time.time() - _started_at, 1),
        "routes": routes,
    }


def reset() -> None:
    """Test hook: drop all recorded samples and counters."""
    with _lock:
        _samples.clear()
        _totals.clear()
