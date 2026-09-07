# Architecture (v0.3)

One Codex-only workflow; no external agent runtime. Optimize accepted completion, total tokens and elapsed time subject to correctness and authorization. Prices, tokens and duration are separate quantities; no universal savings or non-inferiority guarantee.

## Layers

1. On-demand Skill: current coordinator applies a compact policy. Three references cover ambiguous routing, native dispatch and quality/recovery exceptions; none is preloaded wholesale. No classifier inference or per-turn script.
2. Native Codex roles: four pinned model/effort presets; Astra is read-only. Leaves cannot recursively delegate or publish. Parent owns intent, integration, permissions and final acceptance.
3. Offline development tools: installer/lifecycle, static doctor, policy/quality reference functions, paired-data comparison, regression/mutation/token audit and user-run prompt corpus. These are not a live dispatcher or enforcement layer and are not copied into the runtime Skill.

## Capability versus acceptance

Routing recommends sufficient capability; actual dispatch separately depends on host support, user opt-outs and benefit. Same-lane delegation needs contextual value AND benefit. Insufficient capability cannot be repaired by downgrading the same unresolved task.

A compact contract identifies task/unit, revision, required outcomes, evidence/assumptions, state, invariants, scope and remaining attempts. Receiver checks conflicts before editing. Parent verifies current-state criterion coverage and integration; unit PASS is not project PASS. New authoritative requirements reopen the contract without erasing history.

Retry allowance belongs to the task/unit/failure, across agents and compaction. Recovery reconciles actual files, active workers and unknown side effects before replay. Use one permitted task-scoped checkpoint only when needed, not a permanent ledger per call. See [quality protocol](QUALITY-PROTOCOL.md).

## Distribution and ownership

The Skill packages three references and UI metadata. Four role names remain compatible. Hash manifests protect owned install files, detect edits, refuse unowned collisions, preserve user additions and retain backups. Atomic per-file replacement plus ordinary-exception rollback is not a power-loss-atomic multi-file transaction. [Lifecycle](INSTALL.md) · [Security](../SECURITY.md).

## Sources of truth

Runtime policy: [SKILL.md](../skills/codex-efficiency-router/SKILL.md) and packaged references. Presets: `agents/*.toml`, checked against package constants and policy metadata. Offline semantics: `policy_reference.py` and `quality_reference.py`. Source text and selected test cases are measurable; model compliance and real efficiency require [user acceptance](ACCEPTANCE.md).
