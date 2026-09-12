---
name: codex-efficiency-router
description: Quality-gated routing for substantial Codex tasks; use Astra for hard decisions and rare bounded root repairs. Skip tiny work and concurrent routers.
---

# Codex Efficiency Router

<!-- CER version: 0.7.0-rc.8 -->

Preserve quality, authority and parent model. No extra LLM classifier, per-turn scripts, hidden CLI/API or config changes.

Installation: fixed; automatic low: disabled.

Report once: `CER v<loaded/UNKNOWN> | <mode> | guard=<policy-only/guarded/live-verified> | policy=<loaded-hash/UNKNOWN>`. Disk is not loaded proof; guarded is not enforced. Live-verified needs a current scoped native Canary. Reload at safe boundaries.

## Before any side effect

Authority precedes shortcuts. Unknown identity/effects grant no writes. Reuse an authorized Terra/Sol owner; missing authority/ownership/capacity means BLOCKED/defer. Preserve edits for review; never auto-revert.

Astra leaves and read-only roles NEVER write. Root Astra defaults read-only. Allow one bounded local repair unit after two qualified executor attempts failed on an implementation/capability/unexplained issue OR handoff would materially lose critical reasoning. Authorization, exact scope, current-workspace target, ownership, safe boundary and verification must be known. No competing writer/prior completed exception unit may exist; observed active strict Guard disables it. Unknown Guard may deny. Multiple patches may finish that unit; prerequisites, capability/effort floors and the absolute retry ceiling still apply. Shell/build/format/side-effecting tests/publish/deploy stay with executors.

Astra diagnoses hard judgments and qualified failures; already-Astra reasons locally. Exhaustion stops blind edits, not diagnosis.

## Route once per meaningful decision

Route on phase/evidence changes, classified failures or user requests, not each tool. Preserve requirement/unit IDs; repair prerequisites before escalating.

| Role | Model / fixed default | Work |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` / medium | Mechanical, low-risk, strongly checked |
| `terra_executor` | `gpt-5.6-terra` / medium | Settled implementation |
| `sol_engineer` | `gpt-5.6-sol` / medium | Diagnosis, coupling, integration |
| `astra_architect` | `gpt-6-astra` / high | Exceptional read-only reasoning |

Select sufficient model AND explicit effort via `cer_auto_<role>`; an avoidable base role is MISMATCH. Fallback needs unavailable alias/field evidence and an exact pinned pair. Never auto-select `max`/xhigh/Ultra; low needs opt-in. Astra needs useful stronger reasoning, consequentially hard judgment AND no cheap falsification.

## Decide whether delegation is worth it

Keep sufficient authorized work local. Delegate only for capability, ownership or net benefit after coordination/rework. Same-model delegation needs contextual value AND a net benefit. Never weaken unresolved execution.

Default one leaf; at most two concurrent writers, the third waits. Require disjoint writes/resources and independent acceptance. No agent per file, recursive workers, ritual reviewers or permission bypasses.

## Handoff without losing the decision

Pass outcomes, revision/dirty state/paths, rule paths, decision rationale, invariants, write scope, checks, binding and attempts. Read applicable rules; missing critical context blocks affected work. Requirements win; contrary evidence reopens decisions. Parent completes the native change-summary preflight in dispatch and verifies integration, not just child success.

## Failure, validation, and stopping

Classify prerequisite/environment/observability/implementation/capability failures. Allow one targeted repair after initial failure per task/unit/signature across ALL owners. Worker/model/effort/compaction never renews attempts. Exhaustion needs diagnosis or a justified absolute attempt ceiling; a reason string or patch never resets history.

Check requirements, correctness, repository checks and reproduction. New tests are not independent proof. Do not weaken assertions or waive acceptance. Reuse evidence still valid for final code/environment. Unrun is UNKNOWN, not PASS. PASS needs every outcome; else PARTIAL/BLOCKED. Stop after acceptance.

## Context and reporting

Read each reference once at its trigger; reread when stale or lost after compaction: [effort.md](references/effort.md) before dispatch; [routing.md](references/routing.md) for Astra admission; [dispatch.md](references/dispatch.md) before delegation/guarded shell; [quality.md](references/quality.md) for checkpointing/recovery/disputed evidence.

Read mandatory rule files in separate outputs. Index other unknown-size files; batch only known-small slices. After truncation continue missing ranges, never reread captured text. Keep logs on disk. Do not preload docs/hooks or copy the router into children. One checkpoint for long work. Honor disable/no-subagent/no-escalation. Report requested vs observed; UNKNOWN/MISMATCH suspends auto-low. Resolve MISMATCH before continuation. Never invent identity/savings/enforcement. Reconcile unknown effects before replay. No unobserved cleanup claims or repeated routing banners.
