import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_runs import compare
from compare_v2 import compare_two


class PairedAccountingTests(unittest.TestCase):
    def rows(self, trials=3, families=3):
        rows=[]
        for family in range(families):
            for trial in range(trials):
                for n,variant in enumerate(('off','on')):
                    scope=f'{family}/{variant}-{trial}'
                    rows.append(dict(task_id=f'family-{family}',trial_id=str(trial),environment_id='env',
                        input_id=f'input-{family}',acceptance_id=f'oracle-{family}',variant=variant,outcome='pass',
                        elapsed_seconds=10-n,critical_path_seconds=5,waiting_seconds=1,
                        calls_complete=True,run_order=(trial+n)%2+1,randomized_order=True,
                        skills_enabled=variant=='on',isolation_evidence=f'checked:{scope}',
                        parent_call_id='parent',owned_scope_ids=[scope],
                        astra_writes=0,duplicate_writers=0,retry_replays=0,
                        calls=[dict(call_id='parent',scope_id=scope,usage_semantics='per_call',model='gpt-6.1-sol',effort='ultra',
                            attempt=1,status='completed',input_tokens=100,cached_input_tokens=80,
                            output_tokens=20,reasoning_tokens=10)]))
        return rows

    def test_two_arms_separate_token_wall_quality_from_unknown_money(self):
        result=compare(self.rows())
        self.assertTrue(result['claim_eligibility']['total_tokens'])
        self.assertTrue(result['claim_eligibility']['elapsed_seconds'])
        self.assertFalse(result['claim_eligibility']['monetary_cost'])
        self.assertEqual(result['measurements']['total_tokens']['on'],1080)
        self.assertEqual(result['measurements']['cached_input_tokens']['off'],720)
        self.assertEqual(result['measurements']['monetary_cost']['status'],'UNKNOWN')

    def test_paired_controls_and_ownership_fail_closed(self):
        for key,value in (('environment_id','other'),('input_id','other'),('acceptance_id','other'),
                          ('skills_enabled',False),('isolation_evidence',''),('owned_scope_ids',[])):
            rows=self.rows(); rows[1][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): compare_two(rows)
        for key,value in (('model','gpt-6-astra'),('effort','high'),('scope_id','unowned')):
            rows=self.rows(); rows[1]['calls'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): compare_two(rows)

    def test_missing_counter_does_not_invent_zero_or_erase_wall_measurement(self):
        rows=self.rows(); rows[1]['calls'][0].pop('input_tokens')
        result=compare_two(rows)
        self.assertFalse(result['claim_eligibility']['total_tokens'])
        self.assertTrue(result['claim_eligibility']['elapsed_seconds'])
        self.assertEqual(result['measurements']['total_tokens']['status'],'UNKNOWN')
        rows[1]['calls_complete']=False
        self.assertFalse(compare_two(rows)['claim_eligibility']['elapsed_seconds'])

    def test_retries_and_shared_parent_are_included_once(self):
        rows=self.rows(); row=rows[1]
        row['calls'].append(dict(row['calls'][0],call_id='retry',attempt=2,status='failed'))
        row['shared_parent_scope_ids']=list(row['owned_scope_ids'])
        row['shared_parent_attribution']='entire shared preparation belongs to this run'
        result=compare_two(rows)
        self.assertEqual(result['measurements']['total_tokens']['on'],1200)
        self.assertEqual(result['runs'][1]['shared_parent_scope_ids'],row['owned_scope_ids'])
        rows[3]['owned_scope_ids']=list(row['owned_scope_ids'])
        rows[3]['calls'][0]['scope_id']=row['owned_scope_ids'][0]
        with self.assertRaises(ValueError): compare_two(rows)

    def test_cumulative_repeated_snapshots_use_final_totals(self):
        rows=self.rows(); call=rows[1]['calls'][0]
        snapshots=[dict(sequence=1,input_tokens=50,cached_input_tokens=40,output_tokens=10),
                   dict(sequence=2,input_tokens=100,cached_input_tokens=80,output_tokens=20,final=True)]
        call['usage_snapshots']=[snapshots[0],copy.deepcopy(snapshots[0]),snapshots[1]]
        self.assertEqual(compare_two(rows)['measurements']['total_tokens']['on'],1080)
        call['usage_snapshots'][-1]['final']=False
        self.assertFalse(compare_two(rows)['claim_eligibility']['total_tokens'])
        call['usage_snapshots'][1]['input_tokens']=51
        with self.assertRaises(ValueError): compare_two(rows)

    def test_invalid_counters_labels_and_adverse_trials_are_retained(self):
        for key,value in (('cached_input_tokens',101),('reasoning_tokens',21),('effort','imaginary')):
            rows=self.rows(); rows[1]['calls'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): compare_two(rows)
        rows=self.rows(); rows[1]['variant']='router'
        with self.assertRaises(ValueError): compare_two(rows)
        rows=self.rows(); rows[1]['outcome']='fail'
        self.assertFalse(compare_two(rows)['claim_eligibility']['total_tokens'])
        self.assertFalse(compare_two(self.rows(1))['claim_eligibility']['total_tokens'])

    def test_cli_accepts_two_arms_and_rejects_failed_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'runs.json'; rows=self.rows()
            for expected in (0,1):
                path.write_text(json.dumps(rows),encoding='utf-8')
                proc=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve().parents[1]/'scripts/compare_runs.py'),
                                     str(path)],capture_output=True,text=True,timeout=10)
                self.assertEqual(proc.returncode,expected,proc.stderr)
                self.assertEqual(json.loads(proc.stdout)['schema'],4)
                rows[1]['outcome']='fail'

    def test_unpaired_missing_parent_and_changed_frozen_controls_are_rejected(self):
        for change in ('unpaired','parent','control','duplicate'):
            rows=self.rows()
            if change=='unpaired': rows.pop()
            elif change=='parent': rows[1]['parent_call_id']='missing'
            elif change=='control': rows[2]['input_id']='different'
            else: rows[1]['calls'].append(copy.deepcopy(rows[1]['calls'][0]))
            with self.subTest(change=change),self.assertRaises(ValueError): compare_two(rows)

    def test_snapshot_regressions_and_counter_conflicts_fail_closed(self):
        for change in ('regression','subset','after-final','conflict'):
            rows=self.rows(); call=rows[1]['calls'][0]
            call['usage_snapshots']=[dict(sequence=1,input_tokens=50,cached_input_tokens=40,output_tokens=10),
                dict(sequence=2,input_tokens=100,cached_input_tokens=80,output_tokens=20,final=True)]
            if change=='regression': call['usage_snapshots'][1]['input_tokens']=49
            elif change=='subset': call['usage_snapshots'][0]['cached_input_tokens']=51
            elif change=='after-final': call['usage_snapshots'][0]['final']=True
            else: call['input_tokens']=101
            with self.subTest(change=change),self.assertRaises(ValueError): compare_two(rows)

    def test_scope_cumulative_counters_cannot_double_count_calls(self):
        rows=self.rows(); call=rows[1]['calls'][0]
        call['usage_semantics']='scope_cumulative'
        call['usage_snapshots']=[dict(sequence=2,input_tokens=100,cached_input_tokens=80,output_tokens=20,final=True)]
        self.assertEqual(compare_two(rows)['measurements']['total_tokens']['on'],1080)
        rows[1]['calls'].append(dict(call,call_id='retry',attempt=2))
        with self.assertRaises(ValueError): compare_two(rows)
        rows=self.rows(); rows[1]['calls'][0].pop('usage_semantics')
        with self.assertRaises(ValueError): compare_two(rows)

    def test_distinct_per_call_invocations_share_scope_and_attempt_one(self):
        rows=self.rows(); row=rows[1]
        row['calls'].append(dict(row['calls'][0],call_id='second-call',status='failed'))
        result=compare_two(rows)
        self.assertEqual(result['measurements']['total_tokens']['on'],1200)
        self.assertEqual([call['attempt'] for call in result['runs'][1]['calls']],[1,1])
        self.assertEqual(result['runs'][1]['per_model']['gpt-6.1-sol']['statuses'],{'completed':1,'failed':1})
        self.assertTrue(result['claim_eligibility']['total_tokens'])

    def test_per_call_id_and_scope_cumulative_guards_remain_distinct(self):
        rows=self.rows(); row=rows[1]
        row['calls'].append(dict(row['calls'][0],call_id='child',attempt=2))
        row['calls'].append(dict(row['calls'][0],call_id='child',attempt=3))
        with self.assertRaisesRegex(ValueError,'duplicate call_id'): compare_two(rows)
        for reverse in (False,True):
            rows=self.rows(); row=rows[1]
            row['calls'].append(dict(row['calls'][0],call_id='scope-total',usage_semantics='scope_cumulative',
                usage_snapshots=[dict(sequence=1,input_tokens=100,cached_input_tokens=80,output_tokens=20,final=True)]))
            if reverse: row['calls'].reverse()
            with self.subTest(reverse=reverse),self.assertRaisesRegex(ValueError,'cumulative scope totals'):
                compare_two(rows)

    def test_formal_sampling_requires_three_families_with_three_pairs_each(self):
        for families,trials in ((1,3),(2,3),(3,2)):
            result=compare_two(self.rows(trials=trials,families=families))
            with self.subTest(families=families,trials=trials):
                self.assertFalse(result['formal_sampling_ready'])
                self.assertFalse(result['claim_eligibility']['total_tokens'])
                self.assertFalse(result['claim_eligibility']['elapsed_seconds'])
                self.assertEqual(result['measurements']['total_tokens']['status'],'measured')
                self.assertEqual(result['matched_trials'],families*trials)
        self.assertTrue(compare_two(self.rows())['formal_sampling_ready'])

    def test_missing_or_invalid_paired_order_is_controlled_cli_input_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'runs.json'
            for value in ('missing',None,False,True,0,3,1.0,'1'):
                rows=self.rows()
                if value=='missing': rows[0].pop('run_order')
                else: rows[0]['run_order']=value
                path.write_text(json.dumps(rows),encoding='utf-8')
                proc=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve().parents[1]/'scripts/compare_runs.py'),
                                     str(path)],capture_output=True,text=True,timeout=10)
                with self.subTest(value=value):
                    self.assertEqual(proc.returncode,2,proc.stderr)
                    self.assertNotIn('Traceback',proc.stderr)


class ComparisonTests(unittest.TestCase):
    def rows(self):
        base = dict(task_id="a", trial_id="1", environment_id="repo-rev/env-v1",
                    acceptance_id="checks-v1", variant="baseline", outcome="pass",
                    total_tokens=100, expensive_model_tokens=80, elapsed_seconds=20)
        routed = dict(base, variant="router", total_tokens=70, expensive_model_tokens=20, elapsed_seconds=15)
        return [base, routed]

    def test_paired_measurements(self):
        result = compare(self.rows())
        self.assertEqual(result["quality_status"], "no_observed_regression")
        self.assertAlmostEqual(result["measurements"]["total_tokens"]["reduction_fraction"], 0.3)

    def test_regression_overrides_savings(self):
        rows = self.rows()
        rows[1]["outcome"] = "fail"
        self.assertEqual(compare(rows)["quality_status"], "regression")

    def test_unknown_quality_is_not_pass(self):
        rows = self.rows()
        rows[1]["outcome"] = "unknown"
        self.assertEqual(compare(rows)["quality_status"], "unknown")

    def test_missing_metrics_are_not_zero(self):
        rows = self.rows()
        del rows[1]["total_tokens"]
        self.assertEqual(compare(rows)["measurements"]["total_tokens"], {"status": "unknown"})

    def test_invalid_numbers(self):
        for value in (-1, float("nan"), float("inf"), True, "10", 1.5):
            rows = self.rows()
            rows[1]["total_tokens"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                compare(rows)

    def test_duplicate_or_unpaired(self):
        rows = self.rows()
        for bad in (rows[:1], rows + [rows[0]], []):
            with self.assertRaises(ValueError):
                compare(bad)

    def test_changed_conditions(self):
        for key in ("environment_id", "acceptance_id"):
            rows = self.rows()
            rows[1][key] = "different"
            with self.assertRaises(ValueError):
                compare(rows)

    def test_invalid_token_subset(self):
        rows = self.rows()
        rows[1]["expensive_model_tokens"] = 1000
        with self.assertRaises(ValueError):
            compare(rows)

    def test_zero_baseline_is_not_infinite_savings(self):
        rows = self.rows()
        for row in rows:
            row["total_tokens"] = row["expensive_model_tokens"] = 0
        self.assertIsNone(compare(rows)["measurements"]["total_tokens"]["reduction_fraction"])

    def test_two_failures_are_not_quality_success(self):
        rows = self.rows()
        for row in rows:
            row["outcome"] = "fail"
        result = compare(rows)
        self.assertEqual(result["router_passes"], 0)
        self.assertEqual(result["quality_status"], "no_observed_regression")
        self.assertIn("not proof", result["limitation"])

    def test_incomplete_acceptance_is_not_efficiency_success(self):
        rows = self.rows()
        rows[0]['outcome'] = rows[1]['outcome'] = 'fail'
        result = compare(rows)
        self.assertEqual(result['quality_status'], 'no_observed_regression')
        self.assertEqual(result['router_acceptance'], 'incomplete')
        self.assertFalse(result['efficiency_claim_eligible'])

    def test_missing_usage_does_not_authorize_savings_claim(self):
        rows = self.rows()
        del rows[1]['total_tokens']
        result = compare(rows)
        self.assertEqual(result['router_acceptance'], 'pass')
        self.assertFalse(result['efficiency_claim_eligible'])

    def test_cli_rejects_both_fail_even_without_paired_regression(self):
        import json
        import subprocess
        import tempfile
        rows = self.rows()
        for row in rows:
            row['outcome'] = 'fail'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'runs.json'
            path.write_text(json.dumps(rows), encoding='utf-8')
            script = Path(__file__).resolve().parents[1] / 'scripts/compare_runs.py'
            run = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 1)


if __name__ == "__main__":
    unittest.main()
