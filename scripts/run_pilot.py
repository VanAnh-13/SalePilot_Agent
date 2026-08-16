#!/usr/bin/env python3
"""Run deterministic pilot conditions over benchmark dev episodes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

# Pilot always uses the snapshot backend. Registry defaults to crawl (DMX
# canonical); conditions.json or env may override before imports below run.
os.environ.setdefault("SALEPILOT_CATALOG_REGISTRY", "crawl")
os.environ["CATALOG_BACKEND"] = "snapshot"

from app.agent.catalog_domain import (  # noqa: E402
    extract_need_from_text,
    merge_needs,
    pending_slots,
    product_public,
    recommend_top3,
)
from app.agent.decision import build_decision  # noqa: E402
from app.catalog import repository  # noqa: E402
from app.catalog.registry import detect_unsupported, get_category  # noqa: E402
from app.config import get_settings  # noqa: E402


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _backend_path(relative_or_absolute: str) -> Path:
    path = Path(relative_or_absolute)
    if path.is_absolute():
        return path
    return ROOT / "backend" / path


def _load_catalog_pin(
    *,
    config: dict,
    manifest_path: Path,
    explicit_hash: str | None,
) -> tuple[str, Path, str]:
    """Resolve and verify a reproducible snapshot pin before scoring."""
    manifest = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_catalog = manifest.get("catalog") or {}
    config_catalog = config.get("catalog") or {}
    pin_source = (
        "cli"
        if explicit_hash
        else "manifest"
        if manifest.get("status") in {"ready", "frozen"}
        else "conditions"
    )

    expected = explicit_hash or (
        manifest_catalog.get("normalized_catalog_hash")
        if manifest.get("status") in {"ready", "frozen"}
        else None
    ) or config_catalog.get("sha256") or config.get("catalog_sha256")
    if not isinstance(expected, str) or len(expected.removeprefix("sha256:")) != 64:
        raise SystemExit("pilot requires a pinned catalog snapshot sha256")
    expected = expected.lower().removeprefix("sha256:")
    if any(ch not in "0123456789abcdef" for ch in expected):
        raise SystemExit("pilot catalog hash must be 64 hexadecimal characters")

    settings = get_settings()
    snapshot_path = _backend_path(settings.catalog_snapshot).resolve()
    if not snapshot_path.is_file():
        raise SystemExit(f"pilot snapshot missing: {snapshot_path}")
    actual = _sha256_file(snapshot_path)
    if actual != expected:
        raise SystemExit(f"pilot catalog hash mismatch: expected {expected}, got {actual}")

    pinned_path = config_catalog.get("path")
    if isinstance(pinned_path, str) and pin_source == "conditions":
        fixture_path = (ROOT / pinned_path).resolve()
        if not fixture_path.is_file():
            raise SystemExit(f"pilot pinned catalog file missing: {fixture_path}")
        fixture_hash = _sha256_file(fixture_path)
        if fixture_hash != expected:
            raise SystemExit(
                f"pilot pinned catalog file hash mismatch: expected {expected}, got {fixture_hash}"
            )

    return expected, snapshot_path, pin_source


def _predict_action(decision: dict, text: str) -> str:
    low = text.casefold()
    if detect_unsupported(text):
        return "abstain"
    if any(k in low for k in ("còn hàng", "tồn kho", "bảo hành", "giao hàng")):
        return "faq"
    if decision.get("need_more"):
        return "clarify"
    if decision.get("ok") and decision.get("top3"):
        return "recommend"
    return "abstain"


def run_hybrid(episode: dict) -> dict:
    need: dict = {}
    final_text = ""
    for turn in episode.get("turns") or []:
        if turn.get("role") != "user":
            continue
        final_text = turn.get("text") or ""
        fresh = extract_need_from_text(final_text)
        need = merge_needs(need, fresh)
    t0 = time.perf_counter()
    rec = recommend_top3(need)
    decision = build_decision(need, rec)
    latency_ms = (time.perf_counter() - t0) * 1000
    return {
        "episode_id": episode["episode_id"],
        "system_id": "S_hybrid_constraint",
        "condition": "S_hybrid_constraint",
        "decision": decision,
        "predicted_action": _predict_action(decision, final_text),
        "latency_ms": round(latency_ms, 2),
        "catalog_source": repository.source(),
    }


def run_price_popularity(episode: dict) -> dict:
    need: dict = {}
    final_text = ""
    for turn in episode.get("turns") or []:
        if turn.get("role") != "user":
            continue
        final_text = turn.get("text") or ""
        need = merge_needs(need, extract_need_from_text(final_text))
    cat = need.get("category")
    products = [p for p in repository.by_category(cat or "")] if cat else []
    priced = [p for p in products if p.get("price_vnd") is not None]
    budget = need.get("budget_vnd")
    if budget is not None:
        priced = [p for p in priced if int(p["price_vnd"]) <= int(budget)]
    priced.sort(key=lambda p: (-int(p.get("sold") or 0), int(p.get("price_vnd") or 10**15)))
    top = priced[:3]
    fake_rec = {
        "ok": bool(top),
        "need_more": not bool(cat and budget),
        "missing_slots": ([] if cat and budget else ["category" if not cat else "budget_vnd"]),
        "ask": [] if cat and budget else ["Ngân sách / ngành?"],
        "category": cat,
        "top3": [
            {
                **{k: p.get(k) for k in ("sku", "name", "price_vnd", "category", "category_code", "source", "source_row", "sold", "rating")},
                **dict(p.get("norm") or {}),
                "match_score": float(p.get("sold") or 0),
                "why": "baseline price/popularity",
            }
            for p in top
        ],
        "tradeoffs": [],
        "disclaimer": "baseline",
        "source": f"baseline:price_popularity:{repository.source()}",
    }
    decision = build_decision(need, fake_rec)
    return {
        "episode_id": episode["episode_id"],
        "system_id": "B0_price_popularity",
        "condition": "B0_price_popularity",
        "decision": decision,
        "predicted_action": _predict_action(decision, final_text),
        "latency_ms": 0.0,
        "catalog_source": repository.source(),
    }


def run_lexical(episode: dict) -> dict:
    """Independent lexical/filter baseline; never calls the proposed ranker."""
    need: dict = {}
    final_text = ""
    for turn in episode.get("turns") or []:
        if turn.get("role") != "user":
            continue
        final_text = turn.get("text") or ""
        need = merge_needs(need, extract_need_from_text(final_text))
    need = {k: v for k, v in need.items() if k not in {"priority", "priorities"}}
    cat = get_category(need.get("category"))
    missing = (["category"] if cat is None else pending_slots(need))

    tokens = {
        token
        for token in re.findall(r"\w+", final_text.casefold(), flags=re.UNICODE)
        if len(token) >= 3
        and token not in {"cần", "can", "mua", "dưới", "duoi", "triệu", "trieu", "khoảng", "tam"}
    }

    def fits(product: dict) -> bool:
        public = product_public(product)
        budget = need.get("budget_vnd")
        if budget is not None and (
            public.get("price_vnd") is None or int(public["price_vnd"]) > int(budget)
        ):
            return False
        if cat is None:
            return False
        for slot in cat.slots:
            expected = need.get(slot.key)
            if expected is None:
                continue
            hard = getattr(slot, "hardness", "soft") == "hard"
            if slot.kind == "range_fit":
                low = public.get(f"{slot.range_key}_min")
                high = public.get(f"{slot.range_key}_max")
                known = low is not None or high is not None
                matched = known and (low is None or float(expected) >= float(low)) and (
                    high is None or float(expected) <= float(high)
                )
                if hard and not matched:
                    return False
            elif slot.kind in {"max_constraint", "min_constraint"}:
                actual = public.get(slot.spec_key)
                if actual is None:
                    if hard and getattr(slot, "missing_policy", "allow_unknown") != "allow_unknown":
                        return False
                    continue
                if slot.kind == "max_constraint" and float(actual) > float(expected):
                    return False
                if slot.kind == "min_constraint" and float(actual) < float(expected):
                    return False
        return True

    ranked: list[tuple[int, int, dict]] = []
    if not missing and cat is not None:
        for product in repository.by_category(cat.slug):
            if not fits(product):
                continue
            public = product_public(product)
            haystack = str(product.get("search_text") or public.get("name") or "").casefold()
            lexical_score = sum(1 for token in tokens if token in haystack)
            ranked.append(
                (
                    lexical_score,
                    int(public.get("sold") or 0),
                    public,
                )
            )
    ranked.sort(
        key=lambda row: (
            -row[0],
            -row[1],
            int(row[2].get("price_vnd") or 10**15),
            str(row[2].get("sku") or ""),
        )
    )
    top = ranked[:3]
    rec = {
        "ok": bool(top) and not missing,
        "need_more": bool(missing),
        "missing_slots": missing,
        "ask": ["Cần thêm ngành hàng / ngân sách / nhu cầu chính."] if missing else [],
        "category": cat.slug if cat else None,
        "category_display": cat.display if cat else None,
        "top3": [
            {
                **public,
                "match_score": float(score),
                "why": "baseline lexical token overlap + explicit filters",
            }
            for score, _sold, public in top
        ],
        "tradeoffs": [],
        "message": "Không có kết quả qua lexical/filter baseline." if not top and not missing else "",
        "disclaimer": "baseline",
        "source": f"baseline:lexical_filter:{repository.source()}",
    }
    decision = build_decision(need, rec)
    return {
        "episode_id": episode["episode_id"],
        "system_id": "B1_lexical_filter",
        "condition": "B1_lexical_filter",
        "decision": decision,
        "predicted_action": _predict_action(decision, final_text),
        "latency_ms": 0.0,
        "catalog_source": repository.source(),
    }


SYSTEMS = {
    "S_hybrid_constraint": run_hybrid,
    "B0_price_popularity": run_price_popularity,
    "B1_lexical_filter": run_lexical,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "experiments" / "conditions.json")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--benchmark", type=Path, default=ROOT / "experiments" / "benchmark" / "dev.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "experiments" / "results" / "pilot_dev.jsonl")
    parser.add_argument("--manifest", type=Path, default=ROOT / "experiments" / "manifest.json")
    parser.add_argument("--catalog-hash", default=None, help="Override the manifest/conditions snapshot hash")
    args = parser.parse_args()

    conditions = ["S_hybrid_constraint", "B0_price_popularity", "B1_lexical_filter"]
    cfg: dict = {}
    if args.config.is_file():
        cfg = json.loads(args.config.read_text(encoding="utf-8"))
        conditions = list(cfg.get("conditions") or conditions)

    # Deterministic pilot never executes LLM baselines (separate runner).
    unknown = [c for c in conditions if c not in SYSTEMS]
    if unknown:
        raise SystemExit(
            "pilot only supports deterministic conditions "
            f"{sorted(SYSTEMS)}; remove or move to optional_conditions: {unknown}"
        )

    if isinstance(cfg.get("registry"), str) and cfg["registry"].strip():
        os.environ["SALEPILOT_CATALOG_REGISTRY"] = cfg["registry"].strip()
        get_settings.cache_clear()

    manifest_data = (
        json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.manifest.is_file()
        else {}
    )
    family = str((manifest_data.get("catalog") or {}).get("family") or "")
    if manifest_data.get("status") in {"ready", "frozen"} and "dmx" in family:
        os.environ["SALEPILOT_CATALOG_REGISTRY"] = "crawl"
        get_settings.cache_clear()

    pinned_catalog = (
        (manifest_data.get("catalog") or {}).get("snapshot_path")
        if manifest_data.get("status") in {"ready", "frozen"}
        else (cfg.get("catalog") or {}).get("path")
    )
    if isinstance(pinned_catalog, str):
        os.environ["CATALOG_SNAPSHOT"] = str((ROOT / pinned_catalog).resolve())
        get_settings.cache_clear()

    catalog_hash, snapshot_path, pin_source = _load_catalog_pin(
        config=cfg,
        manifest_path=args.manifest,
        explicit_hash=args.catalog_hash,
    )
    repository.reload()
    if repository.source() != "snapshot":
        raise SystemExit(f"pilot requires snapshot catalog backend, got {repository.source()}")

    episodes = []
    for line in args.benchmark.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        if ep.get("split") == args.split:
            episodes.append(ep)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for ep in episodes:
            for cond in conditions:
                row = SYSTEMS[cond](ep)
                row["catalog_hash"] = catalog_hash
                row["catalog_snapshot"] = str(snapshot_path.relative_to(ROOT)).replace("\\", "/")
                row["catalog_pin_source"] = pin_source
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        f"wrote {args.out} episodes={len(episodes)} conditions={conditions} "
        f"source={repository.source()} catalog_hash={catalog_hash} "
        f"registry={os.environ.get('SALEPILOT_CATALOG_REGISTRY')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
