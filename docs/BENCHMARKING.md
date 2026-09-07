# Benchmarking

This repository does not claim a universal percentage reduction in tokens or latency. Results depend on repository size, task type, model availability, caching, Codex version, and verification strategy.

## Recommended experiment

Compare at least three modes on the same sanitized task set:

1. strong-model baseline (for example Sol or Astra throughout);
2. router enabled;
3. cheaper-model baseline if safe to evaluate.

Use tasks from multiple classes:

- mechanical migration;
- normal bounded feature;
- cross-module bug;
- hard ambiguous root-cause problem;
- large deterministic test/build task.

## Record

For every run record:

- Codex version and date;
- model + reasoning effort per agent;
- task prompt and starting commit;
- acceptance criteria;
- pass/fail;
- total tokens across root + children;
- elapsed wall-clock time;
- child-agent count;
- retry/escalation count;
- manual intervention;
- cache/warm-start conditions if observable.

## Quality-first comparison

Do not declare a route more efficient when it uses fewer tokens but fails acceptance or requires more human repair.

A useful primary metric is:

`verified_successes / total_expensive_model_tokens`

A useful latency metric is median end-to-end time over repeated runs, with failures counted rather than discarded.

## Routing regression tests

`tests/cases.json` is intentionally synthetic. It checks that policy edits preserve expected lane choices. It is not a model-quality benchmark.
