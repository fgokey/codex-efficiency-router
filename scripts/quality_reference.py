"""Pure offline examples of the Codex Skill's quality gates, not a live enforcer.

All evidence and fingerprints are caller-declared. These helpers never run commands,
read checkpoints, inspect code, grade an LLM response or prove model compliance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Verdict = Literal['PASS', 'FAIL', 'UNKNOWN']
Status = Literal['PASS', 'PARTIAL', 'BLOCKED']


def text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} must be nonempty text')


def flag(value: bool) -> None:
    if type(value) is not bool:
        raise ValueError('gate flags must be boolean')


@dataclass(frozen=True)
class Contract:
    revision: str
    state: str  # Relevant code/diff, tests, dependencies and environment; not HEAD alone.
    required: tuple[str, ...]

    def validate(self) -> None:
        text(self.revision, 'contract revision')
        text(self.state, 'state fingerprint')
        if not isinstance(self.required, tuple) or not self.required:
            raise ValueError('required must be a nonempty tuple')
        for item in self.required:
            text(item, 'requirement ID')
        if len(set(self.required)) != len(self.required):
            raise ValueError('duplicate requirement ID')


@dataclass(frozen=True)
class Evidence:
    requirement: str
    verdict: Verdict
    contract_revision: str
    state: str
    kind: Literal['command', 'review', 'claim']
    detail: str


@dataclass(frozen=True)
class Completion:
    status: Status
    gaps: tuple[str, ...]


def completion(contract: Contract, evidence: tuple[Evidence, ...], *, blocked: bool = False) -> Completion:
    """Require current supporting evidence for each predeclared required outcome."""
    contract.validate()
    flag(blocked)
    records = {}
    for item in evidence:
        if not isinstance(item, Evidence):
            raise ValueError('expected Evidence records')
        if item.requirement not in contract.required or item.requirement in records:
            raise ValueError('unknown or duplicate evidence requirement')
        if item.verdict not in ('PASS', 'FAIL', 'UNKNOWN') or item.kind not in ('command', 'review', 'claim'):
            raise ValueError('unknown evidence verdict/kind')
        text(item.contract_revision, 'evidence contract')
        text(item.state, 'evidence state')
        text(item.detail, 'evidence detail')
        records[item.requirement] = item
    gaps = []
    for required in contract.required:
        item = records.get(required)
        if item is None:
            gaps.append(f'{required}: missing evidence')
        elif item.verdict != 'PASS':
            gaps.append(f'{required}: {item.verdict}')
        elif item.kind == 'claim':
            gaps.append(f'{required}: assertion alone is not evidence')
        elif item.contract_revision != contract.revision or item.state != contract.state:
            gaps.append(f'{required}: evidence does not match contract/final state')
    if blocked:
        gaps.append('blocking finding or prerequisite remains')
        return Completion('BLOCKED', tuple(gaps))
    return Completion('PARTIAL' if gaps else 'PASS', tuple(gaps))


def handoff(*, complete: bool, aligned: bool, assumptions_checked: bool,
            authorized: bool, state_current: bool) -> Literal['READY', 'RECHECK', 'BLOCKED']:
    """Admission for implementation, not a ban on read-only evidence gathering."""
    for value in (complete, aligned, assumptions_checked, authorized, state_current):
        flag(value)
    if not complete or not aligned or not authorized:
        return 'BLOCKED'
    if not assumptions_checked or not state_current:
        return 'RECHECK'
    return 'READY'


@dataclass(frozen=True)
class Unit:
    task: str
    unit: str
    failure_signature: str  # Canonical behavior, not literal error text or model name.

    def validate(self) -> None:
        for value in (self.task, self.unit, self.failure_signature):
            text(value, 'task/unit/failure signature')


@dataclass(frozen=True)
class Failure:
    key: Unit
    worker: str
    approach: str
    kind: Literal['implementation', 'capability', 'specification', 'environment', 'observability']


def retry(key: Unit, failures: tuple[Failure, ...], *, history_known: bool,
          next_approach: str, new_evidence: str = '', extension: int = 0,
          extension_reason: str = '') -> Literal['RECONCILE', 'PREREQUISITE', 'DIAGNOSE', 'ATTEMPT']:
    """Initial attempt plus one repair per failure signature, shared by all workers.

    Extensions are explicit parent declarations, not authenticated authorizations.
    Preserve supplied history; a new worker or model is intentionally not an input.
    """
    key.validate()
    flag(history_known)
    text(next_approach, 'next approach')
    if not isinstance(new_evidence, str) or not isinstance(extension_reason, str):
        raise ValueError('evidence and extension reason must be text')
    if type(extension) is not int or extension < 0:
        raise ValueError('extension must be a nonnegative integer')
    if extension:
        text(extension_reason, 'explicit parent extension reason')
    relevant = []
    for attempt in failures:
        if not isinstance(attempt, Failure):
            raise ValueError('expected Failure records')
        attempt.key.validate()
        text(attempt.worker, 'worker ID')
        text(attempt.approach, 'failed approach')
        if attempt.kind not in ('implementation', 'capability', 'specification', 'environment', 'observability'):
            raise ValueError('unknown failure class')
        if attempt.key == key:
            relevant.append(attempt)
    if not history_known:
        return 'RECONCILE'
    if relevant and relevant[-1].kind in ('specification', 'environment', 'observability'):
        return 'PREREQUISITE'
    if relevant and relevant[-1].kind == 'capability':
        return 'DIAGNOSE'
    if len(relevant) >= 2 + extension:
        return 'DIAGNOSE'
    if any(item.approach == next_approach for item in relevant) and not new_evidence.strip():
        return 'DIAGNOSE'
    return 'ATTEMPT'


def resume(contract: Contract, evidence: tuple[Evidence, ...], *,
           saved_contract_revision: str, worker_state: Literal['idle', 'active', 'unknown'],
           side_effect_state: Literal['none', 'confirmed', 'unknown'], blocked: bool = False) -> Literal['WAIT', 'RECONCILE', 'REVALIDATE', 'REUSE', 'CONTINUE', 'BLOCKED']:
    """Reconcile ownership first; never redispatch unknown in-flight work."""
    contract.validate()
    flag(blocked)
    text(saved_contract_revision, 'saved contract revision')
    if worker_state not in ('idle', 'active', 'unknown') or side_effect_state not in ('none', 'confirmed', 'unknown'):
        raise ValueError('unknown recovery state')
    if worker_state == 'unknown' or side_effect_state == 'unknown':
        return 'RECONCILE'
    if worker_state == 'active':
        return 'WAIT'
    if saved_contract_revision != contract.revision:
        return 'REVALIDATE'
    result = completion(contract, evidence, blocked=blocked)
    if result.status == 'BLOCKED':
        return 'BLOCKED'
    if result.status == 'PASS':
        return 'REUSE'
    if any(item.contract_revision != contract.revision or item.state != contract.state for item in evidence):
        return 'REVALIDATE'
    return 'CONTINUE'
