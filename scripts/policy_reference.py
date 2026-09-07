#!/usr/bin/env python3
"""Reference routing policy used only by tests/docs, not required at runtime.

The Codex Skill makes the live routing decision from current task context. This
module provides a deterministic approximation so maintainers can regression-test
policy changes without paying for an LLM router call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Lane = Literal["local", "luna", "terra", "sol", "astra"]


@dataclass(frozen=True)
class TaskSignals:
    mechanical: bool = False
    uncertainty: int = 1       # 0 known -> 3 highly unresolved
    risk: int = 1              # 0 trivial -> 3 high consequence/blast radius
    coupling: int = 1          # 0 isolated -> 3 cross-system/long-horizon
    verifiability: int = 2     # 0 weak/judgment -> 3 strong deterministic checks
    irreversibility: int = 0   # 0 easy rollback -> 3 costly/durable commitment
    novelty: int = 0           # 0 established pattern -> 3 genuinely novel mechanism
    evidence_conflict: bool = False
    commitment_boundary: bool = False
    capability_failure: bool = False
    spec_complete: bool = True
    environment_ready: bool = True
    observability_ready: bool = True
    failed_attempts: int = 0
    prior_lane: Lane = "local"
    force_astra: bool = False
    no_subagents: bool = False

    def validate(self) -> None:
        for name in (
            "uncertainty",
            "risk",
            "coupling",
            "verifiability",
            "irreversibility",
            "novelty",
        ):
            value = getattr(self, name)
            if value < 0 or value > 3:
                raise ValueError(f"{name} must be in [0, 3]")
        if self.failed_attempts < 0:
            raise ValueError("failed_attempts must be >= 0")


def choose_lane(s: TaskSignals) -> Lane:
    s.validate()

    if s.no_subagents:
        return "local"
    if s.force_astra:
        return "astra"

    # Missing task packet, broken environment, or missing observability is not a
    # model-capability problem. Keep control local so the prerequisite is repaired
    # instead of spending a stronger model on an unanswerable task.
    if not (s.spec_complete and s.environment_ready and s.observability_ready):
        return "local"

    # Astra: reasoning must have something useful to resolve. High risk or scary
    # technology names alone are deliberately insufficient.
    if (
        s.prior_lane == "sol"
        and s.capability_failure
        and s.failed_attempts >= 1
        and s.uncertainty >= 1
    ):
        return "astra"

    if (
        s.commitment_boundary
        and s.uncertainty >= 2
        and (s.risk >= 2 or s.irreversibility >= 2 or s.coupling >= 2)
    ):
        return "astra"

    if (
        s.evidence_conflict
        and s.uncertainty >= 2
        and (s.risk >= 2 or s.coupling >= 2)
    ):
        return "astra"

    if s.irreversibility >= 3 and s.uncertainty >= 2:
        return "astra"

    if (
        s.novelty >= 3
        and s.uncertainty >= 2
        and (s.coupling >= 2 or s.verifiability <= 1)
    ):
        return "astra"

    if s.risk >= 3 and s.uncertainty >= 2 and s.verifiability <= 2:
        return "astra"

    # Sol: normal senior engineering uncertainty, coupling, or risk. Strong
    # deterministic verification can keep a frozen high-risk implementation below
    # Astra and sometimes below Sol.
    if s.uncertainty >= 2 or s.coupling >= 2:
        return "sol"
    if s.risk >= 2 and (s.uncertainty >= 1 or s.verifiability <= 2):
        return "sol"
    if s.failed_attempts >= 2 and s.uncertainty >= 1:
        return "sol"

    # Cheapest safe deterministic lane.
    if (
        s.mechanical
        and s.uncertainty == 0
        and s.risk <= 1
        and s.verifiability >= 2
        and s.irreversibility <= 1
    ):
        return "luna"

    # Quality-sensitive default implementation lane.
    return "terra"
