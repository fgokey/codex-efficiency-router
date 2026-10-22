"""Causal tests for formerly masked guards; keep real mutation targets unchanged."""
from dataclasses import replace
import unittest
import test_effort_auto as base
from effort_reference import Configuration as C, EffortEvidence, plan
from policy_reference import TaskSignals as S


class EffortRepairRegressions(unittest.TestCase):
    def test_failed_fixed_high_binding_is_not_hidden_by_effort_mismatch(self):
        context = base.host(current=C('luna', 'high'), current_sufficient=False,
                            host_can_set_effort=False)
        positive = plan(S(), context, base.AUTO)
        self.assertEqual(positive.action, 'delegate')
        self.assertEqual(positive.requested_role, 'sol61_engineer')
        self.assertEqual(positive.requested, C('sol', 'high'))
        unavailable = replace(context, unavailable_roles=frozenset(
            ('cer_auto_sol61_engineer', 'sol61_engineer')))
        result = plan(S(), unavailable, base.AUTO)
        self.assertEqual(result.action, 'blocked')
        self.assertIsNone(result.requested)

    def test_ultra_fallback_guard_is_reached_for_an_ordinary_base_recommendation(self):
        signals = S(uncertainty=0, novelty=0, risk=1, coupling=1, verifiability=3)
        evidence = EffortEvidence(
            bottleneck='two independent compatibility proofs remain',
            high_limit='high cannot coordinate both proofs within the boundary',
            extra_effort_value='ultra coordinates the disjoint proofs once',
            high_insufficient=True, independent_units=2, disjoint_ownership=True,
            net_benefit=True, coordinator_authorized=True,
            coordinator_contract_verified=True, single_coordinator=True,
            capacity_available=True, shared_limits_retained=True)
        context = base.host(current=C('luna', 'high'), current_sufficient=False)
        catalog = dict(context.catalog)
        catalog['gpt-6.1-sol'] = frozenset(('medium', 'high', 'ultra'))
        catalog['gpt-5.6-terra'] = frozenset(('medium', 'high', 'ultra'))
        context = replace(context, catalog=catalog)
        positive = plan(signals, context, base.AUTO, automatic_effort='ultra', effort_evidence=evidence)
        self.assertEqual(positive.action, 'delegate')
        self.assertEqual(positive.requested, C('sol', 'ultra'))
        missing = replace(context, unavailable_models={'gpt-6.1-sol': 'observed unavailable'})
        result = plan(signals, missing, base.AUTO, automatic_effort='ultra', effort_evidence=evidence)
        self.assertEqual(result.action, 'blocked')
        self.assertIsNone(result.requested)
        self.assertIn('Ultra coordinator contract', result.reason)


if __name__ == '__main__':
    unittest.main()
