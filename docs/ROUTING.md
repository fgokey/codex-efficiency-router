# Routing and dispatch

The installed [routing reference](../skills/codex-efficiency-router/references/routing.md) is the detailed policy. Do not copy all of it into every task's prompt.

## Admission order

Resolve requirements, authority, environment and evidence gaps first. Use a safe cheap discriminating check when it can settle the uncertainty. Select sufficient capability rather than a technology-specific keyword. Then decide whether the supported execution route is worth using.

Direct local completion is preferred only when the current agent is sufficient. Capability-critical delegation need not promise cost savings. Cost-only delegation needs a benefit after startup, context, handoff, verification and likely rework. If routing is unavailable, stay local when sufficient; otherwise report the blocker, without lowering acceptance or silently pretending the requested model ran.

## Model and phase are independent

| Situation | Likely lane, subject to evidence |
| --- | --- |
| Bulk call-site changes, known pattern, strong checks | Luna |
| Implement a bounded accepted design | Terra |
| Significant uncertain integration or coupled behavior | Sol |
| Consequential unresolved contract or novel mechanism | Astra after its gates |
| Complex-looking question settled by a safe check | Run the check first |
| Missing permission, dependency, requirement or telemetry | Repair the prerequisite |
| Frozen security/migration implementation with strong evidence | Not automatically Astra |
| Many failed network calls | Not a capability escalation |

Astra is not a mandatory final reviewer. A higher-risk topic is not by itself an unresolved high-risk decision. Likewise, do not require a weak-model failure before sending an obviously difficult decision to appropriate capability.

## Failure transitions

A targeted implementation fix stays in its lane. Repeated unexplained failure stops patching and calls for classification, not an automatic Astra call. Escalation requires a new unresolved question or qualified capability failure with adequate specification, authority, environment and observations. New evidence can reopen a frozen decision.

## Overrides

Explicit Astra requests override cost preference, not permissions or missing prerequisites. No-subagent and no-escalation constraints retain the quality floor. Disable requests stop the router for that task. Configuration changes remain explicit user operations, not hidden runtime fallbacks.

The Python reference is an offline approximation for boundary tests, not the Skill's runtime execution engine. Its `local` prerequisite result does not authorize blind implementation. See [dispatch contract](../skills/codex-efficiency-router/references/dispatch.md), [quality gates](QUALITY-GATES.md), and [benchmarking](BENCHMARKING.md).
