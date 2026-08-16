"""Request-scoped bag for Lead tools / skills / trace."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_EMPTY = {
    "results": [],
    "trace": [],
    "final": None,
    "decision": None,
    "delegates": 0,
    "active_skills": [],
    "skill_bodies": {},
}

_run_bag_var: ContextVar[dict[str, Any] | None] = ContextVar("salepilot_run_bag", default=None)


def _new_bag() -> dict[str, Any]:
    return {
        "results": [],
        "trace": [],
        "final": None,
        "decision": None,
        "delegates": 0,
        "active_skills": [],
        "skill_bodies": {},
    }


def reset_run_bag() -> dict[str, Any]:
    bag = _new_bag()
    _run_bag_var.set(bag)
    return bag


def get_run_bag() -> dict[str, Any]:
    bag = _run_bag_var.get()
    if bag is None:
        bag = _new_bag()
        _run_bag_var.set(bag)
    return bag


def bag_trace(agent: str, event: str, detail: str = "") -> None:
    get_run_bag()["trace"].append({"agent": agent, "event": event, "detail": detail})
