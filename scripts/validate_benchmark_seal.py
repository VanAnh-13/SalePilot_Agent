#!/usr/bin/env python3
"""Validate sealed benchmark custody record for RIVF Track 2."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def inputs_only_hash(rows: list[dict[str, Any]]) -> str:
    payload = [
        {
            "episode_id": row.get("episode_id"),
            "split": row.get("split"),
            "turns": row.get("turns"),
        }
        for row in rows
    ]
    blob = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    return _sha256_bytes(blob)


def validate_seal(record: dict[str, Any], *, root: Path) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != "salepilot-seal-v1":
        errors.append("schema_version must be salepilot-seal-v1")
    status = record.get("status")
    if status not in {
        "registered",
        "awaiting_code_freeze",
        "predictions_locked",
        "scored",
    }:
        errors.append(f"invalid status: {status!r}")

    manifest_rel = record.get("manifest_path") or "experiments/manifest.json"
    manifest_path = root / manifest_rel
    if not manifest_path.is_file():
        errors.append(f"manifest missing: {manifest_rel}")
        return errors
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog = manifest.get("catalog") or {}
    declared_catalog = record.get("catalog_normalized_hash")
    actual_catalog = catalog.get("normalized_catalog_hash")
    if declared_catalog != actual_catalog:
        errors.append(
            "catalog_normalized_hash mismatch with manifest: "
            f"{declared_catalog} != {actual_catalog}"
        )
    if manifest.get("status") not in {"ready", "frozen"}:
        errors.append("manifest must be ready/frozen before seal registration")

    for split_name in ("dev", "test"):
        block = record.get(split_name)
        if not isinstance(block, dict):
            errors.append(f"missing {split_name} block")
            continue
        rel = block.get("path")
        path = root / rel if isinstance(rel, str) else None
        if path is None or not path.is_file():
            errors.append(f"{split_name}.path missing: {rel}")
            continue
        rows = _load_jsonl(path)
        file_hash = _sha256_file(path)
        if block.get("file_sha256") != file_hash:
            errors.append(
                f"{split_name}.file_sha256 mismatch: "
                f"declared {block.get('file_sha256')}, actual {file_hash}"
            )
        inputs_hash = inputs_only_hash(rows)
        if block.get("inputs_sha256") != inputs_hash:
            errors.append(
                f"{split_name}.inputs_sha256 mismatch: "
                f"declared {block.get('inputs_sha256')}, actual {inputs_hash}"
            )
        if int(block.get("episodes") or -1) != len(rows):
            errors.append(
                f"{split_name}.episodes mismatch: "
                f"declared {block.get('episodes')}, actual {len(rows)}"
            )
        splits = {row.get("split") for row in rows}
        if splits != {split_name}:
            errors.append(f"{split_name} file contains unexpected split values: {splits}")
        ids = [row.get("episode_id") for row in rows]
        if len(ids) != len(set(ids)):
            errors.append(f"{split_name} has duplicate episode_id values")
        if split_name == "test" and len(rows) < 32:
            errors.append(f"test split expected >=32 episodes, found {len(rows)}")
        if split_name == "dev" and len(rows) < 16:
            errors.append(f"dev split expected >=16 episodes, found {len(rows)}")

    # No episode_id overlap between dev and test.
    try:
        dev_rows = _load_jsonl(root / record["dev"]["path"])
        test_rows = _load_jsonl(root / record["test"]["path"])
        overlap = {r.get("episode_id") for r in dev_rows} & {r.get("episode_id") for r in test_rows}
        if overlap:
            errors.append(f"dev/test episode_id overlap: {sorted(overlap)[:5]}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"overlap check failed: {exc}")

    if not isinstance(record.get("sample_size_rationale"), str) or len(record["sample_size_rationale"]) < 40:
        errors.append("sample_size_rationale must be a substantive string")
    procedure = record.get("release_procedure")
    if not isinstance(procedure, list) or len(procedure) < 3:
        errors.append("release_procedure must list ordered custody steps")

    return errors


def build_record(*, root: Path, status: str = "registered") -> dict[str, Any]:
    manifest = json.loads((root / "experiments/manifest.json").read_text(encoding="utf-8"))
    catalog_hash = (manifest.get("catalog") or {}).get("normalized_catalog_hash")
    record: dict[str, Any] = {
        "schema_version": "salepilot-seal-v1",
        "status": status,
        "created_at": "2026-07-25",
        "split_seed": manifest.get("split_seed"),
        "manifest_path": "experiments/manifest.json",
        "catalog_normalized_hash": catalog_hash,
        "catalog_family": (manifest.get("catalog") or {}).get("family"),
        "sample_size_rationale": (
            "Dev tracer uses 20 DMX-aligned episodes across deep and generic "
            "categories with clarify/abstain/faq/negation branches. Sealed test "
            "uses 40 held-out episodes stratified by category and difficulty to "
            "target primary hard-constraint CI width near +/-0.08 at 95% bootstrap "
            "under the frozen catalog hash."
        ),
        "release_procedure": [
            "Freeze protocol + ready manifest catalog hash",
            "Register sealed dev/test file and inputs-only hashes in SEAL_RECORD",
            "Freeze code/conditions hash before prediction",
            "Run deterministic conditions predict-only; lock prediction hash",
            "Score once against frozen labels; write CHAIN_OF_CUSTODY",
        ],
        "notes": (
            "Labels are colocated in JSONL for single-machine reproducibility. "
            "inputs_sha256 isolates turn text from labels for custody audits."
        ),
    }
    for split_name, rel in (
        ("dev", "experiments/benchmark/dev.jsonl"),
        ("test", "experiments/benchmark/test.jsonl"),
    ):
        path = root / rel
        rows = _load_jsonl(path)
        record[split_name] = {
            "path": rel,
            "episodes": len(rows),
            "file_sha256": _sha256_file(path),
            "inputs_sha256": inputs_only_hash(rows),
        }
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "seal",
        nargs="?",
        type=Path,
        default=ROOT / "experiments" / "benchmark" / "SEAL_RECORD.json",
    )
    parser.add_argument("--write", action="store_true", help="Write/refresh the seal record")
    parser.add_argument(
        "--status",
        default="registered",
        choices=["registered", "awaiting_code_freeze", "predictions_locked", "scored"],
    )
    args = parser.parse_args(argv)

    seal_path = args.seal if args.seal.is_absolute() else (Path.cwd() / args.seal).resolve()
    if args.write:
        record = build_record(root=ROOT, status=args.status)
        seal_path.parent.mkdir(parents=True, exist_ok=True)
        seal_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {seal_path}")
    elif args.status != "registered" and seal_path.is_file():
        # Allow status-only promotion without rewriting frozen hashes.
        record = json.loads(seal_path.read_text(encoding="utf-8"))
        record["status"] = args.status
        seal_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"updated status={args.status} in {seal_path}")
    else:
        if not seal_path.is_file():
            print(f"ERROR: seal record missing: {seal_path}", file=sys.stderr)
            return 2
        record = json.loads(seal_path.read_text(encoding="utf-8"))

    errors = validate_seal(record, root=ROOT)
    if errors:
        print("INVALID seal record:")
        for item in errors:
            print(f"- {item}")
        return 1
    print(f"OK seal record status={record.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
