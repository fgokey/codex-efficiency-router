"""Capability-selected native bindings. No live model calls or user mode switching."""
from dataclasses import replace
from pathlib import Path
from itertools import product
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from effort_reference import Configuration as C, Context, EffortEvidence, RoleBinding, plan, PRESETS, dispatch_arguments
from policy_reference import TaskSignals as S
from profiles import Profile

AUTO = Profile('auto')
SOL = S(uncertainty=2, coupling=1, risk=1)
MECHANICAL = S(mechanical=True, uncertainty=0, coupling=0, verifiability=3)
DATA_TRANSFORM = replace(MECHANICAL, workload='data_transform')


def host(**kwargs):
    bindings = {role: RoleBinding(model, effort) for role, model, effort in PRESETS.values()}
    bindings.update({'cer_auto_' + role: RoleBinding(model, None) for role, model, _ in PRESETS.values()})
    args = dict(current=C('astra', 'high'), current_sufficient=True, benefit_clear=True,
                safe_boundary=True, host_supports_routing=True, host_can_set_effort=True,
                roles=bindings, catalog={m: frozenset(('low','medium','high')) for _,m,_ in PRESETS.values()})
    args.update(kwargs)
    return Context(**args)


class AutomaticBindingTests(unittest.TestCase):
    def test_task_difficulty_selects_model_and_explicit_effort_without_root_inheritance(self):
        cases=(
            (MECHANICAL,C('luna','high')),
            (DATA_TRANSFORM,C('luna','medium')),
            (S(),C('sol','medium')),
            (SOL,C('sol','medium')),
            (S(uncertainty=2,coupling=2,risk=1),C('sol','high')),
            (S(uncertainty=1,coupling=1,risk=2),C('sol','high')),
            (S(risk=3,uncertainty=3),C('astra','high')),
        )
        for signals,expected in cases:
            with self.subTest(expected=expected):
                d=plan(signals,host(current=C('astra','max')),AUTO)
                self.assertEqual(d.requested,expected)
                args=dispatch_arguments(d)
                self.assertEqual(args,dict(agent_type='cer_auto_'+expected.role,
                                          reasoning_effort=expected.effort,fork_turns='none'))

    def test_explicit_spawn_fields_only_for_admitted_delegation(self):
        fixed=plan(S(),host(host_can_set_effort=False),AUTO)
        self.assertEqual(dispatch_arguments(fixed),dict(agent_type='sol_engineer',fork_turns='none'))
        for d in (plan(S(),host(worker_active=True),AUTO),
                  plan(S(no_subagents=True),host(),AUTO),
                  plan(S(failed_attempts=2),host(),AUTO)):
            with self.assertRaises(ValueError):dispatch_arguments(d)

    def test_native_effort_chooses_alias_and_explicit_pair(self):
        d = plan(S(), host(), AUTO)
        self.assertEqual((d.action, d.requested_role, d.binding_kind, d.requested),
                         ('delegate', 'cer_auto_sol_engineer', 'adaptive', C('sol','medium')))

    def test_no_effort_field_uses_exact_fixed_binding(self):
        d = plan(S(), host(host_can_set_effort=False), AUTO)
        self.assertEqual((d.action,d.requested_role,d.binding_kind,d.requested),
                         ('delegate','sol_engineer','fixed',C('sol','medium')))

    def test_missing_alias_is_not_a_reason_to_reinstall(self):
        c=host(); roles=dict(c.roles); del roles['cer_auto_sol_engineer']
        d=plan(S(),replace(c,roles=roles),AUTO)
        self.assertEqual(d.requested_role,'sol_engineer')

    def test_bad_alias_can_use_verified_fixed_binding(self):
        for bad in (RoleBinding('wrong-model',None),RoleBinding('gpt-5.6-sol','medium'),
                    RoleBinding('gpt-6-sol','medium')):
            c=host(); roles=dict(c.roles); roles['cer_auto_sol_engineer']=bad
            d=plan(S(),replace(c,roles=roles),AUTO)
            self.assertEqual(d.requested_role,'sol_engineer')
            self.assertEqual(d.binding_kind,'fixed')

    def test_bad_compatibility_binding_cannot_fake_selected_pair(self):
        for bad in (RoleBinding('wrong-model','medium'),RoleBinding('gpt-6-sol','low'),
                    RoleBinding('gpt-6-sol',None)):
            c=host(host_can_set_effort=False); roles=dict(c.roles); roles['sol_engineer']=bad
            d=plan(S(),replace(c,roles=roles),AUTO, explicit_effort='medium')
            self.assertEqual(d.action,'blocked'); self.assertIsNone(d.requested)

    def test_missing_high_never_falls_back_to_medium(self):
        c=host(current_sufficient=False,host_can_set_effort=False)
        d=plan(SOL,c,AUTO,deep_reasoning=True)
        self.assertEqual(d.action,'blocked');self.assertEqual(d.recommended,C('sol','high'))
        self.assertIsNone(d.requested)

    def test_sufficient_parent_can_work_without_claiming_requested_high(self):
        c=host(current=C('astra','high'),host_can_set_effort=False)
        d=plan(SOL,c,AUTO,deep_reasoning=True)
        self.assertEqual(d.action,'local');self.assertIsNone(d.requested_role)

    def test_explicit_unavailable_setting_is_disclosed(self):
        self.assertEqual(plan(SOL,host(host_can_set_effort=False),AUTO,explicit_effort='high').action,'blocked')

    def test_astra_high_works_with_fixed_fallback(self):
        d=plan(S(risk=3,uncertainty=3),host(current=C('sol','medium'),current_sufficient=False,
                                           host_can_set_effort=False),AUTO)
        self.assertEqual((d.requested_role,d.requested),('astra_architect',C('astra','high')))

    def test_catalog_needed_for_either_binding(self):
        for native in (True,False):
            d=plan(S(),host(host_can_set_effort=native,catalog={}),AUTO,explicit_effort='medium')
            self.assertEqual(d.action,'blocked');self.assertIsNone(d.requested)

    def test_opt_out_has_causal_positive_control_on_both_bindings(self):
        for native in (True,False):
            c=host(host_can_set_effort=native)
            self.assertEqual(plan(S(),c,AUTO).action,'delegate')
            d=plan(S(no_subagents=True),c,AUTO)
            self.assertEqual(d.action,'local');self.assertIsNone(d.requested_role)

    def test_failed_alias_not_reprobed_then_failed_fallback_stops(self):
        c=host(unavailable_roles=frozenset(('cer_auto_sol_engineer',)))
        self.assertEqual(plan(S(),c,AUTO).requested_role,'sol_engineer')
        c=replace(c,unavailable_roles=frozenset(('cer_auto_sol_engineer','sol_engineer')))
        self.assertEqual(plan(S(),c,AUTO,explicit_effort='medium').action,'blocked')

    def test_unknown_active_worker_prevents_replay_to_other_binding(self):
        d=plan(S(),host(worker_active=True,unavailable_roles=frozenset(('cer_auto_sol_engineer',))),AUTO)
        self.assertEqual(d.action,'defer');self.assertIsNone(d.requested_role)

    def test_low_is_opt_in_no_unsupported_compatibility_remap(self):
        s=DATA_TRANSFORM
        self.assertEqual(plan(s,host(),AUTO).requested,C('luna','medium'))
        self.assertEqual(plan(s,host(),Profile('auto',True)).requested,C('luna','low'))
        d=plan(s,host(host_can_set_effort=False),Profile('auto',True))
        self.assertEqual(d.action,'local');self.assertIsNone(d.requested) # No fabricated low.

    def test_unknown_observation_keeps_low_disabled(self):
        s=DATA_TRANSFORM
        d=plan(s,host(last_observation='UNKNOWN'),Profile('auto',True))
        self.assertEqual(d.requested,C('luna','medium'))

    def test_selection_does_not_mutate_inputs_or_renew_budget(self):
        c=host(); before=dict(c.roles)
        d=plan(S(failed_attempts=2),c,AUTO)
        self.assertEqual(d.action,'blocked');self.assertEqual(dict(c.roles),before)

    def test_no_escalation_does_not_allow_compatibility_to_bypass_effort_floor(self):
        for native in (True,False):
            c=host(current=C('sol','medium'),current_sufficient=False,no_escalation=True,host_can_set_effort=native)
            self.assertEqual(plan(SOL,c,AUTO,deep_reasoning=True).action,'blocked')

    def test_no_routing_keeps_parent_or_blocks_without_hidden_session(self):
        for sufficient in (True,False):
            c=host(current=C('luna','medium'),current_sufficient=sufficient,host_supports_routing=False)
            self.assertEqual(plan(S(),c,AUTO).action,'local' if sufficient else 'blocked')

    def test_invalid_task_failure_cache_is_rejected(self):
        for value in (['x'], frozenset((1,)), frozenset(('',))):
            with self.assertRaises(ValueError):plan(S(),host(unavailable_roles=value),AUTO)

    def test_confirmed_new_model_failure_can_use_exact_legacy_binding(self):
        c=host(current=C('luna','high'),current_sufficient=False,
               unavailable_models={'gpt-6-sol':'host rejected selected model'})
        roles=dict(c.roles)
        roles['cer_auto_sol_engineer']=RoleBinding('gpt-5.6-sol',None)
        roles['sol_engineer']=RoleBinding('gpt-5.6-sol','medium')
        catalog=dict(c.catalog);catalog['gpt-5.6-sol']=frozenset(('medium','high'))
        d=plan(S(),replace(c,roles=roles,catalog=catalog),AUTO)
        self.assertEqual((d.action,d.requested.model,d.requested_role),
                         ('delegate','gpt-5.6-sol','cer_auto_sol_engineer'))
        self.assertIn('legacy fallback',d.reason)

    def test_legacy_fallback_needs_unavailability_evidence_and_respects_model_lock(self):
        c=host(current=C('luna','high'),current_sufficient=False)
        roles=dict(c.roles)
        roles['cer_auto_sol_engineer']=RoleBinding('gpt-5.6-sol',None)
        roles['sol_engineer']=RoleBinding('gpt-5.6-sol','medium')
        catalog=dict(c.catalog);catalog['gpt-5.6-sol']=frozenset(('medium',))
        self.assertEqual(plan(S(),replace(c,roles=roles,catalog=catalog),AUTO).action,'blocked')
        c=replace(c,roles=roles,catalog=catalog,
                  unavailable_models={'gpt-6-sol':'host rejected selected model'},keep_model=True)
        self.assertEqual(plan(S(),c,AUTO).action,'blocked')

    def test_complex_sol_never_falls_back_to_terra(self):
        s=S(reasoning_bound=False,coupling=2)
        c=host(current=C('luna','high'),current_sufficient=False,
               unavailable_models={'gpt-6-sol':'host rejected selected model'})
        roles=dict(c.roles)
        del roles['cer_auto_sol_engineer'];del roles['sol_engineer']
        catalog=dict(c.catalog);catalog['gpt-5.6-terra']=frozenset(('medium','high'))
        self.assertEqual(plan(s,replace(c,roles=roles,catalog=catalog),AUTO).action,'blocked')

    def test_new_scope_reclassifies_after_transient_capacity_without_stale_blacklist(self):
        new_duties=S(coupling=2,uncertainty=2,risk=1)
        context=host(current=C('luna','high'),current_sufficient=False,
                     change_event='classified_failure',failure_kind='environment')
        decision=plan(new_duties,context,AUTO)
        self.assertEqual(decision.requested,C('sol','high'))
        self.assertEqual(decision.requested_role,'cer_auto_sol_engineer')
        retained=host(current=C('sol','high'),current_sufficient=True,benefit_clear=False,
                      change_event='classified_failure',failure_kind='environment')
        self.assertEqual(plan(new_duties,retained,AUTO).action,'local')

    def test_ultra_never_falls_back_to_terra(self):
        evidence=EffortEvidence(
            bottleneck='two independent compatibility proofs remain',
            high_limit='high cannot coordinate both proofs within the boundary',
            extra_effort_value='ultra coordinates the disjoint proofs once',
            high_insufficient=True, independent_units=2, disjoint_ownership=True,
            net_benefit=True, coordinator_authorized=True,
            coordinator_contract_verified=True, single_coordinator=True,
            capacity_available=True, shared_limits_retained=True)
        c=host(current=C('luna','high'),current_sufficient=False,
               unavailable_models={'gpt-6-sol':'unavailable','gpt-5.6-sol':'unavailable'})
        catalog=dict(c.catalog);catalog['gpt-5.6-terra']=frozenset(('medium','high','ultra'))
        self.assertEqual(plan(S(),replace(c,catalog=catalog),AUTO,
                              automatic_effort='ultra',effort_evidence=evidence).action,'blocked')

if __name__=='__main__':unittest.main()
