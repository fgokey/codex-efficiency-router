# Benchmarking: do not confuse route tests with model performance

This release includes offline regression tests and a **descriptive paired-run comparator**, not results from live Astra/Luna/Terra/Sol coding trials. There is no automatic online learning, hidden telemetry or per-turn ledger.

## Evaluation design

Use representative tasks from more than one repository: small edits, settled implementation, ambiguous bugs, difficult design, migration strategy and negative controls such as missing permissions or a broken build environment. Include tests for explicit and implicit Skill triggering, irrelevant requests, disabled routing, actual model selection, handoff correctness and complete-task outcomes.

Compare a fixed baseline configuration to the router on the same repository revision, dirty-state policy, environment, tools, task input and externally defined acceptance. Run multiple trials; model output is nondeterministic. Isolate variants so one run's edits do not leak into the other; alternate execution order or control warm/cold-cache conditions. Keep reviewer/grader independence for important judgment not covered by tests.

Measure regressions first. A lower success rate or an important newly failing case is not rescued by cheaper tokens. Aggregate success alone can hide a regression in a critical task. For a quality claim, predefine a tolerable non-inferiority margin, sample size and uncertainty analysis; this simple comparator does not perform that statistical analysis.

## Whole-task accounting

For each trial capture actual parent and child model/effort, total input/output/reasoning usage with the provider's counting semantics, cached input, all retries, verification work, tool duration, task start/end and remaining unknowns. Do not double-count reasoning tokens if already included in output totals. Do not sum repeated cumulative `thread/tokenUsage/updated` totals: take each thread's final total or deduplicated deltas, then aggregate all owned threads. Record `model/rerouted` when exposed.

Include fixture preparation, admission, reads, implementation, parent review, retries and waits in the whole-task totals. Keep task execution and orchestration subtotals so either can be inspected without presenting a child-only number as the total. Prefer deterministic local fixture setup, frozen oracles and metric aggregation; extra model calls are not prerequisites for an evaluation. Create a HOLD worker only after its exact task and prerequisites are ready, verify its current binding, then assign promptly; do not precreate idle workers. A missing or unloaded native thread remains a host limitation until its cause is verified; it does not authorize resume, identity fallback or admission bypass.

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

Legacy CLI exit: 0 only for no observed regression AND every Router outcome passing; 1 for any incomplete Router acceptance, regression or unknown outcome; 2 for invalid input. `router_acceptance` distinguishes completion from relative regression. Legacy `efficiency_claim_eligible` is always false because this format lacks per-call monetary provenance. Exit 0 is not a production rollout certificate. Samples are not automatically accumulated, used to tune thresholds, or uploaded.

The three-variant format (`baseline`, `policy-only`, `guarded`) returns schema 3. Its CLI exits 0 when `quality_status` is `pass`, 1 for incomplete quality and 2 for invalid input; efficiency eligibility has additional accounting, sampling and boundary requirements. Per-model rows mark `calls_complete`, `usage_status`, `price_status` and counted `cost_basis` values (`actual`, `rate-card-estimate`, `UNKNOWN`). Missing calls make token totals null; missing prices or mixed currencies make `costs` null. Complete mixed actual/estimated costs remain estimates and retain both basis counts. UNKNOWN never means zero or savings.

## Release acceptance

Offline tests guard shipped policy, packaging, install/uninstall/restore and measurement semantics. Live model suitability, actual dispatch and verified task outcomes need a separate user-host evaluation. Only after those trials can real token or latency improvements be reported. See [evaluation sources](PRIOR-ART.md).

## v0.3 behavioral acceptance

The [20-case corpus](../evaluation/behavior_cases.json) includes natural user prompts, fixture setup, required observations and forbidden behavior. CI checks its shape only; all live results remain null. A human constructs isolated fixtures and presents prompt/setup without exposing grader answers. Grade actual changes, traces and requirement evidence; do not infer triggering or correctness by scanning output for model names. Completion, handoff and recovery helpers test declared conditions, not natural-language inference. No online calibrator or automatic model trial is included. [Protocol](QUALITY-PROTOCOL.md).

## v0.7 candidate extension

See [three-arm per-call accounting and subprocess measurements](BENCHMARKING-v0.7.md).
The original paired format remains supported, but without attributable per-call money
and all descendants it cannot establish monetary efficiency. No live savings are claimed.

## Off/on per-call pairs

The same `scripts/compare_runs.py runs.json` command also accepts `off` and `on` rows
(schema 4 output). Keep the legacy three-arm format separate; neither format permits
silently dropping a failed or incomplete trial. Freeze at least three task families,
three pairs per family, and their independent acceptance before execution. Randomize
the first order, then alternate; each task's orders must be balanced within one pair.
Record `randomized_order=true` for that randomized-start schedule and `run_order=1|2`.

Each row retains `task_id`, `trial_id`, `environment_id`, `input_id`, `acceptance_id`,
`outcome`, whole-task `elapsed_seconds`, and the existing per-call usage/cost fields.
Add observed `skills_enabled` (false for off, true for on), `isolation_evidence`,
`parent_call_id`, and `owned_scope_ids`. Every call needs its actual `scope_id`,
model, effort (including `ultra`), attempt and status. The parent model/effort and
task/environment/input/acceptance controls must match across all repetitions.
Isolation evidence must identify the verified loaded Skill/role/Hook/config state;
a nonempty reference is supplied evidence, not a comparator or live-host attestation.
Do not call a run off when it only omitted additional Skill activation.

Owned scopes must match the observed calls exactly and cannot be counted in another
run. Distinct `call_id` invocations may share a scope and each have `attempt=1`;
`attempt` is a call's retry ordinal, not a unique sequence within its scope.
Duplicate call IDs remain errors. Include failed/retried attempts once each. Attribute shared preparation/review
to one owned scope using `shared_parent_scope_ids` and `shared_parent_attribution`;
its calls remain in the totals. Unallocated/shared costs or missing descendants mean
`calls_complete=false`, never zero or a child-only whole-task claim. If a parent
cannot be allocated without biasing a pair, the affected comparison remains incomplete.

Optional per-call `usage_snapshots` hold cumulative counters with integer `sequence`
and a terminal `final=true`. Repeated identical sequence records count once;
conflicts, decreasing counters, or counters after final are errors. Only the final
counters count; no terminal snapshot leaves usage UNKNOWN. Explicit call counters
must agree with the final snapshot. Cached input is a subset of input; optional
reasoning is a subset of output and is never added again.
Each call declares `usage_semantics=per_call` for one attempt's counters or
`scope_cumulative` for the final cumulative scope counters. The latter requires
snapshots and cannot share its scope with other call records: do not add a thread
total to that thread's individual turns. The output retains final per-call counters,
attempt/status, scope ownership and task/control identifiers for independent audit.

`claim_eligibility` reports token, elapsed-time and monetary eligibility separately.
All require accepted tasks, complete ownership/identity, finite repeated sampling
and observed boundary checks. Missing usage invalidates token claims; incomplete
call coverage invalidates all efficiency claims. Missing money leaves monetary cost
UNKNOWN without suppressing independently complete token/time evidence. Rate cards
remain estimates and do not establish actual subscription spending. The old
three-arm `efficiency_claim_eligible` money gate is unchanged.

Released writable executors may use authorized bounded native reads in the same
task/root/link/output scope, avoiding unnecessary helper calls. Astra, read-only
and unknown roles retain the existing guarded boundary. This grants no new access
and does not claim the native tool implements Reader's contract. When using Reader,
for known physical paths reuse its CLI directly; help/list/locate is needed
only for missing syntax, unknown locations, stale evidence or an error. In PowerShell,
with verified `$python`, `$skill`, `$repo`, output budget and framing already known:

```powershell
$OutputEncoding = [Text.UTF8Encoding]::new($false)
$cerRaw = '[{"op":"page","path":"VERSION"},{"op":"page","path":"AGENTS.md"}]' |
  & $python -I -B "$skill/scripts/readonly_reader.py" batch --root $repo --requests - --max-bytes $maxBytes --framing-bytes $framingBytes
if ($LASTEXITCODE -ne 0) { throw 'Reader failed; inspect the error before parsing' }
$cerResponse = $cerRaw | ConvertFrom-Json
```

Capture the response before parsing; retain every status/error/cursor and continue
only pending requests. Small complete page requests are captured first to free the
remaining batch budget; results retain request order. Full path/link preflight,
strict UTF-8/JSON, SHA-bound continuations and aggregate framing limits still apply.
