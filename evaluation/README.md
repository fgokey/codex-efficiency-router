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

Counts use explicitly named `o200k_base` and `cl100k_base` encodings. Unknown model mappings stay UNKNOWN. The current core, all four references, and each role instruction are counted against immutable v0.2.1 source; neither core, full-load nor full-load-plus-role totals may regress under either encoding. Role instructions are separate, not the cost of spawning. Host framing, other instructions, prompts, tools, reasoning, output, retries and inherited contexts are excluded.

The original failed experiment is now preserved in main as the [historical report](RESULTS-2026-09-07.md), [original instructions](README-2026-09-07.md), [original script](quality_token_audit.py) and [archived workflow](archive/quality-token-audit-2026-09-07.yml). These four files retain the exact bytes from evaluation commit `557bc7b2461e9c42509879039b01d20ece89f3fa`; their results still describe the old target, not rc.2. The current audit and `.github/workflows/validate.yml` remain authoritative. The old workflow is deliberately outside `.github/workflows` to avoid activating a superseded historical job. The old script checks its fixed target before running tests; reproduce it only in an isolated checkout of the [original evaluation commit](https://github.com/fgokey/codex-efficiency-router/tree/557bc7b2461e9c42509879039b01d20ece89f3fa), never by resetting a working project. Original relative instructions refer to that checkout. Historical failures are not rewritten as passes.

These bounded checks do not prove universal policy correctness, live model compliance, quality equivalence or whole-task savings. Live acceptance is [user-run](../docs/ACCEPTANCE.md).

## Natural-language cases are not offline model runs

`behavior_cases.json` supplies 20 Codex task/setup/rubric entries. Their structure is checked, not agent behavior; report.live_runs remains zero. `quality_reference.py` checks declared evidence, handoff preconditions, cross-worker attempts and recovery state without reading code or invoking a host. Selected mutations must cause assertion failures, not errors/timeouts. The original failed evaluations remain unchanged.

## v0.4 effort coverage

The joint helper adds 18 selected effort mutations, including task-level sticky
low suspension, explicit support, pin precedence, no-escalation across both axes,
and retention of exhausted repair budgets. The original routing and quality
mutations remain. Corpus `effort_cases.json` adds 10 user-run prompts; none is
live-scored by CI. Both fixed and generated adaptive instruction paths are counted,
without claiming parent/child runtime usage or exact model tokenization.

## v0.5 automatic binding coverage

The ordinary installation is auto; runtime tests supply observed capabilities without running a model. Added cases cover native alias preference, missing effort fields, exact fixed compatibility, bad pins/models, task-local failed bindings and uncertain active writers. Migration tests cover old fixed/adaptive installs, alias collisions, rollback, and exact backup restore. Nine added effort mutations test the new admission gates; assertions, not crashes, must detect them.

The tokenizer audit also counts auto core/full text and a declared rendering of the four extra alias name/description strings. Extra discovery text is not free. The auto-full-plus-extra-discovery comparison is separately gated against the historical full reference baseline. This is an illustrative text rendering, not a host metadata schema or whole-task billing. All existing core/full/role gates remain unchanged.
