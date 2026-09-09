"""Read-only offline evaluation. NO model inference, secrets, or production changes."""
from __future__ import annotations
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
TARGET = '7111d7d2b83f330c9f0e693a74fe97c5ea4dec1b'
BASE = 'e92d89a79c05985980420a0bfd6a51baec93ba81'
OUT = ROOT / 'evaluation-results'
SKILL = 'skills/codex-efficiency-router/SKILL.md'
sys.path.insert(0, str(ROOT / 'scripts'))


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, encoding='utf-8')


def text_at(ref: str, path: str) -> str:
    return git('show', f'{ref}:{path}')


def unit_suite() -> dict:
    stream = io.StringIO()
    started = time.perf_counter()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    (OUT / 'unittest.log').write_text(stream.getvalue(), encoding='utf-8')
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                skipped=len(result.skipped), passed=result.wasSuccessful(),
                elapsed_seconds=round(time.perf_counter() - started, 3),
                routing_scenarios=len(json.loads((ROOT / 'tests/cases.json').read_text())))


def token_measurements() -> dict:
    import tiktoken
    old, core = text_at(BASE, SKILL), text_at(TARGET, SKILL)
    prefix = 'skills/codex-efficiency-router/'
    routing = text_at(TARGET, prefix + 'references/routing.md')
    dispatch = text_at(TARGET, prefix + 'references/dispatch.md')
    text = {'v01_core': old, 'v02_core': core,
            'v02_core_plus_dispatch': core + '\n' + dispatch,
            'v02_core_plus_both_references': core + '\n' + routing + '\n' + dispatch}
    def description(s):
        return s.split('description: ', 1)[1].split('\n', 1)[0]
    text['v01_description'] = description(old)
    text['v02_description'] = description(core)
    for stem in ['luna-worker', 'terra-executor', 'sol-engineer', 'astra-architect']:
        data = tomllib.loads(text_at(TARGET, f'agents/{stem}.toml'))
        text[f'v02_{stem}_instructions'] = data['developer_instructions']
    measurements = {}
    for encoding in ['o200k_base', 'cl100k_base']:
        enc = tiktoken.get_encoding(encoding)
        measurements[encoding] = {name: {'tokens': len(enc.encode(s, disallowed_special=())),
                                         'bytes': len(s.encode('utf-8'))} for name, s in text.items()}
    mappings = {}
    for model in ['gpt-6-astra', 'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna']:
        try:
            mappings[model] = tiktoken.encoding_for_model(model).name
        except KeyError:
            mappings[model] = 'UNKNOWN_IN_PINNED_TIKTOKEN'
    return {'tiktoken_version': importlib.metadata.version('tiktoken'), 'model_mappings': mappings,
            'counts': measurements,
            'scope': 'Exact raw-text counts for named reference encodings; NOT live model billing or full host context.',
            'live_total_tokens': None, 'live_expensive_model_tokens': None, 'live_task_elapsed_seconds': None}


def holdout_checks() -> list[dict]:
    from policy_reference import TaskSignals as S, choose_lane, choose_dispatch as D
    observations = []
    def check(name, expected, actual, interpretation='policy boundary'):
        observations.append(dict(name=name, expected=expected, actual=actual,
                                 passed=(expected == actual), interpretation=interpretation))
    check('known work with inadequate verification is not mechanical lane', 'terra',
          choose_lane(S(mechanical=True, uncertainty=0, risk=1, verifiability=0)))
    check('settled but coupled implementation retains Sol', 'sol',
          choose_lane(S(prior_lane='astra', uncertainty=0, coupling=3, risk=1, verifiability=3)))
    check('explicit Astra cost override can bypass cheap-check preference', 'astra',
          choose_lane(S(force_astra=True, cheap_check_available=True)))
    check('no-escalation still permits justified downward handoff', 'delegate',
          D(S(), current_lane='astra', current_sufficient=True, no_escalation=True,
            benefit_clear=True, host_supports_routing=True, available_lanes=('terra',)).action)
    check('already sufficient Astra plus no-subagents stays local', 'local',
          D(S(force_astra=True, no_subagents=True), current_lane='astra', current_sufficient=True).action)
    check('multiple cheap-lane failures need not jump to Astra', 'terra',
          choose_lane(S(prior_lane='luna', capability_failure=True, failed_attempts=20)))
    check('nonreasoning blocker cannot automatically select Astra', False,
          choose_lane(S(reasoning_bound=False, uncertainty=3, risk=3, novelty=3,
                        evidence_conflict=True, prior_lane='sol', capability_failure=True, failed_attempts=2)) == 'astra')
    check('same model insufficient with no declared isolation benefit must not blindly redelegate', 'blocked',
          D(S(uncertainty=2, risk=1), current_lane='sol', current_sufficient=False,
            benefit_clear=False, host_supports_routing=True, available_lanes=('sol',)).action,
          'New proposed invariant from SKILL: same-model delegation needs a concrete isolation/review benefit; offline helper only.')
    return observations


def mutation_checks() -> list[dict]:
    original = (ROOT / 'scripts/policy_reference.py').read_text(encoding='utf-8')
    mutations = [
        ('always_astra', '    s.validate()\n', "    s.validate()\n    return 'astra'\n"),
        ('always_terra', '    s.validate()\n', "    s.validate()\n    return 'terra'\n"),
        ('ignore_prerequisites', 'if not (s.spec_complete and s.authority_ready and s.environment_ready and s.observability_ready):', 'if False:'),
        ('skip_discriminating_check', 'if s.cheap_check_available:', 'if False:'),
        ('ignore_forced_astra', 'if s.force_astra:', 'if False:'),
        ('ignore_no_subagents', 'forbidden = s.no_subagents or ', 'forbidden = False or '),
        ('ignore_no_escalation', '(no_escalation and LANES.index(lane) > LANES.index(current_lane))', 'False'),
        ('skip_benefit_gate', 'if current_sufficient and not s.force_astra and not benefit_clear:', 'if False:'),
        ('unsafe_unavailable_fallback', 'return result("blocked", "no verified sufficient route; do not silently downgrade")', 'return result("local", "MUTANT unsafe fallback")'),
        ('wrong_mechanical_lane', '        return "luna"\n', '        return "terra"\n'),
    ]
    harness = '''import sys, types, unittest
m = types.ModuleType("policy_reference")
sys.modules[m.__name__] = m
exec(compile(sys.stdin.read(), "<mutation>", "exec"), m.__dict__)
suite = unittest.defaultTestLoader.discover("tests", pattern="test_policy.py")
result = unittest.TextTestRunner(verbosity=0).run(suite)
if result.errors: sys.exit(2)
sys.exit(0 if result.wasSuccessful() else 1)
'''
    output = []
    for name, old, new in mutations:
        if old not in original:
            output.append(dict(name=name, outcome='INVALID_MUTATION'))
            continue
        changed = original.replace(old, new, 1)
        compile(changed, '<mutation>', 'exec')
        try:
            run = subprocess.run([sys.executable, '-c', harness], input=changed, cwd=ROOT,
                                 text=True, encoding='utf-8', capture_output=True, timeout=30)
            (OUT / f'mutation-{name}.log').write_text(run.stdout + run.stderr, encoding='utf-8')
            status = {0: 'SURVIVED', 1: 'KILLED', 2: 'TEST_ERROR'}.get(run.returncode, 'RUNNER_ERROR')
        except subprocess.TimeoutExpired:
            status = 'TIMEOUT'
        output.append(dict(name=name, outcome=status))
    return output


def main() -> int:
    OUT.mkdir(exist_ok=True)
    git('diff', '--exit-code', TARGET, 'HEAD', '--', 'scripts', 'tests', 'skills', 'agents', 'policy')
    report = {'target_commit': TARGET, 'historical_baseline_commit': BASE,
              'evaluation_commit': git('rev-parse', 'HEAD').strip(),
              'live_model_evaluation': 'NOT RUN: this workflow requests no model credentials or API calls',
              'unit_suite': unit_suite(), 'holdout_checks': holdout_checks(),
              'mutations': mutation_checks(), 'text_token_measurements': token_measurements()}
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('EVALUATION_REPORT_BEGIN')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print('EVALUATION_REPORT_END')
    if not report['unit_suite']['passed']:
        return 1
    if any(not check['passed'] for check in report['holdout_checks']):
        return 1
    if any(m['outcome'] != 'KILLED' for m in report['mutations']):
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
