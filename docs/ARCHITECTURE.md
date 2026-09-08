# Architecture — v0.4

One Codex-only Skill with four native roles and offline maintenance tools. Preserve required correctness and authorization while reducing avoidable reasoning, context and coordination. Monetary cost, tokens and elapsed time are separate; no universal savings or quality guarantee.

## Layers

1. The current coordinator reads the compact Skill and only needed references: routing, dispatch, effort, quality. No classifier inference, per-turn script or mandatory ledger.
2. Four native roles keep their names, model identities and permissions. Astra is read-only. Fixed installs pin effort; adaptive installs require parent-selected explicit effort. Parent owns requirements, integration and acceptance; leaves cannot recursively delegate or publish.
3. Offline tools generate/install profiles, validate structure, compare supplied runs and test reference rules. They are not a live dispatcher or enforcement layer and are not installed as runtime scripts.

## Joint selection and acceptance

Parent chooses a sufficient model/effort pair; actual delegation also requires host support, compatible role pins, supported pair, authorization and benefit. Identical pairs need contextual value and benefit. Raising effort is not guaranteed to fix a capability gap. Insufficiency cannot be repaired by lowering the same unresolved task's model or effort. No-escalation constrains both axes.

The execution contract includes IDs, revision, required outcomes/checks, facts versus assumptions, relevant state, invariants, scope, pair and remaining attempts. Receivers check conflicts before edits. Parent checks final-state coverage and integration; unit PASS is not project PASS. Contrary evidence reopens a decision.

Only long tasks/recovery need one permitted task checkpoint. Keep failed approaches, attempts, valid completed units and active-worker state. Reconcile uncertain effects before replay. Model/effort/worker changes do not renew attempts. Unknown or mismatched actual identity suspends automatic low for the rest of the task, even after later verified medium work. See [quality protocol](QUALITY-PROTOCOL.md) and [effort design](ADAPTIVE-EFFORT.md).

## Generation and ownership

Canonical `agents/*.toml` is fixed. `profiles.py` generates exactly four role files for either mode; adaptive removes only effort pins. The installed core marker and hash manifest carry mode/low policy. New installs and legacy manifests default fixed; upgrades preserve profile unless explicitly changed.

Hash ownership, collision checks, local-edit detection, backups and ordinary-failure rollback remain. Uninstall removes only owned files; restore is explicit. Per-file atomic replacement is not multi-directory power-loss atomicity. [Lifecycle](INSTALL.md) · [Security](../SECURITY.md).

## Sources of truth

Runtime behavior: [SKILL.md](../skills/codex-efficiency-router/SKILL.md) and its references. Canonical roles: `agents/*.toml`, checked against `scripts/package.py` and policy metadata. `effort_reference.py` is the new joint helper; the legacy lane-only helper remains for historical regressions. All consume declared conditions, not live telemetry. [User acceptance](ACCEPTANCE.md) establishes actual host behavior.
