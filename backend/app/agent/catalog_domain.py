"""Deep catalog domain for AC — pure functions, no LangChain."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "products.json"


@lru_cache(maxsize=1)
def load_products() -> tuple[dict[str, Any], ...]:
    if not DATA.exists():
        return tuple()
    return tuple(json.loads(DATA.read_text(encoding="utf-8")))


def reload_products() -> None:
    load_products.cache_clear()


def _fmt_price(v: int) -> str:
    return f"{int(v):,}".replace(",", ".") + "đ"


def product_public(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "sku": p.get("sku"),
        "name": p.get("name"),
        "brand": p.get("brand"),
        "category": p.get("category"),
        "price_vnd": p.get("price_vnd"),
        "price_display": _fmt_price(int(p.get("price_vnd") or 0)),
        "stock": p.get("stock"),
        "btu": p.get("btu"),
        "hp": p.get("hp"),
        "inverter": p.get("inverter"),
        "room_m2_min": p.get("room_m2_min"),
        "room_m2_max": p.get("room_m2_max"),
        "power_label": p.get("power_label"),
        "noise_db": p.get("noise_db"),
        "promo": p.get("promo"),
        "tags": p.get("tags") or [],
        "pros": p.get("pros") or [],
        "cons": p.get("cons") or [],
        "description": p.get("description") or "",
        "in_stock": int(p.get("stock") or 0) > 0,
        "source": f"catalog:{p.get('sku')}",
    }


def get_by_sku(sku: str) -> dict[str, Any] | None:
    sku_u = sku.upper().strip()
    for p in load_products():
        if str(p.get("sku", "")).upper() == sku_u:
            return product_public(p)
    return None


def search(
    query: str = "",
    *,
    budget_vnd: int | None = None,
    room_m2: float | None = None,
    inverter: bool | None = None,
    brand: str = "",
    limit: int = 8,
) -> list[dict[str, Any]]:
    q = (query or "").lower().strip()
    brand_l = brand.lower().strip()
    scored: list[tuple[float, dict]] = []
    for p in load_products():
        if p.get("category") and p.get("category") != "may_lanh" and "may_lanh" not in str(p.get("category")):
            # allow only AC catalog for this pivot
            if p.get("category") not in ("may_lanh",):
                continue
        text = " ".join(
            str(p.get(k, ""))
            for k in ("name", "brand", "description", "sku", "tags", "promo")
        ).lower()
        score = 0.0
        if q:
            for tok in re.split(r"\s+", q):
                if len(tok) > 1 and tok in text:
                    score += 1.0
            if q in text:
                score += 2.0
        else:
            score = 1.0
        if brand_l and brand_l not in str(p.get("brand", "")).lower():
            continue
        if inverter is True and not p.get("inverter"):
            continue
        if inverter is False and p.get("inverter"):
            continue
        price = int(p.get("price_vnd") or 0)
        if budget_vnd and price > budget_vnd * 1.05:
            continue
        if room_m2 is not None:
            rmin = float(p.get("room_m2_min") or 0)
            rmax = float(p.get("room_m2_max") or 999)
            # soft band ±20%
            if room_m2 < rmin * 0.85 or room_m2 > rmax * 1.2:
                score -= 2.0
            elif rmin <= room_m2 <= rmax:
                score += 3.0
            else:
                score += 1.0
        if int(p.get("stock") or 0) <= 0:
            score -= 1.0
        if score > 0 or not q:
            scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], int(x[1].get("price_vnd") or 0)))
    return [product_public(p) for _, p in scored[: max(1, min(limit, 15))]]


def compare(skus: list[str]) -> dict[str, Any]:
    items = []
    for s in skus[:5]:
        p = get_by_sku(s)
        if p:
            items.append(p)
    if len(items) < 2:
        return {"ok": False, "error": "Cần ≥2 SKU hợp lệ", "items": items, "source": "catalog"}

    tradeoffs = []
    by_price = sorted(items, key=lambda x: int(x["price_vnd"]))
    by_noise = sorted(items, key=lambda x: int(x.get("noise_db") or 99))
    by_btu = sorted(items, key=lambda x: int(x.get("btu") or 0), reverse=True)
    tradeoffs.append(f"Rẻ nhất: {by_price[0]['name']} ({by_price[0]['price_display']}).")
    tradeoffs.append(f"Êm nhất (dB thấp): {by_noise[0]['name']} (~{by_noise[0].get('noise_db')} dB).")
    tradeoffs.append(f"Công suất BTU cao nhất: {by_btu[0]['name']} ({by_btu[0].get('btu')} BTU).")
    inv = [i for i in items if i.get("inverter")]
    if inv and len(inv) < len(items):
        tradeoffs.append("Máy inverter tiết kiệm điện hơn non-inverter khi chạy nhiều giờ/ngày.")

    return {
        "ok": True,
        "items": items,
        "tradeoffs": tradeoffs,
        "plain_summary": " | ".join(tradeoffs),
        "source": "catalog:compare",
    }


def _score_need(p: dict[str, Any], need: dict[str, Any]) -> float:
    score = 0.0
    room = need.get("room_m2")
    budget = need.get("budget_vnd")
    priorities = need.get("priority") or need.get("priorities") or []
    if isinstance(priorities, str):
        priorities = [priorities]

    if room is not None:
        rmin = float(p.get("room_m2_min") or 0)
        rmax = float(p.get("room_m2_max") or 999)
        if rmin <= float(room) <= rmax:
            score += 5.0
        elif rmin * 0.85 <= float(room) <= rmax * 1.2:
            score += 2.0
        else:
            score -= 3.0

    price = int(p.get("price_vnd") or 0)
    if budget:
        b = int(budget)
        if price <= b:
            score += 3.0
            score += max(0, 2.0 - (b - price) / max(b, 1) * 2)  # prefer closer to budget
        else:
            score -= 4.0

    tags = set(p.get("tags") or [])
    for pr in priorities:
        pr_l = str(pr).lower()
        if pr_l in tags or any(pr_l in t for t in tags):
            score += 2.0
        if "tiết kiệm" in pr_l or "tiet_kiem" in pr_l or pr_l == "tiet_kiem_dien":
            if p.get("inverter"):
                score += 2.0
        if pr_l in ("em", "êm", "quiet"):
            noise = int(p.get("noise_db") or 30)
            score += max(0, (30 - noise) / 5)
        if pr_l in ("gia_re", "rẻ", "re"):
            score += max(0, 3.0 - price / 5_000_000)
        if "cong_suat" in pr_l or "mạnh" in pr_l:
            score += int(p.get("btu") or 0) / 10000

    if int(p.get("stock") or 0) > 0:
        score += 0.5
    else:
        score -= 2.0
    return score


def recommend_top3(need: dict[str, Any]) -> dict[str, Any]:
    """Rank AC products for a need profile. LLM must not invent SKUs beyond this list."""
    missing = []
    if not need.get("room_m2") and need.get("room_m2") != 0:
        missing.append("room_m2")
    if not need.get("budget_vnd") and need.get("budget_flexible") is not True:
        missing.append("budget_vnd")

    if missing and not need.get("force"):
        return {
            "ok": False,
            "need_more": True,
            "missing_slots": missing,
            "ask": _clarify_questions(missing),
            "source": "recommend_rules",
        }

    scored = []
    for p in load_products():
        if p.get("category") not in ("may_lanh", None) and p.get("category") != "may_lanh":
            if "may_lanh" not in str(p.get("category", "")):
                # skip non-AC if mixed
                if not str(p.get("sku", "")).startswith("AC-"):
                    continue
        s = _score_need(p, need)
        scored.append((s, p))
    scored.sort(key=lambda x: -x[0])

    # diversify brands in top 3
    top: list[dict] = []
    brands: set[str] = set()
    for s, p in scored:
        if s < -1:
            continue
        b = str(p.get("brand") or "")
        if b in brands and len(top) < 2:
            continue
        pub = product_public(p)
        pub["match_score"] = round(s, 2)
        pub["why"] = _why(p, need)
        top.append(pub)
        brands.add(b)
        if len(top) >= 3:
            break
    if len(top) < 3:
        for s, p in scored:
            if product_public(p)["sku"] in {t["sku"] for t in top}:
                continue
            pub = product_public(p)
            pub["match_score"] = round(s, 2)
            pub["why"] = _why(p, need)
            top.append(pub)
            if len(top) >= 3:
                break

    tradeoffs = []
    if len(top) >= 2:
        c = compare([t["sku"] for t in top])
        tradeoffs = c.get("tradeoffs") or []

    return {
        "ok": True,
        "need_more": False,
        "need": need,
        "top3": top,
        "tradeoffs": tradeoffs,
        "source": "catalog:recommend_top3",
        "disclaimer": "Giá/tồn theo catalog demo; đối chiếu tại quầy trước khi chốt.",
    }


def _clarify_questions(missing: list[str]) -> list[str]:
    qmap = {
        "room_m2": "Phòng khoảng bao nhiêu mét vuông ạ (vd 12, 20, 30)?",
        "budget_vnd": "Ngân sách khoảng bao nhiêu ạ (vd dưới 10 triệu, 12–15 triệu)?",
        "priority": "Mình ưu tiên tiết kiệm điện, máy êm, giá rẻ hay làm lạnh mạnh ạ?",
    }
    return [qmap[m] for m in missing if m in qmap]


def _why(p: dict[str, Any], need: dict[str, Any]) -> str:
    bits = []
    room = need.get("room_m2")
    if room is not None:
        bits.append(f"phù hợp ~{p.get('room_m2_min')}–{p.get('room_m2_max')}m²")
    if p.get("inverter"):
        bits.append("inverter tiết kiệm điện")
    if p.get("noise_db") and int(p["noise_db"]) <= 21:
        bits.append(f"êm ~{p['noise_db']}dB")
    budget = need.get("budget_vnd")
    if budget and int(p.get("price_vnd") or 0) <= int(budget):
        bits.append("trong ngân sách")
    if p.get("promo"):
        bits.append(str(p["promo"])[:40])
    return "; ".join(bits) if bits else (p.get("description") or "")[:80]


def extract_need_from_text(text: str) -> dict[str, Any]:
    """Heuristic need extraction for offline / pre-LLM."""
    t = (text or "").lower()
    need: dict[str, Any] = {"priority": []}

    m = re.search(r"(\d+)\s*m2|(\d+)\s*m²|(\d+)\s*mét", t)
    if m:
        need["room_m2"] = float(m.group(1) or m.group(2) or m.group(3))
    m2 = re.search(r"phòng\s*(\d+)", t)
    if "room_m2" not in need and m2:
        need["room_m2"] = float(m2.group(1))

    # budget
    if re.search(r"dưới\s*(\d+)\s*tr", t):
        need["budget_vnd"] = int(re.search(r"dưới\s*(\d+)\s*tr", t).group(1)) * 1_000_000
    elif re.search(r"(\d+)\s*-\s*(\d+)\s*tr", t):
        mm = re.search(r"(\d+)\s*-\s*(\d+)\s*tr", t)
        need["budget_vnd"] = int(mm.group(2)) * 1_000_000
    elif re.search(r"(\d+)\s*triệu|(\d+)\s*tr\b", t):
        mm = re.search(r"(\d+)\s*triệu|(\d+)\s*tr\b", t)
        need["budget_vnd"] = int(mm.group(1) or mm.group(2)) * 1_000_000
    if "rẻ" in t or "tiết kiệm chi phí" in t or "ngân sách thấp" in t:
        need.setdefault("budget_vnd", 8_000_000)
        need["priority"].append("gia_re")

    if any(k in t for k in ("êm", "em ", "không ồn", "phòng ngủ")):
        need["priority"].append("em")
    if any(k in t for k in ("tiết kiệm điện", "tiet kiem dien", "ít điện", "inverter")):
        need["priority"].append("tiet_kiem_dien")
    if any(k in t for k in ("mạnh", "nhanh lạnh", "phòng khách", "lớn")):
        need["priority"].append("cong_suat_lon")
    if "lọc" in t or "không khí" in t:
        need["priority"].append("loc_khi")
    if "rẻ" in t or "giá rẻ" in t:
        need["priority"].append("gia_re")

    need["priority"] = list(dict.fromkeys(need["priority"]))
    need["raw"] = text[:200]
    return need
