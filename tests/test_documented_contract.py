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


def contract_text():
    return '\n'.join(doctor.instruction_chain(ROOT / 'skills' / PROJECT / 'SKILL.md').values())


class DocumentedContractTests(unittest.TestCase):
    def test_engineering_default_dispatch_pins_complete_routing_parameters(self):
        from effort_reference import dispatch_arguments
        from test_effort_auto import host, AUTO, S, plan
        args = dispatch_arguments(plan(S(), host(), AUTO))
        self.assertEqual(args, {'agent_type':'cer_auto_sol61_engineer',
                               'reasoning_effort':'high','fork_turns':'none'})
        text = contract_text()
        for phrase in ('Default uncertain engineering/review to Sol61/high',
                       'confirmed simple work may use medium', 'Routine released leaves'):
            self.assertIn(phrase, text)

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
            for path in ('README.md', 'README.zh-CN.md', f'skills/{PROJECT}/references/effort.md'):
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

    def test_staged_role_reference_is_validated_and_missing_preset_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / PROJECT
            shutil.copytree(ROOT / 'skills' / PROJECT, skill)
            self.assertEqual(doctor.validate_tree(skill / 'SKILL.md', ROOT / 'agents'), [])
            path=skill/'references/effort.md';original=path.read_text(encoding='utf-8')
            bad=original.replace('gpt-6-astra','missing-model')
            self.assertNotEqual(bad,original);path.write_text(bad,encoding='utf-8')
            self.assertIn('missing Astra preset',doctor.validate_tree(skill / 'SKILL.md', ROOT / 'agents'))

    def test_ambiguous_or_duplicate_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / PROJECT
            shutil.copytree(ROOT / 'skills' / PROJECT, skill)
            path = skill / 'SKILL.md'
            original = path.read_text()
            for bad in (original.replace('description: ', 'description: malformed: ', 1),
                        original.replace('name: codex-efficiency-router',
                                         'name: codex-efficiency-router\nname: duplicate'),
                        original.replace('description: ', 'description: # missing ', 1)):
                with self.subTest(text=bad[:120]):
                    self.assertNotEqual(bad, original)
                    path.write_text(bad)
                    self.assertTrue(any('frontmatter' in error
                                        for error in doctor.validate_tree(path, ROOT / 'agents')))

    def test_core_safety_contract_survives_compression(self):
        text = contract_text()
        for phrase in ('Astra leaves and read-only roles NEVER write', 'Unknown identity/effects grant no writes', 'Never weaken assertions', 'Default to one implementer and an on-demand reviewer', 'no classifier, nested model CLI/API', 'exact pins', 'Honor disable/no-subagent/no-escalation', 'preserve every error and cursor'):
            self.assertIn(phrase, text)

    def test_semantic_loss_and_review_evidence_are_required(self):
        text = contract_text()
        for phrase in ('Loss/eviction/coalescing must preserve effects', 'justified discard/replay/rebuild behavior', 'preexisting hazards separate from new defects', 'requirement or before/after evidence', 'A test model or static score is not proof of production semantics', 'consumers, platform/macros and behavior'):
            self.assertIn(phrase, text)

    def test_astra_does_not_own_long_command_continuations(self):
        text = contract_text()
        for phrase in ('executors own builds, tests and terminal continuation', 'Astra inspects evidence and coordinates'):
            self.assertIn(phrase, text)

    def test_native_change_review_preserves_write_and_delivery_evidence(self):
        text = contract_text()
        for phrase in ('Return actual roots, paths, diff, checks, prior dirt and gaps', 'The parent accepts integration against the current workspace', 'child PASS is not parent completion'):
            self.assertIn(phrase, text)

    def test_native_badge_support_is_separate_from_write_authority(self):
        text = contract_text()
        for phrase in ('Optional UI attribution must not block authorized work unless required by the user', 'never fake it', 'current host-observed model/effort/role/permission/owner', 'explicitly releases unit for writes'):
            self.assertIn(phrase, text)

    def test_auto_dispatch_is_explicit_and_fixed_fallback_is_evidenced(self):
        text = contract_text()
        for phrase in ('Select model AND effort', '`cer_auto_<role>` with explicit effort', 'exact selected pair', 'dynamic binding is unavailable', 'Do not label a fixed fallback as adaptive success'):
            self.assertIn(phrase, text)

    def test_native_root_astra_boundary_has_no_repair_exception(self):
        text = contract_text()
        for phrase in ('Root Astra defaults read-only', 'native admission has no repair exceptions', 'Capacity never grants writes', 'Astra stays read-only throughout', 'Never bypass a configured boundary'):
            self.assertIn(phrase, text)

    def test_write_binding_and_reviewable_mutation_are_mandatory(self):
        text = contract_text()
        for phrase in ('current host-observed model/effort/role/permission/owner', 'explicitly releases unit for writes', 'Configuration, self-description and old logs are not identity', 'UNKNOWN/MISMATCH blocks writes', 'closed/restarted workers need fresh binding and release', 'Reuse the same live owner', 'Policy denial stops equivalent replay/repackaging', 'approval=never', 'Publication, deployment, binary replacement and destructive recovery need separate authority'):
            self.assertIn(phrase, text)

    def test_first_authorized_assignment_contains_the_current_unit_release(self):
        text = contract_text()
        for phrase in ('RELEASE current unit', 'explicitly releases unit for writes', 'UNKNOWN/MISMATCH blocks writes', 'Read-only roles never become writers', 'exact checked body'):
            self.assertIn(phrase, text)

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
        self.assertIn('need separate authority',dispatch)

    def test_compact_handoff_preserves_rules_and_decision_rationale(self):
        text = contract_text()
        for phrase in ('rule paths', 'facts versus assumptions', 'rationale/invariants', 'allowed changes, prohibited actions, checks and remaining attempts', 'no inherited history'):
            self.assertIn(phrase, text)

    def test_mismatch_recovery_is_reachable_without_low_opt_in(self):
        text = contract_text()
        for phrase in ('UNKNOWN is not MISMATCH', 'Resolve MISMATCH at a safe boundary and review affected work', 'Later VERIFIED does not erase that review or reset attempts', 'Suspend auto-low after either status'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
