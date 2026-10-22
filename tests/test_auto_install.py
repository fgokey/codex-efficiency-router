"""One-command install/update, deterministic dual bindings, ownership and recovery."""
import contextlib
import io
import json
import shutil
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
from package import AUTO_DESCRIPTION_PREFIX, EXPECTED, AUTO_EXPECTED, MANIFEST, resolve_targets


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

    def test_compat_install_is_explicit_skill_only_and_idempotent(self):
        self.install(host_mode='compat',dry_run=True)
        self.assertFalse(self.skill.exists());self.assertFalse(self.backups.exists())
        self.install(host_mode='compat')
        manifest=self.manifest();before=self.state();backup=self.backup()
        self.assertEqual(manifest['host_mode'],'compat')
        self.assertFalse(self.agents.exists())
        self.assertTrue(all(k.startswith('skill/') for k in manifest['files']))
        self.assertNotIn('subagent_defaults',manifest)
        self.assertEqual(doctor.validate_tree(self.skill/'SKILL.md',self.agents,
                         from_manifest(manifest)),[])
        self.install();self.assertEqual(self.state(),before);self.assertEqual(self.backup(),backup)
        self.assertIn('Host mode: compat.',(self.skill/'SKILL.md').read_text())
        self.assertFalse((self.root/'.codex/config.toml').exists())
        self.assertFalse((self.root/'.codex/hooks.json').exists())
        text=(self.skill/'SKILL.md').read_text()
        self.assertNotIn('Root Astra defaults read-only',text)
        self.assertNotIn('Unknown identity/effects grant no writes',text)
        self.assertIn("does not block the current executor's already authorized work",text)
        self.assertIn('Python/Reader/completion_check are optional',text)
        for mode in ('fixed','adaptive'):
            self.install(mode=mode)
            profile=from_manifest(self.manifest())
            self.assertEqual(profile.host_mode,'compat')
            self.assertEqual(doctor.validate_tree(self.skill/'SKILL.md',self.agents,profile),[])
            footprint=doctor.instruction_footprint(self.skill/'SKILL.md',self.agents,profile)
            self.assertLessEqual(footprint['full_skill_bytes'],10800)
            self.assertEqual(footprint['role_developer_instruction_bytes'],{})

    def test_compat_never_removes_full_protection_or_sets_defaults(self):
        self.install();before=self.state();backup=self.backup()
        with self.assertRaisesRegex(ValueError,'full installation'):
            self.install(host_mode='compat',force=True)
        self.assertEqual(self.state(),before);self.assertEqual(self.backup(),backup)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'compat.*defaults'):
                manage.install(ROOT,'project',Path(tmp),host_mode='compat',set_subagent_defaults=True)
            self.assertFalse((Path(tmp)/'.codex/config.toml').exists())
            with self.assertRaisesRegex(ValueError,'legacy full installation'):
                manage.install(ROOT,'project',Path(tmp),host_mode='compat',adopt_v01=True)

    def test_host_mode_schema_requires_explicit_compat_and_retains_legacy_full(self):
        self.assertEqual(from_manifest({'mode':'auto','allow_low':False,'profile_schema':2}).host_mode,'full')
        self.assertEqual(from_manifest({}).host_mode,'full')
        for fields in ({'host_mode':'compat','profile_schema':2},
                       {'profile_schema':3},
                       {'host_mode':'unknown','profile_schema':3},
                       {'host_mode':'compat','profile_schema':3,'subagent_defaults':{}},
                       {'host_mode':'compat','profile_schema':3,'allow_low':True}):
            with self.assertRaises(ValueError):
                from_manifest(dict(mode='auto',allow_low=False)|fields)
        with self.assertRaises(ValueError):self.install(host_mode='unknown')
        self.assertFalse(self.skill.exists())

    def test_compat_manifest_cannot_take_ownership_of_full_roles(self):
        self.install(host_mode='compat');manifest=self.manifest()
        manifest['files']['agents/sol61-engineer.toml']='0'*64
        (self.skill/MANIFEST).write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'cannot own roles'):
            manage.uninstall('project',self.root,force=True)

    def test_compat_preserves_foreign_roles_hooks_and_restores_owned_changes(self):
        self.agents.mkdir(parents=True)
        foreign=self.agents/'sol61-engineer.toml';foreign.write_text('private role')
        hooks=self.root/'.codex/hooks.json';hooks.write_text('{"hooks":{}}')
        self.install(host_mode='compat')
        core=self.skill/'SKILL.md';core.write_bytes(core.read_bytes()+b'\nprivate')
        with self.assertRaisesRegex(ValueError,'managed file'):
            self.install()
        customized=self.state();self.install(force=True);backup=self.backup()
        manage.restore(backup,'project',self.root)
        self.assertEqual(self.state(),customized)
        self.install(force=True)
        manage.uninstall('project',self.root)
        self.assertEqual(foreign.read_text(),'private role')
        self.assertEqual(hooks.read_text(),'{"hooks":{}}')

    def test_compat_to_full_requires_explicit_selection_and_checks_collisions(self):
        self.install(host_mode='compat');before=self.state()
        self.agents.mkdir(parents=True)
        role=self.agents/'sol61-engineer.toml';role.write_text('private')
        with self.assertRaisesRegex(ValueError,'unowned'):
            self.install(host_mode='full')
        self.assertEqual((self.skill/MANIFEST).read_bytes(),before[str(self.skill/MANIFEST)])
        role.unlink();self.install(host_mode='full')
        self.assertEqual(from_manifest(self.manifest()).host_mode,'full')
        self.assertEqual(len(list(self.agents.glob('*.toml'))),10)

    def prior_sol_inventory(self):
        # Model the 0.7.1-owned 16 paths without depending on Git history.
        self.install()
        m=self.manifest()
        for name in ('sol61-engineer.toml','cer-auto-sol61-engineer.toml'):
            (self.agents/name).unlink()
            del m['files']['agents/'+name]
        m['version']='0.7.1'
        (self.skill/MANIFEST).write_text(json.dumps(m))

    def test_plain_install_marks_auto_bindings_for_native_discovery(self):
        self.install()
        self.assertEqual(self.manifest()['mode'],'auto')
        self.assertEqual(len(list(self.agents.glob('*.toml'))),10)
        self.assertEqual(doctor.validate_tree(self.skill/'SKILL.md',self.agents,Profile('auto')),[])
        for name,(role,model,effort) in EXPECTED.items():
            fixed=tomllib.loads((self.agents/name).read_text())
            alias=tomllib.loads((self.agents/('cer-auto-'+name)).read_text())
            expected=dict(fixed,name='cer_auto_'+role);del expected['model_reasoning_effort']
            expected['description']=AUTO_DESCRIPTION_PREFIX+fixed['description']
            self.assertEqual(alias,expected)
        astra=tomllib.loads((self.agents/'cer-auto-astra-architect.toml').read_text())
        self.assertEqual(astra['sandbox_mode'],'read-only')

    def test_plain_reinstall_is_noop(self):
        self.install();before=self.state();backup=self.backup()
        self.install();self.assertEqual(self.state(),before);self.assertEqual(self.backup(),backup)

    def test_071_inventory_adds_both_sol61_roles_with_backup_and_restore(self):
        self.prior_sol_inventory()
        self.assertEqual(self.manifest()['profile_schema'], 3)
        self.assertEqual(self.manifest()['host_mode'], 'full')
        before=self.state();old_backup=self.backup()
        self.assertEqual(len(self.manifest()['files']),16)
        self.install(dry_run=True)
        self.assertEqual(self.state(),before);self.assertEqual(self.backup(),old_backup)
        self.install()
        self.assertEqual(self.manifest()['version'],'0.8.5')
        self.assertEqual(len(self.manifest()['files']),18)
        self.assertEqual(len(list(self.agents.glob('*.toml'))),10)
        backup=self.backup()
        self.assertNotEqual(backup,old_backup)
        manage.restore(backup,'project',self.root)
        self.assertEqual(self.state(),before)

    def test_071_inventory_refuses_new_unowned_or_changed_old_role(self):
        self.prior_sol_inventory()
        new=self.agents/'sol61-engineer.toml'
        new.write_text('private role')
        before=self.state()
        with self.assertRaises(ValueError):self.install(force=True)
        self.assertEqual(self.state(),before)
        new.unlink()
        old=self.agents/'sol-engineer.toml'
        old.write_bytes(old.read_bytes()+b'\n# local edit\n')
        before=self.state()
        with self.assertRaises(ValueError):self.install()
        self.assertEqual(self.state(),before)

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

    def test_missing_pinned_or_unmarked_alias_fails_doctor(self):
        self.install();p=self.agents/'cer-auto-sol-engineer.toml';original=p.read_bytes()
        p.write_bytes(b'model_reasoning_effort = "medium"\n'+original)
        self.assertTrue(doctor.validate_tree(self.skill/'SKILL.md',self.agents,Profile('auto')))
        p.write_bytes(original.replace(AUTO_DESCRIPTION_PREFIX.encode(),b''))
        self.assertTrue(doctor.validate_tree(self.skill/'SKILL.md',self.agents,Profile('auto')))
        p.write_bytes(original)
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
        self.assertEqual(source['skill/scripts/readonly_reader.py'],
                         (ROOT/'hooks/readonly_reader.py').read_bytes())
        self.assertEqual(source['skill/cer.ps1'],(ROOT/'cer.ps1').read_bytes())
        rendered=render_payload(source,Profile('auto'))
        self.assertEqual(source,before)
        self.assertEqual(set(rendered)-set(source),{'agents/'+n for n in AUTO_EXPECTED})

    def test_source_payload_refuses_duplicate_reader_or_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for directory in ('skills','agents','hooks'):
                shutil.copytree(ROOT/directory,root/directory)
            shutil.copy2(ROOT/'cer.ps1',root/'cer.ps1')
            for relative in ('scripts/readonly_reader.py','cer.ps1'):
                collision=root/'skills/codex-efficiency-router'/relative
                collision.parent.mkdir(parents=True,exist_ok=True)
                collision.write_text('unowned',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'duplicate source payload'):
                    manage.source_files(root)
                collision.unlink()

    def test_profile_schema_rejects_missing_fields_and_unknown_version(self):
        for value in ({'profile_schema':2}, {'profile_schema':99},
                      {'profile_schema':True,'mode':'auto','allow_low':False}):
            with self.subTest(value=value),self.assertRaises(ValueError):from_manifest(value)
        self.assertEqual(select_profile(None),Profile('auto'))
        self.assertEqual(select_profile(from_manifest({})),Profile('auto'))

    def test_auto_catalog_does_not_require_unused_high_on_every_model(self):
        models={}
        for _,model,effort in EXPECTED.values():
            models.setdefault(model,set()).add(effort)
        data={'data':[{'model':model,'supportedReasoningEfforts':[
            {'reasoningEffort':effort} for effort in sorted(efforts)]}
            for model,efforts in models.items()], 'nextCursor':None}
        self.assertEqual(doctor.validate_catalog(data,Profile('auto')),[])
        self.assertTrue(doctor.validate_catalog(data,Profile('adaptive')))

    def prior_sol_model(self, mode='auto'):
        self.install(mode=mode)
        manifest=self.manifest()
        names=('sol-engineer.toml','cer-auto-sol-engineer.toml') if mode=='auto' else ('sol-engineer.toml',)
        for name in names:
            path=self.agents/name
            raw=path.read_bytes().replace(b'model = "gpt-6.1-sol"',b'model = "gpt-6-sol"')
            self.assertIn(b'model = "gpt-6-sol"',raw)
            path.write_bytes(raw)
            manifest['files']['agents/'+name]=manage.digest(raw)
        (self.skill/MANIFEST).write_text(json.dumps(manifest),encoding='utf-8')
        return names

    def test_retired_owned_sol_roles_upgrade_in_place_and_restore_exactly(self):
        for mode in ('auto','fixed','adaptive'):
            with self.subTest(mode=mode):
                names=self.prior_sol_model(mode)
                before=self.state();previous=self.backup()
                self.install(dry_run=True)
                self.assertEqual(self.state(),before)
                self.assertEqual(self.backup(),previous)
                self.install()
                self.assertEqual(self.manifest()['mode'],mode)
                for name in names:
                    self.assertEqual(tomllib.loads((self.agents/name).read_text())['model'],'gpt-6.1-sol')
                for path in self.agents.glob('*.toml'):
                    self.assertNotIn(tomllib.loads(path.read_text())['model'],('gpt-6-sol','gpt-5.6-sol'))
                backup=self.backup()
                self.assertNotEqual(backup,previous)
                manage.restore(backup,'project',self.root)
                self.assertEqual(self.state(),before)
                self.install()

    def test_retired_sol_customization_blocks_migration_without_partial_writes(self):
        self.prior_sol_model()
        changed=self.agents/'cer-auto-sol-engineer.toml'
        changed.write_bytes(changed.read_bytes()+b'\n# user customization\n')
        before=self.state();backup=self.backup()
        with self.assertRaisesRegex(ValueError,'managed file was changed'):
            self.install()
        self.assertEqual(self.state(),before)
        self.assertEqual(self.backup(),backup)

    def test_policy_default_and_modes_match_installer(self):
        from profiles import MODES
        policy=json.loads((ROOT/'policy/routing-policy.json').read_text())
        effort=policy['effort_policy']
        self.assertEqual(effort['installation_default'],select_profile(None).mode)
        self.assertEqual(effort['modes'],list(MODES))
        self.assertEqual(policy['automatic_bindings']['default_install'],select_profile(None).mode)

if __name__=='__main__':unittest.main()
