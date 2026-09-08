# Automatic capability adaptation — v0.5

## Product behavior

Ordinary install/update is auto. Users do not choose fixed/adaptive to suit each Codex host. The parent selects a model/effort pair from task evidence, then a supported native binding. No new model level, classifier call, proxy, daemon, hidden CLI or in-flight hot switching is introduced.

Four canonical fixed definitions generate four additional aliases named `cer_auto_<role>` in files `cer-auto-<original-file>.toml`. Aliases preserve model, developer instructions and sandbox fields exactly, changing only name and removing the top-level effort pin. Auto installs eight bindings; explicit legacy fixed/adaptive overrides install four. A file does not spawn a worker. Extra role discovery text has a cost and is reported separately.

## Admission order

Apply requirements, quality floors, user opt-outs/ceilings, shared repair budgets, safe boundaries and benefit gates BEFORE choosing a binding. Then:

1. Prefer a discovered matching unpinned alias when native tools expose explicit effort. Pass the chosen model and effort using the actual schema.
2. Otherwise use the matching fixed base role only when its pinned model AND effort equal the selected pair.
3. If no binding qualifies, keep an adequate current agent or report BLOCKED. Explicit unfulfilled settings are disclosed. Never invent parameters, ignore pins, inherit an unknown effort, reduce high to medium or upgrade models solely for compatibility.

Missing alias, lack of native effort, and bad configuration can select the verified compatibility binding BEFORE any child is spawned. This is not failed-model trial and error. Cache confirmed failed bindings per task. A runtime failure does not permit immediate replay: reconcile child status and external effects first. Both bindings share the same unit, ownership, acceptance and attempt history. No failed role probes in loops; no configuration rewrite.

`Decision.requested_role` identifies the actual binding. `recommended` and `requested` contain capability pairs; their conceptual role property is not necessarily the dispatched alias. `binding_kind` is advisory selection, not proof a model ran. Host metadata verifies actual identity; role self-description does not. UNKNOWN/MISMATCH keep auto-low suspended for the task.

## Defaults and overrides

Medium for ordinary implementation; high for deeper suitable reasoning; automatic Astra high. Auto-low remains separately opt-in for strong-check mechanical Luna work with low consequences and no unresolved issues/prior failure. Explicit preferences never waive quality or authority. No-escalation constrains model and effort separately; keep-model may allow effort changes. No forced capability ladder, no automatic xhigh/max. A disabled or unsupported route never certifies a weak parent as sufficient.

New installations and ordinary upgrades from old manifests use auto. Pre-v0.5 manifests cannot prove whether fixed/adaptive was an explicit preference; migration is printed before mutation, with backups and customization checks. New manifests use `profile_schema=2`; explicit advanced overrides made with this version survive later plain updates. Existing low choices are preserved unless switching to fixed. Restore reads old profiles literally and never performs migration. These are package fields, not Codex configuration keys.

## Evidence and scope

Source doctor validates four fixed definitions; installed doctor validates all bindings required by that installation. Optional saved catalog checking in auto requires baseline fixed pairs, not every unused high setting. Each actual dispatch must confirm its selected pair. Neither a catalog export nor file validation proves runtime loading. No credentials, model probes or extra sessions are used by maintenance tools.

Runtime rules live in the Skill; Python is an offline reference, not a hard enforcement layer. Live capability selection, model identity, quality, total tokens and latency remain user-run acceptance. Existing byte/token gates stay in force. Additional alias descriptions are measured, not claimed free.

## Primary sources reviewed 2026-09-08

- [OpenAI Subagents](https://developers.openai.com/codex/subagents): loaded file model/effort precedence, native configuration and inherited settings. This is why compatibility uses pinned files and dynamic selection uses unpinned aliases, not contradictory overrides.
- [OpenAI Skills](https://developers.openai.com/codex/skills): on-demand instructions and self-contained references. Keep one public workflow rather than multiplying user procedures.
- [Superpowers Codex tooling](https://github.com/obra/superpowers/blob/main/skills/using-superpowers/references/codex-tools.md): trust actual tools/allowlists and explicitly specify model AND effort. We do not copy its version-specific flags or wait constants.
- [Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md): adjust workflow to available tools and avoid unsupported benchmark claims. We adopt capability checking, not a Claude runtime.

This design is a local engineering synthesis, not a claim that any referenced project implements this exact binding scheme. [Acceptance](ACCEPTANCE.md) · [Installation](INSTALL.md).
