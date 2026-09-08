"""Read-only offline evaluation. NO model inference, secrets, or production changes."""
from __future__ import annotations
import argparse
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

from effort_mutations import run_mutations

ROOT = Path(__file__).resolve().parents[1]
V021_TREE = 'ed032b3554f768398dbb14795e633b5c2cead54f'  # verified remote v0.2.1 tree
PREVIOUS = '7111d7d2b83f330c9f0e693a74fe97c5ea4dec1b'
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
    if importlib.metadata.version('tiktoken') != '0.11.0':
        raise ValueError('This audit requires tiktoken==0.11.0 for reproducible text counts')
    old, previous = text_at(BASE, SKILL), text_at(PREVIOUS, SKILL)
    core = (ROOT / SKILL).read_text(encoding='utf-8')
    prefix = 'skills/codex-efficiency-router/'
    routing = (ROOT / prefix / 'references/routing.md').read_text(encoding='utf-8')
    dispatch = (ROOT / prefix / 'references/dispatch.md').read_text(encoding='utf-8')
    references = [p.read_text(encoding='utf-8') for p in sorted((ROOT / prefix / 'references').rglob('*.md'))]
    text = {'v01_core': old, 'v02_core': previous, 'current_core': core,
            'v02_full': previous + '\n' + text_at(PREVIOUS, prefix + 'references/routing.md')
                        + '\n' + text_at(PREVIOUS, prefix + 'references/dispatch.md'),
            'current_core_plus_dispatch': core + '\n' + dispatch,
            'current_full': core + ''.join('\n' + reference for reference in references)}
    from profiles import MARKER, Profile
    text['adaptive_core'] = MARKER.sub(Profile('adaptive').marker, core)
    text['adaptive_full'] = text['adaptive_core'] + ''.join('\n' + reference for reference in references)
    text['auto_core'] = MARKER.sub(Profile('auto').marker, core)
    text['auto_full'] = text['auto_core'] + ''.join('\n' + reference for reference in references)
    # A declared rendering for relative metadata accounting, not exact host framing.
    aliases = []
    for source in sorted((ROOT / 'agents').glob('*.toml')):
        definition = tomllib.loads(source.read_text(encoding='utf-8'))
        aliases.append('cer_auto_' + definition['name'] + ': ' + definition['description'])
    text['auto_extra_discovery_text'] = '\n'.join(aliases)
    def description(s):
        return s.split('description: ', 1)[1].split('\n', 1)[0]
    text['v021_core'] = text_at(V021_TREE, SKILL)
    text['v021_full'] = text['v021_core'] + '\n' + text_at(V021_TREE, prefix + 'references/dispatch.md') + '\n' + text_at(V021_TREE, prefix + 'references/routing.md')
    text['v01_description'] = description(old)
    text['current_description'] = description(core)
    for stem in ['luna-worker', 'terra-executor', 'sol-engineer', 'astra-architect']:
        data = tomllib.loads((ROOT / f'agents/{stem}.toml').read_text(encoding='utf-8'))
        text[f'current_{stem}_instructions'] = data['developer_instructions']
        text[f'v021_{stem}_instructions'] = tomllib.loads(text_at(V021_TREE, f'agents/{stem}.toml'))['developer_instructions']
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
            'budget_pass': all(max(v['current_core']['tokens'], v['adaptive_core']['tokens'], v['auto_core']['tokens']) <= v['v021_core']['tokens']
                               and max(v['current_full']['tokens'], v['adaptive_full']['tokens'], v['auto_full']['tokens']) <= v['v021_full']['tokens']
                               and all(max(v['current_full']['tokens'], v['adaptive_full']['tokens'], v['auto_full']['tokens']) + v[f'current_{role}_instructions']['tokens']
                                       <= v['v021_full']['tokens'] + v[f'v021_{role}_instructions']['tokens']
                                       for role in ('luna-worker', 'terra-executor', 'sol-engineer', 'astra-architect'))
                               for v in measurements.values()),
            'auto_with_discovery_budget_pass': all(
                v['auto_full']['tokens'] + v['auto_extra_discovery_text']['tokens'] <= v['v021_full']['tokens']
                for v in measurements.values()),
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
          'Retained historical failing invariant from SKILL: same-model delegation needs a concrete isolation/review benefit; offline helper only.')
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
        ('skip_same_lane_guard', 'if same_lane_reason == "none" or not benefit_clear:', 'if False:'),
        ('skip_insufficient_downgrade_guard', 'elif not current_sufficient and LANES.index(lane) < LANES.index(current_lane):', 'elif False:'),
    ]
    harness = '''import sys, types, unittest
m = types.ModuleType("policy_reference")
sys.modules[m.__name__] = m
exec(compile(sys.stdin.read(), "<mutation>", "exec"), m.__dict__)
suite = unittest.defaultTestLoader.discover("tests", pattern="test_policy*.py")
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



def quality_mutation_checks() -> list[dict]:
    """Deliberately break one quality boundary; only assertion failures count."""
    source = (ROOT / 'scripts/quality_reference.py').read_text(encoding='utf-8')
    mutations = [
        ('false_completion', "return Completion('PARTIAL' if gaps else 'PASS', tuple(gaps))", "return Completion('PASS', tuple(gaps))"),
        ('ignore_missing_outcome', "gaps.append(f'{required}: missing evidence')", 'pass'),
        ('trust_self_claim', "elif item.kind == 'claim':", 'elif False:'),
        ('ignore_final_state', "elif item.contract_revision != contract.revision or item.state != contract.state:", 'elif False:'),
        ('ignore_blocker', '    if blocked:', '    if False:'),
        ('ignore_plan_conflict', 'if not complete or not aligned or not authorized:', 'if not complete or not authorized:'),
        ('reset_cross_worker_history', 'if attempt.key == key:', "if attempt.key == key and attempt.worker == 'new-worker-only':"),
        ('unknown_history_is_zero', 'if not history_known:', 'if False:'),
        ('ignore_exhaustion', 'if len(relevant) >= 2 + extension:', 'if False:'),
        ('blind_repeat_approach', 'if any(item.approach == next_approach for item in relevant) and not new_evidence.strip():', 'if False:'),
        ('replay_active_worker', "if worker_state == 'active':", 'if False:'),
        ('replay_unknown_effect', "if worker_state == 'unknown' or side_effect_state == 'unknown':", "if worker_state == 'unknown':"),
    ]
    harness = """import sys, types, unittest
m = types.ModuleType('quality_reference')
sys.modules[m.__name__] = m
exec(compile(sys.stdin.read(), '<quality-mutation>', 'exec'), m.__dict__)
r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.discover('tests', pattern='test_quality_protocol.py'))
sys.exit(2 if r.errors else 0 if r.wasSuccessful() else 1)
"""
    output = []
    for name, old, new in mutations:
        if source.count(old) != 1:
            output.append({'name': name, 'outcome': 'INVALID_MUTATION'})
            continue
        try:
            result = subprocess.run([sys.executable, '-c', harness], cwd=ROOT,
                                    input=source.replace(old, new, 1), text=True, encoding='utf-8',
                                    capture_output=True, timeout=30)
            (OUT / f'quality-mutation-{name}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            status = {0: 'SURVIVED', 1: 'KILLED', 2: 'TEST_ERROR'}.get(result.returncode, 'RUNNER_ERROR')
        except subprocess.TimeoutExpired:
            status = 'TIMEOUT'
        output.append({'name': name, 'outcome': status})
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--without-tokenizer', action='store_true',
                        help='run rule checks only; token measurements explicitly NOT RUN')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    report = {'previous_release_commit': PREVIOUS, 'historical_baseline_commit': BASE,
              'evaluation_commit': git('rev-parse', 'HEAD').strip(),
              'live_model_evaluation': 'NOT RUN: this workflow requests no model credentials or API calls',
              'unit_suite': unit_suite(), 'holdout_checks': holdout_checks(),
              'mutations': mutation_checks(), 'quality_mutations': quality_mutation_checks(),
              'effort_mutations': run_mutations(ROOT, OUT),
              'behavioral_acceptance': {'prepared_cases': len(json.loads((ROOT / 'evaluation/behavior_cases.json').read_text(encoding='utf-8'))['cases']), 'live_runs': 0, 'status': 'NOT RUN; structure checked only'},
              'text_token_measurements': ({'status': 'NOT RUN', 'budget_pass': None} if args.without_tokenizer else token_measurements()),
              'worktree_dirty': bool(git('status', '--porcelain').strip()),
              'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                               for folder in ('scripts', 'tests', 'skills', 'agents', 'policy', 'evaluation')
                               for p in sorted((ROOT / folder).rglob('*'))
                               if p.is_file() and '__pycache__' not in p.parts}}

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
    if any(m['outcome'] != 'KILLED' for m in report['quality_mutations']):
        return 1
    if any(m['outcome'] != 'KILLED' for m in report['effort_mutations']):
        return 1
    if report['text_token_measurements']['budget_pass'] is False:
        return 1
    if report['text_token_measurements'].get('auto_with_discovery_budget_pass') is False:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
