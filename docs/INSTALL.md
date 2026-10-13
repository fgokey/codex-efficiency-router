# Install, update, uninstall and restore

Copyable commands for Windows and macOS/Linux are in [README](../README.md#install-and-update) and [中文 README](../README.zh-CN.md#安装与更新). Use Python 3.11+, no third-party Python packages. Installation never calls an LLM. Ordinary installation preserves `config.toml`; explicit `--set-subagent-defaults` manages only missing child model/effort defaults, with conflict checks, backup and uninstall restoration. Parent settings remain unchanged.

Desktop session verification on 2026-10-12, before the high-default update: after writing the then-current two defaults, a fresh `agent_type=default`, `fork_turns=none` child without model/effort still observed `gpt-6-astra/high` in native `turn_context`. A fresh `cer_auto_sol61_engineer`, explicit `medium`, `fork_turns=none` child observed `gpt-6.1-sol/medium`. Config persistence is not proof of host/session adoption; the cause of the bare-default result is unverified. Engineering dispatch now selects high for unknown difficulty or medium for confirmed simple work using the explicit role/effort template in [effort.md](../skills/codex-efficiency-router/references/effort.md), checks native binding, then RELEASE. These are policy requirements; Guard registration was ABSENT during this verification.

## What is installed

The complete Skill directory, including four progressive references and UI metadata, plus five canonical roles and, in default auto, five generated native aliases. A `.cer-install.json` manifest records owner, schema, version and exact installed hashes. The clone's scripts, documentation and tests are not loaded into the model as runtime context.

The installed `scripts/` directory contains only `readonly_reader.py`, including its pure-stdlib `assignment` preflight. Run each Reader invocation alone in its tool call; use one Reader `batch` for independent checks under one total output budget. Do not concatenate page calls or mix `Get-Content`/queries into their output. Verify any script's real path before use. `ROOT/scripts/doctor.py --source-tree ROOT --preflight` is only for Router development, with `ROOT` the Router source repository; it is not an installed helper or a prerequisite for unrelated repository work.

Before a task-bearing send to an existing worker, run verified Python `-I -B <Skill>/scripts/readonly_reader.py assignment` with UTF-8 JSON on stdin (at most 16 KiB). Supply `unit_id`, `purpose` (`new_unit`, `continue`, `status`, `stop`), concise `scope`, exact work `message`, and `recipient` with observed `id`, `model`, `effort`, and a bounded `evidence_ref` naming the actual session/turn evidence. `signals` must explicitly set `spec_complete`, `authority_ready`, `environment_ready`, `observability_ready` to true. Engineering/review defaults to Sol61/high; confirmed simple medium needs `confirmed_simple=true` and current low-risk signals. Higher effort needs `effort_supported=true` and a concrete `effort_reason`. The existing-send entry does not establish a new spawn's identity: spawn with explicit role/effort, then verify actual binding before release.

Astra new work additionally requires current `signals.very_complex=true`, `complexity_reason`, and `signals.sol61_unsuitable_reason`. Self-reported `force_astra` cannot waive these checks. Success returns only short `prefix`, `body_sha256`, recipient `dispatch_arguments`, and a policy/scope/work fingerprint `receipt`. Check exit/status, verify the exact body hash, then send `prefix + message`; the shared `assignment_message` function rejects a changed body. Never validate one body and send another. The prefix includes readable parent complexity judgment and Sol61-unsuitable reason for Astra. Failure/UNKNOWN has nonzero exit and no execution parameters. Pure exact `continue`/`status`/`stop` (or `继续`/`状态`/`停止`) may supply the previous current-policy `receipt` and same scope/binding; additional body text always needs fresh admission. Pure waits need no preflight, rule reload, or repeated binding check; contradictions do require rechecking.

Receipts reference caller-supplied observed evidence; they are not signatures or host authentication. Native tools can bypass this policy-consumed entry. Canary shares its boundary checks for offline replay and does not prove live enforcement. No hook, trust setting, persistent ledger, background process, or model call is added. Installation updates files and future/reloaded role instructions; an existing live Astra child cannot hot-load receiver rules. Use a freshly bound Sol61 worker for ordinary new work; do not treat the old child's binding as current task admission. A hard host guarantee would require a separately trusted recipient-aware dispatcher; the current write Guard does not provide that guarantee.

Select either user scope or one explicit existing project root. Keep the repository clone to update/uninstall. `$CODEX_HOME` changes user agent and backup locations, not `~/.agents/skills`. Use the same scope, project and environment for subsequent operations. A project-root flag without project scope is rejected.

## Safe updates

Run `git pull --ff-only`, review changes, preview with `--dry-run`, then reinstall. Identical payloads are not rewritten. A known v0.1.0 installation without a manifest can be explicitly adopted using `--adopt-v01`. Exact legacy text blobs are checked, including CRLF normalization. Unknown/customized legacy files are not silently claimed.

Unowned filename collisions always stop installation. Existing managed-file edits stop it unless `--force` is explicitly supplied; that switch backs up only owned content. It cannot overwrite unrelated files. An unchanged, tool-owned medium child effort default migrates to high on update; a user-owned medium value blocks update and survives uninstall. Source validation occurs before any payload write. Do not edit configuration concurrently with installation.

An ownership manifest must explicitly include `skill/SKILL.md`. Doctor requires the current profile's complete managed inventory. Historical manifests may omit later-added files that are absent on disk and still upgrade normally. Uninstall refuses an existing standard payload path missing from ownership, even with `--force`, and preserves the manifest and files; disk presence never grants ownership.

## Uninstall and recovery

Uninstall reads the manifest, checks modifications, backs up affected bytes, removes only managed files and the manifest, and prunes only owned empty directories. Untracked files/directories and unrelated configuration survive. No manifest means no broad deletion; migrate legacy installations first. Backups survive uninstall.

`install.py --restore ACTUAL_BACKUP_PATH` validates package, original target paths and backup checksums before restoring prior bytes. It refuses intervening local changes unless reviewed and explicitly overridden. Restoring an uninstall restores that managed installation; restoring a first install removes only its originally absent managed files. A restoration itself creates a backup.

## Safety limits and troubleshooting

- Each file uses atomic replacement. Ordinary write exceptions trigger rollback of already-written files. The collection of different files is **not atomic across process termination or power loss**; inspect and use the retained backup after interruption.
- The lock prevents simultaneous package lifecycle commands sharing that backup location. If a crash leaves `.lock`, first ensure no installer is running, inspect the affected files and backup, then remove only that stale lock manually. Do not automatically retry over it.
- Symlinks and Windows junction/reparse targets are rejected. Choose a real trusted configuration directory; this is not a defense against a malicious process racing local filesystem writes.
- Backups may contain private custom instructions. Do not upload them or authentication files in bug reports. The project-local `.codex-router-local/` directory should remain ignored in your project.
- No bundled script needs administrator access or a disabled sandbox. Direct Python commands avoid PowerShell script policy changes; shell wrappers may be invoked with `sh`.
- Restart/reload Codex if roles/Skills are stale. Uninstalling cannot erase text already loaded into an existing conversation. Duplicate user/project installs can leave another copy visible.
- Manually merged optional config defaults are not owned by the installer and are not automatically undone. Remove those specific user-added keys manually only when appropriate; never replace the entire config from an old backup.

## Automatic default and advanced compatibility

Ordinary `install.py` needs no mode flag. Auto installs five pinned roles and five generated unpinned aliases; parent selection uses only one per child. Pre-v0.5 manifests migrate to auto with a printed notice; backups preserve the old mode and user edits still stop replacement. Old manifests cannot identify deliberate mode preference. A v0.5+ explicit override is persisted with profile schema 2 and respected on updates.

Advanced compatibility only (not required for normal use): `--mode fixed`, `--mode adaptive` or `--mode auto`. Existing fixed/adaptive automation remains supported. `--allow-low` is optional and separately gated; `--no-allow-low` disables it. Fixed cannot enable low. These options do not inspect credentials or prove native host capability.

Explicit restore retains the original mode/bytes, including legacy manifests; it does not migrate them. Auto uninstall removes all ten owned bindings, not unrelated aliases or user files. Switching an advanced override removes obsolete owned aliases safely. A collision on any generated filename blocks before writes, even with force.

Python CLI flags are canonical. PowerShell wrappers forward `--scope`, `--dry-run`, etc., not PowerShell-style aliases. There is no `--no-restore`; restoration is `install.py --restore`. Actual dynamic-vs-compatibility selection needs no configuration change. See [acceptance](ACCEPTANCE.md).

## Candidate v0.7.0-rc.1

Use the [candidate upgrade guide](UPGRADE-v0.7.0-rc.1.md) for an extracted unpublished
ZIP. Do not use git pull to replace it with upstream main. Existing profile schema-2
fixed/low choices survive ordinary updates. Installation manifests now include the base
commit and the actual rendered policy hash; the base commit is not a claim that edited
candidate bytes were committed. Full distributions include a separate per-file release
manifest. Guard registration remains explicit and independent of Skill installation.
Rollback preserves concurrently changed files instead of overwriting them with backup
bytes; inspect reported recovery gaps. Multi-file power-loss atomicity is not promised.
