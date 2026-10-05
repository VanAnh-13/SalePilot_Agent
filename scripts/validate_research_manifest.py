#!/usr/bin/env python3
"""Validate SalePilot-R research manifest for RIVF Track 2.

Usage:
  python scripts/validate_research_manifest.py experiments/manifest.json
  python scripts/validate_research_manifest.py experiments/manifest.json --allow-blocked
  python scripts/validate_research_manifest.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


REQUIRED_TOP = {
    "schema_version",
    "project",
    "status",
    "protocol_path",
    "dataset_card_path",
    "split_seed",
    "catalog",
    "assets",
    "privacy",
    "human_study_gate",
}

REQUIRED_CATALOG = {
    "family",
    "source_path",
    "source_required",
    "raw_source_hash",
    "normalized_catalog_hash",
    "snapshot_path",
    "schema_version",
    "experiment_backend",
    "rights_status",
}

VALID_STATUS = {"blocked", "ready", "frozen"}
VALID_HUMAN = {"disabled", "enabled"}
HEX64 = set("0123456789abcdef")
DENIED_RIGHTS = {"denied", "revoked", "not_allowed"}
PUBLICATION_CATALOG_RIGHTS = "owner_confirmed_publication"
DERIVED_SNAPSHOT_RIGHTS = "derived_ready"


def _err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.lower().removeprefix("sha256:")
    return len(text) == 64 and all(ch in HEX64 for ch in text)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_path(root: Path, rel: Any) -> Path | None:
    if not isinstance(rel, str) or not rel:
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _check_declared_hash(
    errors: list[str],
    *,
    label: str,
    declared: Any,
    path: Path | None,
    required: bool,
    check_paths: bool,
) -> None:
    if declared is None:
        if required:
            _err(errors, f"{label} requires sha256")
        return
    if not _is_sha256(declared):
        _err(errors, f"{label} must be sha256")
        return
    if check_paths and path is not None and path.is_file():
        actual = _sha256_file(path)
        expected = str(declared).lower().removeprefix("sha256:")
        if actual != expected:
            _err(errors, f"{label} does not match file bytes: expected {expected}, got {actual}")


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest root must be an object")
    return data


def validate_manifest(
    data: dict[str, Any],
    *,
    root: Path,
    allow_blocked: bool = False,
    check_paths: bool = True,
) -> list[str]:
    errors: list[str] = []

    missing = REQUIRED_TOP - set(data)
    if missing:
        _err(errors, f"missing top-level fields: {sorted(missing)}")
        return errors

    status = data.get("status")
    if status not in VALID_STATUS:
        _err(errors, f"invalid status: {status!r}")

    if data.get("human_study_gate") not in VALID_HUMAN:
        _err(errors, f"invalid human_study_gate: {data.get('human_study_gate')!r}")

    if not isinstance(data.get("split_seed"), int):
        _err(errors, "split_seed must be int")

    catalog = data.get("catalog")
    if not isinstance(catalog, dict):
        _err(errors, "catalog must be object")
        return errors

    cat_missing = REQUIRED_CATALOG - set(catalog)
    if cat_missing:
        _err(errors, f"catalog missing fields: {sorted(cat_missing)}")

    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        _err(errors, "assets must be a non-empty list")
    else:
        for i, asset in enumerate(assets):
            if not isinstance(asset, dict):
                _err(errors, f"assets[{i}] must be object")
                continue
            for key in ("id", "path", "role", "rights_status"):
                if key not in asset:
                    _err(errors, f"assets[{i}] missing {key}")
            rights = asset.get("rights_status")
            if rights in DENIED_RIGHTS:
                _err(errors, f"assets[{i}] has denied rights_status: {rights}")
            if rights is not None and not isinstance(rights, str):
                _err(errors, f"assets[{i}].rights_status must be string")
            _check_declared_hash(
                errors,
                label=f"assets[{asset.get('id', '?')}].hash",
                declared=asset.get("hash"),
                path=_repo_path(root, asset.get("path")),
                required=bool(asset.get("required_for_experiments")) and status in {"ready", "frozen"},
                check_paths=check_paths,
            )

    privacy = data.get("privacy")
    if not isinstance(privacy, dict):
        _err(errors, "privacy must be object")
    else:
        if privacy.get("allow_raw_trajectories_in_release") is not False:
            _err(errors, "privacy.allow_raw_trajectories_in_release must be false")
        if privacy.get("allow_real_phone_email") is not False:
            _err(errors, "privacy.allow_real_phone_email must be false")
        if privacy.get("redaction_required") is not True:
            _err(errors, "privacy.redaction_required must be true")

    if check_paths:
        for rel_key in ("protocol_path", "dataset_card_path"):
            rel = data.get(rel_key)
            if not isinstance(rel, str) or not (root / rel).is_file():
                _err(errors, f"{rel_key} not found: {rel}")

        if isinstance(assets, list):
            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                rel = asset.get("path")
                required = bool(asset.get("required_for_experiments"))
                if not isinstance(rel, str):
                    continue
                path = _repo_path(root, rel)
                if path is None:
                    _err(errors, f"asset path must be repo-relative: {rel}")
                    continue
                exists = path.exists()
                if required and status in {"ready", "frozen"} and not exists:
                    _err(errors, f"required asset missing for {status} status: {rel}")
                if required and status == "blocked" and not exists:
                    # expected while blocked; still require explicit blocker tag
                    pass
                asset["__exists"] = exists

    source_path = catalog.get("source_path")
    source_required = bool(catalog.get("source_required"))
    source_file = _repo_path(root, source_path)
    source_exists = source_file is not None and source_file.is_file()
    snapshot_file = _repo_path(root, catalog.get("snapshot_path"))
    raw_hash = catalog.get("raw_source_hash")
    norm_hash = catalog.get("normalized_catalog_hash")

    catalog_rights = catalog.get("rights_status")
    if catalog_rights in DENIED_RIGHTS:
        _err(errors, f"catalog has denied rights_status: {catalog_rights}")
    if not isinstance(catalog_rights, str) or not catalog_rights:
        _err(errors, "catalog.rights_status must be a non-empty string")
    if status in {"ready", "frozen"} and catalog_rights != PUBLICATION_CATALOG_RIGHTS:
        _err(errors, "ready/frozen requires catalog.rights_status=owner_confirmed_publication")

    _check_declared_hash(
        errors,
        label="catalog.raw_source_hash",
        declared=raw_hash,
        path=source_file,
        required=status in {"ready", "frozen"},
        check_paths=check_paths,
    )
    _check_declared_hash(
        errors,
        label="catalog.normalized_catalog_hash",
        declared=norm_hash,
        path=snapshot_file,
        required=status in {"ready", "frozen"},
        check_paths=check_paths,
    )

    if source_required and not source_exists:
        if status != "blocked":
            _err(errors, "source missing but status is not blocked")
        blockers = data.get("blockers") or []
        accepted_blockers = {
            "canonical_workbook_missing",
            "canonical_source_missing",
        }
        if not accepted_blockers.intersection(blockers or []):
            _err(
                errors,
                "blockers must include canonical_source_missing "
                "(or legacy canonical_workbook_missing) when source is absent",
            )

    if status in {"ready", "frozen"}:
        if not source_exists and source_required:
            _err(errors, "ready/frozen requires canonical source file")
        if not _is_sha256(raw_hash):
            _err(errors, "ready/frozen requires catalog.raw_source_hash sha256")
        if not _is_sha256(norm_hash):
            _err(errors, "ready/frozen requires catalog.normalized_catalog_hash sha256")
        if snapshot_file is None or not snapshot_file.is_file():
            _err(errors, "ready/frozen requires snapshot file")
        if data.get("blockers"):
            _err(errors, "ready/frozen must have empty blockers")
    elif status == "blocked":
        if not allow_blocked:
            _err(
                errors,
                "manifest status=blocked; pass --allow-blocked for structural validation only",
            )
        if not data.get("blockers"):
            _err(errors, "blocked manifest must list blockers")

    # Outside-repo absolute paths are not allowed in declared asset paths.
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            rel = asset.get("path")
            if isinstance(rel, str) and (rel.startswith("/") or (len(rel) > 1 and rel[1] == ":")):
                _err(errors, f"asset path must be repo-relative: {rel}")

            if status in {"ready", "frozen"} and asset.get("required_for_experiments"):
                expected_rights = (
                    PUBLICATION_CATALOG_RIGHTS
                    if asset.get("id") == "catalog_workbook"
                    else DERIVED_SNAPSHOT_RIGHTS
                    if asset.get("id") == "catalog_snapshot"
                    else None
                )
                if expected_rights and asset.get("rights_status") != expected_rights:
                    _err(
                        errors,
                        f"asset {asset.get('id')} requires rights_status={expected_rights}",
                    )

            if asset.get("id") == "catalog_workbook" and _is_sha256(asset.get("hash")) and _is_sha256(raw_hash):
                if str(asset["hash"]).lower().removeprefix("sha256:") != str(raw_hash).lower().removeprefix("sha256:"):
                    _err(errors, "catalog_workbook hash differs from catalog.raw_source_hash")
            if asset.get("id") == "catalog_snapshot" and _is_sha256(asset.get("hash")) and _is_sha256(norm_hash):
                if str(asset["hash"]).lower().removeprefix("sha256:") != str(norm_hash).lower().removeprefix("sha256:"):
                    _err(errors, "catalog_snapshot hash differs from catalog.normalized_catalog_hash")

    return errors


def _self_test(root: Path) -> int:
    good_blocked = {
        "schema_version": "salepilot-research-manifest-v1",
        "project": "salepilot-r",
        "status": "blocked",
        "blockers": ["canonical_workbook_missing"],
        "protocol_path": "docs/RIVF_TRACK2_PROTOCOL.md",
        "dataset_card_path": "docs/DATASET_CARD.md",
        "split_seed": 1,
        "human_study_gate": "disabled",
        "catalog": {
            "family": "workbook_14_categories",
            "source_path": "Spec_cate_gia.xlsx",
            "source_required": True,
            "raw_source_hash": None,
            "normalized_catalog_hash": None,
            "snapshot_path": "backend/data/research/catalog_workbook_snapshot.json",
            "schema_version": "salepilot-catalog-v1",
            "experiment_backend": "snapshot",
            "rights_status": "owner_confirmed_publication_pending_file",
        },
        "assets": [
            {
                "id": "catalog_workbook",
                "path": "Spec_cate_gia.xlsx",
                "role": "canonical_catalog_source",
                "rights_status": "owner_confirmed_publication_pending_file",
                "required_for_experiments": True,
            }
        ],
        "privacy": {
            "benchmark_ids": "synthetic_or_pseudonymous",
            "allow_raw_trajectories_in_release": False,
            "allow_real_phone_email": False,
            "redaction_required": True,
        },
    }

    # Structural blocked validation should pass with --allow-blocked semantics.
    errs = validate_manifest(good_blocked, root=root, allow_blocked=True, check_paths=True)
    assert not errs, errs

    # Strict mode must fail while blocked.
    strict = validate_manifest(good_blocked, root=root, allow_blocked=False, check_paths=True)
    assert any("allow-blocked" in e for e in strict), strict

    missing_seed = json.loads(json.dumps(good_blocked))
    missing_seed.pop("split_seed")
    missing_errs = validate_manifest(missing_seed, root=root, allow_blocked=True, check_paths=False)
    assert any("split_seed" in e for e in missing_errs), missing_errs

    bad_privacy = json.loads(json.dumps(good_blocked))
    bad_privacy["privacy"]["allow_raw_trajectories_in_release"] = True
    privacy_errs = validate_manifest(bad_privacy, root=root, allow_blocked=True, check_paths=False)
    assert any("allow_raw_trajectories_in_release" in e for e in privacy_errs), privacy_errs

    denied = json.loads(json.dumps(good_blocked))
    denied["assets"][0]["rights_status"] = "denied"
    denied_errs = validate_manifest(denied, root=root, allow_blocked=True, check_paths=False)
    assert any("denied rights_status" in e for e in denied_errs), denied_errs

    # A ready manifest must pin the exact bytes, not merely provide hash-shaped
    # strings. Use repo-local temporary files so path containment is exercised.
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        tmp_dir = Path(tmp)
        source = tmp_dir / "source.xlsx"
        snapshot = tmp_dir / "snapshot.json"
        source.write_bytes(b"source")
        snapshot.write_bytes(b"[]\n")
        source_rel = source.relative_to(root).as_posix()
        snapshot_rel = snapshot.relative_to(root).as_posix()
        source_hash = _sha256_file(source)
        snapshot_hash = _sha256_file(snapshot)

        ready_with_files = json.loads(json.dumps(good_blocked))
        ready_with_files["status"] = "ready"
        ready_with_files["blockers"] = []
        ready_with_files["catalog"].update(
            {
                "source_path": source_rel,
                "snapshot_path": snapshot_rel,
                "raw_source_hash": source_hash,
                "normalized_catalog_hash": snapshot_hash,
                "rights_status": PUBLICATION_CATALOG_RIGHTS,
            }
        )
        ready_with_files["assets"] = [
            {
                "id": "catalog_workbook",
                "path": source_rel,
                "role": "canonical_catalog_source",
                "rights_status": PUBLICATION_CATALOG_RIGHTS,
                "required_for_experiments": True,
                "hash": source_hash,
            },
            {
                "id": "catalog_snapshot",
                "path": snapshot_rel,
                "role": "canonical_experiment_snapshot",
                "rights_status": DERIVED_SNAPSHOT_RIGHTS,
                "required_for_experiments": True,
                "hash": snapshot_hash,
            },
        ]
        ready_ok = validate_manifest(ready_with_files, root=root, check_paths=True)
        assert not ready_ok, ready_ok

        ready_with_files["catalog"]["raw_source_hash"] = "a" * 64
        ready_with_files["assets"][0]["hash"] = "a" * 64
        mismatch = validate_manifest(ready_with_files, root=root, check_paths=True)
        assert any("does not match file bytes" in e for e in mismatch), mismatch

    ready = json.loads(json.dumps(good_blocked))
    ready["status"] = "ready"
    ready["blockers"] = []
    ready["catalog"]["raw_source_hash"] = "a" * 64
    ready["catalog"]["normalized_catalog_hash"] = "b" * 64
    # Source/snapshot still missing => ready must fail.
    ready_errs = validate_manifest(ready, root=root, allow_blocked=False, check_paths=True)
    assert ready_errs, "ready without files should fail"

    print("self-test PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, help="Path to experiments/manifest.json")
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="Accept status=blocked if structure/privacy/rights fields are valid",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]

    if args.self_test:
        return _self_test(root)

    if args.manifest is None:
        parser.error("manifest path is required unless --self-test")

    path = args.manifest
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_file():
        print(f"ERROR: manifest not found: {path}", file=sys.stderr)
        return 2

    try:
        data = _load(path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: cannot parse manifest: {exc}", file=sys.stderr)
        return 2

    errors = validate_manifest(
        data,
        root=root,
        allow_blocked=args.allow_blocked,
        check_paths=True,
    )
    if errors:
        print("INVALID research manifest:")
        for item in errors:
            print(f"- {item}")
        return 1

    status = data.get("status")
    print(f"OK research manifest status={status} allow_blocked={args.allow_blocked}")
    if status == "blocked":
        print("blockers:", ", ".join(data.get("blockers") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
