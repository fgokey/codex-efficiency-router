"""Offline joint-selection contracts; these tests do not run Codex models."""
from dataclasses import replace
from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from effort_reference import (Configuration as C, Context, RoleBinding, PRESETS,
                              plan, recommend, check_observation)
from policy_reference import TaskSignals as S
from profiles import Profile

ADAPTIVE = Profile('adaptive')
MECHANICAL = S(mechanical=True, uncertainty=0, risk=1, coupling=0, verifiability=3)
SOL = S(uncertainty=2, risk=1, coupling=1)
ASTRA = S(uncertainty=3, risk=3, coupling=2)


def context(**overrides):
    args = dict(current=C('sol', 'medium'), current_sufficient=False,
                host_supports_routing=True, host_can_set_effort=True,
                roles={r: RoleBinding(m, None) for r, m, _ in PRESETS.values()},
                catalog={m: frozenset(('low', 'medium', 'high', 'xhigh', 'max'))
                         for _, m, _ in PRESETS.values()},
                safe_boundary=True)
    args.update(overrides)
    return Context(**args)


class EffortPolicyTests(unittest.TestCase):
    def test_defaults_preserve_quality(self):
        for signals, expected in ((MECHANICAL, C('luna', 'medium')),
                                  (S(), C('terra', 'medium')),
                                  (SOL, C('sol', 'medium')),
                                  (ASTRA, C('astra', 'high'))):
            self.assertEqual(recommend(signals), expected)

    def test_deep_reasoning_in_suitable_model_selects_high(self):
        result = plan(SOL, context(), ADAPTIVE, deep_reasoning=True)
        self.assertEqual(result.action, 'delegate')
        self.assertEqual(result.requested, C('sol', 'high'))

    def test_medium_to_high_is_not_identical_configuration_retry(self):
        c = context(benefit_clear=False, same_config_reason='none')
        self.assertEqual(plan(SOL, c, ADAPTIVE, deep_reasoning=True).action, 'delegate')
        self.assertEqual(plan(SOL, c, ADAPTIVE).action, 'blocked')

    def test_explicit_high_same_model_does_not_need_new_model(self):
        result = plan(SOL, context(keep_model=True), ADAPTIVE, explicit_effort='high')
        self.assertEqual(result.requested, C('sol', 'high'))

    def test_no_compulsory_cheap_or_effort_ladder(self):
        result = plan(ASTRA, context(current=C('terra', 'medium')), ADAPTIVE)
        self.assertEqual(result.requested, C('astra', 'high'))

    def test_prerequisites_cannot_be_overridden_by_expensive_effort(self):
        for flag in ('spec_complete', 'authority_ready', 'environment_ready', 'observability_ready'):
            signals = replace(ASTRA, force_astra=True, **{flag: False})
            result = plan(signals, context(), ADAPTIVE, explicit_effort='max')
            self.assertEqual(result.action, 'prerequisite')
            self.assertIsNone(result.requested)

    def test_cheap_check_before_more_reasoning(self):
        self.assertIsNone(recommend(replace(ASTRA, cheap_check_available=True), deep_reasoning=True))

    def test_auto_low_requires_opt_in(self):
        self.assertEqual(recommend(MECHANICAL).effort, 'medium')
        self.assertEqual(recommend(MECHANICAL, allow_low=True).effort, 'low')

    def test_low_gate_rejects_every_individual_risk_signal(self):
        bad = dict(uncertainty=1, risk=2, coupling=2, verifiability=2,
                   irreversibility=2, novelty=1, evidence_conflict=True,
                   commitment_boundary=True, failed_attempts=1, capability_failure=True,
                   mechanical=False)
        for name, value in bad.items():
            with self.subTest(name=name):
                self.assertNotEqual(recommend(replace(MECHANICAL, **{name: value}), allow_low=True).effort, 'low')

    def test_deep_request_cannot_auto_low(self):
        self.assertEqual(recommend(MECHANICAL, allow_low=True, deep_reasoning=True).effort, 'high')

    def test_low_only_uses_confirmed_catalog_entry(self):
        c = context(current=C('sol', 'high'), current_sufficient=True, benefit_clear=True)
        result = plan(MECHANICAL, c, Profile('adaptive', True))
        self.assertEqual(result.requested, C('luna', 'low'))
        denied = dict(c.catalog); denied[PRESETS['luna'][1]] = frozenset(('medium', 'high'))
        result = plan(MECHANICAL, replace(c, catalog=denied), Profile('adaptive', True))
        self.assertEqual(result.action, 'local')
        self.assertIn('catalog', result.reason)
        self.assertIsNone(result.requested)

    def test_unknown_or_mismatched_observation_disables_future_auto_low(self):
        c = context(current=C('sol', 'high'), current_sufficient=True, benefit_clear=True)
        for status in ('UNKNOWN', 'MISMATCH'):
            result = plan(MECHANICAL, replace(c, last_observation=status), Profile('adaptive', True))
            self.assertEqual(result.recommended, C('luna', 'medium'))
        self.assertEqual(plan(MECHANICAL, c, Profile('adaptive', True)).recommended.effort, 'low')

    def test_xhigh_and_max_are_never_automatic(self):
        for u, r, v in product(range(4), repeat=3):
            self.assertNotIn(recommend(S(uncertainty=u, risk=r, verifiability=v)).effort, ('xhigh', 'max'))

    def test_explicit_max_requires_support(self):
        c = context()
        self.assertEqual(plan(ASTRA, c, ADAPTIVE, explicit_effort='max').requested, C('astra', 'max'))
        catalog = dict(c.catalog); catalog[PRESETS['astra'][1]] = frozenset(('high',))
        result = plan(ASTRA, replace(c, catalog=catalog), ADAPTIVE, explicit_effort='max')
        self.assertEqual(result.action, 'blocked'); self.assertIsNone(result.requested)

    def test_explicit_medium_cannot_reduce_deep_quality_floor(self):
        self.assertEqual(plan(SOL, context(current=C('terra', 'medium')), ADAPTIVE, deep_reasoning=True,
                              explicit_effort='medium').action, 'blocked')

    def test_explicit_low_cannot_bypass_safety(self):
        for signals in (SOL, ASTRA, replace(MECHANICAL, verifiability=1), S(force_astra=True),
                        replace(MECHANICAL, force_astra=True)):
            self.assertEqual(plan(signals, context(), ADAPTIVE, explicit_effort='low').action, 'blocked')

    def test_explicit_low_on_safe_mechanical_task_can_be_requested(self):
        c = context(current=C('sol', 'high'), current_sufficient=True)
        self.assertEqual(plan(MECHANICAL, c, ADAPTIVE, explicit_effort='low').requested, C('luna', 'low'))

    def test_astra_medium_explicit_only_for_bounded_safe_request(self):
        s = S(force_astra=True)
        self.assertEqual(recommend(s).effort, 'high')
        self.assertEqual(plan(s, context(), ADAPTIVE, explicit_effort='medium').requested, C('astra', 'medium'))
        self.assertEqual(plan(replace(ASTRA, force_astra=True), context(), ADAPTIVE,
                              explicit_effort='medium').action, 'blocked')

    def test_fixed_role_cannot_be_overridden(self):
        bindings = {r: RoleBinding(m, e) for r, m, e in PRESETS.values()}
        c = context(roles=bindings)
        result = plan(SOL, c, Profile(), deep_reasoning=True)
        self.assertEqual(result.action, 'blocked'); self.assertIsNone(result.requested)
        result = plan(S(), replace(c, current_sufficient=True, benefit_clear=True), Profile())
        self.assertEqual(result.requested, C('terra', 'medium'))

    def test_pinned_adaptive_role_is_a_configuration_error_even_when_value_matches(self):
        c = context(roles={PRESETS['astra'][0]: RoleBinding(PRESETS['astra'][1], 'high')})
        result = plan(ASTRA, c, ADAPTIVE)
        self.assertEqual(result.action, 'blocked'); self.assertIn('pins effort', result.reason)

    def test_adaptive_requires_native_effort_field(self):
        self.assertEqual(plan(ASTRA, context(host_can_set_effort=False), ADAPTIVE).action, 'blocked')

    def test_host_role_and_catalog_are_three_independent_gates(self):
        for kwargs in ({'host_supports_routing': False}, {'roles': {}}, {'catalog': {}},
                       {'roles': {PRESETS['astra'][0]: RoleBinding('different-model', None)}}):
            result = plan(ASTRA, context(**kwargs), ADAPTIVE)
            self.assertEqual(result.action, 'blocked'); self.assertIsNone(result.requested)

    def test_no_subagent_causal_positive_control(self):
        for sufficient in (False, True):
            c = context(current_sufficient=sufficient, benefit_clear=True)
            self.assertEqual(plan(ASTRA, c, ADAPTIVE).action, 'delegate')
            result = plan(replace(ASTRA, no_subagents=True), c, ADAPTIVE)
            self.assertEqual(result.action, 'local' if sufficient else 'blocked')
            self.assertIsNone(result.requested)

    def test_no_escalation_prohibits_model_or_effort_increase(self):
        for s, current, deeper in ((ASTRA, C('sol', 'high'), False),
                                   (SOL, C('sol', 'medium'), True),
                                   (S(), C('astra', 'low'), False)):
            c = context(current=current, current_sufficient=True, benefit_clear=True)
            self.assertEqual(plan(s, c, ADAPTIVE, deep_reasoning=deeper).action, 'delegate')
            self.assertEqual(plan(s, replace(c, no_escalation=True), ADAPTIVE,
                                  deep_reasoning=deeper).action, 'local')

    def test_no_effort_escalation_is_separate_from_model_lock(self):
        c = context(current=C('sol', 'medium'), no_effort_escalation=True)
        self.assertEqual(plan(ASTRA, c, ADAPTIVE).action, 'blocked')
        c = replace(c, current=C('sol', 'high'))
        self.assertEqual(plan(ASTRA, c, ADAPTIVE).requested, C('astra', 'high'))
        self.assertEqual(plan(ASTRA, replace(c, keep_model=True), ADAPTIVE).action, 'blocked')

    def test_explicit_max_does_not_bypass_user_limits(self):
        c = context(no_escalation=True)
        self.assertEqual(plan(ASTRA, c, ADAPTIVE, explicit_effort='max').action, 'blocked')

    def test_unknown_current_identity_cannot_verify_no_upgrade(self):
        for flag in ('no_escalation', 'no_effort_escalation', 'keep_model'):
            c = context(current=None, **{flag: True})
            self.assertEqual(plan(ASTRA, c, ADAPTIVE).action, 'blocked')

    def test_safe_justified_downshift_after_phase_change(self):
        c = context(current=C('sol', 'high'), current_sufficient=True, keep_model=True,
                    no_escalation=True, benefit_clear=True, change_event='phase')
        self.assertEqual(plan(SOL, c, ADAPTIVE).requested, C('sol', 'medium'))
        self.assertEqual(plan(SOL, replace(c, benefit_clear=False), ADAPTIVE).action, 'local')

    def test_unresolved_insufficiency_cannot_downgrade_effort_or_model(self):
        c = context(current=C('sol', 'high'), benefit_clear=True)
        for s in (SOL, S()):
            self.assertEqual(plan(s, c, ADAPTIVE).action, 'blocked')

    def test_active_or_unsafe_boundary_defers_even_explicit_max(self):
        for kwargs in ({'worker_active': True}, {'safe_boundary': False}):
            self.assertEqual(plan(ASTRA, context(**kwargs), ADAPTIVE,
                                  explicit_effort='max').action, 'defer')

    def test_no_event_prevents_churn(self):
        c = context(change_event='none')
        self.assertEqual(plan(SOL, c, ADAPTIVE, deep_reasoning=True).action, 'blocked')
        self.assertEqual(plan(SOL, replace(c, current_sufficient=True), ADAPTIVE,
                              deep_reasoning=True).action, 'local')

    def test_identical_pair_needs_both_reason_and_benefit(self):
        for sufficient, benefit, reason in product((False, True), (False, True), ('none', 'independent_review')):
            c = context(current_sufficient=sufficient, benefit_clear=benefit, same_config_reason=reason)
            expected = 'delegate' if benefit and reason != 'none' else 'local' if sufficient else 'blocked'
            self.assertEqual(plan(SOL, c, ADAPTIVE).action, expected)

    def test_unknown_route_retains_sufficient_parent_without_claiming_request(self):
        c = context(current_sufficient=True, benefit_clear=True, roles={})
        result = plan(S(), c, ADAPTIVE)
        self.assertEqual(result.action, 'local'); self.assertIsNone(result.requested)
        self.assertEqual(plan(S(), c, ADAPTIVE, explicit_effort='high').action, 'blocked')

    def test_pair_is_not_observed_by_recommendation_or_request(self):
        p = C('astra', 'high')
        self.assertEqual(check_observation(p, None, None), 'UNKNOWN')
        self.assertEqual(check_observation(p, p.model, None), 'UNKNOWN')
        self.assertEqual(check_observation(p, p.model, 'medium'), 'MISMATCH')
        self.assertEqual(check_observation(p, 'wrong', None), 'MISMATCH')
        self.assertEqual(check_observation(p, p.model, 'high'), 'VERIFIED')

    def test_effort_increase_does_not_renew_exhausted_repair_budget(self):
        s = replace(SOL, failed_attempts=2)
        c = context()
        self.assertEqual(plan(s, c, ADAPTIVE, deep_reasoning=True).action, 'blocked')
        self.assertEqual(plan(s, c, ADAPTIVE, explicit_effort='max').action, 'blocked')
        self.assertEqual(plan(s, replace(c, diagnosis_only=True), ADAPTIVE,
                              deep_reasoning=True).action, 'delegate')
        self.assertEqual(plan(s, replace(c, repair_extension_reason='parent: new evidence narrows repair'),
                              ADAPTIVE, deep_reasoning=True).action, 'delegate')
        self.assertEqual(s.failed_attempts, 2)

    def test_strict_inputs_and_no_budget_side_effects(self):
        for kwargs in ({'current_sufficient': 1}, {'safe_boundary': 'true'}, {'current': 'sol'},
                       {'same_config_reason': 'just retry'}, {'change_event': 'every tool'},
                       {'last_observation': 'probably high'}, {'catalog': {'m': 'high'}},
                       {'roles': {'sol': 'high'}}):
            with self.assertRaises(ValueError): plan(S(), context(**kwargs), ADAPTIVE)
        for effort in ('none', 'ultra', 1, [], ''):
            with self.assertRaises(ValueError): plan(S(), context(), ADAPTIVE, explicit_effort=effort)
        s = replace(SOL, failed_attempts=1)
        before = s.__dict__.copy()
        plan(s, context(), ADAPTIVE, deep_reasoning=True)
        self.assertEqual(s.__dict__, before)
        self.assertEqual(s.failed_attempts, 1)


if __name__ == '__main__':
    unittest.main()
