---
name: codex-efficiency-router
description: Quality-gated model routing for substantial Codex engineering tasks; reserve Astra for exceptional decisions and use sufficient cheaper executors when worthwhile. Use for efficiency-sensitive coding, diagnosis, design or review; not tiny edits, simple questions, or alongside another active router.
---

# Codex Efficiency Router

Codex only. Optimize verified completion, tokens and time; preserve quality and authorization. Native delegation cannot switch the parent model. No extra LLM classifier, per-turn script, mandatory ledger or third-party runtime.

## Route once per meaningful decision

Identify the unresolved question and required outcomes. For substantial work use stable task/unit IDs and a contract revision; map requirements to checks/review. Reclassify on phase changes, failures or contrary evidence, not each tool. Repair missing requirements, authority, environment or observability first; prefer safe cheap discriminating checks.

| Role | Model / effort | Work |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` / medium | Low-risk mechanical changes, explicit scope, strong checks |
| `terra_executor` | `gpt-5.6-terra` / medium | Settled design, bounded implementation |
| `sol_engineer` | `gpt-5.6-sol` / medium | Material uncertainty, coupling, difficult integration or review |
| `astra_architect` | `gpt-6-astra` / high | Exceptional unresolved reasoning; read-only decisions |

Automatic Astra needs all three: stronger reasoning helps now; the decision is consequential or exceptionally difficult; cheap safe falsification is insufficient. Keywords, file count and slow builds are not triggers. Read [routing.md](references/routing.md) for ambiguity only. Four conservative presets, not a compulsory ladder. Never auto-select `max` or Ultra; effort overrides require actual support.

## Decide whether delegation is worth it

Keep sufficient tiny/tool-bound work local; prefer safe independent tool concurrency. Delegate for needed capability or clear benefit after startup, copied context, handoff, verification and rework.

Same-model delegation needs a contextual reason AND a net benefit, not insufficiency alone. Do not downgrade an unresolved task while current capability is insufficient; resolve/re-scope first. Skip futile weak attempts.

Default one leaf, at most two concurrent unless justified. Require independent acceptance, disjoint write ownership, safe resources and observed capacity. No agent per file, recursive delegation or mandatory reviewer chain. Never parallelize conflicting writes, shared builds/devices/credentials or external side effects.

Read [dispatch.md](references/dispatch.md) once before delegation. Use discovered roles and actual schemas; separate requested from observed model/effort. No config rewriting, hidden `codex exec`/API fallback or permission bypass. Unavailable route: stay local only if sufficient; otherwise stop risky writes and disclose the blocker.

## Handoff without losing the decision

Pass IDs, contract revision, required outcomes; revision/dirty state and paths; facts versus assumptions/evidence; decisions/invariants; allowed writes/non-goals; checks and remaining attempts. Preserve critical edge cases, not transcripts or secrets.

Before edits the receiver checks completeness, consequential assumptions, requirement/plan conflicts and current state. A strong model's plan cannot override requirements. Block the affected scope on conflict and return it to the parent, not redesign everything. Contrary evidence/new requirements reopen the contract.

After decisions settle reassess Terra/Luna; no spawn for tiny tails or unresolved reasoning. Astra stays read-only even with broader permissions. Leaves report unit evidence, not parent completion. Parent verifies current-workspace integration.

## Failure, validation, and stopping

Classify specification/authority, environment/tooling, observability, implementation and capability failures. One targeted repair after initial failure, across ALL workers on the unit/failure signature. Model changes/compaction never reset attempts. At exhaustion stop patching: choose a discriminating experiment or escalate. Only explicit parent reassessment extends the budget, retaining history. New error text or retry count is not capability evidence.

Review coverage (missing/extra/misread behavior) and correctness in one bounded pass. Honor repository-required checks; reproduce defects or establish before/after evidence. New tests are not independent proof. Do not weaken assertions, delete relevant tests or rewrite acceptance to get green. Independent review is for residual judgment risk, not ritual Astra approval.

Bind evidence to contract and relevant final-state fingerprint: code/diff, checks, dependencies/environment, not HEAD alone. Reuse unaffected evidence; invalidate changed parts. Unrun checks are UNKNOWN, not PASS. Final PASS needs every required outcome evidenced and no blocking finding; else PARTIAL/BLOCKED with gaps. Disclosure never waives requirements. Stop after required checks; speculative optimization stays a measurement plan.

## Context and reporting

Read narrowly; keep key errors/full-log paths, not all history/references. For long work/recovery use one permitted task-scoped checkpoint: IDs, contract, completed scopes/evidence, state, active workers, failed approaches and remaining budget. Update on transitions only. Reconcile files/workers before resuming; never replay completed work or uncertain side effects blindly. Read [quality.md](references/quality.md) only for disputed completion/recovery.

Honor disable/no-subagent/no-escalation; explicit Astra overrides cost, not prerequisites. Report results/evidence/gaps briefly, no invented identity, savings or speedups. Preserve stable context without claiming unsupported cache/compaction controls. Collect required leaves; stop only this request's superseded work with available tools; no unobserved cleanup claims.
