#!/usr/bin/env python3
"""Static integrity/preset checks plus optional exported Codex model/list validation.

Does not start Codex, spend model tokens, read credentials or prove live routing.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError as exc:
    raise SystemExit("Python 3.11+ is required") from exc

from package import (AUTO_DESCRIPTION_PREFIX, EXPECTED, AUTO_EXPECTED, INSTRUCTION_BUDGETS,
                     MANIFEST, PROJECT, resolve_targets)
from profiles import Profile, MARKER
from catalog import parse_catalog

HEADINGS = ("Route once per meaningful decision", "Decide whether delegation is worth it",
            "Handoff without losing the decision", "Failure, validation, and stopping", "Context and reporting")


def validate_agent(path: Path, expected: tuple[str, str, str], profile: Profile = Profile()) -> list[str]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"invalid or missing agent {path}: {exc}"]
    errors = []
    for key, value in zip(("name", "model"), expected[:2]):
        if data.get(key) != value:
            errors.append(f"{path}: shipped preset expects {key}={value!r}")
    if profile.mode in ("fixed", "auto") and data.get("model_reasoning_effort") != expected[2]:
        errors.append(f"{path}: fixed preset expects model_reasoning_effort={expected[2]!r}")
    if profile.mode == "adaptive" and "model_reasoning_effort" in data:
        errors.append(f"{path}: adaptive role must not pin model_reasoning_effort")
    for key in ("description", "developer_instructions"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"{path}: nonempty {key} is required")
    if expected[0].startswith("cer_auto_") and not data.get("description", "").startswith(AUTO_DESCRIPTION_PREFIX):
        errors.append(f"{path}: auto binding description must expose explicit effort selection")
    instructions = data.get("developer_instructions")
    if (isinstance(instructions, str)
            and len(instructions.encode("utf-8")) > INSTRUCTION_BUDGETS["role_developer_instruction_bytes"]):
        errors.append(f"{path}: role instructions exceed the project instruction budget")
    if expected[0] in ("astra_architect", "cer_auto_astra_architect") and data.get("sandbox_mode") != "read-only":
        errors.append(f"{path}: architect must remain read-only")
    return errors


def validate_tree(skill_file: Path, agent_dir: Path, profile: Profile = Profile()) -> list[str]:
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
    expected_marker = (profile.mode, "enabled" if profile.allow_low else "disabled")
    if MARKER.findall(text) != [expected_marker]:
        errors.append("Skill installation marker does not match manifest/source profile")
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
        errors.extend(validate_agent(agent_dir / filename, expected, profile))
    if profile.mode == "auto":
        for filename, expected in AUTO_EXPECTED.items():
            errors.extend(validate_agent(agent_dir / filename, expected, Profile("adaptive")))
    return errors



def instruction_footprint(skill_file: Path, agent_dir: Path, profile: Profile = Profile()) -> dict:
    """Measure validated source text, never infer tokenizer counts or host billing.

    Full text includes the core once and one separator per reference. Role values
    are separate prompts, NOT four agents that necessarily run or a task total.
    Called only by explicit doctor, not on activation, dispatch or tool events.
    """
    core = skill_file.read_text(encoding="utf-8")
    references = {
        p.relative_to(skill_file.parent).as_posix(): len(p.read_text(encoding="utf-8").encode("utf-8"))
        for p in sorted((skill_file.parent / "references").rglob("*.md"))
    }
    roles = dict(EXPECTED)
    if profile.mode == "auto":
        roles.update(AUTO_EXPECTED)
    role_bytes = {
        name: len(tomllib.loads((agent_dir / name).read_text(encoding="utf-8"))[
            "developer_instructions"].encode("utf-8"))
        for name in roles
    }
    description = next(line.removeprefix("description: ") for line in core.splitlines()
                       if line.startswith("description: "))
    return {
        "basis": "UTF-8 source text; excludes host framing, history, tools and billing",
        "core_skill_bytes": len(core.encode("utf-8")),
        "reference_bytes": references,
        "reference_separator_bytes": len(references),
        "full_skill_bytes": len(core.encode("utf-8")) + sum(references.values()) + len(references),
        "description_characters": len(description),
        "role_developer_instruction_bytes": role_bytes,
        "budgets": dict(INSTRUCTION_BUDGETS),
        "token_counts": "NOT_MEASURED",
        "whole_task_savings": "NOT_MEASURED",
    }


def validate_catalog(data: object, profile: Profile = Profile()) -> list[str]:
    try:
        found = parse_catalog(data)
    except ValueError as exc:
        return [str(exc)]
    errors = []
    for role, model, effort in EXPECTED.values():
        required = {effort}
        if profile.mode == "adaptive" and role != "astra_architect":
            required = {"medium", "high"}
        if profile.allow_low and role == "luna_worker":
            required.add("low")
        for value in sorted(required):
            if value not in found.get(model, frozenset()):
                errors.append(f"catalog does not confirm {model}/{value} for {profile.mode}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--source-tree", type=Path)
    parser.add_argument("--catalog", type=Path, help="exported, fully paginated model/list JSON; no live probing")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        profile = Profile()
        if args.source_tree:
            root = args.source_tree.resolve()
            skill, agents = root / "skills" / PROJECT / "SKILL.md", root / "agents"
        else:
            skill_dir, agents, _ = resolve_targets(args.scope, args.project_root)
            skill = skill_dir / "SKILL.md"
            from manage import installed_profile
            profile = installed_profile(skill_dir, agents)
        errors = validate_tree(skill, agents, profile)
        if not args.source_tree:
            from manage import digest, load_manifest, read_bytes, target
            if not (skill.parent / MANIFEST).exists():
                errors.append("missing ownership manifest; source-only copy or legacy installation")
            else:
                for key, expected in load_manifest(skill.parent, agents).items():
                    if digest(read_bytes(target(key, skill.parent, agents))) != expected:
                        errors.append(f"installed file missing or modified: {key}")
        if args.catalog:
            errors.extend(validate_catalog(json.loads(args.catalog.read_text(encoding="utf-8")), profile))
        from release_identity import source_identity
        identity = source_identity(root) if args.source_tree else None
        guard = None
        if args.source_tree and (root / "plugin.json").exists():
            from release_package import validate_release
            errors.extend(validate_release(root))
        if not args.source_tree:
            from write_guard import inspect_status
            guard = inspect_status(args.scope, args.project_root)
        footprint = instruction_footprint(skill, agents, profile) if not errors else None
        if args.as_json:
            print(json.dumps({"policy": "FAIL" if errors else "PASS", "errors": errors,
                              "instruction_footprint": footprint,
                              "profile": profile.mode, "automatic_low": profile.allow_low,
                              "source_identity": identity, "guard": guard,
                              "enforcement": "NOT_VERIFIED", "runtime_loaded_version": "UNKNOWN",
                              "catalog": "EXPORTED_ONLY" if args.catalog else "NOT_CHECKED"}, indent=2))
            return int(bool(errors))
        for error in errors:
            print(f"- {error}")
        print(f"profile: {profile.mode}; automatic low: {profile.allow_low}")
        print("doctor: STATIC FAIL" if errors else "doctor: STATIC PASS")
        print("live Codex discovery/model execution: NOT VERIFIED")
        if guard:
            print(f"guard registration: {guard['registration']}; trust: UNKNOWN; enforcement: NOT VERIFIED")
        print("catalog: checked supplied export only" if args.catalog else "catalog: NOT CHECKED")
        return int(bool(errors))
    except (OSError, ValueError, TypeError) as exc:
        if args.as_json:
            print(json.dumps({"policy": "FAIL", "errors": [str(exc)], "enforcement": "NOT_VERIFIED"}))
        else:
            print(f"doctor: STATIC FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
