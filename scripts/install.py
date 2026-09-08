#!/usr/bin/env python3
"""Install or restore this Skill and native role bindings; never edit config.toml."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import manage
from package import AGENT_FILES, PROJECT, resolve_targets  # re-export for compatibility


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def install(scope: str, project_root: Path | None, dry_run: bool, *,
            force: bool = False, adopt_v01: bool = False,
            mode: str | None = None, allow_low: bool | None = None) -> int:
    return manage.install(source_root(), scope, project_root, dry_run, force, adopt_v01,
                          mode=mode, allow_low=allow_low)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="back up and replace locally edited OWNED files")
    parser.add_argument("--adopt-v01", action="store_true", help="adopt only exact known legacy file contents")
    parser.add_argument("--restore", type=Path, metavar="BACKUP", help="restore a backup for the same scope")
    parser.add_argument("--mode", choices=("auto", "fixed", "adaptive"), default=None,
                        help="advanced override; ordinary install/update uses auto (explicit v0.5+ overrides are preserved)")
    low = parser.add_mutually_exclusive_group()
    low.add_argument("--allow-low", dest="allow_low", action="store_true", default=None,
                     help="opt in to tightly gated automatic low (off by default)")
    low.add_argument("--no-allow-low", dest="allow_low", action="store_false",
                     help="disable automatic low; omitted preserves installed setting")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.restore:
            if args.adopt_v01 or args.mode is not None or args.allow_low is not None:
                parser.error("--restore cannot be combined with --adopt-v01, --mode or low switches")
            return manage.restore(args.restore, args.scope, args.project_root, args.dry_run, args.force)
        return install(args.scope, args.project_root, args.dry_run, force=args.force, adopt_v01=args.adopt_v01,
                       mode=args.mode, allow_low=args.allow_low)
    except (OSError, ValueError) as exc:
        print(f"install: FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
