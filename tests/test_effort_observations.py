"""Regression for sticky observations and forced-model quality floors."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from effort_reference import Configuration as C, plan, recommend, record_observation
from policy_reference import TaskSignals as S
from profiles import Profile
from test_effort_policy import context, ADAPTIVE, MECHANICAL


class EffortObservationTests(unittest.TestCase):
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
