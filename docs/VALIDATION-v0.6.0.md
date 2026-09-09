# v0.6.0 write boundary validation — 2026-09-09

Source baseline: `fdccefff38f014a312e8057d87dab5129a5c6c35`, tree
`b705e66f8a60b6a1ed9f0358fe0c8e69332356e8`. The mounted archive was verified
against that tree. Its 213 tests passed before this change.

## New boundaries

- Actor write authority precedes local/cheap/sufficient-parent shortcuts, including
  privileged Astra roots, read-only coordinators, unknown identity and opaque effects.
- Already-active and idle compatible writer reuse obeys an explicit two-active-writer
  limit; old edits are preserved for review rather than reverted or blindly rewritten.
- Astra actively handles complex decisions and qualified repeated unexplained failures.
  Write retry exhaustion does not forbid a separately scoped read-only diagnosis.
- Optional native synchronous PreToolUse interception uses real model metadata and
  documented deny/updatedInput outputs. It never treats shared parent session IDs or
  tool arguments claiming to be Sol as proof of actor identity.
- Shell-only source inspection uses a bounded read adapter, not arbitrary shell
  allowlisting. Shared hook registration/removal preserves other groups and refuses
  local/concurrent edits rather than overwriting them.

## Evidence categories

Unit/policy/mutation tests examine declared conditions; synthetic-host tests invoke the
real guard process and verify a deliberately denied mutator was not called, while Sol
writes and guarded source/diff reads behave as expected in the harness. This is NOT a
live Codex hook trust/delivery/enforcement test. The normal installer does not register
hooks; explicit guard registration affects its entire config scope and requires trust.

Local tests before publication include existing regression/lifecycle tests, new writer
and diagnostic gates, guard protocol/sentinel tests, hook lifecycle tests and selected
mutation cases. Source doctor, Python compilation and whitespace checks are required.
Exact totals, remote platform status and tokenizer counts belong to the final emitted
CI report. No result is transferred to a different commit by assumption.

The local container cannot install the pinned tokenizer because package networking is
unavailable; no local text-token savings are invented. Existing core/full/discovery
budgets are retained and enforced in the independent CI audit. No paid model or Codex
cloud task is invoked by installation or any of these offline tests.

## Remaining user acceptance

Follow [WRITE-GATE](WRITE-GATE.md) for project-scoped registration, trust and live
canary. Untrusted/skipped hooks, missing interpreters, host bugs, hosted/specialized
paths, pre-existing write_stdin sessions and hostile local actors are not complete
isolation guarantees. Native read-tool semantics and local binaries are trusted.
Actual model/effort identity, task quality, total tokens and time remain user acceptance.
Astra's no-local-write policy and its active diagnostic duty are both required; neither
is a justification to stop reasoning or to reset failed implementation attempts.
