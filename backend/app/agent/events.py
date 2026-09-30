"""SSE/batch event builders and the run-result contract (pure, no dependencies)."""

from typing import Any, TypedDict


class RunResult(TypedDict, total=False):
    """The result shape every serving route returns (batch and streaming)."""

    reply: str
    used_tools: list[str]
    used_agents: list[str]
    trace: list[dict[str, Any]]
    subagent_results: list[dict[str, Any]]
    needs_human: bool
    lead_id: int | None
    conversation_id: int | None
    run_id: str | None
    memory: dict[str, Any]
    memory_summary: str
    active_skills: list[str]
    memory_before: dict[str, Any]
    fast_path: bool
    decision: dict[str, Any] | None
    route: str


CHUNK_MIN_STEP = 12
CHUNK_DIVISOR = 20


def chunk_reply(reply: str) -> list[str]:
    """Split a fully-computed reply into UI-sized pieces (offline/fast routes)."""
    step = max(CHUNK_MIN_STEP, len(reply) // CHUNK_DIVISOR or CHUNK_MIN_STEP)
    return [reply[i : i + step] for i in range(0, len(reply), step)]


def done_event(result: RunResult) -> dict[str, Any]:
    return {
        "type": "done",
        "reply": result["reply"],
        "used_tools": result["used_tools"],
        "used_agents": result["used_agents"],
        "trace": result["trace"],
        "needs_human": result["needs_human"],
        "lead_id": result["lead_id"],
        "conversation_id": result["conversation_id"],
        "run_id": result.get("run_id"),
        # memory intentionally omitted: the streaming done frame must not carry
        # the customer profile (phone/address/...) to the browser — the batch
        # ChatResponse strips it, and the stream must match that PII boundary.
        "active_skills": result.get("active_skills"),
        "decision": result.get("decision"),
    }


def batched_events(result: RunResult) -> list[dict[str, Any]]:
    """Event sequence for routes that finish before streaming (offline/fast)."""
    events: list[dict[str, Any]] = []
    if result.get("memory_summary"):
        events.append({"type": "memory", "summary": result["memory_summary"]})
    for step in result["trace"]:
        events.append({"type": "trace", **step})
    for piece in chunk_reply(result["reply"]):
        events.append({"type": "token", "content": piece})
    events.append(done_event(result))
    return events
