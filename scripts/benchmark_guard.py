#!/usr/bin/env python3
"""Explicit local subprocess microbenchmark; never calls Codex/models.

Measures process + guard/reader overhead, NOT native Codex end-to-end latency or
production savings. Temporary fixtures contain no user data and are cleaned up.
"""
from __future__ import annotations
import argparse
import base64
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from statistics import mean
from compare_v2 import percentile
from release_identity import ROOT, source_identity


def summary(values):
    return {'samples': len(values), 'p50_ms': percentile(values, .5),
            'p95_ms': percentile(values, .95), 'mean_ms': mean(values)}


def bench(iterations=30):
    if type(iterations) is not int or not 3 <= iterations <= 1000:
        raise ValueError('iterations must be 3..1000')
    identity = source_identity()
    guard = ROOT / 'hooks/astra_write_guard.py'; reader = ROOT / 'hooks/readonly_reader.py'
    samples = {key: [] for key in ('guard_deny', 'guard_passthrough', 'guard_read_rewrite', 'reader_four_processes', 'reader_one_batch')}
    with tempfile.TemporaryDirectory(prefix='cer-benchmark-') as tmp:
        root = Path(tmp)
        (root / 'fixture.txt').write_text('Owner\n' * 120, encoding='utf-8')
        req = {'op': 'read', 'path': 'fixture.txt', 'lines': 20}
        def read_args(request):
            encoded = base64.urlsafe_b64encode(json.dumps(request).encode()).decode()
            return [sys.executable, '-I', '-B', str(reader), str(root), encoded]
        events = {
            'guard_deny': {'model': 'gpt-6-astra', 'tool_name': 'apply_patch', 'tool_input': {}},
            'guard_passthrough': {'model': 'gpt-5.6-sol', 'tool_name': 'apply_patch', 'tool_input': {}},
            'guard_read_rewrite': {'model': 'gpt-6-astra', 'tool_name': 'Bash', 'tool_input': {'command': 'cer-read ' + json.dumps(req)}},
        }
        for index in range(iterations):
            # Rotate order to avoid always measuring the same phase first.
            order = list(samples); order = order[index % len(order):] + order[:index % len(order)]
            for key in order:
                start = time.perf_counter()
                if key.startswith('guard_'):
                    event = {'hook_event_name': 'PreToolUse', 'cwd': str(root), **events[key]}
                    p = subprocess.run([sys.executable, '-I', '-B', str(guard), '--expected-bundle', identity['guard_sha256']],
                                       input=json.dumps(event), capture_output=True, text=True, timeout=10, check=True)
                    decision = json.loads(p.stdout).get('hookSpecificOutput', {}).get('permissionDecision') if p.stdout else None
                    expected = {'guard_deny': 'deny', 'guard_passthrough': None, 'guard_read_rewrite': 'allow'}[key]
                    if decision != expected:
                        raise ValueError('guard benchmark behavior mismatch')
                else:
                    request = {'op': 'batch', 'requests': [req] * 4} if key == 'reader_one_batch' else req
                    for _ in range(1 if key == 'reader_one_batch' else 4):
                        subprocess.run(read_args(request), capture_output=True, text=True, check=True, timeout=15)
                samples[key].append((time.perf_counter() - start) * 1000)
    return {'schema': 1, 'evidence_kind': 'offline-subprocess-microbenchmark', 'identity': identity,
            'platform': platform.system(), 'python_version': platform.python_version(),
            'measurements': {key: summary(value) for key, value in samples.items()},
            'cold_start_included': True, 'live_codex_latency': 'UNKNOWN', 'model_cost': 'UNKNOWN'}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--iterations', type=int, default=30)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    try:
        result = json.dumps(bench(args.iterations), indent=2, allow_nan=False) + '\n'
        if args.output:
            from canary import write_new
            write_new(args.output, result.encode())
        print(result)
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f'benchmark: FAILED: {exc}', file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
