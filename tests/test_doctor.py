import copy
import tempfile
from unittest.mock import patch
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import doctor
from package import EXPECTED, PROJECT


class DoctorTests(unittest.TestCase):
    def test_compat_startup_report_retains_authorized_work_without_model_metadata(self):
        from profiles import Profile
        report=doctor.startup_report(Profile(host_mode='compat'),{'permission':'workspace-write'})
        self.assertEqual(report['status'],'COMPAT')
        self.assertEqual(report['current_binding'],'UNKNOWN')
        self.assertEqual(report['write_authority'],'NOT_GRANTED')
        scope=report['required']
        self.assertNotIn('planning/context/review only',scope)
        self.assertNotIn('Unknown identity/effects grant no writes',scope)
        self.assertIn('current executor can continue already authorized work',scope)
        self.assertIn('Missing model metadata adds no restriction',scope)
        self.assertIn('Read-only/Hook restrictions',scope)
        self.assertIn('separate publication authority',scope)

    def test_startup_never_authenticates_claimed_bindings_or_grants_writes(self):
        from profiles import Profile
        claimed={'model':'gpt-6.1-sol','effort':'high','permission':'full-access',
                 'role_read_only':False,'parent_released':True,
                 'interfaces':['admitted_agent_task','prepare_agent_task'],
                 'binding':{'status':'VERIFIED','session':'old'}}
        with patch.object(doctor,'source_profiles',side_effect=AssertionError('not cheap')):
            full=doctor.startup_report(Profile(),claimed)
            compat=doctor.startup_report(Profile(host_mode='compat'),claimed)
        self.assertEqual(full['host_mode'],'full')
        self.assertEqual(full['status'],'BLOCKED')
        for report in (full,compat):
            self.assertEqual(report['current_binding'],'UNKNOWN')
            self.assertEqual(report['write_authority'],'NOT_GRANTED')
            self.assertEqual(report['claim_basis'],'CALLER_SUPPLIED_NOT_AUTHENTICATED')
            self.assertEqual(report['guard']['trust'],'UNKNOWN')
            self.assertLessEqual(len(json.dumps(report).encode())+2,3072)
        self.assertEqual(compat['status'],'COMPAT')
        self.assertEqual(doctor.startup_report(Profile())['host_mode'],'full')
        missing_model=doctor.startup_report(Profile(host_mode='compat'),{'permission':'workspace-write'})
        self.assertEqual(missing_model['status'],'COMPAT')
        self.assertEqual(missing_model['current_binding'],'UNKNOWN')
        readonly=doctor.startup_report(Profile(host_mode='compat'),{'permission':'read-only','parent_released':False})
        self.assertEqual(readonly['write_authority'],'NOT_GRANTED')
        self.assertIn('Read-only/Hook restrictions',readonly['required'])

    def test_startup_claims_are_bounded_and_cannot_authenticate_hook_trust(self):
        from profiles import Profile
        huge=dict.fromkeys(('model','effort','permission','role_read_only','parent_released'),'\U0001f600'*10000)
        huge['interfaces']=['admitted_agent_task']*10000
        report=doctor.startup_report(Profile(host_mode='compat'),huge,
                 guard={'registration':'PRESENT','trust':'VERIFIED'},dispatch_guard={'registration':'BROKEN'})
        self.assertLessEqual(len(json.dumps(report).encode())+2,3072)
        self.assertEqual(report['guard']['registration'],'PRESENT')
        self.assertEqual(report['guard']['dispatch_registration'],'BROKEN')
        self.assertEqual(report['guard']['trust'],'UNKNOWN')
        with self.assertRaises(ValueError):doctor.startup_report(Profile(),[])

    def test_compat_does_not_bypass_existing_execution_admission(self):
        import runpy
        check=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))['execution_admission']
        baseline={'effects':['write'],'permission':'workspace-write','role_read_only':False,'parent_released':True}
        self.assertEqual(check(baseline,'gpt-6.1-sol'),'VERIFIED')
        self.assertEqual(check(dict(baseline,permission='read-only'),'gpt-6.1-sol'),'MISMATCH')
        self.assertEqual(check(dict(baseline,role_read_only=True),'gpt-6.1-sol'),'MISMATCH')
        self.assertEqual(check(dict(baseline,parent_released=False),'gpt-6.1-sol'),'UNKNOWN')
        self.assertEqual(check(dict(baseline,host_mode='compat'),'gpt-6.1-sol'),'UNKNOWN')
        self.assertEqual(check(dict(baseline,effects=['publish']),'gpt-6.1-sol'),'UNKNOWN')
        from effort_reference import plan
        from profiles import Profile
        with self.assertRaisesRegex(ValueError,'full-mode admission is not used'):
            plan(None,None,Profile(host_mode='compat'))

    def test_startup_cli_is_cheap_and_mode_override_does_not_change_installation(self):
        command=[sys.executable,'-B',str(ROOT/'scripts/doctor.py'),
                 '--source-tree',str(ROOT),'--startup']
        full=subprocess.run(command,capture_output=True,text=True)
        compat=subprocess.run(command+['--host-mode','compat'],capture_output=True,text=True)
        self.assertEqual(full.returncode,1,full.stderr)
        self.assertEqual(compat.returncode,0,compat.stderr)
        self.assertEqual(json.loads(full.stdout)['current_binding'],'UNKNOWN')
        report=json.loads(compat.stdout)
        self.assertEqual(report['host_mode'],'compat')
        self.assertEqual(report['persisted_host_mode'],'full')

    def test_real_cli_does_not_present_policy_pass_as_parent_completion_enforcement(self):
        # Diagnostic regression only: this does not replay model finalization.
        command = [sys.executable, '-B', str(ROOT / 'scripts/doctor.py'),
                   '--source-tree', str(ROOT)]
        structured = subprocess.run(command + ['--json'], capture_output=True, text=True)
        self.assertEqual(structured.returncode, 0, structured.stderr)
        report = json.loads(structured.stdout)
        self.assertEqual(report['policy'], 'PASS')
        self.assertEqual(report['parent_completion'], {
            'router_policy': 'INSTRUCTION_ONLY', 'native_gate': 'UNKNOWN'})
        plain = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertIn('parent completion: Router instruction policy; native gate: UNKNOWN',
                      plain.stdout)

    def catalog(self):
        return {"result": {"data": [
            {"model": model, "supportedReasoningEfforts": [{"reasoningEffort": effort}]}
            for _, model, effort in EXPECTED.values()], "nextCursor": None}}

    def test_instruction_chain_follows_links_not_orphan_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / 'SKILL.md'
            entry.write_text('[quality](quality.md)', encoding='utf-8')
            (root / 'quality.md').write_text('reachable contract', encoding='utf-8')
            (root / 'orphan.md').write_text('unreachable contract', encoding='utf-8')
            chain = doctor.instruction_chain(entry)
            self.assertEqual(set(chain), {'SKILL.md', 'quality.md'})
            self.assertNotIn('unreachable contract', '\n'.join(chain.values()))
            entry.write_text('[missing](missing.md)', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'not packaged'):
                doctor.instruction_chain(entry)
            entry.write_text('[escape](../outside.md)', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'not packaged'):
                doctor.instruction_chain(entry)

    def test_cheap_entry_cannot_move_root_readonly_boundary_into_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'skill'
            shutil.copytree(ROOT / 'skills' / PROJECT, root)
            entry = root / 'SKILL.md'
            text = entry.read_text(encoding='utf-8')
            entry.write_text(text.replace('Root Astra defaults read-only', 'Root Astra'), encoding='utf-8')
            dispatch = root / 'references/dispatch.md'
            dispatch.write_text(dispatch.read_text(encoding='utf-8') + '\nRoot Astra defaults read-only\n', encoding='utf-8')
            self.assertIn('Root Astra defaults read-only', '\n'.join(doctor.instruction_chain(entry).values()))
            errors = doctor.validate_tree(entry, ROOT / 'agents')
            self.assertIn('missing entry authority boundary: Root Astra defaults read-only', errors)

    def test_preflight_checks_every_profile_before_tests(self):
        profiles = doctor.source_profiles(ROOT)
        self.assertEqual([row['mode'] for row in profiles], ['fixed', 'auto', 'adaptive'])
        for row in profiles:
            self.assertLessEqual(row['full_bytes'], 10800)
        with patch('manage.source_files', return_value={}), patch('profiles.render_payload') as render:
            render.side_effect = lambda payload, profile: {'skill/SKILL.md': b'x' * (10801 if profile.mode == 'adaptive' else 1)}
            with self.assertRaisesRegex(ValueError, 'adaptive'):
                doctor.source_profiles(ROOT)
        with patch.object(doctor, 'source_profiles', side_effect=ValueError('bad profile')), \
                patch.object(doctor, 'target_tests') as tests:
            with self.assertRaisesRegex(ValueError, 'bad profile'):
                doctor.preflight(ROOT)
            tests.assert_not_called()

    def test_preflight_is_source_only_and_bounds_failure_output(self):
        with self.assertRaisesRegex(ValueError, "this repository"):
            doctor.preflight(ROOT.parent)
        tests = {'run':8, 'passed':0, 'success':False, 'skipped':0, 'failures':8, 'errors':0,
                 'details':[{'id':'test'+str(i),'reason':'界'*500} for i in range(8)], 'omitted_details':0}
        with patch.object(doctor, 'source_profiles', return_value=[]), patch.object(doctor, 'target_tests', return_value=tests):
            report = doctor.preflight(ROOT)
        self.assertEqual(report['policy'], 'FAIL')
        self.assertEqual(report['target_tests']['failures'], 8)
        self.assertGreater(report['target_tests']['omitted_details'], 0)
        self.assertLessEqual(len(json.dumps(report, ensure_ascii=False).encode('utf-8')) + 2, 3072)
        self.assertEqual(report['enforcement'], 'NOT_VERIFIED')

    def test_preflight_unexpected_success_and_subtests_cannot_pass(self):
        class Samples(unittest.TestCase):
            @unittest.expectedFailure
            def test_expected_failure(self):
                self.fail('known failure')

            @unittest.expectedFailure
            def test_unexpected_success(self):
                pass

            def test_subtests(self):
                for value in range(2):
                    with self.subTest(value=value):
                        self.fail('subtest failure')

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Samples)
        with patch.object(unittest.defaultTestLoader, 'discover', side_effect=[suite] + [unittest.TestSuite() for _ in range(4)]):
            report = doctor.target_tests(ROOT)
        self.assertFalse(report['success'])
        self.assertEqual(report['run'], 3)
        self.assertEqual(report['passed'], 0)
        self.assertEqual(report['expected_failures'], 1)
        self.assertEqual(report['unexpected_successes'], 1)
        self.assertEqual(report['failures'], 2)
        with patch.object(doctor, 'source_profiles', return_value=[]), patch.object(doctor, 'target_tests', return_value=report):
            self.assertEqual(doctor.preflight(ROOT)['policy'], 'FAIL')

    def test_source_integrity(self):
        self.assertEqual(doctor.validate_tree(ROOT / "skills" / PROJECT / "SKILL.md", ROOT / "agents"), [])

    def test_truncation_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "skill"
            shutil.copytree(ROOT / "skills" / PROJECT, skill)
            p = skill / "SKILL.md"
            p.write_text(p.read_text(encoding="utf-8").split("## Delegate")[0], encoding="utf-8")
            self.assertTrue(doctor.validate_tree(p, ROOT / "agents"))

    def test_valid_export_and_raw_result(self):
        data = self.catalog()
        self.assertEqual(doctor.validate_catalog(data), [])
        self.assertEqual(doctor.validate_catalog(data["result"]), [])

    def test_incomplete_catalog_refused(self):
        data = self.catalog()
        data["result"]["nextCursor"] = "more"
        self.assertTrue(doctor.validate_catalog(data))

    def test_missing_model_or_effort(self):
        for field in ("model", "supportedReasoningEfforts"):
            data = self.catalog()
            data["result"]["data"][0][field] = "missing" if field == "model" else []
            self.assertTrue(doctor.validate_catalog(data))

    def test_malformed_catalog(self):
        for data in (None, [], {}, {"result": []}, {"data": [None]}, {"data": [{"model": [], "supportedReasoningEfforts": []}]}):
            with self.subTest(data=data):
                self.assertTrue(doctor.validate_catalog(data))

    def test_policy_manifest_matches_shipped_models(self):
        policy = json.loads((ROOT / "policy/routing-policy.json").read_text())
        actual = {(v["model"], v["effort"]) for v in policy["models"].values()}
        self.assertEqual(actual | {(policy['prior_sol_model'], 'medium')},
                         {(m, e) for _, m, e in EXPECTED.values()})
        self.assertIn("benefit_gated_deescalation", policy["principles"])
        self.assertIn("bounded_output_envelope_before_batch_reads", policy["principles"])
        self.assertIn("model_roundtrips_are_budgeted_even_with_cached_input", policy["principles"])
        self.assertIn("tool_discovery_reused_until_invalidation", policy["principles"])
        self.assertIn("worker_monitoring_uses_backoff_and_delta_cursors", policy["principles"])
        self.assertIn("scoped_repair_binding_reused_until_invalidation", policy["principles"])
        self.assertIn("forward_mutation_is_separate_from_destructive_recovery", policy["principles"])
        self.assertIn("policy_denial_stops_equivalent_replay", policy["principles"])
        self.assertIn("parent_reviews_complete_diff_validation_and_blocking_findings", policy["principles"])
        self.assertIn("every_batched_read_member_is_bounded_before_content", policy["principles"])
        self.assertIn("semantic_invariants_checked_before_implementation", policy["principles"])
        self.assertIn("loss_requires_preserved_effects_or_supported_recovery", policy["principles"])
        self.assertIn("review_findings_trace_changed_behavior_or_requirements", policy["principles"])
        self.assertIn("long_command_continuation_owned_by_executor", policy["principles"])
        self.assertEqual(policy["context_efficiency"], {
            "mandatory_rules": "separate bounded chunks until the required text is complete",
            "unknown_size": "index, summarize or split before combining; line count alone does not bound content volume",
            "batch": "capture shell, web and nested-tool results, select needed fields and retain cursors; serialize/count their total output plus framing before emitting one page within the smallest outer tool cap",
            "mixed_command": "every result counts against the outer envelope",
            "truncation": "recover only the missing relevant range from its cursor without replaying effects; disclose omitted evidence",
            "tool_discovery": "reuse known schemas until host or state invalidation",
            "roundtrip": "act only on changed state or a due checkpoint; batch bounded independent checks",
            "worker_progress": "after two unchanged snapshots read one saved-offset delta, then back off until change or due; no overlapping tails, status nudges or short polls",
            "search_limits": "rg -m and line counts limit each file's matches or lines, not total bytes",
        })
        self.assertEqual(policy["mutation_admission"], {
            "writer_binding": "parent verifies current agent/session host-observed model, effort, role, permission and owner once per scoped repair unit; same-session reuse until those fields change or contradictory evidence appears; real resume voids release, returns read-only, then parent checks new host binding and sends a separate release; resumed model may change",
            "repair_unit": "implementation, source/build config, formatting, targeted tests and self-check need no per-command reauthorization",
            "separate_units": "binary copy, runtime/permission config, deployment and destructive recovery remain separately bounded",
            "policy_denial": "stop exact or equivalent replay until a supported permission change",
            "approval_never": "approval=never alone is not a manual-action boundary",
        })

    def test_shipped_core_budget(self):
        core = (ROOT / "skills" / PROJECT / "SKILL.md").read_bytes()
        self.assertLessEqual(len(core), 8000)


if __name__ == "__main__":
    unittest.main()
