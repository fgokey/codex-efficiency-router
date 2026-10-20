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
        for phrase in ('before dispatch/lane changes', 'for Astra admission',
                       'before delegation, binding or delivery review',
                       'for large evidence, semantic/lifecycle changes, failure or disputed validation'):
            self.assertIn(phrase, text)

    def test_parent_final_requires_objective_and_remaining_work_reconciliation(self):
        # Source-contract regression for the observed premature final, not live behavior proof.
        core = SKILL.read_text(encoding='utf-8')
        self.assertTrue('## Completion' in core, 'Missing prominent parent completion decision')
        self.assertLess(core.index('## Completion'), core.index('## Routing'))
        self.assertTrue('before an active engineering parent final' in core)
        text = contract_text()
        for phrase in ('original user objective', 'accepted scope',
                       'every remaining required item', 'current authority'):
            self.assertTrue(phrase in text, phrase)

    def test_actionable_incomplete_parent_work_requires_continuation(self):
        text = contract_text()
        for phrase in ('CONTINUE while useful authorized diagnosis, delegation or implementation remains',
                       'Missing measurements or an unresolved design decision alone',
                       'never establish completion/blockage',
                       'Do not require the user to type continue'):
            self.assertTrue(phrase in text, phrase)

    def test_partial_child_and_green_local_checks_do_not_end_parent_work(self):
        self.assertTrue('Child PASS/PARTIAL or local checks/reviews never complete the parent'
                        in contract_text())

    def test_parent_complete_requires_all_required_items_and_current_evidence(self):
        self.assertTrue('COMPLETE only when every required item is satisfied by current evidence'
                        in contract_text())

    def test_external_blocker_requires_specific_evidence_and_unaffected_work(self):
        text = contract_text()
        for phrase in ('BLOCKED only for an actual external barrier',
                       'exact missing access/input/resource, evidence, affected scope',
                       'required user/external action', 'finish unaffected authorized work'):
            self.assertTrue(phrase in text, phrase)

    def test_standalone_status_ends_but_mid_task_status_preserves_objective(self):
        text = contract_text()
        self.assertTrue('STATUS/Q&A ends only a standalone question task' in text)
        self.assertTrue('During active work answer briefly then continue the original objective '
                        'unless stopped/changed' in text)

    def test_stop_and_scope_limits_bound_parent_continuation(self):
        text = contract_text()
        for phrase in ('STOP on explicit stop/pause/cancel, accepted scope change',
                       'actual tool/system budget ceiling; report remaining work',
                       'Continue within existing authority/scope',
                       'no automatic monitoring, risky measurement/deploy, new authority, '
                       'infinite retry or extra model probes'):
            self.assertTrue(phrase in text, phrase)

    def test_entry_is_cheap_but_does_not_grant_authority(self):
        text = SKILL.read_text()
        self.assertLessEqual(len(text.encode('utf-8')), 2048)
        for phrase in ('Cheap local Q&A/status/low-risk', 'no children/references', 'Delegation always routes',
                       'repo rules, current permissions/read-only roles',
                       'Unknown identity/effects grant no writes', 'exact pins', 'Low is opt-in',
                       'Sends require Reader `assignment`', 'Root Astra defaults read-only',
                       'native admission has no repair exceptions'):
            self.assertIn(phrase, text)
        chain = doctor.instruction_chain(SKILL)
        self.assertEqual(set(chain), {'SKILL.md', 'references/dispatch.md', 'references/effort.md',
                                     'references/quality.md', 'references/routing.md'})

    def test_no_blanket_loading_or_full_router_in_children(self):
        text = contract_text()
        self.assertIn('No doc/hook preload or child router copy', text)
        self.assertIn('Report once:', text)
        self.assertIn('Never invent identity/savings/enforcement/cleanup', text)

    def test_outer_output_envelope_and_cursor_recovery_are_explicit(self):
        text = contract_text()
        core = SKILL.read_text(encoding='utf-8')
        description = next(line for line in core.splitlines() if line.startswith('description:'))
        self.assertIn('Read SKILL alone, one page per tool call', description)
        self.assertLess(core.index('Check exit before JSON'), core.index('Read [effort.md]'))
        for phrase in ('Read SKILL alone, one page per tool call',
                       'Verified Python `-I -B <Skill>/scripts/readonly_reader.py`',
                       'handoff both', '`page --root ABS --path PATH`',
                       'current located lines: `excerpt --start N --lines N` (count 1..200)',
                       'unknown: `locate --query Q`', 'Files/rules: `page`',
                       'same root/path `--cursor TOKEN` to null', 'Output+framing <=4KiB',
                       'Check exit before JSON', 'Fix limits/page/locate errors',
                       'no full-file slicing/merging pages/files',
                       'JSON+CRLF+framing <=4KiB',
                       'capture/select/serialize/count before emit',
                       'one results JSON', 'keep each cursor', 'no early member output',
                       'batch --requests JSON_ARRAY --max-bytes N --framing-bytes N',
                       'Resume gaps', 'disclose omissions'):
            self.assertIn(phrase, text)
        for name in EXPECTED:
            role = tomllib.loads((ROOT / 'agents' / name).read_text())['developer_instructions']
            phrases = ('Given Python -I -B <reader>', 'page files',
                       'excerpt located lines (count 1..200)', 'Check exit before JSON',
                       'One page, no full-file slicing/merging',
                       'other totals <outer incl framing')
            for phrase in phrases:
                self.assertIn(phrase, role, name)

    def test_reader_call_and_dispatch_checklist_boundaries_are_explicit(self):
        core = SKILL.read_text(encoding='utf-8')
        description = next(line for line in core.splitlines() if line.startswith('description:'))
        self.assertIn('Read SKILL alone, one page per tool call', description)
        self.assertIn('One Reader invocation/tool call', core)
        self.assertIn('no joined pages/queries or mixed Get-Content', core)

    def test_dispatch_preflight_is_installed_reader_and_scripts_are_verified(self):
        dispatch = (SKILL.parent / 'references/dispatch.md').read_text(encoding='utf-8')
        self.assertIn('Dispatch preflight: Reader `assignment` before task-bearing sends', dispatch)
        self.assertIn('assignment --help', dispatch)
        self.assertIn('Verify script paths before use', dispatch)
        self.assertNotIn('Run dispatch preflight.', dispatch)
        self.assertIn('Checks: one Reader `batch', contract_text())
        self.assertIn('Router ROOT dev only:', contract_text())
        self.assertIn('ROOT/scripts/doctor.py --source-tree ROOT --preflight', contract_text())
        from manage import source_files
        scripts = {key for key in source_files(ROOT) if key.startswith('skill/scripts/')}
        self.assertEqual(scripts, {'skill/scripts/readonly_reader.py'})

    def test_monitoring_uses_one_delta_then_backoff(self):
        text = contract_text()
        for phrase in ('Two unchanged snapshots', 'one saved-offset delta', 'back off',
                       'no repeat tails/polls/nudges until change',
                       'Standalone status/check: one-shot; explicit watch',
                       'heartbeat: defer schedule or pause, never skipped wakeups',
                       'compact state/cadence; stop on cancel'):
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
        for phrase in ('Astra leaves and read-only roles NEVER write', 'Root Astra defaults read-only',
                       'native admission has no repair exceptions', 'Unknown identity/effects grant no writes',
                       'no auto-revert', 'Two writers max',
                       'Exhaustion stops blind edits, not diagnosis', 'across ALL owners',
                       'Retries persist per task/unit/signature across ALL owners',
                       'accepts integration'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
