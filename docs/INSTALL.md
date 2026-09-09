# Install, update, uninstall and restore

Copyable commands for Windows and macOS/Linux are in [README](../README.md#install-and-update) and [中文 README](../README.zh-CN.md#安装与更新). Use Python 3.11+, no third-party Python packages. Installation never calls an LLM or edits `config.toml`.

## What is installed

The complete Skill directory, including four progressive references and UI metadata, plus four canonical roles and, in default auto, four generated native aliases. A `.cer-install.json` manifest records owner, schema, version and exact installed hashes. The clone's scripts, documentation and tests are not loaded into the model as runtime context.

Select either user scope or one explicit existing project root. Keep the repository clone to update/uninstall. `$CODEX_HOME` changes user agent and backup locations, not `~/.agents/skills`. Use the same scope, project and environment for subsequent operations. A project-root flag without project scope is rejected.

## Safe updates

Run `git pull --ff-only`, review changes, preview with `--dry-run`, then reinstall. Identical payloads are not rewritten. A known v0.1.0 installation without a manifest can be explicitly adopted using `--adopt-v01`. Exact legacy text blobs are checked, including CRLF normalization. Unknown/customized legacy files are not silently claimed.

Unowned filename collisions always stop installation. Existing managed-file edits stop it unless `--force` is explicitly supplied; that switch backs up only owned content. It cannot overwrite unrelated files. Source validation occurs before any payload write. Do not edit configuration concurrently with installation.

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

Ordinary `install.py` needs no mode flag. Auto installs four pinned roles and four generated unpinned aliases; parent selection uses only one per child. Pre-v0.5 manifests migrate to auto with a printed notice; backups preserve the old mode and user edits still stop replacement. Old manifests cannot identify deliberate mode preference. A v0.5+ explicit override is persisted with profile schema 2 and respected on updates.

Advanced compatibility only (not required for normal use): `--mode fixed`, `--mode adaptive` or `--mode auto`. Existing fixed/adaptive automation remains supported. `--allow-low` is optional and separately gated; `--no-allow-low` disables it. Fixed cannot enable low. These options do not inspect credentials or prove native host capability.

Explicit restore retains the original mode/bytes, including legacy manifests; it does not migrate them. Auto uninstall removes all eight owned bindings, not unrelated aliases or user files. Switching an advanced override removes obsolete owned aliases safely. A collision on any generated filename blocks before writes, even with force.

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
