"""Source-size and loading-contract checks, NOT live model-compliance evidence."""
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import doctor
from package import EXPECTED, INSTRUCTION_BUDGETS, PROJECT
from profiles import Profile

SKILL = ROOT / 'skills' / PROJECT / 'SKILL.md'


def contract_text():
    return '\n'.join(doctor.instruction_chain(SKILL).values())


class InstructionFootprintTests(unittest.TestCase):
    def test_tightened_source_budgets(self):
        # Full budget includes the explicit parent completion decision; other limits stay fixed.
        self.assertLessEqual(INSTRUCTION_BUDGETS['core_skill_bytes'], 5200)
        self.assertLessEqual(INSTRUCTION_BUDGETS['full_skill_bytes'], 10800)
        self.assertLessEqual(INSTRUCTION_BUDGETS['discovery_description_characters'], 180)
        self.assertLessEqual(INSTRUCTION_BUDGETS['role_developer_instruction_bytes'], 950)
        self.assertEqual(doctor.validate_tree(SKILL, ROOT / 'agents'), [])

    def test_footprint_counts_core_once_and_every_reference(self):
        result = doctor.instruction_footprint(SKILL, ROOT / 'agents')
        refs = list((SKILL.parent / 'references').rglob('*.md'))
        self.assertEqual(result['core_skill_bytes'], len(SKILL.read_bytes()))
        self.assertEqual(result['full_skill_bytes'], len(SKILL.read_bytes()) +
                         sum(len(p.read_bytes()) + 1 for p in refs))
        self.assertEqual(len(result['reference_bytes']), len(refs))
        # Description is already in SKILL.md; do not add it again to the total.
        self.assertEqual(result['reference_separator_bytes'], len(refs))

    def test_report_never_calls_bytes_tokens_or_whole_task_savings(self):
        result = doctor.instruction_footprint(SKILL, ROOT / 'agents')
        self.assertEqual(result['token_counts'], 'NOT_MEASURED')
        self.assertEqual(result['whole_task_savings'], 'NOT_MEASURED')
        self.assertIn('UTF-8 source text', result['basis'])
        self.assertNotIn('total_task_tokens', result)

    def test_roles_measured_as_parsed_instructions_separately(self):
        result = doctor.instruction_footprint(SKILL, ROOT / 'agents')
        self.assertEqual(set(result['role_developer_instruction_bytes']), set(EXPECTED))
        for name in EXPECTED:
            data = tomllib.loads((ROOT / 'agents' / name).read_text())
            self.assertEqual(result['role_developer_instruction_bytes'][name],
                             len(data['developer_instructions'].encode('utf-8')))

    def test_role_bloat_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sol-engineer.toml'
            source = (ROOT / 'agents' / path.name).read_text()
            path.write_text(source.replace('developer_instructions = """',
                                           'developer_instructions = """' + 'padding ' * 130))
            for role in ('sol_engineer', 'cer_auto_sol_engineer'):
                text = path.read_text().replace('name = "sol_engineer"', f'name = "{role}"')
                path.write_text(text)
                errors = doctor.validate_agent(path, (role, 'gpt-6-sol', 'medium'), Profile())
                self.assertTrue(any('role instructions exceed' in e for e in errors))

    def test_reference_load_triggers_remain_reachable(self):
        text = SKILL.read_text()
        for name in ('effort', 'routing', 'dispatch', 'quality'):
            self.assertEqual(text.count(f'references/{name}.md'), 1)
            self.assertTrue((SKILL.parent / 'references' / f'{name}.md').is_file())
        for phrase in ("before a parent's first collection/final", 'Routine released leaves',
                       'before dispatch or a meaningful phase change', 'before delegation or binding changes'):
            self.assertIn(phrase, text)

    def test_parent_final_requires_objective_and_remaining_work_reconciliation(self):
        core = SKILL.read_text()
        self.assertLess(core.index('## Completion'), core.index('## Routing'))
        self.assertIn("before a parent's first collection/final", core)
        text = contract_text()
        for phrase in ('original user objective', 'accepted scope', 'every remaining required item', 'current authority'):
            self.assertIn(phrase, text)

    def test_actionable_incomplete_parent_work_requires_continuation(self):
        text = contract_text()
        for phrase in ('CONTINUE while useful authorized diagnosis, delegation or implementation remains', 'without a user nudge', 'Missing measurement/design alone proves neither done nor blocked'):
            self.assertIn(phrase, text)

    def test_partial_child_and_green_local_checks_do_not_end_parent_work(self):
        self.assertTrue('Unit PASS/PARTIAL/checks/reviews != parent completion'
                        in contract_text())

    def test_parent_complete_requires_all_required_items_and_current_evidence(self):
        self.assertTrue('COMPLETE only when every required item is satisfied by current evidence'
                        in contract_text())

    def test_external_blocker_requires_specific_evidence_and_unaffected_work(self):
        text = contract_text()
        for phrase in ('BLOCKED requires an actual external barrier', 'its evidence, affected scope and required external action', 'finish unaffected authorized work'):
            self.assertIn(phrase, text)

    def test_standalone_status_ends_but_mid_task_status_preserves_objective(self):
        text = contract_text()
        for phrase in ('Standalone status questions end after answering', 'mid-task questions do not cancel the objective'):
            self.assertIn(phrase, text)

    def test_stop_and_scope_limits_bound_parent_continuation(self):
        text = contract_text()
        for phrase in ('STOP on explicit stop/pause/cancel', 'accepted scope change', 'actual tool/system budget ceiling', 'report remaining work', 'No unrequested monitoring, risky operations or infinite retries'):
            self.assertIn(phrase, text)

    def test_entry_is_cheap_but_does_not_grant_authority(self):
        text = SKILL.read_text()
        self.assertLessEqual(len(text.encode('utf-8')), 2048)
        for phrase in ('do not invoke for trivial questions or stack routers', 'Low is opt-in',
                       'Unknown identity/effects grant no writes', 'Root Astra defaults read-only',
                       'native admission has no repair exceptions', 'except Astra mutations'):
            self.assertIn(phrase, text)
        self.assertEqual(set(doctor.instruction_chain(SKILL)),
                         {'SKILL.md', *(f'references/{name}.md' for name in ('effort','routing','dispatch','quality'))})

    def test_evidence_efficiency_guidance_preserves_complete_reads_and_unit_ownership(self):
        text = contract_text()
        for phrase in ('Reuse loaded unchanged rules', 'fully read required new/changed rules', 'Batch independent reads', 'link checks', 'preserve every error and cursor', 'Reuse the same live owner', 'Keep successful results and retry failed/pending items only', 'Run required checks once after final changes stabilize'):
            self.assertIn(phrase, text)

    def test_no_blanket_loading_or_full_router_in_children(self):
        text = contract_text()
        for phrase in ('Do not preload reports or copy the Router into workers', 'Report version/mode/Guard once', 'unobserved facts stay UNKNOWN'):
            self.assertIn(phrase, text)

    def test_native_reads_are_scoped_to_released_writers_without_new_authority(self):
        text = contract_text()
        for phrase in ('Prefer scoped native reads for released writers', 'retain guarded reads elsewhere', 'Astra leaves and read-only roles NEVER write', 'Unknown identity/effects grant no writes', 'Authorized native reads use the actual host budget; do not imitate Reader guarantees'):
            self.assertIn(phrase, text)

    def test_outer_output_envelope_and_cursor_recovery_are_explicit(self):
        text = contract_text()
        for phrase in ('verified Python `-I -B <Skill>/scripts/readonly_reader.py`', 'check exit before JSON', 'preserve every error and cursor', 'Count the whole serialized output and framing, not individual rows', 'preserve truncation as PARTIAL', 'Reader responses remain <=4KiB', 'batch uses bounded UTF-8 stdin'):
            self.assertIn(phrase, text)

    def test_reader_call_and_dispatch_checklist_boundaries_are_explicit(self):
        text = SKILL.read_text()
        for phrase in ('substantial Codex coding, diagnosis and review', 'Batch independent reads within the actual output budget', 'check exit before JSON'):
            self.assertIn(phrase, text)

    def test_dispatch_preflight_is_installed_reader_and_scripts_are_verified(self):
        text = contract_text()
        for phrase in ('Use ordinary native delegation when no dispatch admission boundary is active',
                       'Never bypass a configured boundary', 'Strict sends still require fresh checked admission',
                       'Reader `assignment --help`', 'verify script paths before use'):
            self.assertIn(phrase, text)
        self.assertIn('only for Router development', (ROOT/'docs/INSTALL.md').read_text())
        from manage import source_files
        self.assertEqual({k for k in source_files(ROOT) if k.startswith('skill/scripts/')},
                         {'skill/scripts/readonly_reader.py'})

    def test_monitoring_uses_one_delta_then_backoff(self):
        text = contract_text()
        for phrase in ('Two unchanged snapshots: back off', 'one saved-offset delta', 'not repeated tails or nudges', 'No unrequested monitoring', 'retain cursors and liveness/errors'):
            self.assertIn(phrase, text)

    def test_child_instructions_remain_self_contained(self):
        for name in EXPECTED:
            text = tomllib.loads((ROOT / 'agents' / name).read_text())['developer_instructions']
            for boundary in ('UNKNOWN', 'PASS/PARTIAL/BLOCKED', 'parent completion'):
                self.assertIn(boundary, text, name)
            self.assertNotIn('SKILL.md', text, name)
            self.assertNotIn('@include', text, name)
            if name == 'astra-architect.toml':
                for boundary in ('Always read-only', 'file/checkpoint', 'Terra/Sol', 'no auto-revert'):
                    self.assertIn(boundary, text)
            else:
                for boundary in ('write scope', 'retry history across workers',
                                 'Never weaken assertions', 'Parent releases current host binding before'):
                    self.assertIn(boundary, text, name)
                self.assertTrue('No spawning' in text or 'Only parent-authorized Ultra spawns' in text)

    def test_readonly_diagnosis_and_limits_remain_reachable(self):
        text = contract_text()
        for phrase in ('Astra leaves and read-only roles NEVER write', 'Root Astra defaults read-only', 'native admission has no repair exceptions', 'Unknown identity/effects grant no writes', 'no auto-revert', 'Two writers max', 'Exhaustion stops blind edits, not diagnosis', 'Retries persist per task/unit/signature across ALL owners', 'accepts integration'):
            self.assertIn(phrase, text)

    def test_coordination_and_acceptance_enter_before_waits_without_python_parent(self):
        text = contract_text()
        for phrase in ("before a parent's first collection/final", 'Before waiting, check ready work and available parent review', 'Use optional COORDINATION_JS only with matching host tools', 'do not rewrite it each poll', 'completion_check only when the configured host exposes/requires it', 'beginning before appending requirements', 'reconciling before final check', 'Parent review of original code/evidence/test applicability cannot be replaced by a child claim'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
