"""Three-arm, per-call accounting. Normalized data only; no model calls or prices fetched.

input_tokens INCLUDES cached_input_tokens. Actual invoice amounts and rate-card
estimates are distinct. Subscription spend without monetary attribution is UNKNOWN.
"""
from __future__ import annotations
import math
from collections import Counter, defaultdict
from statistics import median

VARIANTS = ('baseline', 'policy-only', 'guarded')
PAIRED_VARIANTS = ('off', 'on')
EFFORTS = ('none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra', 'UNKNOWN')


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
    if row.get('variant') not in VARIANTS + PAIRED_VARIANTS or row.get('outcome') not in ('pass', 'fail', 'unknown'):
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
                                    'statuses': Counter(), 'costs': defaultdict(float),
                                    'cost_basis': Counter()})
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
        number(call.get('reasoning_tokens'), 'reasoning_tokens', integer=True)
        if (call.get('reasoning_tokens') is not None and call.get('output_tokens') is not None
                and call['reasoning_tokens'] > call['output_tokens']):
            raise ValueError('reasoning must be a subset of output, never added twice')
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
        model_row['cost_basis'][basis] += 1
        if amount is not None:
            model_row['costs'][currency] += amount
    for model_row in per_model.values():
        complete = row.get('calls_complete') is True
        model_row['calls_complete'] = complete
        model_row['usage_status'] = ('measured' if complete and all(model_row[key] is not None
                                    for key in ('input_tokens', 'cached_input_tokens', 'output_tokens')) else 'UNKNOWN')
        if not complete:
            for key in ('input_tokens', 'cached_input_tokens', 'output_tokens'):
                model_row[key] = None
        money_complete = complete and not model_row['cost_basis']['UNKNOWN'] and len(model_row['costs']) == 1
        model_row['price_status'] = ('actual' if money_complete and not model_row['cost_basis']['rate-card-estimate']
                                    else 'rate-card-estimate' if money_complete else 'UNKNOWN')
        if not money_complete:
            model_row['costs'] = None
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
    astra_writes = number(row.get('astra_writes'), 'astra_writes', integer=True)
    astra_exceptions = number(row.get('astra_write_exceptions'), 'astra_write_exceptions', integer=True)
    if astra_writes == 0 and astra_exceptions is None:
        astra_exceptions = 0  # Backward-compatible zero; positive writes still need classification.
    if astra_writes is not None and astra_exceptions is not None and astra_exceptions > astra_writes:
        raise ValueError('Astra write exceptions cannot exceed Astra writes')
    unqualified = astra_writes - astra_exceptions if None not in (astra_writes, astra_exceptions) else None
    if row['variant'] in ('guarded', 'on') and astra_exceptions not in (None, 0):
        raise ValueError('strict guarded runs cannot claim Astra write exceptions')
    violations = {'unqualified_astra_writes': unqualified}
    for key in ('duplicate_writers', 'retry_replays'):
        violations[key] = number(row.get(key), key, integer=True)
    return {'variant': row['variant'], 'metrics': metrics, 'price_status': price_status,
            'currency': next(iter(currency_set)) if money_complete else 'UNKNOWN',
            'per_model': dict(per_model), 'guard': guard_stats, 'violations': violations,
            'astra_write_observation': {'total': astra_writes, 'qualified_exceptions': astra_exceptions},
            'calls_complete': row.get('calls_complete') is True,
            'all_pairs_observed': bool(calls) and all(c['model'] != 'UNKNOWN' and c['effort'] != 'UNKNOWN' for c in calls)}


def compare_three(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('nonempty three-arm runs required')
    groups = {}; normalized = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('each run must be an object')
        if row.get('variant') not in VARIANTS:
            raise ValueError('three-arm variant required')
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
    ready = quality and accounting and sampling and boundaries and guard_ready
    return {'schema': 3, 'matched_trials': len(groups), 'quality_status': 'pass' if quality else 'incomplete',
            'efficiency_claim_eligible': quality and accounting and measurements_ready and sampling and boundaries and guard_ready,
            'claim_eligibility': {k: ready and measurements[k]['status'] in ('measured', 'actual')
                                  for k in ('total_tokens', 'elapsed_seconds', 'monetary_cost')},
            'formal_sampling_ready': sampling, 'accounting_complete': accounting,
            'measurements': measurements, 'runs': normalized,
            'limitation': 'Descriptive matched trials, not proof of future quality. Rate-card estimates are not actual subscription charges. Missing data is UNKNOWN.'}


def paired_calls(row):
    """Take final cumulative counters once; retain every failed/retried call."""
    calls = row.get('calls')
    if not isinstance(calls, list) or not calls:
        raise ValueError('paired runs require all owned parent/child attempts')
    result = []
    for original in calls:
        if not isinstance(original, dict):
            raise ValueError('each call must be an object')
        call = dict(original)
        if call.get('usage_semantics') not in ('per_call', 'scope_cumulative'):
            raise ValueError('declare per_call or scope_cumulative usage semantics')
        if call['usage_semantics'] == 'scope_cumulative' and 'usage_snapshots' not in call:
            raise ValueError('scope cumulative usage requires explicit snapshots')
        if 'usage_snapshots' in call:
            snapshots = call['usage_snapshots']
            if not isinstance(snapshots, list) or not snapshots:
                raise ValueError('nonempty cumulative snapshots required')
            unique = {}
            for snapshot in snapshots:
                if not isinstance(snapshot, dict):
                    raise ValueError('snapshot must be an object')
                sequence = number(snapshot.get('sequence'), 'sequence', integer=True, nullable=False)
                if type(snapshot.get('final', False)) is not bool:
                    raise ValueError('final must be boolean')
                if sequence in unique and unique[sequence] != snapshot:
                    raise ValueError('conflicting repeated cumulative snapshot')
                unique[sequence] = snapshot
            ordered = [unique[n] for n in sorted(unique)]
            for position, snapshot in enumerate(ordered):
                if snapshot.get('final') is True and position != len(ordered) - 1:
                    raise ValueError('cumulative counters after final snapshot')
                for key in ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_tokens'):
                    number(snapshot.get(key), key, integer=True)
                    previous = ordered[position - 1].get(key) if position else None
                    if previous is not None and snapshot.get(key) is not None and snapshot[key] < previous:
                        raise ValueError('cumulative counters cannot decrease')
                for subset, total in (('cached_input_tokens', 'input_tokens'), ('reasoning_tokens', 'output_tokens')):
                    if snapshot.get(subset) is not None and snapshot.get(total) is not None and snapshot[subset] > snapshot[total]:
                        raise ValueError('snapshot subset exceeds total')
            final = ordered[-1] if ordered[-1].get('final') is True else {}
            for key in ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_tokens'):
                if final and key == 'reasoning_tokens' and key not in final:
                    continue
                if final and key in original and original[key] != final.get(key):
                    raise ValueError('call counters disagree with final cumulative snapshot')
                call[key] = final.get(key)
        result.append(call)
    return result


def compare_two(rows):
    """Strict off/on trials with explicit isolation and complete cost ownership."""
    if not isinstance(rows, list) or not rows:
        raise ValueError('nonempty off/on runs required')
    groups = {}; normalized = []; seen_scopes = set(); controls = {}
    for row in rows:
        if not isinstance(row, dict) or row.get('variant') not in PAIRED_VARIANTS:
            raise ValueError('off/on variant required')
        if row.get('skills_enabled') is not (row['variant'] == 'on'):
            raise ValueError('observed skill state must match off/on treatment')
        if type(row.get('run_order')) is not int or row['run_order'] not in (1, 2):
            raise ValueError('off/on run_order must be integer 1 or 2')
        text(row.get('isolation_evidence'), 'isolation_evidence')
        calls = paired_calls(row)
        owned = row.get('owned_scope_ids')
        if not isinstance(owned, list) or not owned:
            raise ValueError('owned_scope_ids must enumerate all cost owners')
        for scope in owned: text(scope, 'owned scope')
        if len(set(owned)) != len(owned) or seen_scopes.intersection(owned):
            raise ValueError('duplicate accounting scope across runs')
        seen_scopes.update(owned)
        observed = set(); scope_modes = {}
        for call in calls:
            scope = text(call.get('scope_id'), 'scope_id')
            mode = call['usage_semantics']
            if scope in scope_modes and 'scope_cumulative' in (mode, scope_modes[scope]):
                raise ValueError('cumulative scope totals cannot be combined with other calls in that scope')
            scope_modes[scope] = mode
            observed.add(scope)
        if observed != set(owned):
            raise ValueError('calls must cover exactly all owned accounting scopes')
        parent_id = text(row.get('parent_call_id'), 'parent_call_id')
        parent = [c for c in calls if c.get('call_id') == parent_id]
        if len(parent) != 1:
            raise ValueError('one observed parent call required')
        shared = row.get('shared_parent_scope_ids', [])
        if not isinstance(shared, list) or any(s not in owned for s in shared) or len(set(shared)) != len(shared):
            raise ValueError('shared parent costs must be owned and included exactly once')
        if shared: text(row.get('shared_parent_attribution'), 'shared_parent_attribution')
        item = normalize({**row, 'calls': calls})
        item['owned_scope_ids'] = owned
        item['shared_parent_scope_ids'] = shared
        item['shared_parent_attribution'] = row.get('shared_parent_attribution')
        item.update({k: row[k] for k in ('task_id', 'trial_id', 'environment_id', 'input_id', 'acceptance_id',
                                        'isolation_evidence', 'parent_call_id', 'skills_enabled', 'run_order')})
        item['calls'] = [{k: call.get(k) for k in ('call_id', 'scope_id', 'usage_semantics', 'model', 'effort',
                            'attempt', 'status', 'input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_tokens')}
                         for call in calls]
        normalized.append(item)
        control = tuple(row[k] for k in ('environment_id', 'acceptance_id', 'input_id')) + (parent[0]['model'], parent[0]['effort'])
        if controls.setdefault(row['task_id'], control) != control:
            raise ValueError('frozen task controls differ between trials')
        key = (row['task_id'], row['trial_id'])
        group = groups.setdefault(key, {})
        if row['variant'] in group: raise ValueError('duplicate task/trial variant')
        group[row['variant']] = (row, parent[0])
    for key, group in groups.items():
        if set(group) != set(PAIRED_VARIANTS): raise ValueError(f'complete off/on pair required: {key}')
        a, pa = group['off']; b, pb = group['on']
        if any(a[k] != b[k] for k in ('environment_id', 'acceptance_id', 'input_id')):
            raise ValueError(f'input/environment/acceptance differ: {key}')
        if any(pa[k] != pb[k] for k in ('model', 'effort')):
            raise ValueError(f'actual parent model/effort differ: {key}')
        if {a.get('run_order'), b.get('run_order')} != {1, 2}:
            raise ValueError('paired run_order must be a permutation of 1,2')
    quality = all(row['outcome'] == 'pass' for row in rows)
    sampling = len(controls) >= 3 and all(n >= 3 for n in Counter(task for task, _ in groups).values()) and all(row.get('randomized_order') is True for row in rows)
    for task in controls:
        orders = [pair['off'][0]['run_order'] for (task_id, _), pair in groups.items() if task_id == task]
        sampling = sampling and abs(orders.count(1) - orders.count(2)) <= 1
    accounting = all(r['calls_complete'] and r['all_pairs_observed'] for r in normalized)
    boundaries = all(all(v == 0 for v in r['violations'].values()) for r in normalized)
    measurements = {}
    for metric in normalized[0]['metrics']:
        complete = all(r['metrics'][metric] is not None for r in normalized)
        if metric == 'monetary_cost' and len({r['currency'] for r in normalized}) != 1: complete = False
        if not complete:
            measurements[metric] = {'status': 'UNKNOWN'}
            continue
        totals = {v: sum(r['metrics'][metric] for r in normalized if r['variant'] == v) for v in PAIRED_VARIANTS}
        status = 'measured'
        if metric == 'monetary_cost':
            status = 'actual' if all(r['price_status'] == 'actual' for r in normalized) else 'rate-card-estimate'
        measurements[metric] = {'status': status, **totals,
            'reduction_fraction': None if totals['off'] == 0 else 1 - totals['on'] / totals['off']}
    ready = quality and sampling and accounting and boundaries
    eligibility = {k: ready and measurements[k]['status'] in ('measured', 'actual')
                   for k in ('total_tokens', 'elapsed_seconds', 'monetary_cost')}
    return {'schema': 4, 'matched_trials': len(groups), 'quality_status': 'pass' if quality else 'incomplete',
            'formal_sampling_ready': sampling, 'accounting_complete': accounting, 'claim_eligibility': eligibility,
            'efficiency_claim_eligible': eligibility['total_tokens'] and eligibility['elapsed_seconds'],
            'measurements': measurements, 'runs': normalized,
            'limitation': 'Descriptive off/on trials; isolation evidence is supplied, not live host attestation. Missing money is UNKNOWN; rate cards are not subscription charges.'}
