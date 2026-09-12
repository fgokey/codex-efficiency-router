"""Regression for sticky observations and forced-model quality floors."""
import unittest
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from effort_reference import Configuration as C, plan, recommend, record_observation, resolve_observation
from write_policy import AstraWriteEvidence, WriteScope, Writer
from policy_reference import TaskSignals as S
from profiles import Profile
from test_effort_policy import context, ADAPTIVE, MECHANICAL


class EffortObservationTests(unittest.TestCase):
    def mismatch(self, **changes):
        c=context(current=C('astra','high'),current_sufficient=True,benefit_clear=True,**changes)
        return record_observation(c,C('sol','high'),'gpt-5.6-sol','medium')

    def resolve(self, c, **changes):
        args=dict(effects_reconciled=True,acceptance_reviewed=True,
                  reason='unit-a: diff and checks reviewed; retain valid work, correct binding next phase')
        args.update(changes)
        return resolve_observation(c,**args)

    def test_mismatch_requires_review_even_with_automatic_low_disabled(self):
        c=self.mismatch()
        d=plan(S(uncertainty=2,coupling=2),c,ADAPTIVE)
        self.assertEqual((d.action,d.requested),('prerequisite',None))
        self.assertIn('read-only investigation',d.reason)
        self.assertEqual(c.observation_review,'pending')

    def test_new_verified_or_unknown_identity_cannot_erase_affected_work(self):
        for effort in ('high',None):
            c=record_observation(self.mismatch(),C('sol','high'),'gpt-5.6-sol',effort)
            self.assertEqual(plan(S(),c,ADAPTIVE).action,'prerequisite')
            self.assertEqual(c.observation_review,'pending')

    def test_in_flight_mismatch_defers_without_replay_or_termination(self):
        for changes in (dict(worker_active=True),dict(safe_boundary=False)):
            c=replace(self.mismatch(),**changes)
            self.assertEqual(plan(S(),c,ADAPTIVE).action,'defer')
            with self.assertRaises(ValueError):self.resolve(c)

    def test_mismatch_gate_precedes_root_exception_owner_reuse_and_local_shortcuts(self):
        proof=AstraWriteEvidence(reason='critical_context_loss',root_actor=True,scope_bounded=True,
                                 target_in_workspace=True,verification_defined=True,guard_status='inactive')
        scope=WriteScope('unit-a',True,True,True,local_owner=True,astra_write=proof)
        for c in (replace(self.mismatch(),operation='local_patch',write_scope=scope),
                  replace(self.mismatch(),operation='mutation',write_scope=replace(scope,local_owner=False,
                          writers=(Writer('old','unit-a','gpt-5.6-sol','idle',effort='high'),))),
                  replace(self.mismatch(),host_supports_routing=False),
                  replace(self.mismatch(),diagnosis_only=True)):
            self.assertEqual(plan(S(no_subagents=True),c,ADAPTIVE).action,'prerequisite')

    def test_partial_or_empty_review_does_not_clear_mismatch(self):
        for changes in (dict(effects_reconciled=False),dict(acceptance_reviewed=False),
                        dict(effects_reconciled='yes'),dict(reason=' ')):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.resolve(self.mismatch(),**changes)
        with self.assertRaises(ValueError):self.resolve(context())

    def test_resolution_preserves_observation_retries_and_user_limits(self):
        c=self.mismatch(repair_attempt_limit=3,repair_extension_reason='new evidence')
        resolved=self.resolve(c)
        self.assertEqual(resolved.last_observation,'MISMATCH')
        self.assertEqual(resolved.repair_attempt_limit,3)
        self.assertTrue(resolved.automatic_low_suspended)
        self.assertEqual(c.observation_review,'pending')
        self.assertEqual(plan(S(),resolved,ADAPTIVE).action,'delegate')
        self.assertEqual(plan(S(failed_attempts=3),resolved,ADAPTIVE).action,'blocked')
        self.assertEqual(plan(S(no_subagents=True),resolved,ADAPTIVE).action,'local')
        self.assertEqual(plan(S(),replace(resolved,keep_model=True),ADAPTIVE).action,'local')

    def test_repeat_mismatch_requires_fresh_review(self):
        c=self.resolve(self.mismatch())
        c=record_observation(c,C('sol','high'),'gpt-5.6-terra','medium')
        self.assertEqual(c.observation_review,'pending')
        self.assertIsNone(c.observation_resolution_reason)
        self.assertEqual(plan(S(),c,ADAPTIVE).action,'prerequisite')

    def test_unknown_alone_does_not_assert_a_configuration_failure(self):
        c=record_observation(context(current=C('astra','high'),current_sufficient=True,benefit_clear=True),
                             C('sol','high'),None,None)
        self.assertEqual(c.observation_review,'none')
        self.assertEqual(plan(S(),c,ADAPTIVE).action,'delegate')
        self.assertTrue(c.automatic_low_suspended)

    def test_invalid_resolution_states_are_rejected(self):
        for changes in (dict(observation_review='resolved'),dict(observation_review='trusted'),
                        dict(observation_resolution_reason='unscoped')):
            with self.assertRaises(ValueError):plan(S(),replace(context(),**changes),ADAPTIVE)

    def test_legacy_mismatch_state_cannot_be_overwritten_without_review(self):
        c=context(last_observation='MISMATCH')
        next_c=record_observation(c,C('sol','high'),'gpt-5.6-sol','high')
        self.assertEqual(plan(S(),next_c,ADAPTIVE).action,'prerequisite')
        resolved=self.resolve(c)
        later=record_observation(resolved,C('sol','high'),'gpt-5.6-sol','high')
        self.assertTrue(later.automatic_low_suspended)
        self.assertEqual(later.observation_review,'resolved')

    def test_auto_low_suspension_survives_later_verified_medium(self):
        c = context(current=C('sol', 'high'), current_sufficient=True, benefit_clear=True)
        c = record_observation(c, C('luna', 'low'), 'gpt-5.6-luna', None)
        self.assertTrue(c.automatic_low_suspended)
        c = record_observation(c, C('luna', 'medium'), 'gpt-5.6-luna', 'medium')
        self.assertEqual(c.last_observation, 'VERIFIED')
        self.assertTrue(c.automatic_low_suspended)
        self.assertEqual(plan(MECHANICAL, c, Profile('adaptive', True)).recommended.effort, 'medium')

    def test_forced_astra_does_not_hide_intrinsically_hard_novelty_gate(self):
        s = S(uncertainty=2, risk=1, coupling=0, verifiability=1, novelty=3, force_astra=True)
        self.assertEqual(recommend(s), C('astra', 'high'))
        self.assertEqual(plan(s, context(), ADAPTIVE, explicit_effort='medium').action, 'blocked')


if __name__ == '__main__':
    unittest.main()
