#!/usr/bin/env python3
"""Install or restore this Skill and four roles; never edit config.toml."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import manage
from package import AGENT_FILES, PROJECT, resolve_targets  # re-export for compatibility


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def install(scope: str, project_root: Path | None, dry_run: bool, *,
            force: bool = False, adopt_v01: bool = False) -> int:
    return manage.install(source_root(), scope, project_root, dry_run, force, adopt_v01)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="back up and replace locally edited OWNED files")
    parser.add_argument("--adopt-v01", action="store_true", help="adopt only exact known legacy file contents")
    parser.add_argument("--restore", type=Path, metavar="BACKUP", help="restore a backup for the same scope")
    args = parser.parse_args()
    try:
        if args.restore:
            if args.adopt_v01:
                parser.error("--restore and --adopt-v01 cannot be combined")
            return manage.restore(args.restore, args.scope, args.project_root, args.dry_run, args.force)
        return install(args.scope, args.project_root, args.dry_run, force=args.force, adopt_v01=args.adopt_v01)
    except (OSError, ValueError) as exc:
        print(f"install: FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
