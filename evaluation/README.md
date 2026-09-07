# Offline release audit

`offline_audit.py` runs existing regression tests, the eight retained boundary probes and twelve deliberate policy mutations in subprocess-local module objects. It does not modify production files, authenticate to Codex or call model APIs. Mutants must fail assertions; crashes/timeouts are not counted as detections. New opt-out tests enable available routes so missing-host fallbacks cannot mask a broken guard.

```sh
python evaluation/offline_audit.py --without-tokenizer
```

This mode leaves text-token metrics NOT RUN. For the independent text-budget job:

```sh
python -m pip install tiktoken==0.11.0
python evaluation/offline_audit.py
```

A full Git clone is needed for the fixed v0.1 and v0.2 source baselines. First-time tokenizer vocabulary downloads and package installation need network access; no model inference is involved. Results and logs are stored in `evaluation-results/`, excluded from Git. A missing tokenizer, baseline or encoding is an error, never a fabricated count. CI retains the JSON, source hashes and logs, including failures, for 14 days.

Counts use explicitly named `o200k_base` and `cl100k_base` encodings. Unknown model mappings stay UNKNOWN. Both the current core and full core-plus-all-references are counted; the full-load token budget must not exceed the historical v0.1 core under either encoding. Role instructions are separate, not the cost of spawning. Host framing, other instructions, prompts, tools, reasoning, output, retries and inherited contexts are excluded.

The original failed experiment and report remain in the [historical evaluation branch](https://github.com/fgokey/codex-efficiency-router/tree/evaluation/quality-token-20260907/evaluation) and its immutable commits. The new report is not a rewrite of those results. These bounded checks do not prove universal policy correctness, live model compliance, quality equivalence or whole-task savings. Live acceptance is [user-run](../docs/ACCEPTANCE.md).
