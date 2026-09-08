# Codex Efficiency Router

[简体中文](README.zh-CN.md) · [Design](docs/ARCHITECTURE.md) · [Quality protocol](docs/QUALITY-PROTOCOL.md) · [User acceptance](docs/ACCEPTANCE.md)

**v0.4.0 · Codex-only Skill · MIT · Python 3.11+ · Windows / macOS / Linux**

Use strong reasoning for unresolved decisions and sufficient cheaper execution when delegation pays. Quality and authorization remain constraints. This independent community project does not guarantee unchanged model quality, savings or speedups on every task.

## What runs in Codex

The current coordinator applies a compact Skill and uses native Codex child roles. It does not switch its own model, launch a second CLI/API session, install another agent platform or call a classifier model. Simple work stays local; safe tools run concurrently before adding model contexts. One leaf is the default; more need independent acceptance, disjoint ownership and a benefit.

| Custom role | Model preset | Reasoning |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` | `medium` |
| `terra_executor` | `gpt-5.6-terra` | `medium` |
| `sol_engineer` | `gpt-5.6-sol` | `medium` |
| `astra_architect` | `gpt-6-astra` | `high` |

Four presets, no compulsory escalation ladder or automatic `max`. Astra is read-only decision support. After a decision settles, reassess remaining work; do not spawn for a tiny tail. Identical model/effort delegation needs a concrete contextual reason AND net benefit. Missing prerequisites are not expensive-model triggers.

Actual availability and role/model/effort selection depend on your Codex host/account. Pinned role settings can override spawn values. Requested identity is not observed identity; missing runtime evidence stays UNKNOWN. [Compatibility](docs/COMPATIBILITY.md).

## v0.3 quality changes

Before editing, the receiver checks requirements, plan conflicts, material assumptions and state. A strong model's plan cannot override requirements. Final acceptance maps required outcomes to current evidence: **PASS**, **PARTIAL**, or **BLOCKED**. Disclosure does not waive missing work. Review coverage and correctness together; no mandatory extra reviewer.

Attempts belong to the task/unit/failure signature across workers and compaction, not each agent. For long work/recovery only, reuse one permitted task-scoped checkpoint and reconcile actual files, workers and prior side effects. Do not repeat completed work blindly. Four short references load only as needed; full-load and per-role text budgets are measured separately from live task usage.

The Python quality helpers and evaluation corpus are **offline development aids**, not a runtime dispatcher, security boundary or model-quality certificate. They are not installed into the Skill payload or called every turn. [Protocol and sources](docs/QUALITY-PROTOCOL.md) · [Release validation](docs/VALIDATION-v0.4.0.md).

## Adaptive reasoning effort (v0.4)

Four roles remain; the parent now selects **model + effort** at meaningful task boundaries. New installs default to **fixed** for compatibility. Updates preserve the installed mode and low opt-in; no implicit migration. In **adaptive**, role models and permission instructions stay unchanged, but effort is unpinned and must be explicitly supplied by the parent through an actual native tool parameter. This is not guaranteed on every Codex host.

From the retained clone, enable adaptive mode deliberately:

```powershell
git pull --ff-only
py -3 scripts/install.py --scope user --mode adaptive --dry-run
py -3 scripts/install.py --scope user --mode adaptive
py -3 scripts/doctor.py --scope user
```

On macOS/Linux use `python3`; project scope keeps `--scope project --project-root ...`. Restart/reload Codex. No account, config, authentication or main-thread model change is made. Exactly one four-role set is installed. Do not mix old role files or an old loaded Skill with the new profile.

Ordinary implementation: medium. Deep logic/assumptions/edges: high in a suitable model, or a stronger model when needed. Automatic Astra: high. Automatic low: **off**, optionally enabled only for strictly checked mechanical Luna tasks. xhigh/max: explicit user request only, subject to actual support and quality/user limits. “No escalation” prohibits increases in either model or effort. Model-only locks can allow effort changes. No in-flight hot switching, hidden CLI/API fallback or retry-budget reset.

```powershell
# Optional, conservative auto-low opt-in; keep disabled during initial validation:
py -3 scripts/install.py --scope user --mode adaptive --allow-low
# Disable low while retaining adaptive:
py -3 scripts/install.py --scope user --no-allow-low
# Return to fixed compatibility mode:
py -3 scripts/install.py --scope user --mode fixed
```

Fixed files override conflicting requests; adaptive requires both an unpinned loaded role and an exposed effort field. Unsupported/mismatched settings are not silently downgraded. Requested values are not observed values: UNKNOWN/MISMATCH disables subsequent automatic low. Static doctor checks package/profile integrity, not live execution. [Design, precedence and constraints](docs/ADAPTIVE-EFFORT.md) · [User acceptance](docs/ACCEPTANCE.md).

## Install

Use Git and Python **3.11+**. After cloning, installation is offline and never edits `config.toml`, `AGENTS.md`, authentication, providers, permissions or unrelated agents/Skills. Review files before running. Keep the clone for updates and removal.

### Windows / PowerShell

```powershell
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
py -3 scripts/doctor.py --scope user
```

Use `python` in place of `py -3` when it is your Python 3.11+ interpreter. Direct Python needs no PowerShell execution-policy change. PowerShell wrappers forward Python-style `--scope`/`--dry-run`, not `-Scope`/`-DryRun` aliases.

### macOS / Linux

```sh
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
python3 scripts/install.py --scope user --dry-run
python3 scripts/install.py --scope user
python3 scripts/doctor.py --scope user
```

Shell wrappers also work as `sh install.sh --scope user` and `sh uninstall.sh --scope user`.

### Project scope instead

Choose one scope to avoid duplicate Skill names. Substitute the actual existing project path:

```powershell
py -3 scripts/install.py --scope project --project-root "C:/Work/my-project" --dry-run
py -3 scripts/install.py --scope project --project-root "C:/Work/my-project"
py -3 scripts/doctor.py --scope project --project-root "C:/Work/my-project"
```

On macOS/Linux use `python3` and an absolute project path. Project configuration remains subject to Codex trust/admin policy.

| Scope | Skill | Four role files | Backups |
| --- | --- | --- | --- |
| User | `~/.agents/skills/codex-efficiency-router/` | `$CODEX_HOME/agents/` (default `~/.codex/agents/`) | `$CODEX_HOME/backups/codex-efficiency-router/` |
| Project | `<project>/.agents/skills/codex-efficiency-router/` | `<project>/.codex/agents/` | `<project>/.codex-router-local/backups/` |

A manifest owns only installed payload files. Unowned collisions are refused; locally changed owned files need review before `--force`. Source-only Skill installers do not install the four role presets; use the full package installer. `doctor: STATIC PASS` does not confirm live model execution. Reload Codex when discovery is stale; already-loaded conversations can retain old instructions.

## Use

```text
$codex-efficiency-router
Complete this task with its required checks. Resolve important uncertainty with
sufficient reasoning, avoid unnecessary delegation, and report remaining gaps honestly.
```

Relevant substantial tasks can invoke the Skill implicitly; explicit invocation is clearer. Honor disable/no-subagent/no-escalation requests without pretending an insufficient current model is sufficient. Do not stack routers. The parent retains your selected model.

## Update

For a managed v0.2+ installation:

```powershell
git pull --ff-only
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
py -3 scripts/doctor.py --scope user
```

On macOS/Linux substitute `python3`. For project scope reuse the original scope/root. **Only** original v0.1 installs without manifests need `--adopt-v01` added to install commands. Adoption accepts exact known legacy content (including CRLF-equivalent copies), not arbitrary local edits. An unchanged reinstall is a no-op. Review conflicts instead of immediately forcing.

## Uninstall

Use the same scope, project and `CODEX_HOME` as installation. Do not use the original v0.1 uninstaller on customized files.

```powershell
# Windows user scope
py -3 scripts/uninstall.py --scope user --dry-run
py -3 scripts/uninstall.py --scope user
# Project scope instead
py -3 scripts/uninstall.py --scope project --project-root "C:/Work/my-project"
```

```sh
# macOS/Linux user scope
python3 scripts/uninstall.py --scope user --dry-run
python3 scripts/uninstall.py --scope user
# Project scope instead
python3 scripts/uninstall.py --scope project --project-root "/path/to/my-project"
```

Only manifest-owned files are removed. Untracked user files, unrelated config/agents and backups survive. Modified owned files block removal by default; reviewed `--force` backs them up and removes only owned files. Legacy installs need adoption first. Default uninstall **does not restore an old version** and has no `--no-restore` flag.

### Explicit recovery

Use the actual backup directory printed by the operation:

```powershell
py -3 scripts/install.py --scope user --restore "ACTUAL-BACKUP-PATH" --dry-run
py -3 scripts/install.py --scope user --restore "ACTUAL-BACKUP-PATH"
```

Use `python3` on macOS/Linux and original project-scope flags when applicable. Restore verifies target paths/checksums and refuses intervening edits by default; it retains its own backup. Optional defaults manually merged into `config.toml` are not owned or undone automatically. Backups may contain private instructions; keep them out of Git. [Lifecycle safety and recovery](docs/INSTALL.md).

## Validation versus actual effectiveness

```sh
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py --source-tree .
python3 -m compileall -q scripts tests evaluation
python3 evaluation/offline_audit.py --without-tokenizer
```

Optional raw-text audit requires a full Git clone and `tiktoken==0.11.0`; run `python3 evaluation/offline_audit.py`. Initial package/vocabulary downloads use network, not model inference. CI runs standard Python checks, selected deliberate policy/quality mutations and named-encoding token budgets; results are scoped to the checked commit. Historical failing reports remain available.

The 20 prompts in [behavioral acceptance cases](evaluation/behavior_cases.json) are prepared **but not executed by CI**. Corpus structure checks are not model-response grades. User-run acceptance should observe real role/model identity, requirement coverage, handoff/recovery and whole-task parent/child/retry usage. [Acceptance](docs/ACCEPTANCE.md) · [Benchmark method](docs/BENCHMARKING.md).

The optional `scripts/compare_runs.py runs.json` describes paired data; incomplete Router acceptance cannot exit successfully even when both variants fail. Missing metrics remain unknown. Neither a zero exit code nor text-token reduction proves live non-inferiority or savings. No paid model test is triggered by installation or CI.

## Open-source project

[Architecture](docs/ARCHITECTURE.md) · [Routing](docs/ROUTING.md) · [Quality gates](docs/QUALITY-GATES.md) · [Token efficiency](docs/TOKEN-EFFICIENCY.md) · [Prior art](docs/PRIOR-ART.md) · [Changelog](CHANGELOG.md)

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Support](SUPPORT.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [MIT License](LICENSE)
