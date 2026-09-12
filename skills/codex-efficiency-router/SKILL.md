---
name: codex-efficiency-router
description: Quality-gated routing for substantial Codex tasks; use Astra for hard decisions and rare bounded root repairs. Skip tiny work and concurrent routers.
---

# Codex Efficiency Router

<!-- CER version: 0.7.0-rc.5 -->

Preserve quality, authority and parent model. No extra LLM classifier, per-turn scripts, hidden CLI/API or config changes.

Installation: fixed; automatic low: disabled.

Report once: `CER v<loaded/UNKNOWN> | <mode> | guard=<policy-only/guarded/live-verified> | policy=<loaded-hash/UNKNOWN>`. Disk is not loaded-state proof; guarded is not enforced. Require current scoped native Canary for live-verified; reload only at safe boundaries.

## Before any side effect

Authority precedes shortcuts. Unknown identity/effects grant no writes. Reuse an authorized Terra/Sol owner; missing authority/ownership/capacity means BLOCKED/defer. Preserve edits for review; never auto-revert.

Astra leaves and read-only roles NEVER write. Root Astra defaults read-only, but may apply one bounded local code patch only when two qualified executor attempts failed on an implementation/capability/unexplained issue OR handoff would materially lose critical reasoning, and authorization, exact scope, current-workspace target, ownership, safe boundary and verification are established. No writer or prior exception may exist; strict Guard must be confirmed inactive. The exception excludes shell/build/format/side-effecting tests and publish/deploy; executors handle those.

Astra diagnoses hard judgments and qualified failures; already-Astra reasons locally. Exhaustion stops blind edits, not diagnosis.

## Route once per meaningful decision

Route on phase/evidence changes, classified failures or user requests, not each tool. Preserve requirement/unit IDs; repair prerequisites before escalating.

| Role | Model / fixed default | Work |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` / medium | Mechanical, low-risk, strongly checked |
| `terra_executor` | `gpt-5.6-terra` / medium | Settled implementation |
| `sol_engineer` | `gpt-5.6-sol` / medium | Diagnosis, coupling, integration |
| `astra_architect` | `gpt-6-astra` / high | Exceptional read-only reasoning |

Select sufficient model AND effort. If the schema exposes `reasoning_effort` and matching `cer_auto_<role>`, use it with explicit effort; a base role is MISMATCH. Base roles need unavailable alias/field evidence and an exact pinned pair. Never auto-select `max`/xhigh/Ultra; auto-low needs opt-in. Astra needs useful stronger reasoning, consequentially hard judgment AND no cheap falsification.

## Decide whether delegation is worth it

Keep sufficient authorized work local; prefer safe tool concurrency. Delegate for capability, ownership or net benefit after coordination/rework. Same-model delegation at identical effort needs contextual value AND a net benefit. Never weaken unresolved execution.

Default one leaf; at most two concurrent writers, the third waits. Require disjoint writes/resources and independent acceptance. No agent per file, recursive workers, ritual reviewers or conflicting side effects. Use supported native bindings, not permission bypasses.

## Handoff without losing the decision

Pass outcomes, revision/dirty state/paths, facts/assumptions/evidence, invariants, allowed writes, checks, binding and attempts; no transcripts/secrets. Receiver checks state/conflicts. Requirements outrank plans; contrary evidence reopens decisions. Parent completes the native change-summary preflight in dispatch and verifies integration, not just child success.

## Failure, validation, and stopping

Classify prerequisite/environment/observability/implementation/capability failures. Allow one targeted repair after initial failure per task/unit/signature across ALL owners. Worker/model/effort/compaction never renews attempts. Exhaustion needs diagnosis/experiment/escalation or a justified bounded extension retaining history.

Check requirements, correctness, repository checks and reproduction. New tests are not independent proof. Do not weaken assertions or waive acceptance. Bind evidence to final code/checks/environment; reuse unaffected checks. Unrun is UNKNOWN, not PASS. PASS needs every outcome; else PARTIAL/BLOCKED. Stop after acceptance.

## Context and reporting

Load each reference once at its trigger; reread only when stale or lost after compaction: [effort.md](references/effort.md) before dispatch; [routing.md](references/routing.md) for Astra admission; [dispatch.md](references/dispatch.md) before delegation/guarded shell; [quality.md](references/quality.md) for checkpointing/recovery/disputed evidence.

Read narrowly; keep log paths. Do not preload docs/hooks or copy the router into children; send contract and role. Long work uses one permitted checkpoint. Honor disable/no-subagent/no-escalation. Report requested vs observed; UNKNOWN/MISMATCH suspends auto-low. Never invent identity/savings/cache/enforcement. Reconcile unknown effects before replay. No unobserved cleanup claims or repeated routing banners.
