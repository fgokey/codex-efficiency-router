"""Finite deliberate effort-policy breaks; assertion failures alone count."""
from pathlib import Path
import subprocess
import sys


def run_mutations(root: Path, output: Path) -> list[dict]:
    source = (root / 'scripts/effort_reference.py').read_text(encoding='utf-8')
    specs = [
        ('forget_sticky_low_suspension', 'allow_low=profile.allow_low and not context.automatic_low_suspended and', 'allow_low=profile.allow_low and'),
        ('renew_repair_budget_on_effort_change', 'if s.failed_attempts >= 2 and not context.diagnosis_only and context.repair_extension_reason is None:', 'if False:'),
        ('auto_low_without_opt_in', 'if allow_low and lane == "luna"', 'if lane == "luna"'),
        ('low_after_failed_attempt', 'and not s.capability_failure and s.failed_attempts == 0)', 'and not s.capability_failure)'),
        ('ignore_no_subagents', '    if s.no_subagents:', '    if False:'),
        ('ignore_effort_axis_ceiling', '(model_up or effort_up)', 'model_up'),
        ('ignore_model_lock', 'if context.keep_model and (current is None or current.lane != candidate.lane):', 'if False:'),
        ('skip_native_effort_field', 'if not context.host_can_set_effort:', 'if False:'),
        ('ignore_adaptive_pin', 'if binding.effort is not None:', 'if False:'),
        ('ignore_fixed_pin', 'if binding.effort != candidate.effort:', 'if False:'),
        ('skip_selected_pair_support', 'if candidate.effort not in context.catalog.get(candidate.model, ()):', 'if False:'),
        ('unknown_claimed_verified', 'if model is None or effort is None:', 'if False:'),
        ('medium_high_treated_identical', 'if current == candidate:', 'if current is not None and current.lane == candidate.lane:'),
        ('unsafe_hot_change', 'if context.worker_active or not context.safe_boundary:', 'if False:'),
        ('ignore_quality_floor', 'if EFFORTS.index(candidate.effort) < EFFORTS.index(minimum):', 'if False:'),
        ('allow_per_tool_churn', 'if context.change_event == "none":', 'if False:'),
        ('ignore_unknown_low_stop', 'allow_low=profile.allow_low and not context.automatic_low_suspended and context.last_observation not in ("UNKNOWN", "MISMATCH")', 'allow_low=profile.allow_low'),
        ('ignore_role_model', 'if candidate.role in context.unavailable_roles or binding is None or binding.model != candidate.model:', 'if candidate.role in context.unavailable_roles or binding is None:'),
        ('auto_ignores_effort_field', 'context.host_can_set_effort and alias not in context.unavailable_roles', 'alias not in context.unavailable_roles'),
        ('auto_reprobes_failed_alias', 'alias not in context.unavailable_roles', 'True'),
        ('auto_ignores_alias_pin', 'binding.model == candidate.model and binding.effort is None', 'binding.model == candidate.model'),
        ('auto_ignores_alias_model', 'binding.model == candidate.model and binding.effort is None', 'binding.effort is None'),
        ('auto_ignores_fixed_pin', 'or binding.model != candidate.model or binding.effort != candidate.effort):', 'or binding.model != candidate.model):'),
        ('auto_ignores_fixed_model', 'or binding.model != candidate.model or binding.effort != candidate.effort):', 'or binding.effort != candidate.effort):'),
        ('auto_ignores_catalog', 'if candidate.effort not in supported:', 'if False:'),
        ('auto_uses_wrong_alias', 'role, kind = alias, "adaptive"', 'role, kind = candidate.role, "adaptive"'),
        ('auto_ignores_failed_fixed', 'if (candidate.role in context.unavailable_roles or binding is None', 'if (binding is None'),

    ]
    harness = '''import sys, types, unittest
sys.path.insert(0, 'scripts')
m = types.ModuleType('effort_reference')
sys.modules[m.__name__] = m
exec(compile(sys.stdin.read(), '<effort-mutation>', 'exec'), m.__dict__)
r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.discover('tests', pattern='test_effort*.py'))
sys.exit(2 if r.errors else 0 if r.wasSuccessful() else 1)
'''
    outcomes = []
    for name, old, new in specs:
        if source.count(old) != 1:
            outcomes.append({'name': name, 'outcome': 'INVALID_MUTATION'})
            continue
        try:
            result = subprocess.run([sys.executable, '-c', harness], cwd=root,
                                    input=source.replace(old, new, 1), capture_output=True,
                                    text=True, encoding='utf-8', timeout=30)
            (output / f'effort-mutation-{name}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            status = {0: 'SURVIVED', 1: 'KILLED', 2: 'TEST_ERROR'}.get(result.returncode, 'RUNNER_ERROR')
        except subprocess.TimeoutExpired:
            status = 'TIMEOUT'
        outcomes.append({'name': name, 'outcome': status})
    return outcomes
