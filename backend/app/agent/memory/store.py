from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy import select

from app.config import get_settings
from app.db.session import async_session
from app.models.entities import CustomerMemory

logger = logging.getLogger(__name__)

DEFAULT_PROFILE: dict[str, Any] = {
    "name": "",
    "phone": "",
    "budget_vnd": None,
    "interests": [],
    "preferred_skus": [],
    "notes": [],
    "last_intent": "",
    # Accumulated need profile (category, budget, slots, priorities) so
    # follow-up turns like "giá khoảng 10tr" keep the earlier context.
    "need": {},
}


async def load_profile(channel: str, external_id: str) -> dict[str, Any]:
    if not get_settings().memory_enabled or not external_id:
        return dict(DEFAULT_PROFILE)
    async with async_session() as session:
        row = (
            await session.execute(
                select(CustomerMemory).where(
                    CustomerMemory.channel == channel,
                    CustomerMemory.external_id == external_id,
                )
            )
        ).scalar_one_or_none()
        if not row:
            return dict(DEFAULT_PROFILE)
        try:
            data = json.loads(row.profile_json or "{}")
        except json.JSONDecodeError:
            data = {}
        out = dict(DEFAULT_PROFILE)
        out.update(data)
        return out


async def get_memory_summary(channel: str, external_id: str) -> str:
    profile = await load_profile(channel, external_id)
    if not any(
        [
            profile.get("name"),
            profile.get("phone"),
            profile.get("interests"),
            profile.get("preferred_skus"),
            profile.get("notes"),
            profile.get("budget_vnd"),
            profile.get("conv_summary"),
        ]
    ):
        return ""
    parts = []
    if profile.get("conv_summary"):
        parts.append(f"tóm_tắt={profile['conv_summary'][:160]}")
    if profile.get("name"):
        parts.append(f"tên={profile['name']}")
    if profile.get("phone"):
        parts.append(f"SĐT={profile['phone']}")
    if profile.get("budget_vnd"):
        parts.append(f"budget≈{int(profile['budget_vnd']):,}".replace(",", ".") + "đ")
    if profile.get("interests"):
        parts.append("quan_tâm=" + ", ".join(profile["interests"][:5]))
    if profile.get("preferred_skus"):
        parts.append("SKU=" + ", ".join(profile["preferred_skus"][:5]))
    if profile.get("last_intent"):
        parts.append(f"intent={profile['last_intent'][:80]}")
    if profile.get("notes"):
        parts.append("ghi_chú=" + "; ".join(profile["notes"][-3:]))
    return " | ".join(parts)


async def load_need(channel: str, external_id: str) -> dict[str, Any]:
    """Accumulated multi-turn need profile for this customer."""
    profile = await load_profile(channel, external_id)
    need = profile.get("need")
    return dict(need) if isinstance(need, dict) else {}


async def save_need(channel: str, external_id: str, need: dict[str, Any]) -> None:
    if not get_settings().memory_enabled or not external_id:
        return
    profile = await load_profile(channel, external_id)
    profile["need"] = {k: v for k, v in need.items() if k != "raw" and v not in (None, "", [])}
    summary = await _summary_from_profile(profile)
    async with async_session() as session:
        row = (
            await session.execute(
                select(CustomerMemory).where(
                    CustomerMemory.channel == channel,
                    CustomerMemory.external_id == external_id,
                )
            )
        ).scalar_one_or_none()
        payload = json.dumps(profile, ensure_ascii=False)
        if row:
            row.profile_json = payload
            row.summary = summary
        else:
            session.add(
                CustomerMemory(
                    channel=channel,
                    external_id=external_id,
                    profile_json=payload,
                    summary=summary,
                )
            )
        await session.commit()


async def merge_profile(
    channel: str,
    external_id: str,
    *,
    name: str = "",
    phone: str = "",
    budget_vnd: int | None = None,
    interest: str = "",
    sku: str = "",
    note: str = "",
    last_intent: str = "",
) -> dict[str, Any]:
    if not get_settings().memory_enabled or not external_id:
        return dict(DEFAULT_PROFILE)

    profile = await load_profile(channel, external_id)
    if name:
        profile["name"] = name
    if phone:
        profile["phone"] = phone
    if budget_vnd is not None and budget_vnd > 0:
        profile["budget_vnd"] = budget_vnd
    if interest:
        interests = list(profile.get("interests") or [])
        if interest not in interests:
            interests.append(interest)
        profile["interests"] = interests[-12:]
    if sku:
        skus = list(profile.get("preferred_skus") or [])
        if sku not in skus:
            skus.append(sku)
        profile["preferred_skus"] = skus[-12:]
    if note:
        notes = list(profile.get("notes") or [])
        # Same-value notes (e.g. repeated "auto-extract" turns) must not
        # duplicate — only append when the last note differs.
        if not notes or notes[-1] != note[:200]:
            notes.append(note[:200])
        profile["notes"] = notes[-20:]
    if last_intent:
        profile["last_intent"] = last_intent[:200]

    summary = await _summary_from_profile(profile)
    await _write_profile(channel, external_id, profile, summary)
    return profile


async def _write_profile(
    channel: str,
    external_id: str,
    profile: dict[str, Any],
    summary: str,
) -> None:
    async with async_session() as session:
        row = (
            await session.execute(
                select(CustomerMemory).where(
                    CustomerMemory.channel == channel,
                    CustomerMemory.external_id == external_id,
                )
            )
        ).scalar_one_or_none()
        payload = json.dumps(profile, ensure_ascii=False)
        if row:
            row.profile_json = payload
            row.summary = summary
        else:
            session.add(
                CustomerMemory(
                    channel=channel,
                    external_id=external_id,
                    profile_json=payload,
                    summary=summary,
                )
            )
        await session.commit()


async def _summary_from_profile(profile: dict[str, Any]) -> str:
    return json.dumps(profile, ensure_ascii=False)[:500]


# Refresh the rolling conversation summary at most every N stored messages.
SUMMARY_THRESHOLD = 6


async def maybe_summarize_conversation(
    channel: str,
    external_id: str,
    history: list[dict[str, str]],
) -> str | None:
    """Keep a rolling LLM summary of the conversation in the customer profile.

    Fires when at least SUMMARY_THRESHOLD messages are stored AND another
    SUMMARY_THRESHOLD have arrived since the last summary. Skipped silently
    when no LLM key or MEMORY_SUMMARY_ENABLED=false — offline behavior is
    unchanged. Returns the current summary, if any.
    """
    if not get_settings().memory_summary_enabled or not external_id:
        return None
    from app.agent.llm import get_chat_model, has_llm_key

    if not has_llm_key():
        return None
    profile = await load_profile(channel, external_id)
    existing = profile.get("conv_summary") or None
    summarized_len = int(profile.get("conv_summary_len") or 0)
    if len(history) < SUMMARY_THRESHOLD:
        return existing
    if len(history) - summarized_len < SUMMARY_THRESHOLD:
        return existing

    from langchain_core.messages import HumanMessage, SystemMessage

    transcript = "\n".join(
        f"{'Khách' if m.get('role') != 'assistant' else 'Bot'}: {str(m.get('content', ''))[:200]}"
        for m in history[-12:]
    )
    try:
        ai = await get_chat_model().ainvoke(
            [
                SystemMessage(
                    content=(
                        "Tóm tắt hội thoại tư vấn điện máy sau thành GIẢN LƯỢC tiếng Việt "
                        "tối đa 60 từ: nhu cầu chính (sản phẩm, ngân sách, ràng buộc), "
                        "những gì đã đề xuất, việc còn lại cần làm. Chỉ xuất tóm tắt."
                    )
                ),
                HumanMessage(content=transcript),
            ]
        )
        summary = (ai.content if isinstance(ai.content, str) else str(ai.content or "")).strip()
        if not summary:
            return existing
    except Exception:
        logger.warning("conversation summary failed", exc_info=True)
        return existing

    profile["conv_summary"] = summary[:400]
    profile["conv_summary_len"] = len(history)
    await _write_profile(channel, external_id, profile, await _summary_from_profile(profile))
    return profile["conv_summary"]


async def maybe_extract_from_text(channel: str, external_id: str, text: str) -> dict[str, Any]:
    """Heuristic memory update from user message (offline-safe)."""
    if not get_settings().memory_enabled or not external_id or not text:
        return await load_profile(channel, external_id)

    phone_m = re.search(r"0\d{8,10}", text.replace(" ", "").replace(".", ""))
    interest = ""
    t = text.lower()
    from app.catalog.registry import detect_category

    category = detect_category(text)
    if category:
        interest = category.display.lower()
    # Reuse the robust budget parser (avoids matching "20m2" as 20 triệu).
    from app.agent.catalog_domain import extract_budget

    budget = extract_budget(text)

    if not phone_m and not interest and budget is None:
        return await load_profile(channel, external_id)

    return await merge_profile(
        channel,
        external_id,
        phone=phone_m.group(0) if phone_m else "",
        budget_vnd=budget,
        interest=interest,
        last_intent=text[:160],
        note="auto-extract" if phone_m or interest else "",
    )


async def list_memories(limit: int = 50) -> list[dict[str, Any]]:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(CustomerMemory).order_by(CustomerMemory.id.desc()).limit(limit)
            )
        ).scalars().all()
    out = []
    for r in rows:
        try:
            profile = json.loads(r.profile_json or "{}")
        except json.JSONDecodeError:
            profile = {}
        out.append(
            {
                "id": r.id,
                "channel": r.channel,
                "external_id": r.external_id,
                "profile": profile,
                "summary": r.summary,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
        )
    return out


async def erase_memory(channel: str, external_id: str) -> bool:
    """Delete one customer's stored memory entirely (right to erasure).

    Returns True when a row was deleted, False when nothing was stored.
    """
    async with async_session() as session:
        row = (
            await session.execute(
                select(CustomerMemory).where(
                    CustomerMemory.channel == channel,
                    CustomerMemory.external_id == external_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        await session.delete(row)
        await session.commit()
        return True
