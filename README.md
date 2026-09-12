# Codex Efficiency Router

[简体中文](README.zh-CN.md) · [Automatic adaptation](docs/ADAPTIVE-EFFORT.md) · [Quality protocol](docs/QUALITY-PROTOCOL.md) · [Acceptance](docs/ACCEPTANCE.md)

**v0.7.0-rc.10 · Codex only · MIT · Python 3.11+ · Windows / macOS / Linux**

Choose a sufficient model and reasoning effort per bounded task. Ordinary install/update now selects **auto**: no routine fixed/adaptive mode switching. Quality and authorization remain constraints. Community project, not an OpenAI product or a guarantee of cheaper, faster, quality-equivalent execution.


## Windows Python preflight and acceptance boundaries

Use `cer.ps1` below (the install/uninstall wrappers share it). It checks the actual
Python version and `tomllib`, tries compatible PATH executables and `py -0p` listed
runtimes, and rejects 3.10 **before** invoking any installer. A name such as `python`
or `py -3` does not guarantee 3.11+. No downloads, PATH changes or global configuration edits occur.

To use an already verified runtime, including an app-bundled Python, explicitly set
its **actual full executable path** in this PowerShell session:

```powershell
$env:CER_PYTHON = 'C:\actual\Python312\python.exe'
.\cer.ps1 doctor --scope user --json
```

An invalid explicit override stops; it does not silently fall back. The selected path
and version go to stderr, leaving JSON stdout intact. Bundled runtimes can move after
an app update. Standalone Guard installation binds the selected absolute executable;
recheck/update the Guard and review its definition if that path changes. Portable
Plugin hooks have separate runtime discovery requirements; this launcher does not verify them.

**Skill installation is still policy-only unless a Guard is explicitly installed and
validated.** CI success is offline evidence, not a native Canary or real-task savings
claim. Keep `enforcement=NOT_VERIFIED` and loaded version `UNKNOWN` without corresponding
host evidence. See [explicit Guard activation and Canary](docs/UPGRADE-v0.7.0-rc.1.md).

## v0.7.0-rc.10: reviewable mutation admission

The policy now requires a parent check of the host-observed Terra/Sol binding before each write tool.
Mutation calls use one exact manifest and one bounded action class; forward copies,
configuration rewrites and destructive recovery stay separate. A host policy denial stops
equivalent replay or repackaging until policy changes, including when approval is disabled.

## v0.7.0-rc.9: fewer long-context round trips

Known tool schemas are reused until invalidation. In long contexts, work proceeds on state
changes or due checkpoints and batches only bounded independent checks. Worker monitoring
uses compact waits with backoff; after two unchanged native snapshots it reads one bounded
rollout delta from a saved offset, then waits for progress instead of polling both paths.
Offline state-machine tests cover rediscovery, round-trip admission and delta-tail behavior.

## v0.7.0-rc.8: bounded reads without repeated prefixes

Mandatory rules are read in separate output envelopes. Other unknown-size files are indexed
before relevant ranges are fetched; only known-small slices are batched. If output truncates,
the next read resumes the missing range instead of rereading captured prefixes. The same
contract is embedded in every role, with executable offline decision tests and unchanged
instruction budgets. This is policy behavior, not proof that an existing task loaded it.

## v0.7.0-rc.7: reconcile mismatches and retain critical context

Confirmed model/effort mismatches pause continuation at a safe boundary for binding/effect
reconciliation and review of affected checks. Preserve valid work and attempt history;
later matching metadata cannot erase that review. UNKNOWN alone is not a confirmed failure.
Compact handoffs include applicable rule paths, decision rationale and critical context;
each role reads those rules and stops affected work when essential context is missing.
The exclusive root owner can continue its qualified repair unit; other writers still block it.
Requested cost/quality comparisons reuse existing task logs, without probes or polling.

## v0.7.0-rc.6: repair admission and explicit task-based effort

Root repair exceptions and owner reuse retain prerequisite, capability/effort, boundary and
absolute retry-ceiling checks. One repair unit may contain multiple code/test patches;
a reason string alone cannot renew attempts. Sol/Terra can deliver only with explicit handoff
of existing user authority, exact repository/ref/destination and checks.

Auto selects both model and effort: implementation Terra/medium; diagnosis Sol/medium;
coupled or consequential reasoning Sol/high; exceptional judgment Astra/high. Use the unpinned
alias, explicit effort and a compact contract with `fork_turns="none"`, avoiding root max
inheritance. Reuse sufficient idle owners; preserve fixed/low preferences. Offline checks
prove neither runtime loading nor savings. Badge eligibility needs host attribution evidence.
These rules supersede rc.4's model-specific restriction and rc.5's single-patch limit;
strict Guard still disables the root exception.

## v0.7.0-rc.5 (historical): bounded root-Astra repair

Astra remains the primary reasoner for hard diagnosis and arbitration. Astra leaves and
read-only roles never write. A root Astra may apply one bounded local code patch only after
qualified executor failure or when handoff would materially lose critical reasoning, with
authorization, exact scope, current-workspace ownership, a safe boundary, defined checks,
no active writer or prior exception, and no observed active strict Guard. Unknown Hook layers
may still deny the patch at runtime. Shell/build/test and
publish/deploy work remains with Sol/Terra. Missing evidence falls back to delegation or a
blocked/deferred result. The optional native Guard deliberately remains stricter and denies
all Astra writes.

## v0.7.0-rc.4 (historical): native change-summary preflight

Before write delegation, the Router now checks whether the target Git repository belongs
to the current task workspace and whether the same write-capable parent will own the edits.
This prevents Review fallback from being presented as a fix for the native changed-files
badge. Mutation-heavy tasks that require the badge should use a Sol/Terra parent rooted at
the target repository, with Astra reserved for read-only hard judgments.

## v0.7.0-rc.3: explicit auto-effort dispatch

Auto-generated roles now identify themselves in native role discovery as auto-effort
bindings. When the host exposes both a matching `cer_auto_<role>` and an explicit effort
field, the parent must use that alias and pass the selected effort. Fixed roles are an
evidenced compatibility fallback only; selecting one while the auto path is available is
reported as a mismatch. This remains policy-only and does not add model calls or a daemon.

## v0.7.0-rc.2: smaller instructions

This candidate compresses the loaded Skill and role text without changing routing
or write permissions. References load once at explicit triggers while valid, not
on every tool call. See [footprint and validation](docs/VALIDATION-v0.7.0-rc.2.md).
Existing fixed/low settings and underlying installer arguments remain preserved;
Windows entry-point preflight is described above.


## v0.7.0-rc.1: verifiable state, not assumed enforcement

The source remains a **release candidate, not a stable release**, based on v0.6.0. Existing fixed-mode
installations and automatic-low opt-outs are preserved. No Write Lease, permanent
background service, runtime concurrency ledger or model-driven installer is added.

`policy-only` means policy text only; `guarded` means registered, not trusted or
proven active; `live-verified` requires fresh, scoped **operator-witnessed native**
Canary evidence. Disk version, static tests and an absent sentinel alone are not
proof. Hosted paths and existing `write_stdin` sessions remain outside the guarantee.

The candidate adds status/doctor JSON, version and digest checks, explicit guarded
updates, a bounded `cer-read batch`, per-call three-arm accounting and reproducible
Plugin/source packaging. The Plugin manifest validates offline; native Plugin role
discovery/trust/Windows execution still require host acceptance. Existing users
should keep the supported Skill installer plus explicit standalone Guard path until
that acceptance is complete. Do not install duplicate Plugin and standalone Hooks.

Git checkouts can use the fast-forward update below; record the actual commit.
For a downloaded ZIP, extract and review it using the [RC upgrade instructions](docs/UPGRADE-v0.7.0-rc.1.md).
See [Canary](docs/CANARY.md), [benchmark format](docs/BENCHMARKING-v0.7.md),
[validation status](docs/VALIDATION-v0.7.0-rc.1.md) and [plan review](docs/REVIEW-v0.7.0.md).

## v0.6 historical rule: read-only Astra, active diagnosis

Write authority now precedes tiny/local shortcuts. Astra roots and leaves never patch,
write checkpoints, format, build or run side-effecting tests. They still inspect evidence,
solve hard decisions and diagnose repeated qualified unexplained failures. Executors
apply the resulting plan; changing worker/model never renews repairs. Preserve existing
edits for independent takeover review; wait when two writers are active. rc.5 supersedes
the root-only part of this historical rule with the bounded exception above.

A Skill cannot revoke root tools. A separately registered native synchronous PreToolUse
guard blocks covered side-effect paths and provides bounded read access. **Normal Skill
installation does not register or trust it.** Registration affects its Codex configuration
scope, even outside this Skill, so consent/trust is explicit and project scope is preferred.
This is not another routing mode. [Guard setup, removal and limits](docs/WRITE-GATE.md).

## One install, capability-aware execution

After deciding capability and delegation benefit, the parent uses actual native schemas, loaded roles and supported model/effort pairs:

| Available capability | Action |
| --- | --- |
| Explicit effort field and correctly loaded unpinned alias | Must request the selected effort using that alias |
| Otherwise, a fixed role matches the exact same pair | Use the compatibility binding and record why auto was unavailable |
| Neither route meets the requirement | Keep sufficient permitted work local; Astra mutations still require an executor, otherwise BLOCKED |

Only one binding is selected per child. No model calls just to probe capability, no runtime configuration rewrites, hidden sessions or replay while another writer's state is uncertain. A compatibility route is not dynamic-effort success; missing runtime identity remains UNKNOWN.

| Responsibility | Model | Fixed compatibility effort |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` | `medium` |
| `terra_executor` | `gpt-5.6-terra` | `medium` |
| `sol_engineer` | `gpt-5.6-sol` | `medium` |
| `astra_architect` | `gpt-6-astra` | `high` |

Auto generates four `cer_auto_<role>` unpinned aliases alongside the four fixed bindings: **eight small TOML files, four responsibilities**, not eight running agents or extra capability tiers. Generated aliases add a short auto-effort discovery marker, change the name and remove the effort pin; model, instructions and permissions remain identical. The added discovery text has a small context cost rather than zero overhead.

Ordinary implementation normally uses medium; deeper reasoning may use high; automatic Astra remains high. Automatic low is off by default and retains explicit prior choice. xhigh/max require explicit intent and support. No mandatory weak-model ladder. A host lacking Sol/high does not make Sol/medium an acceptable substitute.

## Install and update

Review source first. Installation only manages owned files; it does not edit global config, authentication, permissions, AGENTS.md or unrelated Skills/agents. Keep the clone for lifecycle commands. Choose one installation scope.

### Windows / PowerShell

```powershell
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
.\cer.ps1 install --scope user --dry-run
.\cer.ps1 install --scope user
.\cer.ps1 doctor --scope user
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
.\cer.ps1 install --scope user --dry-run
.\cer.ps1 install --scope user
.\cer.ps1 doctor --scope user
```

On macOS/Linux, replace `./cer.ps1 <action>` with `python3 -B scripts/<action>.py` after checking Python is 3.11+. **No `--mode adaptive` is needed.** Ordinary updates migrate pre-v0.5 manifests to auto with a printed notice and backup, preserving the low choice. Old manifests did not record whether fixed/adaptive was deliberate or default; advanced users needing a previous policy can explicitly retain it. Later v0.5+ explicit overrides survive ordinary updates. Original unmanifested v0.1 installations still require safe `--adopt-v01` adoption. See [migration details](docs/INSTALL.md).

Review customization/collision errors instead of blindly adding `--force`. STATIC PASS is installation integrity, not live model proof. Reload Codex after updates; an old conversation can retain old instructions. A Skill-only copy does not deploy the role bindings: use the full installer.

### Project scope

```powershell
.\cer.ps1 install --scope project --project-root "C:/Work/my-project" --dry-run
.\cer.ps1 install --scope project --project-root "C:/Work/my-project"
.\cer.ps1 doctor --scope project --project-root "C:/Work/my-project"
```

On macOS/Linux use `python3 -B scripts/<action>.py` and a real absolute project path. User Skills go to `~/.agents/skills/codex-efficiency-router`; bindings to `$CODEX_HOME/agents` or `~/.codex/agents`. Project scope uses `.agents/skills` and `.codex/agents`. The installer prints actual backup paths.

## Use

```text
$codex-efficiency-router
Complete this task using suitable model/effort choices and the required acceptance checks.
```

Relevant substantial work may trigger implicitly; explicit invocation is clearer. The parent model remains unchanged. Simple permitted work stays local. Astra writes normally go to an executor; only the bounded root exception above applies. Do not stack routers. Disable/no-subagent/no-escalation requests remain authoritative. PASS/PARTIAL/BLOCKED depends on evidence for required outcomes; binding/model changes do not reset retries.

The native changed-files badge belongs to the task workspace and its own file-change events. If required, use the target repository and the same parent for writes. Normally that parent is Sol/Terra; root Astra qualifies only for its bounded local-patch exception. A repository outside the task workspace or a host that does not aggregate child `fileChange` events cannot guarantee the badge. The Router detects this before writes instead of treating an unstaged Review as equivalent. Writers still return repository-rooted exact paths; the parent verifies each repository, lists paths and opens supported Reviews.

## Uninstall and restore

Use the same scope, project root and CODEX_HOME as installation.

```powershell
.\cer.ps1 uninstall --scope user --dry-run
.\cer.ps1 uninstall --scope user
```

```sh
python3 scripts/uninstall.py --scope user --dry-run
python3 scripts/uninstall.py --scope user
```

For project scope use `--scope project --project-root ...`. Only manifest-owned files are removed; untracked files, configuration and backups survive. Local modifications block removal by default. Uninstall does not automatically restore an old version; there is no `--no-restore` option. Restore explicitly from the printed backup directory:

```powershell
.\cer.ps1 install --scope user --restore "ACTUAL-BACKUP-PATH" --dry-run
.\cer.ps1 install --scope user --restore "ACTUAL-BACKUP-PATH"
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

[Validation v0.6.0](docs/VALIDATION-v0.6.0.md)
