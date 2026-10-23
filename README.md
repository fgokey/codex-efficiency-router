# Codex Efficiency Router

[简体中文](README.zh-CN.md) · [Repair scope](docs/REPAIR-2026-10-22.md) · [Acceptance](docs/ACCEPTANCE.md)

**v0.8.5 corrective updates · Codex only · MIT · Python 3.11+**

Route substantial engineering work to a suitable native Codex worker with explicit model/effort, bounded ownership and evidence-based acceptance. Astra remains a read-only adviser in strict execution paths. Prefer one implementation owner and a reviewer only when useful; retain the same owner for follow-up work.

This community project does not switch the parent model. Static tests, text-token counts and a successful installation do not establish live compliance, coding quality, speed or subscription savings.

## Sol model retirement

Sol routing now uses **`gpt-6.1-sol` only**. `gpt-6-sol` and `gpt-5.6-sol` are removed from model selection, explicit pins, fallbacks and assignment admission. New Sol routes use `cer_auto_sol61_engineer` with the appropriate effort. Missing 6.1 support never re-enables an older Sol model or silently rewrites an exact model pin.

The owned `sol_engineer` / `cer_auto_sol_engineer` filenames remain migration aliases, also bound to 6.1. This preserves existing references and manifest-owned backup/restore without adding another selectable Sol model. Ordinary reinstall updates unchanged owned files; customized files stop for review. Historical fixtures and accounting evidence are not routing options. Reach a safe boundary, update the Skill and any separately registered Guard, then reload Codex; do not hot-switch running workers.

## Existing-flow fixes

Unchanged completed-worker reports are no longer repeated while other workers run. Revised final text remains visible even when its message ID is unchanged. Errors and undrained evidence remain actionable. Report pages fill the existing 4 KiB budget rather than repeatedly halving it. Source-page fitting no longer serializes the entire remaining file, but still verifies its full hash. No new role, mode, Hook or model call; permissions, model/effort policy and acceptance stay unchanged. These are tested transport/Reader improvements, not measured whole-task token or quality gains.

## Coordination overhead

Keep one owner for a whole authorized repair unit, including implementation, fixes and verification. Do not poll status, admission or completion while nothing changed. Retain a compact checkpoint at safe phase boundaries and use supported compaction rather than copying a long transcript or restarting active workers.

The optional `COORDINATION_QUIET_JS` adapter combines at most two unchanged native waits into one model-visible return on a capability-verified host. The outer Code Mode yield must cover the entire call, not only its inner wait. Completion, errors, approval state, new turns and unfamiliar results return early. Unsupported hosts keep their supported one-wait path. No daemon or hidden model call is introduced.

Hooks retain their authority checks and only reuse validator **code loading within one short-lived process**. Identities, permissions, policy hashes and decisions are never cached. Successful ordinary checks add no model context. Avoid duplicate registrations across plugin/user/project sources; never disable all Hooks for speed or remove a configured mandatory admission handler. See the [Hook review](docs/WRITE-GATE.md#hook-cost-and-redundancy-review).

Paired tests distinguish real Hook subprocess timings from simulated wait transport. Fewer tool returns are not claimed live token or task-speed savings. The commit's `windows-runtime-overhead` job publishes the Windows comparison. Model/effort policy and required acceptance remain unchanged.

## Current repair

The Reader and dispatch guard share supported model/effort pairs. Shipped Luna, Terra and Sol61 bindings have complete admission paths. Known executor medium/high HOLD creation needs no redundant work-admission envelope. Actual binding and RELEASE remain required before writes.

Exact continue/status/stop controls retain the original current-policy receipt and scope; they do not create a new worker or authorize new work. Additional instructions need fresh admission. The guard rejects control-labelled work. With the optional custom host, pass the Reader's returned `admitted_dispatch_arguments`, including model/effort, instead of inheriting Sol61/high defaults.

Windows coverage includes UTF-8 BOM input, exact CRLF preservation, non-default CODEX_HOME with Unicode/spaces, PowerShell 7 and 5.1 launchers, interpreter rejection, and packaged installation/removal. See the actual commit's CI rather than inferring PASS from this feature list.

## Native role presets

| Role | Model | Fixed effort |
| --- | --- | --- |
| `luna_worker` | `gpt-6-luna` | `high` |
| `terra_executor` | `gpt-5.6-terra` | `medium` |
| `sol_engineer` | `gpt-6.1-sol` | `medium` (compatibility name) |
| `sol61_engineer` | `gpt-6.1-sol` | `high` |
| `astra_architect` | `gpt-6-astra` | `high` |

Default routing mode is `auto`: five fixed compatibility bindings plus five `cer_auto_*` aliases with explicit effort selection. These are configuration files, not ten running agents. Actual model availability comes from the host. Automatic low stays disabled unless explicitly enabled. Current high defaults are retained during this repair so model tuning does not confound protocol fixes.

## Install and update

Use a clean repository checkout and the same scope as the existing installation. Review changes and reach a safe boundary in active work first.

```powershell
git switch main
git pull --ff-only
.\cer.ps1 install --scope user --dry-run
.\cer.ps1 install --scope user
.\cer.ps1 doctor --scope user --json
```

First installation: clone `https://github.com/fgokey/codex-efficiency-router.git`, enter its directory, then run the install commands. The checked launcher locates Python 3.11+; it neither downloads Python nor changes PATH. For a particular installed interpreter, set `$env:CER_PYTHON` to its real executable path. Invalid explicit paths fail rather than silently switching interpreters. Do not disable PowerShell policy globally to install this project.

macOS/Linux use `python3 scripts/install.py --scope user --dry-run`, then omit `--dry-run`; run `python3 scripts/doctor.py --scope user`. For project scope use `--scope project --project-root` with the real existing project path. Do not duplicate scopes. Keep the clone for uninstall/restore. Edited owned files and unowned collisions stop the operation; inspect instead of blindly adding `--force`.

Reload Codex after updating. Invoke `$codex-efficiency-router` explicitly for acceptance; implicit discovery remains allowed for matching substantial tasks. A disk version is not evidence that an old conversation loaded it.

## Permissions and host compatibility

Three independent layers exist: the Skill/roles, optional write/dispatch Hooks, and the experimental patched Codex host. Ordinary installation does not register/trust Hooks or replace a binary. `policy-only` means instructions, not native enforcement. Static doctor is not a live Canary.

Routing `auto/fixed/adaptive` is separate from host `full/compat`. Existing explicit choices are preserved; full remains the default. Full requires current trusted binding and authorization for affected work. A local `doctor --startup` can report BLOCKED because it cannot attest a live binding; do not repeatedly run it as a task prerequisite. Explicit compat provides planning/context/review within existing host permissions, not guaranteed model routing. It never removes sandbox/Hook restrictions or automatically replaces a full installation. See [installation and recovery](docs/INSTALL.md) before changing host mode.

Existing Guard users must update their own registered boundary through its documented lifecycle and re-review changed commands in `/hooks`. Reinstalling the Skill alone does not update a separately registered Hook. The optional host patch is packaged as one explicitly allowlisted source file, not a custom binary. Its activation, V1/V2 compatibility and database assumptions remain separate acceptance items. This repair does not claim to rebuild or validate your running desktop host.

## Uninstall and recovery

```powershell
.\cer.ps1 uninstall --scope user --dry-run
.\cer.ps1 uninstall --scope user
# Only when restoring a reviewed actual backup is intended:
.\cer.ps1 install --scope user --restore "ACTUAL-BACKUP-PATH" --dry-run
```

Uninstall removes manifest-owned Skill/role files, preserves user additions and backups, and reverses only explicitly owned child defaults. It does not automatically restore an old version. Separately registered Hooks and a custom host need their own lifecycle; do not delete all `.codex` files or reset business changes. [Full instructions](docs/INSTALL.md).

## Validation

CI runs source regression, static checks, deterministic packaging and the full suite again from the extracted ZIP on Windows/macOS/Linux. A separate audit runs mutation tests and named-reference token budgets; no model task is launched. Native behavior and complete-task measurements remain [user-host acceptance](docs/ACCEPTANCE.md), with [paired accounting](docs/BENCHMARKING.md).

[Architecture](docs/ARCHITECTURE.md) · [Effort](docs/ADAPTIVE-EFFORT.md) · [Write gate](docs/WRITE-GATE.md) · [Sources](docs/PRIOR-ART.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [License](LICENSE)
