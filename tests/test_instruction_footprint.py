"""Readable loading/authority contracts and unchanged size gates; not model evals."""
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
    def test_observed_overhead_repairs_keep_native_reads_and_review_concrete(self):
        for name in ('sol61-engineer.toml', 'sol-engineer.toml'):
            text = tomllib.loads((ROOT / 'agents' / name).read_text(encoding='utf-8'))['developer_instructions']
            for phrase in ('Batch UTF-8 projections', 'before emit', 'counts/cursors/status/errors'):
                self.assertIn(phrase, text)
            self.assertLessEqual(len(text.encode('utf-8')), 945)
        text = contract_text()
        for phrase in ('open the actual source/diff/result',
                       'child reports and completion_check declarations alone',
                       'unit-specific context', 'do not resend unchanged rules or reports',
                       'Check authority, exclusive scope and capacity',
                       'For required independent Standards/Spec',
                       'Reuse compatible owners at safe boundaries',
                       'pin revision/dirt/rules/spec',
                       'dispatch separate read-only owners before waiting',
                       'Locate once; batch independent required ranges',
                       'Store read_thread results; select',
                       'Keep complete id/task_revision inventory; one work entry/id',
                       'Repage new revision',
                       'After tool results: fresh inspect then check alone',
                       'work/input invalidates it', 'Child status adds no work'):
            self.assertIn(phrase, text)

    def test_tightened_source_budgets(self):
        for key, limit in {'core_skill_bytes': 5200, 'full_skill_bytes': 10800,
                           'discovery_description_characters': 180,
                           'role_developer_instruction_bytes': 950}.items():
            self.assertLessEqual(INSTRUCTION_BUDGETS[key], limit)
        self.assertEqual(doctor.validate_tree(SKILL, ROOT / 'agents'), [])

    def test_footprint_counts_core_once_and_every_reference(self):
        result = doctor.instruction_footprint(SKILL, ROOT / 'agents')
        refs = list((SKILL.parent / 'references').rglob('*.md'))
        self.assertEqual(result['core_skill_bytes'], len(SKILL.read_bytes()))
        self.assertEqual(result['full_skill_bytes'], len(SKILL.read_bytes()) +
                         sum(len(p.read_bytes()) + 1 for p in refs))
        self.assertEqual(len(result['reference_bytes']), len(refs))
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
            data = tomllib.loads((ROOT / 'agents' / name).read_text(encoding='utf-8'))
            self.assertEqual(result['role_developer_instruction_bytes'][name],
                             len(data['developer_instructions'].encode('utf-8')))

    def test_role_bloat_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sol-engineer.toml'
            source = (ROOT / 'agents' / path.name).read_text(encoding='utf-8')
            for role in ('sol_engineer', 'cer_auto_sol_engineer'):
                text = source.replace('developer_instructions = """',
                                      'developer_instructions = """' + 'padding ' * 130)
                path.write_text(text.replace('name = "sol_engineer"', f'name = "{role}"'), encoding='utf-8')
                errors = doctor.validate_agent(path, (role, 'gpt-6-sol', 'medium'), Profile())
                self.assertTrue(any('role instructions exceed' in e for e in errors))

    def test_reference_load_triggers_remain_reachable(self):
        text = SKILL.read_text(encoding='utf-8')
        for name in ('effort', 'routing', 'dispatch', 'quality'):
            self.assertEqual(text.count(f'references/{name}.md'), 1)
        self.assertEqual(set(doctor.instruction_chain(SKILL)), {'SKILL.md',
            'references/dispatch.md', 'references/effort.md', 'references/quality.md', 'references/routing.md'})
        for phrase in ('before the first parent wait or final engineering answer',
                       'for complex lifecycle or disputed evidence',
                       'before selecting a worker', 'for Astra admission',
                       'once before delegation', 'not the whole Router'):
            self.assertIn(phrase, text)

    def test_parent_completion_requires_objective_and_current_evidence(self):
        core = SKILL.read_text(encoding='utf-8')
        self.assertLess(core.index('## Completion'), core.index('## Routing'))
        for phrase in ('original user objective', 'accepted scope', 'every remaining required item',
                       'current authority', 'COMPLETE requires current evidence for every requirement',
                       'child PASS or green local checks are not parent completion'):
            self.assertIn(phrase, contract_text())

    def test_incomplete_work_continues_but_external_barriers_are_specific(self):
        for phrase in ('CONTINUE while useful authorized diagnosis, delegation or implementation remains',
                       'BLOCKED requires the exact external missing resource',
                       'evidence, affected scope and required external action', 'finish unaffected work',
                       'STOP on explicit pause/cancel, scope change or actual system budget ceiling',
                       'Answer mid-task status briefly and continue', 'standalone questions end after answering',
                       'Never start unrequested monitoring or risky measurements'):
            self.assertIn(phrase, contract_text())

    def test_independent_answer_is_explicit_bounded_and_keeps_engineering_protection(self):
        self.assertIn('turn_scope:independent_answer', contract_text())
        docs = (ROOT / 'README.md').read_text(encoding='utf-8')
        for phrase in ('turn_scope:independent_answer', 'current versions', '1..1024 UTF-8 bytes',
                       'retains every engineering requirement', 'never completes the objective',
                       'The model judges independence', 'No automatic exemption',
                       'engineering or new evidence requires full reconciliation',
                       'restart discards the declaration'):
            self.assertIn(phrase, docs)

    def test_entry_is_small_but_authority_and_triggers_are_explicit(self):
        text = SKILL.read_text(encoding='utf-8')
        self.assertLessEqual(len(text.encode('utf-8')), 2048)
        for phrase in ('Route substantial Codex coding, diagnosis and review',
                       'Skip simple questions and tiny edits', 'do not stack active routers',
                       'Root Astra defaults read-only', 'native admission has no repair exceptions',
                       'Astra leaves and read-only roles NEVER write',
                       'Unknown identity/effects grant no writes',
                       'No classifier call', 'nested model CLI/API', 'exact pins'):
            self.assertIn(phrase, text)

    def test_native_reads_do_not_expand_actor_authority(self):
        for phrase in ('Released writers: authorized bounded native reads',
                       'Astra/readonly/unknown: guarded reads',
                       'Verify physical paths/links',
                       'Missing capabilities block only affected actions',
                       'never fabricate identity or enforcement'):
            self.assertIn(phrase, contract_text())
        from manage import source_files
        from profiles import render_payload
        source = source_files(ROOT)
        for mode in ('fixed', 'auto', 'adaptive'):
            payload = render_payload(source, Profile(mode))
            for key, raw in payload.items():
                if not key.startswith('agents/') or not key.endswith('.toml'):
                    continue
                role = tomllib.loads(raw.decode('utf-8'))
                instructions = role['developer_instructions']
                if role['model'] == 'gpt-6-astra':
                    self.assertIn('Always read-only', instructions)
                    self.assertNotIn('unless RELEASED writer', instructions)
                else:
                    if role['model'] == 'gpt-6.1-sol':
                        self.assertIn('RELEASED Sol61 may run authorized read commands', instructions)
                        self.assertIn('else Python -I -B <reader>', instructions)
                    else:
                        self.assertIn('Python -I -B <reader> unless RELEASED writer', instructions)
                    for phrase in ('aggregate+framing<=4KiB', 'no full-file slicing/merging',
                                   'Parent releases current host binding before writes; invalidation/UNKNOWN stops'):
                        self.assertIn(phrase, instructions)
                name = key.removeprefix('agents/')
                if name in EXPECTED:
                    original = tomllib.loads(source[key].decode('utf-8'))
                    self.assertEqual(role['model'], original['model'])
                    if mode == 'adaptive':
                        self.assertNotIn('model_reasoning_effort', role)
                    else:
                        self.assertEqual(role['model_reasoning_effort'], original['model_reasoning_effort'])

    def test_reading_keeps_complete_evidence_and_real_output_limits(self):
        for phrase in ('Reuse unchanged loaded rules', 'fully read necessary new/changed rules',
                       'Check exit before parsing', 'retain successful results, errors and each cursor',
                       'one aggregate budget including JSON, CRLF and framing (<=4KiB)',
                       'Read required ranges completely', 'continue missing pages rather than rereading files',
                       'Never slice full-file output', 'concatenate pages to evade limits',
                       'Batch independent reads and merged worker waits'):
            self.assertIn(phrase, contract_text())

    def test_no_blanket_loading_or_development_probe_in_runtime(self):
        text = contract_text()
        for phrase in ('Never copy full history or preload every reference',
                       'not the whole Router', 'Do not run development diagnostics for ordinary tasks',
                       'unavailable facts remain UNKNOWN', 'Report loaded version, mode and Guard evidence once'):
            self.assertIn(phrase, text)
        self.assertNotIn('doctor.py --preflight', text)
        from manage import source_files
        self.assertEqual({key for key in source_files(ROOT) if key.startswith('skill/scripts/')},
                         {'skill/scripts/readonly_reader.py'})

    def test_same_owner_and_control_paths_are_not_blanket_new_work(self):
        for phrase in ('Reuse the owner within the admitted unit',
                       'Keep the same admitted executor',
                       'Exact continue/status/stop controls reuse the current receipt',
                       'Added instructions require new admission',
                       'Bare control words are not receipts', 'Wait/interrupt/close remain separate controls',
                       'admitted_dispatch_arguments', 'never grants authority'):
            self.assertIn(phrase, contract_text())

    def test_monitoring_backs_off_instead_of_repeating_history(self):
        for phrase in ('Review available work before waiting',
                       'Inspect detail only on actionable change, failure or completion',
                       'after two unchanged snapshots back off',
                       'One saved-offset diagnostic delta is enough',
                       'do not repeat tails or nudges without new evidence',
                       'Optional `COORDINATION_JS` is an adapter, not proof of work'):
            self.assertIn(phrase, contract_text())

    def test_child_instructions_remain_self_contained(self):
        for name in EXPECTED:
            text = tomllib.loads((ROOT / 'agents' / name).read_text(encoding='utf-8'))['developer_instructions']
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

    def test_diagnosis_retry_and_quality_floor_survive_rewrite(self):
        for phrase in ('Astra participates directly in difficult diagnosis',
                       'repeated unexplained failure', 'no auto-revert', 'Two writers max',
                       'Attempts persist per task/unit/failure across all owners',
                       'Exhaustion stops blind edits, not Astra diagnosis', 'Never weaken assertions',
                       'Unrun evidence is UNKNOWN', 'required gaps remain PARTIAL/BLOCKED',
                       'only when provided by the host'):
            self.assertIn(phrase, contract_text())


if __name__ == '__main__':
    unittest.main()
