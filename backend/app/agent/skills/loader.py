"""Load portable SKILL.md packages for the Lead prompt catalog."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class SkillMeta:
    name: str
    description: str
    agents: list[str]
    body: str
    path: str


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta_raw, body = parts[1], parts[2]
    meta: dict[str, str] = {}
    for line in meta_raw.strip().splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip("[]").strip()
    return meta, body.strip()


@lru_cache(maxsize=1)
def list_skills() -> tuple[SkillMeta, ...]:
    skills: list[SkillMeta] = []
    if not SKILLS_DIR.is_dir():
        return tuple()
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        name = meta.get("name") or skill_md.parent.name
        desc = meta.get("description") or ""
        agents_raw = meta.get("agents") or ""
        agents = [a.strip() for a in re.split(r"[,\s]+", agents_raw) if a.strip()]
        skills.append(
            SkillMeta(
                name=name,
                description=desc,
                agents=agents,
                body=body,
                path=str(skill_md.relative_to(SKILLS_DIR.parent)),
            )
        )
    return tuple(skills)


def skills_catalog_prompt(max_chars: int = 1200) -> str:
    """Compact skill index for Lead system prompt (metadata only)."""
    skills = list_skills()
    if not skills:
        return ""
    lines = ["## Available skills (progressive — follow when relevant)"]
    for s in skills:
        agents = ", ".join(s.agents) if s.agents else "lead"
        lines.append(f"- **{s.name}** ({agents}): {s.description}")
    text = "\n".join(lines)
    return text[:max_chars]


def load_skill_body(name: str) -> str | None:
    for s in list_skills():
        if s.name == name:
            return s.body
    return None
