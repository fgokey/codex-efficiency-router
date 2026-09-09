"""Three-arm, per-call accounting. Normalized data only; no model calls or prices fetched.

input_tokens INCLUDES cached_input_tokens. Actual invoice amounts and rate-card
estimates are distinct. Subscription spend without monetary attribution is UNKNOWN.
"""
from __future__ import annotations
import math
from collections import Counter, defaultdict
from statistics import median

VARIANTS = ('baseline', 'policy-only', 'guarded')
EFFORTS = ('none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'UNKNOWN')


def number(value, name, integer=False, nullable=True):
    if value is None and nullable:
        return None
    if type(value) not in ((int,) if integer else (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be finite, nonnegative' + (' integer' if integer else ''))
    return value


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')
    return value


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def call_cost(call):
    actual = call.get('actual_cost')
    if actual is not None:
        if not isinstance(actual, dict):
            raise ValueError('actual_cost must be an object')
        amount = number(actual.get('amount'), 'actual_cost.amount', nullable=False)
        currency = text(actual.get('currency'), 'currency')
        text(actual.get('source'), 'actual cost provenance')
        return amount, currency, 'actual'
    rates = call.get('rates')
    if rates is None:
        return None, None, 'UNKNOWN'
    if not isinstance(rates, dict) or rates.get('model') != call['model']:
        raise ValueError('rate card must identify this exact actual model')
    currency = text(rates.get('currency'), 'currency')
    text(rates.get('source'), 'price source'); text(rates.get('effective_at'), 'price effective date')
    prices = [number(rates.get(k), k, nullable=False) for k in
              ('input_per_million', 'cached_input_per_million', 'output_per_million')]
    counts = [call.get(k) for k in ('input_tokens', 'cached_input_tokens', 'output_tokens')]
    if any(v is None for v in counts):
        return None, currency, 'UNKNOWN'
    total, cached, output = counts
    amount = ((total - cached) * prices[0] + cached * prices[1] + output * prices[2]) / 1_000_000
    return amount, currency, 'rate-card-estimate'


def normalize(row):
    for key in ('task_id', 'trial_id', 'environment_id', 'acceptance_id', 'input_id'):
        text(row.get(key), key)
    if row.get('variant') not in VARIANTS or row.get('outcome') not in ('pass', 'fail', 'unknown'):
        raise ValueError('invalid variant/outcome')
    for key in ('calls_complete', 'randomized_order'):
        if key in row and type(row[key]) is not bool:
            raise ValueError(f'{key} must be boolean')
    if row.get('run_order') is not None and row['run_order'] not in (1, 2, 3):
        raise ValueError('run_order must be 1, 2 or 3')
    if isinstance(row.get('run_order'), bool):
        raise ValueError('run_order is not boolean')
    for key in ('elapsed_seconds', 'critical_path_seconds', 'waiting_seconds'):
        number(row.get(key), key)
    if (row.get('elapsed_seconds') is not None and row.get('critical_path_seconds') is not None
            and row['critical_path_seconds'] > row['elapsed_seconds']):
        raise ValueError('critical path cannot exceed wall time')
    calls = row.get('calls')
    if calls is None:
        calls = []
    if not isinstance(calls, list):
        raise ValueError('calls must be an array of all parent/child attempts')
    ids = set()
    per_model = defaultdict(lambda: {'calls': 0, 'input_tokens': 0, 'cached_input_tokens': 0,
                                    'output_tokens': 0, 'efforts': Counter(), 'attempts': [],
                                    'statuses': Counter(), 'costs': defaultdict(float)})
    costs = []
    token_complete = bool(calls) and row.get('calls_complete') is True
    for call in calls:
        if not isinstance(call, dict):
            raise ValueError('each call must be an object')
        cid = text(call.get('call_id'), 'call_id')
        if cid in ids:
            raise ValueError('duplicate call_id within a run')
        ids.add(cid)
        model = text(call.get('model'), 'actual model')
        effort = call.get('effort')
        if effort not in EFFORTS:
            raise ValueError('record actual effort or UNKNOWN')
        attempt = number(call.get('attempt'), 'attempt', integer=True, nullable=False)
        if attempt < 1:
            raise ValueError('attempt starts at 1')
        status = call.get('status')
        if status not in ('completed', 'failed', 'abandoned'):
            raise ValueError('include completed, failed and abandoned attempts')
        for key in ('input_tokens', 'cached_input_tokens', 'output_tokens'):
            number(call.get(key), key, integer=True)
        if (call.get('cached_input_tokens') is not None and call.get('input_tokens') is not None
                and call['cached_input_tokens'] > call['input_tokens']):
            raise ValueError('cached input must be a subset of total input')
        model_row = per_model[model]; model_row['calls'] += 1
        model_row['efforts'][effort] += 1; model_row['attempts'].append(attempt)
        model_row['statuses'][status] += 1
        for key in ('input_tokens', 'cached_input_tokens', 'output_tokens'):
            if call.get(key) is None:
                token_complete = False; model_row[key] = None
            elif model_row[key] is not None:
                model_row[key] += call[key]
        amount, currency, basis = call_cost(call)
        costs.append((amount, currency, basis))
        if amount is not None:
            model_row['costs'][currency] += amount
    currency_set = {currency for amount, currency, _ in costs if amount is not None}
    money_complete = (bool(calls) and row.get('calls_complete') is True
                      and all(amount is not None for amount, _, _ in costs) and len(currency_set) == 1)
    actual = money_complete and all(basis == 'actual' for _, _, basis in costs)
    price_status = 'actual' if actual else 'rate-card-estimate' if money_complete else 'UNKNOWN'
    amount = sum(v for v, _, _ in costs) if money_complete else None
    metrics = {key: sum(call[key] for call in calls) if token_complete else None
               for key in ('input_tokens', 'cached_input_tokens', 'output_tokens')}
    metrics['total_tokens'] = metrics['input_tokens'] + metrics['output_tokens'] if token_complete else None
    metrics.update({key: row.get(key) for key in ('elapsed_seconds', 'critical_path_seconds', 'waiting_seconds')})
    metrics['monetary_cost'] = amount
    guard = row.get('guard')
    guard_stats = {'status': 'UNKNOWN'}
    if guard is not None:
        if not isinstance(guard, dict):
            raise ValueError('guard measurements must be an object')
        times = guard.get('latencies_ms')
        if not isinstance(times, list):
            raise ValueError('guard latency samples required')
        for v in times:
            number(v, 'guard latency', nullable=False)
        count = number(guard.get('calls'), 'guard calls', integer=True, nullable=False)
        denied = number(guard.get('denied'), 'guard denied', integer=True, nullable=False)
        errors = number(guard.get('errors'), 'guard errors', integer=True, nullable=False)
        if len(times) != count or denied + errors > count:
            raise ValueError('guard counters/latency samples inconsistent')
        guard_stats = {'status': 'measured', 'calls': count, 'denied': denied, 'errors': errors,
                       'p50_ms': percentile(times, .50), 'p95_ms': percentile(times, .95)}
    violations = {}
    for key in ('astra_writes', 'duplicate_writers', 'retry_replays'):
        violations[key] = number(row.get(key), key, integer=True)
    return {'variant': row['variant'], 'metrics': metrics, 'price_status': price_status,
            'currency': next(iter(currency_set)) if money_complete else 'UNKNOWN',
            'per_model': dict(per_model), 'guard': guard_stats, 'violations': violations,
            'calls_complete': row.get('calls_complete') is True,
            'all_pairs_observed': bool(calls) and all(c['model'] != 'UNKNOWN' and c['effort'] != 'UNKNOWN' for c in calls)}


def compare_three(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('nonempty three-arm runs required')
    groups = {}; normalized = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('each run must be an object')
        item = normalize(row); normalized.append(item)
        key = (row['task_id'], row['trial_id'])
        group = groups.setdefault(key, {})
        if row['variant'] in group:
            raise ValueError('duplicate run variant in task/trial')
        group[row['variant']] = row
    for key, group in groups.items():
        if set(group) != set(VARIANTS):
            raise ValueError(f'three complete variants required: {key}')
        base = group['baseline']
        for row in group.values():
            if any(row[k] != base[k] for k in ('environment_id', 'acceptance_id', 'input_id')):
                raise ValueError(f'input/environment/acceptance differ: {key}')
        orders = [r.get('run_order') for r in group.values()]
        if any(v is not None for v in orders) and set(orders) != {1, 2, 3}:
            raise ValueError('run_order must be a permutation per trial')
    quality = all(row['outcome'] == 'pass' for row in rows)
    measurements = {}
    for metric in normalized[0]['metrics']:
        complete = all(r['metrics'][metric] is not None for r in normalized)
        if metric == 'monetary_cost' and len({r['currency'] for r in normalized}) != 1:
            complete = False
        if not complete:
            measurements[metric] = {'status': 'UNKNOWN'}
            continue
        totals = {v: sum(r['metrics'][metric] for r in normalized if r['variant'] == v) for v in VARIANTS}
        status = 'measured'
        if metric == 'monetary_cost':
            status = 'actual' if all(r['price_status'] == 'actual' for r in normalized) else 'rate-card-estimate'
        measurements[metric] = {'status': status, **totals,
            'reductions_vs_baseline': {v: None if totals['baseline'] == 0 else 1 - totals[v] / totals['baseline']
                                      for v in VARIANTS[1:]}}
    task_trials = Counter(task for task, _ in groups)
    sampling = all(v >= 3 for v in task_trials.values()) and all(row.get('randomized_order') is True and row.get('run_order') in (1, 2, 3) for row in rows)
    accounting = all(r['calls_complete'] and r['all_pairs_observed'] for r in normalized)
    measurements_ready = all(measurements[k]['status'] in ('measured', 'actual') for k in ('total_tokens', 'monetary_cost', 'elapsed_seconds'))
    guard_ready = all(r['guard']['status'] == 'measured' and r['guard']['errors'] == 0 and r['guard']['calls'] > 0 for r in normalized if r['variant'] == 'guarded')
    boundaries = all(all(v == 0 for v in r['violations'].values()) for r in normalized if r['variant'] != 'baseline')
    return {'schema': 2, 'matched_trials': len(groups), 'quality_status': 'pass' if quality else 'incomplete',
            'efficiency_claim_eligible': quality and accounting and measurements_ready and sampling and boundaries and guard_ready,
            'formal_sampling_ready': sampling, 'accounting_complete': accounting,
            'measurements': measurements, 'runs': normalized,
            'limitation': 'Descriptive matched trials, not proof of future quality. Rate-card estimates are not actual subscription charges. Missing data is UNKNOWN.'}
