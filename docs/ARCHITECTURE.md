# Architecture

## Objective

`codex-efficiency-router` optimizes three outcomes together:

1. verified correctness must not intentionally decrease;
2. expensive-model and duplicated-context token use should decrease;
3. wall-clock time should decrease when safe concurrency or a faster sufficient model can help.

The router is intentionally a **thin policy Skill**, not a daemon and not another LLM call.

## Why there is no router model

A separate model invocation to classify every request adds context ingestion, reasoning tokens, startup latency, and another failure mode before useful work starts. The Skill therefore asks the current coordinator to make one bounded routing decision from evidence already in context.

The reference classifier in `scripts/policy_reference.py` exists only for regression tests and documentation. Codex does not need to invoke it in normal work.

## Capability ladder

```text
L0  GPT-5.6 Luna / medium
    deterministic, repetitive, narrow, strongly verifiable

L1  GPT-5.6 Terra / medium
    default bounded coding executor

L2  GPT-5.6 Sol / medium
    complex engineering, difficult debugging, cross-module reasoning

L3  GPT-6 Astra / high
    exceptional reasoning: commitment boundaries, consequential ambiguity, evidence arbitration, novel design, costly migration strategy, or proven Sol capability failure
```

The ladder is not a prestige ranking. Each lane has a different economic role.

## Root model is not replaced

The installer does not change the user's top-level Codex model. The user's selected root remains the coordinator. The Skill may create a bounded child agent only when a different model has clear net benefit.

This avoids forcing every turn of a long conversation through Astra merely because one decision required Astra.

## Decision freeze and de-escalation

The central state transition is:

```text
EXPLORE -> DECIDE -> EXECUTE -> VERIFY
   |          |          |          |
 Sol/Astra  Sol/Astra  Terra/Luna  cheapest sufficient check
```

Once the consequential decision, invariants, scope, and acceptance criteria are sufficiently known, the expensive lane produces an `EXECUTION CONTRACT` and stops. Deterministic implementation goes back down the ladder.

This transition is mandatory because keeping a frontier model active after the decision is frozen wastes tokens without adding proportional quality.

## Parallelism policy

Parallelism order:

1. independent safe tool calls in the current agent;
2. one child agent when a model change has material net benefit;
3. multiple child agents only for independent workstreams with exclusive ownership or read-only evidence gathering.

Do not use a swarm as the default. Parallel agents often reduce elapsed time but increase total tokens due to duplicated context and aggregation.

## Context contracts

### Execution Contract

Transfers only stable decisions to a cheaper executor:

- goal;
- confirmed facts;
- decisions/invariants;
- in-scope files/components;
- required changes;
- non-goals;
- acceptance criteria;
- verification;
- escalation triggers.

### Escalation Packet

Transfers only unresolved evidence upward:

- goal and frozen decision;
- attempts;
- observed evidence;
- expected vs actual;
- exact unresolved question;
- minimal relevant files/log excerpts.

Full transcripts are explicitly discouraged.

## Installation architecture

The default installer copies files only:

- Skill: user `$HOME/.agents/skills/codex-efficiency-router` or repo `$REPO_ROOT/.agents/skills/codex-efficiency-router`;
- Agents: user `$CODEX_HOME/agents` (default `~/.codex/agents`) or repo `$REPO_ROOT/.codex/agents`.

It does not modify `config.toml`. An optional fragment is provided for users who explicitly want Terra/medium as the default unnamed subagent model.
