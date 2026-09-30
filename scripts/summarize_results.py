#!/usr/bin/env python3
"""Summarize scored experiment JSON into markdown/LaTeX-friendly tables.

Optionally computes episode-level bootstrap 95% CIs for primary metrics when
per-episode rows are present under ``episodes``.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def _fmt(value: Any, digits: int = 4) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        return f"{value:.{digits}f}"
    return str(value)


def _bootstrap_ci(
    values: list[float],
    *,
    n_boot: int = 2000,
    seed: int = 20260723,
) -> tuple[float, float, float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * (n_boot - 1))]
    hi = means[int(0.975 * (n_boot - 1))]
    point = sum(values) / n
    return point, lo, hi


def _episode_pooled_stats(
    episodes: list[dict[str, Any]], condition: str
) -> dict[str, dict[str, float]]:
    """Per-episode raw counts keyed by episode_id for pooled resampling."""
    stats: dict[str, dict[str, float]] = {}
    for row in episodes:
        if row.get("condition") != condition:
            continue
        episode_id = str(row.get("episode_id"))
        slot = row.get("slot_f1") or {}
        hard = row.get("hard_constraints") or {}
        stats[episode_id] = {
            "cat": 1.0 if row.get("category_correct") else 0.0,
            "act": 1.0 if row.get("action_correct") else 0.0,
            "tp": float(slot.get("tp") or 0),
            "fp": float(slot.get("fp") or 0),
            "fn": float(slot.get("fn") or 0),
            "checked": float(hard.get("checked") or 0),
            "violations": float(hard.get("violations") or 0),
        }
    return stats


def _pooled_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    n = len(rows)
    tp = sum(r["tp"] for r in rows)
    fp = sum(r["fp"] for r in rows)
    fn = sum(r["fn"] for r in rows)
    checked = sum(r["checked"] for r in rows)
    violations = sum(r["violations"] for r in rows)
    return {
        "category_accuracy": sum(r["cat"] for r in rows) / n if n else math.nan,
        "action_accuracy": sum(r["act"] for r in rows) / n if n else math.nan,
        "slot_micro_f1": (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) > 0 else math.nan,
        "hard_constraint_violation_rate": (violations / checked) if checked > 0 else math.nan,
    }


def _pooled_bootstrap(
    per_condition: dict[str, dict[str, dict[str, float]]],
    *,
    n_boot: int,
    seed: int,
    diff_pairs: list[tuple[str, str]],
) -> dict[str, Any]:
    """Episode-level bootstrap of the POOLED table metrics.

    One shared resample of episode ids per iteration keeps condition
    comparisons paired; conditions are evaluated on identical resamples.
    """
    episode_ids = sorted(set().union(*(set(v) for v in per_condition.values())))
    for name, stats in per_condition.items():
        missing = [e for e in episode_ids if e not in stats]
        if missing:
            raise SystemExit(f"condition {name} missing episodes: {missing[:5]}")
    rng = random.Random(seed)
    n = len(episode_ids)
    samples: dict[str, dict[str, list[float]]] = {
        name: defaultdict(list) for name in per_condition
    }
    diff_samples: dict[str, list[float]] = defaultdict(list)
    for _ in range(n_boot):
        drawn = [episode_ids[rng.randrange(n)] for _ in range(n)]
        per_iter: dict[str, dict[str, float]] = {}
        for name, stats in per_condition.items():
            metrics = _pooled_metrics([stats[e] for e in drawn])
            per_iter[name] = metrics
            for metric, value in metrics.items():
                if not math.isnan(value):
                    samples[name][metric].append(value)
        for a, b in diff_pairs:
            va = per_iter[a]["hard_constraint_violation_rate"]
            vb = per_iter[b]["hard_constraint_violation_rate"]
            if not (math.isnan(va) or math.isnan(vb)):
                diff_samples[f"{a}-minus-{b}"].append(va - vb)

    def _percentile_ci(values: list[float]) -> dict[str, float]:
        ordered = sorted(values)
        k = len(ordered)
        return {
            "ci95_low": ordered[int(0.025 * (k - 1))],
            "ci95_high": ordered[int(0.975 * (k - 1))],
            "resamples_used": k,
        }

    out: dict[str, Any] = {
        "method": "episode-level percentile bootstrap of pooled metrics, paired resamples",
        "n_boot": n_boot,
        "seed": seed,
        "episodes": n,
        "conditions": {},
        "hard_violation_rate_differences": {},
    }
    for name, stats in per_condition.items():
        point = _pooled_metrics([stats[e] for e in episode_ids])
        out["conditions"][name] = {
            metric: {"point": point[metric], **_percentile_ci(values)}
            for metric, values in samples[name].items()
        }
    for key, values in diff_samples.items():
        a, b = key.split("-minus-")
        pa = _pooled_metrics(list(per_condition[a].values()))
        pb = _pooled_metrics(list(per_condition[b].values()))
        out["hard_violation_rate_differences"][key] = {
            "point": pa["hard_constraint_violation_rate"] - pb["hard_constraint_violation_rate"],
            **_percentile_ci(values),
        }
    return out


def _episode_metric_series(episodes: list[dict[str, Any]], condition: str) -> dict[str, list[float]]:
    series: dict[str, list[float]] = defaultdict(list)
    for row in episodes:
        if row.get("condition") != condition:
            continue
        if "category_correct" in row:
            series["category_accuracy"].append(1.0 if row.get("category_correct") else 0.0)
        if "action_correct" in row:
            series["action_accuracy"].append(1.0 if row.get("action_correct") else 0.0)
        slot = row.get("slot_f1") or {}
        if isinstance(slot, dict) and "f1" in slot:
            series["slot_micro_f1"].append(float(slot["f1"]))
        hard = row.get("hard_constraints") or {}
        if isinstance(hard, dict) and int(hard.get("checked") or 0) > 0:
            series["hard_constraint_violation_rate"].append(float(hard.get("rate") or 0.0))
    return series


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scores", type=Path, help="Path to *_scores.json")
    parser.add_argument("--latex", action="store_true")
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Print episode bootstrap 95%% CIs of episode-mean metrics (does NOT estimate the pooled table metrics; prefer --pooled-bootstrap)",
    )
    parser.add_argument(
        "--pooled-bootstrap",
        action="store_true",
        help="Episode-resample bootstrap 95%% CIs of the pooled table metrics, with paired hard-violation-rate differences",
    )
    parser.add_argument("--bootstrap-out", type=Path, default=None)
    parser.add_argument("--n-boot", type=int, default=2000)
    args = parser.parse_args()
    path = args.scores if args.scores.is_absolute() else Path.cwd() / args.scores
    if not path.is_file():
        print(f"ERROR missing {path}", file=sys.stderr)
        return 2
    data = json.loads(path.read_text(encoding="utf-8"))
    conditions = data.get("conditions") or data.get("aggregates") or data
    if not isinstance(conditions, dict):
        print("ERROR: unexpected scores shape", file=sys.stderr)
        return 2

    headers = [
        "condition",
        "episodes",
        "cat_acc",
        "act_acc",
        "slot_f1",
        "hard_viol",
        "hard_n",
    ]
    rows: list[list[str]] = []
    for name, block in sorted(conditions.items()):
        if not isinstance(block, dict):
            continue
        rows.append(
            [
                name,
                str(block.get("episodes", "")),
                _fmt(block.get("category_accuracy")),
                _fmt(block.get("action_accuracy")),
                _fmt(block.get("slot_micro_f1")),
                _fmt(block.get("hard_constraint_violation_rate")),
                str(block.get("hard_constraints_checked", "")),
            ]
        )

    if args.latex:
        print("\\begin{tabular}{" + ("l" * len(headers)) + "}")
        print("\\toprule")
        print(" & ".join(headers) + " \\\\")
        print("\\midrule")
        for row in rows:
            print(" & ".join(row) + " \\\\")
        print("\\bottomrule")
        print("\\end{tabular}")
    else:
        widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
        fmt = "  ".join(f"{{:{w}}}" for w in widths)
        print(fmt.format(*headers))
        print(fmt.format(*["-" * w for w in widths]))
        for row in rows:
            print(fmt.format(*row))

    if args.pooled_bootstrap:
        episodes = data.get("episodes") or []
        if not isinstance(episodes, list) or not episodes:
            print("pooled bootstrap skipped: no per-episode rows", file=sys.stderr)
            return 0
        per_condition = {
            name: _episode_pooled_stats(episodes, name)
            for name in sorted(conditions)
            if isinstance(conditions.get(name), dict)
        }
        names = sorted(per_condition)
        diff_pairs = [
            (a, b)
            for a in names
            for b in names
            if a.startswith("B0") and not b.startswith("B0")
        ]
        boot = _pooled_bootstrap(
            per_condition,
            n_boot=args.n_boot,
            seed=20260723,
            diff_pairs=diff_pairs,
        )
        print("\nPooled bootstrap 95% CI (episode resample, paired):")
        for name in names:
            print(f"  {name}")
            for metric, row in boot["conditions"][name].items():
                print(
                    f"    {metric}: {_fmt(row['point'])} "
                    f"[{_fmt(row['ci95_low'])}, {_fmt(row['ci95_high'])}] "
                    f"(resamples={row['resamples_used']})"
                )
        for key, row in boot["hard_violation_rate_differences"].items():
            print(
                f"  diff {key}: {_fmt(row['point'])} "
                f"[{_fmt(row['ci95_low'])}, {_fmt(row['ci95_high'])}]"
            )
        if args.bootstrap_out:
            out = args.bootstrap_out if args.bootstrap_out.is_absolute() else Path.cwd() / args.bootstrap_out
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(boot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"wrote {out}")
        return 0

    if args.bootstrap:
        episodes = data.get("episodes") or []
        if not isinstance(episodes, list) or not episodes:
            print("bootstrap skipped: no per-episode rows", file=sys.stderr)
            return 0
        boot: dict[str, Any] = {"n_boot": args.n_boot, "seed": 20260723, "conditions": {}}
        print("\nBootstrap 95% CI (episode resample):")
        for name in sorted(conditions):
            series = _episode_metric_series(episodes, name)
            cond_out: dict[str, Any] = {}
            print(f"  {name}")
            for metric, values in series.items():
                ci = _bootstrap_ci(values, n_boot=args.n_boot)
                if ci is None:
                    continue
                point, lo, hi = ci
                cond_out[metric] = {
                    "point": point,
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "n": len(values),
                }
                print(f"    {metric}: {_fmt(point)} [{_fmt(lo)}, {_fmt(hi)}] n={len(values)}")
            boot["conditions"][name] = cond_out
        if args.bootstrap_out:
            out = args.bootstrap_out if args.bootstrap_out.is_absolute() else Path.cwd() / args.bootstrap_out
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(boot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
