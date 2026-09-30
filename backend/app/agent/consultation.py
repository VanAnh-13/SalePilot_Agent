"""One-pass consultation result shared by every serving route."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agent.decision import build_decision
from app.agent.recommendation import recommend_top3


@dataclass(frozen=True)
class ConsultationResult:
    """Structured recommendation and its decision evidence for one need."""

    need: dict[str, Any]
    recommendation: dict[str, Any]
    decision: dict[str, Any]


def consult(need: dict[str, Any]) -> ConsultationResult:
    """Rank once, then package decision evidence from that exact result."""
    normalized_need = dict(need)
    recommendation = recommend_top3(normalized_need)
    decision = build_decision(normalized_need, recommendation)
    return ConsultationResult(
        need=normalized_need,
        recommendation=recommendation,
        decision=decision,
    )
