# Compatibility and verification levels

Documentation review date: **2026-09-07**. See [primary references](PRIOR-ART.md).

## Supported package layout

User Skills install under `~/.agents/skills`; project Skills under `.agents/skills`. Agents use `$CODEX_HOME/agents` (normally `~/.codex/agents`) or `.codex/agents`. The optional `agents/openai.yaml` inside the Skill contains UI metadata and implicit-invocation policy, not the four model roles. Duplicate Skill names are not merged; prefer one installation scope.

Standalone role TOML requires `name`, `description` and `developer_instructions`. The four shipped roles additionally pin model and reasoning effort. Official documentation gives custom-file model/effort priority over spawn-time choices; do not claim a contradictory spawn override changed the role. The fallback precedence described by the host is spawn parameters, configured defaults, then inherited parent values when not pinned by the role.

## Execution is host dependent

A Skill cannot switch its parent model. Use only the actual exposed collaboration schema and discovered role names; do not invent fields or start hidden nested CLI processes. The host's live permission/sandbox rules may supersede role defaults, so Astra's instructions independently retain a read-only boundary. No provider, sandbox, authentication or feature flag is changed by installation.

Model catalog entries checked in documentation: `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`, `gpt-6-astra`. Availability varies; the project does not assume that your account exposes them. Effort remains medium for the first three and high for Astra. `max` is never automatically selected.

## Four distinct checks

1. `doctor --source-tree .`: local package structure, references and shipped presets.
2. `doctor --scope ...`: installed structure plus manifest hashes; custom edits are reported, not rewritten.
3. `doctor --catalog FILE`: optional offline validation of a supplied, fully paginated Codex App Server `model/list` response. Supports a `result` wrapper or its raw object, a `data` array, `model`, `supportedReasoningEfforts[].reasoningEffort`, and `nextCursor`. A non-null cursor is incomplete. A saved export is not a live availability guarantee.
4. Live read-only smoke task: observe actual model, effort, role, permission behavior, and completion from host/session metadata. This is not performed by the installer or static doctor.

The model's self-description is not runtime evidence. Where available, account for `model/rerouted` events instead of assuming requested configuration was honored. No live Codex installation was available in the audit environment, so the audit does not claim live execution validation.

## Release versus host acceptance

v0.2.1 ships the same four model/effort pairs; no additional Sol/high preset, automatic xhigh/max step or automatic model switch is introduced. An account catalog can confirm availability at export time, not actual dispatch. Installation/doctor never authenticates, reads private sessions or probes models. Follow [user-run acceptance](ACCEPTANCE.md) and preserve UNKNOWN where runtime metadata is absent.

## v0.3 acceptance additions

Codex-only operation and four presets remain unchanged. Three on-demand references cover routing, dispatch and quality/recovery. Required-outcome statuses and checkpoints are instruction-level conventions, not new Codex APIs or guaranteed enforcement. The pure offline helpers are not installed runtime code. See [quality protocol](QUALITY-PROTOCOL.md).
