# GPT-6 Astra Escalation Design

## Purpose

This document defines when the router should spend its highest-capability reasoning budget.

The central question is not “does this task sound hard?” It is:

> **Will stronger reasoning materially reduce a consequential uncertainty that cannot be settled more cheaply by evidence or a lower-capability lane?**

This avoids two common routing mistakes:

1. keyword escalation — treating security, concurrency, migrations, or architecture as automatic strongest-model work;
2. failure escalation — treating every failed command or test as evidence that the current model is too weak.

## Three preconditions

Astra is an automatic candidate only when all three hold.

### P1 — Reasoning-bound

The remaining blocker is reducible by reasoning using available evidence.

Do not use Astra to compensate for:
- missing/contradictory requirements;
- missing authority or user approval;
- broken dependencies/environment/network/device state;
- missing credentials or inaccessible data;
- absent observability/test infrastructure.

### P2 — Consequential or exceptionally difficult

At least one is true:
- a wrong decision has broad or durable blast radius;
- the decision is costly to reverse;
- errors compound into substantial downstream rework;
- the problem is genuinely novel/deep with little established precedent;
- a qualified lower-tier reasoning attempt has already failed.

### P3 — Evidence alone is insufficient

If a cheap, bounded experiment can decide between hypotheses or verify the choice, run it first with a lower-cost lane. Use Astra after the experiment only if material judgment remains.

## General Astra task shapes

### Commitment boundaries

Choices that constrain future work: public/external interfaces, persistent formats, compatibility guarantees, ownership boundaries, platform foundations, decomposition, dependency direction, and other long-lived contracts.

### Consequential ambiguity

Important policy/design decisions affecting correctness, security, privacy, authorization, data integrity, production behavior, destructive actions, billing/financial behavior, or comparable invariants.

The key word is **ambiguity**. A frozen policy with strong tests is an implementation problem, not automatically an Astra problem.

### Deep diagnosis and evidence arbitration

Several hypotheses survive bounded investigation; evidence conflicts with the current model; behavior is nondeterministic; hidden interactions remain; or credible independent analyses disagree.

### Costly migration / rollout / recovery strategy

Sequencing, compatibility, rollback, partial failure, recovery, and irreversibility dominate the decision. Once the strategy is frozen, execution routes down.

### Novel mechanism / open-ended design

The task requires inventing or selecting a new algorithm, protocol, state model, system mechanism, or cross-domain design with weak precedent.

### Technical arbitration / independent high-consequence review

Use a fresh reasoning pass when credible alternatives conflict or deterministic checks leave a critical residual risk. This is an exception, not a mandatory final-review ritual.

### Proven capability failure

Astra is justified when a correctly specified, observable task in a functioning environment has already received a serious Sol-level reasoning attempt and the remaining blocker is genuinely capability/reasoning, not implementation or harness failure.

## Failure taxonomy

| Failure class | Meaning | Correct action |
|---|---|---|
| Specification | Missing/conflicting acceptance, context, assumption, authority | Repair task packet; no capability escalation |
| Environment | Dependency, permission, network, branch/state, device, credential, tool failure | Repair/report environment |
| Verifiability | Important behavior cannot be observed/tested | Add evidence path or surface limitation |
| Implementation | Sound plan, bounded worker mistake | Same-lane repair within retry budget |
| Capability | Sound spec/environment/evidence, reasoning still insufficient | Escalate one capability step |

## De-escalation

Astra ends when the decision is frozen, not when the project ends.

The output should be a compact contract containing:
- decision;
- rationale;
- invariants;
- scope/non-goals;
- acceptance criteria;
- verification;
- rollback/recovery considerations when relevant;
- explicit evidence that would reopen the decision.

Then route implementation to the cheapest sufficient lane.

## Why this is better than technology lists

Technology names are weak proxies. A routine security patch with a frozen design can be easier than a novel low-risk algorithmic decision. A 100-file mechanical migration can be cheaper than a one-line public-contract change whose semantics are irreversible.

The router therefore evaluates task shape and uncertainty instead of domain keywords.
