import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import write_guard as wg


class GuardLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.directory,self.config,self.backups=wg.targets('project',self.root)
        stream=contextlib.redirect_stdout(io.StringIO());stream.__enter__();self.addCleanup(stream.__exit__,None,None,None)

    def runop(self,action='install',**kwargs):
        return wg.lifecycle(action,'project',self.root,**kwargs)

    def test_install_merge_and_remove_preserve_foreign_hooks(self):
        self.config.parent.mkdir(parents=True)
        foreign={'matcher':'Bash','hooks':[{'type':'command','command':'echo existing'}]}
        original={'description':'keep','hooks':{'PreToolUse':[foreign],'Stop':[]}}
        self.config.write_text(json.dumps(original))
        self.runop(); doc=json.loads(self.config.read_text())
        self.assertEqual(len(doc['hooks']['PreToolUse']),2)
        self.runop('remove')
        self.assertEqual(json.loads(self.config.read_text()),original)
        self.assertFalse((self.directory/'astra_write_guard.py').exists())

    def test_dry_run_has_no_writes(self):
        self.runop(dry_run=True);self.assertEqual(list(self.root.iterdir()),[])

    def test_reinstall_is_idempotent(self):
        self.runop(); before=self.config.read_bytes();count=len(list(self.backups.iterdir()))
        self.runop();self.assertEqual(self.config.read_bytes(),before);self.assertEqual(len(list(self.backups.iterdir())),count)

    def test_user_modification_blocks_update_and_remove(self):
        self.runop();(self.directory/wg.FILES[0]).write_text('user edit')
        for action in ('install','remove'):
            with self.assertRaises(ValueError):self.runop(action)
        self.assertIn('PreToolUse',self.config.read_text())

    def test_force_backs_up_owned_edits_not_unowned_collisions(self):
        self.directory.mkdir(parents=True);(self.directory/wg.FILES[0]).write_text('not owned')
        with self.assertRaises(ValueError):self.runop(force=True)
        self.assertEqual((self.directory/wg.FILES[0]).read_text(),'not owned')

    def test_changed_registration_is_not_deleted(self):
        self.runop();doc=json.loads(self.config.read_text())
        doc['hooks']['PreToolUse'][0]['matcher']='Bash'
        self.config.write_text(json.dumps(doc))
        with self.assertRaises(ValueError):self.runop('remove',force=True)
        self.assertEqual(json.loads(self.config.read_text()),doc)

    def test_untracked_files_survive_removal(self):
        self.runop();note=self.directory/'notes.txt';note.write_text('keep')
        self.runop('remove');self.assertEqual(note.read_text(),'keep')

    def test_ordinary_failure_rolls_back_every_written_file(self):
        real=wg.replace;count=0
        def broken(path,data):
            nonlocal count
            count+=1
            if count==3:raise OSError('injected')
            return real(path,data)
        with patch.object(wg,'replace',side_effect=broken),self.assertRaises(OSError):self.runop()
        self.assertFalse(self.config.exists())
        self.assertFalse((self.directory/wg.FILES[0]).exists())

    def test_does_not_edit_global_codex_config_or_trust(self):
        self.config.parent.mkdir(parents=True);cfg=self.config.parent/'config.toml';cfg.write_text('custom')
        self.runop();self.assertEqual(cfg.read_text(),'custom')
        doc=json.loads(self.config.read_text());self.assertNotIn('trust',doc)
        command=doc['hooks']['PreToolUse'][0]['hooks'][0]['command']
        self.assertIn('-I',command);self.assertIn('-B',command)
        self.assertNotIn('bypass',command)

    def test_bad_existing_json_is_not_replaced(self):
        self.config.parent.mkdir(parents=True);self.config.write_text('{bad')
        with self.assertRaises(ValueError):self.runop()
        self.assertEqual(self.config.read_text(),'{bad')

    def test_duplicate_registration_is_error(self):
        self.runop();doc=json.loads(self.config.read_text());doc['hooks']['PreToolUse']*=2
        self.config.write_text(json.dumps(doc))
        with self.assertRaises(ValueError):self.runop('remove')

    def test_concurrent_foreign_hook_change_is_not_overwritten(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text('{}')
        original=wg.apply
        newer={'description':'concurrent edit','hooks':{'Stop':[]}}
        def raced(changes, backups, dry_run, expected=None):
            self.config.write_text(json.dumps(newer))
            return original(changes,backups,dry_run,expected)
        with patch.object(wg,'apply',side_effect=raced),self.assertRaises(ValueError):self.runop()
        self.assertEqual(json.loads(self.config.read_text()),newer)
        self.assertFalse((self.directory/wg.FILES[0]).exists())

    def test_guard_is_independent_of_main_skill_uninstall(self):
        self.runop();self.assertTrue((self.directory/'readonly_reader.py').exists())
        self.assertNotIn('.agents/skills',self.config.read_text())


class DispatchLifecycleTests(GuardLifecycleTests):
    def setUp(self):
        super().setUp()
        self.directory,self.config,self.backups=wg.targets('project',self.root,'dispatch')

    def runop(self,action='install',**kwargs):
        return wg.lifecycle(action,'project',self.root,boundary='dispatch',**kwargs)

    def test_guard_is_independent_of_main_skill_uninstall(self):
        self.runop()
        group=json.loads(self.config.read_text())['hooks']['PreToolUse'][0]
        self.assertNotEqual(group['matcher'],'*')
        self.assertIn('--dispatch-only',group['hooks'][0]['command'])
        self.assertIn('--policy-root',group['hooks'][0]['command'])
        status=wg.inspect_status('project',self.root,'dispatch')
        self.assertEqual(status['registration'],'PRESENT')
        self.assertEqual(status['trust'],'UNKNOWN')
        self.assertEqual(status['live_verification'],'NOT_RUN')

    def test_dispatch_and_strict_registrations_preserve_each_other_and_foreign_hook(self):
        self.config.parent.mkdir(parents=True)
        foreign={'matcher':'Bash','hooks':[{'type':'command','command':'r2c-owned'}]}
        self.config.write_text(json.dumps({'hooks':{'PreToolUse':[foreign]}}))
        wg.lifecycle('install','project',self.root)
        strict=json.loads(self.config.read_text())['hooks']['PreToolUse'][1]
        self.runop()
        groups=json.loads(self.config.read_text())['hooks']['PreToolUse']
        self.assertEqual(groups[:2],[foreign,strict])
        self.runop('remove')
        self.assertEqual(json.loads(self.config.read_text())['hooks']['PreToolUse'],[foreign,strict])
        wg.lifecycle('remove','project',self.root)
        self.assertEqual(json.loads(self.config.read_text())['hooks']['PreToolUse'],[foreign])


if __name__=='__main__':unittest.main()
