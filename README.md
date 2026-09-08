# Codex Efficiency Router

[简体中文](README.zh-CN.md) · [Automatic adaptation](docs/ADAPTIVE-EFFORT.md) · [Quality protocol](docs/QUALITY-PROTOCOL.md) · [Acceptance](docs/ACCEPTANCE.md)

**v0.5.0 · Codex only · MIT · Python 3.11+ · Windows / macOS / Linux**

Choose a sufficient model and reasoning effort per bounded task. Ordinary install/update now selects **auto**: no routine fixed/adaptive mode switching. Quality and authorization remain constraints. Community project, not an OpenAI product or a guarantee of cheaper, faster, quality-equivalent execution.

## One install, capability-aware execution

After deciding capability and delegation benefit, the parent uses actual native schemas, loaded roles and supported model/effort pairs:

| Available capability | Action |
| --- | --- |
| Explicit effort field and correctly loaded unpinned alias | Request the selected pair using that alias |
| Otherwise, a fixed role matches the exact same pair | Use the compatibility binding, without reinstalling |
| Neither route meets the requirement | Keep a sufficient parent, or report BLOCKED; never silently weaken effort |

Only one binding is selected per child. No model calls just to probe capability, no runtime configuration rewrites, hidden sessions or replay while another writer's state is uncertain. A compatibility route is not dynamic-effort success; missing runtime identity remains UNKNOWN.

| Responsibility | Model | Fixed compatibility effort |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` | `medium` |
| `terra_executor` | `gpt-5.6-terra` | `medium` |
| `sol_engineer` | `gpt-5.6-sol` | `medium` |
| `astra_architect` | `gpt-6-astra` | `high` |

Auto generates four `cer_auto_<role>` unpinned aliases alongside the four fixed bindings: **eight small TOML files, four responsibilities**, not eight running agents or extra capability tiers. Generated aliases change only name and effort pin; model, instructions and permissions remain identical. Additional discovery descriptions can add host context; the text audit reports their separate footprint rather than claiming zero overhead.

Ordinary implementation normally uses medium; deeper reasoning may use high; automatic Astra remains high. Automatic low is off by default and retains explicit prior choice. xhigh/max require explicit intent and support. No mandatory weak-model ladder. A host lacking Sol/high does not make Sol/medium an acceptable substitute.

## Install and update

Review source first. Installation only manages owned files; it does not edit global config, authentication, permissions, AGENTS.md or unrelated Skills/agents. Keep the clone for lifecycle commands. Choose one installation scope.

### Windows / PowerShell

```powershell
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
py -3 scripts/doctor.py --scope user
```

### macOS / Linux

```sh
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
python3 scripts/install.py --scope user --dry-run
python3 scripts/install.py --scope user
python3 scripts/doctor.py --scope user
```

### Existing installation

```powershell
git pull --ff-only
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
py -3 scripts/doctor.py --scope user
```

Use `python3` on macOS/Linux. **No `--mode adaptive` is needed.** Ordinary updates migrate pre-v0.5 manifests to auto with a printed notice and backup, preserving the low choice. Old manifests did not record whether fixed/adaptive was deliberate or default; advanced users needing a previous policy can explicitly retain it. Later v0.5+ explicit overrides survive ordinary updates. Original unmanifested v0.1 installations still require safe `--adopt-v01` adoption. See [migration details](docs/INSTALL.md).

Review customization/collision errors instead of blindly adding `--force`. STATIC PASS is installation integrity, not live model proof. Reload Codex after updates; an old conversation can retain old instructions. A Skill-only copy does not deploy the role bindings: use the full installer.

### Project scope

```powershell
py -3 scripts/install.py --scope project --project-root "C:/Work/my-project" --dry-run
py -3 scripts/install.py --scope project --project-root "C:/Work/my-project"
py -3 scripts/doctor.py --scope project --project-root "C:/Work/my-project"
```

On macOS/Linux substitute `python3` and a real absolute project path. User Skills go to `~/.agents/skills/codex-efficiency-router`; bindings to `$CODEX_HOME/agents` or `~/.codex/agents`. Project scope uses `.agents/skills` and `.codex/agents`. The installer prints actual backup paths.

## Use

```text
$codex-efficiency-router
Complete this task using suitable model/effort choices and the required acceptance checks.
```

Relevant substantial work may trigger implicitly; explicit invocation is clearer. The parent model remains unchanged. Simple work stays local; do not stack routers. Disable/no-subagent/no-escalation requests remain authoritative. PASS/PARTIAL/BLOCKED depends on evidence for required outcomes; binding/model changes do not reset retries.

## Uninstall and restore

Use the same scope, project root and CODEX_HOME as installation.

```powershell
py -3 scripts/uninstall.py --scope user --dry-run
py -3 scripts/uninstall.py --scope user
```

```sh
python3 scripts/uninstall.py --scope user --dry-run
python3 scripts/uninstall.py --scope user
```

For project scope use `--scope project --project-root ...`. Only manifest-owned files are removed; untracked files, configuration and backups survive. Local modifications block removal by default. Uninstall does not automatically restore an old version; there is no `--no-restore` option. Restore explicitly from the printed backup directory:

```powershell
py -3 scripts/install.py --scope user --restore "ACTUAL-BACKUP-PATH" --dry-run
py -3 scripts/install.py --scope user --restore "ACTUAL-BACKUP-PATH"
```

Restore preserves the original selection without migrating it to auto. Reload Codex after uninstall; keep private customization backups out of public reports. [Full lifecycle and recovery](docs/INSTALL.md).

## Validation and limits

```sh
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py --source-tree .
python3 evaluation/offline_audit.py --without-tokenizer
```

No model calls. CI also measures named reference token encodings. Pure helpers test declared conditions, not live enforcement. Actual binding/model/effort, task quality, all parent/child usage and elapsed time remain [user acceptance](docs/ACCEPTANCE.md). Historical failures are retained; do not equate static PASS with proven savings. [Benchmark method](docs/BENCHMARKING.md).

[Architecture](docs/ARCHITECTURE.md) · [Sources](docs/PRIOR-ART.md) · [Changes](CHANGELOG.md) · [Contribute](CONTRIBUTING.md) · [Security](SECURITY.md) · [MIT](LICENSE)

[Validation v0.5.0](docs/VALIDATION-v0.5.0.md)
