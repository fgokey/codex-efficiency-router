"""Code loading may be reused; current identity/policy decisions must not be."""
from contextlib import closing
import json
from pathlib import Path
import runpy
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class HookCodeReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.policy = self.root / 'policy'
        shutil.copytree(ROOT / 'skills/codex-efficiency-router', self.policy)
        self.guard = runpy.run_path(str(ROOT / 'hooks/astra_write_guard.py'))
        self.reader = runpy.run_path(str(ROOT / 'hooks/readonly_reader.py'))
        self.database = self.root / 'state_5.sqlite'
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('CREATE TABLE threads (id TEXT, model TEXT, reasoning_effort TEXT, '
                       'source TEXT, thread_source TEXT, agent_role TEXT, agent_path TEXT, '
                       'archived INTEGER, rollout_path TEXT)')
            db.execute('INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)',
                       ('parent','gpt-6-astra','high','{}','','','/parent',0,''))
            source = json.dumps({'subagent': {'thread_spawn': {'parent_thread_id': 'parent'}}})
            db.execute('INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)',
                       ('child','gpt-6.1-sol','high',source,'','sol61_engineer','/child',0,''))
        request = {'unit_id': 'owned-test', 'purpose': 'new_unit', 'scope': 'src/example.py',
                   'message': 'Review the owned source unit.',
                   'recipient': {'id':'child','model':'gpt-6.1-sol','effort':'high',
                                 'evidence_ref':'temporary test observation'},
                   'signals': dict.fromkeys(('spec_complete','authority_ready',
                                             'environment_ready','observability_ready'), True)}
        result = self.reader['assignment_preflight'](request,
                    policy_sha256=self.reader['assignment_policy_sha256'](self.policy))
        self.assertEqual(result['status'], 'VERIFIED')
        self.event = {'hook_event_name':'PreToolUse','model':'gpt-6-astra',
                      'session_id':'parent','tool_name':'send_input',
                      'tool_input':{'id':'child','message':self.reader['assignment_message'](result,request['message'])}}

    def decide(self):
        return self.guard['decide_dispatch'](self.event, host_directory=self.root, policy_root=self.policy)

    def test_full_dispatch_loads_reader_code_once_and_emits_no_success_context(self):
        original = runpy.run_path
        with patch.object(runpy, 'run_path', wraps=original) as loader:
            self.assertEqual(self.decide(), {})
            paths = [Path(call.args[0]).name for call in loader.call_args_list]
        self.assertEqual(paths, ['readonly_reader.py'])

    def test_same_process_does_not_cache_recipient_identity(self):
        self.assertEqual(self.decide(), {})
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("UPDATE threads SET reasoning_effort='medium' WHERE id='child'")
        self.assertEqual(self.decide()['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_same_process_does_not_cache_policy_fingerprint(self):
        self.assertEqual(self.decide(), {})
        path = self.policy / 'SKILL.md'
        path.write_bytes(path.read_bytes() + b'\nChanged test policy.\n')
        self.assertEqual(self.decide()['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_same_process_does_not_cache_message_authorization(self):
        self.assertEqual(self.decide(), {})
        self.event['tool_input']['message'] += '\nUnrelated extra mutation'
        self.assertEqual(self.decide()['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_failed_code_load_is_not_cached_as_allow(self):
        with patch.object(runpy, 'run_path', side_effect=OSError('missing reader')):
            self.assertEqual(self.decide()['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assertEqual(self.decide(), {})

    def test_separate_hook_process_modules_start_with_empty_code_cache(self):
        self.assertEqual(self.decide(), {})
        fresh = runpy.run_path(str(ROOT / 'hooks/astra_write_guard.py'))
        original = runpy.run_path
        with patch.object(runpy, 'run_path', wraps=original) as loader:
            fresh['reader_contract']()
        self.assertEqual(loader.call_count, 1)

    def test_policy_hook_remains_synchronous_and_unknown_tools_remain_covered(self):
        doc = json.loads((ROOT/'hooks/hooks.json').read_text())
        self.assertEqual(set(doc['hooks']), {'PreToolUse'})
        groups = doc['hooks']['PreToolUse']
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['matcher'], '*')
        for handler in groups[0]['hooks']:
            self.assertEqual(handler['type'], 'command')
            self.assertIsNot(handler.get('async'), True)
            self.assertIn('--expected-bundle', handler['command'])
        event={**self.event,'tool_name':'unrecognized_side_effect_tool'}
        self.assertEqual(self.guard['decide'](event)['hookSpecificOutput']['permissionDecision'],'deny')

    def test_no_reader_load_for_wait_or_executor_tool_passthrough(self):
        with patch.object(runpy, 'run_path', side_effect=AssertionError('needless reader import')):
            for event in ({**self.event,'tool_name':'wait'},
                          {**self.event,'tool_name':'apply_patch','model':'gpt-6.1-sol'},
                          {**self.event,'tool_name':'apply_patch'}):
                result = self.guard['decide'](event)
                if event['tool_name']=='apply_patch' and event['model']=='gpt-6-astra':
                    self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')
                else:
                    self.assertEqual(result, {})


if __name__ == '__main__':
    unittest.main()
