#!/usr/bin/env python3
"""Install codex-efficiency-router without modifying Codex config.toml."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT = "codex-efficiency-router"
AGENT_FILES = [
    "luna-worker.toml",
    "terra-executor.toml",
    "sol-engineer.toml",
    "astra-architect.toml",
]


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_targets(scope: str, project_root: Path | None) -> tuple[Path, Path, Path]:
    if scope == "user":
        home = Path.home()
        codex_home = Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser()
        skill_dir = home / ".agents" / "skills" / PROJECT
        agent_dir = codex_home / "agents"
        backup_root = codex_home / "backups" / PROJECT
        return skill_dir, agent_dir, backup_root

    root = (project_root or Path.cwd()).resolve()
    skill_dir = root / ".agents" / "skills" / PROJECT
    agent_dir = root / ".codex" / "agents"
    backup_root = root / ".codex-router-local" / "backups"
    return skill_dir, agent_dir, backup_root


def backup_existing(skill_dir: Path, agent_dir: Path, backup_root: Path, dry_run: bool) -> Path | None:
    existing = [skill_dir] + [agent_dir / name for name in AGENT_FILES]
    existing = [path for path in existing if path.exists()]
    if not existing:
        return None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_root / stamp
    if dry_run:
        print(f"[dry-run] backup existing managed files to {dest}")
        return dest

    dest.mkdir(parents=True, exist_ok=False)
    if skill_dir.exists():
        shutil.copytree(skill_dir, dest / "skill")
    managed_agents = dest / "agents"
    managed_agents.mkdir(parents=True, exist_ok=True)
    for name in AGENT_FILES:
        src = agent_dir / name
        if src.exists():
            shutil.copy2(src, managed_agents / name)
    return dest


def install(scope: str, project_root: Path | None, dry_run: bool) -> int:
    root = source_root()
    source_skill = root / "skills" / PROJECT
    source_agents = root / "agents"

    skill_dir, agent_dir, backup_root = resolve_targets(scope, project_root)

    missing = [p for p in [source_skill / "SKILL.md"] + [source_agents / n for n in AGENT_FILES] if not p.exists()]
    if missing:
        print("Source tree is incomplete:", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 2

    backup = backup_existing(skill_dir, agent_dir, backup_root, dry_run)

    print(f"scope: {scope}")
    print(f"skill: {skill_dir}")
    print(f"agents: {agent_dir}")
    if backup:
        print(f"backup: {backup}")

    if dry_run:
        print("[dry-run] no files changed")
        return 0

    skill_dir.parent.mkdir(parents=True, exist_ok=True)
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Replace only this project's Skill directory. Other Skills are untouched.
    with tempfile.TemporaryDirectory(prefix=f".{PROJECT}-", dir=str(skill_dir.parent)) as tmp:
        staged = Path(tmp) / PROJECT
        shutil.copytree(source_skill, staged)
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
        shutil.move(str(staged), str(skill_dir))

    # Replace only named files owned by this project. Other custom agents remain untouched.
    for name in AGENT_FILES:
        shutil.copy2(source_agents / name, agent_dir / name)

    print("installed successfully")
    print("restart Codex or force a Skill reload if the new Skill/agents are not visible")
    print(f"invoke with: ${PROJECT}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(install(args.scope, args.project_root, args.dry_run))
