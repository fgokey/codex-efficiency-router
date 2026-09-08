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

## Executed remote validation and measurements

Code commit: `1271d5b8fde9ce073035174cdd751b0885cc32d0`, tree
`37267aa1ca8a100899a129bfe75b6a9531d4a427`. The [exact CI run](https://github.com/fgokey/codex-efficiency-router/actions/runs/34230042864)
completed successfully in all seven jobs. Its audit confirms 213 tests with zero
failures/errors/skips, 8/8 retained boundaries, and 51/51 selected mutations detected
(12 routing, 12 quality, 27 effort/binding). The report's working tree was clean;
all reported source SHA-256 values matched the locally tested payload. Local and
uploaded Git trees were identical before publication.

[Raw report and logs](https://github.com/fgokey/codex-efficiency-router/actions/runs/34230042864/artifacts/10057376800)
are retained for 14 days. Artifact ZIP SHA-256:
`204d5b8c92621ba90a0dd60cc87f266402e72fa15faf254770e6483fb2a30b11`.

Pinned `tiktoken==0.11.0`, raw instruction text only:

| Measured text | o200k_base | cl100k_base |
| --- | ---: | ---: |
| v0.5 auto core | 1,085 | 1,091 |
| v0.5 auto core + all references | 1,953 | 1,962 |
| Additional four alias name/description strings | 67 | 67 |
| Auto full text plus that additional discovery rendering | 2,020 | 2,029 |
| Immutable v0.2.1 full-text budget baseline | 2,074 | 2,093 |

Both the pre-existing instruction gates and the additional discovery-inclusive gate
passed. Fixed/adaptive low-off variants produced the same token totals as auto
under these two encodings; their byte counts differ by the installation marker.
Auto core is 5,565 UTF-8 bytes and auto full text is 10,254 bytes. Byte/token limits
were not raised to accommodate compatibility bindings.

The 67-token discovery rendering is an explicit measurement format, not Codex's
actual role-metadata serialization. Do not infer zero role-discovery overhead,
exact Astra billing, whole-task savings or fewer model retries. All four model
encoding lookups remain UNKNOWN in the pinned tokenizer. Parent context, tool
framing/results, generated reasoning/output and actual task latency are unmeasured.
These results refer to the exact code commit above; any documentation-only follow-up
commit must be checked against its own CI rather than inheriting success by claim.
