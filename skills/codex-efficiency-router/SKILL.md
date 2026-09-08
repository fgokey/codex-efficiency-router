---
name: codex-efficiency-router
description: Quality-gated model and effort routing for substantial Codex tasks; reserve Astra for exceptional decisions and use sufficient cheaper models for coding, diagnosis, design or review. Not for tiny edits, simple questions or concurrent routers.
---

# Codex Efficiency Router

Preserve quality/authorization; minimize wasted work. Keep the parent model. No extra LLM classifier, per-turn scripts or foreign runtime.

Installation: fixed; automatic low: disabled.

## Route once per meaningful decision

Map requirements to evidence; track task/unit IDs and contract revisions. Reassess on phases, contrary evidence, classified failures or user requests, not each tool. Repair missing requirements, permissions, environment or observations first; prefer safe discriminating checks.

| Role | Model / fixed default | Work |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` / medium | Mechanical, low-risk, strongly verifiable |
| `terra_executor` | `gpt-5.6-terra` / medium | Settled design, bounded implementation |
| `sol_engineer` | `gpt-5.6-sol` / medium | Uncertainty, coupling, integration/review |
| `astra_architect` | `gpt-6-astra` / high | Exceptional judgment; read-only |

Choose model AND effort: medium normally, high for deeper reasoning; automatic Astra stays high. Read [effort.md](references/effort.md) before delegation. In auto, prefer the unpinned `cer_auto_<role>` binding when native effort is supported; otherwise use the original fixed role only for the SAME selected pair. No user mode switch or runtime config edits. Explicit fixed/adaptive overrides remain respected.

Astra needs useful stronger reasoning, consequential/exceptionally hard judgment and insufficient cheap falsification. Size/keywords/build time are not triggers; [routing.md](references/routing.md) covers ambiguous cases. No compulsory ladder. Never auto-select `max` or xhigh. Ultra is excluded. Auto-low stays opt-in and strictly gated; preferences cannot waive quality.

## Decide whether delegation is worth it

Keep sufficient tiny/tool-bound work local; prefer safe tool concurrency. Delegate for needed capability or benefit after startup, context copying, handoff, checks and rework. Same-model delegation at identical effort needs contextual value AND a net benefit. Increased effort needs reasoning evidence; never downgrade unresolved insufficiency.

Default one leaf, at most two concurrent unless justified by independent acceptance, disjoint writes and safe capacity. No agent per file, recursion or mandatory reviewer chain. Never parallelize conflicting writes, shared builds/devices/credentials or external side effects.

Use actual tools, roles and supported pairs, never invented parameters. Read [dispatch.md](references/dispatch.md) once. If neither binding suffices, keep a sufficient parent; otherwise stop risky writes and disclose the blocker. Reconfigure at safe boundaries, not by steering active work. No hidden CLI/API fallback or permission bypass.

## Handoff without losing the decision

Pass IDs/contract/outcomes; revision/dirty state and paths; facts versus assumptions/evidence; decisions/invariants; writes/non-goals; checks, selected binding/pair and attempts. Keep critical edges, not transcripts/secrets.

Receiver checks completeness, assumptions, plan conflicts and state before edits. Strong-model plans cannot override requirements. Return conflicts, blocking only affected scope. New evidence reopens decisions. Reassess cheaper work after decisions settle, not tiny tails. Astra remains read-only despite broader host permissions. Parent verifies integration; leaf success is not project success.

## Failure, validation, and stopping

Classify prerequisite, environment, observability, implementation and capability failures. One targeted repair after initial failure across ALL workers on the unit/failure signature. Model/effort/binding changes and compaction never reset attempts. Exhaustion requires diagnosis/experiment/escalation or justified bounded parent extension retaining history. New error text/retry count is not capability evidence.

Review missing/extra/misread behavior and correctness together. Honor repository checks; reproduce defects or establish before/after evidence. New tests are not independent proof. Do not weaken assertions, delete relevant tests or waive acceptance. Independent review addresses residual judgment risk, not ritual approval.

Bind evidence to contract and relevant final state, not HEAD alone. Reuse unaffected checks; invalidate changed parts. Unrun checks are UNKNOWN, not PASS. PASS needs every required outcome evidenced and no blocker; else PARTIAL/BLOCKED. Disclosure never waives requirements. Stop after acceptance; speculative optimization remains a measurement plan.

## Context and reporting

Read narrowly; keep errors/log paths, not all history/references. Long work/recovery uses one permitted checkpoint: IDs, contract, completed evidence, state, active workers, failed methods, pair and attempts. Update on transitions; reconcile before resuming or replaying uncertain effects. [quality.md](references/quality.md) covers disputed recovery/completion.

Honor disable/no-subagent/no-escalation; the last covers BOTH model and effort. Separate requested/observed pairs; unknown or mismatched metadata stops auto-low. Report material fallback and gaps once, no fabricated identity/savings/cache claims. Collect required leaves; stop only owned superseded work using exposed controls; never claim unobserved cleanup.
