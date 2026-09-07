#!/usr/bin/env python3
"""Static integrity/preset checks plus optional exported Codex model/list validation.

Does not start Codex, spend model tokens, read credentials or prove live routing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError as exc:
    raise SystemExit("Python 3.11+ is required") from exc

from package import EXPECTED, INSTRUCTION_BUDGETS, MANIFEST, PROJECT, resolve_targets

HEADINGS = ("Route once per meaningful decision", "Decide whether delegation is worth it",
            "Handoff without losing the decision", "Failure, validation, and stopping", "Context and reporting")


def validate_agent(path: Path, expected: tuple[str, str, str]) -> list[str]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"invalid or missing agent {path}: {exc}"]
    errors = []
    for key, value in zip(("name", "model", "model_reasoning_effort"), expected):
        if data.get(key) != value:
            errors.append(f"{path}: shipped preset expects {key}={value!r}")
    for key in ("description", "developer_instructions"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"{path}: nonempty {key} is required")
    if expected[0] == "astra_architect" and data.get("sandbox_mode") != "read-only":
        errors.append(f"{path}: architect must remain read-only")
    return errors


def validate_tree(skill_file: Path, agent_dir: Path) -> list[str]:
    errors = []
    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"missing Skill: {exc}"]
    parts = text.split("---\n", 2)
    if len(parts) != 3 or parts[0]:
        errors.append("Skill requires opening and closing YAML frontmatter")
    else:
        # This package deliberately uses only two plain, single-line YAML scalars.
        # Reject ambiguous YAML instead of treating a broken description as loaded.
        meta = {}
        for line in parts[1].splitlines():
            if not line.strip():
                continue
            key, separator, value = line.partition(": ")
            if (key not in ("name", "description") or not separator or key in meta
                    or not value or not value[0].isalnum() or ": " in value
                    or " #" in value or "\t" in value):
                errors.append("package frontmatter requires unique plain single-line name/description scalars")
                continue
            meta[key] = value
        if meta.get("name") != PROJECT or not meta.get("description"):
            errors.append("Skill name/description are missing or invalid")
        if len(meta.get("description", "")) > INSTRUCTION_BUDGETS["discovery_description_characters"]:
            errors.append("Skill description exceeds the project discovery budget")
    core_bytes = len(text.encode("utf-8"))
    if core_bytes > INSTRUCTION_BUDGETS["core_skill_bytes"]:
        errors.append("Skill exceeds the project core instruction budget")
    full_bytes = core_bytes
    for reference in sorted((skill_file.parent / "references").rglob("*.md")):
        if not reference.resolve().is_relative_to(skill_file.parent.resolve()):
            errors.append(f"reference escapes Skill: {reference.name}")
            continue
        full_bytes += len(reference.read_text(encoding="utf-8").encode("utf-8")) + 1
    if full_bytes > INSTRUCTION_BUDGETS["full_skill_bytes"]:
        errors.append("core plus ALL references exceeds the project full instruction budget")
    for heading in HEADINGS:
        if f"## {heading}" not in text:
            errors.append(f"missing policy section: {heading}")
    for link in re.findall(r"\]\(([^)]+)\)", text):
        if "://" not in link:
            path = (skill_file.parent / link.split("#")[0]).resolve()
            if not path.is_relative_to(skill_file.parent.resolve()) or not path.is_file():
                errors.append(f"reference not packaged with Skill: {link}")
    if "gpt-6-astra" not in text:
        errors.append("missing Astra preset")
    metadata = skill_file.parent / "agents/openai.yaml"
    if not metadata.is_file():
        errors.append("missing UI/invocation metadata")
    for filename, expected in EXPECTED.items():
        errors.extend(validate_agent(agent_dir / filename, expected))
    return errors


def validate_catalog(data: dict) -> list[str]:
    if not isinstance(data, dict):
        return ["expected a model/list JSON object"]
    payload = data.get("result", data)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return ["expected exported Codex model/list JSON object with a data array"]
    if payload.get("nextCursor") is not None:
        return ["catalog export is incomplete: follow pagination before assessing availability"]
    found = {}
    for entry in payload["data"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("supportedReasoningEfforts"), list):
            return ["invalid model catalog entry"]
        if not isinstance(entry.get("model"), str):
            return ["catalog model must be a string"]
        found[entry["model"]] = {e.get("reasoningEffort") for e in entry["supportedReasoningEfforts"] if isinstance(e, dict)}
    return [f"catalog does not confirm {model}/{effort}"
            for _, model, effort in EXPECTED.values() if effort not in found.get(model, set())]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--source-tree", type=Path)
    parser.add_argument("--catalog", type=Path, help="exported, fully paginated model/list JSON; no live probing")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.source_tree:
            root = args.source_tree.resolve()
            skill, agents = root / "skills" / PROJECT / "SKILL.md", root / "agents"
        else:
            skill_dir, agents, _ = resolve_targets(args.scope, args.project_root)
            skill = skill_dir / "SKILL.md"
        errors = validate_tree(skill, agents)
        if not args.source_tree:
            from manage import digest, load_manifest, read_bytes, target
            if not (skill.parent / MANIFEST).exists():
                errors.append("missing ownership manifest; source-only copy or legacy installation")
            else:
                for key, expected in load_manifest(skill.parent, agents).items():
                    if digest(read_bytes(target(key, skill.parent, agents))) != expected:
                        errors.append(f"installed file missing or modified: {key}")
        if args.catalog:
            errors.extend(validate_catalog(json.loads(args.catalog.read_text(encoding="utf-8"))))
        for error in errors:
            print(f"- {error}")
        print("doctor: STATIC FAIL" if errors else "doctor: STATIC PASS")
        print("live Codex discovery/model execution: NOT VERIFIED")
        print("catalog: checked supplied export only" if args.catalog else "catalog: NOT CHECKED")
        return int(bool(errors))
    except (OSError, ValueError, TypeError) as exc:
        print(f"doctor: STATIC FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
