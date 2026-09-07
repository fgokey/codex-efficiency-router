# v0.2.1 offline hardening — 2026-09-07

Baseline runtime: `7111d7d2b83f330c9f0e693a74fe97c5ea4dec1b`.

The known same-lane admission gap and opt-out test coverage gap are addressed by
explicit contextual-reason/benefit gating and causal tests with available routes.
The same unresolved task cannot move downward while current capability is insufficient.
Four model presets remain unchanged. Default uninstall still removes owned files;
restoration is explicit and no `--no-restore` option exists.

Core and reference duplication has been reduced; budgets now include ALL references,
not only the entry file. The package uses two plain single-line frontmatter scalars; ambiguous/duplicate metadata is rejected before installation. Doctor enforces project byte limits and separate tokenizer CI
checks two named reference encodings against immutable historical source.

The original failed evaluation remains in the historical evaluation branch and commits.
This document does not transfer old CI results to a new commit. See the workflow for
the exact installed commit and the emitted report/source hashes for measured results.

Live model discovery, actual model/effort, permissions, task-quality non-inferiority,
whole-task tokens and elapsed time are **NOT VERIFIED** by this release's offline tests.
The user performs [installation acceptance](ACCEPTANCE.md); no Codex task or model API
is launched by the installer or offline audit. [Method](../evaluation/README.md).

## Executed local checks

- 82 unittest methods: PASS, no failures/errors/skips, including the 36 existing scenarios.
- Eight retained boundary probes: 8/8 PASS; the historically failing same-lane probe is unchanged.
- Twelve selected mutations: 12/12 detected by assertion failures, including the previously surviving opt-out deletion.
- Real historical v0.2 install -> current upgrade -> installed doctor -> uninstall: PASS in a temporary project.
- Source doctor, compileall and Git whitespace check: PASS.

These are finite offline checks, not a universal correctness proof. Token counts and
remote-platform results are recorded from their own emitted CI report, not inferred
from these local checks. The historical v0.2 core was 7,206 bytes; current core is
6,239 and current core plus all references (one separator per file) is 11,298 bytes.

## Executed cross-platform CI and text-token measurements

Code and evaluation commit: `22c633ef8883f0eaa7de51a8033f6637fd2ffe53`.
The [exact run](https://github.com/fgokey/codex-efficiency-router/actions/runs/34131004327)
completed successfully. All seven jobs passed: Ubuntu/Windows/macOS with Python
3.11 and 3.13, plus the independent offline mutation/text-token audit. Its report
confirms 82 tests with zero failures, errors or skips, 8/8 retained boundaries and
12/12 selected mutations detected. The checked-out tree was clean and its source
SHA-256 hashes matched the locally tested payload. The temporary read-only source
snapshot workflow is absent from the released tree; no history was rewritten.

The [original report and logs](https://github.com/fgokey/codex-efficiency-router/actions/runs/34131004327/artifacts/10022059486)
are retained for 14 days. Artifact SHA-256:
`af99a019a1584126f239dc51a58d291848425c59011d889eeb3721bfca607083`.

Pinned `tiktoken==0.11.0`, raw text only:

| Loaded instruction text | o200k_base | cl100k_base |
| --- | ---: | ---: |
| Historical v0.1 core | 2,511 | 2,541 |
| v0.2.0 core | 1,354 | 1,359 |
| v0.2.0 core + both references | 2,793 | 2,805 |
| v0.2.1 core | 1,155 | 1,168 |
| v0.2.1 core + dispatch | 1,653 | 1,667 |
| v0.2.1 core + ALL references | 2,074 | 2,093 |

Under o200k_base, the new core is 14.7% smaller than v0.2.0; full reference loading
is 25.7% smaller than v0.2.0 and 17.4% below even the original v0.1 core. Thus the
previous full-load instruction-overhead regression is closed under both measured
reference encodings, without asserting anything about whole-task billing.

All four model-to-tokenizer mappings remain UNKNOWN in the pinned library. These
counts exclude host framing, tools, task context, inherited history, model reasoning,
output, verification and retries. They are NOT exact Astra billing, real task token
savings, speedup, model-quality equivalence, or subscription-quota conversion.
User [acceptance](ACCEPTANCE.md) remains the authority for actual runtime behavior.
Any later commit must be judged by its own workflow result; this section records
only the exact code/evaluation commit above.
