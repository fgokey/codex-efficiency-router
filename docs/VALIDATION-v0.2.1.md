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
