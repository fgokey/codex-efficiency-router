# v0.4.0 validation — 2026-09-08

Source baseline: v0.3.0 commit `53cee91604e9af71e7bd565173eef68961f3efc4`, tree `3fc54c77035d7c8f1b70dd07d006da20031af52b`. The local starting archive was checked against this tree, not inferred from its filename.

This release adds joint model/effort selection and explicit fixed/adaptive installation. Existing acceptance, ownership, permission and task-wide retry rules remain. Exactly four canonical roles generate exactly four installed roles in either mode. Fixed remains the new-install default; updates preserve the chosen mode and low opt-in.

Validation commands:

```sh
python -m unittest discover -s tests -v
python scripts/doctor.py --source-tree .
python -m compileall -q scripts tests evaluation
python evaluation/offline_audit.py --without-tokenizer
git diff --check
```

The full offline CI also uses pinned `tiktoken==0.11.0` for named reference-encoding counts. The report includes ordinary tests, retained routing/quality mutation checks, new effort mutations, source hashes and measurement limits. Refer to the exact commit's workflow, not historical successful runs.

No Codex executable or authenticated model runtime is invoked by these tests. Actual native effort-parameter support, model/effort identity, same-thread continuation, quality non-inferiority and task token/latency changes remain user-run acceptance. The Python helpers consume declared metadata, not live telemetry. Text token counts exclude host framing, task history, generated reasoning/output, tools and retries; they are not exact Astra billing or quota conversion.

[Design](ADAPTIVE-EFFORT.md) · [Acceptance](ACCEPTANCE.md) · [Offline audit](../evaluation/README.md)
