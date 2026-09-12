# Astra write boundary and active diagnostic participation (v0.7.0-rc.5)

## Two independent decisions

A model's ability to solve a task is not permission to write. Before any side effect,
check the actor, authorization and exclusive owner; only then select a model/effort
and consider cost. The gate outranks tiny-task, sufficient-parent, unavailable-binding
and exhausted-slot fallbacks. Unknown effect/identity is not permission.

All Astra leaves and read-only roles stay read-only. Root Astra also defaults read-only,
but can apply **one bounded local code patch** when every condition below is observed:

1. Two qualified executor attempts failed on the same task/unit/failure signature for a
   classified implementation, capability or unexplained issue, or a handoff would
   materially lose reasoning context needed for the fix. Prerequisite, environment,
   specification and observability gaps do not qualify.
2. The user authorized the change; exact files/scope, verification and safe boundary are
   known; the target repository is the current task workspace.
3. Ownership is exclusive, no writer is active, and no earlier root exception was used.
4. An observed active strict Guard is absent. UNKNOWN does not grant host permission:
   the policy may request the patch, but an unobserved active Hook can still deny it.

This exception covers the patch only. It does not cover arbitrary shell, formatting,
builds, side-effecting tests, Git mutation, publishing or deployment. Sol/Terra performs
those steps. Missing evidence fails closed to reuse/delegation/defer/BLOCKED. High risk,
task size, an Astra model selection, or a no-subagent request alone does not grant it.
Auto/fixed/adaptive do not alter the boundary.

## Astra must still participate

Hard consequential decisions need not wait for a weaker model to fail. After two
qualified attempts with an unexplained or capability failure, stop blind editing and
bring the unresolved question to Astra with original requirements, actual diff, failure
history and evidence. Retry counts, missing dependencies and absent observations alone
are not proof that stronger reasoning will solve the problem.

If the parent is already Astra, it investigates directly rather than spawning another
Astra merely to think. It reconciles hypotheses and designs a minimal experiment.
Executors normally perform experiments/builds and return results. Once the decision is
stable, reuse Sol/Terra unless the bounded root exception above is fully established.
An exhausted repair budget does NOT forbid a separately scoped diagnosis and does NOT
get reset by that diagnosis. An explicit bounded parent reassessment is needed for more
repairs. Missing observations may justify an instrumentation-design subtask, not an
invented root cause. User no-escalation/no-subagent constraints still apply.

## Existing edits and writers

Do not reset/revert edits merely because Astra made them. Mark their provenance and
unverified status; pass the current diff, requirements, affected paths, environment and
remaining attempts to a compatible owner. That owner independently reviews the actual
changes, preserves correct work, adds required tests and acknowledges ownership before
further modification. Reviewing a patch does not require rewriting it.

Prefer the existing compatible Sol/Terra owner at a safe boundary. Busy owners finish
or acknowledge the handoff before expanding scope. Two active writers means wait; an
idle third owner must not start alongside them. Shared integration files have one owner.
Astra can diagnose against stable evidence while writers exist; it is not a third writer.
Its bounded patch exception requires no active writer.
Unknown writer state or potentially completed side effects must be reconciled, not replayed.
Business-specific agent names and file counts are not hardcoded in this Skill.

## What is enforced, and where

1. **Skill policy:** always loaded on invocation; no root tool revocation is claimed.
2. **Offline references:** `write_policy.py` and the operation-aware joint planner test
   declared authorization, writer capacity, reuse and diagnostic admission. Legacy
   lane-only planner results describe reasoning recommendations, never write permission.
3. **Optional strict native Hook:** `hooks/astra_write_guard.py` emits documented
   `PreToolUse` denial for every covered Astra/unknown-model side effect, so it disables
   the bounded root exception in its scope. Unknown Hook state remains a runtime outcome,
   not proof of denial or success. It acts on the host's
   `model`, not prompt text, `tool_input.model`, or the parent's shared `session_id`.
4. **Host acceptance:** trust, event delivery and actual prevention must be checked in
   the intended Codex version. A synthetic-host test is NOT that live acceptance.

Normal Skill installation does **not** modify a shared hooks file. A separate explicit
registration is necessary because it affects every Astra/unknown-model call within
that Codex configuration scope, including tasks that do not activate this Skill. It is
not a model-routing mode and never rewrites modes during execution. Prefer project
scope; one-time review/trust must not be bypassed.

## Install the native guard once (optional but required for tool interception)

From this repository, for an existing project:

```powershell
py -3 scripts/write_guard.py install --scope project --project-root "C:/Work/my-project" --dry-run
py -3 scripts/write_guard.py install --scope project --project-root "C:/Work/my-project"
py -3 scripts/write_guard.py status --scope project --project-root "C:/Work/my-project"
```

macOS/Linux: replace `py -3` with `python3` and use a real project path. User-wide
registration uses `--scope user` without a project root; it affects all sessions in
that user config layer. Reopen Codex and review the exact definition with `/hooks`.
Untrusted/disabled/unsupported hooks provide no runtime protection. Never use a trust
bypass flag, change global permissions, or pass a fake model to make a call succeed.

Registration merges one exact group into `.codex/hooks.json`, copies two self-contained
scripts under `.codex/hooks/cer-astra-write-guard/`, and records ownership/checksums.
Other hook groups, config.toml and authentication remain unchanged. Existing group
changes, duplicate ownership, unowned collisions, symlinks and edited scripts stop the
operation. Dry-run does not write; ordinary write failures roll back; backups are retained.
Operations across files are not power-loss atomic. Do not restore an old shared
hooks.json over newer user changes; reconcile its own group using the backup.

Guard files are independent of the installed Skill. Normal Skill uninstall intentionally
does not silently remove this protection; remove it explicitly, then reload Codex:

```powershell
py -3 scripts/write_guard.py remove --scope project --project-root "C:/Work/my-project" --dry-run
py -3 scripts/write_guard.py remove --scope project --project-root "C:/Work/my-project"
```

Use explicit `write_guard.py update` for an existing owned registration; review
changes and inspect trust again. `update` does not implicitly install an absent Guard.
Native trust is never inferred by the installer. The Hook command includes the
version and current guard+reader bundle digest, so changes are visible to definition
review. A digest mismatch denies covered calls, including executor calls, until reviewed.
Exact base model IDs in the audited executor allowlist are used; unknown snapshot
suffixes are not accepted by prefix similarity. Normal executors return no additional
permission decision; the host sandbox and other Hook decisions remain in force.

## Source inspection without an arbitrary shell

The strict hook denies ordinary Bash from Astra, including commands named `check` or
marked dry-run; shell snippets cannot be reliably classified by a name blacklist.
Exact trusted native read and orchestration tools remain available. For shell-only
file access, use the ordinary Bash tool with a **guard protocol** request:

```text
cer-read {"op":"read","path":"src/component.cpp","start":1,"lines":120}
cer-read {"op":"search","path":"src/component.cpp","query":"shutdown"}
cer-read {"op":"list","path":"src"}
cer-read {"op":"diff","path":"src/component.cpp"}
cer-read {"op":"status","path":"."}
```

`cer-read` is NOT a binary installed on PATH. A trusted supported PreToolUse hook
validates its JSON and rewrites it to an isolated `python -I -B` reader with quoted
arguments. No arbitrary code or subprocess arguments are accepted. File operations
are bounded to the host-reported workspace; symlink/path escapes are rejected. Diff
and status use fixed Git argv without a shell, external diff/textconv, pager, optional
locks or fsmonitor. Trusted local OS/binaries/filesystem remain assumptions.

If the hook is not installed or rewriting isn't supported, do NOT execute the marker
as a guessed command or replace it with unrestricted shell. Use exposed read tools or
ask an authorized executor for the required evidence. The guard has no model call,
state/trace file or recurring success message; local process startup still has a cost.

## Coverage limits and live canary

Current official docs state hosted tools and some specialized paths bypass these hooks;
`write_stdin` does not run PreToolUse again for an existing exec session. Do not use a
pre-existing shell to bypass the restriction. Close/reconcile inherited shells at a safe
boundary using authorized owners. Do not kill in-flight writers merely to install this.

Missing/invalid input in the guard produces the documented deny shape, not unsupported
`continue:false` or `ask`. An interpreter missing, timeout, skipped hook or host bug is
outside that guarantee. Native read-tool names assume trusted host semantics. This is
not hostile-code containment, OS process isolation, writer-ownership enforcement or a
complete protection against an authorized actor altering guard files.

Before relying on it, use a disposable project: deliberately request an Astra patch and
shell sentinel write, verify the tools did NOT run and files/state stayed unchanged;
then verify a legitimate Sol write works and Astra read/orchestration still works.
Include malformed metadata, disabled/untrusted hook, unsupported tool path, same-session
Sol and active shell cases. Report coverage gaps as UNKNOWN/unprotected, not PASS. This
live canary consumes model work if run through Codex and is not started by CI or installers.

## Primary references (checked 2026-09-09)

- [Codex Hooks](https://developers.openai.com/codex/hooks): synchronous PreToolUse,
  canonical names, host model identity, shared parent session ID, deny/updatedInput
  shapes, trust review and explicit coverage exceptions.
- [Codex Subagents](https://developers.openai.com/codex/subagents): parent sandbox
  inheritance and live permission overrides; don't make all writers read-only to
  compensate for a coordinator policy.

These sources define the host contract. The Astra default boundary, strict optional
Guard, bounded root exception, failure escalation, reader protocol and ownership are project policy,
not OpenAI's guarantee that an arbitrary Skill is enforced.

## v0.7 status and batching

`write_guard.py status --json` and `doctor --json` are read-only diagnostics for the
selected standalone registration layer: ABSENT/PRESENT/OUTDATED/BROKEN, interpreter
existence, actual bytes, version drift, duplicated/overlapping definitions, UNKNOWN
trust and NOT_RUN/STALE/FAIL/PASS/UNKNOWN evidence. No trustworthy access to Plugin or
other configuration layers is inferred. See [upgrade](UPGRADE-v0.7.0-rc.1.md) and
[explicit operator-witnessed Canary](CANARY.md); native evidence is never prebundled.

```text
cer-read {"op":"batch","requests":[{"op":"status","path":"."},{"op":"search","path":"src/component.cpp","query":"Owner"},{"op":"read","path":"src/component.cpp","start":1,"lines":120}]}
```

Batch limit: 16 operations; 16 KiB input; 16 MiB combined file reads plus at most one
byte of overflow detection; 128 KiB returned body. All requests/paths preflight before
execution. Search remains one literal file, not recursive directory scanning. Aggregate
output failure emits no partial batch. Git uses a bounded output pipe and timeout, not
an unbounded capture or an output temp file. This does not bound Git's internal scanning
or eliminate local path TOCTOU; trusted local binaries/filesystem remain assumptions.

Source references for candidate packaging: [OpenAI Plugin guide](https://developers.openai.com/plugins/build/plugins)
and [portable Plugin schema](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json).
Native scope/trust restrictions remain governed by the host version, not this package.
