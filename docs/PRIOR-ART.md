# Primary sources and adopted experience

Reviewed through **2026-09-23**. This project synthesizes workflow principles; it does not vendor these projects' code. Model-family ranking and policy thresholds are project heuristics, not facts established by the references. Community star counts and unverified benchmark savings are intentionally not used as quality evidence.

## OpenAI documentation

| Primary source | Relevant guidance | Application and boundary |
| --- | --- | --- |
| [Codex Skills](https://developers.openai.com/codex/skills) | Skill metadata discovery, on-demand instructions, packaged references and UI policy | Short metadata, small core, on-demand references. Our description, core and full-reference budgets are project limits in `scripts/package.py`, not official platform limits. |
| [Codex subagents](https://developers.openai.com/codex/subagents) | Standalone agent configuration, model/effort precedence, parent permissions and extra token work | Use native roles; distinguish requested/observed models; avoid unnecessary children. Parent configuration stays unchanged. |
| [Choosing Astra, Sol, and Luna](https://learn.chatgpt.com/docs/models#choosing-astra-sol-and-luna) | Sol Medium and Luna High are recommended defaults; supported effort sets differ by model | Use those defaults where the task lane fits, then require the host catalog and actual runtime evidence for availability. Legacy exact bindings remain compatibility options. |
| [Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization) | Reduce unnecessary requests/output; parallelize suitable work; use non-LLM methods | Native tools first, bounded independent concurrency and stop conditions. No universal speedup percentage. |
| [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) | Prefix-sensitive reuse of stable input | Avoid rewriting stable instructions; do not claim cross-model reuse, zero cached tokens or host controls the Skill lacks. |
| [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | Evaluate workflow components and final outcomes; justify multi-agent complexity through evidence | Separate routing/dispatch tests from real task-quality trials and account for regressions. |
| [Codex App Server](https://developers.openai.com/codex/app-server) | `model/list`, `model/rerouted`, token-usage events | Optional saved catalog validation; actual execution metadata and cumulative-usage deduplication. No silent API/CLI calls. |

## Mature industry practice

**Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents).** Start with the simplest sufficient workflow; orchestration is useful when its added complexity pays. We avoid a permanent planner/router/reviewer chain and choose tools before additional model contexts.

**Anthropic, [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system).** Delegation needs clear task boundaries, output requirements and coordination. Independent research differs from shared-state coding. We require disjoint write ownership and capacity checks; their research-system results are not claimed as Codex coding results.

**Anthropic, [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).** Retrieve relevant context when needed, using compact state and evidence pointers. We preserve critical invariants and unresolved questions rather than copying full transcripts or dropping details to satisfy arbitrary compression targets.

**Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).** Tasks, trials, graders, traces and final outcomes are distinct. We test structural behavior offline and document repeated, independently graded live evaluations separately. A syntactically valid Skill or plausible trajectory is not a successful engineering outcome.

**Aider, [Separating code reasoning and editing](https://aider.chat/2024/09/26/architect.html), [chat modes](https://aider.chat/docs/usage/modes.html).** Architect/editor separation motivates a compact decision contract followed by bounded implementation. We adopt the separation, not a mandatory two-call sequence or a claim that every model pair benefits.

**LMSYS, [RouteLLM](https://github.com/lm-sys/RouteLLM).** Cost-quality routing requires workload-specific calibration. We adopt the evaluation mindset, not a learned online classifier or transferred benchmark percentages. This package makes no model-optimality claim without user-host measurements.

## Deliberately not adopted

No paid inference solely to select a model; no unbounded agent swarm; no fixed startup-time assumptions from another machine; no retry-count-only escalation; no technology keyword forcing Astra; no higher effort without parent-reviewed task evidence; no Ultra without one authorized coordinator and disjoint beneficial work; no automatic test deletion; no blanket independent reviewer for every change. We also avoid importing undocumented hook/configuration fields from small community projects.

[Audit decisions and validation limits](AUDIT-2026-09-07.md)

## v0.2.1 recheck

The official Skills and Subagents pages and all four model pages were rechecked on 2026-09-07. Four presets remain unchanged; role-file model/effort precedence is preserved. Same-lane recovery and instruction-budget thresholds are local engineering decisions motivated by the retained failed evaluation, not newly claimed platform features. User acceptance, not this documentation review, establishes actual model execution.

## v0.3 Codex-only adaptation

[Quality protocol](QUALITY-PROTOCOL.md) maps current primary-source designs to concrete completion, handoff and recovery rules. Sources rechecked on 2026-09-07 include official Codex Skills/Subagents/evals, Aider Architect/Editor, Superpowers task review/progress, and Anthropic context engineering/skill-creator. Only ideas are adopted: no third-party runtime, Claude CLI, compulsory review chain, hidden model call or additional model tier. The natural-language corpus is prepared, not live-tested.

## v0.4 documentation recheck — 2026-09-08

OpenAI Subagents, Skills and App Server documentation were rechecked for role-file precedence, explicit effort, catalog support and next-turn versus steer behavior. Native capability exposure is not assumed from a documentation API alone. The [adaptive-effort design](ADAPTIVE-EFFORT.md) records what is implemented and what requires user-host acceptance; no learned classifier, foreign runtime or benchmark percentage is imported.

## v0.5 capability-adaptive installation

Reviewed 2026-09-08. [Superpowers Codex tooling](https://github.com/obra/superpowers/blob/main/skills/using-superpowers/references/codex-tools.md) trusts actual schemas/allowlists and explicit model+effort, rather than hardcoded assumptions. [Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) adapts available workflow mechanics without asserting missing capabilities. Combined with [OpenAI role-file precedence](https://developers.openai.com/codex/subagents), these motivate one ordinary installation and native binding selection. We do not copy their runtime, obsolete feature flags, wait constants or benchmark claims. The exact dual-binding mechanism is this project's design, not an upstream product claim. [Details](ADAPTIVE-EFFORT.md).
