# v0.4.0 validation — 2026-09-08

Source baseline: v0.3.0 commit `53cee91604e9af71e7bd565173eef68961f3efc4`, tree `3fc54c77035d7c8f1b70dd07d006da20031af52b`. The starting archive was checked against this Git tree, not inferred from its filename.

Verified code/evaluation commit: `8c04a00a2c7fe2dcdc338bb54b31a3abf89721ff`, tree `fe47a0625d6916db547d39d429ac32380bf2a483`. The uploaded tree equals the locally tested tree. The [exact CI run](https://github.com/fgokey/codex-efficiency-router/actions/runs/34210974083) completed all seven jobs successfully: Windows, macOS and Ubuntu with Python 3.11 and 3.13, plus the independent offline audit.

## Delivered behavior

The parent policy jointly selects model and effort at meaningful safe boundaries. Fixed/adaptive installation is explicit: four canonical fixed roles generate exactly four roles in either mode. Adaptive removes only top-level effort pins; model, instructions and permissions stay intact. Fixed is the new-install default, and updates preserve the selected mode and low opt-in. No implicit profile migration or global Codex configuration edit is performed.

Ordinary work defaults to medium, deeper reasoning may use high, and automatic Astra stays high. Automatic low is separately opted in and restricted to strongly verified mechanical Luna tasks. Explicit preferences still respect prerequisites, quality floors and user limits. No-escalation covers both axes. Unknown/mismatched runtime identity suspends automatic low for the rest of the task, even after later verified observations. Changes never renew task-wide repair budgets or hot-switch active writers.

These are Skill instructions with offline reference helpers, not a universal live enforcement layer. Actual supported tool fields, role loading and runtime identity remain host dependent.

## Executed checks

| Check | Observed result |
| --- | --- |
| Unittest suite in the downloaded audit report | 180 tests; zero failures, errors or skips |
| Existing routing scenarios | 36 within that suite, not additional model trials |
| Retained independent boundary probes | 8/8 passed |
| Selected routing mutations | 12/12 detected by assertion failures |
| Selected quality-protocol mutations | 12/12 detected by assertion failures |
| New selected effort mutations | 18/18 detected by assertion failures |
| Source doctor and compilation | Passed in all six platform/Python jobs |
| Real v0.3.0 install -> v0.4.0 upgrade -> doctor -> uninstall | Passed locally for fixed and adaptive in temporary projects; unrelated configuration preserved |
| Prepared behavioral/effort acceptance prompts | 20 existing + 10 new, structurally checked; zero live model runs |

The suite covers explicit generation, mode/low persistence, dry-run, custom-file conflicts, rollback, uninstall/restore, native parameter admission, fixed/adaptive pin precedence, supported pairs, dual-axis opt-outs, safe boundaries, identical-pair recovery, budget preservation and sticky observation state. Mutant errors/timeouts are not counted as detections. Finite tests do not establish arbitrary model compliance or comprehensive mutation coverage.

The downloaded report has a clean working tree and its source SHA-256 values match every corresponding local source file. The [original report and logs](https://github.com/fgokey/codex-efficiency-router/actions/runs/34210974083/artifacts/10049773778) are retained for 14 days. Artifact ZIP SHA-256:

`534ec96d9b5c846d8307ce56d93c1698197c3f8621f5f958838258fdc7cd4691`.

## Preserved first-run failures and corrections

The [first feature run](https://github.com/fgokey/codex-efficiency-router/actions/runs/34210415386) at `3b34c5ac62e5fe8b960daf1037a8e135eb2e5543` did not fully pass. Its Windows/Ubuntu tests passed; macOS found that one new user-home test fixture used the `/var` temporary-directory alias. The fixture now resolves its temporary path before setting `CODEX_HOME`; production symlink rejection was not weakened. The first offline audit also exceeded its existing text budget. Repeated core wording was trimmed without raising byte/token thresholds or deleting required acceptance rules. The failures and commits remain in history; no failed report was rewritten as success.

## Measured instruction text

Pinned `tiktoken==0.11.0`, exact raw-text counts under the two named reference encodings:

| Loaded text | o200k_base | cl100k_base |
| --- | ---: | ---: |
| v0.4 fixed core | 1,141 | 1,147 |
| v0.4 adaptive core (automatic low off) | 1,141 | 1,147 |
| v0.4 fixed core + dispatch | 1,301 | 1,307 |
| v0.4 fixed core + ALL four references | 2,035 | 2,045 |
| v0.4 adaptive core + ALL references (automatic low off) | 2,035 | 2,045 |
| Luna developer instructions only | 191 | 193 |
| Terra developer instructions only | 190 | 192 |
| Sol developer instructions only | 208 | 212 |
| Astra developer instructions only | 217 | 219 |

Fixed core is 5,885 UTF-8 bytes; fixed core plus all references with one separator per file is 10,713 bytes. Adaptive low-off text adds three bytes to the marker. Existing 6,500-core / 12,000-full byte budgets are unchanged. The full-load budget and full-load-plus-each-role budget pass under both encodings against the immutable v0.2.1 baseline used by CI. Role instruction text is identical between fixed/adaptive because only the TOML effort setting is removed.

For context, the [published v0.3.0 measurements](VALIDATION-v0.3.0.md) reported 1,139 / 1,152 core and 2,054 / 2,071 full-load tokens under o200k_base / cl100k_base. The new o200k core is two tokens larger, while the full-load text is nineteen smaller. Individual role instructions grew to preserve identity and effort boundaries; not every component decreased. This is a bounded instruction-footprint comparison, not a universal savings claim.

All four model-to-tokenizer lookups remain UNKNOWN in the pinned package. Counts exclude host framing, inherited task history, tool schemas/results, model reasoning/output, verification and retries. They are not exact Astra billing, subscription quota, task latency or model-quality measurements. Automatic-low-on marker variants were not separately token-counted in this report; both low settings are covered by generation/lifecycle tests.

## Reproduce and complete user acceptance

```sh
python -m unittest discover -s tests -v
python scripts/doctor.py --source-tree .
python -m compileall -q scripts tests evaluation
python evaluation/offline_audit.py --without-tokenizer
git diff --check
```

For text measurement, use a full Git clone, install `tiktoken==0.11.0`, and run `python evaluation/offline_audit.py`. Initial dependency/vocabulary downloads use the network, not model inference. The script does not log in to Codex or start model tasks.

Actual native effort support, loaded role configuration, model/effort identity, optional same-thread continuation, final coding quality, whole-task tokens and elapsed time remain **user-run acceptance**. Installing adaptive mode is not proof of dynamic execution. The parent must use actual native fields; no new App Server client or hidden fallback is bundled. A later documentation-only publication commit must still be checked against its own workflow result.

[Design](ADAPTIVE-EFFORT.md) · [Acceptance](ACCEPTANCE.md) · [Offline audit](../evaluation/README.md)
