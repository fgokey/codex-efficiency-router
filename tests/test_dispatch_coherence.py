"""Positive end-to-end admission paths plus negative controls; no model inference.

Exercise the actual Reader, Hook, SQLite adapter and CLI subprocess with temporary
state only. This is not evidence that a desktop loaded or trusted these tools.
"""
from __future__ import annotations

import copy
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import runpy
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
READER_PATH = ROOT / 'hooks/readonly_reader.py'
GUARD_PATH = ROOT / 'hooks/astra_write_guard.py'
R = runpy.run_path(str(READER_PATH))
G = runpy.run_path(str(GUARD_PATH))


class DispatchCoherenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.host = self.root / 'native home 中文'
        self.host.mkdir()
        self.skill = self.root / 'skill'
        self.skill.mkdir()
        (self.skill / 'SKILL.md').write_text('test policy\n', encoding='utf-8')
        self.policy = R['assignment_policy_sha256'](self.skill)
        self.db = self.host / 'state_5.sqlite'
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('CREATE TABLE threads (id TEXT PRIMARY KEY, model TEXT, reasoning_effort TEXT, '
                       'source TEXT, thread_source TEXT, agent_role TEXT, agent_path TEXT, '
                       'archived INTEGER, rollout_path TEXT)')
            db.execute('INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)',
                       ('parent', 'gpt-6-astra', 'high', '{}', '', '', '', 0, ''))

    def child(self, model='gpt-6.1-sol', effort='high', identifier='child', owner='parent'):
        source = json.dumps({'subagent': {'thread_spawn': {'parent_thread_id': owner}}})
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('INSERT OR REPLACE INTO threads VALUES (?,?,?,?,?,?,?,?,?)',
                       (identifier, model, effort, source, '', '', identifier, 0, ''))
        return {'id': identifier, 'model': model, 'effort': effort, 'evidence_ref': 'temporary native row'}

    def request(self, receiver, *, simple=False):
        return {'unit_id': 'fix_1', 'purpose': 'new_unit', 'scope': 'src/example.py and its tests',
                'message': R['EXECUTION_PREFIX'] + json.dumps(
                    {'effects': ['read', 'write', 'test'], 'permission': 'workspace-write',
                     'role_read_only': False, 'parent_released': True}) + '\nRELEASE fix_1. Fix the bounded defect.',
                'recipient': receiver, 'confirmed_simple': simple,
                'signals': {key: True for key in ('spec_complete', 'authority_ready',
                                                 'environment_ready', 'observability_ready')}}

    def prepare(self, request):
        return R['assignment_preflight'](request, policy_sha256=self.policy)

    def send(self, receiver, message):
        return G['decide']({'hook_event_name': 'PreToolUse', 'model': 'gpt-6-astra',
                           'session_id': 'parent', 'tool_name': 'send_input',
                           'tool_input': {'id': receiver['id'], 'message': message}},
                          dispatch_only=True, host_directory=self.host, policy_root=self.skill)

    def assertDenied(self, result):
        self.assertEqual(result.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')

    def test_every_shipped_executor_can_hold_bind_release_and_continue(self):
        package = runpy.run_path(str(ROOT / 'scripts/package.py'))
        expected = {role: (model, effort) for role, model, effort in package['EXPECTED'].values()}
        self.assertEqual(R['ASSIGNMENT_ROLES'], expected)
        for role, (model, effort) in expected.items():
            if model == 'gpt-6-astra':
                continue
            with self.subTest(role=role):
                spawn = {'agent_type': 'cer_auto_' + role, 'reasoning_effort': effort,
                         'fork_turns': 'none', 'message': G['HOLD_MESSAGE']}
                self.assertEqual(G['decide_dispatch'](
                    {'hook_event_name': 'PreToolUse', 'tool_name': 'spawn_agent', 'tool_input': spawn},
                    host_directory=self.host, policy_root=self.skill), {})
                receiver = self.child(model, effort, role)
                request = self.request(receiver, simple=True)
                released = self.prepare(request)
                self.assertEqual(released['status'], 'VERIFIED')
                self.assertEqual(released['admitted_dispatch_arguments'], {
                    'operation': 'assign', 'target': receiver['id'],
                    'model': model, 'reasoning_effort': effort})
                self.assertEqual(released['dispatch_arguments'], {'id': receiver['id']})
                self.assertEqual(self.send(receiver, R['assignment_message'](released, request['message'])), {})
                for purpose, word in [('continue', '继续'), ('status', 'status'), ('stop', '停止')]:
                    follow = {'unit_id': request['unit_id'], 'purpose': purpose, 'scope': request['scope'],
                              'message': word, 'recipient': receiver, 'receipt': released['receipt']}
                    control = self.prepare(follow)
                    self.assertEqual(control['status'], 'VERIFIED')
                    self.assertEqual(control['receipt']['message_sha256'], released['receipt']['message_sha256'])
                    self.assertEqual(self.send(receiver, R['assignment_message'](control, word)), {})
                    self.assertNotIn(request['message'], control['prefix'])

    def test_sol_medium_hold_does_not_need_a_second_identity_only_preflight(self):
        for field, value in [('fork_context', False), ('fork_turns', 'none')]:
            data = {'agent_type': 'cer_auto_sol61_engineer', 'reasoning_effort': 'medium',
                    field: value, 'message': G['HOLD_MESSAGE']}
            event = {'hook_event_name': 'PreToolUse', 'model': 'gpt-6-astra',
                     'tool_name': 'spawn_agent', 'tool_input': data}
            self.assertEqual(G['decide_dispatch'](event, policy_root=self.skill), {})
            self.assertEqual(G['decide'](event), {})

    def test_non_hold_work_cannot_use_the_identity_only_shortcut(self):
        for message in [G['HOLD_MESSAGE'] + '\nNow write a file.', 'Fix source now.', 'continue']:
            self.assertDenied(G['decide_dispatch'](
                {'hook_event_name': 'PreToolUse', 'tool_name': 'spawn_agent',
                 'tool_input': {'agent_type': 'cer_auto_sol61_engineer', 'reasoning_effort': 'medium',
                                'fork_turns': 'none', 'message': message}}, policy_root=self.skill))

    def test_cheaper_models_still_reject_uncertain_or_risky_units(self):
        for model in ('gpt-6-luna', 'gpt-5.6-luna', 'gpt-5.6-terra'):
            receiver = self.child(model, 'high')
            for signals in ({'risk': 2}, {'coupling': 2}, {'uncertainty': 2}, {'novelty': 2},
                            {'evidence_conflict': True}, {'capability_failure': True},
                            {'irreversibility': 1}, {'risk': True}, {'novelty': '0'}):
                with self.subTest(model=model, signals=signals):
                    request = self.request(receiver, simple=True)
                    request['signals'].update(signals)
                    self.assertNotEqual(self.prepare(request)['status'], 'VERIFIED')
            self.assertNotEqual(self.prepare(self.request(receiver, simple=False))['status'], 'VERIFIED')

    def test_low_requires_explicit_support_and_reason_and_never_astra_or_terra(self):
        request = self.request(self.child('gpt-6-luna', 'low'), simple=True)
        self.assertNotEqual(self.prepare(request)['status'], 'VERIFIED')
        request.update(effort_supported=True, effort_reason='User requested low for this mechanical unit')
        self.assertEqual(self.prepare(request)['status'], 'VERIFIED')
        for model in ('gpt-6-astra', 'gpt-5.6-terra', 'gpt-6.1-sol'):
            request['recipient'] = self.child(model, 'low')
            self.assertNotEqual(self.prepare(request)['status'], 'VERIFIED')
        self.assertFalse(R['assignment_pair_known']('gpt-6-luna', 'ultra'))

    def test_unknown_model_or_effort_never_passes_by_prefix(self):
        for model, effort in [('gpt-6-sol-fake', 'high'), ('gpt-6.1-sol', 'unlimited'), ([], 'high')]:
            self.assertFalse(R['assignment_pair_known'](model, effort))

    def test_controls_preserve_current_policy_scope_identity_and_no_extra_work(self):
        receiver = self.child()
        request = self.request(receiver)
        released = self.prepare(request)
        follow = {'unit_id': request['unit_id'], 'purpose': 'continue', 'scope': request['scope'],
                  'message': 'continue', 'recipient': receiver, 'receipt': released['receipt']}
        control = self.prepare(follow)
        good = R['assignment_message'](control, 'continue')
        self.assertEqual(self.send(receiver, good), {})
        for message in ('continue\nAlso edit a different file.', '继续完成另一件事', 'RELEASE new_unit'):
            self.assertDenied(self.send(receiver, control['prefix'] + message))
        for key, bad in [('unit_id', 'other'), ('scope_sha256', '0' * 64),
                         ('policy_sha256', '0' * 64), ('model', 'gpt-6-astra'), ('effort', 'medium'),
                         ('recipient_id', 'someone-else'), ('message_sha256', 'not-a-hash')]:
            altered = copy.deepcopy(control['receipt']); altered[key] = bad
            self.assertDenied(self.send(receiver, G['ASSIGNMENT_PREFIX'] + json.dumps(altered) + '\ncontinue'))
        self.assertDenied(self.send(receiver, 'continue'))
        self.assertDenied(self.send(receiver, 'status'))
        self.assertDenied(self.send(receiver, 'stop'))

    def test_current_native_owner_is_rechecked_for_cached_control(self):
        receiver = self.child()
        request = self.request(receiver)
        released = self.prepare(request)
        control = self.prepare({'unit_id': request['unit_id'], 'purpose': 'continue', 'scope': request['scope'],
                                'message': 'continue', 'recipient': receiver, 'receipt': released['receipt']})
        self.child(owner='other-parent')
        self.assertDenied(self.send(receiver, R['assignment_message'](control, 'continue')))
        self.child()
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("UPDATE threads SET archived=1 WHERE id='child'")
        self.assertDenied(self.send(receiver, R['assignment_message'](control, 'continue')))

    def test_astra_continuation_keeps_complexity_gate_and_readonly_effects(self):
        receiver = self.child('gpt-6-astra', 'high')
        request = self.request(receiver)
        self.assertNotEqual(self.prepare(request)['status'], 'VERIFIED')
        request['signals'].update(very_complex=True, sol61_unsuitable_reason='Unresolved causal contradiction')
        request['complexity_reason'] = 'Independent causal hypotheses survive verified observations'
        request['message'] = R['EXECUTION_PREFIX'] + json.dumps(
            {'effects': ['read'], 'permission': 'read-only', 'role_read_only': True,
             'parent_released': False}) + '\nAnalyze the contradictory evidence; do not modify files.'
        release = self.prepare(request)
        self.assertEqual(release['status'], 'VERIFIED')
        self.assertEqual(self.send(receiver, R['assignment_message'](release, request['message'])), {})
        control = self.prepare({'unit_id': request['unit_id'], 'purpose': 'continue', 'scope': request['scope'],
                                'message': 'continue', 'recipient': receiver, 'receipt': release['receipt']})
        self.assertEqual(self.send(receiver, R['assignment_message'](control, 'continue')), {})
        altered = copy.deepcopy(control['receipt'])
        altered['admission']['signals']['very_complex'] = False
        self.assertDenied(self.send(receiver, G['ASSIGNMENT_PREFIX'] + json.dumps(altered) + '\ncontinue'))
        self.assertDenied(G['decide']({'hook_event_name': 'PreToolUse', 'model': 'gpt-6-astra',
                                      'tool_name': 'apply_patch', 'tool_input': {}}))

    def test_guard_cli_honors_non_default_codex_home_and_unicode_paths(self):
        receiver = self.child()
        request = self.request(receiver)
        release = self.prepare(request)
        event = {'hook_event_name': 'PreToolUse', 'model': 'gpt-6-astra', 'session_id': 'parent',
                 'tool_name': 'send_input', 'tool_input': {'id': receiver['id'],
                     'message': R['assignment_message'](release, request['message'])}}
        env = dict(os.environ, CODEX_HOME=str(self.host))
        run = subprocess.run([sys.executable, '-I', '-B', str(GUARD_PATH), '--dispatch-only',
                              '--policy-root', str(self.skill)], input=json.dumps(event).encode(),
                             capture_output=True, env=env, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'', run.stdout)
        self.assertFalse((self.host / 'state_5.sqlite-journal').exists())

    def test_cli_accepts_utf8_bom_without_relaxing_duplicate_key_checks(self):
        target = self.root / '中文 file.txt'
        target.write_text('你好\r\nsecond line', encoding='utf-8')
        items = json.dumps([{'op': 'page', 'path': target.name}], ensure_ascii=False).encode()
        args = [sys.executable, '-I', '-B', str(READER_PATH), 'batch', '--root', str(self.root),
                '--requests', '-', '--max-bytes', '4096', '--framing-bytes', '0']
        run = subprocess.run(args, input=b'\xef\xbb\xbf' + items, capture_output=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['results'][0]['data'], '你好\r\nsecond line')
        bad = subprocess.run(args, input=b'\xef\xbb\xbf[{"op":"page","op":"list","path":"."}]',
                             capture_output=True, timeout=10)
        self.assertNotEqual(bad.returncode, 0)
        self.assertEqual(bad.stdout, b'')


if __name__ == '__main__':
    unittest.main()
