"""Offline authority gate and diagnostic admission; NOT live ownership telemetry."""
from __future__ import annotations
from dataclasses import dataclass

OPERATIONS = ('reasoning', 'read', 'coordinate', 'local_patch', 'mutation', 'unknown')
ASTRA_WRITE_REASONS = ('none', 'qualified_executor_failure', 'critical_context_loss')


def is_astra(model: str | None) -> bool:
    # Host-reported family slug, including dated Astra snapshots. Never read a prompt.
    return isinstance(model, str) and (model == 'gpt-6-astra' or model.startswith('gpt-6-astra-'))


@dataclass(frozen=True)
class Writer:
    agent_id: str
    unit: str
    model: str
    state: str  # idle, active, unknown, stopped
    authorized: bool = True
    sufficient: bool = True
    effort: str | None = None

    def __post_init__(self):
        if any(not isinstance(v, str) or not v.strip() for v in (self.agent_id, self.unit, self.model)):
            raise ValueError('writer identity, unit and model are required')
        if self.effort is not None and self.effort not in ('low', 'medium', 'high', 'xhigh', 'max'):
            raise ValueError('invalid observed writer effort')
        if self.state not in ('idle', 'active', 'unknown', 'stopped'):
            raise ValueError('invalid writer state')
        if any(type(v) is not bool for v in (self.authorized, self.sufficient)):
            raise ValueError('writer flags must be boolean')


@dataclass(frozen=True)
class AstraWriteEvidence:
    """Caller-observed evidence for one exceptional root-Astra local patch.

    This is an offline policy input, not a permission token or runtime ledger.
    """
    reason: str = 'none'
    root_actor: bool = False
    scope_bounded: bool = False
    target_in_workspace: bool = False
    verification_defined: bool = False
    failure_kind: str = 'none'
    qualified_attempts: int = 0
    prior_exception_writes: int = 0
    guard_status: str = 'unknown'  # unknown, inactive, active

    def validate(self):
        if self.reason not in ASTRA_WRITE_REASONS:
            raise ValueError('invalid Astra write reason')
        flags = (self.root_actor, self.scope_bounded, self.target_in_workspace,
                 self.verification_defined)
        if any(type(v) is not bool for v in flags):
            raise ValueError('Astra write evidence flags must be boolean')
        if self.guard_status not in ('unknown', 'inactive', 'active'):
            raise ValueError('invalid strict Guard status')
        if self.failure_kind not in ('none', 'capability', 'unexplained', 'implementation',
                                     'environment', 'specification', 'observability'):
            raise ValueError('invalid Astra write failure kind')
        for value in (self.qualified_attempts, self.prior_exception_writes):
            if type(value) is not int or value < 0:
                raise ValueError('Astra write evidence counts must be nonnegative integers')

    def qualifies(self) -> bool:
        failure_ready = (self.reason == 'qualified_executor_failure' and self.qualified_attempts >= 2
                         and self.failure_kind in ('capability', 'unexplained', 'implementation'))
        context_ready = self.reason == 'critical_context_loss'
        return (self.root_actor and self.scope_bounded and self.target_in_workspace
                and self.verification_defined and self.prior_exception_writes == 0
                and self.guard_status == 'inactive' and (failure_ready or context_ready))


@dataclass(frozen=True)
class WriteScope:
    unit: str = ''
    authorized: bool = False
    ownership_clear: bool = False
    safe_boundary: bool = False
    writers: tuple[Writer, ...] = ()
    local_owner: bool = False
    writer_limit: int = 2
    actor_id: str | None = None
    astra_write: AstraWriteEvidence = AstraWriteEvidence()

    def validate(self):
        if self.actor_id is not None and (not isinstance(self.actor_id, str) or not self.actor_id):
            raise ValueError("invalid current actor identity")
        if not isinstance(self.unit, str):
            raise ValueError('unit must be a string')
        if any(type(v) is not bool for v in (self.authorized, self.ownership_clear, self.safe_boundary, self.local_owner)):
            raise ValueError('scope flags must be boolean')
        if type(self.writer_limit) is not int or self.writer_limit < 1:
            raise ValueError('positive writer limit required')
        if not isinstance(self.writers, tuple) or any(not isinstance(w, Writer) for w in self.writers):
            raise ValueError('writers must be a tuple of Writer')
        if len({w.agent_id for w in self.writers}) != len(self.writers):
            raise ValueError('duplicate writer identity')
        if not isinstance(self.astra_write, AstraWriteEvidence):
            raise ValueError('invalid Astra write evidence')
        self.astra_write.validate()


@dataclass(frozen=True)
class WriteDecision:
    action: str  # local_read, local_write, delegate, reuse, defer, blocked
    reason: str
    owner: str | None = None
    exception: str | None = None


def before_action(operation: str, model: str | None, scope: WriteScope = WriteScope(), *,
                  read_only: bool = False, no_subagents: bool = False,
                  host_supports_routing: bool = False) -> WriteDecision:
    """Capability/cheapness never grants write authority. Run BEFORE local shortcuts.

    'delegate' is admission to select a writer; model/effort support is checked next.
    'reuse' names an already-observed, idle compatible owner, never a new process.
    """
    if operation not in OPERATIONS or (model is not None and (not isinstance(model, str) or not model)):
        raise ValueError('invalid action or observed model')
    if any(type(v) is not bool for v in (read_only, no_subagents, host_supports_routing)):
        raise ValueError('action flags must be boolean')
    scope.validate()
    if operation in ('reasoning', 'read', 'coordinate'):
        return WriteDecision('local_read', 'read/analysis/owned orchestration is permitted, not local writing')
    if not scope.unit.strip() or not scope.authorized or not scope.ownership_clear:
        return WriteDecision('blocked', 'establish authorization, unit and exclusive ownership first')
    if not scope.safe_boundary or any(w.state == 'unknown' for w in scope.writers):
        return WriteDecision('defer', 'reconcile in-flight work and side effects; never replay blindly')
    owners = [w for w in scope.writers if w.unit == scope.unit and w.state != 'stopped']
    if len(owners) > 1:
        return WriteDecision('blocked', 'conflicting owners for this unit')
    known_executor = isinstance(model, str) and any(model == m or model.startswith(m + '-') for m in ('gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna'))
    can_write = known_executor and not is_astra(model) and not read_only
    continuing_owner = len(owners) == 1 and owners[0].agent_id == scope.actor_id and owners[0].model == model and owners[0].authorized
    if can_write and scope.local_owner and (not owners or continuing_owner):
        if not continuing_owner and sum(w.state == 'active' for w in scope.writers) >= scope.writer_limit:
            return WriteDecision('defer', 'writer slots occupied; do not become a third writer')
        return WriteDecision('local_write', 'known authorized non-read-only owner; normal checks still apply')
    astra_patch = (operation == 'local_patch' and is_astra(model) and not read_only
                   and scope.local_owner and not owners
                   and not any(w.state == 'active' for w in scope.writers)
                   and scope.astra_write.qualifies())
    if astra_patch:
        return WriteDecision('local_write',
                             'one bounded root-Astra patch is justified by recorded exception evidence; '
                             'ordinary implementation and side-effecting verification remain executor work',
                             exception='bounded_astra_patch')
    if sum(w.state == 'active' for w in scope.writers) >= scope.writer_limit:
        return WriteDecision('defer', 'writer slots occupied; do not create an extra writer')
    if no_subagents:
        return WriteDecision('blocked', 'delegation forbidden; read-only status is not waived')
    if owners:
        owner = owners[0]
        if owner.state == 'active':
            return WriteDecision('defer', 'wait for the existing owner at a safe boundary', owner.agent_id)
        if (owner.authorized and owner.sufficient and owner.model in ('gpt-5.6-sol', 'gpt-5.6-terra')):
            return WriteDecision('reuse', 'handoff to compatible idle owner; preserve diff and retry history', owner.agent_id)
        return WriteDecision('blocked', 'existing owner is not an eligible executor; reconcile ownership')
    if not host_supports_routing:
        return WriteDecision('blocked', 'no eligible writer route; Astra/unknown identity cannot write locally')
    return WriteDecision('delegate', 'assign the bounded write unit to Terra/Sol, not Astra')


def diagnostic_action(*, model: str | None, complex_judgment: bool = False,
                      unresolved: bool = True, prerequisites_ready: bool = True,
                      cheap_check_available: bool = False, failure_kind: str = 'none',
                      qualified_attempts: int = 0, no_escalation: bool = False) -> str:
    """Stop blind repairs, NOT strong-model diagnosis. Counts alone are insufficient."""
    flags = (complex_judgment, unresolved, prerequisites_ready, cheap_check_available, no_escalation)
    if any(type(v) is not bool for v in flags) or type(qualified_attempts) is not int or qualified_attempts < 0:
        raise ValueError('invalid diagnostic evidence')
    if failure_kind not in ('none', 'capability', 'unexplained', 'implementation', 'environment', 'specification', 'observability'):
        raise ValueError('unknown failure kind')
    if not unresolved:
        return 'return_to_executor'
    if not prerequisites_ready or failure_kind in ('environment', 'specification', 'observability'):
        return 'repair_prerequisite'
    if cheap_check_available:
        return 'executor_experiment'
    if complex_judgment or (qualified_attempts >= 2 and failure_kind in ('capability', 'unexplained')):
        if is_astra(model):
            return 'astra_local_readonly_diagnosis'
        return 'blocked' if no_escalation else 'delegate_astra_readonly'
    return 'continue_scoped_diagnosis'
