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

    def test_exactly_five_roles_match_readme_and_core(self):
        self.assertEqual(len(EXPECTED), 5)
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
            for bad in (original.replace('description: ', 'description: malformed: ', 1),
                        original.replace('name: codex-efficiency-router',
                                         'name: codex-efficiency-router\nname: duplicate'),
                        original.replace('description: Quality-gated', 'description: # missing')):
                with self.subTest(text=bad[:120]):
                    self.assertNotEqual(bad, original)
                    path.write_text(bad)
                    self.assertTrue(any('frontmatter' in error
                                        for error in doctor.validate_tree(path, ROOT / 'agents')))

    def test_core_safety_contract_survives_compression(self):
        # Wording sentinels prevent accidental deletion, not semantic-quality proof.
        core = (ROOT / 'skills' / PROJECT / 'SKILL.md').read_text()
        for phrase in ('UNKNOWN, not PASS', 'read-only', 'no-subagent/no-escalation',
                       'Do not weaken assertions', 'contrary evidence', 'revision/dirt',
                       'same-model handoff', 'AND net benefit', 'without authority/ownership/capacity',
                       'no classifier', 'no agent per file',
                       'higher efforts need evidence/support'):
            self.assertIn(phrase, core)

    def test_semantic_loss_and_review_evidence_are_required(self):
        core = (ROOT / 'skills' / PROJECT / 'SKILL.md').read_text()
        quality = (ROOT / 'skills' / PROJECT / 'references/quality.md').read_text()
        for phrase in ('changed semantic invariants', 'Loss/eviction/coalescing',
                       'discard/replay/rebuild', 'affected states', 'PARTIAL/BLOCKED'):
            self.assertIn(phrase, core)
        for phrase in ('Findings cite before/after or requirement violation', 'label hypotheses',
                       'Callback/gray/static score cannot prove event loss safe',
                       'preexisting hazards', 'unchanged baseline'):
            self.assertIn(phrase, quality)

    def test_astra_does_not_own_long_command_continuations(self):
        dispatch = (ROOT / 'skills' / PROJECT / 'references/dispatch.md').read_text()
        for phrase in ('Astra never uses write_stdin', 'Executors own long commands',
                       'long commands/continuation', 'bounded saved evidence'):
            self.assertIn(phrase, dispatch)

    def test_native_change_summary_is_preflighted_before_delegation(self):
        core = (ROOT / 'skills' / PROJECT / 'SKILL.md').read_text()
        dispatch = (ROOT / 'skills' / PROJECT / 'references/dispatch.md').read_text()
        self.assertIn('Run dispatch preflight', core)
        for phrase in ('every root', 'exact changed paths/status',
                       'owned/prior dirt', 'Parent checks each diff/status',
                       'review/open-review', 'unstaged review',
                       'workspace roots', 'native parent file-change attribution',
                       'model name and review/open-review do not prove it',
                       'Missing/unknown support stops',
                       'Never edit for attribution'):
            self.assertIn(phrase, dispatch)
        for filename in ('luna-worker.toml', 'terra-executor.toml', 'sol-engineer.toml'):
            instructions = tomllib.loads((ROOT / 'agents' / filename).read_text())['developer_instructions']
            for phrase in ('roots', 'exact paths/status/diff', 'owned/prior dirt',
                           'current evidence', 'never parent completion'):
                self.assertIn(phrase, instructions)

    def test_auto_dispatch_is_explicit_and_fixed_fallback_is_evidenced(self):
        core = (ROOT / 'skills' / PROJECT / 'SKILL.md').read_text()
        effort = (ROOT / 'skills' / PROJECT / 'references/effort.md').read_text()
        for text in (core, effort):
            self.assertIn('`cer_auto_<role>`', text)
            self.assertIn('base role is MISMATCH', text)
        self.assertIn('Select model AND effort', core)
        self.assertIn('explicit effort', effort)
        self.assertIn('exact role/catalog pair', effort)

    def test_bounded_root_astra_exception_and_strict_guard_are_not_conflated(self):
        core = (ROOT / 'skills' / PROJECT / 'SKILL.md').read_text()
        dispatch = (ROOT / 'skills' / PROJECT / 'references/dispatch.md').read_text()
        for phrase in ('one bounded local repair unit', 'two failed qualified executor attempts',
                       'current-workspace target', 'no observed active strict Guard'):
            self.assertIn(phrase, core)
        self.assertIn('Strict Guard denies Astra', dispatch)
        self.assertIn('UNKNOWN may deny', dispatch)

    def test_write_binding_and_reviewable_mutation_are_mandatory(self):
        core = (ROOT / 'skills' / PROJECT / 'SKILL.md').read_text()
        dispatch = (ROOT / 'skills' / PROJECT / 'references/dispatch.md').read_text()
        for phrase in ('host-observed', 'explicitly releases unit for writes',
                       'ID/config/claims/old logs fail', 'Same-session turns reuse release',
                       'real restart/resume or contradiction rechecks',
                       'UNKNOWN/MISMATCH blocks writes',
                       'source/build config', 'destructive recovery'):
            self.assertIn(phrase, dispatch)
        for phrase in ('Policy denial', 'equivalent replay/repackaging',
                       'approval=never', 'no manual boundary'):
            self.assertIn(phrase, dispatch)
        self.assertIn('Read dispatch before writes/delegation', core)

    def test_no_implicit_restore_or_nested_model_process_in_lifecycle(self):
        # The existing function tests exercise restore separately and owned-only deletion.
        import inspect
        self.assertNotIn('restore(', inspect.getsource(uninstall.main))

    def test_delivery_owner_requires_existing_user_authority(self):
        for name in ('sol-engineer.toml','terra-executor.toml'):
            text=tomllib.loads((ROOT/'agents'/name).read_text())['developer_instructions']
            self.assertIn('Commit/push/deploy/publish: user authority',text)
            self.assertIn('exact repo/ref/destination/checks',text)
        luna=tomllib.loads((ROOT/'agents/luna-worker.toml').read_text())['developer_instructions']
        for phrase in ('No spawning', 'nested model CLI/API', 'self model/effort changes',
                       'no commit/push/deploy/publish'):
            self.assertIn(phrase,luna)
        dispatch=(ROOT/'skills'/PROJECT/'references/dispatch.md').read_text()
        self.assertIn('grants none',dispatch)

    def test_compact_handoff_preserves_rules_and_decision_rationale(self):
        core=(ROOT/'skills'/PROJECT/'SKILL.md').read_text()
        for phrase in ('rule paths','rationale','context gaps block affected work'):
            self.assertIn(phrase,core)
        for name in EXPECTED:
            role=tomllib.loads((ROOT/'agents'/name).read_text())['developer_instructions'].lower()
            self.assertRegex(role,r'read (?:applicable )?repo(?:sitory)? rules',name)
            self.assertRegex(role,r'(?:missing critical context blocks|critical (?:context )?gaps block) affected work',name)

    def test_mismatch_recovery_is_reachable_without_low_opt_in(self):
        core=(ROOT/'skills'/PROJECT/'SKILL.md').read_text()
        effort=(ROOT/'skills'/PROJECT/'references/effort.md').read_text()
        self.assertIn('Resolve MISMATCH before continuation',core)
        for phrase in ('safe boundary','review affected checks','Later VERIFIED does not erase review',
                       'UNKNOWN is not failure','Retain work/attempts/limits'):
            self.assertIn(phrase,effort)


if __name__ == '__main__':
    unittest.main()
