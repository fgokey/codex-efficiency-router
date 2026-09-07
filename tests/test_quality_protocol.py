"""Finite declared-input checks; NOT a live Codex behavioral evaluation."""
import sys
import unittest
from dataclasses import replace
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from quality_reference import Contract, Evidence, Failure, Unit, completion, handoff, retry, resume


class QualityProtocolTests(unittest.TestCase):
    def setUp(self):
        self.contract = Contract('r1', 'code+tests+env-v1', ('behavior', 'integration'))
        self.evidence = tuple(Evidence(item, 'PASS', 'r1', self.contract.state, 'command', 'Observed exit 0; expected output matched')
                              for item in self.contract.required)
        self.key = Unit('task-a', 'unit-1', 'observable-failure')

    def failure(self, worker='worker-1', approach='approach-1', kind='implementation', key=None):
        return Failure(key or self.key, worker, approach, kind)

    def test_complete_current_required_evidence_passes(self):
        self.assertEqual(completion(self.contract, self.evidence).status, 'PASS')

    def test_missing_requirement_cannot_pass(self):
        self.assertEqual(completion(self.contract, self.evidence[:1]).status, 'PARTIAL')

    def test_disclosure_and_unknown_do_not_waive_requirement(self):
        evidence = (self.evidence[0], replace(self.evidence[1], verdict='UNKNOWN', detail='Cannot run; disclosed'))
        self.assertEqual(completion(self.contract, evidence).status, 'PARTIAL')

    def test_failed_required_check_cannot_pass(self):
        for index in (0, 1):
            evidence = list(self.evidence)
            evidence[index] = replace(evidence[index], verdict='FAIL')
            self.assertEqual(completion(self.contract, tuple(evidence)).status, 'PARTIAL')

    def test_schema_valid_claim_is_not_observed_evidence(self):
        evidence = tuple(replace(item, kind='claim', detail='I verified everything') for item in self.evidence)
        self.assertEqual(completion(self.contract, evidence).status, 'PARTIAL')

    def test_stale_code_test_or_environment_requires_revalidation(self):
        self.assertEqual(completion(replace(self.contract, state='same-HEAD+changed-tests'), self.evidence).status, 'PARTIAL')

    def test_changed_contract_invalidates_old_acceptance(self):
        self.assertEqual(completion(replace(self.contract, revision='r2'), self.evidence).status, 'PARTIAL')

    def test_blocking_finding_overrides_green_checks(self):
        self.assertEqual(completion(self.contract, self.evidence, blocked=True).status, 'BLOCKED')

    def test_readonly_design_can_use_reasoned_review(self):
        evidence = tuple(replace(item, kind='review', detail='Compared alternatives and documented criterion evidence')
                         for item in self.evidence)
        self.assertEqual(completion(self.contract, evidence).status, 'PASS')

    def test_no_vacuous_pass_empty_requirements(self):
        with self.assertRaises(ValueError):
            completion(replace(self.contract, required=()), ())

    def test_duplicate_or_unknown_evidence_not_silently_overwritten(self):
        for evidence in (self.evidence + self.evidence[:1], (replace(self.evidence[0], requirement='invented'),)):
            with self.assertRaises(ValueError):
                completion(self.contract, evidence)

    def test_invalid_evidence_or_flags_rejected(self):
        for field, value in (('verdict', 'SKIPPED'), ('kind', 'self-certified'), ('detail', ''), ('state', None)):
            with self.assertRaises(ValueError):
                completion(self.contract, (replace(self.evidence[0], **{field: value}),))
        with self.assertRaises(ValueError):
            completion(self.contract, self.evidence, blocked=1)

    def test_every_combination_of_handoff_gate(self):
        for complete, aligned, assumptions, authorized, state in product((False, True), repeat=5):
            expected = 'BLOCKED' if not (complete and aligned and authorized) else 'RECHECK' if not (assumptions and state) else 'READY'
            self.assertEqual(handoff(complete=complete, aligned=aligned, assumptions_checked=assumptions,
                                     authorized=authorized, state_current=state), expected)

    def test_handoff_does_not_treat_string_false_as_true(self):
        with self.assertRaises(ValueError):
            handoff(complete='false', aligned=True, assumptions_checked=True, authorized=True, state_current=True)

    def test_one_targeted_repair_allowed(self):
        self.assertEqual(retry(self.key, (self.failure(),), history_known=True, next_approach='targeted-fix'), 'ATTEMPT')

    def test_new_worker_cannot_reset_budget(self):
        failures = (self.failure('terra'), self.failure('sol', 'targeted-fix'))
        self.assertEqual(retry(self.key, failures, history_known=True, next_approach='third-patch'), 'DIAGNOSE')

    def test_unknown_history_after_compaction_is_not_zero(self):
        self.assertEqual(retry(self.key, (), history_known=False, next_approach='patch'), 'RECONCILE')

    def test_identical_failed_approach_requires_new_evidence(self):
        failures = (self.failure(),)
        self.assertEqual(retry(self.key, failures, history_known=True, next_approach='approach-1'), 'DIAGNOSE')
        self.assertEqual(retry(self.key, failures, history_known=True, next_approach='approach-1', new_evidence='Discriminating check explains former failure'), 'ATTEMPT')

    def test_new_evidence_alone_cannot_reset_exhausted_budget(self):
        failures = (self.failure('a'), self.failure('b', 'fix'))
        self.assertEqual(retry(self.key, failures, history_known=True, next_approach='new', new_evidence='new log'), 'DIAGNOSE')

    def test_explicit_bounded_extension_preserves_old_attempts(self):
        failures = (self.failure('a'), self.failure('b', 'fix'))
        with self.assertRaises(ValueError):
            retry(self.key, failures, history_known=True, next_approach='new', extension=1)
        self.assertEqual(retry(self.key, failures, history_known=True, next_approach='new', extension=1,
                               extension_reason='Parent: experiment isolated a new fault; one repair'), 'ATTEMPT')
        failures += (self.failure('c', 'new'),)
        self.assertEqual(retry(self.key, failures, history_known=True, next_approach='another', extension=1,
                               extension_reason='Same extension, not a reset'), 'DIAGNOSE')

    def test_other_task_history_does_not_consume_this_task_budget(self):
        failures = tuple(self.failure(key=Unit('other', 'unit-1', 'observable-failure')) for _ in range(3))
        self.assertEqual(retry(self.key, failures, history_known=True, next_approach='new'), 'ATTEMPT')

    def test_failure_taxonomy_before_retry(self):
        for kind, expected in [('environment', 'PREREQUISITE'), ('observability', 'PREREQUISITE'),
                               ('specification', 'PREREQUISITE'), ('capability', 'DIAGNOSE')]:
            self.assertEqual(retry(self.key, (self.failure(kind=kind),), history_known=True, next_approach='new'), expected)

    def test_retry_rejects_bad_budget_and_history(self):
        for extension in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                retry(self.key, (), history_known=True, next_approach='new', extension=extension)
        with self.assertRaises(ValueError):
            retry(self.key, (), history_known='yes', next_approach='new')

    def test_completed_work_is_reused_not_reimplemented(self):
        self.assertEqual(resume(self.contract, self.evidence, saved_contract_revision='r1', worker_state='idle', side_effect_state='none'), 'REUSE')

    def test_changed_state_revalidates_completed_unit(self):
        self.assertEqual(resume(replace(self.contract, state='changed'), self.evidence, saved_contract_revision='r1', worker_state='idle', side_effect_state='none'), 'REVALIDATE')

    def test_contract_change_reopens_work(self):
        self.assertEqual(resume(self.contract, self.evidence, saved_contract_revision='old', worker_state='idle', side_effect_state='none'), 'REVALIDATE')

    def test_partial_work_continues_instead_of_false_reuse(self):
        self.assertEqual(resume(self.contract, self.evidence[:1], saved_contract_revision='r1', worker_state='idle', side_effect_state='none'), 'CONTINUE')

    def test_live_or_unknown_worker_prevents_redispatch(self):
        for worker, expected in [('active', 'WAIT'), ('unknown', 'RECONCILE')]:
            self.assertEqual(resume(self.contract, self.evidence, saved_contract_revision='r1', worker_state=worker, side_effect_state='none'), expected)

    def test_uncertain_external_side_effect_is_not_replayed(self):
        self.assertEqual(resume(self.contract, self.evidence, saved_contract_revision='r1', worker_state='idle', side_effect_state='unknown'), 'RECONCILE')

    def test_known_blocker_prevents_false_reuse(self):
        self.assertEqual(resume(self.contract, self.evidence, saved_contract_revision='r1', worker_state='idle', side_effect_state='none', blocked=True), 'BLOCKED')

    def test_recovery_rejects_unknown_labels(self):
        with self.assertRaises(ValueError):
            resume(self.contract, self.evidence, saved_contract_revision='r1', worker_state='probably-done', side_effect_state='none')


if __name__ == '__main__':
    unittest.main()
