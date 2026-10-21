"""Pure offline examples of the Codex Skill's quality gates, not a live enforcer.

All evidence and fingerprints are caller-declared. These helpers never run commands,
read checkpoints, inspect code, grade an LLM response or prove model compliance.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Literal

Verdict = Literal['PASS', 'FAIL', 'UNKNOWN']
Status = Literal['PASS', 'PARTIAL', 'BLOCKED']
ReadAction = Literal['INDEX', 'BATCH', 'RANGE', 'RESUME', 'LOCATE_GAP']
ToolAction = Literal['REUSE', 'DISCOVER']
RoundtripAction = Literal['DEFER', 'BATCH', 'SINGLE']
ProgressAction = Literal['COLLECT', 'WAIT_COMPACT', 'TAIL_DELTA', 'BACKOFF']
MutationAction = Literal['ADMIT', 'REROUTE', 'DECOMPOSE', 'BLOCKED']
PatchAction = Literal['INSPECT', 'REPAIR', 'DIAGNOSE']
MUTATION_CLASSES = frozenset(('implementation', 'build_config', 'format', 'targeted_test',
                              'self_check', 'binary_copy', 'runtime_config', 'deploy',
                              'destructive_recovery'))
REPAIR_CLASSES = frozenset(('implementation', 'build_config', 'format', 'targeted_test',
                            'self_check'))
BINDING_INVALIDATORS = frozenset(('model', 'effort', 'role', 'permission', 'owner',
                                  'session_resume', 'contradictory_evidence'))


def text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} must be nonempty text')


def flag(value: bool) -> None:
    if type(value) is not bool:
        raise ValueError('gate flags must be boolean')


def serialize_output(value: object) -> str:
    """Exact compact JSON for one outer emit, including all selected nested results."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def bounded_output(value: object, *, framing_bytes: int, max_bytes: int = 4096) -> str:
    """Prepare one output or fail; caller must account for its actual host framing."""
    if (type(framing_bytes) is not int or framing_bytes < 0
            or type(max_bytes) is not int or not 256 <= max_bytes <= 4096):
        raise ValueError('known nonnegative framing and max_bytes 256..4096 required')
    output = serialize_output(value)
    if len(output.encode('utf-8')) + 2 + framing_bytes > max_bytes:
        raise ValueError('complete serialized output plus CRLF/framing exceeds max_bytes')
    return output


def coordination_output(workers: tuple[dict, ...], *, previous: tuple[dict, ...] = (),
                        framing_bytes: int, max_bytes: int = 4096) -> str:
    """Offline projection of caller-normalized results, not a live polling adapter."""
    fields = ('threadId', 'turnId', 'status', 'cursor', 'pending', 'error', 'evidence')
    def indexed(rows):
        if not isinstance(rows, tuple):
            raise ValueError('worker snapshots must be tuples')
        result = {}
        for row in rows:
            if not isinstance(row, dict) or any(key not in row for key in fields):
                raise ValueError('complete worker status/error/cursor/pending/evidence required')
            for key in ('threadId', 'status'):
                text(row[key], key)
            for key in ('turnId', 'cursor', 'error', 'evidence'):
                if row[key] is not None and not isinstance(row[key], str):
                    raise ValueError(f'{key} must be text or None')
            flag(row['pending'])
            if row['threadId'] in result:
                raise ValueError('duplicate worker identity')
            result[row['threadId']] = row
        return result
    old, current = indexed(previous), indexed(workers)
    selected = []
    for identifier, row in current.items():
        prior = old.get(identifier)
        changed = prior is None or any(row[key] != prior[key]
            for key in ('turnId', 'status', 'pending', 'error', 'evidence'))
        detail_due = changed and (prior is not None or row['error'] is not None
                                  or row['evidence'] is not None or not row['pending'])
        selected.append(dict((key, row[key]) for key in fields) |
                        {'changed': changed, 'detail_due': detail_due})
    return bounded_output({'workers': selected}, framing_bytes=framing_bytes, max_bytes=max_bytes)


def read_action(*, mandatory_full: bool, size_known: bool, aggregate_fits: bool,
                members_bounded: bool, truncated: bool = False,
                continuation_known: bool = False) -> ReadAction:
    """Choose from caller-declared facts for the smallest enclosing output cap."""
    for value in (mandatory_full, size_known, aggregate_fits, members_bounded,
                  truncated, continuation_known):
        flag(value)
    if truncated:
        return 'RESUME' if continuation_known else 'LOCATE_GAP'
    if not size_known or not members_bounded:
        return 'INDEX'
    if mandatory_full:
        return 'RANGE'
    return 'BATCH' if aggregate_fits else 'RANGE'


def tool_action(*, known: bool, invalidated: bool) -> ToolAction:
    """Reuse a known native tool contract until caller-observed invalidation."""
    flag(known)
    flag(invalidated)
    return 'DISCOVER' if invalidated or not known else 'REUSE'


def validation_fingerprint(state: object) -> str | None:
    """Hash supplied verification scope; does not collect or authenticate evidence."""
    if not isinstance(state, dict) or set(state) != {'repo', 'commit', 'files', 'dependencies',
                                                   'commands', 'scope', 'environment'}:
        return None
    if (not isinstance(state['repo'], str) or not state['repo']
            or not isinstance(state['commit'], str) or not re.fullmatch(r'[0-9a-f]{40,64}', state['commit'])
            or not isinstance(state['environment'], str)
            or not re.fullmatch(r'[0-9a-f]{64}', state['environment'])):
        return None
    for field in ('files', 'dependencies'):
        pairs = state[field]
        if not isinstance(pairs, tuple) or any(not isinstance(pair, tuple) or len(pair) != 2
                or not isinstance(pair[0], str) or not pair[0] or not isinstance(pair[1], str)
                or not re.fullmatch(r'[0-9a-f]{64}', pair[1]) for pair in pairs):
            return None
        if len({pair[0] for pair in pairs}) != len(pairs): return None
    scope = state['scope']; commands = state['commands']
    if (not isinstance(scope, tuple) or not scope or any(not isinstance(p, str) or not p for p in scope)
            or len(set(scope)) != len(scope) or set(scope) != {p for p, _ in state['files']}
            or not isinstance(commands, tuple) or not commands
            or any(not isinstance(command, tuple) or not command
                   or any(not isinstance(arg, str) or not arg for arg in command) for command in commands)):
        return None
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def reuse_validation(previous: object, current: object, evidence: object, *, scope_known: bool,
                     changed_paths: tuple[str, ...] | None = None) -> Literal['REUSE', 'REVALIDATE', 'UNKNOWN']:
    """Reuse only a passing receipt bound to known files/dependencies/commands/scope/environment."""
    flag(scope_known)
    old = validation_fingerprint(previous); new = validation_fingerprint(current)
    if not scope_known or old is None or new is None or not isinstance(evidence, dict): return 'UNKNOWN'
    if set(evidence) != {'fingerprint', 'verdict'} or evidence['fingerprint'] != old:
        return 'UNKNOWN'
    if evidence['verdict'] == 'UNKNOWN': return 'UNKNOWN'
    if evidence['verdict'] != 'PASS': return 'REVALIDATE'
    if old == new: return 'REUSE'
    if any(previous[key] != current[key] for key in previous if key != 'commit'): return 'REVALIDATE'
    if changed_paths is None: return 'UNKNOWN'
    if (not isinstance(changed_paths, tuple)
            or any(not isinstance(path, str) or not path for path in changed_paths)):
        return 'UNKNOWN'
    affected = set(current['scope']) | {name for name, _ in current['dependencies']}
    return 'REVALIDATE' if affected.intersection(changed_paths) else 'REUSE'


def roundtrip_action(*, work_due: bool, checks: int, independent: bool,
                     known_small: bool, aggregate_fits: bool) -> RoundtripAction:
    """Avoid a model/tool round with no due work; batch only bounded checks."""
    for value in (work_due, independent, known_small, aggregate_fits):
        flag(value)
    if type(checks) is not int or checks < 1:
        raise ValueError('checks must be a positive integer')
    if not work_due:
        return 'DEFER'
    return 'BATCH' if checks > 1 and independent and known_small and aggregate_fits else 'SINGLE'


def progress_action(*, worker_active: bool, progress_changed: bool,
                    unchanged_polls: int, tail_cursor_current: bool,
                    detail_due: bool = False, diagnostic_due: bool = False) -> ProgressAction:
    """Quiet live status backs off; evidence of a diagnostic gap permits one delta."""
    for value in (worker_active, progress_changed, tail_cursor_current, detail_due, diagnostic_due):
        flag(value)
    if type(unchanged_polls) is not int or unchanged_polls < 0:
        raise ValueError('unchanged polls must be a nonnegative integer')
    if detail_due or not worker_active:
        return 'COLLECT'
    if diagnostic_due and not tail_cursor_current:
        return 'TAIL_DELTA'
    if progress_changed or unchanged_polls < 2:
        return 'WAIT_COMPACT'
    return 'BACKOFF'


def mutation_action(*, observed_model: str | None, read_only: bool, binding_match: bool,
                    exact_manifest: bool, bounded: bool, actions: tuple[str, ...],
                    destructive_rollback: bool, policy_denied: bool,
                    binding_invalidators: tuple[str, ...] = (),
                    parent_released: bool = False) -> MutationAction:
    """Admit a delegated child unit; direct parent work uses its local gates."""
    for value in (read_only, binding_match, exact_manifest, bounded,
                  destructive_rollback, policy_denied, parent_released):
        flag(value)
    if observed_model is not None and (not isinstance(observed_model, str) or not observed_model.strip()):
        raise ValueError('observed model must be nonempty text or None')
    if (not isinstance(actions, tuple) or not actions
            or any(not isinstance(action, str) or action not in MUTATION_CLASSES for action in actions)
            or len(set(actions)) != len(actions)):
        raise ValueError('actions must be unique known mutation classes')
    if (not isinstance(binding_invalidators, tuple)
            or any(not isinstance(item, str) or item not in BINDING_INVALIDATORS
                   for item in binding_invalidators)):
        raise ValueError('unknown binding invalidator')
    if policy_denied:
        return 'BLOCKED'
    if observed_model is None:
        return 'BLOCKED'
    executor = observed_model in ('gpt-6.1-sol', 'gpt-6-sol', 'gpt-6-luna', 'gpt-5.6-sol',
                                  'gpt-5.6-terra', 'gpt-5.6-luna')
    if read_only or not binding_match or binding_invalidators or not executor:
        return 'REROUTE'
    if not parent_released:
        return 'BLOCKED'
    if not exact_manifest or not bounded:
        return 'DECOMPOSE'
    action_set = frozenset(actions)
    if action_set <= REPAIR_CLASSES and not destructive_rollback:
        return 'ADMIT'
    if len(actions) == 1:
        destructive = actions[0] == 'destructive_recovery'
        return 'ADMIT' if destructive == destructive_rollback else 'DECOMPOSE'
    return 'DECOMPOSE'


def patch_action(*, same_signature_failures: int, expected_and_current_checked: bool,
                 encoding_checked: bool, line_endings_checked: bool) -> PatchAction:
    """Inspect one patch mismatch, allow one justified repair, then diagnose."""
    for value in (expected_and_current_checked, encoding_checked, line_endings_checked):
        flag(value)
    if type(same_signature_failures) is not int or same_signature_failures < 1:
        raise ValueError('same-signature failures must be a positive integer')
    if same_signature_failures >= 2:
        return 'DIAGNOSE'
    return ('REPAIR' if expected_and_current_checked and encoding_checked and line_endings_checked
            else 'INSPECT')


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


@dataclass(frozen=True)
class FinalReview:
    """Caller-declared offline parent review evidence, not a runtime ledger."""
    contract_revision: str
    state: str
    delivered_diff: str
    reviewed_diff: str
    validated_requirements: tuple[str, ...]
    open_blocking_findings: tuple[str, ...] = ()
    objective_reconciled: bool = False
    applicable_requirements: tuple[str, ...] = ()
    disagreements_resolved: bool = False
    evidence_basis: str = ''

    def validate(self) -> None:
        flag(self.objective_reconciled)
        flag(self.disagreements_resolved)
        if not isinstance(self.evidence_basis, str):
            raise ValueError('parent evidence basis must be text')
        for value, field in ((self.contract_revision, 'review contract'), (self.state, 'review state'),
                             (self.delivered_diff, 'delivered diff'), (self.reviewed_diff, 'reviewed diff')):
            text(value, field)
        if (not isinstance(self.validated_requirements, tuple)
                or any(not isinstance(item, str) or not item.strip() for item in self.validated_requirements)
                or len(set(self.validated_requirements)) != len(self.validated_requirements)):
            raise ValueError('validated requirements must be unique nonempty IDs')
        if (not isinstance(self.open_blocking_findings, tuple)
                or any(not isinstance(item, str) or not item.strip()
                       for item in self.open_blocking_findings)):
            raise ValueError('open blocking findings must be nonempty text records')
        if (not isinstance(self.applicable_requirements, tuple)
                or any(not isinstance(item, str) or not item.strip() for item in self.applicable_requirements)
                or len(set(self.applicable_requirements)) != len(self.applicable_requirements)):
            raise ValueError('applicable requirements must be unique nonempty IDs')


def completion(contract: Contract, evidence: tuple[Evidence, ...], *,
               final_review: FinalReview | None = None, blocked: bool = False) -> Completion:
    """Require current evidence and parent review of the complete delivered state."""
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
    if final_review is None:
        gaps.append('parent final review missing')
    elif not isinstance(final_review, FinalReview):
        raise ValueError('expected FinalReview')
    else:
        final_review.validate()
        if final_review.contract_revision != contract.revision or final_review.state != contract.state:
            gaps.append('parent review does not match contract/final state')
        if final_review.delivered_diff != final_review.reviewed_diff:
            gaps.append('parent did not review the complete delivered diff')
        if set(final_review.validated_requirements) != set(contract.required):
            gaps.append('parent did not review all required validation evidence')
        if final_review.open_blocking_findings:
            gaps.append('parent review has open blocking findings')
        if not final_review.objective_reconciled:
            gaps.append('parent has not reconciled original objective and remaining required work')
        if set(final_review.applicable_requirements) != set(contract.required):
            gaps.append('parent has not examined code/evidence and test applicability for every requirement')
        if not final_review.disagreements_resolved:
            gaps.append('parent has not resolved review disagreements')
        if not final_review.evidence_basis.strip():
            gaps.append('parent evidence basis missing; child PASS is not parent acceptance')
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
           side_effect_state: Literal['none', 'confirmed', 'unknown'],
           final_review: FinalReview | None = None,
           blocked: bool = False) -> Literal['WAIT', 'RECONCILE', 'REVALIDATE', 'REUSE', 'CONTINUE', 'BLOCKED']:
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
    result = completion(contract, evidence, final_review=final_review, blocked=blocked)
    if result.status == 'BLOCKED':
        return 'BLOCKED'
    if result.status == 'PASS':
        return 'REUSE'
    if any(item.contract_revision != contract.revision or item.state != contract.state for item in evidence):
        return 'REVALIDATE'
    return 'CONTINUE'
