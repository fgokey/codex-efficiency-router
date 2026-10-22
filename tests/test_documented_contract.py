"""Distribution/CLI contracts and readable instruction boundaries, not live compliance.

Keep executable policy tests separate. These assertions cover meaning-bearing
sentences in the compact instructions, not obsolete wording or protocol repetition.
"""
from pathlib import Path
import inspect
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

SKILL = ROOT / 'skills' / PROJECT


def contract_text():
    return '\n'.join(doctor.instruction_chain(SKILL / 'SKILL.md').values())


class DocumentedContractTests(unittest.TestCase):
    def requires(self, *phrases, file=None):
        text = (SKILL / file).read_text(encoding='utf-8') if file else contract_text()
        for phrase in phrases:
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
        self.assertEqual({p.name for p in (ROOT / 'agents').glob('*.toml')}, set(EXPECTED))
        for filename, (role, model, effort) in EXPECTED.items():
            data = tomllib.loads((ROOT / 'agents' / filename).read_text(encoding='utf-8'))
            self.assertEqual((data['name'], data['model'], data['model_reasoning_effort']), (role, model, effort))
            for path in ('README.md', 'README.zh-CN.md', f'skills/{PROJECT}/references/effort.md'):
                rows = [line for line in (ROOT / path).read_text(encoding='utf-8').splitlines()
                        if line.startswith('|') and f'`{role}`' in line]
                self.assertEqual(len(rows), 1, (path, role))
                self.assertIn(model, rows[0]); self.assertIn(effort, rows[0])

    def test_restore_is_explicit_not_an_uninstall_option(self):
        self.assertIn('--restore', install.build_parser()._option_string_actions)
        self.assertEqual(set(uninstall.build_parser()._option_string_actions),
                         {'-h', '--help', '--scope', '--project-root', '--dry-run', '--force'})
        self.assertNotIn('restore(', inspect.getsource(uninstall.main))

    def test_policy_budgets_and_version_match_code(self):
        policy = json.loads((ROOT / 'policy/routing-policy.json').read_text(encoding='utf-8'))
        for key, value in INSTRUCTION_BUDGETS.items():
            self.assertEqual(policy['budgets'][key], value)
        self.assertEqual(policy['version'], (ROOT / 'VERSION').read_text().strip())

    def test_full_reference_budget_detects_hidden_bloat(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / PROJECT
            shutil.copytree(SKILL, skill)
            (skill / 'references/extra.md').write_text('padding ' * 2000)
            self.assertTrue(any('ALL references' in e for e in doctor.validate_tree(skill / 'SKILL.md', ROOT / 'agents')))

    def test_staged_role_reference_is_validated_and_missing_preset_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / PROJECT
            shutil.copytree(SKILL, skill)
            self.assertEqual(doctor.validate_tree(skill / 'SKILL.md', ROOT / 'agents'), [])
            path = skill / 'references/effort.md'
            original = path.read_text(encoding='utf-8')
            bad = original.replace('gpt-6-astra', 'missing-model')
            self.assertNotEqual(bad, original); path.write_text(bad, encoding='utf-8')
            self.assertIn('missing Astra preset', doctor.validate_tree(skill / 'SKILL.md', ROOT / 'agents'))

    def test_ambiguous_or_duplicate_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / PROJECT
            shutil.copytree(SKILL, skill)
            path = skill / 'SKILL.md'; original = path.read_text(encoding='utf-8')
            for bad in (original.replace('description: ', 'description: malformed: ', 1),
                        original.replace('name: codex-efficiency-router', 'name: codex-efficiency-router\nname: duplicate'),
                        original.replace('description: ', 'description: # missing ', 1)):
                self.assertNotEqual(bad, original); path.write_text(bad, encoding='utf-8')
                self.assertTrue(any('frontmatter' in e for e in doctor.validate_tree(path, ROOT / 'SKILL.md')))

    def test_core_safety_contract_survives_compression(self):
        self.requires('Unknown identity/effects grant no writes', 'NEVER write, build, test',
                      'No classifier call, nested model CLI/API', 'no-subagent and no-escalation',
                      'Never weaken assertions', 'required gaps remain PARTIAL/BLOCKED',
                      'same admitted executor', 'contextual value AND net benefit')

    def test_engineering_default_dispatch_pins_complete_routing_parameters(self):
        self.requires('`cer_auto_<role>` with explicit effort and `fork_turns=none`',
                      'Sol61/high when difficulty is unknown', 'Confirmed simple work may use medium',
                      'Verify actual host binding before RELEASE', 'Respect explicit pins',
                      file='references/effort.md')

    def test_auto_dispatch_is_explicit_and_fixed_fallback_is_evidenced(self):
        self.requires('Choose model and effort jointly', 'observed unavailability',
                      'exact role/catalog pair', 'Never silently remap',
                      'Low remains opt-in', file='references/effort.md')

    def test_semantic_loss_and_review_evidence_are_required(self):
        self.requires('platform/macros, consumers and lifecycle effects', 'Loss/eviction/coalescing',
                      'safe discard/replay/rebuild', 'source evidence or a requirement violation',
                      'hypotheses and preexisting hazards', 'not proof of end-to-end correctness',
                      file='references/quality.md')

    def test_astra_does_not_own_long_command_continuations(self):
        self.requires('Astra uses permitted reads and saved evidence, never `write_stdin`',
                      'Executors own long commands/continuation', file='references/dispatch.md')

    def test_native_change_review_preserves_write_and_delivery_evidence(self):
        self.requires('all roots, exact paths/status/diffs and prior dirt', 'accepts integration',
                      'never fake a badge or edit for attribution', file='references/dispatch.md')
        for filename in ('luna-worker.toml', 'terra-executor.toml', 'sol-engineer.toml'):
            instructions = tomllib.loads((ROOT / 'agents' / filename).read_text())['developer_instructions']
            for phrase in ('roots', 'exact paths/status/diff', 'owned/prior dirt', 'current evidence', 'never parent completion'):
                self.assertIn(phrase, instructions)

    def test_native_badge_support_is_separate_from_write_authority(self):
        self.requires('file-change attribution is optional unless required by the user',
                      'never fake a badge', 'UNKNOWN/MISMATCH blocks writes',
                      file='references/dispatch.md')

    def test_native_root_astra_boundary_has_no_repair_exception(self):
        self.requires('Root Astra defaults read-only', 'native admission has no repair exceptions',
                      'Strict Guard remains strict', 'Custom-host installation is separate')
        self.assertNotIn('one bounded local repair unit', contract_text())

    def test_write_binding_and_reviewable_mutation_are_mandatory(self):
        self.requires('host model/effort/role/permission/owner is verified',
                      'explicitly RELEASE the unit', 'UNKNOWN/MISMATCH blocks writes',
                      'Closed/unloaded/restarted workers need fresh binding',
                      'raw `resume_agent` cannot pin them', 'Policy denial stops equivalent replay',
                      'never evade `approval=never`', file='references/dispatch.md')

    def test_first_authorized_assignment_contains_the_current_unit_release(self):
        self.requires('HOLD until current host', 'explicitly RELEASE the unit',
                      'Send exactly the checked prefix and body', 'never grants authority',
                      'always pass returned `admitted_dispatch_arguments`',
                      file='references/dispatch.md')

    def test_controls_are_not_new_work_or_write_authority(self):
        self.requires('Exact continue/status/stop controls reuse the current receipt, scope and binding',
                      'Added instructions require new admission', 'Bare control words are not receipts',
                      'Wait/interrupt/close remain separate controls', file='references/dispatch.md')

    def test_delivery_owner_requires_existing_user_authority(self):
        self.requires('commit/push/deploy need separate user authority and exact destinations')
        for name in ('sol-engineer.toml', 'terra-executor.toml'):
            text = tomllib.loads((ROOT / 'agents' / name).read_text())['developer_instructions']
            self.assertIn('Commit/push/deploy/publish: user authority', text)
            self.assertIn('exact repo/ref/destination/checks', text)
        luna = tomllib.loads((ROOT / 'agents/luna-worker.toml').read_text())['developer_instructions']
        for phrase in ('No spawning', 'nested model CLI/API', 'self model/effort changes', 'no commit/push/deploy/publish'):
            self.assertIn(phrase, luna)

    def test_compact_handoff_preserves_rules_and_decision_rationale(self):
        self.requires('facts versus assumptions', 'revision/dirt', 'rule paths', 'rationale/invariants',
                      'critical gaps block affected work', 'Contrary evidence reopens decisions')
        for name in EXPECTED:
            role = tomllib.loads((ROOT / 'agents' / name).read_text())['developer_instructions'].lower()
            self.assertRegex(role, r'read (?:applicable )?repo(?:sitory)? rules', name)
            self.assertRegex(role, r'(?:missing critical context blocks|critical (?:context )?gaps block) affected work', name)

    def test_mismatch_recovery_is_reachable_without_low_opt_in(self):
        self.requires('Resolve MISMATCH at a safe boundary', 'reconcile effects',
                      'review affected acceptance', 'later VERIFIED does not erase outstanding review',
                      'Keep attempts and user limits', file='references/effort.md')


if __name__ == '__main__':
    unittest.main()
