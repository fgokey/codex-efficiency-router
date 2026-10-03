"""Synthetic host execution tests: prove denied tools are not invoked by this harness.
Not a claim that an untested Codex version loads/trusts/enforces the hook.
"""
import json
import os
from pathlib import Path
import runpy
import shlex
import shutil
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
        for m in ('gpt-6.1-sol','gpt-6-sol','gpt-6-luna','gpt-5.6-terra','gpt-5.6-luna','gpt-5.6-sol'):
            self.assertEqual(self.hook(model=m),{})

    def test_unknown_identity_and_snapshot_deny(self):
        for m in (None,'','gpt-6-astra-2026-09-01','gpt-6.1-sol-lookalike','gpt-6-sol-2026-09-01','gpt-6-sol-untrusted',
                  'gpt-5.6-sol-2026-09-01','gpt-5.6-sol-untrusted','fake-sol',{'model':'gpt-6-sol'}):
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

    def test_reader_cli_pages_exact_text_with_bounded_utf8_output(self):
        expected=('汉🙂"\\' * 1800) + '\r\n' + ('A' * 6000) + '\nend'
        self.file.write_bytes(expected.encode('utf-8'))
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        index=subprocess.run([*cli,'index',*common],capture_output=True,timeout=10)
        self.assertEqual(index.returncode,0,index.stderr.decode('utf-8','replace'))
        cursor=json.loads(index.stdout)['cursor']
        pages=[]
        for _ in range(100):
            result=subprocess.run([*cli,'page',*common,'--cursor',cursor,'--max-bytes','4096'],
                                  capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8','replace'))
            self.assertLessEqual(len(result.stdout),4096)
            payload=json.loads(result.stdout)
            pages.append(payload['data'])
            cursor=payload['next_cursor']
            if cursor is None:
                break
        else:
            self.fail('reader cursor did not terminate')
        self.assertEqual(''.join(pages),expected)

    def test_reader_cli_range_cursor_and_changed_file(self):
        expected=('line\r\n' * 5999) + '目标🙂\\"\r\n' + 'tail\n'
        self.file.write_bytes(expected.encode('utf-8'))
        before=(self.file.read_bytes(),self.file.stat().st_mtime_ns)
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        index=subprocess.run([*cli,'index',*common,'--start','6000','--lines','2'],
                             capture_output=True,timeout=10)
        self.assertEqual(index.returncode,0,index.stderr)
        cursor=json.loads(index.stdout)['cursor'];parts=[]
        while cursor is not None:
            page=subprocess.run([*cli,'page',*common,'--cursor',cursor],capture_output=True,timeout=10)
            self.assertEqual(page.returncode,0,page.stderr)
            self.assertLessEqual(len(page.stdout)+len(page.stderr),4096)
            data=json.loads(page.stdout);parts.append(data['data']);cursor=data['next_cursor']
        self.assertEqual(''.join(parts),'目标🙂\\"\r\ntail\n')
        self.assertEqual((self.file.read_bytes(),self.file.stat().st_mtime_ns),before)
        self.file.write_bytes(expected.replace('目标', '换字').encode('utf-8'))
        stale=subprocess.run([*cli,'page',*common,'--cursor',json.loads(index.stdout)['cursor']],
                             capture_output=True,timeout=10)
        self.assertEqual(stale.returncode,2)
        self.assertIn(b'cursor',stale.stderr)

    def test_reader_cli_invalid_cursor_path_and_bounded_errors(self):
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        index=subprocess.run([*cli,'index',*common],capture_output=True,timeout=10)
        self.assertEqual(index.returncode,0,index.stderr)
        cursor=json.loads(index.stdout)['cursor']
        for args in ([*cli,'page',*common,'--cursor',cursor+'!'],
                     [*cli,'index','--root',str(self.root),'--path','../sentinel.txt'],
                     [*cli,'index','--root',str(self.root),'--path','*.txt'],
                     [*cli,'index',*common,'--start','3','--lines','1'],
                     [*cli,'index','--root',str(self.root),'--path','missing.txt']):
            result=subprocess.run(args,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,2,result.stdout)
            self.assertEqual(result.stdout,b'')
            self.assertLessEqual(len(result.stderr),4096)
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        identity={'path':'a'*2000,'size':1,'mtime_ns':1,'dev':1,'ino':1,'sha256':'0'*64}
        with self.assertRaisesRegex(ValueError,'cursor size'):
            reader['cursor_token'](identity,0,0,1)

    def test_reader_page_without_cursor_reads_small_and_empty_files_once(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        for raw in (b'', 'small 汉🙂\\\"\r\nlast\n'.encode('utf-8')):
            with self.subTest(raw=raw):
                self.file.write_bytes(raw)
                before=(self.file.read_bytes(),self.file.stat().st_mtime_ns)
                result=subprocess.run([*cli,'page',*common],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertLessEqual(len(result.stdout)+len(result.stderr)+1,4096)
                value=json.loads(result.stdout)
                self.assertEqual(value['op'],'page')
                self.assertEqual(value['data'],raw.decode('utf-8'))
                self.assertIsNone(value['next_cursor'])
                request={'op':'page','path':'sentinel.txt'}
                self.assertEqual(json.loads(reader['run'](self.root,request)),value)
                self.assertEqual((self.file.read_bytes(),self.file.stat().st_mtime_ns),before)

    def test_reader_page_without_cursor_continues_exactly_and_rejects_changed_file(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        expected=('汉🙂\\\"\r\n'*1500)+'tail'
        self.file.write_bytes(expected.encode('utf-8'))
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        result=subprocess.run([*cli,'page',*common],capture_output=True,timeout=10)
        pieces=[]
        first=None
        for _ in range(30):
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertLessEqual(len(result.stdout)+len(result.stderr)+1,4096)
            value=json.loads(result.stdout)
            pieces.append(value['data'])
            cursor=value['next_cursor']
            if first is None:
                first=cursor
            if cursor is None:
                break
            result=subprocess.run([*cli,'page',*common,'--cursor',cursor],
                                  capture_output=True,timeout=10)
        else:
            self.fail('first-page cursor did not terminate')
        self.assertGreaterEqual(len(pieces),2)
        self.assertEqual(''.join(pieces),expected)
        self.assertIsNotNone(first)
        index=json.loads(reader['run'](self.root,{'op':'index','path':'sentinel.txt'}))
        old=json.loads(reader['run'](self.root,{'op':'page','path':'sentinel.txt',
                                              'cursor':index['cursor']}))
        self.assertEqual(old['data'],pieces[0])
        before=self.file.stat()
        self.file.write_bytes(expected.replace('tail','fail').encode('utf-8'))
        os.utime(self.file,ns=(before.st_atime_ns,before.st_mtime_ns))
        stale=subprocess.run([*cli,'page',*common,'--cursor',first],
                             capture_output=True,timeout=10)
        self.assertEqual(stale.returncode,2)
        self.assertEqual(stale.stdout,b'')
        self.assertLessEqual(len(stale.stderr)+1,4096)

    def test_reader_page_first_read_rejects_explicit_bad_cursor_and_invalid_bounds(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        for cursor in ('',None,False,0,[]):
            with self.subTest(cursor=cursor),self.assertRaises(ValueError):
                reader['run'](self.root,{'op':'page','path':'sentinel.txt','cursor':cursor})
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        for extra in (['--cursor',''],['--cursor','malformed'],
                      ['--max-bytes','255'],['--max-bytes','4097'],['--start','1']):
            with self.subTest(extra=extra):
                result=subprocess.run([*cli,'page',*common,*extra],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,2)
                self.assertEqual(result.stdout,b'')
                self.assertLessEqual(len(result.stderr)+1,4096)
        for path in ('../sentinel.txt',str(self.file),'.','sentinel*.txt'):
            with self.subTest(path=path):
                result=subprocess.run([*cli,'page','--root',str(self.root),'--path',path],
                                      capture_output=True,timeout=10)
                self.assertEqual(result.returncode,2)
                self.assertEqual(result.stdout,b'')
                self.assertLessEqual(len(result.stderr)+1,4096)
        for raw in (b'\xff',b'x'*(16*1024*1024+1)):
            self.file.write_bytes(raw)
            result=subprocess.run([*cli,'page',*common],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,2)
            self.assertEqual(result.stdout,b'')
            self.assertLessEqual(len(result.stderr)+1,4096)

    def test_reader_cli_gbk_environment_and_exact_cap(self):
        self.file.write_text('汉🙂\\"'*1500,encoding='utf-8')
        cli=[sys.executable,'-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        env=dict(os.environ,PYTHONIOENCODING='ascii')
        index=subprocess.run([*cli,'index',*common],env=env,capture_output=True,timeout=10)
        self.assertEqual(index.returncode,0,index.stderr)
        cursor=json.loads(index.stdout)['cursor'];parts=[]
        while cursor is not None:
            result=subprocess.run([*cli,'page',*common,'--cursor',cursor,'--max-bytes','4096'],
                                  env=env,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertLessEqual(len(result.stdout)+len(result.stderr),4096)
            payload=json.loads(result.stdout);parts.append(payload['data']);cursor=payload['next_cursor']
        self.assertEqual(''.join(parts),self.file.read_text(encoding='utf-8'))

    def test_reader_cli_terminal_empty_invalid_utf8_and_file_limit(self):
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        self.file.write_bytes(b'')
        index=subprocess.run([*cli,'index',*common],capture_output=True,timeout=10)
        self.assertEqual(index.returncode,0,index.stderr)
        cursor=json.loads(index.stdout)['cursor']
        terminal=subprocess.run([*cli,'page',*common,'--cursor',cursor],capture_output=True,timeout=10)
        self.assertEqual(terminal.returncode,0,terminal.stderr)
        self.assertEqual(json.loads(terminal.stdout)['data'],'')
        self.assertIsNone(json.loads(terminal.stdout)['next_cursor'])
        self.file.write_bytes(b'\xff')
        invalid=subprocess.run([*cli,'index',*common],capture_output=True,timeout=10)
        self.assertEqual(invalid.returncode,2)
        self.assertLessEqual(len(invalid.stderr),4096)
        with self.file.open('wb') as stream:
            stream.truncate(16*1024*1024+1)
        large=subprocess.run([*cli,'index',*common],capture_output=True,timeout=10)
        self.assertEqual(large.returncode,2)
        self.assertIn(b'16 MiB',large.stderr)

    def test_reader_cli_cap_includes_envelope_and_line_ending(self):
        self.file.write_text('汉🙂'*1000,encoding='utf-8')
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        index=subprocess.run([*cli,'index',*common],capture_output=True,timeout=10)
        self.assertEqual(index.returncode,0,index.stderr)
        cursor=json.loads(index.stdout)['cursor']
        page=subprocess.run([*cli,'page',*common,'--cursor',cursor],capture_output=True,timeout=10)
        self.assertEqual(page.returncode,0,page.stderr)
        exact=len(page.stdout)+1  # Reader reserves the possible PowerShell CRLF.
        equal=subprocess.run([*cli,'page',*common,'--cursor',cursor,'--max-bytes',str(exact)],
                             capture_output=True,timeout=10)
        self.assertEqual(equal.returncode,0,equal.stderr)
        self.assertEqual(equal.stdout,page.stdout)
        shorter=subprocess.run([*cli,'page',*common,'--cursor',cursor,'--max-bytes',str(exact-1)],
                               capture_output=True,timeout=10)
        self.assertEqual(shorter.returncode,0,shorter.stderr)
        self.assertLessEqual(len(shorter.stdout)+1,exact-1)
        self.assertNotEqual(shorter.stdout,page.stdout)
        rejected=subprocess.run([*cli,'page',*common,'--cursor',cursor,'--max-bytes','4097'],
                                capture_output=True,timeout=10)
        self.assertEqual(rejected.returncode,2)
        self.assertLessEqual(len(rejected.stderr),4096)

    def test_reader_cli_excerpt_jumps_to_known_line_without_index(self):
        expected='目标🙂\\"\r\nnext\n'
        self.file.write_bytes((('skip\n'*4258)+expected).encode('utf-8'))
        before=(self.file.read_bytes(),self.file.stat().st_mtime_ns)
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        result=subprocess.run([*cli,'excerpt','--root',str(self.root),'--path','sentinel.txt',
                               '--start','4259','--lines','2'],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertLessEqual(len(result.stdout)+len(result.stderr),4096)
        page=json.loads(result.stdout)
        self.assertEqual(page['data'],expected)
        self.assertIsNone(page['next_cursor'])
        self.assertEqual((self.file.read_bytes(),self.file.stat().st_mtime_ns),before)

    @unittest.skipUnless(shutil.which('rg'),'rg unavailable')
    def test_reader_cli_locate_lists_only_bounded_candidates(self):
        (self.root/'src').mkdir()
        (self.root/'src/a.py').write_text('none\n-needle -needle 中🙂\n',encoding='utf-8')
        (self.root/'src/b.txt').write_text('-needle\n',encoding='utf-8')
        (self.root/'src/中文 空格.py').write_text('-needle\n',encoding='utf-8')
        (self.root/'src/.hidden').mkdir()
        (self.root/'src/.hidden/skip.py').write_text('-needle\n',encoding='utf-8')
        (self.root/'src/ignored').mkdir()
        (self.root/'src/ignored/skip.py').write_text('-needle\n',encoding='utf-8')
        (self.root/'.gitignore').write_text('src/ignored/\n',encoding='utf-8')
        subprocess.run(['git','init','-q',str(self.root)],check=True,capture_output=True)
        (self.root/'src/node_modules').mkdir()
        (self.root/'src/node_modules/x.py').write_text('-needle\n',encoding='utf-8')
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        base=[*cli,'locate','--root',str(self.root),'--path','src','--query','-needle']
        result=subprocess.run(base,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertLessEqual(len(result.stdout)+len(result.stderr),4096)
        value=json.loads(result.stdout)
        self.assertTrue(value['complete'])
        self.assertEqual({(item['path'],item['line']) for item in value['candidates']},
                         {('src/a.py',2),('src/b.txt',1),('src/中文 空格.py',1)})
        self.assertEqual(len(value['candidates']),3)
        self.assertEqual(value['scope'],'rg-default-ignore-max-16MiB')
        self.assertNotIn('中🙂',result.stdout.decode('utf-8'))
        chosen=subprocess.run([*base,'--glob','*.py'],capture_output=True,timeout=10)
        self.assertEqual(chosen.returncode,0,chosen.stderr)
        self.assertEqual({(item['path'],item['line']) for item in json.loads(chosen.stdout)['candidates']},
                         {('src/a.py',2),('src/中文 空格.py',1)})
        missing=subprocess.run([*cli,'locate','--root',str(self.root),'--path','src',
                                '--query','unseen'],capture_output=True,timeout=10)
        self.assertEqual(missing.returncode,0,missing.stderr)
        self.assertTrue(json.loads(missing.stdout)['complete'])
        self.assertEqual(json.loads(missing.stdout)['candidates'],[])

    def test_reader_cli_help_is_short_and_side_effect_free(self):
        before=(self.file.read_bytes(),self.file.stat().st_mtime_ns)
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        result=subprocess.run([*cli,'--help'],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertLessEqual(len(result.stdout)+len(result.stderr),4096)
        for part in (b'excerpt',b'--start',b'--lines',b'locate',b'--query',b'--glob',b'next_cursor'):
            self.assertIn(part,result.stdout)
        self.assertEqual((self.file.read_bytes(),self.file.stat().st_mtime_ns),before)

    def test_reader_cli_excerpt_pages_exact_range_and_rejects_stale_cursor(self):
        target=('中🙂\\\"'*500)+'\r\ntail\n'
        self.file.write_bytes(('head\n'+target+'outside\n').encode('utf-8'))
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        args=['--root',str(self.root),'--path','sentinel.txt']
        result=subprocess.run([*cli,'excerpt',*args,'--start','2','--lines','2'],
                              capture_output=True,timeout=10)
        pieces=[]
        first=None
        for _ in range(20):
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertLessEqual(len(result.stdout)+len(result.stderr),4096)
            page=json.loads(result.stdout)
            pieces.append(page['data'])
            cursor=page['next_cursor']
            if first is None:
                first=cursor
            if cursor is None:
                break
            result=subprocess.run([*cli,'page',*args,'--cursor',cursor],
                                  capture_output=True,timeout=10)
        else:
            self.fail('excerpt cursor did not terminate')
        self.assertEqual(''.join(pieces),target)
        self.assertIsNotNone(first)
        self.file.write_text('changed\n',encoding='utf-8')
        stale=subprocess.run([*cli,'page',*args,'--cursor',first],
                             capture_output=True,timeout=10)
        self.assertEqual(stale.returncode,2)
        self.assertLessEqual(len(stale.stdout)+len(stale.stderr),4096)
        for bad in (['excerpt',*args,'--start','2'],
                    ['excerpt',*args,'--start','2','--lines','201']):
            rejected=subprocess.run([*cli,*bad],capture_output=True,timeout=10)
            self.assertEqual(rejected.returncode,2)

    @unittest.skipUnless(shutil.which('rg'),'rg unavailable')
    def test_reader_cli_locate_partial_and_invalid_inputs(self):
        (self.root/'dense.txt').write_text('needle\n'*18000,encoding='utf-8')
        (self.root/'long.txt').write_text(('x'*200000)+'needle\n',encoding='utf-8')
        (self.root/'oversize.txt').write_bytes(b'x'*(16*1024*1024)+b'needle')
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        base=[*cli,'locate','--root',str(self.root),'--path','dense.txt','--query','needle']
        result=subprocess.run(base,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertLessEqual(len(result.stdout)+len(result.stderr),4096)
        page=json.loads(result.stdout)
        self.assertEqual(page['status'],'PARTIAL')
        self.assertFalse(page['complete'])
        self.assertIn('narrow',page['hint'])
        long_line=subprocess.run([*cli,'locate','--root',str(self.root),'--path','long.txt',
                                  '--query','needle'],capture_output=True,timeout=10)
        self.assertEqual(long_line.returncode,0,long_line.stderr)
        self.assertLessEqual(len(long_line.stdout)+len(long_line.stderr),4096)
        self.assertEqual(json.loads(long_line.stdout)['candidates'],[{'path':'long.txt','line':1}])
        oversize=subprocess.run([*cli,'locate','--root',str(self.root),'--path','oversize.txt',
                                 '--query','needle'],capture_output=True,timeout=10)
        self.assertEqual(oversize.returncode,0,oversize.stderr)
        self.assertEqual(json.loads(oversize.stdout)['candidates'],[])
        self.assertEqual(json.loads(oversize.stdout)['status'],'PARTIAL')
        self.assertFalse(json.loads(oversize.stdout)['complete'])
        self.assertIn('16MiB',json.loads(oversize.stdout)['scope'])
        for bad in ([*base[:-1],'needle\nanother'],[*base,'--glob','[']):
            rejected=subprocess.run(bad,capture_output=True,timeout=10)
            if '--glob' in bad:
                self.assertEqual(rejected.returncode,0)
                self.assertFalse(json.loads(rejected.stdout)['complete'])
            else:
                self.assertEqual(rejected.returncode,2)
            self.assertLessEqual(len(rejected.stdout)+len(rejected.stderr),4096)
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        original=reader['locate'].__globals__['bounded_process']
        try:
            reader['locate'].__globals__['bounded_process']=lambda *unused: (
                0,b'dense.txt\x001:needle\nbad.txt\x002:need',True)
            partial=json.loads(reader['run'](self.root,{'op':'locate','path':'.','query':'needle'}))
        finally:
            reader['locate'].__globals__['bounded_process']=original
        self.assertEqual(partial['candidates'],[{'path':'dense.txt','line':1}])
        self.assertFalse(partial['complete'])
        for output in ((0,b'bad\xff.txt\x001:needle\n',False),
                       (0,b'',True)):
            try:
                reader['locate'].__globals__['bounded_process']=lambda *unused: output
                broken=json.loads(reader['run'](self.root,{'op':'locate','path':'.','query':'needle'}))
                self.assertFalse(broken['complete'])
                self.assertEqual(broken['status'],'PARTIAL')
            finally:
                reader['locate'].__globals__['bounded_process']=original
        try:
            reader['locate'].__globals__['bounded_process']=lambda *unused: (_ for _ in ()).throw(ValueError('timeout'))
            timeout=json.loads(reader['run'](self.root,{'op':'locate','path':'.','query':'needle'}))
            self.assertFalse(timeout['complete'])
        finally:
            reader['locate'].__globals__['bounded_process']=original
        resolver=shutil.which
        try:
            shutil.which=lambda unused: None
            unavailable=json.loads(reader['run'](self.root,{'op':'locate','path':'.','query':'needle'}))
            self.assertFalse(unavailable['complete'])
            self.assertIn('unavailable',unavailable['hint'])
        finally:
            shutil.which=resolver
        with self.assertRaises(ValueError):
            reader['validate']({'op':'batch','requests':[{'op':'locate','path':'.','query':'needle'}]})
        with self.assertRaises(ValueError):
            reader['validate']({'op':'batch','requests':[{'op':'excerpt','path':'dense.txt','start':1,'lines':2}]})

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
