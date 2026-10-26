"""Discover every native guard case with the current Sol routing contract.

The transport, Reader and permission suite remains in native_guard_cases.py,
with valid engineering fixtures binding their actual role. Inheritance preserves
its checks; policy-specific role/model cases live here. No tests are skipped or
patched at runtime. The helper's filename avoids duplicate discovery.
"""
from native_guard_cases import *


class NativeGuardTests(NativeGuardTests):
    def test_current_sol_default_role_cannot_skip_engineering_instructions(self):
        for role in (None, 'default'):
            for effort in ('low', 'medium', 'high'):
                data = {'model': 'gpt-6.1-sol', 'reasoning_effort': effort, 'fork_turns': 'none'}
                if role is not None:
                    data['agent_type'] = role
                result = self.hook('spawn_agent', 'gpt-6-astra', data)
                self.assertTrue(self.denied(result))
                self.assertIn('sol61_engineer', str(result))
        for role, effort in (('sol61_engineer', 'high'), ('cer_auto_sol61_engineer', 'medium')):
            self.assertEqual(self.hook('spawn_agent', 'gpt-6-astra',
                {'agent_type': role, 'model': 'gpt-6.1-sol', 'reasoning_effort': effort,
                 'fork_turns': 'none'}), {})

    def test_spawn_preserves_fixed_roles_and_explicit_legacy_model_pins(self):
        # Current Sol and the unrelated supported legacy Luna pin remain valid.
        for data in ({'agent_type':'sol61_engineer','fork_turns':'none'},
                     {'agent_type':'sol_engineer','fork_turns':'none'},
                     {'agent_type':'astra_architect','fork_turns':'none'},
                     {'agent_type':'default','model':'gpt-5.6-luna','reasoning_effort':'high','fork_turns':'none'},
                     {'agent_type':'custom_reader','model':'gpt-6-luna','reasoning_effort':'low','fork_turns':'none'}):
            self.assertEqual(self.hook('spawn_agent','gpt-6-astra',data),{})
        self.assertEqual(self.hook('spawn_agent','gpt-6.1-sol',
                                   {'agent_type':'sol61_engineer','fork_turns':'none','reasoning_effort':'high'}), {})
        for data in ({'agent_type':'sol61_engineer','fork_turns':'none','reasoning_effort':'medium'},
                     {'agent_type':'default','model':'gpt-6.1-sol','reasoning_effort':'high','fork_turns':'none'},
                     {'model':'gpt-6.1-sol','reasoning_effort':'high','fork_turns':'none'},
                     {'agent_type':'default','model':'inherit','reasoning_effort':'high','fork_turns':'none'}):
            self.assertTrue(self.denied(self.hook('spawn_agent','gpt-6.1-sol',data)))
        for retired in ('gpt-6-sol','gpt-5.6-sol'):
            for role in ('default','sol_engineer','cer_auto_sol_engineer','sol61_engineer'):
                with self.subTest(model=retired,role=role):
                    data={'agent_type':role,'model':retired,'reasoning_effort':'high','fork_turns':'none'}
                    self.assertTrue(self.denied(self.hook('spawn_agent','gpt-6.1-sol',data)))
        # Agent is a separate unverified schema in the write guard, unchanged.
        self.assertEqual(self.hook('Agent','gpt-6-astra',{}),{})


if __name__ == '__main__':
    unittest.main()
