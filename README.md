# Codex Efficiency Router

[简体中文](README.zh-CN.md) · [Design](docs/ARCHITECTURE.md) · [Audit](docs/AUDIT-2026-09-07.md) · [Evidence and prior art](docs/PRIOR-ART.md)

A small, quality-gated Codex Skill that reserves GPT-6 Astra for difficult unresolved decisions and delegates bounded implementation only when the benefit justifies the overhead.

**Version 0.2.0 · MIT · Python 3.11+ · Windows / macOS / Linux**

This is a community project, not an OpenAI product. It aims to reduce avoidable tokens and elapsed time while preserving required acceptance checks. It cannot guarantee unchanged model quality, lower cost, or faster completion for every task. Offline policy tests are not live coding benchmarks.

## How it works

```text
Current coordinator (your selected model stays unchanged)
  ├─ sufficient, tiny, or tool-bound task → direct tools
  ├─ safe independent operations         → bounded tool concurrency
  └─ worthwhile or necessary delegation  → one bounded leaf
       Luna  → mechanical, low-risk, strongly verifiable work
       Terra → bounded implementation with a settled design
       Sol   → difficult integration, uncertainty, or review
       Astra → exceptional unresolved reasoning, read-only advice
                    ↓ decision resolved
             reconsider the remaining work; hand off only when worthwhile
```

No router-model call, daemon, mandatory planner/reviewer chain, per-turn ledger, hidden nested Codex process, or automatic `max` effort. Technology keywords and file counts do not determine capability. A missing requirement, permission, environment, or observation is repaired before escalating the model.

| Custom role | Model preset | Reasoning |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` | `medium` |
| `terra_executor` | `gpt-5.6-terra` | `medium` |
| `sol_engineer` | `gpt-5.6-sol` | `medium` |
| `astra_architect` | `gpt-6-astra` | `high` |

Presets were checked against official documentation on **2026-09-07**. Your account, host, model catalog, permissions, and actual child metadata determine availability. Agent files can take precedence over spawn-time model/effort requests: a requested model is not proof of the model that ran. See [compatibility](docs/COMPATIBILITY.md).

## Install

Requirements: Git, Python **3.11 or newer**, and a Codex host that supports local Skills and custom agents. Installation is offline after cloning; it does not request an API key or alter your Codex authentication.

### Windows / PowerShell

```powershell
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
py -3 scripts/doctor.py --scope user
```

Use `python` instead of `py -3` when that is your Python 3.11+ interpreter. Direct Python commands do not require changing PowerShell execution policy.

### macOS / Linux

```sh
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
python3 scripts/install.py --scope user --dry-run
python3 scripts/install.py --scope user
python3 scripts/doctor.py --scope user
```

The shell wrappers are also usable as `sh install.sh --scope user` and `sh uninstall.sh --scope user`; no executable-bit assumption is required.

### Install for one project instead

Choose **one scope**, rather than installing duplicate Skill names at both scopes. From this router repository, substitute the real existing project root:

```powershell
py -3 scripts/install.py --scope project --project-root "C:/Work/my-project" --dry-run
py -3 scripts/install.py --scope project --project-root "C:/Work/my-project"
py -3 scripts/doctor.py --scope project --project-root "C:/Work/my-project"
```

On macOS/Linux replace `py -3` with `python3` and use an absolute project path. Local project configuration remains subject to Codex trust/administration policies.

| Scope | Skill | Four named agent files | Retained backups |
| --- | --- | --- | --- |
| User | `~/.agents/skills/codex-efficiency-router/` | `$CODEX_HOME/agents/` or `~/.codex/agents/` | `$CODEX_HOME/backups/codex-efficiency-router/` |
| Project | `<project>/.agents/skills/codex-efficiency-router/` | `<project>/.codex/agents/` | `<project>/.codex-router-local/backups/` |

The installer never changes `config.toml`, `AGENTS.md`, MCP servers, providers, permissions, or unrelated agents/Skills. It refuses unowned filename collisions. A hash manifest tracks only the installed payload; user edits require explicit review before replacement.

`doctor` reports **STATIC PASS/FAIL**, separately from **live model execution: NOT VERIFIED**. It does not run models. Reload/restart Codex if the Skill or roles are not discovered. Installing only `SKILL.md` through another Skill installer does not install the four role presets; use the full installer for this package.

## Use

```text
$codex-efficiency-router
Implement the requested change. Preserve the agreed design and required checks.
Use Astra only for consequential unresolved reasoning; avoid unnecessary delegation.
```

Implicit invocation is enabled in the packaged UI metadata for relevant substantial engineering work. Explicit `$codex-efficiency-router` is the reliable way to request it. Requests to disable routing, avoid subagents, or avoid escalation take precedence, but do not make an insufficient current model sufficient. Do not stack several routers on the same task.

For an initial live smoke test, ask for a small **read-only** bounded child task and inspect host/session metadata for the actual role, model, effort, and result. Model self-identification is not evidence. A successful installation or catalog export alone does not prove child dispatch works.

## Update and migrate from v0.1.0

```powershell
git pull --ff-only
# Existing v0.2+ managed installation:
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
# ONLY for the original v0.1.0 installation without an ownership manifest:
py -3 scripts/install.py --scope user --adopt-v01 --dry-run
py -3 scripts/install.py --scope user --adopt-v01
```

These are alternative upgrade paths, not commands to run all at once. On macOS/Linux use `python3`. For project scope, append the same `--scope project --project-root ...` arguments used at installation.

Legacy adoption recognizes the exact published v0.1.0 content, including CRLF-equivalent copies. Unknown or customized legacy files are preserved and require manual review. Even `--force` cannot claim an unrelated file. Reinstalling an unchanged managed version is a no-op.

## Uninstall

Run these from your retained clone of this repository, using the **same scope and CODEX_HOME** as installation. Do not use the old v0.1.0 uninstaller on customized files.

### Windows / PowerShell

```powershell
py -3 scripts/uninstall.py --scope user --dry-run
py -3 scripts/uninstall.py --scope user
# For project scope instead:
py -3 scripts/uninstall.py --scope project --project-root "C:/Work/my-project"
```

### macOS / Linux

```sh
python3 scripts/uninstall.py --scope user --dry-run
python3 scripts/uninstall.py --scope user
# For project scope instead:
python3 scripts/uninstall.py --scope project --project-root "/path/to/my-project"
```

Only manifest-owned files are removed. Unrelated/untracked files, other agents, existing configuration, and backups remain. Locally edited owned files block removal by default. After reviewing them, `--force` backs them up and removes only owned files; it is not a broad cleanup switch. Legacy installations must first be adopted with `--adopt-v01`. Reload Codex after uninstalling; an already-loaded conversation may still contain the old instructions.

### Restore an installation or uninstall

Use the backup directory printed by the operation, not a guessed timestamp:

```powershell
py -3 scripts/install.py --scope user --restore "C:/Users/you/.codex/backups/codex-efficiency-router/ACTUAL-BACKUP" --dry-run
py -3 scripts/install.py --scope user --restore "C:/Users/you/.codex/backups/codex-efficiency-router/ACTUAL-BACKUP"
```

On macOS/Linux use `python3` and the actual backup path. Restore refuses different target paths, corrupt backups, and intervening local changes unless explicitly overridden after review. Each restore also retains a recovery backup. Files manually added to `config.toml`, such as [optional defaults](config/optional-defaults.toml), are never removed automatically. See [detailed installation and recovery](docs/INSTALL.md).

## Validation and measurable claims

```sh
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py --source-tree .
python3 -m compileall -q scripts tests
# Optional: compare your own normalized paired runs, no API call:
python3 scripts/compare_runs.py runs.json
```

The suite checks routing boundaries, dispatch admission, install/update/uninstall/restore safety, static package integrity, and honest measurement handling. CI defines Windows, macOS and Linux jobs. See the actual workflow result for which platforms passed.

The v0.2.0 core Skill is smaller through progressive disclosure, not removal of acceptance gates. This is **instruction-byte reduction**, not a measured percentage of total task tokens. No live Astra/Terra/Sol/Luna task-quality, token, or latency benchmark is claimed. [Benchmarking](docs/BENCHMARKING.md) describes controlled paired trials and whole-task accounting.

## Project documentation

[Architecture](docs/ARCHITECTURE.md) · [Routing](docs/ROUTING.md) · [Astra gates](docs/ASTRA-ESCALATION.md) · [Token and latency](docs/TOKEN-EFFICIENCY.md) · [Quality gates](docs/QUALITY-GATES.md) · [Compatibility](docs/COMPATIBILITY.md) · [Audit](docs/AUDIT-2026-09-07.md) · [Prior art](docs/PRIOR-ART.md)

Contributions: [CONTRIBUTING](CONTRIBUTING.md). Safety/reporting: [SECURITY](SECURITY.md). Support: [SUPPORT](SUPPORT.md). Community conduct: [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md). Changes: [CHANGELOG](CHANGELOG.md). License: [MIT](LICENSE).
