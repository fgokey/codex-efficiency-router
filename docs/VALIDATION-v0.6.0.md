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

## Executed code validation

Code commit: `d3407aae356a3a4d150250ca7dfe75b136dce4cc`; tree
`2272838fb2142cc4df684eecc519db002402ca7a`. This tree exactly matched the local
staged source. The [exact run](https://github.com/fgokey/codex-efficiency-router/actions/runs/34318247159)
completed successfully in all seven jobs: Windows/macOS/Ubuntu with Python 3.11 and
3.13, plus the independent offline audit. Both downloaded reports' source hashes
match all corresponding local files, including the hook scripts and new write gate.

- Unittest: **278 passed**, zero failures/errors/skips, including 36 existing routing scenarios.
- Retained boundary probes: **8/8 passed**.
- Selected mutations: **63/63 detected by assertions** (12 routing, 12 quality,
  27 effort/binding, 12 new write/diagnostic mutations). Crashes are not detections.
- New tests include real guard subprocesses inside a synthetic host: Astra sentinel
  mutators were not called; Sol writes and guarded file/diff reads worked. These do
  not establish live Codex hook delivery, trust, permission coverage or model quality.
- Local full suite also passed; source doctor, compilation and whitespace checks passed.

[Raw reports and logs](https://github.com/fgokey/codex-efficiency-router/actions/runs/34318247159/artifacts/10090849753)
are retained for 14 days. Downloaded ZIP SHA-256:
`598504ba8fd3f5a5ce09738333d8d083b16be28652d03b414e315a76e43236b5`.

### Instruction footprint, not live task consumption

Pinned `tiktoken==0.11.0`; raw text counts only:

| Auto instruction text | o200k_base | cl100k_base |
| --- | ---: | ---: |
| Core | 1,120 | 1,128 |
| Core + all references | 1,989 | 2,009 |
| Additional alias-name/description rendering | 67 | 67 |
| Full plus that rendering | 2,056 | 2,076 |
| Existing discovery-inclusive ceiling (v0.2.1 baseline) | 2,074 | 2,093 |
| Astra role instructions alone | 196 | 196 |

Against the published v0.5 o200k counts, core increases from 1,085 to 1,120 and
full text from 1,953 to 1,989. This is a small measured instruction increase for the
new boundary and active-diagnosis rules, not a claimed reduction. Existing core/full,
role and discovery-inclusive gates passed without raising thresholds. The alias
rendering is not the host's exact serialization. Hook scripts are not prompt text;
hook startup, denied-call retries and reader execution have unmeasured runtime costs.
All model/tokenizer lookups remain UNKNOWN in the pinned library. Host framing,
reasoning/output, retries, real quota, end-to-end time and live task quality are excluded.

These observations belong to this exact code commit. A documentation-only publication
commit must be checked against its own CI result; real native enforcement still needs
user acceptance. No Codex model calls or paid model probes were performed.
