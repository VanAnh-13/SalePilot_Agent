"""Recompute the paper's descriptive tables; never regenerate historic predictions.

Full audit requires the original repository inputs; use --repo-root explicitly.
The standalone paper package supports --check-report (derived arithmetic only).
Only aggregate tool counts are read into the output; customer examples are omitted.
"""

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("audit.json")


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path):
    file = ROOT / path
    return hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else None


def counts(rows):
    checked = sum(r["hard_constraints"]["checked"] for r in rows)
    violations = sum(r["hard_constraints"]["violations"] for r in rows)
    return {
        "episodes": len(rows), "checks": checked, "violations": violations,
        "rate": violations / checked if checked else None,
        "episodes_with_checks": sum(r["hard_constraints"]["checked"] > 0 for r in rows),
        "episodes_with_violations": sum(r["hard_constraints"]["violations"] > 0 for r in rows),
    }


def check_report():
    report = json.loads(OUT.read_text(encoding="utf-8"))
    support = report["label_support"]
    total = sum(support.values())
    order = report["action_matrix_order"]
    for name, result in report["results"].items():
        matrix = result["confusion_matrix_gold_rows_predicted_columns"]
        assert [sum(row) for row in matrix] == [support.get(k, 0) for k in order], name
        assert [sum(row[i] for row in matrix) for i in range(len(order))] == [result["actions"].get(k, 0) for k in order], name
        assert sum(matrix[i][i] for i in range(len(order))) / total == result["action_accuracy"], name
        slots = result["slot_counts"]
        assert 2 * slots["tp"] / (2 * slots["tp"] + slots["fp"] + slots["fn"]) == result["slot_micro_f1"], name
        for key in ("all_payloads", "recommend_actions_only", "common_recommendation_episodes"):
            group = result[key]
            assert group["rate"] == (group["violations"] / group["checks"] if group["checks"] else None), (name, key)
            assert 0 <= group["episodes_with_violations"] <= group["episodes_with_checks"] <= group["episodes"], (name, key)
        assert result["all_payloads"]["episodes"] == total, name
        assert result["recommend_actions_only"]["episodes"] == result["actions"].get("recommend", 0), name
        assert result["common_recommendation_episodes"]["episodes"] == len(report["common_recommendation_ids"]), name
    print("PASS: derived-report arithmetic only. Raw rows, input hashes and source correspondence were NOT verified.")


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, help="Full SalePilot repository containing the original audit inputs")
    parser.add_argument("--check-report", action="store_true", help="Check bundled audit.json arithmetic only; no raw-data reaggregation")
    args = parser.parse_args()
    if args.check_report:
        check_report()
        return
    if args.repo_root:
        ROOT = args.repo_root.resolve()
    required = [
        "experiments/benchmark/dev.jsonl", "experiments/benchmark/test.jsonl",
        "experiments/benchmark/SEAL_RECORD.json", "experiments/results/exp_test_scores.json",
        "experiments/results/CHAIN_OF_CUSTODY.json", "experiments/manifest.json",
        "backend/data/catalog_stats.json", "backend/data/spec_index.json", "backend/data/faq.json",
        "backend/data/research/dmx_tool_schemas.json",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        parser.error("Raw audit inputs absent. Pass --repo-root /path/to/full/repository. "
                     "The paper-only package supports only --check-report. Missing: " + ", ".join(missing))
    label_path = "experiments/benchmark/test.jsonl"
    score_path = "experiments/results/exp_test_scores.json"
    labels = [json.loads(line) for line in (ROOT / label_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    gold = {r["episode_id"]: r for r in labels}
    scores = read(score_path)
    custody = read("experiments/results/CHAIN_OF_CUSTODY.json")["deterministic"]
    groups = {
        name: {r["episode_id"]: r for r in scores["episodes"] if r["condition"] == name}
        for name in scores["aggregates"]
    }
    assert len(labels) == len(gold) == 40
    assert len(scores["episodes"]) == 120
    assert all(set(rows) == set(gold) for rows in groups.values())
    common = set.intersection(*[
        {i for i, r in rows.items() if r["predicted_action"] == "recommend"}
        for rows in groups.values()
    ])
    results = {}
    action_order = ["recommend", "clarify", "faq", "abstain"]
    for name, by_id in groups.items():
        rows = list(by_id.values())
        actions = Counter(r["predicted_action"] for r in rows)
        confusion = Counter((gold[r["episode_id"]]["expected_action"], r["predicted_action"]) for r in rows)
        all_counts = counts(rows)
        tp, fp, fn = (sum(r["slot_f1"][k] for r in rows) for k in ("tp", "fp", "fn"))
        recomputed = {
            "category_accuracy": sum(r["category_correct"] for r in rows) / len(rows),
            "action_accuracy": sum(r["action_correct"] for r in rows) / len(rows),
            "slot_micro_f1": 2 * tp / (2 * tp + fp + fn),
        }
        for key, value in recomputed.items():
            assert round(value, 4) == scores["aggregates"][name][key], (name, key)
        assert all_counts["checks"] == scores["aggregates"][name]["hard_constraints_checked"]
        assert all_counts["violations"] == scores["aggregates"][name]["hard_constraint_violations"]
        results[name] = {
            **recomputed, "slot_counts": {"tp": tp, "fp": fp, "fn": fn},
            "actions": dict(actions), "all_payloads": all_counts,
            "recommend_actions_only": counts([r for r in rows if r["predicted_action"] == "recommend"]),
            "common_recommendation_episodes": counts([by_id[i] for i in sorted(common)]),
            "confusion_matrix_gold_rows_predicted_columns": [[confusion[(g, p)] for p in action_order] for g in action_order],
            "non_recommendations_with_checks": [
                {"episode_id": r["episode_id"], "action": r["predicted_action"], **r["hard_constraints"]}
                for r in rows if r["predicted_action"] != "recommend" and r["hard_constraints"]["checked"]
            ],
        }
    artifact_checks = {}
    for key in ["predictions", "scores", "bootstrap", "bootstrap_pooled"]:
        actual = digest(custody[key])
        artifact_checks[key] = {"path": custody[key], "expected_sha256": custody[key + "_sha256"], "actual_sha256": actual, "matches": actual == custody[key + "_sha256"]}
    # Preserve the raw-byte comparison and check the score's CRLF representation.
    score_bytes = (ROOT / custody["scores"]).read_bytes()
    score_lf = score_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    score_crlf_sha256 = hashlib.sha256(score_lf.replace(b"\n", b"\r\n")).hexdigest()
    artifact_checks["scores"]["crlf_sha256"] = score_crlf_sha256
    artifact_checks["scores"]["matches_with_crlf"] = score_crlf_sha256 == custody["scores_sha256"]
    seal = read("experiments/benchmark/SEAL_RECORD.json")
    for split in ["dev", "test"]:
        actual = digest(seal[split]["path"])
        artifact_checks[split + "_labels"] = {"actual_sha256": actual, "matches": actual == seal[split]["file_sha256"]}
        assert artifact_checks[split + "_labels"]["matches"]
    catalog = read("experiments/manifest.json")["catalog"]
    artifact_checks["historic_catalog"] = {"path": catalog["snapshot_path"], "exists": (ROOT / catalog["snapshot_path"]).is_file(), "claimed_products": catalog["expected_total_products"], "claimed_categories": catalog["expected_categories"]}
    tool_counts = {k: v["call_count"] for k, v in read("backend/data/research/dmx_tool_schemas.json").items()}
    source_paths = [
        "backend/app/agent/graph.py", "backend/app/agent/offline.py", "backend/app/agent/fast_path.py",
        "backend/app/agent/intent.py", "backend/app/agent/recommendation.py", "backend/app/agent/consultation.py",
        "backend/app/agent/decision.py", "backend/app/agent/lead_tools.py", "backend/app/agent/subagents/base.py",
        "backend/app/agent/tools/catalog.py", "backend/app/config.py",
        "backend/app/agent/memory/store.py",
        "backend/app/catalog/category_model.py", "backend/app/catalog/crawl_categories.py", "backend/app/catalog/repository.py",
        "backend/app/api/chat.py", "scripts/run_pilot.py", "experiments/evaluate/runner.py", "experiments/evaluate/metrics.py",
        label_path, score_path, "backend/data/catalog_stats.json", "backend/data/spec_index.json", "backend/data/faq.json",
        "experiments/conditions.json", "experiments/manifest.json", "experiments/results/CHAIN_OF_CUSTODY.json",
    ]
    report = {
        "revision_date": "2026-09-28", "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "scope": "Author-side full-repository audit and reaggregation; not a new inference run or custody repair. Paper-only distribution includes this derived report, not its raw inputs.",
        "label_support": dict(Counter(r["expected_action"] for r in labels)),
        "user_turn_counts": dict(Counter(sum(t["role"] == "user" for t in r["turns"]) for r in labels)),
        "action_matrix_order": action_order, "common_recommendation_ids": sorted(common),
        "results": results, "artifact_checks": artifact_checks,
        "catalog_summary_as_stored": read("backend/data/catalog_stats.json"),
        "spec_keys_in_available_index": len(read("backend/data/spec_index.json")),
        "faq_chunks_in_available_file": len(read("backend/data/faq.json")),
        "tool_call_counts_only": tool_counts, "tool_call_total": sum(tool_counts.values()),
        "source_sha256": {path: digest(path) for path in source_paths},
    }
    manuscript = ROOT / "PaperDraf/main.tex"
    if manuscript.is_file():
        tex = manuscript.read_text(encoding="utf-8")
        citations = {key.strip() for group in re.findall(r"\\cite\{([^}]+)\}", tex) for key in group.split(",")}
        bibliography = set(re.findall(r"\\bibitem\{([^}]+)\}", tex))
        labels_tex = re.findall(r"\\label\{([^}]+)\}", tex)
        refs = set(re.findall(r"\\(?:eqref|ref)\{([^}]+)\}", tex))
        report["manuscript_checks"] = {
            "missing_citations": sorted(citations - bibliography), "unused_bibliography": sorted(bibliography - citations),
            "unresolved_references": sorted(refs - set(labels_tex)),
            "duplicate_labels": sorted(k for k, n in Counter(labels_tex).items() if n > 1),
            "external_input_commands": re.findall(r"\\(?:input|include|includegraphics|bibliography)\{([^}]+)\}", tex),
            "flow_diagrams": tex.count("\\begin{tikzpicture}"),
        }
        bib_keys = set(re.findall(r"@\w+\{([^,]+),", (manuscript.parent / "ref.bib").read_text(encoding="utf-8")))
        report["manuscript_checks"]["companion_bibliography_key_difference"] = sorted(bib_keys ^ bibliography)
        for check, findings in report["manuscript_checks"].items():
            assert findings == 5 if check == "flow_diagrams" else not findings, (check, findings)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "episodes": len(labels), "common_recommendations": len(common), "artifact_status": {k: v.get("matches", v.get("exists")) for k, v in artifact_checks.items()}, "score_matches_with_crlf": artifact_checks["scores"]["matches_with_crlf"], "manuscript_checks": report.get("manuscript_checks")}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
