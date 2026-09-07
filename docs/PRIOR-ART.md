# Prior Art and Design Context

This project is an original implementation built around current OpenAI Codex Skills/custom-agent capabilities and public work on quality/cost routing.

## Sources studied

- OpenAI Codex custom agents / Skills documentation — native per-agent model and reasoning configuration.
- `orange-the-weak/codex-auto-model-router` — fail-open benefit gating, no unnecessary child agents, direct tool concurrency, one-dimension-at-a-time escalation, and the rule that environment failures are not capability failures.
- `capitalparser/codex-model-router` — routing by verifiability, failure cost, volume, depth, decomposability, observed outcomes, and evidence-gated escalation rather than phase names.
- `giannhs2454/code-complexity-router` — inspection-based escalation when repository evidence disproves initial scope; de-escalation when work becomes local/mechanical.
- `2manslkh/codex-orchestrator` / related Sol-Terra-Luna orchestration work — blast-radius routing, independent verification for consequential closes, and migration/security/arbitration as judgment-heavy categories.
- `vimoxshah/claude-router` and `nobodyohm-web/claude-code-model-router` — premium reasoning at commitment boundaries, persistent bounded workers, evidence-based escalation, and strongest-model participation in substantial ambiguous planning rather than all implementation.
- `midego1/claude-orchestrate` — explicit failure taxonomy: specification, environment, capability, and verifiability gaps; a stronger model should not be used to compensate for a bad task packet or broken harness.
- LMSYS `RouteLLM` — quality/cost routing as a calibrated tradeoff rather than a prestige ranking; empirical routing should be evaluated against a strong-model quality baseline.
- 2026 cascaded routing research — route cheaply first where appropriate, then escalate based on observed/estimated quality rather than sending every request to the oracle.

## Design conclusions adopted here

1. **Marginal reasoning value beats keyword routing.** Domain labels are examples, not triggers.
2. **Reducible uncertainty is the scarce-resource target.** Missing requirements, permissions, environment, or observability are prerequisite failures, not reasons for Astra.
3. **Failure cost and reversibility matter.** Commitment boundaries and costly-to-reverse decisions justify more reasoning than equivalent-volume local edits.
4. **Verifiability pushes execution downward.** Strong deterministic checks let cheaper lanes safely handle more volume.
5. **Failure must be classified before escalation.** Capability escalation is only one failure class.
6. **Escalate with evidence; de-escalate with certainty.** Once the decision is frozen, expensive reasoning stops.
7. **Independent review is selective.** Use it for high-consequence residual judgment, not every successful patch.
8. **No routing model on the critical path.** The live Skill remains a thin policy layer; deterministic code exists only for regression testing.

## Deliberate differences

`codex-efficiency-router` deliberately differs from several prior projects:

1. GPT-6 Astra is an explicit exceptional reasoning lane above Sol/Terra/Luna.
2. Quality is a hard constraint rather than merely another weighted score.
3. Terra is the default quality-sensitive executor; Luna is reserved for strongly deterministic work.
4. Astra requires a three-part reasoning escalation gate and is not triggered by technology names alone.
5. De-escalation after the decision freezes is mandatory.
6. The default installer does not edit `config.toml`.
7. Runtime routing requires no additional classifier model or daemon.
8. Synthetic policy code is used only for regression tests, not for live routing.

No third-party source code is required at runtime.
