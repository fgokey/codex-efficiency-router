# Quality Gates

## Definition

A lower-cost route is acceptable only when its verification strategy can reasonably detect the failures that matter for the task. A higher-cost route is justified only when stronger reasoning can reduce material uncertainty that evidence alone cannot cheaply resolve.

## Gate levels

### Q0 — Mechanical

Examples: rename, generated config, known call-site migration.

Evidence: compiler/type check, exact search, focused test, or deterministic diff invariant.

### Q1 — Bounded implementation

Examples: approved feature, localized bug fix.

Evidence: focused tests plus repository-required checks relevant to changed code.

### Q2 — Cross-module/risky integration

Examples: cross-module state flow, lifecycle, persistent behavior, protocol integration, or complex refactor with frozen target design.

Evidence: focused tests + integration checks + review of changed invariants. Use Sol when reasoning evidence remains important.

### Q3 — Exceptional reasoning decision

Astra is appropriate when the task passes the reasoning escalation gate and involves a commitment boundary, high-consequence ambiguity, deep unresolved diagnosis/evidence conflict, costly irreversible migration strategy, novel mechanism, technical arbitration, or proven Sol capability failure.

Evidence: Astra resolves/narrows the decision; lower lanes implement; verification targets the exact invariants that justified escalation. Independent high-level review may be appropriate only when deterministic evidence cannot cover the residual high-consequence risk.

## Failure-class gate

Before increasing model capability, classify the failure:

- Spec failure -> repair requirements/context/authority.
- Environment failure -> repair/report environment, permissions, dependencies, state, credentials, or tooling.
- Verifiability gap -> add instrumentation/tests or explicitly surface the gap.
- Implementation failure -> bounded same-lane repair.
- Capability/reasoning failure -> escalate one level with evidence.

A stronger model does not fix a broken harness or missing evidence.

## Evidence-driven optimization

For performance, memory, stability, or architecture optimizations:

1. establish a baseline;
2. identify a measurable mechanism;
3. change only when evidence supports expected benefit;
4. measure after the change;
5. revert or reconsider when benefit is absent or regression risk dominates.

Do not modify production code solely because an optimization sounds plausible.
