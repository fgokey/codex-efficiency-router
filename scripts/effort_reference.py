"""Offline joint model/effort policy. Declared evidence, not a live dispatcher.

The Skill applies equivalent rules without running Python each turn. These pure
helpers do not read sessions, retry tasks, change budgets or call model APIs.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal, Mapping

from package import EXPECTED
from policy_reference import LANES, SAME_LANE_REASONS, TaskSignals, choose_lane
from profiles import Profile
from write_policy import OPERATIONS, WriteScope, before_action, diagnostic_action

EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")
PRESETS = {
    "luna": EXPECTED["luna-worker.toml"],
    "terra": EXPECTED["terra-executor.toml"],
    "sol": EXPECTED["sol61-engineer.toml"],
    "astra": EXPECTED["astra-architect.toml"],
}
MODEL_ROLES = {model: role for role, model, _ in EXPECTED.values()}
MODEL_ROLES["gpt-5.6-sol"] = EXPECTED["sol-engineer.toml"][0]
MODEL_LANES = {
    "gpt-6-luna": "luna",
    "gpt-5.6-luna": "luna",
    "gpt-5.6-terra": "terra",
    "gpt-6.1-sol": "sol",
    "gpt-6-sol": "sol",
    "gpt-5.6-sol": "sol",
    "gpt-6-astra": "astra",
}
LEGACY_FALLBACKS = {
    "luna": ("gpt-5.6-luna",),
    "sol": ("gpt-6-sol", "gpt-5.6-sol", "gpt-5.6-terra"),
}
EVENTS = ("initial", "phase", "evidence", "classified_failure", "user", "none")


@dataclass(frozen=True)
class Configuration:
    lane: str
    effort: str
    model_id: str | None = None

    def __post_init__(self) -> None:
        if self.lane not in LANES[1:] or self.effort not in EFFORTS:
            raise ValueError("unknown model lane or reasoning effort")
        model = PRESETS[self.lane][1] if self.model_id is None else self.model_id
        if MODEL_LANES.get(model) != self.lane:
            raise ValueError("model does not belong to the selected lane")
        object.__setattr__(self, "model_id", model)

    @property
    def model(self) -> str:
        return self.model_id

    @property
    def role(self) -> str:
        return MODEL_ROLES.get(self.model, PRESETS[self.lane][0])


@dataclass(frozen=True)
class RoleBinding:
    model: str
    effort: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model:
            raise ValueError("role model must be a nonempty string")
        if self.effort is not None and self.effort not in EFFORTS:
            raise ValueError("unknown pinned effort")


@dataclass(frozen=True)
class EffortEvidence:
    bottleneck: str = ""
    high_limit: str = ""
    extra_effort_value: str = ""
    high_insufficient: bool = False
    independent_units: int = 0
    disjoint_ownership: bool = False
    net_benefit: bool = False
    coordinator_authorized: bool = False
    coordinator_contract_verified: bool = False
    single_coordinator: bool = False
    capacity_available: bool = False
    shared_limits_retained: bool = False

    def validate(self) -> None:
        for name in ("bottleneck", "high_limit", "extra_effort_value"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be text")
        if type(self.independent_units) is not int or self.independent_units < 0:
            raise ValueError("independent_units must be a nonnegative integer")
        for name in ("high_insufficient", "disjoint_ownership", "net_benefit",
                     "coordinator_authorized", "coordinator_contract_verified", "single_coordinator",
                     "capacity_available", "shared_limits_retained"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")

    def complete_reason(self) -> bool:
        return all(value.strip() for value in
                   (self.bottleneck, self.high_limit, self.extra_effort_value))

    def summary(self) -> str:
        return f"{self.bottleneck.strip()}; {self.high_limit.strip()}; {self.extra_effort_value.strip()}"

    def ultra_ready(self) -> bool:
        return (self.independent_units >= 2 and self.disjoint_ownership and self.net_benefit
                and self.coordinator_authorized and self.coordinator_contract_verified
                and self.single_coordinator and self.capacity_available
                and self.shared_limits_retained)


@dataclass(frozen=True)
class Context:
    current: Configuration | None = None
    operation: str = "reasoning"  # Legacy planner calls are analysis, NEVER write authorization.
    read_only: bool = False
    write_scope: WriteScope = field(default_factory=WriteScope)
    current_sufficient: bool = False
    host_supports_routing: bool = False
    host_can_set_effort: bool = False
    roles: Mapping[str, RoleBinding] = field(default_factory=dict)
    catalog: Mapping[str, frozenset[str]] = field(default_factory=dict)
    benefit_clear: bool = False
    same_config_reason: str = "none"
    no_escalation: bool = False  # Both model and effort, separately ordered.
    no_effort_escalation: bool = False
    keep_model: bool = False
    change_event: str = "initial"
    safe_boundary: bool = False
    worker_active: bool = False
    last_observation: str = "NOT_CHECKED"
    observation_review: str = "none"  # none, pending, resolved; scoped to this unit.
    observation_resolution_reason: str | None = None
    automatic_low_suspended: bool = False  # Sticky for this task after unknown/mismatched identity.
    failure_kind: str = "none"  # Classified evidence, not just an error counter.
    diagnosis_only: bool = False
    repair_extension_reason: str | None = None
    repair_attempt_limit: int = 2  # Absolute unit/signature ceiling, never a fresh allowance.
    unavailable_roles: frozenset[str] = frozenset()  # Task-local confirmed failures; never probe in a loop.
    unavailable_models: Mapping[str, str] = field(default_factory=dict)  # Confirmed reason, not catalog absence.

    def validate(self) -> None:
        if self.operation not in OPERATIONS or type(self.read_only) is not bool or not isinstance(self.write_scope, WriteScope):
            raise ValueError("invalid operation/authority context")
        self.write_scope.validate()
        if self.failure_kind not in ("none", "capability", "unexplained", "implementation", "environment", "specification", "observability"):
            raise ValueError("invalid classified failure")
        for name in ("current_sufficient", "host_supports_routing", "host_can_set_effort",
                     "benefit_clear", "no_escalation", "no_effort_escalation", "keep_model",
                     "safe_boundary", "worker_active", "diagnosis_only", "automatic_low_suspended"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        if self.current is not None and not isinstance(self.current, Configuration):
            raise ValueError("current must be observed Configuration or None")
        if self.same_config_reason not in SAME_LANE_REASONS or self.change_event not in EVENTS:
            raise ValueError("invalid contextual reason or reassessment event")
        if self.repair_extension_reason is not None and (not isinstance(self.repair_extension_reason, str)
                or not self.repair_extension_reason.strip()):
            raise ValueError("repair extension needs a justified parent reassessment")
        if type(self.repair_attempt_limit) is not int or self.repair_attempt_limit < 2:
            raise ValueError("repair attempt limit must be an integer >= 2")
        if self.repair_attempt_limit > 2 and self.repair_extension_reason is None:
            raise ValueError("extended absolute limit requires a parent reassessment")
        if self.last_observation not in ("NOT_CHECKED", "VERIFIED", "UNKNOWN", "MISMATCH"):
            raise ValueError("invalid observed configuration status")
        if self.observation_review not in ("none", "pending", "resolved"):
            raise ValueError("invalid observation review state")
        if self.observation_review == "resolved":
            if not isinstance(self.observation_resolution_reason, str) or not self.observation_resolution_reason.strip():
                raise ValueError("resolved mismatch requires scoped review evidence")
        elif self.observation_resolution_reason is not None:
            raise ValueError("resolution evidence requires a resolved review")
        if (not isinstance(self.roles, Mapping) or not isinstance(self.catalog, Mapping)
                or not isinstance(self.unavailable_models, Mapping)):
            raise ValueError("roles, catalog and unavailable_models must be mappings")
        if not isinstance(self.unavailable_roles, frozenset) or any(
                not isinstance(name, str) or not name for name in self.unavailable_roles):
            raise ValueError("unavailable_roles must contain confirmed role names")
        if any(model not in MODEL_LANES or not isinstance(reason, str) or not reason.strip()
               for model, reason in self.unavailable_models.items()):
            raise ValueError("unavailable_models requires known models and nonempty reasons")
        for name, binding in self.roles.items():
            if not isinstance(name, str) or not isinstance(binding, RoleBinding):
                raise ValueError("invalid role binding")
        for model, efforts in self.catalog.items():
            if (not isinstance(model, str) or not isinstance(efforts, (set, frozenset, tuple))
                    or any(not isinstance(e, str) for e in efforts)):
                raise ValueError("invalid supported-effort catalog")


@dataclass(frozen=True)
class Decision:
    recommended: Configuration | None
    requested: Configuration | None
    action: Literal["local", "delegate", "blocked", "prerequisite", "defer", "reuse"]
    reason: str
    requested_role: str | None = None
    binding_kind: Literal["adaptive", "fixed"] | None = None
    owner_id: str | None = None


def low_eligible(s: TaskSignals) -> bool:
    return (s.workload == "data_transform" and s.mechanical
            and s.uncertainty == 0 and s.risk <= 1 and s.coupling <= 1
            and s.verifiability == 3 and s.irreversibility <= 1 and s.novelty == 0
            and not s.evidence_conflict and not s.commitment_boundary
            and not s.capability_failure and s.failed_attempts == 0)


def needs_deeper_reasoning(s: TaskSignals, deep_reasoning: bool) -> bool:
    return s.reasoning_bound and (deep_reasoning or
        (s.uncertainty >= 2 and s.coupling >= 2) or
        (s.uncertainty >= 1 and s.risk >= 2) or s.evidence_conflict)


def ordinary_terra_eligible(s: TaskSignals, rec: Configuration) -> bool:
    return (rec.lane == "sol" and rec.effort == "medium" and s.workload == "general"
            and not s.mechanical and s.uncertainty <= 1 and s.risk <= 1 and s.coupling <= 1
            and s.irreversibility <= 1 and s.novelty <= 1 and not s.evidence_conflict
            and not s.commitment_boundary and not s.capability_failure)


def recommend(s: TaskSignals, *, deep_reasoning: bool = False,
              allow_low: bool = False) -> Configuration | None:
    """Conservative effort recommendation; actual support is checked separately."""
    if type(deep_reasoning) is not bool or type(allow_low) is not bool:
        raise ValueError("effort selection flags must be boolean")
    lane = choose_lane(s)  # Includes specification, authority and cheap-check gates.
    if lane == "local":
        return None
    effort = "high" if (lane == "astra" or needs_deeper_reasoning(s, deep_reasoning)
                        or (lane == "luna" and s.workload != "data_transform")) else "medium"
    if allow_low and lane == "luna" and low_eligible(s) and not deep_reasoning:
        effort = "low"
    return Configuration(lane, effort)


def plan(s: TaskSignals, context: Context, profile: Profile = Profile("auto"), *,
         deep_reasoning: bool = False, explicit_effort: str | None = None,
         explicit_model: str | None = None, automatic_effort: str | None = None,
         effort_evidence: EffortEvidence | None = None) -> Decision:
    """Return an admission decision. Never imply that a model has actually run.

    No silent unsupported-effort remapping. Same-model higher effort is an
    evidence-backed effort change, not an identical-configuration retry. Model
    and effort rankings are guardrails, not a universal quality/cost ordering.
    """
    if not isinstance(context, Context):
        raise ValueError("execution Context required")
    context.validate()
    if not isinstance(profile, Profile):
        raise ValueError("profile required")
    if explicit_effort is not None and explicit_effort not in EFFORTS:
        raise ValueError("explicit effort is not supported by this policy")
    if automatic_effort is not None and automatic_effort not in ("xhigh", "max", "ultra"):
        raise ValueError("automatic effort override must be xhigh, max or ultra")
    if explicit_effort is not None and automatic_effort is not None:
        raise ValueError("explicit and automatic effort selections are mutually exclusive")
    if explicit_model is not None and explicit_model not in MODEL_LANES:
        raise ValueError("explicit model is not supported by this policy")
    if effort_evidence is not None and not isinstance(effort_evidence, EffortEvidence):
        raise ValueError("effort evidence must be EffortEvidence")
    evidence = effort_evidence or EffortEvidence()
    evidence.validate()
    rec = recommend(s, deep_reasoning=deep_reasoning, allow_low=profile.allow_low and not context.automatic_low_suspended and context.last_observation not in ("UNKNOWN", "MISMATCH"))

    if context.observation_review == "pending" or (
            context.last_observation == "MISMATCH" and context.observation_review != "resolved"):
        return Decision(rec, None, "defer" if context.worker_active or not context.safe_boundary else "prerequisite",
                        "reconcile actual binding and effects, then review affected acceptance before continuation; read-only investigation remains available")

    write_intent = context.operation in ("local_patch", "mutation", "unknown")
    gate = before_action(context.operation, context.current.model if context.current else None,
                         context.write_scope, read_only=context.read_only,
                         no_subagents=s.no_subagents, host_supports_routing=context.host_supports_routing)
    must_delegate = write_intent and gate.action != "local_write"
    diagnostic = diagnostic_action(
        model=context.current.model if context.current else None,
        complex_judgment=rec is not None and rec.lane == "astra",
        prerequisites_ready=s.spec_complete and s.authority_ready and s.environment_ready and s.observability_ready,
        cheap_check_available=s.cheap_check_available, failure_kind=context.failure_kind,
        qualified_attempts=s.failed_attempts, no_escalation=context.no_escalation)
    if context.diagnosis_only and not write_intent and diagnostic == "delegate_astra_readonly":
        rec = Configuration("astra", "high")

    def result(action, reason, requested=None, requested_role=None, binding_kind=None):
        if action == "local" and must_delegate:
            return Decision(rec, None, "blocked", "local mutation forbidden; " + reason)
        return Decision(rec, requested, action, reason, requested_role, binding_kind)

    if write_intent and gate.action in ("blocked", "defer"):
        return Decision(rec, None, gate.action, gate.reason, owner_id=gate.owner)
    if write_intent:
        if not (s.spec_complete and s.authority_ready and s.environment_ready and s.observability_ready) or s.cheap_check_available:
            return result("prerequisite", "repair prerequisites or run a safe discriminating check")
        if context.worker_active or not context.safe_boundary:
            return result("defer", "wait for a safe task boundary; no in-flight hot switch")
        if s.failed_attempts >= context.repair_attempt_limit:
            return result("blocked", "write budget exhausted; reuse/diagnosis labels cannot renew repairs")
    if rec is None:
        return result("prerequisite", "repair prerequisites or run a safe discriminating check")
    if automatic_effort is not None:
        if not evidence.high_insufficient or not evidence.complete_reason():
            return result("blocked", "automatic xhigh/max/ultra needs task-specific evidence that high is insufficient")
        if automatic_effort == "ultra" and not evidence.ultra_ready():
            return result("blocked", "automatic ultra needs one authorized coordinator and independent disjoint beneficial units")
    minimum = "high" if (needs_deeper_reasoning(s, deep_reasoning) or
        (rec is not None and rec.lane == "astra" and choose_lane(replace(s, force_astra=False)) == "astra")) else "low" if low_eligible(s) else "medium"
    if write_intent and gate.exception == "bounded_astra_patch":
        if diagnostic == "repair_prerequisite":
            return result("prerequisite", "classified prerequisite failures do not qualify for root repairs")
        if not context.current_sufficient:
            return result("blocked", "root repair requires current capability evidence")
        if (context.current.effort == "low"
                or ((explicit_effort or automatic_effort) is not None
                    and context.current.effort != (explicit_effort or automatic_effort))
                or (explicit_model is not None and context.current.model != explicit_model)
                or EFFORTS.index(context.current.effort) < EFFORTS.index(minimum)):
            return result("blocked", "root repair cannot change local effort or bypass the quality floor")
        if context.write_scope.astra_write.qualified_attempts > s.failed_attempts:
            return result("blocked", "reconcile qualified failures with retained unit history")
        return Decision(rec, None, "local", gate.reason)
    if write_intent and rec is not None and rec.lane == "astra":
        return result("blocked", "split out Astra read-only diagnosis, then assign settled writes to Terra/Sol")

    if write_intent and gate.action == "reuse":
        owner = next(w for w in context.write_scope.writers if w.agent_id == gate.owner)
        owner_lane = MODEL_LANES.get(owner.model)
        current = context.current
        if context.keep_model and (current is None or owner.model != current.model):
            return result("blocked", "existing owner does not satisfy the model lock")
        if explicit_model is not None and owner.model != explicit_model:
            return result("blocked", "existing owner does not confirm the explicitly requested model")
        if (explicit_effort or automatic_effort) is not None and owner.effort != (explicit_effort or automatic_effort):
            return result("blocked", "existing owner does not confirm the explicitly requested effort")
        if owner.effort is None or EFFORTS.index(owner.effort) < EFFORTS.index(minimum):
            return result("blocked", "existing owner does not confirm the required effort floor; reassess at a safe boundary")
        if context.no_escalation or context.no_effort_escalation:
            if current is None or owner.effort is None:
                return result("blocked", "unknown owner configuration cannot verify upgrade limits")
            if (context.no_escalation and LANES.index(owner_lane) > LANES.index(current.lane)) or EFFORTS.index(owner.effort) > EFFORTS.index(current.effort):
                return result("blocked", "existing owner exceeds an upgrade limit")
        return Decision(rec, None, "reuse", gate.reason, owner_id=gate.owner)
    if context.diagnosis_only and not write_intent and diagnostic in ("repair_prerequisite", "executor_experiment"):
        return result("prerequisite", "repair prerequisites or run a safe discriminating check before diagnosis")
    if context.diagnosis_only and not write_intent and diagnostic == "astra_local_readonly_diagnosis":
        return result("local", "Astra participates directly in read-only diagnosis; exhausted write budget remains exhausted")
    if s.failed_attempts >= context.repair_attempt_limit and not context.diagnosis_only:
        return result("blocked", "repair budget exhausted; changing model/effort never renews it")
    current = context.current
    candidate_model = explicit_model
    if candidate_model is None and context.keep_model and current is not None:
        candidate_model = current.model
    requested_lane = MODEL_LANES[candidate_model] if candidate_model is not None else rec.lane
    if requested_lane != rec.lane:
        higher_or_equal = LANES.index(requested_lane) >= LANES.index(rec.lane)
        ordinary_terra_override = requested_lane == "terra" and ordinary_terra_eligible(s, rec)
        retained_astra = explicit_model is None and context.keep_model and current is not None and current.lane == "astra"
        if (requested_lane == "astra" and not retained_astra) or not (higher_or_equal or ordinary_terra_override):
            return result("blocked", "explicit model does not satisfy the identified capability floor")
    retained_effort = (current.effort if context.keep_model and current is not None
                       and LANES.index(current.lane) > LANES.index(rec.lane)
                       and context.current_sufficient else rec.effort)
    candidate = Configuration(requested_lane, automatic_effort or explicit_effort or retained_effort, candidate_model)
    if candidate.effort == "ultra" and candidate.lane not in ("sol", "astra"):
        return result("blocked", "ultra requires a Sol or Astra coordinator-capable role")
    if candidate.effort == "ultra" and not evidence.ultra_ready():
        return result("blocked", "ultra dispatch needs one authorized coordinator and independent disjoint beneficial units")
    # Explicit preferences are not permission to ignore an identified quality floor.
    if explicit_effort == "low" and (not low_eligible(s) or deep_reasoning or rec.lane == "astra"):
        return result("blocked", "explicit low does not satisfy the scoped quality floor")
    if EFFORTS.index(candidate.effort) < EFFORTS.index(minimum):
        return result("blocked", "requested effort is below the identified quality floor")
    if s.no_subagents:
        return result("local" if context.current_sufficient else "blocked", "user forbids subagents")
    if context.keep_model and (current is None or current.model != candidate.model):
        return result("local" if context.current_sufficient else "blocked", "user model lock retained")
    if context.no_escalation or context.no_effort_escalation:
        if current is None:
            return result("blocked", "unknown current configuration cannot verify upgrade limits")
        model_up = LANES.index(candidate.lane) > LANES.index(current.lane)
        effort_up = EFFORTS.index(candidate.effort) > EFFORTS.index(current.effort)
        if (context.no_escalation and (model_up or effort_up)) or (
                context.no_effort_escalation and effort_up):
            return result("local" if context.current_sufficient else "blocked", "user escalation limit retained")
    if context.worker_active or not context.safe_boundary:
        return result("defer", "wait for a safe task boundary; no in-flight hot switch")
    if context.change_event == "none":
        return result("local" if context.current_sufficient else "blocked", "no event justifies reselection")
    if current == candidate:
        if (context.same_config_reason == "none" or not context.benefit_clear) and not (must_delegate and context.current_sufficient):
            return result("local" if context.current_sufficient else "blocked", "identical configuration needs contextual value and benefit")
    elif current is not None and not context.current_sufficient:
        if LANES.index(candidate.lane) < LANES.index(current.lane) or (
                candidate.lane == current.lane and EFFORTS.index(candidate.effort) < EFFORTS.index(current.effort)):
            return result("blocked", "do not downgrade the same unresolved insufficiency")
    if (context.current_sufficient and explicit_effort is None and automatic_effort is None
            and explicit_model is None
            and not s.force_astra and not context.benefit_clear and not must_delegate):
        return result("local", "current agent is sufficient; handoff benefit not established")

    def unavailable(reason):
        # Local means current configuration retained, not a secretly applied fallback.
        return result("local" if context.current_sufficient and explicit_effort is None
                      and automatic_effort is None and explicit_model is None and not s.force_astra
                      else "blocked", reason)

    if not context.host_supports_routing:
        return unavailable("native dispatch unavailable")
    def native_binding(config: Configuration):
        if config.model in context.unavailable_models:
            return None
        if config.effort not in context.catalog.get(config.model, ()):
            return None
        if profile.mode == "auto":
            alias = "cer_auto_" + config.role
            binding = context.roles.get(alias)
            if (context.host_can_set_effort and alias not in context.unavailable_roles
                    and binding is not None and binding.model == config.model and binding.effort is None):
                return alias, "adaptive"
            binding = context.roles.get(config.role)
            if (config.role not in context.unavailable_roles and binding is not None
                    and binding.model == config.model and binding.effort == config.effort):
                return config.role, "fixed"
            return None
        binding = context.roles.get(config.role)
        if config.role in context.unavailable_roles or binding is None or binding.model != config.model:
            return None
        if profile.mode == "adaptive":
            if not context.host_can_set_effort or binding.effort is not None:
                return None
        elif binding.effort != config.effort:
            return None
        return config.role, profile.mode

    selected = candidate
    binding = native_binding(selected)
    if (binding is None and explicit_model is None and not context.keep_model
            and candidate.model in context.unavailable_models):
        for fallback_model in LEGACY_FALLBACKS.get(candidate.lane, ()):
            if fallback_model == "gpt-5.6-terra" and not ordinary_terra_eligible(s, rec):
                continue
            fallback = Configuration(MODEL_LANES[fallback_model], candidate.effort, fallback_model)
            binding = native_binding(fallback)
            if binding is not None:
                selected = fallback
                break
    if binding is None:
        return unavailable("no exact role and catalog support for the selected pair; no silent remapping")
    if selected.effort == "ultra" and selected.lane not in ("sol", "astra"):
        return unavailable("legacy fallback cannot bypass the Sol/Astra Ultra coordinator contract")
    if context.keep_model and (current is None or selected.model != current.model):
        return unavailable("legacy fallback does not satisfy the exact model lock")
    used_fallback = selected.model != candidate.model
    if used_fallback and current == selected and not context.current_sufficient:
        return unavailable("legacy fallback would repeat the same insufficient configuration")
    if current is not None and not context.current_sufficient and (
            LANES.index(selected.lane) < LANES.index(current.lane) or
            (selected.lane == current.lane and EFFORTS.index(selected.effort) < EFFORTS.index(current.effort))):
        return unavailable("legacy fallback would downgrade the same unresolved insufficiency")
    role, kind = binding
    reason = ("evidence-backed exact legacy fallback; preserve checks and attempts"
              if selected.model != candidate.model else
              "exact native binding selection; preserve checks and attempts")
    if automatic_effort is not None:
        reason += f"; automatic {automatic_effort}: {evidence.summary()}"
    return result("delegate", reason, selected, role, kind)


def dispatch_arguments(decision: Decision) -> dict[str, str]:
    """Native spawn selection fields; caller supplies the scoped message/task name.

    No call is made. A compact contract avoids inherited history and permits an
    explicit effort override; fixed bindings already pin the verified pair.
    """
    if decision.action != "delegate" or decision.requested is None or decision.requested_role is None or decision.binding_kind not in ("fixed", "adaptive"):
        raise ValueError("an admitted delegation decision is required")
    args = {"agent_type": decision.requested_role, "fork_turns": "none"}
    if decision.binding_kind == "adaptive":
        args["reasoning_effort"] = decision.requested.effort
    return args


def check_observation(requested: Configuration, model: str | None,
                      effort: str | None) -> Literal["VERIFIED", "UNKNOWN", "MISMATCH"]:
    """Only pass host metadata, never an agent's self-description as these fields."""
    if not isinstance(requested, Configuration):
        raise ValueError("requested configuration required")
    if any(v is not None and (not isinstance(v, str) or not v) for v in (model, effort)):
        raise ValueError("observed identity fields must be strings or None")
    if (model is not None and model != requested.model) or (effort is not None and effort != requested.effort):
        return "MISMATCH"
    if model is None or effort is None:
        return "UNKNOWN"
    return "VERIFIED"


def record_observation(context: Context, requested: Configuration, model: str | None,
                       effort: str | None) -> Context:
    """Carry a sticky task-level auto-low suspension across subsequent observations.

    This returns declared state only; the parent owns its task checkpoint. Starting
    a new task creates a new Context, while worker/effort changes do not clear it.
    """
    context.validate()
    status = check_observation(requested, model, effort)
    pending = status == "MISMATCH" or context.observation_review == "pending" or (
        context.last_observation == "MISMATCH" and context.observation_review != "resolved")
    return replace(context, last_observation=status,
                   observation_review="pending" if pending else context.observation_review,
                   observation_resolution_reason=None if pending else context.observation_resolution_reason,
                   automatic_low_suspended=context.automatic_low_suspended or
                   context.last_observation in ("UNKNOWN", "MISMATCH") or status in ("UNKNOWN", "MISMATCH"))


def resolve_observation(context: Context, *, effects_reconciled: bool,
                        acceptance_reviewed: bool, reason: str) -> Context:
    """Record a scoped parent review, not a model identity or live PASS certificate.

    The reason identifies affected work/checks and whether to retain sufficient
    work or correct a binding. No restart, effort change or budget renewal occurs.
    """
    context.validate()
    if any(type(v) is not bool for v in (effects_reconciled, acceptance_reviewed)):
        raise ValueError("review evidence flags must be boolean")
    pending = context.observation_review == "pending" or (
        context.last_observation == "MISMATCH" and context.observation_review != "resolved")
    if not pending or context.worker_active or not context.safe_boundary:
        raise ValueError("an outstanding mismatch needs a safe review boundary")
    if not effects_reconciled or not acceptance_reviewed or not isinstance(reason, str) or not reason.strip():
        raise ValueError("reconcile effects and review affected acceptance with scoped evidence")
    return replace(context, observation_review="resolved", observation_resolution_reason=reason,
                   automatic_low_suspended=True)
