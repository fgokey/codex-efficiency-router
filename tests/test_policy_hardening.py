"""Regressions for the independently found gaps, with dispatch actually available."""
from dataclasses import replace
from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from policy_reference import TaskSignals as S, choose_dispatch as dispatch, choose_lane


class PolicyHardeningTests(unittest.TestCase):
    def test_no_subagents_is_causal_with_available_routes(self):
        # Removing only the opt-out must change the outcome: no fallback can mask it.
        cases = [(S(), "sol", True), (S(risk=3, uncertainty=3), "terra", False),
                 (S(force_astra=True), "sol", True)]
        for signals, current, sufficient in cases:
            args = dict(current_lane=current, current_sufficient=sufficient,
                        host_supports_routing=True, available_lanes=("terra", "astra"),
                        benefit_clear=True)
            with self.subTest(current=current, sufficient=sufficient):
                self.assertEqual(dispatch(signals, **args).action, "delegate")
                forbidden = dispatch(replace(signals, no_subagents=True), **args)
                self.assertEqual(forbidden.action, "local" if sufficient else "blocked")
                self.assertEqual(forbidden.recommended_lane, choose_lane(signals))

    def test_same_lane_insufficiency_is_not_an_upgrade(self):
        result = dispatch(S(uncertainty=2), current_lane="sol", current_sufficient=False,
                          host_supports_routing=True, available_lanes=("sol",))
        self.assertEqual(result.action, "blocked")

    def test_cost_benefit_alone_cannot_justify_same_lane_recovery(self):
        result = dispatch(S(uncertainty=2), current_lane="sol", current_sufficient=False,
                          host_supports_routing=True, available_lanes=("sol",), benefit_clear=True)
        self.assertEqual(result.action, "blocked")

    def test_same_lane_requires_reason_and_benefit(self):
        for reason, benefit, sufficient in product(
                ("none", "context_recovery", "independent_review", "scope_isolation"),
                (False, True), (False, True)):
            args = dict(current_lane="sol", current_sufficient=sufficient,
                        host_supports_routing=True, available_lanes=("sol",),
                        same_lane_reason=reason, benefit_clear=benefit)
            with self.subTest(reason=reason, benefit=benefit, sufficient=sufficient):
                expected = "delegate" if reason != "none" and benefit else "local" if sufficient else "blocked"
                self.assertEqual(dispatch(S(uncertainty=2), **args).action, expected)
                self.assertEqual(dispatch(S(uncertainty=2, no_subagents=True), **args).action,
                                 "local" if sufficient else "blocked")

    def test_recovery_does_not_bypass_host_availability(self):
        for host, lanes in ((False, ("sol",)), (True, ("terra",))):
            self.assertEqual(dispatch(S(uncertainty=2), current_lane="sol", current_sufficient=False,
                                     same_lane_reason="context_recovery", benefit_clear=True,
                                     host_supports_routing=host, available_lanes=lanes).action, "blocked")

    def test_insufficient_current_agent_cannot_solve_it_by_downgrading(self):
        self.assertEqual(dispatch(S(), current_lane="sol", current_sufficient=False,
                                 host_supports_routing=True, available_lanes=("terra",),
                                 benefit_clear=True).action, "blocked")

    def test_settled_rescoped_work_can_downgrade(self):
        self.assertEqual(dispatch(S(uncertainty=0), current_lane="sol", current_sufficient=True,
                                 host_supports_routing=True, available_lanes=("terra",),
                                 benefit_clear=True).action, "delegate")

    def test_capability_upgrade_needs_no_recovery_flag(self):
        self.assertEqual(dispatch(S(risk=3, uncertainty=3), current_lane="sol", current_sufficient=False,
                                 host_supports_routing=True, available_lanes=("astra",)).action, "delegate")

    def test_no_escalation_still_allows_justified_downgrade(self):
        self.assertEqual(dispatch(S(), current_lane="astra", current_sufficient=True,
                                 no_escalation=True, benefit_clear=True,
                                 host_supports_routing=True, available_lanes=("terra",)).action, "delegate")

    def test_all_lanes_keep_opt_out_even_when_every_route_exists(self):
        for current, sufficient, force, benefit in product(("luna", "terra", "sol", "astra"),
                                                          (False, True), (False, True), (False, True)):
            result = dispatch(S(no_subagents=True, force_astra=force), current_lane=current,
                              current_sufficient=sufficient, benefit_clear=benefit,
                              host_supports_routing=True, available_lanes=("luna", "terra", "sol", "astra"))
            self.assertEqual(result.action, "local" if sufficient else "blocked")

    def test_invalid_recovery_reason_rejected(self):
        for reason in (True, None, "try again", [], 42):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                dispatch(S(), current_lane="sol", current_sufficient=True, same_lane_reason=reason)

    def test_insufficient_same_lane_forced_astra_is_still_blocked(self):
        self.assertEqual(dispatch(S(force_astra=True), current_lane="astra", current_sufficient=False,
                                 host_supports_routing=True, available_lanes=("astra",)).action, "blocked")

    def test_quality_probe_frozen_but_coupled_work_stays_senior(self):
        self.assertEqual(choose_lane(S(prior_lane="astra", uncertainty=0, coupling=3,
                                       risk=1, verifiability=3)), "sol")

    def test_quality_probe_low_verifiability_is_not_mechanical_lane(self):
        self.assertEqual(choose_lane(S(mechanical=True, uncertainty=0, risk=1, verifiability=0)), "terra")


if __name__ == "__main__":
    unittest.main()
