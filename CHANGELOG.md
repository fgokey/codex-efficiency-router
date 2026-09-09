# Changelog

## Unreleased — rc.2 compatibility corrections

- Isolate the readonly Git fixture from automatic maintenance and external config; keep byte-for-byte workspace and .git checks and exercise an actual external-diff sentinel. Fixes the maintenance.lock race seen in validate #27 on macOS/Python 3.11. No platform is skipped to obtain green CI.
- Add a shared Windows launcher with actual Python 3.11+/tomllib preflight and authoritative CER_PYTHON override. Install, uninstall, doctor, standalone Guard and Canary use the same selected interpreter; no Python downloads or PATH/config changes.
- Keep policy-only, native Canary and real-task accounting boundaries explicit. These corrections do not enable or trust Hooks, certify performance, or constitute a stable release.

## 0.7.0-rc.2 — 2026-09-09 (candidate, not published)

- Compress the core Skill, private references and self-contained worker instructions.
- Add explicit once-per-valid-context reference triggers, no blanket docs/hooks loading,
  no copying the full Router into children, and no repeated routing banners.
- Tighten core/full/discovery budgets and add per-role instruction-size enforcement.
- Report source instruction bytes in doctor JSON; not model token counts or billing.
- Preserve model/effort presets, fixed/low opt-outs, guard decisions, ownership,
  evidence requirements and task-wide repair budgets. No new runtime calls or service.
- Refresh version/digest metadata; old Canary evidence cannot certify this candidate.
- Native prompt-compliance, exact token counts, Windows Canary and live costs NOT VERIFIED.

## 0.7.0-rc.1 — 2026-09-09 (candidate, not published)

- Add portable plugin packaging, synchronized version/hash checks and deterministic ZIP provenance.
- Separate policy, registration, trust, current task loading and native Canary evidence.
- Add read-only JSON diagnostics and explicit Guard update; preserve external changes on rollback.
- Bind registered hook definitions to exact script hashes; reject unaudited model suffix aliases.
- Add bounded, whole-batch-preflight `cer-read batch` and explicit local latency measurement.
- Add operator-witnessed native Canary preparation/verification without nested model calls.
- Add three-arm per-call accounting; distinguish actual cost, rate-card estimate and UNKNOWN.
- Preserve existing fixed profile, low opt-in rules, writer ownership and active Astra diagnosis.
- Pending: Windows/macOS execution, native Codex trust/Canary, live cost/quality trials, tag and release.


## [0.6.0] - 2026-09-09

- Put actor write authority ahead of local/cost fallbacks; include Astra roots and leaves.
- Preserve existing edits and task-wide attempts; prefer compatible Terra/Sol owners, never a third active writer.
- Keep Astra actively involved in hard decisions and qualified repeated failures; repair exhaustion does not disable read-only diagnosis.
- Add an optional synchronous native PreToolUse guard, bounded reader protocol, owned hook registration/removal and explicit trust/coverage limits.
- Add operation-aware, real-sentinel synthetic-host, lifecycle and adversarial tests. No live Codex task is started.


## [0.5.0] - 2026-09-08

- Ordinary install/update now uses automatic native capability adaptation, without routine mode flags.
- Generate four unpinned aliases alongside four fixed roles; use one exact supported binding per child, not extra workers.
- Retain safe quality/effort gates, opt-outs, attempt history and unavailable-role memory. No hidden probes, config rewriting or silent effort remapping.
- Migrate legacy manifests with a printed notice/backup; preserve subsequent explicit overrides and local modification protection.
- Extend generation, migration, collision, restore, capability and mutation coverage; measure alias metadata separately.
- Native execution and whole-task quality/cost remain user acceptance, not offline guarantees.

## [0.4.0] - 2026-09-08

- Added explicit fixed/adaptive installation profiles, generated from the same four
  role sources. Updates preserve the mode and low opt-in; restore preserves both.
- Parent policy jointly selects model/effort: medium/high by default, conservative
  automatic Astra high, opt-in strictly mechanical Luna low, explicit-only xhigh/max.
- Added native-field, role-pin and supported-pair checks; no silent effort fallback.
- Distinguished identical-pair recovery from same-model deeper reasoning. No-escalation
  controls both axes; safe boundaries and task-wide retry history remain mandatory.
- Added offline joint-policy/lifecycle/catalog tests and effort mutation checks.
- Documented actual tool exposure and runtime identity as user acceptance, not a
  guaranteed hot-switch API. No model inference is performed by installation/CI.

## [0.3.0] - 2026-09-07

- Codex-only adaptation of mature decision/editor, requirement review and compact recovery patterns; no foreign runtime or extra model tier.
- Current-evidence completion gates (PASS/PARTIAL/BLOCKED), receiver conflict checks and shared task-level retry history.
- One optional task checkpoint for long work/recovery; reconcile active workers and uncertain side effects before replay.
- Added pure offline quality references, selected quality mutations and 20 user-run natural-language acceptance cases (not live-scored).
- Paired comparison can no longer exit successfully when Router acceptance is incomplete, even if both variants fail.
- Three on-demand references; unchanged core/full byte budgets plus v0.2.1-relative core/full/per-role text-token regression gates.
- Four models/efforts, config ownership, install/uninstall/restore semantics unchanged. Real quality and usage remain user acceptance.

## [0.2.1] - 2026-09-07

### Fixed
- Same-lane delegation now requires a specific contextual reason and net benefit;
  an insufficient agent cannot solve the same unresolved task by downgrading.
- User opt-out tests enable real dispatch availability and causal positive controls;
  removing the guard is detected by mutation testing.
- Compressed duplicated core/reference instructions with full-load budgets, rather
  than claiming savings from the entry file alone.
- Kept four role presets; corrected five-tier and uninstall/auto-restore misunderstandings.
- Added CLI/documentation consistency checks and separate offline mutation/token CI.

### Validation boundary
- No Codex model task or paid API inference is run by this release workflow.
- Actual host role/model identity, coding quality, total usage and latency remain
  user-run acceptance; historical failing evaluations are retained.


## [0.2.0] - 2026-09-07

### Changed
- Audited against current OpenAI documentation and primary industry engineering guidance.
- Reduced the on-demand Skill core through packaged progressive references; kept quality gates.
- Separated capability recommendation, dispatch admission and observed runtime identity.
- Replaced mandatory downgrade with benefit-gated handoff after decisions settle.
- Encoded cheap discriminating checks, prerequisite repair and classified capability failure.
- Removed recursive leaf delegation and any automatic maximum-effort exception.
- Added manifest-owned install/update/uninstall, explicit verified v0.1 adoption, collision protection,
  modification detection, retained backups, ordinary-failure rollback and guarded restore.
- Made doctor explicitly static; added optional exported model/list validation.
- Added paired-run comparison with unknown measurements and regression handling, not a live benchmark.
- Expanded regression/safety tests and CI platforms; rewrote install and uninstall commands in both READMEs.

### Limits
- Live model execution and coding-quality/token/latency improvements are not established by these offline tests.
- Multi-file lifecycle operations are not power-loss atomic; retained backups support recovery.

## Historical v0.1.0 refinement - 2026-09-07

### Changed
- Replaced technology-keyword Astra triggers with a general reasoning-escalation gate based on reducible uncertainty, failure cost/reversibility, coupling, verifiability, novelty, evidence conflict, and qualified prior failure.
- Added failure triage before model escalation: specification, environment, verifiability, implementation, and capability failures now have distinct responses.
- Added explicit Astra task shapes for commitment boundaries, consequential ambiguity, deep evidence arbitration, costly migration/rollout strategy, novel mechanisms, technical arbitration, and proven Sol capability failure.
- Added regression cases proving that frozen high-risk implementation, missing requirements, environment failures, and observability gaps do not automatically route to Astra.
- Added `docs/ASTRA-ESCALATION.md` and expanded prior-art documentation.

## [0.1.0] - 2026-09-07

### Added
- Initial `codex-efficiency-router` Skill.
- GPT-6 Astra escalation lane using `gpt-6-astra`.
- GPT-5.6 Sol, Terra, and Luna execution presets.
- Quality-first routing policy with mandatory de-escalation after decisions freeze.
- Token/latency guardrails: one-agent default, direct tool concurrency, bounded subagents, compact handoffs.
- User- and repository-scoped cross-platform installers.
- Doctor, uninstall, routing regression cases, CI, security, contributing, and bilingual documentation.
