"""Shared package identity and target paths; no filesystem mutation on import."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT = "codex-efficiency-router"
MANIFEST = ".cer-install.json"
# Project-specific source budgets, not platform limits or billed-token estimates.
INSTRUCTION_BUDGETS = {
    "core_skill_bytes": 6500,
    "full_skill_bytes": 12000,
    "discovery_description_characters": 400,
}
EXPECTED = {
    "luna-worker.toml": ("luna_worker", "gpt-5.6-luna", "medium"),
    "terra-executor.toml": ("terra_executor", "gpt-5.6-terra", "medium"),
    "sol-engineer.toml": ("sol_engineer", "gpt-5.6-sol", "medium"),
    "astra-architect.toml": ("astra_architect", "gpt-6-astra", "high"),
}
AGENT_FILES = list(EXPECTED)


def resolve_targets(scope: str, project_root: Path | None) -> tuple[Path, Path, Path]:
    if scope == "user":
        if project_root is not None:
            raise ValueError("--project-root requires --scope project")
        home = Path.home().resolve()
        codex = Path(os.environ.get("CODEX_HOME", str(home / ".codex"))).expanduser().absolute()
        return home / ".agents/skills" / PROJECT, codex / "agents", codex / "backups" / PROJECT
    if scope != "project":
        raise ValueError("scope must be user or project")
    root = (project_root or Path.cwd()).resolve()
    if not root.is_dir():
        raise ValueError(f"project root does not exist: {root}")
    return root / ".agents/skills" / PROJECT, root / ".codex/agents", root / ".codex-router-local/backups"
