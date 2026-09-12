---
name: codex-efficiency-router
description: Quality-gated routing for substantial Codex tasks; reserve Astra for hard read-only decisions. Skip tiny edits, simple questions and concurrent routers.
---

# Codex Efficiency Router

<!-- CER version: 0.7.0-rc.3 -->

Preserve quality, authority and parent model. No extra LLM classifier, per-turn scripts, hidden CLI/API or config changes.

Installation: fixed; automatic low: disabled.

Report once: `CER v<loaded/UNKNOWN> | <mode> | guard=<policy-only/guarded/live-verified> | policy=<loaded-hash/UNKNOWN>`. Disk is not loaded-state proof; guarded is not enforced. Require current scoped native Canary for live-verified; reload only at safe boundaries.

## Before any side effect

Authority precedes every shortcut. Astra roots/leaves and read-only coordinators NEVER patch, write/checkpoint, format, build or run side-effecting tests/commands. Unknown identity/effects grant no writes. Reuse compatible authorized Terra/Sol owners; missing authority/owner/capacity means stop risky writes and BLOCKED/defer. Preserve existing edits for independent review/tests/ownership; never auto-revert.

Astra actively diagnoses hard judgments and qualified repeated failures; executors run its experiments/fixes. Already-Astra reasons locally. Exhaustion stops blind edits, not diagnosis.

## Route once per meaningful decision

Route on phase/evidence changes, classified failures or user requests, not each tool. Preserve requirement/unit IDs; repair prerequisites before escalating.

| Role | Model / fixed default | Work |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` / medium | Mechanical, low-risk, strongly checked |
| `terra_executor` | `gpt-5.6-terra` / medium | Settled implementation |
| `sol_engineer` | `gpt-5.6-sol` / medium | Diagnosis, coupling, integration |
| `astra_architect` | `gpt-6-astra` / high | Exceptional read-only reasoning |

Select sufficient model AND effort. Auto preflight: when the actual schema exposes `reasoning_effort` and matching `cer_auto_<role>`, use that alias with explicit effort; a base role is MISMATCH. Base roles require unavailable alias/field evidence and an exact pinned pair; state why. Never auto-select `max`/xhigh/Ultra; auto-low needs opt-in. Astra needs useful stronger reasoning, consequentially hard judgment AND no cheap falsification.

## Decide whether delegation is worth it

Keep sufficient authorized work local; prefer safe tool concurrency. Delegate for capability, write ownership or benefit after context/coordination/checks/rework. Same-model delegation at identical effort needs contextual value AND a net benefit, except mandatory write separation. Never weaken unresolved execution.

Default one leaf; at most two concurrent writers, the third waits. Require disjoint writes/resources and independent acceptance. No agent per file, recursive workers, ritual reviewers or conflicting side effects. Use supported native bindings, not permission bypasses.

## Handoff without losing the decision

Pass contract/outcomes, revision/dirty state/paths, facts vs assumptions/evidence, invariants, allowed writes/non-goals, checks, pair/binding and attempts; no transcripts/secrets. Receiver checks completeness/state/assumptions/conflicts. Requirements outrank plans; block affected scope, and contrary evidence reopens decisions. Parent verifies integration and completes the writer review handoff in dispatch, not just child success.

## Failure, validation, and stopping

Classify prerequisite/environment/observability/implementation/capability failures. One targeted repair after initial failure per task/unit/failure signature across ALL owners. Worker/model/effort/compaction never renews attempts. Exhaustion needs diagnosis/experiment/escalation or justified bounded extension retaining history.

Check requirements/correctness, repository checks and reproduction. New tests are not independent proof. Do not weaken assertions, delete relevant tests or waive acceptance. Bind evidence to final code/checks/environment; reuse unaffected checks. Unrun is UNKNOWN, not PASS. PASS needs all outcomes with no blocker; else PARTIAL/BLOCKED. Stop after acceptance; speculative optimization stays a measurement plan.

## Context and reporting

Load each reference once at its trigger; reread only when stale or lost after compaction: [effort.md](references/effort.md) before dispatch; [routing.md](references/routing.md) for Astra admission; [dispatch.md](references/dispatch.md) before delegation/guarded shell; [quality.md](references/quality.md) for checkpointing/recovery/disputed evidence.

Read narrowly; keep log paths. Do not preload docs/hooks or copy the router into children; send contract and role. Long work uses one permitted writer checkpoint. Honor disable/no-subagent/no-escalation. Report requested vs observed; UNKNOWN/MISMATCH suspends auto-low. Never invent identity/savings/cache/enforcement. Collect leaves and reconcile unknown effects before replay. No unobserved cleanup claims or repeated routing banners.
