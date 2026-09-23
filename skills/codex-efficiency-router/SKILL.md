---
name: codex-efficiency-router
description: Quality-gated routing for substantial Codex tasks; use Astra for hard decisions and rare bounded root repairs. Skip tiny work and concurrent routers.
---

# Codex Efficiency Router

<!-- CER version: 0.7.0-rc.15 -->

Preserve quality, authority, parent model; no classifier, hidden CLI/API/config edits.

Installation: fixed; automatic low: disabled.

Report once: `CER v<loaded/UNKNOWN> | <mode> | guard=<policy-only/guarded/live-verified> | policy=<loaded-hash/UNKNOWN>`. Disk is not live proof.

## Before any side effect

Unknown identity/effects grant no writes. Reuse authorized exact-model executors; without authority/ownership/capacity BLOCK/defer. Preserve edits; no auto-revert. Read dispatch before writes/delegation.

Astra leaves and read-only roles NEVER write. Root Astra defaults read-only; host permissions may allow bounded read-only shell/diff/source/log review. Its one bounded local repair unit requires two qualified executor attempts failed or material critical-context loss, authorization, current-workspace target, exclusive ownership and checks; observed active strict Guard disables it. Multiple patches may finish that unit within retained attempts/absolute ceiling. Side-effecting shell, build, test, publish and deploy stay with executors.

Exhaustion stops blind edits, not diagnosis.

## Route once per meaningful decision

Route on phase/evidence changes, failures or user requests, not each tool. Preserve requirement/unit IDs; repair prerequisites first.

| Role | Model / fixed default | Work |
| --- | --- | --- |
| `luna_worker` | `gpt-6-luna` / high | Focused low-risk code; data transforms medium |
| `terra_executor` | `gpt-5.6-terra` / medium | Legacy explicit/fallback |
| `sol_engineer` | `gpt-6-sol` / medium | Ordinary work, diagnosis, integration |
| `astra_architect` | `gpt-6-astra` / high | Exceptional read-only reasoning |

Select model AND effort via `cer_auto_<role>`; read effort. Avoidable base role is MISMATCH. Exact pins win; fallback needs an exact supported pair plus observed selected-model unavailability. Legacy `gpt-5.6-sol/luna` are explicit/fallback only. Low is opt-in; higher efforts need evidence/support. Qualified Ultra is one Sol/Astra coordinator for disjoint leaves with shared limits; no duplicate/recursion. Astra needs consequential hard judgment AND no cheap falsification; parent acceptance applies.

## Decide whether delegation is worth it

Keep sufficient authorized work local. Delegate for capability, ownership or benefit; same-model handoff needs contextual value AND net benefit. Default one leaf; only qualified Ultra coordinates disjoint leaves. Two writers max; no agent per file, recursive Ultra or permission bypass.

## Handoff without losing the decision

Pass outcomes, revision/dirt, rule paths, rationale/invariants, scope/checks, binding/attempts. Receiver reads rules; missing context blocks affected work. Before work identify changed semantic invariants, platform/macros, consumers and validation. Loss/eviction/coalescing must preserve effects or support discard/replay/rebuild across affected states; else PARTIAL/BLOCKED. Requirements win; contrary evidence reopens decisions. Run dispatch preflight.

Child reports evidence, roots, paths/status/diff, checks/gaps, owned/prior dirt. Child PASS is unit evidence, never parent PASS. Parent reviews every diff/actual validation, rechecks corrections, closes blockers and accepts integration.

## Failure, validation, and stopping

Classify failures. Patch mismatch: inspect expected/current context, encoding and line endings; after one justified repair, a second same-signature failure stops blind retry. Retries persist per task/unit/signature across ALL owners, models, efforts and compaction. Exhaustion needs diagnosis and a justified absolute ceiling.

Check requirements/correctness, repo checks/reproduction; new tests are not independent proof. Do not weaken assertions. Reuse evidence. Unrun is UNKNOWN, not PASS; required gaps mean PARTIAL/BLOCKED.

## Context and reporting

Read each reference once at its trigger; reread when stale/lost: [effort.md](references/effort.md) before dispatch; [routing.md](references/routing.md) for Astra admission; [dispatch.md](references/dispatch.md) before delegation/writes; [quality.md](references/quality.md) for recovery/disputed evidence.

Set a global byte/character cap within the smallest outer tool cap; include all shell/web/nested-tool output and margin. `rg -m` and line counts limit per-file matches/lines, not total bytes. Index/split unknowns; resume missing cursor/ranges only without replaying effects; disclose omissions. Read required rules fully in chunks. Reuse tools; act on change/due. Two unchanged snapshots: read one saved-offset delta then back off; no repeat tails/polls/nudges until change. Do not preload docs/hooks or copy router into children. Honor disable/no-subagent/no-escalation. Report requested/observed; UNKNOWN/MISMATCH suspends auto-low. Resolve MISMATCH before continuation. Never invent identity/savings/enforcement/cleanup; reconcile unknown effects before replay. No repeated routing banners.
