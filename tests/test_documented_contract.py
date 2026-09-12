"""Executable interface checks, not claims of live model compliance."""
from pathlib import Path
import json
import re
import shutil
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import install
import uninstall
import doctor
from package import EXPECTED, INSTRUCTION_BUDGETS, PROJECT


class DocumentedContractTests(unittest.TestCase):
    def test_readme_cli_options_match_real_parsers(self):
        modules = {'install': install, 'uninstall': uninstall, 'doctor': doctor}
        for filename in ('README.md', 'README.zh-CN.md', 'docs/INSTALL.md', 'docs/ACCEPTANCE.md'):
            text = (ROOT / filename).read_text(encoding='utf-8')
            for block in re.findall(r'```(?:sh|bash|powershell)\n(.*?)```', text, re.S):
                commands = re.findall(r'scripts[/\\](install|uninstall|doctor)\.py([^\n]*)', block)
                commands += re.findall(r'\.\\cer\.ps1 (install|uninstall|doctor)([^\n]*)', block)
                for script, rest in commands:
                    accepted = modules[script].build_parser()._option_string_actions
                    for option in re.findall(r'--[a-z][a-z0-9-]*', rest):
                        self.assertIn(option, accepted, f'{filename}: {script}.py {option}')

    def test_exactly_four_roles_match_readme_and_core(self):
        self.assertEqual(len(EXPECTED), 4)
        self.assertEqual(set(p.name for p in (ROOT / 'agents').glob('*.toml')), set(EXPECTED))
        for filename, (role, model, effort) in EXPECTED.items():
            data = tomllib.loads((ROOT / 'agents' / filename).read_text())
            self.assertEqual((data['name'], data['model'], data['model_reasoning_effort']), (role, model, effort))
            for path in ('README.md', 'README.zh-CN.md', f'skills/{PROJECT}/SKILL.md'):
                rows = [line for line in (ROOT / path).read_text(encoding='utf-8').splitlines()
                        if line.startswith('|') and f'`{role}`' in line]
                self.assertEqual(len(rows), 1, (path, role))
                self.assertIn(model, rows[0])
                self.assertIn(effort, rows[0])

    def test_restore_is_explicit_not_an_uninstall_option(self):
        self.assertIn('--restore', install.build_parser()._option_string_actions)
        opts = uninstall.build_parser()._option_string_actions
        self.assertEqual(set(opts), {'-h', '--help', '--scope', '--project-root', '--dry-run', '--force'})
        self.assertNotIn('--restore', opts)
        self.assertNotIn('--no-restore', opts)

    def test_policy_budgets_and_version_match_code(self):
        policy = json.loads((ROOT / 'policy/routing-policy.json').read_text())
        for key, value in INSTRUCTION_BUDGETS.items():
            self.assertEqual(policy['budgets'][key], value)
        self.assertEqual(policy['version'], (ROOT / 'VERSION').read_text().strip())

    def test_full_reference_budget_detects_hidden_bloat(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / PROJECT
            shutil.copytree(ROOT / 'skills' / PROJECT, skill)
            (skill / 'references/extra.md').write_text('padding ' * 2000)
            errors = doctor.validate_tree(skill / 'SKILL.md', ROOT / 'agents')
            self.assertTrue(any('ALL references' in error for error in errors))

    def test_ambiguous_or_duplicate_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / PROJECT
            shutil.copytree(ROOT / 'skills' / PROJECT, skill)
            path = skill / 'SKILL.md'
            original = path.read_text()
            for bad in (original.replace('tasks; reserve', 'tasks: reserve'),
                        original.replace('name: codex-efficiency-router',
                                         'name: codex-efficiency-router\nname: duplicate'),
                        original.replace('description: Quality-gated', 'description: # missing')):
                with self.subTest(text=bad[:120]):
                    path.write_text(bad)
                    self.assertTrue(any('frontmatter' in error
                                        for error in doctor.validate_tree(path, ROOT / 'agents')))

    def test_core_safety_contract_survives_compression(self):
        # Wording sentinels prevent accidental deletion, not semantic-quality proof.
        core = (ROOT / 'skills' / PROJECT / 'SKILL.md').read_text()
        for phrase in ('UNKNOWN, not PASS', 'read-only', 'no-subagent/no-escalation',
                       'Do not weaken assertions', 'contrary evidence', 'revision/dirty state',
                       'Same-model delegation', 'AND a net benefit', 'stop risky writes',
                       'No extra LLM classifier', 'No agent per file', 'Never auto-select `max`'):
            self.assertIn(phrase, core)

    def test_writer_changes_remain_reviewable_from_readonly_parent(self):
        core = (ROOT / 'skills' / PROJECT / 'SKILL.md').read_text()
        dispatch = (ROOT / 'skills' / PROJECT / 'references/dispatch.md').read_text()
        self.assertIn('writer review handoff in dispatch', core)
        for phrase in ('every repository root', 'exact changed paths/status',
                       'pre-existing dirt', 'status/diff per repository',
                       'native review/open-review', 'unstaged review',
                       'does not aggregate child `fileChange` events',
                       'never touches or reapplies files for attribution'):
            self.assertIn(phrase, dispatch)
        for filename in ('luna-worker.toml', 'terra-executor.toml', 'sol-engineer.toml'):
            instructions = tomllib.loads((ROOT / 'agents' / filename).read_text())['developer_instructions']
            self.assertIn('every repository root and exact changed paths/status', instructions)
            self.assertIn('owned from prior dirt', instructions)
            self.assertIn('current requirement-to-check/review evidence', instructions)
            self.assertIn('not parent completion', instructions)

    def test_no_implicit_restore_or_nested_model_process_in_lifecycle(self):
        # The existing function tests exercise restore separately and owned-only deletion.
        import inspect
        self.assertNotIn('restore(', inspect.getsource(uninstall.main))


if __name__ == '__main__':
    unittest.main()
