---
name: codex-efficiency-router
description: Multi-step repo work/delegation/large evidence reads; first load SKILL alone in bounded pages; skip tiny work/concurrent routers.
---

# Codex Efficiency Router

<!-- CER version: 0.8.5 -->

Keep quality/authority/parent model; no classifier or hidden CLI/API/config edits.

Installation: fixed; automatic low: disabled.

Verified Python `-I -B <Skill>/scripts/readonly_reader.py`; handoff both. All ops: `--root ABS --path PATH`. Files/rules: `page`, same root/path `--cursor TOKEN` to null; unknown: `locate --query Q`; current located lines: `excerpt --start N --lines N` (count 1..200). JSON: `json --help`. Check exit before JSON; fix limits/page/locate on error. Page <=4096B; no full-file slicing/merging pages/files.

Report once: `CER v<loaded/UNKNOWN> | <mode> | guard=<policy-only/guarded/live-verified> | policy=<loaded-hash/UNKNOWN>`. Disk is not live proof.

## Authority

Unknown identity/effects grant no writes. Spawn/resume children read-only until parent verifies/releases binding/unit; authority/ownership/capacity gaps BLOCK/defer. Keep edits; no auto-revert. Read dispatch before writes/delegation.

Astra leaves and read-only roles NEVER write. Root Astra defaults read-only; bounded review needs host permission. Its one bounded local repair unit needs two failed qualified executor attempts or material critical-context loss, authority, current-workspace target, exclusive ownership/checks, no observed active strict Guard; shared attempts/absolute ceiling. Executors own shell/build/test/publish/deploy.

Exhaustion stops blind edits, not diagnosis.

## Routing

Keep requirement/unit IDs; route by phase/evidence/failure/user changes; fix prerequisites.

Select model AND effort via `cer_auto_<role>`; dispatch loads role table/effort. Avoidable base role is MISMATCH; exact pins win. Low opt-in; higher efforts need evidence/support. Astra admission needs routing and parent acceptance.

## Delegate

Keep enough authorized work local. Delegate for capability/ownership/benefit; same-model needs contextual value AND net benefit. Default one leaf; qualified Sol/Astra Ultra only: disjoint leaves/shared limits, no duplicate/recursion. Two writers max; no agent per file or permission bypass.

## Handoff

Handoff only owned unit: outcomes, revision/dirt, rule paths, rationale/invariants, scope/checks, binding/attempts; `fork_turns=none`. Read rules; gaps block affected work. Check semantic invariants, platform/macros, consumers, validation. Loss/eviction/coalescing: preserve effects or supported discard/replay/rebuild across affected states; else PARTIAL/BLOCKED. Requirements win; contrary evidence reopens decisions. Run dispatch preflight.

Child: current evidence, roots, paths/status/diff, checks/gaps, owned/prior dirt; unit PASS never parent PASS. Parent reviews all diffs/actual validation, rechecks fixes, closes blockers/accepts integration. Keep workers through checks/delivery/acceptance.

## Recovery

Classify failures. Patch mismatch: inspect context/encoding/line endings; one justified repair, then repeat stops blind retry. Retries persist per task/unit/signature across ALL owners/models/efforts/compaction; exhaustion needs diagnosis and justified absolute ceiling.

Check requirements/correctness, repo checks/reproduction; new tests are not independent proof. Do not weaken assertions. Reuse only scope-bound current evidence (quality). Unrun is UNKNOWN, not PASS; required gaps mean PARTIAL/BLOCKED.

## Context and reporting

Read references on trigger/stale/lost: [effort.md](references/effort.md) before dispatch; [routing.md](references/routing.md) for Astra admission; [dispatch.md](references/dispatch.md) before delegation/writes; [quality.md](references/quality.md) for recovery/disputed evidence.

Other tools: capture result, select fields, retain cursor, serialize/count total output below outer incl framing, then emit one page; index unknowns. Inner/item/line caps fail. Resume gaps, shrink batches, disclose omissions. Reuse tools; act on change/due. Two unchanged snapshots: one saved-offset delta then back off; no repeat tails/polls/nudges until change. No doc/hook preload or child router copy. Honor disable/no-subagent/no-escalation. Report requested/observed; UNKNOWN/MISMATCH suspends auto-low. Resolve MISMATCH before continuation. Never invent identity/savings/enforcement/cleanup; reconcile unknown effects before replay.
