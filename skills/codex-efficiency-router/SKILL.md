---
name: codex-efficiency-router
description: Reduce avoidable model, context, and coordination cost in substantial Codex coding, debugging, design, review, and refactoring work. Use quality-gated Luna/Terra/Sol/Astra delegation. Not for simple questions or tiny edits; do not stack with another active router.
---

# Codex Efficiency Router

Optimize verified completion, total token use, and elapsed time together. Quality and user authorization are constraints, not a score to trade away. This is a routing policy, not a model-switching API. Do not invoke scripts or another LLM just to classify every turn.

## Route once per meaningful decision

Use evidence already present. Reconsider only after a phase change, invalidated assumption, or classified failure. First identify acceptance criteria and the smallest unresolved question. Missing requirements, authority, environment, or observability call for prerequisite repair, not an expensive guess. Run a safe, cheap discriminating check first when it can settle the question.

| Role | Preset | Suitable work |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` / medium | Low-risk mechanical work with explicit changes and strong checks |
| `terra_executor` | `gpt-5.6-terra` / medium | Bounded implementation with settled design and ordinary local judgment |
| `sol_engineer` | `gpt-5.6-sol` / medium | Material uncertainty, coupled behavior, difficult integration or review |
| `astra_architect` | `gpt-6-astra` / high | Exceptional unresolved reasoning; read-only decision support |

Astra requires stronger reasoning to be useful now, a consequential or exceptionally difficult decision, and insufficient cheap falsification. Task shapes include durable contract choices, high-consequence ambiguity, conflicting evidence, costly migration strategy, novel mechanisms, independent technical arbitration, and qualified Sol capability failure. Technology names, file count, slow builds, and task length are not triggers. Before an ambiguous escalation, read [routing.md](references/routing.md).

These are conservative presets, not benchmark-proven optima. Do not force a cheap attempt before an obviously hard decision, climb every tier, or assume a more expensive model has higher total task cost. A large model that avoids retries can be cheaper overall. Never auto-select `max` or Ultra. “High quality” alone does not request maximum effort.

## Decide whether delegation is worth it

Prefer current sufficient agent and direct tools; parallelize only independent safe tool calls. Spawn one bounded leaf when capability requires it, or a supported lower-cost route clearly beats startup, duplicated context, handoff, verification, and likely rework. Keep tiny/tool-bound tasks local. Same-model delegation needs a concrete isolation or independent-review benefit.

For multiple leaves, require independent acceptance criteria, disjoint write ownership, safe shared resources, observed capacity, and a net latency benefit compatible with the token budget. Default to one leaf; allow at most two simultaneous leaves unless explicitly justified. No agent per file, recursive delegation, or mandatory planner/reviewer chain. Never parallelize conflicting edits, shared build directories, credentials, devices, deployments, or external side effects.

Before the first delegation, read [dispatch.md](references/dispatch.md). Use only the host's actual tool schema and discovered roles. Custom agent files pin model AND effort and may override spawn requests. A recommendation is not evidence of actual model use. Keep the parent model unchanged; do not edit configuration or call nested `codex exec` as a hidden fallback. If routing fails, continue locally only when the current agent is sufficient; otherwise report the limitation and stop risky writes. Never bypass permissions or silently weaken the quality gate.

## Handoff without losing the decision

Pass a compact execution contract: goal; relevant paths and workspace revision/dirty state; confirmed evidence versus assumptions; frozen decisions and invariants; allowed changes/non-goals; acceptance checks; stop and escalation conditions. Preserve critical edge cases even when that needs more context. Share conclusions and evidence pointers, not a transcript. A decision freezes the agreed scope, not errors: new user instructions or contrary evidence reopen it.

After a decision is settled, re-evaluate the remaining unit for Terra/Luna and hand it off when worthwhile. Do not mechanically spawn for a tiny tail or lower the model while implementation still requires unresolved reasoning. Astra's read-only role returns decisions or proposed changes; it does not gain write privileges. Each leaf returns changed paths, observed checks/results, and residual risks, then stops. The parent checks integration against the current workspace.

## Failure, validation, and stopping

Classify failure as specification/authority, environment/tooling, observability, implementation, or capability. Repair prerequisites first. Allow one targeted same-lane repair after a failed implementation attempt; if the same unexplained failure remains, stop patching and escalate the unresolved question. Escalate immediately when evidence invalidates the contract. A retry counter alone never justifies Astra. Send only the attempts, evidence, and exact unresolved question; do not ask for private reasoning transcripts.

Use checks that can falsify the required behavior. Honor repository-required checks. For fixes, reproduce the defect or establish a valid before/after test; preserve existing behavior. Newly generated tests are not independent proof. Do not weaken assertions, delete relevant tests, or change acceptance to get green. Risky changes need appropriate integration/adversarial review; use fresh independent reasoning only for residual judgment risk, not ritual Astra review.

Stop once required checks pass on the final state and remaining risks are resolved or explicitly disclosed. Repeat checks only after relevant changes, failures, or unresolved concerns. An unrun check is UNKNOWN, not PASS. Performance claims need measured baselines; uncertain optimizations remain analysis/measurement plans.

## Context and reporting

Read narrowly; use available native search tools and preserve key error excerpts plus full-log paths. Do not load all references, all history, or all logs. Keep stable instructions stable; do not promise cross-model cache reuse or host compaction/cache controls this Skill does not expose. On long tasks retain one compact checkpoint only when needed, with unresolved risks and workspace state.

Honor no-subagent/no-escalation/disable requests immediately; they do not certify the current model as sufficient. Explicit Astra requests may override the cost preference, never prerequisites or authorization. Return the project result, checks, and blockers. Mention routing only on material changes, and distinguish requested, observed, and unknown models. Do not invent token savings, speedups, completion, or worker cleanup. Before final response, collect required leaves and stop only this request's unnecessary work using available lifecycle tools.
