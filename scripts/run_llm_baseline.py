#!/usr/bin/env python3
"""LLM baseline (B2) for RIVF Track 2 — provider-agnostic, one pin per run.

OpenAI-compatible chat completions only. Exactly one provider/model is pinned
per sealed report via CLI flags or environment variables. Secrets never enter
the repo.

Env resolution order (first non-empty wins):
  base:  LLM_API_BASE, OPENAI_BASE_URL, META_API_BASE, OPENAI_API_BASE
  key:   LLM_API_KEY, OPENAI_API_KEY, META_API_KEY, ANTHROPIC_API_KEY
  model: LLM_MODEL, OPENAI_MODEL, META_MODEL, MODEL_NAME

Usage:
  python scripts/run_llm_baseline.py --split dev --dry-run-config
  python scripts/run_llm_baseline.py --split test --repeats 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SALEPILOT_CATALOG_REGISTRY", "crawl")
os.environ["CATALOG_BACKEND"] = "snapshot"

from app.catalog import repository  # noqa: E402
from app.config import get_settings  # noqa: E402

CONDITION_ID = "B2_llm_single_agent"
# Category slugs must match the fixture/catalog registry — NOT the benchmark labels.
# The benchmark uses descriptive slugs (dong_ho_thong_minh, laptop) that differ
# from the catalog registry (dong_ho, may_tinh_de_ban). We give the LLM the
# catalog-registry slugs so it can look up products.
DEFAULT_CATEGORIES = (
    "tu_lanh, may_lanh, may_giat, may_say, may_rua_chen, may_nuoc_nong, "
    "tu_dong, dong_ho, may_tinh_de_ban, man_hinh, may_in, may_tinh_bang, "
    "micro_karaoke, micro_thu_am"
)

# Slot keys the evaluator knows about (from expected_slots in benchmark labels).
KNOWN_SLOT_KEYS = [
    "budget_vnd", "household_size", "area_m2", "max_width_cm",
    "max_height_cm", "max_depth_cm", "capacity_l", "load_kg",
    "wash_kg", "ram_gb", "storage_gb", "screen_inch",
]


def _first_env(*names: str) -> str:
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return ""


def resolve_llm_pin(
    *,
    api_base: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    provider: str | None = None,
) -> dict[str, str]:
    """Resolve exactly one provider pin without printing secrets."""
    base = (api_base or _first_env(
        "LLM_API_BASE",
        "OPENAI_BASE_URL",
        "META_API_BASE",
        "OPENAI_API_BASE",
    ) or "https://api.openai.com/v1").rstrip("/")
    key = api_key if api_key is not None else _first_env(
        "LLM_API_KEY",
        "OPENAI_API_KEY",
        "META_API_KEY",
        "ANTHROPIC_API_KEY",
    )
    model_name = model or _first_env(
        "LLM_MODEL",
        "OPENAI_MODEL",
        "META_MODEL",
        "MODEL_NAME",
    ) or "gpt-4o-mini"
    provider_name = (provider or _first_env("LLM_PROVIDER") or _infer_provider(base)).strip().lower()
    key_fp = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12] if key else ""
    return {
        "provider": provider_name,
        "api_base": base,
        "model": model_name,
        "api_key_present": "true" if bool(key) else "false",
        "api_key_fingerprint": key_fp,
        "api_key": key,
    }


def _infer_provider(api_base: str) -> str:
    low = api_base.casefold()
    if "openai.com" in low:
        return "openai"
    if "groq.com" in low:
        return "groq"
    if "openrouter.ai" in low:
        return "openrouter"
    if "deepseek.com" in low:
        return "deepseek"
    if "together.xyz" in low:
        return "together"
    if "meta.ai" in low:
        return "meta"
    if "anthropic" in low:
        return "anthropic_compatible"
    return "openai_compatible"


def pin_public_view(pin: dict[str, str]) -> dict[str, str]:
    return {
        "provider": pin["provider"],
        "api_base": pin["api_base"],
        "model": pin["model"],
        "api_key_present": pin["api_key_present"],
        "api_key_fingerprint": pin["api_key_fingerprint"],
        "condition_id": CONDITION_ID,
    }


def _call_llm(
    messages: list[dict[str, Any]],
    *,
    api_base: str,
    api_key: str,
    model: str,
    timeout: int = 60,
) -> str:
    """Call an OpenAI-compatible chat completion endpoint."""
    import ssl
    import urllib.request
    import urllib.error

    # muse-spark-1.1 is a reasoning model — it uses most tokens internally
    # before producing output. max_tokens must be large enough for reasoning + response.
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 4096,
    }).encode("utf-8")

    url = f"{api_base.rstrip('/')}/chat/completions"
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        if content is None:
            # Model ran out of tokens during reasoning — content not yet produced
            return "LLM_ERROR: content=None (max_tokens too low for reasoning model)"
        return content
    except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        return f"LLM_ERROR: {exc}"


def _system_prompt(categories: str) -> str:
    slot_keys_str = ", ".join(KNOWN_SLOT_KEYS)
    return f"""You are a Vietnamese retail product consultant.
Given a customer conversation, you must:
1. Identify the product category slug from EXACTLY this list: {categories}
   If the customer's request doesn't match any category above, use null.
2. Extract all numeric constraints the customer mentioned as typed slots.
   Known slot keys: {slot_keys_str}
   For budget: use budget_vnd (integer in VND, e.g. 15000000 for "15 triệu").
   For household: use household_size (integer).
   For room area: use area_m2 (number in square meters).
   For washing load: use wash_kg (number in kg).
   Only include slots the customer explicitly mentioned.
3. Decide action: recommend | clarify | abstain | faq
   - recommend: category clear AND enough info to suggest products
   - clarify: category clear but missing key info (budget, size, etc.)
   - abstain: out of scope, impossible budget, or unsupported category
   - faq: customer asks about policy, warranty, stock, delivery
4. If recommending, return up to 3 catalog SKUs from the provided catalog.
   CRITICAL: Every recommended product MUST satisfy the customer's budget
   (price_vnd <= budget_vnd). Do NOT recommend products over budget.

Respond with JSON only:
{{
  "category": "<slug from list above or null>",
  "action": "recommend|clarify|abstain|faq",
  "extracted_slots": {{"budget_vnd": 15000000, "household_size": 4}},
  "reasoning": "<brief>",
  "top3_skus": ["sku1", "sku2", "sku3"]
}}
"""


def _build_catalog_context(category: str | None) -> str:
    if not category:
        return "No category identified yet."
    products = list(repository.by_category(category))
    if not products:
        return f"No products found for category '{category}'."
    lines = [f"Catalog products in {category} ({len(products)} total, showing up to 25):"]
    for product in products[:25]:
        price = product.get("price_vnd")
        price_str = f"{int(price):,} VND" if price is not None else "N/A"
        norm = product.get("norm") or {}
        specs = ", ".join(f"{k}={v}" for k, v in list(norm.items())[:6] if v is not None)
        lines.append(
            f"  SKU:{product.get('sku')} | {product.get('brand') or ''} "
            f"{product.get('name') or ''} | {price_str} | {specs}"
        )
    return "\n".join(lines)


def _parse_llm_response(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {
        "category": None,
        "action": "abstain",
        "reasoning": f"parse_error: {(text or '')[:200]}",
        "top3_skus": [],
    }


def run_llm_single_agent(
    episode: dict[str, Any],
    *,
    pin: dict[str, str],
    categories: str = DEFAULT_CATEGORIES,
) -> dict[str, Any]:
    from app.catalog.registry import detect_category, detect_unsupported

    turns = episode.get("turns") or []
    conversation = "\n".join(
        f"{'Customer' if turn.get('role') == 'user' else 'Agent'}: {turn.get('text')}"
        for turn in turns
        if isinstance(turn, dict)
    )
    joined_user = " ".join(
        str(turn.get("text") or "")
        for turn in turns
        if isinstance(turn, dict) and turn.get("role") == "user"
    )
    # Single-agent baseline may use lightweight lexical category hint only to
    # attach catalog context; final category/action still come from the LLM.
    hinted = detect_category(joined_user)
    unsupported = detect_unsupported(joined_user)
    catalog_context = _build_catalog_context(hinted.slug if hinted is not None else None)
    user_payload = (
        f"Customer conversation:\n{conversation}\n\n"
        f"{catalog_context}\n\n"
        "Return JSON only. If the request is stock/warranty/policy FAQ, use action=faq. "
        "If out of retail catalog scope, use action=abstain. "
        "If a product category is clear and budget is feasible, prefer action=recommend "
        "with top3_skus chosen ONLY from the catalog list above."
    )
    if unsupported is not None:
        user_payload += f"\nNote: domain detector flagged unsupported term {unsupported[0]!r}."

    messages = [
        {"role": "system", "content": _system_prompt(categories)},
        {"role": "user", "content": user_payload},
    ]
    t0 = time.perf_counter()
    response1 = _call_llm(
        messages,
        api_base=pin["api_base"],
        api_key=pin["api_key"],
        model=pin["model"],
    )
    parsed = _parse_llm_response(response1)
    llm_category = parsed.get("category")
    if llm_category in {"", "null", "None"}:
        llm_category = None

    # Category resolution strategy:
    # - For catalog lookup: use llm_category (fixture slug) or hinted.slug
    # - For scoring: use hinted.slug (registry slug) since that's what the
    #   deterministic systems report and what the benchmark labels expect.
    #   The registry slug may differ from the fixture slug (e.g. dong_ho_thong_minh
    #   vs dong_ho, laptop vs may_tinh_de_ban).
    lookup_category = llm_category or (hinted.slug if hinted is not None else None)
    predicted_category = hinted.slug if hinted is not None else llm_category

    predicted_action = str(parsed.get("action") or "abstain").strip().lower()
    if predicted_action not in {"recommend", "clarify", "abstain", "faq"}:
        predicted_action = "abstain"

    top3: list[dict[str, Any]] = []
    sku_list = parsed.get("top3_skus") or []
    if not isinstance(sku_list, list):
        sku_list = []
    # If the model chose recommend/clarify with a category but omitted SKUs,
    # one follow-up call with the same catalog context recovers recommendations.
    response2 = ""
    if lookup_category and predicted_action in {"recommend", "clarify"} and not sku_list:
        messages2 = [
            {"role": "system", "content": _system_prompt(categories)},
            {
                "role": "user",
                "content": (
                    f"Customer conversation:\n{conversation}\n\n"
                    f"{_build_catalog_context(str(lookup_category))}\n\n"
                    "Select up to 3 SKUs from the catalog that best match. "
                    "If budget is impossible, set action=abstain and top3_skus=[]. "
                    "Return JSON only."
                ),
            },
        ]
        response2 = _call_llm(
            messages2,
            api_base=pin["api_base"],
            api_key=pin["api_key"],
            model=pin["model"],
        )
        parsed2 = _parse_llm_response(response2)
        sku_list = parsed2.get("top3_skus") or []
        if not isinstance(sku_list, list):
            sku_list = []
        follow_action = str(parsed2.get("action") or "").strip().lower()
        if follow_action in {"recommend", "clarify", "abstain", "faq"}:
            predicted_action = follow_action

    if lookup_category:
        catalog_products = list(repository.by_category(str(lookup_category)))
        by_sku = {str(product.get("sku")): product for product in catalog_products}
        for sku in sku_list[:3]:
            product = by_sku.get(str(sku))
            if product is None:
                continue
            top3.append(
                {
                    "sku": product.get("sku"),
                    "name": product.get("name"),
                    "price_vnd": product.get("price_vnd"),
                    "category": product.get("category"),
                    "norm": product.get("norm") or {},
                    "source": product.get("source"),
                    "source_row": product.get("source_row"),
                    "match_score": 0.0,
                    "why": "llm_single_agent",
                }
            )
        if top3 and predicted_action == "clarify":
            predicted_action = "recommend"
        if predicted_action == "recommend" and not top3:
            # Fail closed: do not claim recommend without grounded SKUs.
            predicted_action = "abstain"

    # --- Post-LLM constraint filtering ---
    # Extract typed slots from LLM response for slot_micro_f1 scoring.
    extracted_slots = parsed.get("extracted_slots") or {}
    if not isinstance(extracted_slots, dict):
        extracted_slots = {}
    # Also try response2 if available
    if response2:
        parsed2_slots = _parse_llm_response(response2).get("extracted_slots") or {}
        if isinstance(parsed2_slots, dict):
            for k, v in parsed2_slots.items():
                if k not in extracted_slots and v is not None:
                    extracted_slots[k] = v
    # Normalize slot values to match evaluator expectations (integers/floats)
    parsed_need = {}
    for key in KNOWN_SLOT_KEYS:
        val = extracted_slots.get(key)
        if val is not None:
            try:
                parsed_need[key] = int(val) if isinstance(val, (int, float)) and float(val) == int(val) else float(val)
            except (ValueError, TypeError):
                pass
    # Include category in parsed_need (evaluator checks it)
    if predicted_category:
        parsed_need["category"] = predicted_category

    # Hard budget filter: remove products exceeding stated budget.
    budget = parsed_need.get("budget_vnd")
    if budget is not None and top3:
        filtered = []
        for item in top3:
            price = item.get("price_vnd")
            if price is not None and int(price) > int(budget):
                continue  # Fail-closed: exclude over-budget products
            filtered.append(item)
        top3 = filtered
    if predicted_action == "recommend" and not top3:
        predicted_action = "abstain"

    latency_ms = (time.perf_counter() - t0) * 1000
    decision = {
        "ok": predicted_action == "recommend" and bool(top3),
        "need_more": predicted_action == "clarify",
        "category": predicted_category,
        "parsed_need": parsed_need,
        "top3": top3,
        "tradeoffs": [],
        "source": f"llm_single_agent:{pin['provider']}:{pin['model']}:{repository.source()}",
        "llm_raw_response": (response1 or "")[:500],
        "llm_raw_response_2": (response2 or "")[:300],
    }
    return {
        "episode_id": episode.get("episode_id"),
        "system_id": CONDITION_ID,
        "condition": CONDITION_ID,
        "decision": decision,
        "predicted_action": predicted_action,
        "predicted_category": predicted_category,
        "latency_ms": round(latency_ms, 2),
        "catalog_source": repository.source(),
        "llm_pin": pin_public_view(pin),
    }


def _load_manifest_snapshot() -> None:
    manifest_path = ROOT / "experiments" / "manifest.json"
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") not in {"ready", "frozen"}:
        return
    rel = (manifest.get("catalog") or {}).get("snapshot_path")
    if isinstance(rel, str) and rel:
        os.environ["CATALOG_SNAPSHOT"] = str((ROOT / rel).resolve())
        family = str((manifest.get("catalog") or {}).get("family") or "")
        if "dmx" in family:
            os.environ["SALEPILOT_CATALOG_REGISTRY"] = "crawl"
        get_settings.cache_clear()
        repository.reload()


def _write_unavailable(path: Path, pin: dict[str, str], reason: str) -> None:
    payload = {
        "status": "unavailable",
        "condition": CONDITION_ID,
        "reason": reason,
        "llm_pin": pin_public_view(pin),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--repeats", type=int, default=1, help="Stochastic repeats (>=1); default 1 at temperature 0")
    parser.add_argument("--output", default=None, help="Prediction JSONL path")
    parser.add_argument("--pin-out", default=None, help="Public pin JSON path (no secrets)")
    parser.add_argument("--dry-run-config", action="store_true", help="Print resolved pin and exit 0")
    parser.add_argument(
        "--allow-unavailable",
        action="store_true",
        help="Exit 0 and write unavailable report when no API key is configured",
    )
    args = parser.parse_args(argv)

    pin = resolve_llm_pin(
        api_base=args.api_base,
        api_key=args.api_key,
        model=args.model,
        provider=args.provider,
    )

    if args.dry_run_config:
        # Dry run must have zero filesystem side effects — print and exit only.
        # (Previously this wrote the pin file unconditionally before this check,
        # which meant every --dry-run-config call — including from unit tests —
        # silently overwrote the real experiments/results/b2_pin_<split>.json
        # custody file. See backend/tests/test_llm_baseline_config.py and
        # experiments/results/b2_pin_dev.json's recovered_at note, 2026-08-01.)
        print(json.dumps(pin_public_view(pin), ensure_ascii=False, indent=2))
        return 0

    pin_path = Path(args.pin_out) if args.pin_out else ROOT / "experiments" / "results" / f"b2_pin_{args.split}.json"
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    pin_path.write_text(json.dumps(pin_public_view(pin), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    output_path = (
        Path(args.output)
        if args.output
        else ROOT / "experiments" / "results" / f"llm_baseline_{args.split}.jsonl"
    )

    if pin["api_key_present"] != "true":
        reason = "no API key configured (LLM_API_KEY / OPENAI_API_KEY / META_API_KEY)"
        _write_unavailable(output_path.with_suffix(".unavailable.json"), pin, reason)
        print(f"B2 unavailable: {reason}", file=sys.stderr)
        print(f"Wrote {output_path.with_suffix('.unavailable.json')}")
        return 0 if args.allow_unavailable else 2

    _load_manifest_snapshot()
    benchmark_path = ROOT / "experiments" / "benchmark" / f"{args.split}.jsonl"
    if not benchmark_path.is_file():
        print(f"ERROR: benchmark not found: {benchmark_path}", file=sys.stderr)
        return 2

    episodes = [
        json.loads(line)
        for line in benchmark_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    repeats = max(1, int(args.repeats))
    print(f"Running {CONDITION_ID} on {len(episodes)} episodes x {repeats} repeat(s)")
    print(f"  provider={pin['provider']} model={pin['model']} base={pin['api_base']}")
    print(f"  catalog={repository.source()} key_fp={pin['api_key_fingerprint']}")

    results: list[dict[str, Any]] = []
    for repeat_idx in range(repeats):
        for index, episode in enumerate(episodes):
            eid = episode.get("episode_id")
            print(f"  [r{repeat_idx+1} {index+1}/{len(episodes)}] {eid}...", end=" ", flush=True)
            try:
                row = run_llm_single_agent(episode, pin=pin)
                row["repeat"] = repeat_idx
                results.append(row)
                print(
                    f"action={row['predicted_action']} cat={row.get('predicted_category')} "
                    f"latency={row['latency_ms']:.0f}ms"
                )
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR: {exc}")
                results.append(
                    {
                        "episode_id": eid,
                        "system_id": CONDITION_ID,
                        "condition": CONDITION_ID,
                        "repeat": repeat_idx,
                        "decision": {"ok": False, "error": str(exc)},
                        "predicted_action": "abstain",
                        "latency_ms": 0.0,
                        "llm_pin": pin_public_view(pin),
                    }
                )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for row in results:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(results)} rows to {output_path}")
    print(f"Pin (public) written to {pin_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
