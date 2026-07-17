"""Optional auto-draft of a new SKILL.md after complex successful runs."""

from __future__ import annotations

import re
from pathlib import Path

from app.config import get_settings

SKILLS_DIR = Path(__file__).resolve().parent


def maybe_write_skill_from_run(
    *,
    user_text: str,
    agents: list[str],
    reply: str,
) -> str | None:
    settings = get_settings()
    if not settings.auto_skill_write:
        return None
    specialists = [a for a in agents if a != "lead"]
    if len(specialists) < 2:
        return None

    slug = re.sub(r"[^a-z0-9]+", "_", user_text.lower())[:40].strip("_") or "auto"
    name = f"auto_{slug}"
    dest = SKILLS_DIR / name
    if dest.exists():
        return None
    dest.mkdir(parents=True, exist_ok=True)
    body = f"""---
name: {name}
description: Auto-drafted from multi-agent run involving {", ".join(specialists)}.
agents: [lead, {", ".join(specialists[:3])}]
---

# {name}

## Trigger
User intent similar to: {user_text[:200]}

## Approach
1. Lead routes to: {", ".join(specialists)}
2. Synthesize Vietnamese reply with CTA.

## Sample outcome
{reply[:400]}
"""
    (dest / "SKILL.md").write_text(body, encoding="utf-8")
    # bust loader cache
    from app.agent.skills.loader import list_skills

    list_skills.cache_clear()
    return name
