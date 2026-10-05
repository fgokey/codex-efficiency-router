---
name: codex-efficiency-router
description: Complex repo routing and bounded evidence; skip Q&A, status and clear low-risk single-owner tasks.
---

# Codex Efficiency Router

<!-- CER version: 0.8.5 -->

Installation: fixed; automatic low: disabled.

Keep parent model/exact pins; Low is opt-in; no classifier/nested model CLI/API/hidden config edits.

Cheap: Q&A, status and bounded low-risk single-owner work: no routing, references or children. Honor repo rules, current permissions/read-only roles. Unknown identity/effects grant no writes. If an executor is required, use routing.

## Routing

Read [effort.md](references/effort.md) before dispatch/lane changes; [routing.md](references/routing.md) for Astra admission.

## Delegate

Read [dispatch.md](references/dispatch.md) before delegation, binding or delivery review. Children start read-only; parent verifies/releases writes. Astra leaves and read-only roles NEVER write. Root Astra defaults read-only; read dispatch for exceptions.

## Handoff

Owned scope; requirements win; acceptance: dispatch.

## Recovery

Read [quality.md](references/quality.md) for large evidence, semantic/lifecycle changes, failure or disputed validation. Retain attempts; do not weaken assertions.

## Context and reporting

Verified Python `-I -B <Skill>/scripts/readonly_reader.py`, one page, default `--max-bytes 3072`; output+framing <=4KiB, unknown framing is a gap. Batch independent read-only checks once; act on substantive events, save short state, back off.

Report once: `CER v<loaded/UNKNOWN> | <mode> | guard=<policy-only/guarded/live-verified> | policy=<loaded-hash/UNKNOWN>`. Disk is not live proof.
