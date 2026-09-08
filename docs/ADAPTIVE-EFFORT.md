# Joint model and reasoning-effort routing (v0.4)

## Scope and defaults

Still one Codex Skill and four native role definitions. The parent selects a model/effort pair at the creation of a bounded unit, or at a meaningful safe phase boundary. The leaf executes and reports evidence; it cannot change its own configuration. No classifier call, proxy, foreign runtime, hidden second Codex process or running-turn hot-switch is added.

The repository's `agents/*.toml` remains the canonical **fixed** source. `profiles.render_payload` generates either fixed files or adaptive files with only the top-level effort pin removed. Models, instructions, names and sandbox policy are preserved. Exactly four files are installed, not a growing matrix of role variants. The installed Skill's short `Installation:` line and manifest describe the chosen mode. They are package metadata, not unsupported Codex config keys.

New installs default to fixed. An upgrade without `--mode` preserves the existing mode; old manifests without profile fields mean fixed. `--mode adaptive` is explicit opt-in, not a host capability certificate. `--allow-low` is a separate conservative opt-in; `--no-allow-low` disables it; switching to fixed disables it. Both settings survive no-op reinstall and explicit restore. Profile changes are subject to the same collision/modification protection and backups as ordinary updates.

## Parent selection rules

| Unit | Initial policy |
| --- | --- |
| Ordinary settled implementation | Sufficient model / medium |
| Deep logic, assumptions or edge analysis within a suitable model | Same model / high, or stronger model when capability requires it |
| Exceptional answerable decision satisfying Astra's three gates | Astra / high |
| Strict mechanical Luna unit | Medium by default; low only with installation opt-in and the safe-work gate |
| Missing prerequisites or cheap safe falsification available | Repair/check first, not more model effort |

The low gate requires mechanical, settled work; low consequences/reversibility/coupling; strong behavior checks; no novelty, evidence conflict, consequential commitment or previous failed attempts. Explicit low cannot waive this floor. Automatic Astra remains high. Explicit Astra/medium is reserved for bounded tasks where high judgment is not required. xhigh/max require explicit user intent and actual catalog support; Ultra is outside this Skill policy. Effort is not a numeric reasoning-token limit, and no universal quality/cost ranking is claimed for cross-model combinations.

The offline helpers in `effort_reference.py` implement these declared-signal rules for development tests. `policy_reference.py` remains the legacy lane-only reference for historical regressions; adaptive tests use the joint helper. Neither is a live execution engine or an LLM classifier.

## Three gates before native dispatch

1. The actual host exposes native delegation and an explicit effort parameter. Do not guess its name or call App Server from a hidden session.
2. The loaded role matches the chosen model. Fixed files pin effort and cannot be overridden by a contrary request. Adaptive files must not retain a pin, even one that happens to match this request.
3. The selected model/effort is supported by the account/host catalog. No remapping from unsupported high to medium, no omitted effort interpreted as automatic selection.

When any gate fails, keep sufficient current execution with its configuration unchanged, or report BLOCKED if sufficient execution is unavailable. A requested explicit configuration that cannot be honored must be disclosed, not reported as success. Fixed installations do not gain same-model high merely because the Skill recommends it: switch modes explicitly or keep an adequate current agent. Installation does not rewrite defaults to achieve a route.

`doctor --catalog FILE` parses a supplied fully paginated `model/list` export. Fixed mode checks its four pinned pairs. Adaptive mode checks medium/high for Luna/Terra/Sol, high for Astra, and low for Luna only when opted in. This tests the configured profile's intended range, not live dispatch. At runtime, each individual route checks its selected pair, without probing every model. Duplicate/malformed entries and unknown pagination are errors. A saved catalog can become stale.

## Configuration precedence and observations

Maintain three separate facts: recommended pair, request actually sent, and host-observed pair. Role labels and a model saying “I am Astra” are not runtime evidence. Missing metadata is UNKNOWN; a contradictory known model or effort is MISMATCH, including partial metadata. Either state suspends automatic low for the rest of the task, even after a later verified observation; reassess the quality risk rather than blindly restarting completed work. Costs and dynamic-success claims remain unverified until authoritative evidence exists.

Parent context/default effort is not a selection algorithm. The role's effort pin takes precedence over spawn values. An unpinned role preserves previously resolved effort, so adaptive requests must explicitly supply the chosen model AND effort where the native schema supports them. Directory availability, schema availability and actual use are distinct.

## Events, opt-outs and recovery

Only initial creation, a phase transition, new evidence, classified failure or explicit user request permits reselection. No escalation means no increase in either model capability tier or effort tier, even if the other decreases. Model-only locks may allow effort changes; effort-only ceilings may allow model changes. Unknown current settings cannot prove compliance with a ceiling. No-subagent/disable rules are never bypassed.

Same model + same effort is the old contextual-recovery case and needs reason plus net benefit. Same model + higher effort is an evidence-backed reasoning adjustment; it is not guaranteed to help. Neither change renews retry budgets. The offline joint helper also blocks further implementation after two failed attempts unless a justified parent extension is declared; a separately scoped diagnosis can proceed. Declared reasons are not proof of user authority or a new automatic budget. Same unresolved insufficiency cannot be pushed to a weaker model or less effort. Once scope is settled/reduced, reassess the new unit rather than carrying over the original label forever.

Do not interrupt an active writer to change settings. A safe idle next turn can reuse context **only if the parent's exposed native tools support that operation** and ownership/contract/permissions remain compatible. Otherwise use a bounded new leaf when its benefit warrants the handoff. This release does not implement a separate App Server client or promise same-thread reuse on every host. Preserve failed methods, remaining attempts, active-worker state and uncertainty about side effects.

## Validation layers

Offline: canonical generation, install/mode switch/update/uninstall/restore, role precedence, selected-pair admission, no-escalation, low opt-in, unknown metadata, no hot-switch and mutation coverage. Source/installed profiles are checked separately. Mode switches are idempotent, backed up and rolled back on ordinary write failures; cross-directory power-loss atomicity is not promised.

Live (user-run): role discovery, actual native parameter schema, actual model/effort, boundary handoff, fixed/adaptive configuration precedence, final task quality, complete parent/child usage and elapsed time. No installer or CI starts this validation. See [ACCEPTANCE](ACCEPTANCE.md). Do not grade the Skill's live compliance by passing Python tests alone.

## Primary documentation checked 2026-09-08

- [Codex Subagents](https://developers.openai.com/codex/subagents): model/effort selection, role-file precedence, defaults/inheritance and parent permissions.
- [Codex App Server](https://developers.openai.com/codex/app-server): `model/list` and `supportedReasoningEfforts`; optional later `turn/start` overrides; `turn/steer` appends input rather than accepting turn-level overrides. These APIs do not automatically become parent Skill tools.
- [Codex Skills](https://developers.openai.com/codex/skills): concise on-demand instructions and packaged references.

Policies such as conservative low eligibility, dual-axis ceilings and task-level retry preservation are this project's design, not OpenAI platform features or benchmark-proven optimal settings.
