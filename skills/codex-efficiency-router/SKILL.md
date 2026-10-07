---
name: codex-efficiency-router
description: Complex repo routing and bounded evidence; skip Q&A, status and clear low-risk single-owner tasks. Load SKILL alone in bounded pages.
---

# Codex Efficiency Router

<!-- CER version: 0.8.5 -->

Installation: fixed; automatic low: disabled.

first load SKILL alone in bounded pages. Verified Python `-I -B <Skill>/scripts/readonly_reader.py`: `page --root ABS --path PATH`; same root/path `--cursor TOKEN` to null. Check exit before JSON; no full-file slicing/merging pages/files. Output+framing <=4KiB; unknown framing: gap; handoff both.

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

`batch --help`: checks; substantive events, short state, back off.

Report once: `CER v<loaded/UNKNOWN> | <mode> | guard=<policy-only/guarded/live-verified> | policy=<loaded-hash/UNKNOWN>`. Disk is not live proof.
