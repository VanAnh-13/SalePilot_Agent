#!/usr/bin/env python3
"""Run deterministic RIVF conditions on a sealed split and score once."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "test"], default="test")
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=None,
        help="Override benchmark JSONL (default: experiments/benchmark/{split}.jsonl)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Prediction JSONL output",
    )
    parser.add_argument(
        "--scores-out",
        type=Path,
        default=None,
        help="Scores JSON output",
    )
    parser.add_argument(
        "--custody-out",
        type=Path,
        default=ROOT / "experiments" / "results" / "CHAIN_OF_CUSTODY.json",
    )
    parser.add_argument("--manifest", type=Path, default=ROOT / "experiments" / "manifest.json")
    parser.add_argument("--config", type=Path, default=ROOT / "experiments" / "conditions.json")
    parser.add_argument("--seal", type=Path, default=ROOT / "experiments" / "benchmark" / "SEAL_RECORD.json")
    args = parser.parse_args()

    py = sys.executable
    split = args.split
    benchmark = args.benchmark or (ROOT / "experiments" / "benchmark" / f"{split}.jsonl")
    out = args.out or (ROOT / "experiments" / "results" / f"exp_{split}_predictions.jsonl")
    scores_out = args.scores_out or (ROOT / "experiments" / "results" / f"exp_{split}_scores.json")

    # 1) Validate seal + benchmark before any prediction.
    checks = [
        [py, str(ROOT / "scripts" / "validate_research_manifest.py"), str(args.manifest)],
        [py, str(ROOT / "scripts" / "validate_benchmark_seal.py"), str(args.seal)],
        [py, str(ROOT / "scripts" / "validate_benchmark.py"), str(benchmark), "--manifest", str(args.manifest)],
    ]
    for cmd in checks:
        print("run:", " ".join(cmd))
        proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
        if proc.returncode != 0:
            return proc.returncode

    # 2) Predict with deterministic pilot runner.
    pilot_cmd = [
        py,
        str(ROOT / "scripts" / "run_pilot.py"),
        "--split",
        split,
        "--benchmark",
        str(benchmark),
        "--out",
        str(out),
        "--manifest",
        str(args.manifest),
        "--config",
        str(args.config),
    ]
    print("run:", " ".join(pilot_cmd))
    proc = subprocess.run(pilot_cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        return proc.returncode

    # 3) Score once.
    score_cmd = [
        py,
        "-m",
        "experiments.evaluate.runner",
        "--input",
        str(out),
        "--labels",
        str(benchmark),
        "--out",
        str(scores_out),
        "--conditions-config",
        str(args.config),
    ]
    print("run:", " ".join(score_cmd))
    proc = subprocess.run(score_cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        return proc.returncode

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    seal = json.loads(args.seal.read_text(encoding="utf-8")) if args.seal.is_file() else {}
    custody = {
        "schema_version": "salepilot-custody-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "split": split,
        "manifest_status": manifest.get("status"),
        "catalog_normalized_hash": (manifest.get("catalog") or {}).get("normalized_catalog_hash"),
        "seal_status": seal.get("status"),
        "benchmark_path": str(benchmark.relative_to(ROOT)).replace("\\", "/"),
        "benchmark_file_sha256": _sha256_file(benchmark),
        "predictions_path": str(out.relative_to(ROOT)).replace("\\", "/"),
        "predictions_sha256": _sha256_file(out),
        "scores_path": str(scores_out.relative_to(ROOT)).replace("\\", "/"),
        "scores_sha256": _sha256_file(scores_out),
        "conditions": (json.loads(args.config.read_text(encoding="utf-8")).get("conditions") if args.config.is_file() else None),
    }
    args.custody_out.parent.mkdir(parents=True, exist_ok=True)
    args.custody_out.write_text(json.dumps(custody, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote custody {args.custody_out}")
    print(json.dumps(json.loads(scores_out.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
