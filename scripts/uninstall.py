#!/usr/bin/env python3
"""Remove only files installed by codex-efficiency-router."""

from __future__ import annotations

import argparse
from pathlib import Path

from install import AGENT_FILES, resolve_targets


def uninstall(scope: str, project_root: Path | None, dry_run: bool) -> int:
    skill_dir, agent_dir, _ = resolve_targets(scope, project_root)
    targets = [skill_dir] + [agent_dir / name for name in AGENT_FILES]

    for target in targets:
        if not target.exists():
            continue
        if dry_run:
            print(f"[dry-run] remove {target}")
            continue
        if target.is_dir():
            import shutil
            shutil.rmtree(target)
        else:
            target.unlink()
        print(f"removed {target}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(uninstall(args.scope, args.project_root, args.dry_run))
