"""Positive routing-to-native-admission flows, not live Codex model benchmarks.

Use the real preparation and guard functions with a temporary host identity DB.
Every allowed example also has a contradictory-identity or authority control.
"""
from pathlib import Path
import copy
import json
import runpy
import sys
import unittest

import test_native_write_guard as fixtures

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from package import EXPECTED
from effort_reference import MODEL_LANES


class DispatchContractTests(unittest.TestCase):
    setUp = fixtures.NativeDispatchTests.setUp
    connect = fixtures.NativeDispatchTests.connect
    row = fixtures.NativeDispatchTests.row
    request = fixtures.NativeDispatchTests.request
    text = fixtures.NativeDispatchTests.text
    hook = fixtures.NativeDispatchTests.hook
    denied = fixtures.NativeDispatchTests.denied

    def test_registry_agrees_with_all_shipped_roles_and_reference_lanes(self):
        self.assertEqual(self.reader['SPAWN_ROLES'],
                         {role: (model, effort) for role, model, effort in EXPECTED.values()})
        self.assertEqual(self.reader['MODEL_LANES'], MODEL_LANES)
        guard = fixtures.MODULE['reader_policy']()
        self.assertEqual(guard['SPAWN_ROLES'], self.reader['SPAWN_ROLES'])
        self.assertEqual(guard['MODEL_LANES'], MODEL_LANES)

    def test_every_shipped_executor_can_hold_bind_release_and_continue_owned_work(self):
        for role, model, fixed_effort in EXPECTED.values():
            if role == 'astra_architect':
                continue
            for automatic in (False, True):
                with self.subTest(role=role, automatic=automatic):
                    name = ('cer_auto_' if automatic else '') + role
                    spawn = {'agent_type': name, 'fork_turns': 'none',
                             'message': fixtures.MODULE['HOLD_MESSAGE']}
                    if automatic:
                        spawn['reasoning_effort'] = fixed_effort
                    self.assertEqual(self.hook(name='spawn_agent', data=spawn), {})
                    # Host observation is supplied by the fixture, not inferred from spawn args.
                    worker = name
                    self.row(worker, model, 'parent', '/root/' + worker, effort=fixed_effort)
                    request = self.request(worker, model, confirmed_simple=True)
                    request['recipient']['effort'] = fixed_effort
                    request['signals'].update(uncertainty=0, risk=1, coupling=0, novelty=0,
                                              mechanical=True, verifiability=3)
                    execution = {'effects': ['write', 'test'], 'permission': 'workspace-write',
                                 'role_read_only': False, 'parent_released': True}
                    for work in ('RELEASE current unit. Implement the owned fixture and validate it.',
                                 'Fix the reported edge case within the same owned fixture; rerun its check.'):
                        request['message'] = self.reader['EXECUTION_PREFIX'] + json.dumps(execution) + '\n' + work
                        prepared = self.text(request)
                        self.assertEqual(self.hook(target=worker, text=prepared), {})
                    with self.connect() as db:
                        db.execute('UPDATE threads SET model=? WHERE id=?', ('UNKNOWN', worker))
                    self.denied(self.hook(target=worker, text=prepared))

    def test_creation_medium_does_not_require_fake_engineering_admission(self):
        for role in ('cer_auto_sol61_engineer', 'cer_auto_terra_executor', 'cer_auto_luna_worker'):
            data = {'agent_type': role, 'reasoning_effort': 'medium', 'fork_context': False,
                    'message': fixtures.MODULE['HOLD_MESSAGE']}
            self.assertEqual(self.hook(name='spawn_agent', data=data), {})
            self.denied(self.hook(name='spawn_agent', data=dict(data, message='Write now.')))

    def test_cheaper_executor_cannot_take_unresolved_high_risk_work(self):
        for model in ('gpt-6-luna', 'gpt-5.6-luna', 'gpt-5.6-terra'):
            request = self.request(model=model, confirmed_simple=True)
            for signal in ('risk', 'coupling', 'uncertainty'):
                changed = copy.deepcopy(request)
                changed['signals'][signal] = 3
                result = self.reader['assignment_preflight'](changed)
                self.assertEqual(result['status'], 'MISMATCH')
                self.assertNotIn('dispatch_arguments', result)

    def test_low_needs_owned_opt_in_and_full_deterministic_evidence(self):
        request = self.request(model='gpt-6-luna', confirmed_simple=True)
        request['recipient']['effort'] = 'low'
        request['signals'].update(mechanical=True, uncertainty=0, novelty=0, verifiability=3)
        self.assertEqual(self.reader['assignment_preflight'](request)['status'], 'MISMATCH')
        self.assertEqual(self.reader['assignment_preflight'](request, allow_low=True)['status'], 'VERIFIED')
        for key in ('mechanical', 'uncertainty', 'novelty', 'verifiability'):
            bad = copy.deepcopy(request)
            del bad['signals'][key]
            self.assertNotEqual(self.reader['assignment_preflight'](bad, allow_low=True)['status'], 'VERIFIED')
        self.assertFalse(self.reader['supported_admission_pair']('gpt-6-luna', 'ultra'))
        self.assertFalse(self.reader['supported_admission_pair']('gpt-5.6-terra', 'ultra'))

    def test_status_wait_and_cancel_use_native_controls_not_task_inference(self):
        # These native controls carry no work and need no preparation call.
        # Raw textual 'continue' remains denied: a caller-made receipt isn't trusted release state.
        for name in ('wait', 'wait_agent', 'interrupt_agent', 'close_agent'):
            self.assertEqual(self.hook(name=name, data={'id': 'sol'}), {})
        for text in ('continue', 'status', 'stop', '继续'):
            self.denied(self.hook(text=text))

    def test_cheap_models_still_cannot_mutate_under_readonly_or_unreleased_declarations(self):
        for model in ('gpt-6-luna', 'gpt-5.6-terra', 'gpt-6-sol', 'gpt-6.1-sol'):
            request = self.request(model=model, confirmed_simple=True)
            for permission, readonly, released in (('read-only', False, True),
                                                   ('workspace-write', True, True),
                                                   ('workspace-write', False, False)):
                execution = dict(effects=['write'], permission=permission,
                                 role_read_only=readonly, parent_released=released)
                request['message'] = self.reader['EXECUTION_PREFIX'] + json.dumps(execution) + '\nUpdate fixture'
                self.assertNotEqual(self.reader['assignment_preflight'](request)['status'], 'VERIFIED')

    def test_strict_signals_do_not_accept_string_booleans_or_nonfinite_scores(self):
        for key, value in (('risk', True), ('novelty', -1), ('coupling', float('nan')),
                           ('authority_ready', 'true'), ('mechanical', 1), ('failed_attempts', -1)):
            request = self.request(confirmed_simple=True)
            request['signals'][key] = value
            self.assertEqual(self.reader['assignment_preflight'](request)['status'], 'UNKNOWN')


class PackageClosureTests(unittest.TestCase):
    def test_pinned_host_source_is_present_with_exact_bytes(self):
        from release_package import source_payload
        payload = source_payload(ROOT)
        path = 'host/required-agent-admission.patch'
        self.assertEqual(payload[path], (ROOT / path).read_bytes())
        self.assertFalse(any(p.endswith(('.exe', '.dll', '.pdb')) for p in payload))


if __name__ == '__main__':
    unittest.main()
