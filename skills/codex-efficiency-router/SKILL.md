---
name: codex-efficiency-router
description: Quality-gated routing for substantial Codex tasks; use Astra for hard decisions and rare bounded root repairs. Skip tiny work and concurrent routers.
---

# Codex Efficiency Router

<!-- CER version: 0.7.0-rc.13 -->

Preserve quality, authority and parent model. No extra LLM classifier, hidden CLI/API or config edits.

Installation: fixed; automatic low: disabled.

Report once: `CER v<loaded/UNKNOWN> | <mode> | guard=<policy-only/guarded/live-verified> | policy=<loaded-hash/UNKNOWN>`. Disk is not live proof.

## Before any side effect

Unknown identity/effects grant no writes. Reuse authorized Terra/Sol; missing authority/ownership/capacity means BLOCKED/defer. Preserve edits; never auto-revert. Read dispatch before delegation/writes.

Astra leaves and read-only roles NEVER write. Root Astra defaults read-only; host permissions may allow bounded read-only shell/diff/source/log review. Its one bounded local repair unit requires two qualified executor attempts failed or material critical-context loss, authorization, current-workspace target, exclusive ownership and checks; observed active strict Guard disables it. Multiple patches may finish that unit within retained attempts/absolute ceiling. Side-effecting shell, build, test, publish and deploy stay with executors.

Astra diagnoses hard judgments and qualified failures; Astra reasons locally. Exhaustion stops blind edits, not diagnosis.

## Route once per meaningful decision

Route on phase/evidence changes, failures or user requests, not each tool. Preserve requirement/unit IDs; repair prerequisites first.

| Role | Model / fixed default | Work |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` / medium | Mechanical, low-risk, strongly checked |
| `terra_executor` | `gpt-5.6-terra` / medium | Settled implementation |
| `sol_engineer` | `gpt-5.6-sol` / medium | Diagnosis, coupling, integration |
| `astra_architect` | `gpt-6-astra` / high | Exceptional read-only reasoning |

Select sufficient model AND explicit effort via `cer_auto_<role>` with a concise difficulty basis; read effort. An avoidable base role is MISMATCH; fallback needs evidence and an exact pinned pair. Never auto-select `max`/xhigh/Ultra; low needs opt-in. Exceptional Astra escalation needs consequential hard judgment AND no cheap falsification; parent acceptance still applies to Astra.

## Decide whether delegation is worth it

Keep sufficient authorized work local. Delegate for capability, ownership or net benefit. Same-model delegation needs contextual value AND a net benefit. Default one leaf; at most two disjoint writers, the third waits. No agent per file, recursive workers or permission bypasses.

## Handoff without losing the decision

Pass outcomes, revision/dirty state/paths, rule paths, rationale, invariants, scope, checks, binding and attempts. Read rules separately; missing critical context blocks affected work. Before implementation confirm platform/macros, reachable consumers and validation entry. Requirements win; contrary evidence reopens decisions. Complete the native change-summary preflight in dispatch.

Child reports compact evidence, roots, exact paths/status, diff and checks/gaps; reuse it without repeating the investigation. Child PASS is unit evidence, never parent PASS. Parent inspects every delivered diff and actual validation, corrects and rechecks affected areas, closes blocking findings and accepts integration.

## Failure, validation, and stopping

Classify failures. Patch failure: inspect expected/current context, encoding and line endings; after one justified repair, a second same-signature failure stops blind retry. Attempts stay per task/unit/signature across ALL owners; worker/model/effort/compaction never renews attempts. Exhaustion needs diagnosis and a justified absolute ceiling; no magic reset.

Check requirements, correctness, repository checks and reproduction. New tests are not independent proof. Do not weaken assertions. Reuse current evidence. Unrun is UNKNOWN, not PASS. Every outcome is required for PASS; else PARTIAL/BLOCKED.

## Context and reporting

Read each reference once at its trigger; reread when stale/lost: [effort.md](references/effort.md) before dispatch; [routing.md](references/routing.md) for Astra admission; [dispatch.md](references/dispatch.md) before delegation/writes; [quality.md](references/quality.md) for recovery/disputed evidence.

Bound each batch member; fit total shell/web/nested-tool output+margin in smallest outer cap. Shape unknowns by index/summarize/split; line counts don't bound it. Read required rules fully in chunks. Recover cursor gaps without replaying effects. Reuse tools; act on change/due. Two unchanged snapshots: one saved-offset delta then back off; while unchanged avoid repeat tails/polls/nudges. Do not preload docs/hooks or copy the router into children. Honor disable/no-subagent/no-escalation. Report requested/observed; UNKNOWN/MISMATCH suspends auto-low. Resolve MISMATCH before continuation. Never invent identity/savings/enforcement/cleanup; reconcile unknown effects before replay. No repeated routing banners.
