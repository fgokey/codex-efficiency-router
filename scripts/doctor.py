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

HEADINGS = ("Completion", "Routing", "Delegate")


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


def instruction_chain(skill_file: Path) -> dict[str, str]:
    """Read only local Markdown reachable from the entrypoint's actual links."""
    root = skill_file.parent.resolve()
    pending = [skill_file.resolve()]
    chain = {}
    while pending:
        path = pending.pop()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"reference not packaged with Skill: {path.name}")
        key = path.relative_to(root).as_posix()
        if key in chain:
            continue
        text = path.read_text(encoding="utf-8")
        chain[key] = text
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in link:
                target = (path.parent / link.split("#")[0]).resolve()
                if target.suffix == ".md":
                    pending.append(target)
    return chain


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
    if ('Host mode: compat.' in text) != (profile.host_mode == 'compat'):
        errors.append('Skill host mode does not match manifest/source profile')
    core_bytes = len(text.encode("utf-8"))
    boundaries = (("Actual sandbox/read-only/Hook restrictions prevail", "no new write authority",
                   "deployment/publication needs separate authority") if profile.host_mode == 'compat' else
                  ("Root Astra defaults read-only", "Astra leaves and read-only roles NEVER write",
                   "Unknown identity/effects grant no writes"))
    for required in boundaries:
        if required not in text:
            errors.append(f"missing entry authority boundary: {required}")
    if core_bytes > INSTRUCTION_BUDGETS["core_skill_bytes"]:
        errors.append("Skill exceeds the project core instruction budget")
    full_bytes = core_bytes
    has_astra_preset = "gpt-6-astra" in text
    for reference in sorted((skill_file.parent / "references").rglob("*.md")):
        if not reference.resolve().is_relative_to(skill_file.parent.resolve()):
            errors.append(f"reference escapes Skill: {reference.name}")
            continue
        reference_text = reference.read_text(encoding="utf-8")
        full_bytes += len(reference_text.encode("utf-8")) + 1
        if reference.relative_to(skill_file.parent).as_posix() == "references/effort.md":
            has_astra_preset |= "gpt-6-astra" in reference_text
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
    try:
        chain = instruction_chain(skill_file)
        for name in (() if profile.host_mode == "compat" else
                     ("dispatch", "effort", "quality", "routing")):
            if f"references/{name}.md" not in chain:
                errors.append(f"required policy reference is unreachable: {name}")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    if profile.host_mode == "full" and not has_astra_preset:
        errors.append("missing Astra preset")
    metadata = skill_file.parent / "agents/openai.yaml"
    if not metadata.is_file():
        errors.append("missing UI/invocation metadata")
    for filename, expected in (EXPECTED.items() if profile.host_mode == "full" else ()):
        errors.extend(validate_agent(agent_dir / filename, expected, profile))
    if profile.host_mode == "full" and profile.mode == "auto":
        for filename, expected in AUTO_EXPECTED.items():
            errors.extend(validate_agent(agent_dir / filename, expected, Profile("adaptive")))
    return errors



def instruction_footprint(skill_file: Path, agent_dir: Path, profile: Profile = Profile()) -> dict:
    """Measure validated source text, never infer tokenizer counts or host billing.

    Full text includes the core once and one separator per reference. Role values
    are separate prompts, NOT five agents that necessarily run or a task total.
    Called only by explicit doctor, not on activation, dispatch or tool events.
    """
    core = skill_file.read_text(encoding="utf-8")
    references = {
        p.relative_to(skill_file.parent).as_posix(): len(p.read_text(encoding="utf-8").encode("utf-8"))
        for p in sorted((skill_file.parent / "references").rglob("*.md"))
    }
    roles = dict(EXPECTED) if profile.host_mode == "full" else {}
    if profile.host_mode == "full" and profile.mode == "auto":
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
    for role, model, effort in (EXPECTED.values() if profile.host_mode == "full" else ()):
        required = {effort}
        if profile.mode == "adaptive" and role != "astra_architect":
            required = {"medium", "high"}
        if profile.allow_low and role == "luna_worker":
            required.add("low")
        for value in sorted(required):
            if value not in found.get(model, frozenset()):
                errors.append(f"catalog does not confirm {model}/{value} for {profile.mode}")
    return errors


def source_profiles(root: Path) -> list[dict]:
    from manage import source_files
    from profiles import render_payload
    payload = source_files(root)
    result = []
    for mode in ("fixed", "auto", "adaptive"):
        rendered = render_payload(payload, Profile(mode))
        references = [v for k, v in rendered.items() if k.startswith("skill/references/") and k.endswith(".md")]
        core = len(rendered["skill/SKILL.md"])
        full = core + sum(map(len, references)) + len(references)
        if core > INSTRUCTION_BUDGETS["core_skill_bytes"] or full > INSTRUCTION_BUDGETS["full_skill_bytes"]:
            raise ValueError(f"{mode} rendered instruction budget exceeded")
        result.append({"mode": mode, "core_bytes": core, "full_bytes": full,
                       "margin_bytes": INSTRUCTION_BUDGETS["full_skill_bytes"] - full})
    return result


def target_tests(root: Path) -> dict:
    import contextlib
    import io
    import unittest
    patterns = ("test_doctor.py", "test_instruction_footprint.py", "test_documented_contract.py",
                "test_profiles.py", "test_v070.py")
    if any(not (root / "tests" / name).is_file() for name in patterns):
        raise ValueError("preflight target tests are missing")
    class CountedResult(unittest.TextTestResult):
        passed = 0

        def addSuccess(self, test):
            super().addSuccess(test)
            self.passed += 1

    capture = io.StringIO()
    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
        suite = unittest.TestSuite(unittest.defaultTestLoader.discover(str(root / "tests"), pattern=name)
                                   for name in patterns)
        result = unittest.TextTestRunner(stream=capture, resultclass=CountedResult).run(suite)
    if not result.testsRun:
        raise ValueError("preflight discovered no target tests")
    failures = result.failures + result.errors + [(test, "unexpected success") for test in result.unexpectedSuccesses]
    details = []
    for test, trace in failures[:8]:
        reason = next((line for line in trace.splitlines()
                       if line.startswith(("AssertionError", "ValueError", "ImportError", "unexpected success"))), "test failed")
        details.append({"id": test.id(), "reason": reason[:120]})
    return {"run": result.testsRun, "passed": result.passed, "success": result.wasSuccessful(),
            "skipped": len(result.skipped), "failures": len(result.failures), "errors": len(result.errors),
            "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses),
            "details": details, "omitted_details": max(0, len(failures) - len(details))}


def preflight(root: Path) -> dict:
    if root.resolve() != Path(__file__).resolve().parents[1]:
        raise ValueError("preflight requires this repository's source tree")
    profiles = source_profiles(root)
    tests = target_tests(root)
    report = {"policy": "PASS" if tests["success"] else "FAIL",
              "profiles": profiles, "target_tests": tests, "enforcement": "NOT_VERIFIED",
              "parent_completion": {"router_policy": "INSTRUCTION_ONLY", "native_gate": "UNKNOWN"}}
    while len(json.dumps(report, ensure_ascii=False).encode("utf-8")) + 2 > 3072 and tests["details"]:
        tests["details"].pop()
        tests["omitted_details"] += 1
    return report


def startup_report(profile: Profile, claims: object = None, *, guard: dict | None = None,
                   dispatch_guard: dict | None = None) -> dict:
    """Cheap local facts only. No caller JSON can authenticate a live host binding."""
    if claims is not None and not isinstance(claims, dict):
        raise ValueError('host context must be a JSON object of untrusted claims')
    claims = claims or {}
    declarations = {key: value[:24] if isinstance(value, str) else value
                    if type(value) is bool else 'UNKNOWN'
                    for key in ('model', 'effort', 'permission', 'role_read_only', 'parent_released')
                    for value in (claims.get(key, 'UNKNOWN'),)}
    interfaces = claims.get('interfaces', [])
    if not isinstance(interfaces, list):
        raise ValueError('declared interfaces must be a list')
    declared = [name for name in ('admitted_agent_task', 'prepare_agent_task', 'read_only')
                if name in interfaces]
    def registration(value):
        state = (value or {}).get('registration', 'UNKNOWN')
        return state if state in ('ABSENT', 'PRESENT', 'OUTDATED', 'BROKEN') else 'UNKNOWN'
    return {'status': 'COMPAT' if profile.host_mode == 'compat' else 'BLOCKED',
            'host_mode': profile.host_mode, 'routing_mode': profile.mode,
            'claim_basis': 'CALLER_SUPPLIED_NOT_AUTHENTICATED', 'declarations': declarations,
            'interfaces': {'declared': declared, 'live_availability': 'UNKNOWN'},
            'current_binding': 'UNKNOWN', 'current_permission': 'UNKNOWN', 'release': 'UNKNOWN',
            'write_authority': 'NOT_GRANTED',
            'guard': {'registration': registration(guard), 'dispatch_registration': registration(dispatch_guard),
                      'basis': 'LOCAL_CONFIG_ONLY', 'trust': 'UNKNOWN', 'coverage': 'NOT_LIVE_VERIFIED'},
            'required': ('Current trusted host/tool binding and authorized RELEASE before affected full work.'
                         if profile.host_mode == 'full' else
                         'Compat policy provides planning/context/review; the current executor can continue already '
                         'authorized work within existing host/user authority. Missing model metadata adds no restriction. '
                         'Read-only/Hook restrictions and separate publication authority still apply.'),
            'enforcement': 'NOT_VERIFIED'}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--source-tree", type=Path)
    parser.add_argument("--preflight", action="store_true", help="source profiles and related contract tests; no models/install")
    parser.add_argument("--startup", action="store_true", help="cheap local host capability gaps; no models/tests or write grant")
    parser.add_argument("--host-mode", choices=("full", "compat"), help="explicit startup selection only; does not alter installation")
    parser.add_argument("--host-context", type=Path, help="optional bounded JSON claims, never authenticated host evidence")
    parser.add_argument("--catalog", type=Path, help="exported, fully paginated model/list JSON; no live probing")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.startup:
            if args.preflight or args.catalog:
                parser.error('--startup cannot be combined with --preflight or --catalog')
            profile = Profile()
            guard = dispatch_guard = None
            if not args.source_tree:
                from manage import installed_profile
                from write_guard import inspect_status
                skill_dir, agents, _ = resolve_targets(args.scope, args.project_root)
                profile = installed_profile(skill_dir, agents)
                guard = inspect_status(args.scope, args.project_root)
                dispatch_guard = inspect_status(args.scope, args.project_root, 'dispatch')
            persisted = profile.host_mode
            if args.host_mode:
                from dataclasses import replace
                profile = replace(profile, host_mode=args.host_mode, allow_low=False
                                  if args.host_mode == 'compat' else profile.allow_low)
            claims = None
            if args.host_context:
                with args.host_context.open('rb') as stream:
                    raw = stream.read(16385)
                if len(raw) > 16384:
                    raise ValueError('host context exceeds 16 KiB')
                claims = json.loads(raw)
            report = startup_report(profile, claims, guard=guard, dispatch_guard=dispatch_guard)
            report['persisted_host_mode'] = persisted
            print(json.dumps(report, ensure_ascii=True))
            return int(report['status'] == 'BLOCKED')
        if args.host_mode is not None or args.host_context is not None:
            parser.error('--host-mode/--host-context require --startup')
        if args.preflight:
            if not args.source_tree or args.catalog:
                parser.error("--preflight requires --source-tree and no --catalog")
            report = preflight(args.source_tree.resolve())
            print(json.dumps(report, ensure_ascii=False))
            return int(report["policy"] != "PASS")
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
            from manage import digest, load_manifest, read_bytes, target, required_ownership, installed_defaults
            if not (skill.parent / MANIFEST).exists():
                errors.append("missing ownership manifest; source-only copy or legacy installation")
            else:
                owned = load_manifest(skill.parent, agents)
                installed_defaults(skill.parent, agents)
                missing = required_ownership(profile) - owned.keys()
                if missing:
                    errors.append('incomplete ownership manifest: ' + ', '.join(sorted(missing)))
                for key, expected in owned.items():
                    if digest(read_bytes(target(key, skill.parent, agents))) != expected:
                        errors.append(f"installed file missing or modified: {key}")
        if args.catalog:
            errors.extend(validate_catalog(json.loads(args.catalog.read_text(encoding="utf-8")), profile))
        from release_identity import source_identity
        identity = source_identity(root) if args.source_tree else None
        guard = None
        dispatch_guard = None
        if args.source_tree and (root / "plugin.json").exists():
            from release_package import validate_release
            errors.extend(validate_release(root))
            from manage import source_files
            source_files(root)  # Include the reader and launcher that ordinary Skill installs copy.
        if not args.source_tree:
            from write_guard import inspect_status
            guard = inspect_status(args.scope, args.project_root)
            dispatch_guard = inspect_status(args.scope, args.project_root, 'dispatch')
        footprint = instruction_footprint(skill, agents, profile) if not errors else None
        if args.as_json:
            print(json.dumps({"policy": "FAIL" if errors else "PASS", "errors": errors,
                              "instruction_footprint": footprint,
                              "profile": profile.mode, "automatic_low": profile.allow_low,
                              "host_mode": profile.host_mode,
                              "source_identity": identity, "guard": guard, "dispatch_guard": dispatch_guard,
                              "enforcement": "NOT_VERIFIED", "runtime_loaded_version": "UNKNOWN",
                              "parent_completion": {"router_policy": "INSTRUCTION_ONLY", "native_gate": "UNKNOWN"},
                              "catalog": "EXPORTED_ONLY" if args.catalog else "NOT_CHECKED"}, indent=2))
            return int(bool(errors))
        for error in errors:
            print(f"- {error}")
        print(f"profile: {profile.mode}; automatic low: {profile.allow_low}")
        print("doctor: STATIC FAIL" if errors else "doctor: STATIC PASS")
        # A policy/test pass does not register a Stop handler or assess an open objective.
        print("parent completion: Router instruction policy; native gate: UNKNOWN")
        print("live Codex discovery/model execution: NOT VERIFIED")
        if guard:
            print(f"guard registration: {guard['registration']}; trust: UNKNOWN; enforcement: NOT VERIFIED")
            print(f"dispatch registration: {dispatch_guard['registration']}; trust: UNKNOWN; enforcement: NOT VERIFIED")
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
