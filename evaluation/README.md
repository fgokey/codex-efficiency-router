# Offline release audit

`offline_audit.py` runs existing regression tests, the eight retained boundary probes and twelve deliberate routing-policy plus twelve quality-protocol mutations in subprocess-local module objects. It does not modify production files, authenticate to Codex or call model APIs. Mutants must fail assertions; crashes/timeouts are not counted as detections. New opt-out tests enable available routes so missing-host fallbacks cannot mask a broken guard.

```sh
python evaluation/offline_audit.py --without-tokenizer
```

This mode leaves text-token metrics NOT RUN. For the independent text-budget job:

```sh
python -m pip install tiktoken==0.11.0
python evaluation/offline_audit.py
```

A full Git clone is needed for the fixed v0.1 and v0.2 source baselines. First-time tokenizer vocabulary downloads and package installation need network access; no model inference is involved. Results and logs are stored in `evaluation-results/`, excluded from Git. A missing tokenizer, baseline or encoding is an error, never a fabricated count. CI retains the JSON, source hashes and logs, including failures, for 14 days.

Counts use explicitly named `o200k_base` and `cl100k_base` encodings. Unknown model mappings stay UNKNOWN. The current core, all three references, and each role instruction are counted against immutable v0.2.1 source; neither core, full-load nor full-load-plus-role totals may regress under either encoding. Role instructions are separate, not the cost of spawning. Host framing, other instructions, prompts, tools, reasoning, output, retries and inherited contexts are excluded.

The original failed experiment and report remain in the [historical evaluation branch](https://github.com/fgokey/codex-efficiency-router/tree/evaluation/quality-token-20260907/evaluation) and its immutable commits. The new report is not a rewrite of those results. These bounded checks do not prove universal policy correctness, live model compliance, quality equivalence or whole-task savings. Live acceptance is [user-run](../docs/ACCEPTANCE.md).

## Natural-language cases are not offline model runs

`behavior_cases.json` supplies 20 Codex task/setup/rubric entries. Their structure is checked, not agent behavior; report.live_runs remains zero. `quality_reference.py` checks declared evidence, handoff preconditions, cross-worker attempts and recovery state without reading code or invoking a host. Selected mutations must cause assertion failures, not errors/timeouts. The original failed evaluations remain unchanged.
