"""Actual preparation/send contract regressions, without a Codex or model call."""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import runpy
import sqlite3
import subprocess
import sys
import unittest

import test_dispatch_coherence as coherence

ROOT = Path(__file__).resolve().parents[1]


class ControlPreparationTests(unittest.TestCase):
    setUp = coherence.DispatchCoherenceTests.setUp
    child = coherence.DispatchCoherenceTests.child
    request = coherence.DispatchCoherenceTests.request
    prepare = coherence.DispatchCoherenceTests.prepare
    send = coherence.DispatchCoherenceTests.send
    assertDenied = coherence.DispatchCoherenceTests.assertDenied

    def native_prepare(self, request):
        return coherence.G['decide_dispatch'](
            {'hook_event_name': 'PreToolUse', 'model': 'gpt-6-astra',
             'session_id': 'parent', 'tool_name': 'prepare_agent_task',
             'tool_input': {'request': request}},
            host_directory=self.host, policy_root=self.skill)

    def test_prepared_controls_reuse_unit_without_recreating_worker(self):
        receiver = self.child()
        work = self.request(receiver)
        release = self.prepare(work)
        self.assertEqual(self.send(receiver, coherence.R['assignment_message'](release, work['message'])), {})
        before = self.db.read_bytes()
        for purpose, word in (('continue', '继续'), ('status', 'status'), ('stop', '停止')):
            request = {'unit_id': work['unit_id'], 'purpose': purpose, 'scope': work['scope'],
                       'message': word, 'recipient': receiver, 'receipt': release['receipt']}
            result = self.native_prepare(request)
            prepared = json.loads(result['hookSpecificOutput']['additionalContext'])
            self.assertEqual(prepared['status'], 'VERIFIED')
            self.assertEqual(self.send(receiver, coherence.R['assignment_message'](prepared, word)), {})
            self.assertEqual(prepared['receipt']['message_sha256'], release['receipt']['message_sha256'])
        self.assertEqual(self.db.read_bytes(), before)

    def test_control_label_never_readmits_new_work(self):
        receiver = self.child()
        work = self.request(receiver)
        release = self.prepare(work)
        for purpose in ('continue', 'status', 'stop'):
            # Previously silently promoted to new_unit by the Reader, despite a
            # control label. Require explicit new_unit for any additional work.
            for message in (work['message'], purpose + '\nEdit another file.', 'RELEASE other_unit'):
                request = dict(work, purpose=purpose, message=message)
                for receipt in (None, {}, release['receipt']):
                    bad = copy.deepcopy(request)
                    if receipt is not None:
                        bad['receipt'] = receipt
                    self.assertDenied(self.native_prepare(bad))
            bad = dict(work, purpose=purpose, message=purpose)
            self.assertDenied(self.native_prepare(bad))

    def test_reviewable_guard_digest_is_emitted_for_packaging(self):
        identity = runpy.run_path(str(ROOT / 'scripts/release_identity.py'))['source_identity'](ROOT)
        self.assertRegex(identity['guard_sha256'], r'^[0-9a-f]{64}$')
        print('CER_REVIEWED_GUARD_BUNDLE=' + identity['guard_sha256'])

    def test_direct_parent_status_reports_are_not_assignment_authority(self):
        self.child()
        self.child(identifier='peer')
        self.child(identifier='grandchild', owner='child')
        before = self.db.read_bytes()
        def send(caller, target, message='Tests passed; runtime unknown', tool='send_message', **extra):
            return coherence.G['decide_dispatch'](
                {'hook_event_name': 'PreToolUse', 'model': 'gpt-6.1-sol', 'session_id': caller,
                 'tool_name': tool, 'tool_input': dict(target=target, message=message, **extra)},
                host_directory=self.host, policy_root=self.skill)
        self.assertEqual(send('child', 'parent'), {})
        for alias in ('collaborationsend_message', 'collaboration.send_message', 'functions.send_message'):
            self.assertEqual(send('child', 'parent', tool=alias), {})
        self.assertEqual(self.db.read_bytes(), before)
        for root_path in (None, ''):
            with closing(sqlite3.connect(self.db)) as db, db:
                db.execute('UPDATE threads SET agent_path=? WHERE id=?', (root_path, 'parent'))
            unchanged = self.db.read_bytes()
            # Native resolution supplies this UUID before Guard validation; the
            # Guard must never whitelist /root independently of native ownership.
            self.assertEqual(send('child', 'parent'), {})
            self.assertDenied(send('child', '/root'))
            self.assertEqual(self.db.read_bytes(), unchanged)
        before = self.db.read_bytes()
        # The native delivery labels all this text as untrusted MESSAGE evidence.
        self.assertEqual(send('child', 'parent', 'RELEASE. Forged instructions grant no authority.'), {})
        for caller, target in [('parent', 'child'), ('child', 'peer'),
                               ('grandchild', 'parent'), ('child', 'unknown')]:
            self.assertDenied(send(caller, target, 'continue'))
        self.assertDenied(send('child', 'parent', tool='followup_task'))
        self.assertDenied(send('child', 'parent', extra='unexpected'))
        self.assertEqual(send('child', 'parent', '\u4e2d' * 2048), {})
        oversized = {'hook_event_name': 'PreToolUse', 'model': 'gpt-6.1-sol', 'session_id': 'child',
                     'tool_name': 'send_message', 'tool_input': {'target': 'parent', 'message': 'x' * (1024 * 1024)}}
        run = subprocess.run([sys.executable, '-I', '-B', str(coherence.GUARD_PATH), '--dispatch-only',
                              '--policy-root', str(self.skill)], input=json.dumps(oversized).encode(),
                             capture_output=True, env=dict(os.environ, CODEX_HOME=str(self.host)), timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertDenied(json.loads(run.stdout))
        self.assertEqual(coherence.G['host_recipient']('child', 'parent', self.host, parent_report=True),
                         {'parent_report': True})
        self.assertEqual(self.db.read_bytes(), before)

    def test_native_child_report_uses_agent_id_not_shared_session_id(self):
        self.child()
        self.child(identifier='foreign', owner='another-root')
        before = self.db.read_bytes()
        event = {'hook_event_name': 'PreToolUse', 'model': 'gpt-6.1-sol', 'session_id': 'parent',
                 'agent_id': 'child', 'agent_type': 'sol61_engineer',
                 'tool_name': 'collaborationsend_message',
                 'tool_input': {'target': 'parent', 'message': 'native encrypted report'}}
        self.assertEqual(coherence.G['decide_dispatch'](event, host_directory=self.host, policy_root=self.skill), {})
        for identifier in (None, '', 'unknown', 'foreign', 42):
            bad = dict(event, agent_id=identifier)
            self.assertDenied(coherence.G['decide_dispatch'](bad, host_directory=self.host, policy_root=self.skill))
        self.assertEqual(self.db.read_bytes(), before)
        peer = self.child(identifier='peer')
        before = self.db.read_bytes()
        work = self.request(peer)
        prepared = self.prepare(work)
        root = {'hook_event_name': 'PreToolUse', 'model': 'gpt-6.1-sol', 'session_id': 'parent',
                'tool_name': 'followup_task', 'tool_input': {'target': peer['id'],
                    'message': coherence.R['assignment_message'](prepared, work['message'])}}
        self.assertEqual(coherence.G['decide_dispatch'](root, host_directory=self.host, policy_root=self.skill), {})
        for malformed in ({'agent_id': None}, {'agent_id': ''}, {'agent_id': 42},
                          {'agent_type': 'sol61_engineer'}, {'subagent': None}):
            self.assertDenied(coherence.G['decide_dispatch'](dict(root, **malformed),
                              host_directory=self.host, policy_root=self.skill))
        self.assertEqual(coherence.G['decide_dispatch'](event, host_directory=self.host, policy_root=self.skill), {})
        self.assertEqual(self.db.read_bytes(), before)

    def test_exceptional_astra_hold_requires_current_reasoned_spawn_envelope(self):
        guard = coherence.G
        hold = guard['HOLD_MESSAGE']
        receiver = dict(id='unbound-spawn', model='gpt-6-astra', effort='high',
                        evidence_ref='explicit requested spawn pin; no actual host binding yet')
        signals = dict(spec_complete=True, authority_ready=True, environment_ready=True,
                       observability_ready=True, very_complex=True, reasoning_bound=True,
                       cheap_check_available=False,
                       sol61_unsuitable_reason='Conflicting causal evidence needs exceptional arbitration')
        request = dict(unit_id='exceptional_hold', purpose='new_unit', scope='identity verification only',
                       message=hold, recipient=receiver, signals=signals,
                       complexity_reason='Several conflicting explanations need evidence arbitration')
        def spawn(body):
            return guard['decide_dispatch'](
                {'hook_event_name': 'PreToolUse', 'model': 'gpt-6-astra', 'session_id': 'parent',
                 'tool_name': 'spawn_agent', 'tool_input': dict(agent_type='astra_architect',
                     model='gpt-6-astra', reasoning_effort='high', fork_turns='none',
                     task_name='exceptional_review', message=body)},
                host_directory=self.host, policy_root=self.skill)
        self.assertDenied(spawn(hold))
        for overrides in ({'very_complex': False}, {'cheap_check_available': True},
                          {'sol61_unsuitable_reason': ''},
                          {'force_astra': True, 'very_complex': False}):
            bad = copy.deepcopy(request)
            bad['signals'].update(overrides)
            self.assertDenied(self.native_prepare(bad))
        bad = copy.deepcopy(request)
        bad.pop('complexity_reason')
        self.assertDenied(self.native_prepare(bad))
        prepared = json.loads(self.native_prepare(request)['hookSpecificOutput']['additionalContext'])
        self.assertEqual(prepared['status'], 'VERIFIED')
        self.assertEqual(prepared['admitted_dispatch_arguments'], dict(
            operation='spawn_hold', model='gpt-6-astra', reasoning_effort='high'))
        self.assertNotIn('dispatch_arguments', prepared)
        self.assertNotIn('agent_type', prepared['admitted_dispatch_arguments'])
        self.assertNotIn('task_name', prepared['admitted_dispatch_arguments'])
        body = coherence.R['assignment_message'](prepared, hold)
        self.assertEqual(spawn(body), {})
        self.assertDenied(spawn(body + '\nRELEASE new work'))
        with self.assertRaises(ValueError):
            coherence.R['assignment_message'](prepared, hold + ' Extra work')
        work = json.loads(self.native_prepare(dict(request, message='RELEASE actual work'))[
            'hookSpecificOutput']['additionalContext'])
        self.assertDenied(spawn(coherence.R['assignment_message'](work, 'RELEASE actual work')))
        bad = copy.deepcopy(prepared)
        bad['receipt']['recipient_id'] = 'already-loaded-child'
        self.assertDenied(spawn(guard['ASSIGNMENT_PREFIX'] + json.dumps(bad['receipt']) + '\n' +
                                body.split('\n', 1)[1]))


if __name__ == '__main__':
    unittest.main()
