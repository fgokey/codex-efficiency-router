"""Real temporary-directory lifecycle coverage for generated installation modes."""
from dataclasses import replace
from pathlib import Path
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import manage
import doctor
from package import EXPECTED, MANIFEST, PROJECT, resolve_targets
from profiles import Profile, render_payload, select_profile, from_manifest
from catalog import parse_catalog


class ProfileLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name).resolve() / 'project space'
        self.project.mkdir()
        self.skill, self.agents, self.backups = resolve_targets('project', self.project)
        out = contextlib.redirect_stdout(io.StringIO())
        out.__enter__(); self.addCleanup(out.__exit__, None, None, None)

    def install(self, **kwargs):
        return manage.install(ROOT, 'project', self.project, **kwargs)

    def files(self):
        return {str(p): p.read_bytes() for d in (self.skill, self.agents) if d.exists()
                for p in d.rglob('*') if p.is_file()}

    def manifests(self):
        return json.loads((self.skill / MANIFEST).read_text())

    def backups_list(self):
        return sorted(p for p in self.backups.iterdir() if p.is_dir())

    def assert_installed(self, profile):
        self.assertEqual(manage.installed_profile(self.skill, self.agents), profile)
        self.assertEqual(doctor.validate_tree(self.skill / 'SKILL.md', self.agents, profile), [])
        for name, (_, model, effort) in EXPECTED.items():
            config = tomllib.loads((self.agents / name).read_text())
            self.assertEqual(config['model'], model)
            if profile.mode == 'adaptive':
                self.assertNotIn('model_reasoning_effort', config)
            else:
                self.assertEqual(config['model_reasoning_effort'], effort)
        self.assertEqual(set(p.name for p in self.agents.glob('*.toml')), set(EXPECTED))
        self.assertIn(profile.marker, (self.skill / 'SKILL.md').read_text())

    def test_new_default_fixed(self):
        self.install(); self.assert_installed(Profile())

    def test_explicit_adaptive_renders_four_unpinned_roles(self):
        self.install(mode='adaptive'); self.assert_installed(Profile('adaptive'))
        source = manage.source_files(ROOT)
        target = self.files()
        for name in EXPECTED:
            original = tomllib.loads(source['agents/' + name].decode())
            new = tomllib.loads((self.agents / name).read_text())
            self.assertEqual(new, {k: v for k, v in original.items() if k != 'model_reasoning_effort'})
        self.assertEqual(new['developer_instructions'], original['developer_instructions'])

    def test_implicit_update_preserves_adaptive_and_low(self):
        self.install(mode='adaptive', allow_low=True)
        before = self.files(); backups = self.backups_list()
        self.install()
        self.assert_installed(Profile('adaptive', True))
        self.assertEqual(self.files(), before)
        self.assertEqual(self.backups_list(), backups)

    def test_switch_to_fixed_disables_low_and_can_restore_profile(self):
        self.install(mode='adaptive', allow_low=True)
        previous = self.files()
        self.install(mode='fixed'); self.assert_installed(Profile())
        backup = self.backups_list()[-1]
        manage.restore(backup, 'project', self.project)
        self.assertEqual(self.files(), previous)
        self.assert_installed(Profile('adaptive', True))

    def test_low_can_be_explicitly_disabled(self):
        self.install(mode='adaptive', allow_low=True)
        self.install(allow_low=False)
        self.assert_installed(Profile('adaptive'))

    def test_low_invalid_in_fixed_even_with_force(self):
        self.install(); before = self.files()
        with self.assertRaises(ValueError): self.install(allow_low=True, force=True)
        self.assertEqual(self.files(), before)

    def test_switch_dry_run_is_read_only(self):
        self.install(); before = self.files(); backups = self.backups_list()
        self.install(mode='adaptive', allow_low=True, dry_run=True)
        self.assertEqual(self.files(), before); self.assertEqual(self.backups_list(), backups)

    def test_locally_modified_fixed_or_adaptive_roles_block_mode_change(self):
        for mode in ('fixed', 'adaptive'):
            self.install(mode=mode, force=True)
            p = self.agents / 'sol-engineer.toml'
            p.write_bytes(p.read_bytes() + b'\n# user change\n')
            before = self.files()
            with self.assertRaises(ValueError):
                self.install(mode='fixed' if mode == 'adaptive' else 'adaptive')
            self.assertEqual(self.files(), before)

    def test_force_mode_change_backs_up_customized_owned_files(self):
        self.install()
        p = self.agents / 'sol-engineer.toml'
        p.write_bytes(p.read_bytes() + b'\n# custom\n'); original = p.read_bytes()
        self.install(mode='adaptive', force=True)
        saved = self.backups_list()[-1] / 'files/agents/sol-engineer.toml'
        self.assertEqual(saved.read_bytes(), original)
        self.assert_installed(Profile('adaptive'))

    def test_switch_failure_rolls_back_profile_and_files_together(self):
        self.install(); before = self.files()
        original = manage.os.replace
        calls = 0
        def fail_once(a, b):
            nonlocal calls
            calls += 1
            if calls == 3: raise OSError('injected mode-switch failure')
            return original(a, b)
        with patch.object(manage.os, 'replace', side_effect=fail_once), self.assertRaises(OSError):
            self.install(mode='adaptive')
        self.assertEqual(self.files(), before); self.assert_installed(Profile())

    def test_adaptive_uninstall_and_explicit_restore(self):
        self.install(mode='adaptive', allow_low=True)
        before = self.files()
        manage.uninstall('project', self.project)
        self.assertFalse(self.skill.exists())
        self.assertFalse(any(self.agents.glob('*.toml')))
        manage.restore(self.backups_list()[-1], 'project', self.project)
        self.assertEqual(self.files(), before); self.assert_installed(Profile('adaptive', True))

    def test_mode_tampered_manifest_is_not_silently_accepted(self):
        self.install(mode='adaptive')
        data = self.manifests(); data['mode'] = 'fixed'
        (self.skill / MANIFEST).write_text(json.dumps(data))
        self.assertTrue(doctor.validate_tree(self.skill / 'SKILL.md', self.agents, Profile()))

    def test_invalid_profile_manifest_blocks_lifecycle(self):
        self.install(); p = self.skill / MANIFEST
        original = p.read_text()
        for bad in ({'mode': 'automatic', 'allow_low': False}, {'mode': 'fixed', 'allow_low': True},
                    {'mode': 'adaptive', 'allow_low': 'false'}):
            data = json.loads(original); data.update(bad); p.write_text(json.dumps(data))
            before = self.files()
            with self.assertRaises(ValueError): self.install(force=True)
            with self.assertRaises(ValueError): manage.uninstall('project', self.project, force=True)
            self.assertEqual(self.files(), before)

    def test_legacy_manifest_without_profile_upgrades_to_fixed(self):
        self.install()
        data = self.manifests(); del data['mode']; del data['allow_low']; data['version'] = '0.3.0'
        (self.skill / MANIFEST).write_text(json.dumps(data))
        self.install(); self.assert_installed(Profile())

    def test_user_scope_honors_codex_home_without_touching_config(self):
        home = Path(self.tmp.name) / 'home'; home.mkdir()
        codex = home / 'custom_codex'; codex.mkdir()
        conf = codex / 'config.toml'; conf.write_bytes(b'model = "custom"\r\n')
        with patch.object(Path, 'home', return_value=home), patch.dict(os.environ, {'CODEX_HOME': str(codex)}):
            manage.install(ROOT, 'user', None, mode='adaptive')
            skill, agents, _ = resolve_targets('user', None)
            self.assertEqual(doctor.validate_tree(skill / 'SKILL.md', agents, Profile('adaptive')), [])
            manage.uninstall('user', None)
        self.assertEqual(conf.read_bytes(), b'model = "custom"\r\n')

    def test_existing_legacy_adoption_can_directly_choose_adaptive(self):
        import shutil
        fixture = ROOT / 'tests/fixtures/v01'
        shutil.copytree(fixture / 'skill', self.skill)
        shutil.copytree(fixture / 'agents', self.agents)
        self.install(adopt_v01=True, mode='adaptive'); self.assert_installed(Profile('adaptive'))

    def test_legacy_collision_stays_unowned_in_adaptive(self):
        self.agents.mkdir(parents=True)
        p = self.agents / 'sol-engineer.toml'; p.write_text('unrelated')
        with self.assertRaises(ValueError): self.install(mode='adaptive', force=True)
        self.assertEqual(p.read_text(), 'unrelated')

    def test_canonical_source_is_not_mutated_by_generation(self):
        source = manage.source_files(ROOT); before = dict(source)
        for p in (Profile(), Profile('adaptive'), Profile('adaptive', True)):
            generated = render_payload(source, p)
            self.assertEqual(set(source), set(generated))
        self.assertEqual(source, before)
        broken = dict(source); broken['skill/SKILL.md'] += b'\nInstallation: fixed; automatic low: disabled.\n'
        with self.assertRaises(ValueError): render_payload(broken, Profile('adaptive'))

    def test_cli_profile_and_restore_argument_contract(self):
        flags = ['--scope', 'project', '--project-root', str(self.project)]
        def run(script, *args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *flags, *args],
                                  capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(run('install.py', '--mode', 'adaptive', '--allow-low').returncode, 0)
        check = run('doctor.py'); self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn('profile: adaptive', check.stdout); self.assertIn('NOT VERIFIED', check.stdout)
        self.assertEqual(run('install.py', '--mode', 'fixed', '--restore', 'not-a-real-path').returncode, 2)
        self.assertEqual(run('install.py', '--allow-low', '--no-allow-low').returncode, 2)
        self.assertEqual(run('uninstall.py').returncode, 0)


class ProfileAndCatalogUnitTests(unittest.TestCase):
    def test_profile_options_are_strict_and_preserved(self):
        self.assertEqual(select_profile(Profile('adaptive', True)), Profile('adaptive', True))
        self.assertEqual(select_profile(Profile('adaptive', True), mode='fixed'), Profile())
        self.assertEqual(from_manifest({}), Profile())
        for bad in ({'mode': 'adaptive'}, {'allow_low': True}, {'mode': 'fixed', 'allow_low': True}):
            with self.assertRaises(ValueError): from_manifest(bad)
        for args in (('unknown', False), ('fixed', True), ('adaptive', 1)):
            with self.assertRaises(ValueError): Profile(*args)

    def catalog(self):
        return {'data': [{'model': m, 'supportedReasoningEfforts': [{'reasoningEffort': e} for e in ('medium', 'high')]}
                         for _, m, _ in EXPECTED.values()], 'nextCursor': None}

    def test_catalog_for_fixed_adaptive_and_opt_in_low(self):
        data = self.catalog()
        self.assertEqual(doctor.validate_catalog(data), [])
        self.assertEqual(doctor.validate_catalog(data, Profile('adaptive')), [])
        self.assertTrue(doctor.validate_catalog(data, Profile('adaptive', True)))
        data['data'][0]['supportedReasoningEfforts'].append({'reasoningEffort': 'low'})
        self.assertEqual(doctor.validate_catalog(data, Profile('adaptive', True)), [])

    def test_catalog_missing_high_rejected_for_adaptive_not_fixed(self):
        data = self.catalog(); data['data'][2]['supportedReasoningEfforts'] = [{'reasoningEffort': 'medium'}]
        self.assertEqual(doctor.validate_catalog(data), [])
        self.assertTrue(doctor.validate_catalog(data, Profile('adaptive')))

    def test_bad_efforts_duplicate_models_and_missing_pagination_are_errors(self):
        data = self.catalog(); data['data'].append(data['data'][0])
        with self.assertRaises(ValueError): parse_catalog(data)
        data = self.catalog(); del data['nextCursor']
        with self.assertRaises(ValueError): parse_catalog(data)
        for value in ([], True, None, '', {}):
            data = self.catalog(); data['data'][0]['supportedReasoningEfforts'][0]['reasoningEffort'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): parse_catalog(data)

    def test_static_doctor_distinguishes_pinned_missing_and_generated_effort(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'role.toml'; name, entry = next(iter(EXPECTED.items()))
            original = (ROOT / 'agents' / name).read_text()
            p.write_text(original)
            self.assertEqual(doctor.validate_agent(p, entry), [])
            self.assertTrue(doctor.validate_agent(p, entry, Profile('adaptive')))
            p.write_text(original.replace('model_reasoning_effort = "medium"\n', ''))
            self.assertTrue(doctor.validate_agent(p, entry))
            self.assertEqual(doctor.validate_agent(p, entry, Profile('adaptive')), [])


if __name__ == '__main__':
    unittest.main()
