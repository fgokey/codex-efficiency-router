# v0.2.0 published validation

Verified on 2026-09-07 against commit `c2e33b9e410efef8649bcb28c7997d8905de30e4`.

The [validate run](https://github.com/fgokey/codex-efficiency-router/actions/runs/34111792301) completed successfully. Its job results confirm all six combinations:

| Operating system | Python 3.11 | Python 3.13 |
| --- | --- | --- |
| Ubuntu | PASS | PASS |
| Windows | PASS | PASS |
| macOS | PASS | PASS |

The inspected Ubuntu/Python 3.11 job log reports `Ran 60 tests` and `OK`, including the routing scenario test, dispatch admission, lifecycle safety, catalog validation, comparison semantics, CLI smoke, and documentation targets. The scenario fixture contains 36 cases; these cases are part of the unittest suite, not 36 additional live-model experiments.

All six jobs passed compilation, regression/lifecycle tests, and static source validation. The static doctor explicitly reports:

```text
doctor: STATIC PASS
live Codex discovery/model execution: NOT VERIFIED
catalog: NOT CHECKED
```

This distinction is intentional. These jobs do not authenticate to Codex, call a model, measure actual task token use, or prove model-quality non-inferiority. Actual role discovery and execution require a smoke test on the intended Codex host, followed by controlled paired tasks before publishing savings claims. See [benchmarking](BENCHMARKING.md) and [compatibility](COMPATIBILITY.md).

Both [English](../README.md) and [Chinese](../README.zh-CN.md) READMEs include installation, scope selection, update, explicit v0.1 adoption, uninstallation, dry-run and restore instructions.

The final publication cleanup removes the temporary `.bootstrap` archive and write-enabled `apply-audited-release` workflow. Normal validation remains read-only. No runtime policy or model preset is changed by that cleanup. Historical commits are retained; there is no history rewrite. For any subsequent commit, inspect its own Actions result rather than transferring this result blindly.

[Audit findings](AUDIT-2026-09-07.md) · [Official and industry references](PRIOR-ART.md)
