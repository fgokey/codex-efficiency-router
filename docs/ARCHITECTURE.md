# Architecture — v0.5

One Codex-only Skill with four role responsibilities and generated native bindings and offline maintenance tools. Preserve required correctness and authorization while reducing avoidable reasoning, context and coordination. Monetary cost, tokens and elapsed time are separate; no universal savings or quality guarantee.

## Layers

1. The current coordinator reads the compact Skill and only needed references: routing, dispatch, effort, quality. No classifier inference, per-turn script or mandatory ledger.
2. Four canonical roles retain models, policy and permissions. Auto also generates four unpinned aliases; native capabilities choose one binding per child. No runtime file switch or duplicate workers. Parent owns requirements/integration; leaves cannot recursively delegate or publish. Astra stays read-only.
3. Offline tools generate/install profiles, validate structure, compare supplied runs and test reference rules. They are not a live dispatcher or enforcement layer and are not installed as runtime scripts.

## Joint selection and acceptance

Parent chooses a sufficient model/effort pair; actual delegation also requires host support, compatible role pins, supported pair, authorization and benefit. Identical pairs need contextual value and benefit. Raising effort is not guaranteed to fix a capability gap. Insufficiency cannot be repaired by lowering the same unresolved task's model or effort. No-escalation constrains both axes.

The execution contract includes IDs, revision, required outcomes/checks, facts versus assumptions, relevant state, invariants, scope, pair and remaining attempts. Receivers check conflicts before edits. Parent checks final-state coverage and integration; unit PASS is not project PASS. Contrary evidence reopens a decision.

Only long tasks/recovery need one permitted task checkpoint. Keep failed approaches, attempts, valid completed units and active-worker state. Reconcile uncertain effects before replay. Model/effort/worker changes do not renew attempts. Unknown or mismatched actual identity suspends automatic low for the rest of the task, even after later verified medium work. See [quality protocol](QUALITY-PROTOCOL.md) and [effort design](ADAPTIVE-EFFORT.md).

## Generation and ownership

Canonical `agents/*.toml` is fixed. Auto derives unpinned aliases and installs eight bindings from four definitions. The parent picks the alias when native explicit effort works or the exact fixed pair otherwise. New and legacy ordinary installs use auto; v0.5+ explicit overrides survive updates. Manifest/backup ownership covers aliases and original files; no credentials or runtime probes.

Hash ownership, collision checks, local-edit detection, backups and ordinary-failure rollback remain. Uninstall removes only owned files; restore is explicit. Per-file atomic replacement is not multi-directory power-loss atomicity. [Lifecycle](INSTALL.md) · [Security](../SECURITY.md).

## Sources of truth

Runtime behavior: [SKILL.md](../skills/codex-efficiency-router/SKILL.md) and its references. Canonical roles: `agents/*.toml`, checked against `scripts/package.py` and policy metadata. `effort_reference.py` is the new joint helper; the legacy lane-only helper remains for historical regressions. All consume declared conditions, not live telemetry. [User acceptance](ACCEPTANCE.md) establishes actual host behavior.
