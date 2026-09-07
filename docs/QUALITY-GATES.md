# Quality gates

## Before routing

Clarify the required behavior, repository constraints, material edge cases, available evidence, write scope and authorization. A vague specification cannot be repaired merely by buying a more capable model. Do not downgrade solely because coding begins; coding can expose unresolved design.

## During execution

Keep accepted decisions unless new evidence or user intent invalidates them. Respect disjoint write ownership and the active workspace state. Preserve the failure evidence. One targeted same-lane correction is allowed for ordinary implementation mistakes; repeated unexplained failure stops patching for diagnosis. Classify specification, environment, observation and capability failures separately.

## Verification

Use observable acceptance checks capable of failing on the defect; a regression test should reproduce the original issue when feasible. Run repository-required checks and risk-proportionate integration, compatibility or adversarial checks. Generated tests and their implementation can share a mistake; neither self-review nor passing narrow new tests is independent proof.

Do not weaken assertions, delete relevant tests, rewrite acceptance, or hide skipped checks for green status. Obsolete tests may be changed only when changed requirements and the user's scope justify it, with remaining coverage explained. A check is PASS only when observed on the relevant final state; unrun or inaccessible checks are UNKNOWN.

Stop once required checks pass and residual risks are resolved or disclosed. Additional validation needs relevant changes, failures or unresolved concerns, not a ritual request for maximum confidence. Fresh independent review is reserved for material judgment risk; it is not an Astra tax on every patch.

## Fail safely

If the actual host cannot supply sufficient capability, report the limitation and avoid risky writes. No-subagent/no-escalation constraints do not certify the current model. Read-only advice does not grant execution permission. Backups do not justify unsafe edits. Measurements are required before performance claims.

## What the repository tests prove

Unit/property/scenario tests check the offline policy and lifecycle implementation. They cannot establish actual Skill trigger accuracy, live model routing, reasoning quality, or equivalence on arbitrary repositories. [Paired model evaluations](BENCHMARKING.md) are a separate acceptance layer.
