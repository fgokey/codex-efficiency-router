# v0.3 quality protocol: Codex only

## Scope

This is still one Codex Skill, four role responsibilities (auto supplies two native bindings each) and offline maintenance tools. No Claude/Roo/Cline runtime, foreign configuration, proxy, model classifier, mandatory reviewer agent or online calibration is added. Model/effort presets and parent selection are unchanged. The installer remains offline and does not edit global config. Source instruction budgets remain 6,500 core / 12,000 full-reference UTF-8 bytes, not platform limits.

## Contract before execution

Use a stable task/unit identity and contract revision for substantial work. Keep required outcomes and invariants, write boundaries, evidence pointers, code/dirty state and remaining attempts in the existing handoff. The receiver checks completeness, material assumptions and conflicts with user/repository requirements before edits. Block the affected scope on conflict while preserving independent safe work. A strong model's plan is a proposal, not higher authority.

Frozen decisions reduce repeated reasoning; they are not immune to contrary evidence. An authoritative change creates a new contract revision and records the earlier unmet requirement. An executor cannot waive its own failed checks.

## Completion is criterion-based

Map each required outcome to current check/review evidence. Include mandated integration and residual-risk review as requirements rather than treating unit success as project success. Review missing/extra/misread behavior and implementation correctness in one bounded pass; separate agents only when independent judgment adds value.

PASS requires all required outcomes supported and no blocking finding. PARTIAL preserves useful output but acknowledges missing work/evidence. BLOCKED names a prerequisite or decision preventing continuation. Optional disclosed risks can coexist with PASS; missing required work cannot. A plausible narrative or schema-valid report is not evidence. Read-only design tasks can use reasoned review against explicit criteria; there is no mandatory build for prose.

Evidence applies to relevant final state: code/diff, test definitions, dependencies and environment. Matching HEAD alone does not prove freshness. Reuse unaffected checks; revalidate changed or uncertain parts. Do not rerun everything by default or accept stale green results.

## Recovery and bounded retry

An implementation failure allows one targeted repair, shared across workers for that task/unit/failure signature. Worker/model changes and compaction do not renew the budget. Preserve approaches that failed and evidence that ruled them out. Exhaustion triggers diagnosis, a discriminating experiment or escalation; a bounded extension needs an explicit justified parent reassessment, not renaming the failure.

Only long work or recovery needs a task-scoped checkpoint in a permitted location. Reuse an existing project mechanism when suitable. One parent owns it; no per-turn ledger or separate daemon. Reconcile the record with actual files and worker state, reuse valid completed units and preserve retries. Unknown in-flight work or external side effects must be reconciled before replay. Never overwrite another task's record or persist secrets.

## Offline references and real acceptance

`scripts/quality_reference.py` provides pure completion, handoff, retry and resume helpers. They consume declared conditions; they do not inspect code, authenticate authority, read actual checkpoints, invoke Codex or enforce the host. `tests/test_quality_protocol.py` and selected mutations guard those finite semantics, not model reasoning.

`evaluation/behavior_cases.json` contains 20 user-run prompts with setup, expected observations and prohibited behavior. CI checks structure and keeps `live_result=null`. For real evaluation, give the agent the task/setup, not the grader's answer. Grade traces, changes and outcomes independently; preserve failures and unknowns. No keyword classifier or same-model self-score substitutes for execution. Actual model-pair calibration is deferred until usable task evidence exists.

The paired-run comparator now distinguishes no relative regression from completed acceptance. Two failures cannot produce a successful CLI exit; missing usage cannot authorize an efficiency claim. Descriptive sample results still do not establish future quality or statistical non-inferiority.

## Adopted designs and boundaries

Reviewed 2026-09-07; original design synthesis, no copied third-party code:

| Primary source | Adopted here | Not imported |
| --- | --- | --- |
| [OpenAI Codex Skills](https://developers.openai.com/codex/skills) | Small entry point, on-demand references | No always-loaded external framework |
| [OpenAI Codex Subagents](https://developers.openai.com/codex/subagents) | Native roles, pinned effort, observed identity, bounded scope | No invented dispatch or model-switch APIs |
| [OpenAI evaluation practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | Fixed required outcomes, distinct offline and live evidence | No offline-test-to-model-quality leap |
| [Aider Architect/Editor](https://aider.chat/2024/09/26/architect.html) | Explicit decision-to-edit handoff | No mandatory second call or transferred benchmark win |
| [Superpowers subagent workflow](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md) | Requirement fit, bounded review, recoverable progress | No compulsory workflow chain or its runtime scripts |
| [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Compact relevant state across long work | No per-turn notebook or other platform config |
| [Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) | Realistic positive/negative prompts, optional independent grading | No Claude CLI invocation, auto-eval spending or blind score claims |

[User acceptance](ACCEPTANCE.md) · [Offline audit](../evaluation/README.md) · [Broader references](PRIOR-ART.md)
