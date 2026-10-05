"""Auto-activate skills whose metadata matches the user message.

Pure lexical matching over each skill's own frontmatter name + description —
there is no per-skill hardcoded keyword list, so editing a SKILL.md
description immediately updates matching. Diacritics are folded on both
sides so "tu van" matches "tư vấn".
"""

from __future__ import annotations

import re
import unicodedata

from app.agent.skills.loader import list_skills

# Vietnamese function words that would otherwise match almost any description.
_STOPWORDS = frozenset(
    {
        "cho", "của", "cũng", "có", "khi", "không", "nhưng", "người",
        "theo", "thật", "thông", "từng", "và", "với", "cách", "dữ", "liệu",
    }
)

_MIN_TOKEN = 3
_LONG_TOKEN = 6  # a single long unigram match (e.g. "khiếu") is meaningful alone
_MIN_MATCHES = 2
MAX_AUTO_SKILLS = 2


def _fold(text: str) -> str:
    """Lowercase + strip Vietnamese diacritics (NFD, drop combining marks)."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _tokens(text: str) -> tuple[set[str], set[str]]:
    """(unigrams, adjacent bigrams) after folding — Vietnamese is syllabic, so
    bigrams like "so_sanh"/"gap_nguoi" carry far more signal than syllables.
    Bigrams keep 2-char function syllables ("so" of "so sánh"); unigrams
    require the longer _MIN_TOKEN so noise words don't score alone."""
    all_words = [w for w in re.findall(r"[a-z0-9]+", _fold(text)) if w not in _STOPWORDS]
    unigrams = {w for w in all_words if len(w) >= _MIN_TOKEN}
    bigrams = {f"{a}_{b}" for a, b in zip(all_words, all_words[1:]) if len(a) >= 2 and len(b) >= 2}
    return unigrams, bigrams


def _score(text_uni: set[str], text_bi: set[str], skill_text: str) -> int:
    uni, bi = _tokens(skill_text)
    uni_hits = uni & text_uni
    bi_hits = bi & text_bi
    strong = sum(1 for m in uni_hits if len(m) >= _LONG_TOKEN)
    if len(uni_hits) + len(bi_hits) < _MIN_MATCHES and not bi_hits and not strong:
        return 0
    return len(uni_hits) + strong + 2 * len(bi_hits)


def match_skills(user_text: str, *, max_skills: int = MAX_AUTO_SKILLS) -> list[str]:
    """Skill names whose metadata lexically matches the message, best first."""
    text_uni, text_bi = _tokens(user_text or "")
    if not text_uni and not text_bi:
        return []
    scored: list[tuple[int, str]] = []
    for skill in list_skills():
        points = _score(text_uni, text_bi, f"{skill.name} {skill.description}")
        if points > 0:
            scored.append((points, skill.name))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [name for _, name in scored[:max_skills]]


__all__ = ["match_skills", "MAX_AUTO_SKILLS"]
