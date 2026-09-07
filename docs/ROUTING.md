# Routing Guide

## Core rule

Route by the **marginal value of stronger reasoning**, not by task length, file count, or scary keywords.

A stronger model is justified when it can materially reduce **reducible uncertainty** whose wrong resolution has meaningful cost. If the blocker is missing information, permissions, environment, or observability, fix that first.

## Fast decision tree

```text
Can current agent + direct tools finish reliably?
  yes -> stay local
  no / different lane clearly pays
       |
       +-- Are decisions frozen, work mechanical, low-risk, strongly verifiable?
       |      yes -> Luna / medium
       |
       +-- Is this bounded implementation with known design and acceptance?
       |      yes -> Terra / medium
       |
       +-- Does normal professional engineering uncertainty/coupling remain?
       |      yes -> Sol / medium
       |
       +-- Before Astra: is the blocker actually spec/env/permission/observability?
       |      yes -> resolve the blocker; DO NOT escalate for capability
       |
       +-- Can a cheap discriminating experiment resolve the uncertainty?
       |      yes -> lower lane collects evidence, then re-route
       |
       +-- Is this a commitment boundary, high-consequence ambiguous decision,
       |   deep unresolved diagnosis, costly irreversible migration, novel mechanism,
       |   technical arbitration, or proven Sol capability failure?
              yes -> Astra / high
```

## Routing axes

Evaluate these axes together:

| Axis | Question | Effect |
|---|---|---|
| Reducible uncertainty | Can better reasoning materially resolve what is unknown? | Main reason to move upward |
| Failure cost / blast radius | What happens if the decision is wrong? How reversible is it? | Raises required judgment |
| Coupling / horizon | How many subsystems, contracts, states, or later decisions interact? | Raises reasoning depth |
| Verifiability | Can deterministic evidence cheaply falsify a wrong result? | Strong verification lets execution move downward |
| Novelty / precedent | Is there a known pattern, or must a new mechanism/tradeoff be invented? | Novel work may justify Astra |
| Evidence conflict | Do credible observations/analyses disagree? | Raises need for arbitration |
| Prior qualified failure | Did a well-specified, evidence-rich Sol attempt fail for capability reasons? | Strong escalation evidence |
| Volume | Is there lots of repetitive work? | By itself pushes work down, not up |

## Astra reasoning escalation gate

Astra requires all of:

1. **Reasoning can help now.** There is enough evidence/context to make progress through judgment.
2. **The decision is consequential or exceptionally difficult.** Wrong reasoning compounds, is costly to reverse, or the problem is unusually novel/deep.
3. **Lower-cost falsification is insufficient.** A focused test/experiment cannot cheaply settle the important question first.

Then one of the following task shapes should be present.

### 1. Commitment-boundary decisions

Long-lived choices that constrain future work: external/public contracts, compatibility guarantees, persistent data formats, ownership/module/service boundaries, platform foundations, dependency direction, or similar architectural commitments.

Use Astra only while alternatives and consequential tradeoffs remain open. Once frozen, implementation drops to Terra/Luna or Sol if integration remains complex.

### 2. High-consequence ambiguous decisions

Security, privacy, authorization, data integrity, production behavior, destructive operations, financial/billing behavior, or other important invariants where the **policy/design itself** is unresolved.

A high-risk but fully specified change with strong acceptance tests is not automatically an Astra task.

### 3. Deep diagnosis and evidence reconciliation

Use Astra when bounded investigation has produced multiple surviving hypotheses, contradictory evidence, non-deterministic behavior, hidden long-range interactions, or disagreement between credible analyses.

Astra should seek a discriminating explanation/experiment, not brute-force more logs.

### 4. Irreversible/costly migration and rollout strategy

Use for migration sequencing, backward/forward compatibility, rollback/recovery design, partial-failure behavior, and other decisions where an incorrect plan is difficult to undo.

Execution of a frozen migration plan remains a lower-lane task.

### 5. Novel mechanism or open-ended design

Use when there is no obvious established pattern and the core work is inventing or selecting an algorithm, protocol, state model, system mechanism, or cross-domain architecture.

Do not use Astra merely because implementation is large.

### 6. Arbitration / independent high-consequence review

Use when two credible technical conclusions conflict, requirements force a difficult tradeoff, or deterministic verification cannot cover a critical residual risk and an independent reasoning pass can materially improve confidence.

Independent review should be fresh-context when practical and should receive requirements, decision ledger/diff, and evidence rather than the implementer's full narrative.

### 7. Proven capability failure

Escalate after Sol only when:

- the task is correctly specified;
- the environment/permissions/tools are working;
- evidence is sufficient for reasoning;
- the failure is not just an implementation mistake;
- a scoped Sol attempt still cannot resolve the problem.

Pass the failed reasoning/evidence and exact unresolved question. Do not blindly rerun the whole task.

## Failure triage before escalation

```text
FAILED ATTEMPT
   |
   +-- Missing/contradictory spec or authority? -> repair spec, same/no model escalation
   |
   +-- Environment/tool/permission/credential/flaky state? -> fix/report environment
   |
   +-- Cannot observe/test the important behavior? -> add observability/verification
   |
   +-- Ordinary bounded implementation mistake? -> same-lane repair (bounded)
   |
   +-- Genuine reasoning/capability failure? -> escalate one step
```

This prevents a stronger model from masking a weak task packet or broken harness.

## De-escalation

Move down as soon as discovery makes the remaining work local, deterministic, or covered by focused checks.

```text
Astra resolves decision
      -> Execution Contract
      -> Sol only if integration reasoning remains complex
      -> otherwise Terra
      -> Luna for mechanical sub-units
```

Astra is not the final reviewer by default. Use it again only if new evidence reopens an Astra-class question.

## Examples

| Work | Default lane | Why |
|---|---|---|
| Rename a symbol across 80 call sites | Luna | Mechanical, compiler/search-verifiable |
| Implement an approved endpoint + tests | Terra | Bounded coding with known acceptance |
| Cross-module refactor with known target architecture | Sol/Terra | Integration reasoning remains; architecture is frozen |
| Choose a public API/versioning contract with several viable long-term options | Astra | Commitment boundary + consequential tradeoff |
| Routine implementation of an already-approved auth policy | Terra/Sol | Security keyword alone does not imply Astra |
| Design a new authorization model with conflicting trust requirements | Astra | High-consequence policy remains ambiguous |
| Production schema migration with frozen steps and proven rollback | Terra/Sol | Execution is bounded and verifiable |
| Decide migration/rollback strategy with compatibility and partial-failure uncertainty | Astra | Costly-to-reverse strategy decision |
| Test fails because dependency is missing | local/same lane | Environment failure, not capability failure |
| No test can detect the critical regression | add verification first | Verifiability gap; stronger model is not evidence |
| Two credible investigations explain an intermittent failure differently | Astra | Evidence arbitration / surviving hypotheses |
| Sol fails because requirements contradict each other | resolve requirements | Specification failure, not model weakness |
| Sol has sound task packet/evidence but cannot resolve a novel coupled mechanism | Astra | Proven capability escalation |

## Astra effort policy

`gpt-6-astra` / `high` is the automatic exceptional lane.

- `xhigh`: deliberate escalation when `high` has demonstrably insufficient depth on the same narrowed reasoning question.
- `max`: explicit user request or exceptional manual choice only; never automatic.
- Do not keep the elevated effort after the unresolved decision is closed.
