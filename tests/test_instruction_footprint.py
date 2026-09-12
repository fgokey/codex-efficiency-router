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


class InstructionFootprintTests(unittest.TestCase):
    def test_tightened_source_budgets(self):
        # These limits are smaller than rc.1, not raised to make compression pass.
        self.assertLessEqual(INSTRUCTION_BUDGETS['core_skill_bytes'], 5200)
        self.assertLessEqual(INSTRUCTION_BUDGETS['full_skill_bytes'], 9600)
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
                errors = doctor.validate_agent(path, (role, 'gpt-5.6-sol', 'medium'), Profile())
                self.assertTrue(any('role instructions exceed' in e for e in errors))

    def test_reference_load_triggers_remain_reachable(self):
        text = SKILL.read_text()
        for name in ('effort', 'routing', 'dispatch', 'quality'):
            self.assertEqual(text.count(f'references/{name}.md'), 1)
            self.assertTrue((SKILL.parent / 'references' / f'{name}.md').is_file())
        for phrase in ('once at its trigger', 'stale or lost after compaction',
                       'before dispatch', 'before delegation/guarded shell',
                       'for checkpointing/recovery/disputed evidence'):
            self.assertIn(phrase, text)

    def test_no_blanket_loading_or_full_router_in_children(self):
        text = SKILL.read_text()
        self.assertIn('Do not preload docs/hooks or copy the router into children', text)
        self.assertIn('Report once:', text)
        self.assertIn('No unobserved cleanup claims or repeated routing banners', text)

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
                                 'Never weaken assertions', 'No spawning'):
                    self.assertIn(boundary, text, name)

    def test_readonly_diagnosis_and_limits_remain_in_core(self):
        text = SKILL.read_text()
        for phrase in ('Astra leaves and read-only roles NEVER write', 'Root Astra defaults read-only',
                       'one bounded local code patch', 'Unknown identity/effects grant no writes',
                       'never auto-revert', 'two concurrent writers', 'the third waits',
                       'Exhaustion stops blind edits, not diagnosis', 'across ALL owners',
                       'never renews attempts', 'independent acceptance'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
