---
name: codex-efficiency-router
description: Quality-gated model and reasoning-effort routing for substantial Codex engineering tasks; reserve Astra for exceptional decisions and cheaper executors for settled work. Use for coding, diagnosis, design or review; not tiny edits, simple questions, or alongside another router.
---

# Codex Efficiency Router

Codex only. Optimize quality, tokens/time within authorization. Never change the parent model. No extra LLM classifier, per-turn script, ledger or foreign runtime.

Installation: fixed; automatic low: disabled.

## Route once per meaningful decision

Map required outcomes to checks/review; identify the unresolved question. Use task/unit IDs and contract revision for substantial work. Reassess on phases, contrary evidence, classified failures or user requests, not each tool. Repair missing requirements, authority, environment or observations first; prefer safe cheap discriminating checks.

| Role | Model / fixed default | Work |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` / medium | Mechanical, low risk, explicit scope, strong checks |
| `terra_executor` | `gpt-5.6-terra` / medium | Settled design, bounded implementation |
| `sol_engineer` | `gpt-5.6-sol` / medium | Uncertainty, coupling, integration/review |
| `astra_architect` | `gpt-6-astra` / high | Exceptional reasoning; read-only decisions |

Choose model AND effort. Fixed mode pins defaults; adaptive explicitly passes effort through a supported native field. Normally medium; high for deep logic/assumptions/edges; Astra defaults high. Auto-low needs installation opt-in and the strict mechanical-work gate in [effort.md](references/effort.md); read it before first adaptive use/override. Unsupported settings never silently downgrade.

Automatic Astra requires useful stronger reasoning, consequential/exceptionally difficult judgment and insufficient cheap falsification. Keywords, size and slow builds are not triggers. Consult [routing.md](references/routing.md) for ambiguity. No compulsory ladder; Never auto-select `max` or xhigh. Ultra is outside this policy. Explicit preferences never waive quality/prerequisites.

## Decide whether delegation is worth it

Keep sufficient tiny/tool-bound work local; prefer safe tool concurrency. Delegate for necessary capability or benefit after startup, copied context, handoff, verification and rework. Same-model delegation at IDENTICAL effort needs contextual value AND a net benefit. Higher effort needs reasoning evidence, not renewed retries. Never downgrade unresolved insufficiency; resolve/re-scope first. Skip futile weak attempts.

Default one leaf, at most two concurrent unless justified. Require independent acceptance, disjoint writes, safe resources and capacity. No agent per file, recursive delegation or mandatory reviewer chain. Never parallelize conflicting writes, shared builds/devices/credentials or external side effects.

Read [dispatch.md](references/dispatch.md) before dispatch. Use discovered roles/actual schemas; distinguish recommended/requested/observed pairs. No config rewriting, hidden `codex exec`/API fallback or permission bypass. Unavailable route: stay local only if sufficient; otherwise stop risky writes and report the blocker. Change effort at safe boundaries, never by steering an active turn. Reuse idle threads only with exposed compatible next-turn controls.

## Handoff without losing the decision

Pass IDs/contract, outcomes; revision/dirty state and paths; facts versus assumptions/evidence; decisions/invariants; write scope/non-goals; checks, pair and remaining attempts. Preserve critical edges, not transcripts/secrets.

Receiver checks completeness, assumptions, plan conflicts and state before edits. Strong-model plans cannot override requirements. Block affected scope on conflict, preserve independent progress. New evidence/requirements reopen the contract. After decisions settle reassess cheaper work, not for tiny tails. Astra stays read-only despite broader host permissions. Leaves report unit evidence; parent checks integration and project completion.

## Failure, validation, and stopping

Classify specification/authority, environment/tooling, observability, implementation and capability failures. One targeted repair after initial failure across ALL workers on the unit/failure signature. Model/effort changes and compaction never reset attempts. Exhaustion needs diagnosis/experiment/escalation or justified parent extension with history retained. Retry count/new error text is not capability evidence.

Review missing/extra/misread behavior and correctness together. Honor repository checks; reproduce defects or establish before/after evidence. New tests are not independent proof. Do not weaken assertions, delete relevant tests or rewrite acceptance to get green. Independent review addresses residual judgment risk, not ritual approval.

Bind evidence to contract and final state (code/diff, checks, dependencies/environment), not HEAD alone. Reuse unaffected evidence; invalidate changed parts. Unrun checks are UNKNOWN, not PASS. PASS requires every required outcome evidenced, no blocker; else PARTIAL/BLOCKED. Disclosure never waives requirements. Stop after acceptance; speculative optimization stays a measurement plan.

## Context and reporting

Read narrowly; retain key errors/log paths, not all references/history. Long work/recovery uses one permitted task checkpoint: IDs, contract, completed evidence, state, active workers, failed methods, pair and attempts. Update on transitions; reconcile files/workers before resume, never replay uncertain effects. Read [quality.md](references/quality.md) for disputed recovery/completion.

Honor disable/no-subagent/no-escalation; the last forbids BOTH model and effort increases. A model-only lock may allow effort changes. Unknown identity is not success; disable automatic low after unverified/mismatched effort. Report evidence/gaps; no invented savings or cache promises. Collect required leaves; stop only owned superseded work with supported tools, no unobserved cleanup claims.
