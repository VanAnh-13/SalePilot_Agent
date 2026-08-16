"""Agent package. Import concrete modules directly to avoid heavy import side effects."""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    if name in {"run_agent", "run_agent_stream"}:
        from app.agent.graph import run_agent, run_agent_stream

        return run_agent if name == "run_agent" else run_agent_stream
    raise AttributeError(name)


__all__ = ["run_agent", "run_agent_stream"]
