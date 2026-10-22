"""Cross-layer Sol retirement checks. No model calls or real user state."""
from contextlib import closing
from pathlib import Path
import copy
import json
import runpy
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
R = runpy.run_path(str(ROOT / 'hooks/readonly_reader.py'))
G = runpy.run_path(str(ROOT / 'hooks/astra_write_guard.py'))
RETIRED = ('gpt-6-sol', 'gpt-5.6-sol')


class Sol61RetirementTests(unittest.TestCase):
    def request(self, model='gpt-6.1-sol'):
        return {'unit_id':'retirement-test','purpose':'new_unit','scope':'src/example.py',
                'message':'Review the owned unit only.',
                'recipient':{'id':'child','model':model,'effort':'high',
                             'evidence_ref':'temporary host observation'},
                'signals':{key:True for key in ('spec_complete','authority_ready',
                                               'environment_ready','observability_ready')}}

    def test_all_sol_role_names_resolve_to_current_model_without_silent_pin_remap(self):
        for role in ('sol_engineer','sol61_engineer','cer_auto_sol_engineer','cer_auto_sol61_engineer'):
            data={'agent_type':role,'fork_turns':'none','message':G['HOLD_MESSAGE']}
            if role.startswith('cer_auto_'):
                data['reasoning_effort']='high'
            pair=G['validate_spawn'](data)
            self.assertEqual(pair[0],'gpt-6.1-sol')
            event={'hook_event_name':'PreToolUse','model':'gpt-6-astra',
                   'tool_name':'spawn_agent','tool_input':data}
            self.assertEqual(G['decide_dispatch'](event),{})
            for retired in RETIRED:
                with self.subTest(role=role,retired=retired):
                    with self.assertRaises(ValueError):
                        G['validate_spawn'](dict(data,model=retired))

    def test_retired_models_cannot_be_admitted_by_fresh_or_cached_requests(self):
        current=self.request()
        admitted=R['assignment_preflight'](current)
        self.assertEqual(admitted['status'],'VERIFIED')
        for model in RETIRED:
            for effort in R['ASSIGNMENT_EFFORTS']:
                self.assertFalse(R['assignment_pair_known'](model,effort))
            request=self.request(model)
            self.assertNotEqual(R['assignment_preflight'](request)['status'],'VERIFIED')
            for purpose,word in [('continue','continue'),('status','状态'),('stop','stop')]:
                receipt=copy.deepcopy(admitted['receipt'])
                receipt['model']=model
                request.update(purpose=purpose,message=word,receipt=receipt)
                result=R['assignment_preflight'](request)
                self.assertNotEqual(result['status'],'VERIFIED')
                self.assertNotIn('dispatch_arguments',result)
                self.assertNotIn('admitted_dispatch_arguments',result)

    def test_current_host_rows_do_not_reenable_retired_sol(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            database=root/'state_5.sqlite'
            source=json.dumps({'subagent':{'thread_spawn':{'parent_thread_id':'parent'}}})
            with closing(sqlite3.connect(database)) as db,db:
                db.execute('CREATE TABLE threads (id TEXT PRIMARY KEY, model TEXT, reasoning_effort TEXT, '
                           'source TEXT, thread_source TEXT, agent_role TEXT, agent_path TEXT, '
                           'archived INTEGER, rollout_path TEXT)')
                db.execute('INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)',
                           ('parent','gpt-6-astra','high','{}','','','',0,''))
                db.execute('INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)',
                           ('child','gpt-6.1-sol','high',source,'','sol61_engineer','/child',0,''))
            self.assertEqual(G['host_recipient']('parent','child',root)['model'],'gpt-6.1-sol')
            for retired in RETIRED:
                with closing(sqlite3.connect(database)) as db,db:
                    db.execute('UPDATE threads SET model=? WHERE id=?',(retired,'child'))
                with self.assertRaisesRegex(ValueError,'outside current admission policy'):
                    G['host_recipient']('parent','child',root)

    def test_retired_explicit_default_spawns_are_rejected_in_both_boundaries(self):
        for model in RETIRED:
            event={'hook_event_name':'PreToolUse','model':'gpt-6-astra','tool_name':'spawn_agent',
                   'tool_input':{'agent_type':'default','model':model,'reasoning_effort':'high',
                                 'fork_turns':'none','message':G['HOLD_MESSAGE']}}
            for decision in (G['decide'](event),G['decide_dispatch'](event)):
                self.assertEqual(decision['hookSpecificOutput']['permissionDecision'],'deny')


if __name__ == '__main__':
    unittest.main()
