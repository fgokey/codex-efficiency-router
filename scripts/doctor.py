#!/usr/bin/env python3
"""Validate source-tree or installed codex-efficiency-router files."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    import tomllib
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Python 3.11+ is required (tomllib missing)") from exc

PROJECT = "codex-efficiency-router"
EXPECTED = {
    "luna-worker.toml": ("luna_worker", "gpt-5.6-luna", "medium"),
    "terra-executor.toml": ("terra_executor", "gpt-5.6-terra", "medium"),
    "sol-engineer.toml": ("sol_engineer", "gpt-5.6-sol", "medium"),
    "astra-architect.toml": ("astra_architect", "gpt-6-astra", "high"),
}


def validate_agent(path: Path, expected: tuple[str, str, str]) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing: {path}"]
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"invalid TOML {path}: {exc}"]

    name, model, effort = expected
    for key, value in (("name", name), ("model", model), ("model_reasoning_effort", effort)):
        if data.get(key) != value:
            errors.append(f"{path}: expected {key}={value!r}, got {data.get(key)!r}")
    if not data.get("description"):
        errors.append(f"{path}: description is required")
    if not data.get("developer_instructions"):
        errors.append(f"{path}: developer_instructions is required")
    return errors


def validate_tree(skill_file: Path, agent_dir: Path) -> list[str]:
    errors: list[str] = []
    if not skill_file.exists():
        errors.append(f"missing: {skill_file}")
    else:
        text = skill_file.read_text(encoding="utf-8")
        if "name: codex-efficiency-router" not in text:
            errors.append(f"{skill_file}: expected Skill name not found")
        if "gpt-6-astra" not in text:
            errors.append(f"{skill_file}: Astra routing rule not found")
    for filename, expected in EXPECTED.items():
        errors.extend(validate_agent(agent_dir / filename, expected))
    return errors


def installed_paths(scope: str, project_root: Path | None) -> tuple[Path, Path]:
    if scope == "user":
        home = Path.home()
        codex_home = Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser()
        return home / ".agents" / "skills" / PROJECT / "SKILL.md", codex_home / "agents"
    root = (project_root or Path.cwd()).resolve()
    return root / ".agents" / "skills" / PROJECT / "SKILL.md", root / ".codex" / "agents"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--source-tree", type=Path, default=None, help="validate a checkout instead of installed files")
    args = parser.parse_args()

    if args.source_tree:
        root = args.source_tree.resolve()
        skill = root / "skills" / PROJECT / "SKILL.md"
        agents = root / "agents"
    else:
        skill, agents = installed_paths(args.scope, args.project_root)

    errors = validate_tree(skill, agents)
    if errors:
        print("doctor: FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("doctor: OK")
    print(f"skill: {skill}")
    print(f"agents: {agents}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
