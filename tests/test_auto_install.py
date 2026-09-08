"""One-command install/update, deterministic dual bindings, ownership and recovery."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import manage
import doctor
from profiles import Profile, from_manifest, select_profile, render_payload
from package import EXPECTED, AUTO_EXPECTED, MANIFEST, resolve_targets


class AutomaticInstallTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve()
        self.skill,self.agents,self.backups=resolve_targets('project',self.root)
        stream=contextlib.redirect_stdout(io.StringIO());stream.__enter__()
        self.addCleanup(stream.__exit__,None,None,None)

    def install(self,**kw):return manage.install(ROOT,'project',self.root,**kw)
    def state(self):
        return {str(p):p.read_bytes() for d in (self.skill,self.agents) if d.exists()
                for p in d.rglob('*') if p.is_file()}
    def backup(self):return sorted(p for p in self.backups.iterdir() if p.is_dir())[-1]
    def manifest(self):return json.loads((self.skill/MANIFEST).read_text())

    def test_plain_install_creates_eight_bindings_with_four_unchanged_policies(self):
        self.install()
        self.assertEqual(self.manifest()['mode'],'auto')
        self.assertEqual(len(list(self.agents.glob('*.toml'))),8)
        self.assertEqual(doctor.validate_tree(self.skill/'SKILL.md',self.agents,Profile('auto')),[])
        for name,(role,model,effort) in EXPECTED.items():
            fixed=tomllib.loads((self.agents/name).read_text())
            alias=tomllib.loads((self.agents/('cer-auto-'+name)).read_text())
            expected=dict(fixed,name='cer_auto_'+role);del expected['model_reasoning_effort']
            self.assertEqual(alias,expected)
        astra=tomllib.loads((self.agents/'cer-auto-astra-architect.toml').read_text())
        self.assertEqual(astra['sandbox_mode'],'read-only')

    def test_plain_reinstall_is_noop(self):
        self.install();before=self.state();backup=self.backup()
        self.install();self.assertEqual(self.state(),before);self.assertEqual(self.backup(),backup)

    def test_old_fixed_and_adaptive_plain_update_migrates_with_backup(self):
        for mode in ('fixed','adaptive'):
            self.install(mode=mode,allow_low=mode=='adaptive')
            m=self.manifest();del m['profile_schema'];m['version']='0.4.0'
            (self.skill/MANIFEST).write_text(json.dumps(m))
            before=self.state()
            self.install()
            self.assertEqual(self.manifest()['mode'],'auto')
            self.assertEqual(self.manifest()['allow_low'],mode=='adaptive')
            backup=self.backup()
            manage.restore(backup,'project',self.root)
            self.assertEqual(self.state(),before) # Restores exact old selection, not auto.

    def test_new_explicit_override_survives_plain_update(self):
        for mode in ('fixed','adaptive'):
            self.install(mode=mode)
            before=self.state();self.install();self.assertEqual(self.state(),before)
            self.assertEqual(self.manifest()['mode'],mode)

    def test_migration_preview_does_not_change_files_or_backups(self):
        self.install(mode='fixed');m=self.manifest();del m['profile_schema']
        (self.skill/MANIFEST).write_text(json.dumps(m));before=self.state();backup=self.backup()
        self.install(dry_run=True)
        self.assertEqual(self.state(),before);self.assertEqual(self.backup(),backup)

    def test_modified_old_role_prevents_automatic_migration(self):
        self.install(mode='adaptive');m=self.manifest();del m['profile_schema']
        (self.skill/MANIFEST).write_text(json.dumps(m))
        role=self.agents/'terra-executor.toml';role.write_bytes(role.read_bytes()+b'\n# custom\n')
        before=self.state()
        with self.assertRaises(ValueError):self.install()
        self.assertEqual(self.state(),before)

    def test_unowned_alias_collision_is_refused_even_with_force(self):
        self.agents.mkdir(parents=True)
        p=self.agents/'cer-auto-sol-engineer.toml';p.write_text('private unrelated settings')
        with self.assertRaises(ValueError):self.install(force=True)
        self.assertEqual(p.read_text(),'private unrelated settings')
        self.assertFalse((self.skill/MANIFEST).exists())

    def test_missing_or_pinned_alias_fails_doctor(self):
        self.install();p=self.agents/'cer-auto-sol-engineer.toml';original=p.read_bytes()
        p.write_bytes(b'model_reasoning_effort = "medium"\n'+original)
        self.assertTrue(doctor.validate_tree(self.skill/'SKILL.md',self.agents,Profile('auto')))
        p.unlink()
        self.assertTrue(doctor.validate_tree(self.skill/'SKILL.md',self.agents,Profile('auto')))

    def test_auto_uninstall_preserves_private_file_and_explicit_restore(self):
        self.install();extra=self.agents/'private.toml';extra.write_text('keep')
        before=self.state();manage.uninstall('project',self.root)
        self.assertEqual(list(self.agents.glob('*.toml')),[extra])
        manage.restore(self.backup(),'project',self.root)
        self.assertEqual(self.state(),before)

    def test_migration_write_failure_rolls_back_all_bindings_and_selection(self):
        self.install(mode='adaptive');m=self.manifest();del m['profile_schema']
        (self.skill/MANIFEST).write_text(json.dumps(m));before=self.state()
        original=manage.os.replace;count=0
        def fail_once(src,dst):
            nonlocal count
            count+=1
            if count==5:raise OSError('injected failure')
            return original(src,dst)
        with patch.object(manage.os,'replace',side_effect=fail_once), self.assertRaises(OSError):self.install()
        self.assertEqual(self.state(),before)

    def test_generate_aliases_without_mutating_canonical_source(self):
        source=manage.source_files(ROOT);before=dict(source)
        rendered=render_payload(source,Profile('auto'))
        self.assertEqual(source,before)
        self.assertEqual(set(rendered)-set(source),{'agents/'+n for n in AUTO_EXPECTED})

    def test_profile_schema_rejects_missing_fields_and_unknown_version(self):
        for value in ({'profile_schema':2}, {'profile_schema':99},
                      {'profile_schema':True,'mode':'auto','allow_low':False}):
            with self.subTest(value=value),self.assertRaises(ValueError):from_manifest(value)
        self.assertEqual(select_profile(None),Profile('auto'))
        self.assertEqual(select_profile(from_manifest({})),Profile('auto'))

    def test_auto_catalog_does_not_require_unused_high_on_every_model(self):
        data={'data':[{'model':m,'supportedReasoningEfforts':[{'reasoningEffort':e}]} for _,m,e in EXPECTED.values()],
              'nextCursor':None}
        self.assertEqual(doctor.validate_catalog(data,Profile('auto')),[])
        self.assertTrue(doctor.validate_catalog(data,Profile('adaptive')))

    def test_policy_default_and_modes_match_installer(self):
        from profiles import MODES
        policy=json.loads((ROOT/'policy/routing-policy.json').read_text())
        effort=policy['effort_policy']
        self.assertEqual(effort['installation_default'],select_profile(None).mode)
        self.assertEqual(effort['modes'],list(MODES))
        self.assertEqual(policy['automatic_bindings']['default_install'],select_profile(None).mode)

if __name__=='__main__':unittest.main()
