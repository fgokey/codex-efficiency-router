# Architecture

## Objective and boundaries

Preserve required correctness/authorization gates while reducing avoidable expensive-model reasoning, total tokens, and task elapsed time. These are separate quantities. Cheap model selection alone optimizes none of them reliably; duplicated context and repairs count too. No universal non-inferiority or savings guarantee is made.

## Three layers

1. **On-demand Skill**: a compact policy applied by the current coordinator. No classifier LLM, daemon, per-turn Python invocation, or always-on ledger. Metadata participates in discovery; full instructions load on activation, with two references loaded only when needed.
2. **Native Codex leaves**: four role files with explicit model and effort. Astra is read-only decision support. Leaves cannot delegate, create a hidden Codex process, or publish changes. The parent owns user intent, integration, live capability checks, permissions, and the final answer.
3. **Offline maintenance**: installer, uninstaller, static doctor, policy regression reference, and optional paired-run comparison. These utilities are not a runtime dispatcher and cannot prove the model followed the Skill.

## Decision versus execution

Classify the smallest meaningful work unit from available evidence. A phase label does not fix a model: exploration may be a cheap lookup, while implementation may discover a difficult invariant. `choose_lane` in the offline reference recommends capability; `choose_dispatch` separately accounts for user constraints, the current agent's sufficiency, supported routes, and delegation benefit. No-subagent means no dispatch, not automatic permission to finish with an insufficient model.

A settled decision initiates a new cost/capability judgment. It does not mandate creating another child for a trivial tail. Substantial deterministic work should leave the expensive reasoning lane when the verified handoff is worthwhile. If uncertainty persists, retain suitable capability.

## Handoff and ownership

An execution contract preserves goal, code revision and dirty state, known facts versus assumptions, decisions, invariants, write scope, acceptance, and stop/escalation conditions. Store pointers to evidence rather than full transcripts. Do not drop material edge cases to meet a text quota.

Use one child by default. Multiple children require independent acceptance, nonoverlapping write scopes, safe shared resources, observed capacity, and a clear net latency benefit. The parent validates current-workspace integration and collects required work before finishing. Do not manipulate other requests' workers.

## Distribution and safe lifecycle

The Skill packages its own references and UI metadata. Four existing role names are retained for v0.1 compatibility. Installation records exact payload hashes in `.cer-install.json`, refuses unowned collisions and edited owned content, and never edits configuration. Updates are idempotent; ordinary write failures roll back already-written files. Uninstall removes only manifest-owned files and preserves user additions.

Per-file replacement is atomic; a multi-directory operation is not power-loss atomic. Backups, checksums and target-path checks support recovery. This is a local trusted-directory tool, not a hostile filesystem security boundary. See [security](../SECURITY.md).

## Source of truth

Runtime behavior: [SKILL.md](../skills/codex-efficiency-router/SKILL.md) and its referenced files. Shipped presets: `agents/*.toml`, checked against `scripts/package.py` and `policy/routing-policy.json`. Offline regression behavior: `scripts/policy_reference.py`. A passing unit test only establishes the tested code property, not model capability or host integration.

[Official and industry sources](PRIOR-ART.md) explain the adopted principles and their limits.

## v0.2.1 closure

Same-lane delegation requires an explicit contextual purpose and benefit; it is not a capability promotion. Unresolved insufficiency never justifies downward delegation. The core and full-reference instruction budgets are defined once in `scripts/package.py` and checked by doctor, tests and policy metadata. Optional CI measures named reference encodings as well as bytes. Live host acceptance stays separate in [ACCEPTANCE](ACCEPTANCE.md); no automated model smoke task is bundled.
