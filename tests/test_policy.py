import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from policy_reference import TaskSignals, choose_lane  # noqa: E402


class RoutingPolicyTests(unittest.TestCase):
    def test_regression_cases(self):
        cases = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["name"]):
                signals = TaskSignals(**case["signals"])
                self.assertEqual(choose_lane(signals), case["expected"])

    def test_signal_range_validation(self):
        with self.assertRaises(ValueError):
            choose_lane(TaskSignals(uncertainty=4))


if __name__ == "__main__":
    unittest.main()
