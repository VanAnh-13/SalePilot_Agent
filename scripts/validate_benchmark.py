#!/usr/bin/env python3
"""Validate SalePilot-R benchmark JSONL episodes against the frozen schema."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "experiments" / "benchmark" / "schema.json"
DEFAULT_MANIFEST = ROOT / "experiments" / "manifest.json"
PII_RE = re.compile(r"(?:0\d{8,10}|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.I)


def _type_matches(value: Any, expected: str) -> bool:
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return checks.get(expected, lambda _item: False)(value)


def _schema_errors(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validate the JSON Schema subset used by ``benchmark/schema.json``.

    Keeping this small avoids adding a runtime dependency solely for a CLI
    gate, while still making the checked-in schema the executable contract.
    """
    errors: list[str] = []
    declared_type = schema.get("type")
    allowed_types = declared_type if isinstance(declared_type, list) else [declared_type]
    allowed_types = [item for item in allowed_types if isinstance(item, str)]
    if allowed_types and not any(_type_matches(value, item) for item in allowed_types):
        return [f"{path}: expected type {'|'.join(allowed_types)}"]

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in {schema['enum']}")

    if isinstance(value, str) and len(value) < int(schema.get("minLength") or 0):
        errors.append(f"{path}: string shorter than minLength={schema['minLength']}")
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems") or 0):
            errors.append(f"{path}: array shorter than minItems={schema['minItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_schema_errors(item, item_schema, f"{path}[{index}]"))
    if isinstance(value, (int, float)) and not isinstance(value, bool) and "minimum" in schema:
        if value < schema["minimum"]:
            errors.append(f"{path}: value below minimum={schema['minimum']}")
    if isinstance(value, dict):
        properties = schema.get("properties") or {}
        required = schema.get("required") or []
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unknown property {key!r}")
        for key, item in value.items():
            child_schema = properties.get(key)
            if isinstance(child_schema, dict):
                errors.extend(_schema_errors(item, child_schema, f"{path}.{key}"))
    return errors


def _load_object(path: Path, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.is_file():
        return None, [f"{label} missing: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{label} invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, [f"{label} root must be an object"]
    return payload, []


def validate_file(
    path: Path,
    manifest_path: Path | None = None,
    schema_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    counts: Counter[str] = Counter()
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return ["empty benchmark file"]

    schema, schema_load_errors = _load_object(schema_path or DEFAULT_SCHEMA, "benchmark schema")
    errors.extend(schema_load_errors)
    if schema is None:
        return errors

    allowed_cats: set[str] | None = None
    if manifest_path is not None:
        manifest, manifest_errors = _load_object(manifest_path, "research manifest")
        errors.extend(manifest_errors)
        if manifest is not None:
            catalog = manifest.get("catalog") or {}
            categories = catalog.get("categories")
            if not isinstance(categories, list) or not categories or not all(isinstance(item, str) for item in categories):
                errors.append("research manifest catalog.categories must be a non-empty string list")
            else:
                allowed_cats = set(categories)
                expected_count = catalog.get("expected_categories")
                if isinstance(expected_count, int) and len(allowed_cats) != expected_count:
                    errors.append(
                        "research manifest category count mismatch: "
                        f"expected {expected_count}, listed {len(allowed_cats)}"
                    )

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            episode = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid json ({exc})")
            continue

        shape_errors = _schema_errors(episode, schema)
        errors.extend(f"line {line_number}: {item}" for item in shape_errors)
        if not isinstance(episode, dict):
            continue

        episode_id = episode.get("episode_id")
        if isinstance(episode_id, str):
            if episode_id in ids:
                errors.append(f"line {line_number}: duplicate episode_id {episode_id}")
            ids.add(episode_id)

        category = episode.get("category")
        if category is not None and allowed_cats is not None and category not in allowed_cats:
            errors.append(f"line {line_number}: category {category!r} not declared in research manifest")

        turns = episode.get("turns")
        if isinstance(turns, list):
            for turn in turns:
                if not isinstance(turn, dict):
                    continue
                text = turn.get("text")
                if isinstance(text, str) and PII_RE.search(text):
                    errors.append(f"line {line_number}: possible PII in turn text")

        action = episode.get("expected_action", "?")
        split = episode.get("split")
        counts[str(action)] += 1
        counts[f"split:{split}"] += 1
        if category:
            counts[f"cat:{category}"] += 1

    if len(ids) < 16:
        errors.append(f"expected >=16 episodes for tracer pilot, found {len(ids)}")

    print("distribution:")
    for key, value in sorted(counts.items()):
        print(f"  {key}: {value}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()
    path = args.benchmark if args.benchmark.is_absolute() else (Path.cwd() / args.benchmark).resolve()
    manifest = args.manifest if args.manifest.is_absolute() else (Path.cwd() / args.manifest).resolve()
    schema = args.schema if args.schema.is_absolute() else (Path.cwd() / args.schema).resolve()
    if not path.is_file():
        print(f"ERROR missing {path}", file=sys.stderr)
        return 2
    errors = validate_file(path, manifest, schema)
    if errors:
        print("INVALID benchmark:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OK benchmark {path} episodes_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
