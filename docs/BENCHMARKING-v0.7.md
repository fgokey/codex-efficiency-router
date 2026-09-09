# v0.7 accounting and guard measurements

## Three separate arms

`compare_runs.py` retains legacy baseline/router input, but legacy records cannot
establish monetary efficiency. New rows use `baseline`, `policy-only`, `guarded`.
One complete triple is required for each `(task_id, trial_id)` and must share
`input_id`, `environment_id`, `acceptance_id`. Use the same task and independent
reset fixtures, not differently sized examples. Warm-cache and cold-cache conditions
must not be silently mixed. Before formal conclusions use at least three trials per
task/condition and randomized execution order; three trials are a minimum, not a
statistical significance guarantee.

The normalized JSON file is an array of rows. JSONL is not supported by this CLI.
No parser here discovers missing sessions, reads private transcripts, fetches prices,
or contacts models. `calls_complete=true` is a collector/operator attestation, not
proof that omitted children do not exist. Each row includes:

| Field | Meaning |
| --- | --- |
| task_id / trial_id / variant | Matched task, repetition and one of three arms |
| input_id / environment_id / acceptance_id | Same inputs, runtime/settings and independent acceptance contract |
| outcome | pass / fail / unknown; use real tests, static checks and code-review evidence |
| elapsed_seconds / critical_path_seconds / waiting_seconds | Measured run wall time, dependency path and waiting; do not sum overlapping child durations |
| run_order / randomized_order | 1..3 permutation in the trial and explicit randomized-order declaration |
| calls_complete | Whether all parent, child, failed, abandoned and retried calls were captured |
| calls | Full normalized per-call records below |
| astra_writes / duplicate_writers / retry_replays | Observed counts; omitted is UNKNOWN, not zero |
| guard | Calls, denied, errors and a latency sample per invocation for the guarded arm |

A per-call example **with unknown prices, not fictional billing evidence**:

```json
{
  "call_id": "unique-attempt-id",
  "model": "ACTUAL_MODEL_SLUG",
  "effort": "medium",
  "attempt": 1,
  "status": "completed",
  "input_tokens": 100,
  "cached_input_tokens": 40,
  "output_tokens": 20
}
```

Token values above demonstrate structure only. `input_tokens` already INCLUDES cached
input: total tokens = input + output, not input + cached + output. If actual counts
are missing use null; never substitute zero. Failed/abandoned calls retain their cost.
For actual attributable monetary cost add `actual_cost` with numeric `amount`, currency
and explicit source. Paid plan credits/weekly percentages are not attributable money.

Alternatively `rates` may contain the exact `model`, `currency`, `source`, `effective_at`,
`input_per_million`, `cached_input_per_million`, `output_per_million`. Formula:

```text
((input - cached) * input_rate + cached * cached_rate + output * output_rate) / 1e6
```

That is labelled `rate-card-estimate`, NEVER `actual`. Mixed currencies, missing usage,
unknown price sources or incomplete descendants cannot produce a complete monetary
comparison. Do not put private invoice content into shared evaluation records; retain
an appropriate minimal source identifier.

For guard measurements use e.g. `{"calls":2,"denied":1,"errors":0,"latencies_ms":[1,2]}`
as a format illustration only; counters must match sample count. The comparator reports
per-model tokens/costs/efforts/statuses/attempts, P50/P95, relative measurements and
explicit missing data. `efficiency_claim_eligible` requires complete actual costs,
observed model/effort, quality pass, recorded safe behavior, measured guard calls,
wall time/tokens and the formal sampling gate. This Boolean is a necessary data gate,
not a guarantee that costs fell, future quality is preserved or a causal effect exists.

```powershell
python -B scripts/compare_runs.py ACTUAL_RUNS.json
```

The CLI prints JSON to stdout; it does not manage report files. Unit tests use obvious
synthetic invoice labels; they are not results from live model experiments.

## Offline process microbenchmark

```powershell
python -B scripts/benchmark_guard.py --iterations 30 --output NEW_REPORT.json
```

Creates local disposable text fixtures; invokes Python guard/reader subprocesses only.
It measures guard denial, normal executor passthrough, cer-read rewrite, four separate
reader processes versus one four-operation batch. Operation order rotates between
iterations; Python startup and bundle-hash checking are included. P50/P95 use nearest
rank. This is NOT native Codex Hook latency, tool-response token use or end-to-end task
speed. CI does not enforce a universal millisecond target across unrelated machines.

A batch input allows at most 16 operations and 16 KiB JSON. Combined file-byte budget
is 16 MiB, also checked against actual reads (at most one extra overflow-detection byte);
combined output is 128 KiB before the CLI newline. Each op preflights its path, no nested
batch/extra Git args/environment/redirect is allowed, and an invalid item rejects the
batch. Search remains a literal single-file operation; directory-recursive search is
not introduced by this optimization. Git output/time is bounded separately; the reader
cannot promise a bound on internal Git repository scanning.

The archived Linux microbenchmark, when supplied with the validation report, applies
only to its recorded guard digest/platform. No live model prices, cost savings or
Windows speed claims are inferred. Do not add a resident daemon without further
end-to-end measurements establishing worthwhile benefit.
