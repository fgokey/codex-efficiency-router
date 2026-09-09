# Astra write boundary and active diagnostic participation (v0.6)

## Two independent decisions

A model's ability to solve a task is not permission to write. Before any side effect,
check the actor, authorization and exclusive owner; only then select a model/effort
and consider cost. The gate outranks all tiny-task, sufficient-parent, unavailable
binding and exhausted-slot local fallbacks. It applies to Astra **roots and leaves**,
not just the `astra_architect` TOML sandbox setting. Auto/fixed/adaptive do not alter it.

Astra may read source, inspect existing diffs/logs, reason, propose patches as text,
coordinate owned agents, and accept/reject evidence. It must not apply patches, write
reports/checkpoints, format, generate, build, execute side-effecting tests, mutate Git
or publish/deploy. Unknown effect/identity is not permission. Read-only responsibility
also remains if a coordinator changes models; role changes need explicit reassessment.

## Astra must still participate

Hard consequential decisions need not wait for a weaker model to fail. After two
qualified attempts with an unexplained or capability failure, stop blind editing and
bring the unresolved question to Astra with original requirements, actual diff, failure
history and evidence. Retry counts, missing dependencies and absent observations alone
are not proof that stronger reasoning will solve the problem.

If the parent is already Astra, it investigates directly in read-only mode rather than
spawning another Astra merely to think. It can reconcile hypotheses, design a safe
minimal experiment and propose precise changes. Executors perform experiments/builds
and return results. Once the decision is stable, reuse Sol/Terra for implementation.
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
Unknown writer state or potentially completed side effects must be reconciled, not replayed.
Business-specific agent names and file counts are not hardcoded in this Skill.

## What is enforced, and where

1. **Skill policy:** always loaded on invocation; no root tool revocation is claimed.
2. **Offline references:** `write_policy.py` and the operation-aware joint planner test
   declared authorization, writer capacity, reuse and diagnostic admission. Legacy
   lane-only planner results describe reasoning recommendations, never write permission.
3. **Native synchronous Hook:** `hooks/astra_write_guard.py` emits documented
   `PreToolUse` denial for covered Astra/unknown-model side effects. It acts on the host's
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

Rerun guard registration after updating this repo to update its owned scripts; review
changes and inspect trust again. Native trust is never inferred by the installer.

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

These sources define the host contract. Strict Astra write separation, qualified
failure escalation, the reader protocol and writer ownership are this project's policy,
not OpenAI's guarantee that an arbitrary Skill is enforced.
