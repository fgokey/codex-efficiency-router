#!/usr/bin/env python3
"""Uninstall manifest-owned files only; preserve config, backups, and untracked files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from manage import uninstall


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="back up and remove locally edited OWNED files")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return uninstall(args.scope, args.project_root, args.dry_run, args.force)
    except (OSError, ValueError) as exc:
        print(f"uninstall: FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
