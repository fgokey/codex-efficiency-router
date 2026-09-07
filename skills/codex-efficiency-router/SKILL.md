---
name: codex-efficiency-router
description: Quality-gated model routing for substantial Codex engineering tasks; reserve Astra for exceptional decisions and use sufficient cheaper executors when worthwhile. Use for efficiency-sensitive coding, diagnosis, design or review; not tiny edits, simple questions, or alongside another active router.
---

# Codex Efficiency Router

Optimize verified completion, total tokens and elapsed time. Quality and authorization are constraints. This Skill recommends native delegation; it cannot switch the parent model. No extra LLM classifier, per-turn script or mandatory ledger.

## Route once per meaningful decision

Identify acceptance criteria and the smallest unresolved question from available evidence. Reclassify after phase changes, classified failures or contrary evidence, not every tool call. Missing requirements, authority, environment or observability require prerequisite repair, not a more expensive guess. Prefer a safe cheap discriminating check when it can settle the question.

| Role | Model / effort | Work |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` / medium | Low-risk mechanical changes with explicit scope and strong checks |
| `terra_executor` | `gpt-5.6-terra` / medium | Settled design, bounded implementation, ordinary local judgment |
| `sol_engineer` | `gpt-5.6-sol` / medium | Material uncertainty, coupled behavior, difficult integration or review |
| `astra_architect` | `gpt-6-astra` / high | Exceptional unresolved reasoning; read-only decisions |

Automatic Astra requires all three: stronger reasoning can help now; the decision is consequential or exceptionally difficult; cheap safe falsification is insufficient. Technology keywords, file count and slow builds are not triggers. Consult [routing.md](references/routing.md) only for ambiguous boundaries. These are four conservative presets, not proven optima or a compulsory ladder. Never auto-select `max` or Ultra; explicit effort overrides require actual host support and cannot override a pinned role by assertion.

## Decide whether delegation is worth it

Keep sufficient, tiny or tool-bound work local. Prefer independent safe tool concurrency over extra model contexts. Delegate for necessary capability or a clear benefit after startup, duplicated context, handoff, verification and likely rework.

Same-model delegation needs a concrete reason (context recovery, independent review or scope isolation) AND a net benefit. Insufficiency alone does not justify another copy of the same model. An insufficient current agent must not downgrade the same unresolved task; first resolve or re-scope it. Do not exhaust cheap tiers before an obviously difficult decision.

Default to one leaf, at most two concurrent leaves unless justified. Require independent acceptance, disjoint write ownership, safe resources and observed capacity. No agent per file, recursive delegation or mandatory reviewer chain. Never parallelize conflicting writes, shared build state, devices, credentials, deployments or external side effects.

Before first dispatch read [dispatch.md](references/dispatch.md) once. Use only discovered roles and the actual host schema. Distinguish recommended, requested and runtime-observed models; self-identification is not evidence. Do not edit global configuration or start hidden nested `codex exec`/API sessions. On unavailable routing, stay local only if sufficient; otherwise report the blocker and stop risky writes. Never bypass permissions.

## Handoff without losing the decision

Pass: goal; revision/dirty state and relevant paths; facts versus assumptions with evidence pointers; decisions/invariants; allowed writes/non-goals; acceptance checks; stop/escalation conditions. Keep critical edge cases even when longer context is needed. Do not copy transcripts or secrets. Contrary evidence or new user requirements reopen a contract.

Once decisions settle, reassess remaining work for Terra/Luna; hand off only when worthwhile, not for a tiny tail or unresolved implementation reasoning. Astra stays read-only even if the host grants broader permissions. Leaves report changed paths, checks actually run, outcomes and risks, then stop. Parent verifies integration on the current workspace.

## Failure, validation, and stopping

Classify specification/authority, environment/tooling, observability, implementation and capability failures. Repair prerequisites first. Allow one targeted same-lane repair of an implementation mistake; repeated unexplained failure stops patching for diagnosis. Contract invalidation warrants immediate escalation. Retry count alone never justifies Astra; send attempts, evidence and the exact question, not private reasoning transcripts.

Honor repository-required checks. Reproduce a defect or establish a valid before/after test; preserve unrelated behavior. Newly generated tests are not independent proof. Do not weaken assertions, delete relevant tests or rewrite acceptance to get green. Risky changes need appropriate integration/adversarial checks; fresh review is for residual judgment risk, not ritual Astra approval.

Stop when required checks pass on the final state and residual risks are resolved or disclosed. Repeat checks only for relevant changes, failures or unresolved concerns. Unrun checks are UNKNOWN, not PASS. Speculative optimizations remain analysis/measurement plans until supported by evidence.

## Context and reporting

Read narrowly with available native tools; retain key errors and full-log paths. Do not preload all references, history or logs. Keep stable instructions stable; do not promise cross-model cache reuse or unsupported compaction controls. Retain one compact checkpoint only when needed, including workspace state and unresolved risks.

Honor disable/no-subagent/no-escalation requests; they never certify insufficient capability. Explicit Astra changes cost preference, not prerequisites or authority. Return results, observed checks and blockers; mention routing only for material changes. Never invent savings, speedups or actual model identity. Collect required leaves and stop only this request's superseded work with supported lifecycle tools; do not claim unobserved cleanup.
