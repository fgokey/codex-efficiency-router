"""Causal diagnosis controls: help with hard problems, not repeated tool failures."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from write_policy import diagnostic_action


class DiagnosisRegressionTests(unittest.TestCase):
    def test_astra_parent_analyzes_known_complexity_without_another_agent(self):
        self.assertEqual(diagnostic_action(model='gpt-6-astra', complex_judgment=True),
                         'astra_local_readonly_diagnosis')
        self.assertEqual(diagnostic_action(model='gpt-6-astra', complex_judgment=True,
                                           no_escalation=True), 'astra_local_readonly_diagnosis')

    def test_same_attempt_count_does_not_replace_failure_classification(self):
        # Positive controls reach the exact formerly untested condition. Changing
        # only failure_kind must change the result; prerequisites cannot mask it.
        for kind in ('capability', 'unexplained'):
            self.assertEqual(diagnostic_action(model='gpt-6-astra', qualified_attempts=2,
                                               failure_kind=kind), 'astra_local_readonly_diagnosis')
        for kind in ('implementation', 'none'):
            for count in (2, 20):
                self.assertEqual(diagnostic_action(model='gpt-6-astra', qualified_attempts=count,
                                                   failure_kind=kind), 'continue_scoped_diagnosis')

    def test_prerequisite_and_cheap_experiment_still_precede_premium_diagnosis(self):
        for kind in ('environment', 'specification', 'observability', 'capacity'):
            self.assertEqual(diagnostic_action(model='gpt-6-astra', complex_judgment=True,
                                               qualified_attempts=20, failure_kind=kind),
                             'repair_prerequisite')
        self.assertEqual(diagnostic_action(model='gpt-6-astra', complex_judgment=True,
                                           cheap_check_available=True), 'executor_experiment')


if __name__ == '__main__':
    unittest.main()
