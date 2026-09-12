from dataclasses import replace
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from write_policy import AstraWriteEvidence, Writer, WriteScope, before_action, diagnostic_action
from effort_reference import Context, Configuration as C, RoleBinding, PRESETS, plan
from policy_reference import TaskSignals as S


def scope(**kw):
    return replace(WriteScope('unit-a', True, True, True), **kw)


def astra_write(**kw):
    evidence = AstraWriteEvidence(reason='qualified_executor_failure', root_actor=True,
                                  scope_bounded=True, target_in_workspace=True,
                                  verification_defined=True, failure_kind='unexplained', qualified_attempts=2,
                                  guard_status='inactive')
    return replace(evidence, **kw)


def host(**kw):
    roles = {role: RoleBinding(m,e) for role,m,e in PRESETS.values()}
    roles.update({'cer_auto_'+r: RoleBinding(m,None) for r,m,e in PRESETS.values()})
    c=Context(current=C('astra','high'), current_sufficient=True, operation='mutation',
              write_scope=scope(), host_supports_routing=True, host_can_set_effort=True,
              safe_boundary=True, roles=roles,
              catalog={m:frozenset(('low','medium','high')) for _,m,_ in PRESETS.values()})
    return replace(c, **kw)


class WriteGateTests(unittest.TestCase):
    def test_astra_defaults_to_no_local_write_despite_privileges_or_tiny_task(self):
        for operation in ('mutation','unknown'):
            for local_owner in (False,True):
                d=before_action(operation,'gpt-6-astra',scope(local_owner=local_owner),host_supports_routing=True)
                self.assertEqual(d.action,'delegate')

    def test_astra_snapshot_is_readonly_without_exception_evidence(self):
        self.assertEqual(before_action('mutation','gpt-6-astra-2026-09-01',scope(local_owner=True)).action,'blocked')

    def test_root_astra_can_apply_one_qualified_bounded_local_patch(self):
        d=before_action('local_patch','gpt-6-astra',
                        scope(local_owner=True,astra_write=astra_write()),
                        host_supports_routing=True)
        self.assertEqual((d.action,d.exception),('local_write','bounded_astra_patch'))

    def test_context_loss_can_qualify_without_fake_failed_attempts(self):
        evidence=astra_write(reason='critical_context_loss',qualified_attempts=0)
        d=before_action('local_patch','gpt-6-astra',scope(local_owner=True,astra_write=evidence))
        self.assertEqual(d.action,'local_write')

    def test_astra_exception_fails_closed_when_any_gate_is_missing(self):
        cases=(
            astra_write(root_actor=False), astra_write(scope_bounded=False),
            astra_write(target_in_workspace=False), astra_write(verification_defined=False),
            astra_write(qualified_attempts=1), astra_write(prior_exception_writes=1),
            astra_write(guard_status='active'), astra_write(guard_status='unknown'),
            astra_write(failure_kind='environment'), astra_write(failure_kind='specification'),
            astra_write(failure_kind='observability'),
        )
        for evidence in cases:
            with self.subTest(evidence=evidence):
                d=before_action('local_patch','gpt-6-astra',scope(local_owner=True,astra_write=evidence),
                                host_supports_routing=True)
                self.assertNotEqual(d.action,'local_write')

    def test_exception_is_only_for_explicit_local_patch(self):
        for operation in ('mutation','unknown'):
            d=before_action(operation,'gpt-6-astra',scope(local_owner=True,astra_write=astra_write()),
                            host_supports_routing=True)
            self.assertNotEqual(d.action,'local_write')

    def test_astra_leaf_readonly_role_and_active_writer_still_prevent_exception(self):
        evidence=astra_write()
        self.assertNotEqual(before_action('local_patch','gpt-6-astra',
                            scope(local_owner=True,astra_write=evidence),read_only=True,
                            host_supports_routing=True).action,'local_write')
        writers=(Writer('other','other-unit','gpt-5.6-sol','active'),)
        self.assertNotEqual(before_action('local_patch','gpt-6-astra',
                            scope(local_owner=True,astra_write=evidence,writers=writers),
                            host_supports_routing=True).action,'local_write')

    def test_read_and_orchestration_remain_local(self):
        for operation in ('read','reasoning','coordinate'):
            self.assertEqual(before_action(operation,'gpt-6-astra').action,'local_read')

    def test_unknown_identity_never_local_write(self):
        self.assertEqual(before_action('mutation',None,scope(local_owner=True)).action,'blocked')

    def test_model_change_does_not_revoke_readonly_role(self):
        self.assertEqual(before_action('mutation','gpt-5.6-sol',scope(local_owner=True),read_only=True).action,'blocked')

    def test_legitimate_exclusive_sol_owner_can_write(self):
        self.assertEqual(before_action('mutation','gpt-5.6-sol',scope(local_owner=True)).action,'local_write')

    def test_no_subagents_not_an_astra_write_exception(self):
        self.assertEqual(before_action('mutation','gpt-6-astra',scope(),no_subagents=True,host_supports_routing=True).action,'blocked')

    def test_no_subagents_does_not_block_a_fully_qualified_local_exception(self):
        d=before_action('local_patch','gpt-6-astra',scope(local_owner=True,astra_write=astra_write()),
                        no_subagents=True,host_supports_routing=True)
        self.assertEqual(d.action,'local_write')

    def test_authority_or_ownership_unknown_blocks(self):
        for field in ('authorized','ownership_clear'):
            self.assertEqual(before_action('mutation','gpt-6-astra',scope(**{field:False}),host_supports_routing=True).action,'blocked')

    def test_two_active_writers_defer_not_third_writer(self):
        ws=(Writer('a','other','gpt-5.6-sol','active'),Writer('b','another','gpt-5.6-sol','active'))
        self.assertEqual(before_action('mutation','gpt-6-astra',scope(writers=ws),host_supports_routing=True).action,'defer')

    def test_reuse_compatible_idle_owner_without_extra_slot(self):
        ws=(Writer('classification_fix','unit-a','gpt-5.6-sol','idle'),)
        d=before_action('mutation','gpt-6-astra',scope(writers=ws),host_supports_routing=True)
        self.assertEqual((d.action,d.owner),('reuse','classification_fix'))

    def test_active_compatible_owner_waits_before_scope_expansion(self):
        ws=(Writer('recovery_fix','unit-a','gpt-5.6-sol','active'),)
        self.assertEqual(before_action('mutation','gpt-6-astra',scope(writers=ws)).action,'defer')

    def test_unknown_writer_prevents_replay(self):
        ws=(Writer('old','unit-b','gpt-5.6-sol','unknown'),)
        self.assertEqual(before_action('mutation','gpt-6-astra',scope(writers=ws),host_supports_routing=True).action,'defer')

    def test_conflicting_owners_block(self):
        ws=(Writer('a','unit-a','gpt-5.6-sol','idle'),Writer('b','unit-a','gpt-5.6-terra','idle'))
        self.assertEqual(before_action('mutation','gpt-6-astra',scope(writers=ws)).action,'blocked')

    def test_ownership_not_transferred_to_incapable_or_astra_owner(self):
        for w in (Writer('a','unit-a','gpt-6-astra','idle'),Writer('a','unit-a','gpt-5.6-sol','idle',sufficient=False)):
            self.assertEqual(before_action('mutation','gpt-6-astra',scope(writers=(w,))).action,'blocked')

    def test_joint_planner_no_benefit_local_shortcut_for_astra_write(self):
        d=plan(S(),host())
        self.assertEqual((d.action,d.requested.lane),('delegate','terra'))

    def test_joint_planner_mechanical_astra_writes_go_to_terra_not_luna(self):
        d=plan(S(mechanical=True,uncertainty=0,verifiability=3),host())
        self.assertEqual((d.action,d.requested.lane),('delegate','terra'))

    def test_joint_planner_retains_root_astra_for_qualified_bounded_patch(self):
        c=host(operation='local_patch',write_scope=scope(local_owner=True,astra_write=astra_write()))
        d=plan(S(risk=3,uncertainty=3,failed_attempts=2,prior_lane='sol'),c)
        self.assertEqual(d.action,'local');self.assertIn('bounded root-Astra patch',d.reason)

    def test_joint_planner_no_route_blocks_even_sufficient_astra(self):
        for c in (host(host_supports_routing=False),host(roles={}),host(catalog={})):
            self.assertEqual(plan(S(),c).action,'blocked')

    def test_joint_planner_opt_out_cannot_fall_back_to_local_write(self):
        self.assertEqual(plan(S(no_subagents=True),host()).action,'blocked')

    def test_joint_planner_reuse_returns_existing_id_without_spawn(self):
        c=host(write_scope=scope(writers=(Writer('existing','unit-a','gpt-5.6-sol','idle'),)))
        d=plan(S(),c)
        self.assertEqual((d.action,d.owner_id,d.requested_role),('reuse','existing',None))

    def test_owner_reuse_cannot_reset_failed_write_budget(self):
        c=host(write_scope=scope(writers=(Writer('old','unit-a','gpt-5.6-sol','idle'),)),diagnosis_only=True)
        self.assertEqual(plan(S(failed_attempts=2),c).action,'blocked')

    def test_reuse_respects_model_and_effort_locks(self):
        ws=scope(writers=(Writer('old','unit-a','gpt-5.6-sol','idle',effort='high'),))
        self.assertEqual(plan(S(),host(current=C('terra','medium'),no_escalation=True,write_scope=ws)).action,'blocked')
        self.assertEqual(plan(S(),host(keep_model=True,write_scope=ws)).action,'blocked')
        self.assertEqual(plan(S(),host(write_scope=ws),explicit_effort='medium').action,'blocked')

    def test_reuse_unknown_effort_cannot_verify_ceiling(self):
        ws=scope(writers=(Writer('old','unit-a','gpt-5.6-sol','idle'),))
        self.assertEqual(plan(S(),host(no_effort_escalation=True,write_scope=ws)).action,'blocked')

    def test_complex_write_splits_out_readonly_diagnosis(self):
        d=plan(S(risk=3,uncertainty=3),host())
        self.assertEqual(d.action,'blocked'); self.assertIn('diagnosis',d.reason)

    def test_complex_task_does_not_need_failed_worker_first(self):
        self.assertEqual(diagnostic_action(model='gpt-5.6-sol',complex_judgment=True),'delegate_astra_readonly')

    def test_repeated_unexplained_failures_get_astra_diagnosis(self):
        for kind in ('unexplained','capability'):
            self.assertEqual(diagnostic_action(model='gpt-5.6-sol',qualified_attempts=2,failure_kind=kind),'delegate_astra_readonly')

    def test_failure_count_alone_is_not_astra_trigger(self):
        self.assertEqual(diagnostic_action(model='gpt-5.6-sol',qualified_attempts=20),'continue_scoped_diagnosis')

    def test_broken_environment_does_not_escalate(self):
        self.assertEqual(diagnostic_action(model='gpt-5.6-sol',complex_judgment=True,qualified_attempts=5,failure_kind='environment'),'repair_prerequisite')

    def test_astra_parent_participates_instead_of_only_dispatching(self):
        c=host(operation='reasoning', diagnosis_only=True,failure_kind='unexplained')
        d=plan(S(failed_attempts=2,prior_lane='terra'),c)
        self.assertEqual(d.action,'local');self.assertIn('read-only diagnosis',d.reason)
        # This diagnosis has NOT replenished the writing budget.
        self.assertEqual(plan(S(failed_attempts=2),host()).action,'blocked')

    def test_exhausted_workers_can_request_astra_without_repair_extension(self):
        c=host(current=C('sol','medium'),current_sufficient=False,operation='reasoning',diagnosis_only=True,failure_kind='unexplained')
        d=plan(S(failed_attempts=2,prior_lane='terra'),c)
        self.assertEqual(d.action,'delegate');self.assertIsNotNone(d.requested)
        self.assertEqual(d.requested.lane,'astra')

    def test_cheap_discriminating_check_before_strong_reasoning(self):
        self.assertEqual(diagnostic_action(model='gpt-6-astra',complex_judgment=True,cheap_check_available=True),'executor_experiment')

    def test_no_escalation_respected_but_existing_astra_can_reason(self):
        self.assertEqual(diagnostic_action(model='gpt-5.6-sol',complex_judgment=True,no_escalation=True),'blocked')
        self.assertEqual(diagnostic_action(model='gpt-6-astra',complex_judgment=True,no_escalation=True),'astra_local_readonly_diagnosis')

    def test_strict_input_validation(self):
        for ctx in (scope(authorized='yes'),scope(writer_limit=0)):
            with self.assertRaises(ValueError):before_action('mutation','gpt-6-astra',ctx)
        with self.assertRaises(ValueError):
            before_action('local_patch','gpt-6-astra',scope(astra_write=astra_write(reason='invented')))
        with self.assertRaises(ValueError):before_action('write?',None)


if __name__=='__main__':unittest.main()

class CapacityRegressionTests(unittest.TestCase):
    def test_idle_owner_cannot_become_third_active_writer(self):
        ws=(Writer('a','other','gpt-5.6-sol','active'),Writer('b','different','gpt-5.6-sol','active'),Writer('c','unit-a','gpt-5.6-sol','idle'))
        self.assertEqual(before_action('mutation','gpt-6-astra',scope(writers=ws),host_supports_routing=True).action,'defer')

    def test_unknown_model_string_not_writer_permission(self):
        self.assertEqual(before_action('mutation','future-unknown',scope(local_owner=True)).action,'blocked')

class ContinuingOwnerTests(unittest.TestCase):
    def test_existing_writer_can_continue_without_consuming_third_slot(self):
        ws=(Writer('a','unit-a','gpt-5.6-sol','active'),Writer('b','other','gpt-5.6-sol','active'))
        d=before_action('mutation','gpt-5.6-sol',scope(writers=ws,local_owner=True,actor_id='a'))
        self.assertEqual(d.action,'local_write')

    def test_claiming_ownership_without_matching_actor_does_not_override_busy_owner(self):
        ws=(Writer('a','unit-a','gpt-5.6-sol','active'),)
        self.assertEqual(before_action('mutation','gpt-5.6-sol',scope(writers=ws,local_owner=True,actor_id='b')).action,'defer')
