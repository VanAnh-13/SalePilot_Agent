"""Shared per-turn bag for Lead tools / skills / trace (avoids circular imports)."""

from __future__ import annotations

from typing import Any

_run_bag: dict[str, Any] = {
    "results": [],
    "trace": [],
    "final": None,
    "delegates": 0,
    "active_skills": [],
    "skill_bodies": {},
}


def reset_run_bag() -> dict[str, Any]:
    bag: dict[str, Any] = {
        "results": [],
        "trace": [],
        "final": None,
        "delegates": 0,
        "active_skills": [],
        "skill_bodies": {},
    }
    _run_bag.clear()
    _run_bag.update(bag)
    return _run_bag


def get_run_bag() -> dict[str, Any]:
    return _run_bag


def bag_trace(agent: str, event: str, detail: str = "") -> None:
    _run_bag["trace"].append({"agent": agent, "event": event, "detail": detail})
