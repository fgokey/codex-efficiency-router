# v0.5.0 validation — 2026-09-08

Source baseline: `9a10e466ac374fd27e37f2e31bace0f232d79bdb`, tree
`9edffca71d9db74e66a8f5382c0bf531df2f0b71`. The mounted archive was verified by
Git tree identity, not its filename. The old source passed 180 local tests before edits.

## Local checks before publication

- 213 unittest methods passed; no failures, errors or skips.
- Eight retained boundary checks passed.
- Twelve routing and twelve quality mutations were detected.
- Twenty-seven effort/binding mutations were detected, including nine new automatic-binding mutations.
- Source doctor, compileall and Git whitespace checks passed.

Local mutation groups were run separately within the execution tool's time limits;
only assertion failures count as detections. The unchanged complete audit command
is also configured in CI. The local container could not install the pinned tokenizer;
local token numbers are not invented. The independent CI audit produces the named
encoding counts and enforces existing budgets before the tested commit enters main.

CI defines six platform/Python jobs (Windows/macOS/Ubuntu; 3.11/3.13) and one
offline audit. Check the workflow attached to the exact installed SHA. Raw JSON and
mutation logs are retained as workflow artifacts for 14 days, including failures.
This document does not assert success for a commit before its run completes.

## New coverage

Ordinary install and legacy upgrade select auto. Explicit v0.5+ overrides survive
updates. Eight generated bindings share four canonical policies. Tests check exact
alias generation, architect read-only settings, customization conflicts, unowned
alias collisions, migration notices, dry-run, rollback and byte-for-byte restore.

Runtime reference tests cover dynamic preference, missing fields, invalid aliases,
exact fixed fallback, unsupported high, unknown catalog, opt-out positive controls,
failed-binding cache, active-worker replay protection and shared retry budgets.
They test declared conditions, not live Codex capability detection or enforcement.

## Text measurement and honest limits

The audit measures fixed, adaptive and auto instruction paths and a declared
name/description rendering for four extra aliases. It adds a separate gate for auto
full instructions plus this discovery text; existing core/full/role budgets are not
raised. The rendering is not Codex's exact metadata serialization. Alias files are
not additional running workers, but discovery overhead is not claimed to be zero.

Actual model/effort, runtime binding selection, task quality, full usage and latency
remain user acceptance. No model inference, Codex login, hidden sessions, paid probes
or live A/B runs are invoked by installation or CI. [Design](ADAPTIVE-EFFORT.md) ·
[Acceptance](ACCEPTANCE.md) · [Offline audit](../evaluation/README.md).
