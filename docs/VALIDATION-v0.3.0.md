# v0.3.0 validation — 2026-09-07

Baseline: v0.2.1 commit `1d7a93df1a3700d1c20e0100a5889677cb6163c3`, tree `ed032b3554f768398dbb14795e633b5c2cead54f`. The local starting archive and final uploaded payload were compared by Git tree identity.

Code/evaluation commit: `c3c812123d5f1e82177a99574ad3469a08334e43`, tree `b795827698d5735913ac442cf4360286c95a4dc3`.

## Executed checks

The [exact CI run](https://github.com/fgokey/codex-efficiency-router/actions/runs/34139579125) passed all seven jobs: Windows, macOS and Ubuntu with Python 3.11 and 3.13, plus the independent offline audit. The downloaded report's source SHA-256 values matched the local tested files; its working tree was clean.

| Check | Observed result |
| --- | --- |
| Unittest suite | 117 tests, zero failures/errors/skips |
| Existing routing scenarios | 36 within the suite, not additional model trials |
| Retained boundary probes | 8/8 passed |
| Selected routing mutations | 12/12 detected by assertion failures |
| Selected quality-protocol mutations | 12/12 detected by assertion failures |
| Static doctor / compile checks | Passed |
| Local historical v0.2.1 install -> new upgrade -> doctor -> uninstall | Passed in an isolated temporary project |
| Natural-language acceptance corpus | 20 cases prepared and structurally checked; zero live model runs |

The new finite checks cover requirement evidence, claim-only reports, stale checks, plan conflicts, cross-worker retries, unknown history, active workers and uncertain side effects. Existing tests and the original failed evaluation remain intact. Mutant crashes/timeouts are not counted as detections. These checks do not prove arbitrary model behavior.

[Original report and logs artifact](https://github.com/fgokey/codex-efficiency-router/actions/runs/34139579125/artifacts/10025348793), retained for 14 days. ZIP SHA-256:
`d2ece5c394d6d407b2cd47c71bb4ca7e7ef98a934711d772adab77af78b91e1c`.

## Measured instruction text

Pinned `tiktoken==0.11.0`; exact raw-text counts for the named reference encodings only:

| Loaded text | v0.2.1 o200k_base | v0.3.0 o200k_base | v0.2.1 cl100k_base | v0.3.0 cl100k_base |
| --- | ---: | ---: | ---: | ---: |
| Core Skill | 1,155 | 1,139 | 1,168 | 1,152 |
| Core + ALL references | 2,074 | 2,054 | 2,093 | 2,071 |
| Luna developer instructions only | 163 | 173 | 162 | 174 |
| Terra developer instructions only | 162 | 172 | 161 | 173 |
| Sol developer instructions only | 199 | 190 | 198 | 193 |
| Astra developer instructions only | 249 | 204 | 248 | 205 |

Current core + dispatch text: 1,457 / 1,472 tokens under o200k_base / cl100k_base. Core bytes: 6,012. Core plus all three references, with one separator per file: 11,143 bytes. The existing 6,500-core / 12,000-full byte budgets were not raised.

Core and full-load instruction text are slightly smaller despite added quality/recovery rules. Luna and Terra's own instructions increased; these increases are explicit, not hidden. Full-load plus any one corresponding role's instruction text remains below the v0.2.1 total under both encodings, as enforced by the audit. This is a scoped additive text comparison, NOT the cost of spawning an agent, multiple children, or a full conversation. Do not claim that every component decreased or every live workload uses fewer tokens.

All four model-to-tokenizer lookups remain UNKNOWN in the pinned library. Counts exclude host framing, inherited history, tool schemas/results, task input, model reasoning/output and retries. No exact Astra billing, subscription-quota conversion, task speedup or quality non-inferiority is claimed.

## Release boundary

The implementation is a Codex-only Skill plus four native role presets; there is no imported agent runtime or new routing-model call. Python quality helpers are offline development aids, not live enforcement. The paired comparator now refuses a successful CLI exit for incomplete Router acceptance even when both variants fail.

Actual role/model/effort identity, compliance with handoff/recovery rules, final task quality, full usage and speed remain [user-run acceptance](ACCEPTANCE.md). No Codex or model API is invoked by installation or these CI jobs. The 20 realistic prompts are prepared, not live-scored.

This record applies to the exact code commit above. A documentation-only publication commit should still be checked against its own workflow result rather than inheriting success by assertion.

[Protocol and primary-source design mapping](QUALITY-PROTOCOL.md) · [Offline audit](../evaluation/README.md) · [Acceptance](ACCEPTANCE.md)
