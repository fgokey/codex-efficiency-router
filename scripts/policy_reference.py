"""Offline reference rules, NOT a live Codex dispatcher or model-quality benchmark."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Literal

Lane = Literal["local", "luna", "terra", "sol", "astra"]
LANES = ("local", "luna", "terra", "sol", "astra")
SameLaneReason = Literal["none", "context_recovery", "independent_review", "scope_isolation"]
SAME_LANE_REASONS = ("none", "context_recovery", "independent_review", "scope_isolation")


@dataclass(frozen=True)
class TaskSignals:
    mechanical: bool = False
    uncertainty: int = 1
    risk: int = 1
    coupling: int = 1
    verifiability: int = 2
    irreversibility: int = 0
    novelty: int = 0
    evidence_conflict: bool = False
    commitment_boundary: bool = False
    capability_failure: bool = False
    spec_complete: bool = True
    authority_ready: bool = True
    environment_ready: bool = True
    observability_ready: bool = True
    reasoning_bound: bool = True
    cheap_check_available: bool = False
    failed_attempts: int = 0
    prior_lane: Lane = "local"
    force_astra: bool = False
    no_subagents: bool = False

    def validate(self) -> None:
        scores = ("uncertainty", "risk", "coupling", "verifiability", "irreversibility", "novelty")
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in scores:
                if type(value) is not int or not 0 <= value <= 3:
                    raise ValueError(f"{field.name} must be an integer in [0, 3]")
            elif field.name == "failed_attempts":
                if type(value) is not int or value < 0:
                    raise ValueError("failed_attempts must be a nonnegative integer")
            elif field.name == "prior_lane":
                if value not in LANES:
                    raise ValueError("unknown prior_lane")
            elif type(value) is not bool:
                raise ValueError(f"{field.name} must be boolean")


def choose_lane(s: TaskSignals) -> Lane:
    """Recommend capability independently from whether a host can dispatch it."""
    s.validate()
    if not (s.spec_complete and s.authority_ready and s.environment_ready and s.observability_ready):
        return "local"  # Repair a prerequisite; not permission to implement blindly.
    if s.force_astra:
        return "astra"
    if s.cheap_check_available:
        return "local"  # The described check must be safe, bounded and discriminating.

    if s.reasoning_bound:
        if s.capability_failure and s.failed_attempts >= 1 and s.prior_lane == "sol" and s.uncertainty >= 1:
            return "astra"
        consequential = s.risk >= 2 or s.irreversibility >= 2 or s.coupling >= 2
        if s.uncertainty >= 2 and (
            (s.commitment_boundary and consequential)
            or (s.evidence_conflict and (s.risk >= 2 or s.coupling >= 2))
            or s.irreversibility == 3
            or (s.novelty == 3 and (s.coupling >= 2 or s.verifiability <= 1))
            or (s.risk == 3 and s.verifiability <= 2)
        ):
            return "astra"
    if s.uncertainty >= 2 or s.coupling >= 2:
        return "sol"
    if s.risk >= 2 and (s.uncertainty >= 1 or s.verifiability <= 2):
        return "sol"
    if s.capability_failure and s.failed_attempts >= 1:
        if s.prior_lane in ("terra", "sol"):
            return "sol"
        if s.prior_lane == "luna":
            return "terra"
    if (s.mechanical and s.uncertainty == 0 and s.risk <= 1
            and s.verifiability >= 2 and s.irreversibility <= 1):
        return "luna"
    return "terra"


@dataclass(frozen=True)
class DispatchDecision:
    recommended_lane: Lane
    action: Literal["local", "delegate", "blocked", "prerequisite"]
    reason: str


def choose_dispatch(s: TaskSignals, *, current_lane: Lane, current_sufficient: bool,
                    available_lanes: tuple[str, ...] = (), host_supports_routing: bool = False,
                    benefit_clear: bool = False, no_escalation: bool = False,
                    same_lane_reason: SameLaneReason = "none") -> DispatchDecision:
    """Offline admission gate; caller-supplied evidence is not model telemetry.

    A same-lane route needs a concrete contextual purpose AND a net benefit.
    Neither a purpose label nor a fresh agent makes an incapable model sufficient.
    Re-scope the task before treating cheaper execution as safe after insufficiency.
    """
    if current_lane not in LANES or any(lane not in LANES[1:] for lane in available_lanes):
        raise ValueError("unknown execution lane")
    if any(type(v) is not bool for v in (current_sufficient, host_supports_routing, benefit_clear, no_escalation)):
        raise ValueError("execution flags must be boolean")
    if same_lane_reason not in SAME_LANE_REASONS:
        raise ValueError("unknown same_lane_reason")
    lane = choose_lane(s)

    def result(action: Literal["local", "delegate", "blocked", "prerequisite"], reason: str) -> DispatchDecision:
        return DispatchDecision(lane, action, reason)
    if lane == "local":
        return result("prerequisite", "repair prerequisites or run the safe discriminating check")
    forbidden = s.no_subagents or (no_escalation and LANES.index(lane) > LANES.index(current_lane))
    if forbidden:
        return result("local" if current_sufficient else "blocked", "user routing constraint; quality floor retained")
    if current_lane == lane:
        if same_lane_reason == "none" or not benefit_clear:
            return result("local" if current_sufficient else "blocked",
                          "same-lane delegation requires a concrete contextual reason and net benefit")
    elif not current_sufficient and LANES.index(lane) < LANES.index(current_lane):
        return result("blocked", "insufficient current capability cannot be repaired by a cheaper lane; re-scope first")
    if current_sufficient and not s.force_astra and not benefit_clear:
        return result("local", "delegation benefit not established")
    if host_supports_routing and lane in available_lanes:
        return result("delegate", "required capability or justified route benefit")
    if current_sufficient and not s.force_astra:
        return result("local", "route unavailable; sufficient current agent retained")
    return result("blocked", "no verified sufficient route; do not silently downgrade")
