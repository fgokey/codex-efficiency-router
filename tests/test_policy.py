import json
import sys
import unittest
from dataclasses import replace
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from policy_reference import TaskSignals, choose_lane, choose_dispatch


class RoutingPolicyTests(unittest.TestCase):
    def test_regression_cases(self):
        cases = json.loads((ROOT / "tests/cases.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cases), 36)
        self.assertEqual(len(cases), len({c["name"] for c in cases}))
        for case in cases:
            with self.subTest(case=case["name"]):
                self.assertEqual(choose_lane(TaskSignals(**case["signals"])), case["expected"])

    def test_strict_signal_validation(self):
        for key, value in (("uncertainty", 4), ("risk", True), ("novelty", 1.5),
                           ("mechanical", "false"), ("failed_attempts", -1),
                           ("failed_attempts", True), ("prior_lane", "unknown")):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                choose_lane(TaskSignals(**{key: value}))

    def test_prerequisite_gate_holds_across_risks(self):
        for uncertainty, risk, coupling in product(range(4), repeat=3):
            s = TaskSignals(uncertainty=uncertainty, risk=risk, coupling=coupling, force_astra=True)
            for flag in ("spec_complete", "environment_ready", "authority_ready", "observability_ready"):
                self.assertEqual(choose_lane(replace(s, **{flag: False})), "local")

    def test_cheap_check_always_precedes_automatic_premium(self):
        for uncertainty, risk, novelty in product(range(4), repeat=3):
            s = TaskSignals(uncertainty=uncertainty, risk=risk, novelty=novelty, cheap_check_available=True)
            self.assertEqual(choose_lane(s), "local")

    def test_no_subagents_does_not_certify_quality(self):
        s = TaskSignals(risk=3, uncertainty=3, no_subagents=True)
        d = choose_dispatch(s, current_lane="terra", current_sufficient=False)
        self.assertEqual((d.recommended_lane, d.action), ("astra", "blocked"))

    def test_no_subagents_sufficient_local(self):
        s = TaskSignals(no_subagents=True)
        self.assertEqual(choose_dispatch(s, current_lane="sol", current_sufficient=True).action, "local")

    def test_no_escalation_retains_quality_floor(self):
        s = TaskSignals(risk=3, uncertainty=3)
        d = choose_dispatch(s, current_lane="sol", current_sufficient=False, no_escalation=True,
                            host_supports_routing=True, available_lanes=("astra",))
        self.assertEqual(d.action, "blocked")

    def test_missing_host_or_model_blocks_unsafe_fallback(self):
        s = TaskSignals(risk=3, uncertainty=3)
        for host, available in ((False, ("astra",)), (True, ("terra",))):
            d = choose_dispatch(s, current_lane="terra", current_sufficient=False,
                                host_supports_routing=host, available_lanes=available)
            self.assertEqual(d.action, "blocked")

    def test_missing_route_can_keep_sufficient_current_agent(self):
        d = choose_dispatch(TaskSignals(), current_lane="sol", current_sufficient=True, benefit_clear=True)
        self.assertEqual(d.action, "local")

    def test_cost_only_dispatch_requires_benefit(self):
        args = dict(current_lane="sol", current_sufficient=True, available_lanes=("terra",), host_supports_routing=True)
        self.assertEqual(choose_dispatch(TaskSignals(), **args).action, "local")
        self.assertEqual(choose_dispatch(TaskSignals(), benefit_clear=True, **args).action, "delegate")

    def test_capability_upgrade_does_not_require_cost_savings(self):
        d = choose_dispatch(TaskSignals(risk=3, uncertainty=3), current_lane="terra", current_sufficient=False,
                            host_supports_routing=True, available_lanes=("astra",))
        self.assertEqual(d.action, "delegate")

    def test_forced_route_is_not_claimed_when_unavailable(self):
        d = choose_dispatch(TaskSignals(force_astra=True), current_lane="sol", current_sufficient=True)
        self.assertEqual(d.action, "blocked")

    def test_same_sufficient_lane_needs_no_child(self):
        d = choose_dispatch(TaskSignals(), current_lane="terra", current_sufficient=True, benefit_clear=True)
        self.assertEqual(d.action, "local")

    def test_dispatch_validation(self):
        with self.assertRaises(ValueError):
            choose_dispatch(TaskSignals(), current_lane="sol", current_sufficient="yes")
        with self.assertRaises(ValueError):
            choose_dispatch(TaskSignals(), current_lane="sol", current_sufficient=True, available_lanes=("fake",))


if __name__ == "__main__":
    unittest.main()
