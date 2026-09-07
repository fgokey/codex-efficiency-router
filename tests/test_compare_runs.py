import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_runs import compare


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
