# Compatibility and verification levels

Documentation review: **2026-09-08**. [Primary references](PRIOR-ART.md) · [Effort design](ADAPTIVE-EFFORT.md).

## Layout and modes

User Skills live in `~/.agents/skills`; project Skills in `.agents/skills`. Roles live in `$CODEX_HOME/agents` (normally `~/.codex/agents`) or project `.codex/agents`. The Skill's `agents/openai.yaml` is discovery/UI metadata, not the four model roles. Prefer one scope to avoid duplicate names.

Role TOML supplies name, description, developer instructions and model. Canonical/fixed files also pin effort; generated adaptive files do not. File values override contradictory spawn requests. Omission is not adaptive selection: host defaults/inheritance can resolve effort before a model-only role is applied. Adaptive must use actual explicit model/effort tool fields. No unsupported configuration keys are inserted.

The four models remain `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`, `gpt-6-astra`. Fixed efforts are medium/medium/medium/high. Adaptive uses medium/high, with separately opted-in mechanical Luna/low; xhigh/max are explicit only. These are policy choices, not a guarantee every account exposes them.

## Host boundary

A Skill cannot change its parent model or obtain unavailable tools. Use discovered roles and the actual schema. App Server next-turn overrides are not automatically callable by an ordinary Skill; steer input is not a running-turn effort setter. Only exposed compatible idle-turn controls may reuse a child. Do not create a hidden CLI/API session or change global defaults to obtain routing.

Parent/runtime permissions may override sandbox defaults, so Astra remains read-only in instructions too; instructions are not an OS security boundary. Installation does not change authentication, providers, network permissions, trust or features.

## Separate validation levels

1. `doctor --source-tree .` validates canonical fixed source, metadata, references, budgets and four presets.
2. `doctor --scope ...` validates the installed profile/marker, fixed pins or adaptive absence, plus manifest hashes. Local edits are reported, not repaired.
3. Optional `doctor --catalog FILE` parses a supplied complete `model/list` export (raw result or result wrapper). It requires `data`, valid model/effort strings, unique models and explicit `nextCursor=null`. Fixed checks four pinned pairs; adaptive checks medium/high on lower roles and high on Astra, plus opted-in Luna/low. Runtime only needs the selected pair; a saved export is not proof of current access or dispatch.
4. User-run read-only smoke work checks actual role, model, effort and permissions from host metadata. A model's self-description is not evidence. Missing fields are UNKNOWN, contradictory fields MISMATCH; either suspends subsequent automatic low for the task.

No installer, doctor or CI calls models. Live identity, actual handoffs, acceptance and whole-task usage remain [user acceptance](ACCEPTANCE.md).
