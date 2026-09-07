# Benchmarking: do not confuse route tests with model performance

This release includes offline regression tests and a **descriptive paired-run comparator**, not results from live Astra/Luna/Terra/Sol coding trials. There is no automatic online learning, hidden telemetry or per-turn ledger.

## Evaluation design

Use representative tasks from more than one repository: small edits, settled implementation, ambiguous bugs, difficult design, migration strategy and negative controls such as missing permissions or a broken build environment. Include tests for explicit and implicit Skill triggering, irrelevant requests, disabled routing, actual model selection, handoff correctness and complete-task outcomes.

Compare a fixed baseline configuration to the router on the same repository revision, dirty-state policy, environment, tools, task input and externally defined acceptance. Run multiple trials; model output is nondeterministic. Isolate variants so one run's edits do not leak into the other; alternate execution order or control warm/cold-cache conditions. Keep reviewer/grader independence for important judgment not covered by tests.

Measure regressions first. A lower success rate or an important newly failing case is not rescued by cheaper tokens. Aggregate success alone can hide a regression in a critical task. For a quality claim, predefine a tolerable non-inferiority margin, sample size and uncertainty analysis; this simple comparator does not perform that statistical analysis.

## Whole-task accounting

For each trial capture actual parent and child model/effort, total input/output/reasoning usage with the provider's counting semantics, cached input, all retries, verification work, tool duration, task start/end and remaining unknowns. Do not double-count reasoning tokens if already included in output totals. Do not sum repeated cumulative `thread/tokenUsage/updated` totals: take each thread's final total or deduplicated deltas, then aggregate all owned threads. Record `model/rerouted` when exposed.

Define expensive-model tokens consistently across both variants. Cost and tokens are different; API list pricing must not be converted to Codex subscription quota. Cache discounts are not zero tokens. Use full task elapsed time, not first-token latency or the sum of concurrent child durations.

## Normalized input for the optional comparator

`runs.json` is an array of paired records. One row represents the **entire task** after correct accounting. Example below is synthetic, for format demonstration only:

```json
[
  {"task_id":"sample", "trial_id":"1", "environment_id":"revision-and-env-v1", "acceptance_id":"checks-v1", "variant":"baseline", "outcome":"pass", "total_tokens":100, "expensive_model_tokens":80, "elapsed_seconds":20},
  {"task_id":"sample", "trial_id":"1", "environment_id":"revision-and-env-v1", "acceptance_id":"checks-v1", "variant":"router", "outcome":"pass", "total_tokens":70, "expensive_model_tokens":20, "elapsed_seconds":15}
]
```

```sh
python3 scripts/compare_runs.py runs.json
```

Use `outcome` = `pass`, `fail` or `unknown`. Omitted/null metrics mean unknown, not zero. Token fields must be nonnegative integers; elapsed seconds must be finite and nonnegative. Both variants must share environment and acceptance IDs. Duplicate or incomplete pairs are rejected.

The report identifies baseline-pass/router-fail regressions, unknown outcomes, both pass counts, and sums of comparable metrics. If any value of a metric is missing, its aggregate is unknown. Zero baseline has no percentage reduction. `no_observed_regression` means only that this sample showed no paired pass-to-fail case: **both variants could still have failed**. Check pass counts and failure severity before interpreting it.

CLI exit: 0 for no observed regression, 1 for a regression or unknown outcome, 2 for invalid input. Exit 0 is not a production rollout certificate. Samples are not automatically accumulated, used to tune thresholds, or uploaded.

## Release acceptance

Offline tests guard shipped policy, packaging, install/uninstall/restore and measurement semantics. Live model suitability, actual dispatch and verified task outcomes need a separate user-host evaluation. Only after those trials can real token or latency improvements be reported. See [evaluation sources](PRIOR-ART.md).
