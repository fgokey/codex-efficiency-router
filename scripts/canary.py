#!/usr/bin/env python3
"""Explicit operator-witnessed native Canary preparation and evidence verification.

Does NOT start Codex or call models. The operator executes the prepared native
probes in the existing trusted Codex session, then supplies minimal observations.
A direct Python guard test is always synthetic, never evidence of host enforcement.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re
import subprocess
from uuid import uuid4

from manage import reject_links, read_bytes
from write_guard import inspect_status, loads, encode

OWNER = 'cer-native-canary'
SEED = b'CER read-only canary fixture\n'
WRITTEN = b'CER executor canary\n'
CASES = {
    'astra_patch_denied': ('apply_patch', 'deny'),
    'astra_shell_denied': ('Bash', 'deny'),
    'astra_read_allowed': ('read_file', 'success'),
    'astra_coordinate_allowed': ('update_plan', 'success'),
    'executor_write_allowed': ('apply_patch', 'success'),
}
FILES = ('plan.json', 'observations.json', 'read.txt', 'astra-patch.txt', 'astra-shell.txt', 'executor.txt')


def now():
    return datetime.now(timezone.utc)


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError('timestamp required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp must include timezone')
    return result


def write_new(path: Path, content: bytes):
    reject_links(path)
    with path.open('xb') as stream:
        stream.write(content)


def prepare(root: Path, scope='project') -> Path:
    reject_links(root)
    root = root.resolve(strict=True)
    status = inspect_status(scope, root if scope == 'project' else None)
    if status['registration'] != 'PRESENT':
        raise ValueError('Canary needs a current PRESENT guard; explicitly install/update and review it first')
    token = uuid4().hex
    run = root / ('.cer-canary-' + token)
    run.mkdir(mode=0o700)
    plan = {'owner': OWNER, 'schema': 1, 'run_id': token, 'workspace': str(root), 'scope': scope,
            'created_at': now().isoformat(), 'expires_at': (now() + timedelta(hours=2)).isoformat(),
            'fingerprint': status['fingerprint'], 'guard_sha256': status['guard_sha256'],
            'router_version': status['router']['version'], 'expected': CASES}
    observations = {'source': 'operator-witnessed-native', 'codex_version': None,
                    'reviewed_fingerprint': None, 'preexisting_exec_sessions': None,
                    'cases': {name: {'model': None, 'tool': tool, 'result': None,
                              'hook_invoked': None, 'guard_sha256': None,
                              'elapsed_ms': None} for name, (tool, _) in CASES.items()}}
    try:
        write_new(run / 'read.txt', SEED)
        write_new(run / 'plan.json', encode(plan))
        write_new(run / 'observations.json', encode(observations))
    except BaseException:
        for name in ('read.txt', 'plan.json', 'observations.json'):
            (run / name).unlink(missing_ok=True)
        run.rmdir()
        raise
    return run


def load_plan(run: Path):
    reject_links(run)
    plan = loads((run / 'plan.json').read_bytes())
    if not isinstance(plan, dict):
        raise ValueError('invalid Canary plan')
    token = plan.get('run_id')
    if (plan.get('owner') != OWNER or plan.get('schema') != 1
            or not isinstance(token, str) or not re.fullmatch(r'[0-9a-f]{32}', token)
            or run.name != '.cer-canary-' + token
            or Path(plan.get('workspace', '')).resolve() != run.resolve().parent
            or plan.get('scope') not in ('project', 'user')):
        raise ValueError('invalid Canary ownership/scope')
    return plan


def synthetic_unknown_check(guard: Path, root: Path) -> bool:
    for model in (None, 'unrecognized-model'):
        event = {'hook_event_name': 'PreToolUse', 'model': model, 'cwd': str(root),
                 'tool_name': 'apply_patch', 'tool_input': {'command': 'synthetic; never executed'}}
        result = subprocess.run([sys.executable, '-I', '-B', str(guard)], input=json.dumps(event),
                                capture_output=True, text=True, timeout=10)
        try:
            if result.returncode != 0 or loads(result.stdout)['hookSpecificOutput']['permissionDecision'] != 'deny':
                return False
        except (ValueError, KeyError, TypeError):
            return False
    return True


def verify(run: Path) -> dict:
    plan = load_plan(run)
    raw = read_bytes(run / 'observations.json')
    if raw is None or len(raw) > 32768:
        raise ValueError('missing/oversized observations')
    observed = loads(raw)
    allowed = {'source', 'codex_version', 'reviewed_fingerprint', 'preexisting_exec_sessions', 'cases'}
    if not isinstance(observed, dict) or set(observed) != allowed:
        raise ValueError('observation fields are strict; never include prompt, arguments, content or credentials')
    if observed['source'] != 'operator-witnessed-native':
        raise ValueError('synthetic/offline observations cannot establish native Canary success')
    version = observed['codex_version']
    if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9._+ -]{1,80}', version):
        raise ValueError('record the actual current Codex version')
    sessions = observed['preexisting_exec_sessions']
    if sessions is not None and type(sessions) is not bool:
        raise ValueError('preexisting_exec_sessions must be true/false/null')
    status = inspect_status(plan['scope'], run.parent if plan['scope'] == 'project' else None)
    stale = (now() > parse_time(plan['expires_at']) or status['registration'] != 'PRESENT'
             or status['fingerprint'] != plan['fingerprint']
             or status['guard_sha256'] != plan['guard_sha256'])
    reviews = observed['reviewed_fingerprint'] == plan['fingerprint']
    case_results = []
    cases = observed['cases']
    if not isinstance(cases, dict) or set(cases) != set(CASES):
        raise ValueError('all five native cases must be recorded exactly once')
    for name, (tool, expected) in CASES.items():
        item = cases[name]
        fields = {'model', 'tool', 'result', 'hook_invoked', 'guard_sha256', 'elapsed_ms'}
        if not isinstance(item, dict) or set(item) != fields:
            raise ValueError('case fields are strict; no raw tool arguments/results')
        if not isinstance(item['model'], str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,80}', item['model']):
            raise ValueError('record an actual model slug only')
        if item['result'] not in ('deny', 'success', 'failed', 'unknown'):
            raise ValueError('record a result enum, not tool output')
        if not isinstance(item['tool'], str) or not re.fullmatch(r'[A-Za-z0-9_]{1,80}', item['tool']):
            raise ValueError('record a canonical tool name only')
        if type(item['hook_invoked']) is not bool:
            raise ValueError('record whether the native hook was actually invoked')
        elapsed = item['elapsed_ms']
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError('record nonnegative measured elapsed_ms')
        models = ('gpt-5.6-sol', 'gpt-5.6-terra') if name.startswith('executor') else ('gpt-6-astra',)
        allowed_tools = ('read_file', 'Bash') if name == 'astra_read_allowed' else (tool,)
        passed = (item['model'] in models and item['tool'] in allowed_tools
                  and item['result'] == expected and item['hook_invoked'] is True
                  and item['guard_sha256'] == plan['guard_sha256'])
        case_results.append({'id': name, 'expected': expected, 'actual': item['result'],
                             'model': item['model'], 'tool': item['tool'], 'elapsed_ms': elapsed,
                             'hook_invoked': item['hook_invoked'] is True, 'pass': passed})
    filesystem = (read_bytes(run / 'read.txt') == SEED
                  and read_bytes(run / 'astra-patch.txt') is None
                  and read_bytes(run / 'astra-shell.txt') is None
                  and read_bytes(run / 'executor.txt') == WRITTEN)
    guard = Path(status['guard_directory']) / 'astra_write_guard.py'
    synthetic = False if stale else synthetic_unknown_check(guard, run.parent)
    complete = all(item['pass'] for item in case_results) and filesystem and synthetic and reviews
    result = 'STALE' if stale else 'FAIL' if not complete else 'UNKNOWN' if sessions is not False else 'PASS'
    return {'owner': OWNER, 'schema': 1, 'result': result, 'evidence_basis': observed['source'],
            'evidence_limitation': 'Operator-witnessed native runs; not authenticated host telemetry or OS isolation.',
            'run_id': plan['run_id'], 'created_at': now().isoformat(), 'expires_at': plan['expires_at'],
            'router_version': plan['router_version'], 'guard_sha256': plan['guard_sha256'],
            'fingerprint': plan['fingerprint'], 'codex_version': version,
            'review_attestation': 'CURRENT_HASH_REVIEWED' if reviews else 'UNKNOWN',
            'preexisting_exec_sessions': sessions, 'cases': case_results,
            'filesystem_checks': 'PASS' if filesystem else 'FAIL',
            'synthetic_unknown_model': 'PASS' if synthetic else 'FAIL',
            'coverage': {'write_stdin': 'UNPROTECTED', 'hosted_tools': 'UNPROTECTED',
                         'specialized_paths': 'UNKNOWN'}, 'cleanup': 'NOT_RUN'}


def cleanup(run: Path):
    load_plan(run)
    # Refuse recursive cleanup or unknown files; only the known fresh nonce directory.
    if any(p.name not in FILES or not p.is_file() or p.is_symlink() for p in run.iterdir()):
        raise ValueError('unexpected Canary files preserved; inspect manually')
    for name in FILES:
        reject_links(run / name)
    for name in FILES:
        (run / name).unlink(missing_ok=True)
    run.rmdir()


def evaluate_saved_report(status: dict, report: dict, codex_version=None) -> dict:
    out = dict(status)
    out['evidence_basis'] = report.get('evidence_basis') if isinstance(report, dict) else 'UNKNOWN'
    if (not isinstance(report, dict) or report.get('owner') != OWNER or report.get('schema') != 1
            or out['evidence_basis'] != 'operator-witnessed-native'):
        out['live_verification'] = 'NOT_RUN'
        return out
    if not codex_version:
        out['live_verification'] = 'UNKNOWN'
        out['warnings'] = [*out['warnings'], 'current Codex version unknown; cannot reuse prior Canary PASS']
        return out
    try:
        stale = (status['registration'] != 'PRESENT' or status['fingerprint'] != report.get('fingerprint')
                 or status['guard_sha256'] != report.get('guard_sha256')
                 or codex_version != report.get('codex_version') or now() > parse_time(report.get('expires_at')))
    except (ValueError, TypeError):
        stale = True
    result = report.get('result')
    out['live_verification'] = 'STALE' if stale else result if result in ('PASS', 'FAIL', 'UNKNOWN') else 'FAIL'
    # Recheck all evidence gates, rather than trusting a single JSON "PASS" field.
    if out['live_verification'] == 'PASS':
        items = report.get('cases', [])
        valid = (report.get('review_attestation') == 'CURRENT_HASH_REVIEWED'
                 and report.get('preexisting_exec_sessions') is False
                 and report.get('filesystem_checks') == 'PASS'
                 and report.get('synthetic_unknown_model') == 'PASS'
                 and report.get('cleanup') == 'PASS'
                 and isinstance(items, list) and len(items) == len(CASES)
                 and all(isinstance(i, dict) for i in items)
                 and {i.get('id') for i in items} == set(CASES)
                 and all(i.get('pass') is True and i.get('hook_invoked') is True for i in items))
        if valid:
            for item in items:
                name = item['id']; tool, expected = CASES[name]
                models = ('gpt-5.6-sol', 'gpt-5.6-terra') if name.startswith('executor') else ('gpt-6-astra',)
                tools = ('read_file', 'Bash') if name == 'astra_read_allowed' else (tool,)
                elapsed = item.get('elapsed_ms')
                valid = valid and (item.get('expected') == expected and item.get('actual') == expected
                                   and item.get('model') in models and item.get('tool') in tools
                                   and type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0)
        if valid:
            out['installation_mode'] = 'live-verified'
            out['review_attestation'] = 'CURRENT_HASH_REVIEWED'
            out['coverage'] = {**out['coverage'], 'native_hooked_paths': 'SCOPED_CANARY_PASS'}
        else:
            out['live_verification'] = 'FAIL'
    # Codex's persisted trust database and current task loading remain UNKNOWN.
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--project-root', type=Path, required=True)
    p.add_argument('--scope', choices=('user', 'project'), default='project')
    v = sub.add_parser('verify'); v.add_argument('--run-dir', type=Path, required=True)
    v.add_argument('--output', type=Path, required=True)
    c = sub.add_parser('cleanup'); c.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            run = prepare(args.project_root, args.scope)
            print(json.dumps({'run_dir': str(run), 'status': 'PREPARED_NOT_RUN',
                              'next': 'Read docs/CANARY.md; execute native probes explicitly, then fill observations.json.'}))
            return 0
        if args.action == 'cleanup':
            cleanup(args.run_dir); print('{"cleanup":"PASS"}'); return 0
        reject_links(args.output)
        if args.output.exists() or args.output.resolve().is_relative_to(args.run_dir.resolve()):
            raise ValueError('output must be a NEW report outside the Canary directory')
        if not args.output.parent.is_dir():
            raise ValueError('report parent must already exist')
        report = verify(args.run_dir)
        # Persist the result before cleanup, so an output failure cannot destroy
        # the only observations. An interrupted cleanup leaves NOT_RUN, not PASS.
        original = encode(report)
        write_new(args.output, original)
        cleanup(args.run_dir)
        report['cleanup'] = 'PASS'
        if read_bytes(args.output) != original:
            raise ValueError('report changed concurrently; preserved without overwrite')
        from manage import replace
        replace(args.output, encode(report))
        print(json.dumps(report, indent=2))
        return 0 if report['result'] == 'PASS' else 1
    except (ValueError, OSError, TypeError, subprocess.SubprocessError) as exc:
        print(f'Canary: FAILED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
