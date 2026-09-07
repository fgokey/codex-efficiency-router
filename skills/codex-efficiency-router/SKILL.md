---
name: codex-efficiency-router
description: Quality-gated model and reasoning router for substantial Codex engineering work. Reduce token use and elapsed time without intentionally lowering correctness by keeping one agent by default, using direct tool concurrency where possible, routing deterministic work to GPT-5.6 Luna/Terra, complex engineering to GPT-5.6 Sol, and escalating only the hardest unresolved high-risk decisions to GPT-6 Astra. Use for coding, debugging, refactoring, reviews, tests, builds, architecture, performance/memory investigations, or long multi-step repository work where model efficiency matters. Do not trigger for simple factual questions or tiny edits that the current model can finish directly.
---

# Codex Efficiency Router

Optimize **verified task success per expensive-model token and unit of wall-clock time**.

Quality is a hard constraint. Never save tokens by knowingly accepting weaker correctness, skipping necessary verification, or assigning a task to a model that is not sufficient for its risk.

## 1. Default: do less routing

For each meaningful task unit, make one fast routing decision from the evidence already available. Do not call another model merely to classify the task.

Prefer, in order:

1. **Current agent + direct tools** when it can finish reliably.
2. **Direct tool/process concurrency** for independent safe reads, searches, metadata queries, or isolated checks.
3. **One bounded child agent** only when a different model is materially better for cost, latency, or capability and the expected benefit exceeds startup/context/aggregation overhead.
4. **Multiple agents** only for genuinely independent workstreams with clear ownership and integration checks.

Do not create agents just because parallelism exists. Additional agents usually increase total context and token use.

## 2. Route by unresolved reasoning, not task size

### L0 — Luna / medium: mechanical lane

Model preset: `gpt-5.6-luna` / `medium`.

Route to `luna_worker` when all important decisions are already known and the work is narrow, repetitive, low-risk, and easy to verify.

Typical work:
- deterministic multi-file edits;
- call-site migrations or renames;
- known config/generated-file updates;
- straightforward tests from explicit acceptance criteria;
- build/test execution;
- obvious compiler/type/lint fixes;
- bounded log filtering or evidence extraction.

Do not use Luna when architecture, root cause, behavioral intent, or important invariants remain uncertain.

### L1 — Terra / medium: default implementation lane

Model preset: `gpt-5.6-terra` / `medium`.

Route to `terra_executor` for normal bounded coding where the design and acceptance criteria are known but ordinary local implementation judgment is still required.

Typical work:
- approved feature implementation;
- localized bug fix with confirmed root cause;
- ordinary refactor with fixed boundaries;
- tests and integration work;
- normal multi-file implementation with clear ownership.

Terra is the preferred default child executor for quality-sensitive engineering.

### L2 — Sol / medium: senior engineering lane

Model preset: `gpt-5.6-sol` / `medium`.

Route to `sol_engineer` when meaningful uncertainty or coupling remains but the problem is still a normal professional engineering problem.

Typical work:
- difficult debugging with a bounded hypothesis space;
- cross-module state/data-flow reasoning;
- lifetime/threading/concurrency analysis that is not yet a frontier case;
- consequential code review;
- non-trivial integration or refactor decisions;
- performance/memory investigation that first needs evidence interpretation.

Before escalating beyond Sol, prefer one strong evidence-driven attempt rather than bouncing models repeatedly.

### L3 — Astra / high: exceptional reasoning lane

Model preset: `gpt-6-astra` / `high`.

Astra is selected by a **reasoning escalation gate**, not by a list of technologies. Security, concurrency, databases, protocols, or large refactors are examples only; none of them automatically require Astra.

Before using Astra, all three preconditions must hold:

1. **Reasoning-bound** — stronger reasoning can materially reduce the remaining uncertainty. The blocker is not merely missing requirements, missing permissions, a broken environment, unavailable credentials/data, or absent test infrastructure.
2. **Consequential or exceptionally difficult** — a wrong decision has meaningful blast radius/rework cost, or the reasoning problem is genuinely novel/deep enough that a lower lane is not a reliable choice.
3. **Not cheaply falsifiable at a lower tier** — deterministic verification alone cannot safely substitute for the missing judgment. If a cheap experiment can resolve the question, run that experiment with a lower-cost lane first.

When those preconditions hold, Astra is appropriate for one or more of these general task shapes:

#### A. Commitment-boundary decisions

A choice will constrain many later decisions and is expensive to reverse. Examples include public contracts, persistent formats, compatibility guarantees, ownership boundaries, platform foundations, service/module decomposition, dependency direction, or other long-lived interfaces. Use Astra when multiple viable choices remain and their consequences require deep tradeoff analysis.

#### B. High-consequence ambiguous decisions

The task affects correctness, security, privacy, authorization, data integrity, production behavior, money/billing, destructive operations, or another important invariant **and** the correct policy/design is still unresolved. High consequence alone is not enough: a frozen, well-tested implementation can remain on Terra/Sol.

#### C. Deep diagnosis with surviving hypotheses

After bounded evidence collection, multiple plausible explanations still fit; observations contradict the current mental model; a failure is intermittent/non-deterministic; or different credible investigations disagree. Astra should reconcile the evidence and identify the cheapest discriminating experiment when proof is still missing.

#### D. Irreversible or costly migration/rollout strategy

Schema/data/platform/protocol/authentication/compatibility migrations, rollout ordering, rollback/recovery strategy, and other changes where a wrong sequence can create durable damage or expensive recovery. Routine execution of an already-approved migration stays lower.

#### E. Novel mechanism or open-ended design

There is little established precedent, the problem spans several domains, or success depends on inventing/choosing an algorithm, protocol, state model, or system mechanism rather than implementing a known pattern. Use Astra for the decision; delegate the resulting bounded implementation.

#### F. Technical arbitration and independent high-consequence review

Two credible analyses/reviews recommend materially different directions, requirements conflict in ways that require judgment, or a high-consequence close needs an independent reasoning pass because deterministic checks cannot cover the important risk. Do not add Astra review to every normal change.

#### G. Proven capability escalation

A well-specified task with a stable environment and sufficient evidence has already received a strong Sol-level attempt, yet the remaining failure is classified as a **reasoning/capability failure**, not a specification, environment, permission, or tooling failure. Escalate with the failed reasoning/evidence, not with the entire transcript.

### Failure triage before any model escalation

Classify a failed attempt before increasing model capability:

- **Specification failure** — acceptance criteria, assumptions, context, or authority are missing/contradictory. Clarify or repair the task packet; a stronger model may only produce a more expensive wrong answer.
- **Environment failure** — dependency, network, permission, branch/state, device, simulator, credential, flaky infrastructure, or tool failure. Fix/report the environment; do not escalate the model for this reason.
- **Verifiability gap** — the important failure mode cannot currently be observed or tested. Add instrumentation/test infrastructure or explicitly surface the unverifiable risk; stronger reasoning is not a substitute for evidence.
- **Implementation failure** — the approach is sound but the worker made a bounded coding mistake. Retry/fix at the same lane within the retry budget.
- **Capability/reasoning failure** — the specification and environment are sound, evidence is sufficient, and the model still cannot resolve the reasoning problem. Escalate one capability step.

Never route to Astra solely because:
- many files are involved;
- the task or context is long;
- a build/test suite is slow;
- implementation is tedious or repetitive;
- one tool/test command failed;
- the repository lacks tests or observability;
- requirements or permissions are missing;
- the user requested a complete end-to-end result.

`max` is never automatic. Use Astra `xhigh`/`max` only on explicit user request or when a deliberate one-off escalation has evidence that `high` is insufficient for an exceptional reasoning decision. Do not permanently raise the lane.

## 3. Mandatory de-escalation

Astra and Sol are decision resources, not default construction crews.

As soon as the unresolved architecture/root cause/invariant is sufficiently settled, emit a compact execution contract and immediately return deterministic implementation to Terra or Luna.

Use this format:

```text
EXECUTION CONTRACT
Goal:
Confirmed facts:
Decisions:
Invariants:
Files/components in scope:
Required changes:
Do not change:
Acceptance criteria:
Verification:
Escalation triggers:
```

Pass conclusions, not the exploration transcript. Include only relevant file paths and minimal evidence excerpts.

## 4. Escalation without thrashing

A lower lane should repair normal mistakes itself.

Do **not** escalate for:
- missing imports/includes;
- obvious type/signature mismatch;
- ordinary test fixture updates;
- formatting/lint;
- a simple implementation bug introduced by the worker;
- one understandable failed attempt.

Escalate one level when:
- evidence invalidates a confirmed assumption;
- implementation requires changing the frozen design;
- an important hidden dependency/invariant appears;
- two substantive attempts fail without a clear implementation-level explanation;
- verification reveals a deeper correctness issue.

Use a compact packet:

```text
ESCALATION PACKET
Goal:
Frozen decision:
Attempted:
Observed evidence:
Expected vs actual:
Exact unresolved question:
Relevant files/log excerpts:
```

After the higher lane resolves the question, update the execution contract and **de-escalate immediately**.

## 5. Verification is the quality gate

Choose the cheapest verification that can actually falsify the implementation.

- Small deterministic edit: focused test/static check/diff inspection.
- Normal feature: focused tests + repository-required checks.
- Cross-module or risky change: broader integration checks appropriate to the changed invariants.
- Performance/memory change: measurement before and after; do not implement speculative optimization without evidence.

Do not repeat already-successful checks unless new changes, failures, or unresolved risks justify it.

Do not automatically send every successful implementation to Astra for final review. Use a higher review lane only when the change remains high-risk or architecture changed materially.

## 6. Token and latency rules

- Keep the main thread concise: store decisions, not investigation narration.
- Prefer exact file paths over broad repository re-reading.
- Prefer targeted log excerpts over entire logs.
- Avoid duplicate agents independently rediscovering the same facts.
- Prefer one agent by default.
- Parallelize I/O-bound safe tool calls before parallelizing reasoning.
- Do not create a routing ledger on the critical path.
- Do not ask a routing model to choose another model.
- Stop exploration when evidence is sufficient to decide.
- Do not let a low-cost model brute-force an unexplained problem; bounded escalation is cheaper than repeated failure.

## 7. User overrides

Honor explicit intent:

- `astra`, `deep`, `highest quality`, `use the strongest model`: allow Astra for the requested phase.
- `cheap`, `save tokens`, `luna`, `executor`: bias downward only while the quality gate remains satisfied.
- `no subagents`: stay in the current agent and use direct tools only.
- `no escalation`: report a blocker instead of escalating.
- `auto route`: apply this policy normally.

A user override may raise capability. A request to lower capability must not silently bypass correctness or safety requirements.

## 8. Minimal visible notices

Do not narrate routing constantly. For substantial work, one short label is enough when routing materially changes execution:

- `[LUNA] deterministic execution`
- `[TERRA] bounded implementation`
- `[SOL] complex engineering reasoning`
- `[ASTRA] exceptional unresolved decision`
- `[DOWNGRADE] decision frozen; returning to executor`
- `[ESCALATE] new evidence requires stronger reasoning`

The project result matters more than router commentary.
