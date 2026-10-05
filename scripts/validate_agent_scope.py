#!/usr/bin/env python3
"""Validate WIP=1 metadata and per-feature file edit permissions."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import stat
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEATURE_LIST = ROOT / "feature_list.json"
VALID_STATUSES = {"not_started", "in_progress", "blocked", "passing"}
GLOB_CHARS = frozenset("*?[")
LEGACY_PASSING_FEATURE_IDS = {
    "agent-001",
    "chat-001",
    "zalo-001",
    "fridge-001",
    "catalog-002",
    "mcp-001",
}
SKIPPED_DIR_NAMES = {
    ".claude",
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".venv",
    ".vscode",
    "__pycache__",
    "node_modules",
    "tmp",
}
SKIPPED_DIR_PATHS = {".pnpm-store", "backend/data/chroma", "backend/data/trajectories", "frontend/.next"}
SKIPPED_FILE_PATTERNS = ["*.db", "*.db-*", "*.log", "*.pid", "*.pyc", "*.swp", "*.tsbuildinfo", "*~"]

REQUIRED_RULES: dict[str, Any] = {
    "single_active_feature": True,
    "wip_limit": 1,
    "passing_requires_evidence": True,
    "do_not_skip_verification": True,
    "tests_must_pass_before_next_feature": True,
    "unrelated_refactors_forbidden": True,
    "whitelist_required_for_in_progress": True,
    "state_files_always_allowed": ["feature_list.json", "claude-progress.md"],
    "sensitive_files_never_edit": [
        ".env",
        ".env.*",
        "**/.env",
        "**/.env.*",
        "*.pem",
        "**/*.pem",
        "*.key",
        "**/*.key",
        ".git/**",
    ],
    "protected_paths_require_user_approval": [
        "AGENT.md",
        "AGENTS.md",
        "backend/AGENTS.md",
        "frontend/AGENTS.md",
        "scripts/validate_agent_scope.py",
        "init.sh",
        ".github/workflows/**",
        "docker-compose.yml",
        "backend/app/main.py",
        "backend/app/db/**",
        "backend/app/models/**",
        "backend/requirements.txt",
        "frontend/package.json",
        "frontend/package-lock.json",
        "mcp/package.json",
        "mcp/package-lock.json",
    ],
}
RECORDED_PROTECTED_APPROVALS = {
    "harness-001": {
        "AGENT.md",
        "AGENTS.md",
        "init.sh",
        "scripts/validate_agent_scope.py",
    },
    # 2026-08-01: owner approved fixing (a) init.sh's and this script's own
    # Windows-only bugs, and (b) recording after-the-fact approval for 5
    # protected files whose real diffs already existed in the working tree
    # with no approval recorded anywhere (found by an independent audit, see
    # claude-progress.md Sessions 021-023). Owner's exact words in response to
    # that finding: "fix tat ca loi tren di, toi muon chuong trinh final phai
    # khong co loi nao" (fix all the errors above, I want the final program
    # to have zero errors).
    "audit-fix-001": {
        "init.sh",
        "scripts/validate_agent_scope.py",
        "AGENTS.md",
        "backend/app/main.py",
        "backend/app/db/session.py",
        "backend/app/db/sync.py",
        "backend/app/models/entities.py",
    },
    # 2026-08-16: owner approved hoisting the two deferred catalog.repository
    # imports in backend/app/main.py to module top (verified: no import cycle).
    # Owner's exact words: "Phê duyệt, làm đi" (approved, do it), via the
    # AskUserQuestion confirmation during the 2026-08-16 refactor series.
    # This script itself is listed because recording the approval requires
    # editing this dict (same mechanism audit-fix-001 used above).
    "refactor-main-imports-001": {
        "backend/app/main.py",
        "scripts/validate_agent_scope.py",
    },
    # 2026-08-19: owner approved editing this protected script to add .idea,
    # .vscode, and tmp to SKIPPED_DIR_NAMES so the baseline hash walk stops
    # tripping on IDE churn and tmp/ scratch (the recurring stale-baseline /
    # .idea issue from Sessions 028-029), and to record this approval.
    # Owner's approval was captured via AskUserQuestion during the 2026-08-19
    # audit-hygiene reconciliation (scope guard fix, recommendation #3).
    "audit-hygiene-001": {
        "scripts/validate_agent_scope.py",
    },
    # 2026-08-23: owner approved removing the Zalo integration entirely
    # ("xoa sach", AskUserQuestion), which requires protected app/main.py
    # (router wiring), models/entities.py (channel default), both AGENTS.md
    # context files (stale map/commands), and this script to record it.
    "zalo-removal-001": {
        "backend/app/main.py",
        "backend/app/models/entities.py",
        "AGENTS.md",
        "backend/AGENTS.md",
        "scripts/validate_agent_scope.py",
    },
    # 2026-08-23: owner retroactively approved (AskUserQuestion) the missed
    # frontend/AGENTS.md row edit ("Zalo outbox" -> post-removal wording) plus
    # this script edit to record it, during fe-redesign-001 closure.
    "fe-redesign-001": {
        "frontend/AGENTS.md",
        "scripts/validate_agent_scope.py",
    },
    # 2026-10-05: owner approved ("ok fix it", after an exact-path proposal)
    # adding a customer_memories backfill + unique-index migration to the
    # startup paths in backend/app/db/session.py and backend/app/db/sync.py.
    # This script is listed because recording the approval requires editing
    # this dict.
    "memory-unique-index-001": {
        "backend/app/db/session.py",
        "backend/app/db/sync.py",
        "scripts/validate_agent_scope.py",
    },
}


class ScopeError(ValueError):
    pass


def _patterns_match(path: str, patterns: list[str]) -> bool:
    folded_path = path.casefold()
    return any(fnmatch.fnmatchcase(folded_path, pattern.casefold()) for pattern in patterns)


def _same_path(left: str, right: str) -> bool:
    return left == right


def _normalize_path(raw_path: str) -> str:
    if not isinstance(raw_path, str) or not raw_path:
        raise ScopeError("path must be a non-empty string")
    if PureWindowsPath(raw_path).drive:
        raise ScopeError(f"path must be repository-relative: {raw_path}")
    candidate = raw_path.replace("\\", "/")
    path = PurePosixPath(candidate)
    if path.is_absolute() or ".." in path.parts:
        raise ScopeError(f"path must be repository-relative: {raw_path}")
    normalized = path.as_posix()
    if not normalized or normalized == ".":
        raise ScopeError(f"path must name a file: {raw_path}")
    return normalized


def _is_sensitive(path: str, rules: dict[str, Any]) -> bool:
    folded = path.casefold()
    if folded == ".env.example" or folded.endswith("/.env.example"):
        return False
    return _patterns_match(path, rules["sensitive_files_never_edit"])


def _has_glob(path: str) -> bool:
    return any(char in path for char in GLOB_CHARS)


def load_feature_list(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScopeError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ScopeError("feature list root must be an object")
    return data


def _validate_test_evidence(feature: dict[str, Any]) -> None:
    feature_id = feature["id"]
    tests = feature.get("test_evidence")
    if not isinstance(tests, list) or not tests:
        raise ScopeError(f"passing feature {feature_id} requires test_evidence")
    for test in tests:
        if not isinstance(test, dict):
            raise ScopeError(f"feature {feature_id} test_evidence entries must be objects")
        if not isinstance(test.get("command"), str) or not test["command"]:
            raise ScopeError(f"feature {feature_id} test evidence requires command")
        if test.get("result") != "passed":
            raise ScopeError(f"feature {feature_id} has non-passing test evidence")
        if not isinstance(test.get("date"), str) or not test["date"]:
            raise ScopeError(f"feature {feature_id} test evidence requires date")


def validate_metadata(data: dict[str, Any]) -> list[dict[str, Any]]:
    rules = data.get("rules")
    features = data.get("features")
    if not isinstance(rules, dict) or not isinstance(features, list):
        raise ScopeError("feature_list.json requires object 'rules' and array 'features'")

    for key, required_value in REQUIRED_RULES.items():
        if rules.get(key) != required_value:
            raise ScopeError(f"rules.{key} must match the enforced harness policy")

    active = [feature for feature in features if feature.get("status") == "in_progress"]
    if len(active) > REQUIRED_RULES["wip_limit"]:
        ids = ", ".join(str(feature.get("id", "<missing>")) for feature in active)
        raise ScopeError(f"WIP limit exceeded ({len(active)} > 1): {ids}")

    seen_ids: set[str] = set()
    for feature in features:
        feature_id = feature.get("id")
        if not isinstance(feature_id, str) or not feature_id:
            raise ScopeError("every feature requires a non-empty id")
        if feature_id in seen_ids:
            raise ScopeError(f"duplicate feature id: {feature_id}")
        seen_ids.add(feature_id)

        status = feature.get("status")
        if status not in VALID_STATUSES:
            raise ScopeError(f"feature {feature_id} has invalid status: {status}")

        allowed = feature.get("allowed_files")
        governed_passing = status == "passing" and feature_id not in LEGACY_PASSING_FEATURE_IDS
        if (status == "in_progress" or governed_passing) and (
            not isinstance(allowed, list) or not allowed
        ):
            raise ScopeError(f"governed feature {feature_id} requires allowed_files")
        if allowed is not None:
            if not isinstance(allowed, list) or not all(isinstance(value, str) for value in allowed):
                raise ScopeError(f"feature {feature_id} allowed_files must be a string array")
            normalized_allowed = [_normalize_path(value) for value in allowed]
            if any(_has_glob(value) for value in normalized_allowed):
                raise ScopeError(f"feature {feature_id} allowed_files must contain exact file paths")
            if len({value.casefold() for value in normalized_allowed}) != len(normalized_allowed):
                raise ScopeError(f"feature {feature_id} allowed_files contains duplicate paths")
            if any(_is_sensitive(value, rules) for value in normalized_allowed):
                raise ScopeError(f"feature {feature_id} cannot allowlist sensitive files")

        approved = feature.get("approved_protected_files", [])
        if not isinstance(approved, list) or not all(isinstance(value, str) for value in approved):
            raise ScopeError(f"feature {feature_id} approved_protected_files must be a string array")
        normalized_approved = [_normalize_path(value) for value in approved]
        if any(_has_glob(value) for value in normalized_approved):
            raise ScopeError(f"feature {feature_id} protected approvals must be exact paths")
        for path in normalized_approved:
            if path not in RECORDED_PROTECTED_APPROVALS.get(feature_id, set()):
                raise ScopeError(f"feature {feature_id} has no recorded user approval for: {path}")
            if not _patterns_match(path, rules["protected_paths_require_user_approval"]):
                raise ScopeError(f"feature {feature_id} approval is not a protected path: {path}")
            if not isinstance(allowed, list) or not any(
                _same_path(path, _normalize_path(item)) for item in allowed
            ):
                raise ScopeError(f"feature {feature_id} approved path is not allowlisted: {path}")

        if status == "passing":
            evidence = feature.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                raise ScopeError(f"passing feature {feature_id} requires evidence")
            if governed_passing:
                _validate_test_evidence(feature)

    return active


def _select_active_feature(
    data: dict[str, Any], feature_id: str | None = None
) -> dict[str, Any]:
    active = validate_metadata(data)
    if len(active) != 1:
        raise ScopeError("checking files requires exactly one in-progress feature")
    feature = active[0]
    if feature_id is not None and feature["id"] != feature_id:
        raise ScopeError(f"feature {feature_id} is not the active feature")
    return feature


def validate_files(data: dict[str, Any], feature_id: str | None, raw_paths: list[str]) -> list[str]:
    feature = _select_active_feature(data, feature_id)
    rules = data["rules"]
    allowed = [_normalize_path(path) for path in feature["allowed_files"]]
    approved = [_normalize_path(path) for path in feature.get("approved_protected_files", [])]
    state_files = [_normalize_path(path) for path in rules["state_files_always_allowed"]]

    normalized_paths = [_normalize_path(path) for path in raw_paths]
    for path in normalized_paths:
        if _is_sensitive(path, rules):
            raise ScopeError(f"sensitive file is never editable: {path}")

        state_file = any(_same_path(path, item) for item in state_files)
        if not state_file and not any(_same_path(path, item) for item in allowed):
            raise ScopeError(f"file is outside feature {feature['id']} whitelist: {path}")

        if _patterns_match(path, rules["protected_paths_require_user_approval"]):
            if not any(_same_path(path, item) for item in approved):
                raise ScopeError(f"protected file lacks explicit approval: {path}")

    return normalized_paths


def _baseline_path() -> Path:
    git_path = ROOT / ".git"
    if git_path.is_dir():
        return git_path / "agent-scope-baseline.json"
    if git_path.is_file():
        marker = "gitdir:"
        content = git_path.read_text(encoding="utf-8").strip()
        if not content.casefold().startswith(marker):
            raise ScopeError("cannot resolve worktree git directory")
        directory = Path(content[len(marker) :].strip())
        return (directory if directory.is_absolute() else ROOT / directory) / "agent-scope-baseline.json"
    raise ScopeError("session baseline requires a Git worktree")


def _baseline_sentinel_path() -> Path:
    return _baseline_path().with_name("agent-scope-baseline-required")


def _hash_file(path: Path, *, include_metadata: bool = True) -> str:
    digest = hashlib.sha256()
    if include_metadata:
        mode = stat.S_IMODE(path.lstat().st_mode)
        digest.update(f"mode:{mode:o}\0".encode("ascii"))
    if path.is_symlink():
        if include_metadata:
            digest.update(b"symlink\0")
        digest.update(os.readlink(path).encode("utf-8"))
        return digest.hexdigest()
    if include_metadata:
        digest.update(b"file\0")
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_hashes(rules: dict[str, Any], *, include_metadata: bool = True) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for current_root, dirnames, filenames in os.walk(ROOT):
        current = Path(current_root)
        symlink_dirs = [name for name in dirnames if (current / name).is_symlink()]
        for name in symlink_dirs:
            path = current / name
            relative = _normalize_path(path.relative_to(ROOT).as_posix())
            hashes[relative] = _hash_file(path, include_metadata=include_metadata)
        dirnames[:] = [
            name
            for name in dirnames
            if name not in symlink_dirs
            and name.casefold() not in {item.casefold() for item in SKIPPED_DIR_NAMES}
            and (current / name).relative_to(ROOT).as_posix() not in SKIPPED_DIR_PATHS
        ]
        for filename in filenames:
            if _patterns_match(filename, SKIPPED_FILE_PATTERNS):
                continue
            path = current / filename
            relative = _normalize_path(path.relative_to(ROOT).as_posix())
            # Sensitive files (.env, *.pem, *.key, ...) can never be agent-
            # editable regardless of feature (validate_files always rejects
            # them), so there is no scope-compliance question their hash
            # could ever answer. Excluding them here (2026-08-01) means a
            # legitimate non-agent change — secrets rotation, local .env
            # setup — can no longer permanently brick --start-session /
            # --check-session with an unrecoverable "sensitive file is never
            # editable" error. validate_files() still independently rejects
            # any sensitive path if it is ever explicitly passed via
            # --check-files or recorded in session_changed_paths.
            if _is_sensitive(relative, rules):
                continue
            if path.is_file() or path.is_symlink():
                hashes[relative] = _hash_file(path, include_metadata=include_metadata)

    git_dir = _baseline_path().parent
    git_sensitive = [git_dir / "config", git_dir / "info" / "exclude"]
    hooks_dir = git_dir / "hooks"
    if hooks_dir.is_dir():
        git_sensitive.extend(path for path in hooks_dir.iterdir() if path.is_file())
    for path in git_sensitive:
        if path.is_file() or path.is_symlink():
            relative = f".git/{path.relative_to(git_dir).as_posix()}"
            hashes[relative] = _hash_file(path, include_metadata=include_metadata)
    return hashes


def _scope_snapshot(data: dict[str, Any], feature: dict[str, Any]) -> dict[str, Any]:
    return {
        "rules": data["rules"],
        "features": [feature],
    }


def _read_baseline() -> dict[str, Any] | None:
    path = _baseline_path()
    sentinel = _baseline_sentinel_path()
    if not path.exists():
        if sentinel.exists():
            raise ScopeError("session baseline was removed or replaced")
        return None
    try:
        content = path.read_text(encoding="utf-8")
        if sentinel.exists():
            expected = sentinel.read_text(encoding="utf-8").strip()
            actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if expected != actual:
                raise ScopeError("session baseline integrity check failed")
        baseline = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        raise ScopeError(f"cannot read session baseline: {exc}") from exc
    if not isinstance(baseline, dict) or baseline.get("version") != 3:
        raise ScopeError("invalid session baseline")
    if not sentinel.exists():
        raise ScopeError("session baseline sentinel is missing")
    return baseline


def _write_baseline(baseline: dict[str, Any]) -> None:
    path = _baseline_path()
    sentinel = _baseline_sentinel_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(baseline, indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")
    sentinel.write_text(hashlib.sha256(content.encode("utf-8")).hexdigest() + "\n", encoding="utf-8")


def _changed_since_baseline(baseline: dict[str, Any]) -> list[str]:
    old_hashes = baseline.get("file_hashes")
    scope = baseline.get("scope")
    if not isinstance(old_hashes, dict) or not isinstance(scope, dict):
        raise ScopeError("invalid session baseline contents")
    current_hashes = _repo_hashes(scope["rules"])
    changed = {
        path
        for path in set(old_hashes) | set(current_hashes)
        if old_hashes.get(path) != current_hashes.get(path)
    }
    changed.update(baseline.get("session_changed_paths", []))
    return sorted(changed)


def check_session(data: dict[str, Any]) -> list[str]:
    validate_metadata(data)
    baseline = _read_baseline()
    if baseline is None:
        raise ScopeError("no session baseline; run --start-session after selecting a feature")

    scope = baseline.get("scope")
    feature_id = baseline.get("feature_id")
    if not isinstance(scope, dict) or not isinstance(feature_id, str):
        raise ScopeError("invalid session baseline scope")
    changed = _changed_since_baseline(baseline)
    validate_files(scope, feature_id, changed)

    current_feature = next(
        (feature for feature in data["features"] if feature.get("id") == feature_id), None
    )
    if current_feature is None:
        raise ScopeError(f"baseline feature was removed: {feature_id}")
    if current_feature.get("status") == "passing":
        _validate_test_evidence(current_feature)
    elif current_feature.get("status") != "in_progress":
        raise ScopeError(f"baseline feature {feature_id} is neither in_progress nor passing")
    return changed


def accept_external_changes(data: dict[str, Any], raw_paths: list[str]) -> list[str]:
    feature = _select_active_feature(data)
    baseline = _read_baseline()
    if baseline is None:
        raise ScopeError("no session baseline; external changes cannot be accepted")
    if baseline.get("feature_id") != feature["id"]:
        raise ScopeError("external changes must be accepted by the baseline feature")

    scope = baseline["scope"]
    rules = scope["rules"]
    paths = [_normalize_path(path) for path in raw_paths]
    for path in paths:
        if _is_sensitive(path, rules):
            raise ScopeError(f"sensitive external change cannot be accepted: {path}")
        if _patterns_match(path, rules["protected_paths_require_user_approval"]):
            raise ScopeError(f"protected external change cannot be accepted: {path}")

    current_hashes = _repo_hashes(rules)
    for path in paths:
        if path not in current_hashes:
            raise ScopeError(f"external file does not exist: {path}")
        baseline["file_hashes"][path] = current_hashes[path]
    baseline["accepted_external_paths"] = sorted(
        set(baseline.get("accepted_external_paths", [])) | set(paths)
    )
    _write_baseline(baseline)
    return paths


def start_session(data: dict[str, Any]) -> tuple[str | None, list[str]]:
    active = validate_metadata(data)
    previous = _read_baseline()
    previous_changes = check_session(data) if previous is not None else []
    if not active:
        return None, previous_changes

    feature = active[0]
    if previous is not None and previous.get("feature_id") == feature["id"]:
        previous_feature = previous["scope"]["features"][0]
        previous_approved = [
            _normalize_path(path) for path in previous_feature.get("approved_protected_files", [])
        ]
        current_approved = [
            _normalize_path(path) for path in feature.get("approved_protected_files", [])
        ]
        if previous_approved != current_approved:
            raise ScopeError("protected-file approvals cannot change after session start")
        previous["version"] = 3
        previous["file_hashes"] = _repo_hashes(data["rules"])
        previous["session_changed_paths"] = sorted(
            set(previous.get("session_changed_paths", [])) | set(previous_changes)
        )
        previous["scope"] = _scope_snapshot(data, feature)
        _write_baseline(previous)
        return feature["id"], previous_changes

    if previous is not None:
        previous_feature = next(
            (item for item in data["features"] if item.get("id") == previous.get("feature_id")), None
        )
        if previous_feature is None or previous_feature.get("status") != "passing":
            raise ScopeError("cannot start another feature before the previous feature passes")

    baseline = {
        "version": 3,
        "feature_id": feature["id"],
        "scope": _scope_snapshot(data, feature),
        "file_hashes": _repo_hashes(data["rules"]),
        "session_changed_paths": [],
    }
    _write_baseline(baseline)
    return feature["id"], previous_changes


def _expect_scope_error(label: str, message: str, call) -> None:
    try:
        call()
    except ScopeError as exc:
        if message not in str(exc):
            raise AssertionError(f"{label} rejected for wrong reason: {exc}") from exc
        return
    raise AssertionError(f"self-test expected rejection: {label}")


def _expect_rejected(data: dict[str, Any], path: str, message: str) -> None:
    _expect_scope_error(path, message, lambda: validate_files(data, None, [path]))


def run_self_test() -> None:
    data = {
        "rules": json.loads(json.dumps(REQUIRED_RULES)),
        "features": [
            {
                "id": "harness-001",
                "status": "in_progress",
                "allowed_files": [
                    "src/feature.py",
                    ".env.example",
                    "AGENTS.md",
                    "backend/app/main.py",
                ],
                "approved_protected_files": ["AGENTS.md"],
                "evidence": [],
            }
        ],
    }

    validate_metadata(data)
    validate_files(data, None, ["src/feature.py", ".env.example", "feature_list.json", "AGENTS.md"])
    _expect_rejected(data, "agents.md", "outside")
    _expect_rejected(data, ".env", "sensitive file")
    _expect_rejected(data, "src/unrelated.py", "outside")
    _expect_rejected(data, "backend/app/main.py", "lacks explicit approval")
    _expect_rejected(data, "C:\\repo\\file.txt", "repository-relative")
    _expect_rejected(data, "../outside.txt", "repository-relative")

    inactive = json.loads(json.dumps(data))
    inactive["features"][0].update(
        {
            "status": "passing",
            "evidence": ["verified"],
            "test_evidence": [{"command": "test", "result": "passed", "date": "2026-07-24"}],
        }
    )
    _expect_scope_error(
        "inactive feature",
        "requires exactly one in-progress feature",
        lambda: validate_files(inactive, "harness-001", ["src/feature.py"]),
    )

    wildcard = json.loads(json.dumps(data))
    wildcard["features"][0]["approved_protected_files"] = ["**"]
    _expect_scope_error(
        "wildcard approval", "must be exact paths", lambda: validate_metadata(wildcard)
    )

    failed_tests = json.loads(json.dumps(inactive))
    failed_tests["features"][0]["test_evidence"][0]["result"] = "failed"
    _expect_scope_error(
        "failed test evidence", "non-passing test evidence", lambda: validate_metadata(failed_tests)
    )

    stripped_scope = json.loads(json.dumps(inactive))
    stripped_scope["features"][0].pop("allowed_files")
    stripped_scope["features"][0].pop("approved_protected_files")
    _expect_scope_error(
        "governed passing scope",
        "requires allowed_files",
        lambda: validate_metadata(stripped_scope),
    )

    windows_spelling = json.loads(json.dumps(data))
    windows_spelling["features"][0]["allowed_files"][0] = "src\\feature.py"
    validate_metadata(windows_spelling)
    validate_files(windows_spelling, None, ["src/feature.py"])

    two_active = json.loads(json.dumps(data))
    two_active["features"].append(
        {"id": "test-002", "status": "in_progress", "allowed_files": ["src/other.py"], "evidence": []}
    )
    _expect_scope_error(
        "two active features", "WIP limit exceeded", lambda: validate_metadata(two_active)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature_list", nargs="?", type=Path, default=DEFAULT_FEATURE_LIST)
    parser.add_argument("--feature-id", help="Assert the expected active feature")
    parser.add_argument("--check-files", nargs="*", default=[], metavar="PATH")
    parser.add_argument("--accept-external-files", nargs="*", default=[], metavar="PATH")
    parser.add_argument("--start-session", action="store_true")
    parser.add_argument("--check-session", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.self_test:
            run_self_test()
            print("agent scope self-test: PASS")
            return 0

        feature_list_path = args.feature_list
        if not feature_list_path.is_absolute():
            feature_list_path = ROOT / feature_list_path
        data = load_feature_list(feature_list_path)
        active = validate_metadata(data)
        checked = validate_files(data, args.feature_id, args.check_files) if args.check_files else []
        accepted_external = (
            accept_external_changes(data, args.accept_external_files)
            if args.accept_external_files
            else []
        )
        session_changes: list[str] = []
        if args.check_session:
            session_changes = check_session(data)
        if args.start_session:
            feature_id, previous_changes = start_session(data)
            print(
                f"agent scope session: STARTED (feature={feature_id or 'none'}, "
                f"previous_changes={len(previous_changes)})"
            )
    except (AssertionError, KeyError, ScopeError) as exc:
        print(f"agent scope validation: FAIL: {exc}", file=sys.stderr)
        return 1

    active_ids = ", ".join(feature["id"] for feature in active) or "none"
    print(
        f"agent scope validation: PASS (active={active_ids}, checked_files={len(checked)}, "
        f"session_changes={len(session_changes)}, accepted_external={len(accepted_external)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
