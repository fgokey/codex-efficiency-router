# Compatibility — v0.5

Source review: 2026-09-08. [Design and primary sources](ADAPTIVE-EFFORT.md).

Four canonical fixed roles remain under `agents/`. Default auto generates four unpinned `cer_auto_` aliases as well. User bindings live under `$CODEX_HOME/agents`, project bindings under `.codex/agents`; Skills use `~/.agents/skills` or project `.agents/skills`. No runtime config rewrite or foreign framework. Legacy fixed/adaptive overrides remain supported but are unnecessary for ordinary use.

File pins override contradictory spawn values. Auto requires a verified unpinned alias when explicit native effort exists; the generated description marks that binding in native discovery. Otherwise it uses the exact matching fixed pair and records why the alias or field was unavailable. Absence of an effort pin alone is not adaptive behavior: explicitly pass supported model/effort through the real schema. Do not infer support from version strings, model self-description or successful installation.

If no sufficient binding exists, use a sufficient current parent or disclose BLOCKED. No silent downgrade, hidden CLI, paid capability probes or retry loops. Parent live permissions still govern execution; architect instructions and both architect bindings retain read-only intent and defaults, not a new OS security guarantee.

Checks remain separate:

1. Source doctor validates fixed source, packaged references and budgets.
2. Installed doctor validates profile/marker, all required fixed/unpinned bindings and manifest hashes.
3. Optional complete saved model/list export checks availability at export time. Auto checks the baseline fixed pairs; dynamic high/low availability is assessed per selected route, not forced for unused roles. Adaptive-only override retains its stricter profile range check.
4. User-run task verifies actual binding, model/effort, permission behavior, quality and usage. Missing telemetry is UNKNOWN, not success.

Ordinary upgrades from pre-v0.5 manifests migrate with an explicit console notice and backup, rather than inferring intent the old manifest never stored. Later explicit overrides are preserved. Custom file conflicts always stop automatic replacement. Restore never migrates a legacy selection. [Install](INSTALL.md) · [Acceptance](ACCEPTANCE.md).
