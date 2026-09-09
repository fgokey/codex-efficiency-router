"""Synthetic host execution tests: prove denied tools are not invoked by this harness.
Not a claim that an untested Codex version loads/trusts/enforces the hook.
"""
import json
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
GUARD=ROOT/'hooks/astra_write_guard.py'
MODULE=runpy.run_path(str(GUARD))


class NativeGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.file=self.root/'sentinel.txt';self.file.write_text('before',encoding='utf-8')

    def hook(self,tool='apply_patch',model='gpt-6-astra',data=None,raw=None):
        event={'hook_event_name':'PreToolUse','model':model,'session_id':'shared-parent',
               'cwd':str(self.root),'tool_name':tool,'tool_input':data or {}}
        p=subprocess.run([sys.executable,'-I','-B',str(GUARD)],input=raw if raw is not None else json.dumps(event),
                         capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else {}

    @staticmethod
    def denied(output):
        return output.get('hookSpecificOutput',{}).get('permissionDecision')=='deny'

    def test_astra_patch_denied_and_real_mutator_not_invoked(self):
        output=self.hook()
        self.assertTrue(self.denied(output))
        invoked=False
        if not self.denied(output):
            invoked=True;self.file.write_text('changed')
        self.assertFalse(invoked);self.assertEqual(self.file.read_text(),'before')

    def test_shell_build_test_format_and_hidden_language_writes_blocked(self):
        for cmd in ('cmake --build build','pytest --cov','cargo fmt','python -c "open(\"x\",\"w\")"',
                    'powershell Set-Content x y','git checkout -- .','curl -X POST example.invalid',
                    'echo x > sentinel.txt','check --dry-run'):
            self.assertTrue(self.denied(self.hook('Bash',data={'command':cmd})),cmd)

    def test_mcp_and_unknown_tool_not_authorized_by_readlike_names(self):
        for tool in ('mcp__fs__write_file','mcp__evil__read_file','python','js','new_tool','exec_command'):
            self.assertTrue(self.denied(self.hook(tool)))

    def test_sol_child_sharing_parent_session_is_not_misclassified(self):
        output=self.hook(model='gpt-5.6-sol')
        self.assertEqual(output,{})
        if not self.denied(output):self.file.write_text('sol-owned')
        self.assertEqual(self.file.read_text(),'sol-owned')

    def test_terra_and_luna_not_given_explicit_permission_override(self):
        for m in ('gpt-5.6-terra','gpt-5.6-luna','gpt-5.6-sol'):
            self.assertEqual(self.hook(model=m),{})

    def test_unknown_identity_and_snapshot_deny(self):
        for m in (None,'','gpt-6-astra-2026-09-01','gpt-5.6-sol-2026-09-01','gpt-5.6-sol-untrusted','fake-sol',{'model':'gpt-5.6-sol'}):
            self.assertTrue(self.denied(self.hook(model=m)))

    def test_tool_input_cannot_spoof_actual_model(self):
        self.assertTrue(self.denied(self.hook(data={'model':'gpt-5.6-sol','agent_type':'terra_executor'})))

    def test_astra_reasoning_tools_and_orchestration_remain_available(self):
        for tool in ('spawn_agent','send_input','wait','close_agent','update_plan','read_file'):
            self.assertEqual(self.hook(tool),{})

    def test_guarded_read_rewrite_runs_and_preserves_workspace(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        output=self.hook('Bash',data={'command':'cer-read '+json.dumps({'op':'read','path':'sentinel.txt'})})
        specific=output['hookSpecificOutput']
        self.assertEqual(specific['permissionDecision'],'allow')
        cmd=specific['updatedInput']['command']
        argv=['pwsh','-NoProfile','-NonInteractive','-Command',cmd] if os.name=='nt' else ['/bin/sh','-c',cmd]
        p=subprocess.run(argv,cwd=self.root,capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('before',p.stdout)
        self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)

    def test_virtual_protocol_does_not_fall_through_to_shell(self):
        bad=('cer-read {"op":"read","path":"sentinel.txt"}; touch hacked',
             'cer-read {"op":"read","command":"touch hacked"}',
             'cer-read {"op":"read","op":"write"}', 'cer-read invalid')
        for cmd in bad:self.assertTrue(self.denied(self.hook('Bash',data={'command':cmd})))
        self.assertFalse((self.root/'hacked').exists())

    def test_malformed_event_and_duplicate_keys_are_denied(self):
        for raw in ('[1]','not json','{}','{"model":"gpt-6-astra","model":"gpt-5.6-sol"}',
                    '{"hook_event_name":"PostToolUse"}'):
            self.assertTrue(self.denied(self.hook(raw=raw)))

    def test_reader_rejects_outside_workspace_and_arbitrary_operations(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        for req in ({'op':'write','path':'sentinel.txt'},{'op':'read','path':'../secret'},
                    {'op':'read','lines':100000}, {'op':'diff','command':'touch x'}):
            with self.assertRaises(ValueError):reader['run'](self.root,req)

    def test_reader_search_is_literal_not_executable(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        self.assertEqual(reader['run'](self.root,{'op':'search','path':'sentinel.txt','query':'before'}),'1: before')

    def test_readonly_git_diff_disables_external_diff(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        # Fixture writes must finish before the read-only snapshot. In validate #27
        # commit's auto-maintenance removed .git/objects/maintenance.lock mid-check.
        # Isolate setup; never hide .git changes, sleep, or skip the assertion.
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        git = ['git', '-c', 'maintenance.auto=false', '-c', 'gc.auto=0',
               '-c', 'gc.autoDetach=false', '-c', 'core.hooksPath=' + os.devnull,
               '-C', str(self.root)]
        subprocess.run([*git, 'init', '-q', '--template='], env=env, check=True)
        subprocess.run([*git, 'add', 'sentinel.txt'], env=env, check=True)
        subprocess.run([*git, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                        'commit', '--no-gpg-sign', '-qm', 'base'], env=env, check=True)
        # Actually configure an external diff that would leave an observable write.
        external = self.root / 'external_diff.py'
        external.write_text('from pathlib import Path\nPath(__file__).with_name("external-called").write_text("called")\n', encoding='utf-8')
        command = shlex.join([Path(sys.executable).as_posix(), external.as_posix()])
        subprocess.run([*git, 'config', 'diff.external', command], env=env, check=True)
        self.file.write_text('after', encoding='utf-8')
        subprocess.run([*git, 'diff', '--ext-diff', '--', 'sentinel.txt'], env=env, check=True)
        self.assertTrue((self.root / 'external-called').is_file(), 'external diff positive control did not run')
        (self.root / 'external-called').unlink()
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result=reader['run'](self.root,{'op':'diff','path':'sentinel.txt'})
        self.assertIn('-before',result);self.assertIn('+after',result)
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertFalse((self.root / 'external-called').exists())
        changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        self.assertEqual(changed, [], 'read-only operation changed paths (including .git)')

    def test_windows_command_quoting_is_literal(self):
        cmd=MODULE['command'](["C:/Program Files/Python/python.exe","-I","C:/O'Brien/reader.py"],True)
        self.assertIn("'C:/O''Brien/reader.py'",cmd)
        self.assertTrue(cmd.startswith('& '))

    def test_no_unsupported_continue_or_permission_ask(self):
        output=self.hook()
        self.assertEqual(set(output),{'hookSpecificOutput'})
        self.assertNotIn('continue',output)
        self.assertEqual(output['hookSpecificOutput']['permissionDecision'],'deny')


if __name__=='__main__':unittest.main()
