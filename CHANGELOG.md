# Changelog

All notable changes to this project are documented here.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Changed
- Replaced technology-keyword Astra triggers with a general reasoning-escalation gate based on reducible uncertainty, failure cost/reversibility, coupling, verifiability, novelty, evidence conflict, and qualified prior failure.
- Added failure triage before model escalation: specification, environment, verifiability, implementation, and capability failures now have distinct responses.
- Added explicit Astra task shapes for commitment boundaries, consequential ambiguity, deep evidence arbitration, costly migration/rollout strategy, novel mechanisms, technical arbitration, and proven Sol capability failure.
- Added regression cases proving that frozen high-risk implementation, missing requirements, environment failures, and observability gaps do not automatically route to Astra.
- Added `docs/ASTRA-ESCALATION.md` and expanded prior-art documentation.

## [0.1.0] - 2026-09-07

### Added
- Initial `codex-efficiency-router` Skill.
- GPT-6 Astra escalation lane using `gpt-6-astra`.
- GPT-5.6 Sol, Terra, and Luna execution presets.
- Quality-first routing policy with mandatory de-escalation after decisions freeze.
- Token/latency guardrails: one-agent default, direct tool concurrency, bounded subagents, compact handoffs.
- User- and repository-scoped cross-platform installers.
- Doctor, uninstall, routing regression cases, CI, security, contributing, and bilingual documentation.
