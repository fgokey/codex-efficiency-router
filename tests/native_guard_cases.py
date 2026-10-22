"""Synthetic host execution tests: prove denied tools are not invoked by this harness.
Not a claim that an untested Codex version loads/trusts/enforces the hook.
"""
import json
import hashlib
from contextlib import contextmanager
import base64
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tracemalloc
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
GUARD=ROOT/'hooks/astra_write_guard.py'
MODULE=runpy.run_path(str(GUARD))


class NativeDispatchTests(unittest.TestCase):
    def test_installed_schema3_full_policy_admits_sol61_high_and_rechecks_actual_effort(self):
        import contextlib, io, sys
        sys.path.insert(0,str(ROOT/'scripts'))
        import manage
        from package import resolve_targets, MANIFEST
        project=self.root/'installed'
        project.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            manage.install(ROOT,'project',project)
        self.policy,_,_=resolve_targets('project',project)
        manifest=json.loads((self.policy/MANIFEST).read_text())
        self.assertEqual((manifest['profile_schema'],manifest['host_mode']),(3,'full'))
        reader=runpy.run_path(str(self.policy/'scripts/readonly_reader.py'))
        execution={'effects':['write'],'permission':'workspace-write','role_read_only':False,'parent_released':True}
        request=self.request(message=reader['EXECUTION_PREFIX']+json.dumps(execution)+'\nRELEASE current unit. Update owned fixture')
        result=reader['assignment_preflight'](request,policy_sha256=reader['assignment_policy_sha256'](self.policy))
        self.assertEqual(result['status'],'VERIFIED',result)
        message=reader['assignment_message'](result,request['message'])
        self.assertEqual(self.hook(text=message),{})
        with self.connect() as db:db.execute("UPDATE threads SET reasoning_effort='medium' WHERE id='sol'")
        self.assertEqual(self.hook(text=message)['hookSpecificOutput']['permissionDecision'],'deny')

    def test_compat_policy_cannot_provide_full_native_admission(self):
        import contextlib, io, sys
        sys.path.insert(0,str(ROOT/'scripts'))
        import manage
        from package import resolve_targets
        message=self.text(self.request())
        project=self.root/'compat'
        project.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            manage.install(ROOT,'project',project,host_mode='compat')
        self.policy,_,_=resolve_targets('project',project)
        reader=runpy.run_path(str(self.policy/'scripts/readonly_reader.py'))
        with self.assertRaisesRegex(ValueError,'full admission'):
            reader['assignment_policy_sha256'](self.policy)
        self.assertEqual(self.hook(text=message)['hookSpecificOutput']['permissionDecision'],'deny')

    def setUp(self):
        import sqlite3
        self.sql = sqlite3
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.database = self.root / 'state_5.sqlite'
        self.policy = ROOT / 'skills/codex-efficiency-router'
        self.reader = runpy.run_path(str(ROOT / 'hooks/readonly_reader.py'))
        with self.connect() as db:
            db.execute('CREATE TABLE threads (id TEXT, model TEXT, reasoning_effort TEXT, source TEXT, '
                       'thread_source TEXT, agent_role TEXT, agent_path TEXT, archived INTEGER, rollout_path TEXT)')
        self.row('parent', 'gpt-6-astra', None, '/root')
        self.row('sol', 'gpt-6.1-sol', 'parent', '/root/sol')
        self.row('astra', 'gpt-6-astra', 'parent', '/root/astra')

    @contextmanager
    def connect(self):
        db = self.sql.connect(self.database)
        try:
            with db:
                yield db
        finally:
            db.close()

    def row(self, identifier, model, owner, path, effort='high', archived=0):
        source = json.dumps({'subagent': {'thread_spawn': {'parent_thread_id': owner}}}) if owner else 'desktop'
        with self.connect() as db:
            db.execute('INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)',
                       (identifier, model, effort, source, '', '', path, archived, ''))

    def request(self, recipient='sol', model='gpt-6.1-sol', message='Review the owned source unit', **changes):
        request = {'unit_id': 'source-review', 'purpose': 'new_unit', 'scope': 'owned source unit',
                   'message': message, 'recipient': {'id': recipient, 'model': model, 'effort': 'high',
                   'evidence_ref': 'caller claim is independently checked'},
                   'signals': dict.fromkeys(('spec_complete', 'authority_ready', 'environment_ready',
                                            'observability_ready'), True)}
        if model == 'gpt-6-astra':
            request['signals'].update(very_complex=True, reasoning_bound=True, cheap_check_available=False,
                                     sol61_unsuitable_reason='Conflicting causal evidence needs joint arbitration')
            request['complexity_reason'] = 'Several competing lifecycle explanations remain unresolved'
        request.update(changes)
        return request

    def test_execution_declaration_rejects_readonly_mutation_before_dispatch(self):
        request = self.request()
        work = request['message']
        def declared(value):
            request['message'] = self.reader['EXECUTION_PREFIX'] + json.dumps(value) + '\n' + work
        execution = {'effects': ['read'], 'permission': 'read-only',
                     'role_read_only': True, 'parent_released': False}
        declared(execution)
        self.assertEqual(self.reader['assignment_preflight'](request)['status'], 'VERIFIED')
        self.assertEqual(self.hook(text=self.text(request)), {})
        receipt = self.reader['assignment_preflight'](request)['receipt']
        self.assertEqual(set(receipt['admission']['signals']), {
            'spec_complete', 'authority_ready', 'environment_ready', 'observability_ready'})
        self.assertEqual(receipt['message_sha256'], hashlib.sha256(request['message'].encode()).hexdigest())
        self.denied(self.hook(text=self.text(request).replace('read-only', 'full-access')))
        for effects in (['write'], ['build'], ['test'], ['read', 'test']):
            with self.subTest(effects=effects):
                declared(dict(execution, effects=effects))
                result = self.reader['assignment_preflight'](request)
                self.assertEqual(result['status'], 'MISMATCH')
                self.assertNotIn('dispatch_arguments', result)
        writer = dict(execution, effects=['write', 'build', 'test'],
                      permission='full-access', role_read_only=False, parent_released=True)
        declared(writer)
        self.assertEqual(self.reader['assignment_preflight'](request)['status'], 'VERIFIED')
        admitted = self.text(request)
        self.assertEqual(self.hook(text=admitted), {})
        header, body = admitted.split('\n', 1)
        receipt = json.loads(header.removeprefix('CER assignment (caller evidence): '))
        receipt['admission']['signals']['execution'] = writer
        rejected = self.hook(text='CER assignment (caller evidence): ' + json.dumps(receipt) + '\n' + body)
        self.denied(rejected)
        self.assertIn('unsupported current admission signals', json.dumps(rejected))
        declared(dict(writer, parent_released=False))
        self.assertEqual(self.reader['assignment_preflight'](request)['status'], 'UNKNOWN')
        for bad in ({}, dict(execution, permission='UNKNOWN'), dict(execution, effects=[]),
                    dict(execution, role_read_only='false'), dict(execution, effects=['unknown'])):
            declared(bad)
            self.assertEqual(self.reader['assignment_preflight'](request)['status'], 'UNKNOWN')
        declared(execution)
        request['signals']['execution'] = execution
        self.assertEqual(self.reader['assignment_preflight'](request)['status'], 'MISMATCH')
        request['signals'].pop('execution')
        request['message'] = self.reader['EXECUTION_PREFIX'] + '{"effects":["read"],"effects":["write"]}\n' + work
        self.assertEqual(self.reader['assignment_preflight'](request)['status'], 'UNKNOWN')

    def test_packaged_javascript_adapter_runs_allowed_parent_path_with_lossless_pages(self):
        import shutil
        import subprocess
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable for offline functions.exec replay')
        snapshots = []
        for index in range(5):
            snapshots.append({'timedOut': True, 'wake': None, 'polls': [{
                'thread': {'id': 'worker', 'status': {'type': 'active'}},
                'latestTurn': {'id': 't1', 'status': 'inProgress', 'error': None},
                'cursor': f'cursor:{index}', 'revision': index, 'changed': True,
                'latestAssistantMessage': {'id': f'm{index}', 'phase': 'commentary', 'text': 'progress'},
                'latestToolMarker': {'id': f'exec:{index}', 'turnId': 't1', 'type': 'commandExecution',
                                     'name': 'commandExecution', 'status': 'completed'}}]})
        from copy import deepcopy
        snapshots[2]['polls'][0]['latestAssistantMessage'] = deepcopy(snapshots[1]['polls'][0]['latestAssistantMessage'])
        snapshots[2]['polls'][0]['latestToolMarker'] = deepcopy(snapshots[1]['polls'][0]['latestToolMarker'])
        snapshots[3]['polls'][0]['latestToolMarker']['name'] = 'wait_threads'
        failed = deepcopy(snapshots[-1]); failed['polls'][0]['latestToolMarker'].update(id='exec:failure-1', status='failed')
        repeated_failure = deepcopy(failed); repeated_failure['polls'][0]['cursor'] = 'failure:repeat'
        new_failure = deepcopy(failed); new_failure['polls'][0]['latestToolMarker']['id'] = 'exec:failure-2'
        recovered = deepcopy(new_failure); recovered['polls'][0]['latestToolMarker']['status'] = 'completed'
        new_turn = deepcopy(snapshots[-1]); new_turn['polls'][0]['latestTurn']['id'] = 't2'
        error = deepcopy(new_turn); error['polls'][0]['latestTurn']['error'] = {'message': '错误' * 4000}
        final = deepcopy(new_turn); final['polls'][0]['latestTurn']['status'] = 'completed'
        final['polls'][0]['latestAssistantMessage'] = {'id': 'final', 'phase': 'final_answer', 'text': '证据😀' * 4000}
        final['errors'] = [{'threadId': 'other', 'error': 'unavailable'}]
        native_error = {'toolError': 'native wait unavailable: ' + '错误' * 2000}
        schema_error = {'schemaError': {'unexpected': '保留原始结果'}}
        snapshots.extend((failed, repeated_failure, new_failure, recovered, new_turn, error, final, native_error, schema_error))
        script = r'''
const fs=require('fs'), input=JSON.parse(fs.readFileSync(0,'utf8'));
const run=new (Object.getPrototypeOf(async function(){}).constructor)('tools','targets','framingBytes','store','load','text','parentReady',input.code);
const pageRun=new (Object.getPrototypeOf(async function(){}).constructor)('framingBytes','store','load','text',input.page);
(async()=>{
const memory=new Map(), store=(k,v)=>memory.set(k,v), load=k=>memory.get(k), results=[];
let calls=0,maxBytes=0,totalBytes=0,targets=[{threadId:'worker'}],pageCount=0,pendingRejected=0;
for(const snapshot of input.snapshots){
 let pages=[],last;
 const text=p=>{const bytes=Buffer.byteLength(JSON.stringify(p))+2+64; if(bytes>4096)throw Error('outer overflow');maxBytes=Math.max(maxBytes,bytes);totalBytes+=bytes;pages.push(p);last=p;pageCount++;};
 const original=snapshot.toolError ? {isError:true,content:[{type:'text',text:snapshot.toolError}]} : {content:[{type:'text',text:JSON.stringify(snapshot.schemaError||snapshot)}]};
 const tools={mcp__codex_app__wait_threads:async args=>{calls++;if(args.timeoutMs!==50000)throw Error('wait bound');if(calls>1&&!args.targets[0].afterCursor)throw Error('cursor missing');return original;}};
 await run(tools,targets,64,store,load,text,true);
 const summary=last;let recovered=load('cerRaw');
 if(JSON.stringify(recovered)!==JSON.stringify(original))throw Error('original result lost');
 if(last.status==='PARTIAL'){
  try{await run(tools,targets,64,store,load,text,true);throw Error('pending overwritten');}catch(e){if(e.message!=='pending page')throw e;pendingRejected++;}
  pages=[];do{await pageRun(64,store,load,text);}while(last.next!==null);
  let raw='',offset=0;for(const page of pages){if(page.offset!==offset)throw Error('page gap');raw+=page.data;offset+=page.data.length;}
  recovered=JSON.parse(raw);if(JSON.stringify(recovered)!==JSON.stringify(original))throw Error('page evidence lost');
 }
 const decoded=recovered.isError?recovered:JSON.parse(recovered.content[0].text);
 results.push({summary,decoded});if(snapshot.polls)targets=[{threadId:'worker',afterCursor:snapshot.polls[0].cursor}];
}
let rejected=false;try{await run({},undefined,undefined,store,load,()=>{});}catch(e){rejected=e.message==='unknown framing';}
process.stdout.write(JSON.stringify({results,calls,maxBytes,totalBytes,pageCount,rejected,pendingRejected}));
})().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
'''
        result = subprocess.run([node, '-e', script], input=json.dumps({
            'code': self.reader['COORDINATION_JS'], 'page': self.reader['COORDINATION_PAGE_JS'], 'snapshots': snapshots}),
            capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed['calls'], len(snapshots))
        self.assertLessEqual(observed['maxBytes'], 4096)
        self.assertGreater(observed['pageCount'], len(snapshots))
        self.assertTrue(observed['rejected'])
        self.assertGreater(observed['pendingRejected'], 0)
        rows = [item['summary']['polls'][0] for item in observed['results'][:10]]
        self.assertEqual([row[8] for row in rows],
                         [True, False, False, False, False, True, False, True, True, True])
        self.assertTrue(all(row[4] == 'inProgress' for row in rows))
        self.assertEqual(rows[5][6], failed['polls'][0]['latestToolMarker'])
        self.assertEqual(rows[6][6], repeated_failure['polls'][0]['latestToolMarker'])
        self.assertFalse(rows[6][8])
        self.assertEqual(rows[7][6]['id'], 'exec:failure-2')
        self.assertIsNone(rows[8][6])  # Recovery is actionable, ordinary completed tools are not.
        self.assertIsNone(rows[2][6])
        recovered = [item['decoded'] for item in observed['results']]
        self.assertTrue(all(item['summary']['status'] == 'PARTIAL' for item in observed['results'][10:]))
        self.assertEqual(recovered[10]['polls'][0]['latestTurn']['error'], error['polls'][0]['latestTurn']['error'])
        self.assertEqual(recovered[11]['polls'][0]['latestAssistantMessage'], final['polls'][0]['latestAssistantMessage'])
        self.assertEqual(recovered[11]['errors'], final['errors'])
        self.assertEqual(recovered[11]['polls'][0]['latestTurn']['status'], 'completed')
        self.assertTrue(recovered[12]['isError'])
        self.assertEqual(recovered[12]['content'][0]['text'], native_error['toolError'])
        self.assertEqual(recovered[13], schema_error['schemaError'])
        self.assertEqual([row[9] for row in rows[:5]], [None] * 5)
        print('COORDINATION_OFFLINE ' + json.dumps({key: observed[key] for key in (
            'calls', 'maxBytes', 'totalBytes', 'pageCount')}, separators=(',', ':')))

    def test_coordination_readiness_merged_waits_adaptive_backoff_and_target_errors(self):
        import shutil
        import subprocess
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable for offline functions.exec replay')
        script = r'''
const input=JSON.parse(require('fs').readFileSync(0,'utf8')),Async=Object.getPrototypeOf(async function(){}).constructor;
(async()=>{
const memory=new Map(),store=(k,v)=>memory.set(k,v),load=k=>memory.get(k);let calls=[],last,snapshot,serial=0;
const check=(v,m)=>{if(!v)throw Error(m);};
const row=(id,turn='t1',status='inProgress')=>({thread:{id,status:{type:'active'}},cursor:'c'+(++serial),
 latestTurn:{id:turn,status,error:null},latestAssistantMessage:{id:'m'+serial,phase:status==='completed'?'final_answer':'commentary',text:'progress '+serial},
 latestToolMarker:{id:'exec'+serial,turnId:turn,status:'completed'}});
let targets=[{threadId:'a'},{threadId:'b'}],framing=64;
const tools={mcp__codex_app__wait_threads:async args=>{calls.push(args);return {content:[{type:'text',text:JSON.stringify(snapshot)}]};}};
const text=v=>{check(Buffer.byteLength(JSON.stringify(v))+2+framing<=4096,'framed overflow');last=v;};
const run=async(ready=true)=>new Async('tools','targets','framingBytes','store','load','text','parentReady',input.adaptive)(tools,targets,framing,store,load,text,ready);
await run(false);check(last.action==='WORK'&&calls.length===0,'available parent work waited');
for(let n=0;n<5;n++){
 snapshot={timedOut:true,wake:null,polls:[row('a'),row('b')]};await run();
 check(load('cerRaw').content[0].text===JSON.stringify(snapshot),'raw snapshot lost');
 if(n)check(last.unchanged===2&&last.polls.length===0,'commentary/tools caused duplicate detail');
}
check(JSON.stringify(calls.map(c=>c.timeoutMs))==='[50000,50000,50000,60000,60000]','quiet backoff');
check(calls.every(c=>c.targets.length===2),'separate child waits');
check(calls.slice(1).every(c=>c.targets.every(t=>t.afterCursor)),'automatic cursors missing');
targets[0].afterCursor='explicit-current';
snapshot={timedOut:false,wake:{type:'completed'},polls:[row('a','t2','completed'),row('b')]};await run();
check(calls.at(-1).targets[0].afterCursor==='explicit-current','explicit cursor replaced by stale cache');
check(last.polls[0][3]==='t2'&&last.polls[0][7]&&last.polls[0][9]===snapshot.polls[0].latestAssistantMessage.text,'new turn/final lost');
let before=calls.length;await run(false);check(calls.length===before,'unreviewed result waited');
// Caller reviews this exact completion and retires a; readiness is not native proof.
targets=[{threadId:'b'}];snapshot={timedOut:true,wake:null,polls:[row('b')]};await run();
check(calls.at(-1).timeoutMs===50000&&calls.at(-1).targets[0].threadId==='b','real change reset/retirement');
snapshot={timedOut:false,wake:null,polls:[],errors:[{threadId:'b',error:'not found'}]};await run();
check(last.errors[0].threadId==='b','target error missing');before=calls.length;await run(false);check(calls.length===before,'unreviewed target error waited');
// Exact error review removes b from the authoritative live list, without a ledger.
targets=[{threadId:'c'}];snapshot={timedOut:true,wake:null,polls:[row('c')]};await run();
check(calls.at(-1).targets.length===1&&calls.at(-1).targets[0].threadId==='c','inaccessible target retained');
// Eight maximum-width IDs and only 496B available: cold pages contain all data;
// there is no generated review map/token that could become unrecoverable.
framing=3600;targets=Array.from({length:8},(_,n)=>({threadId:String(n)+'x'.repeat(127)}));
snapshot={timedOut:false,wake:null,polls:[],errors:targets.map(t=>({threadId:t.threadId,error:'not found'}))};await run();
check(last.status==='PARTIAL'&&load('cerPending'),'overflow not recoverable');
let rejected=false;try{await run();}catch(e){rejected=String(e).includes('pending page');}check(rejected,'pending overwritten');
let raw='',offset=0;do{await new Async('framingBytes','store','load','text',input.page)(framing,store,load,text);
 check(last.offset===offset,'page gap');raw+=last.data;offset+=last.data.length;}while(last.next!==null);
check(JSON.parse(JSON.parse(raw).content[0].text).errors.length===8,'error evidence lost');
await run(false);check(last.action==='WORK','review gate unusable after pages');
process.stdout.write(JSON.stringify({calls:calls.length,timeouts:calls.map(c=>c.timeoutMs)}));
})().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
'''
        result = subprocess.run([node, '-e', script], input=json.dumps({
            'adaptive': self.reader['COORDINATION_ADAPTIVE_JS'], 'page': self.reader['COORDINATION_PAGE_JS']}),
            capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['calls'], 10)
    def test_paired_coordination_counts_generated_caller_and_complete_results(self):
        import shutil
        import subprocess
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable for offline functions.exec replay')
        ids = ['01a15ba8-f763-72b3-b218-526613d9cc07', '01a15bb8-9042-75e0-ae01-0afa8df6a19c']
        snapshots = []
        for index in range(6):
            polls = []
            for worker, identifier in enumerate(ids):
                final = index == 5
                failed = index in (3, 4) and worker == 0
                message_id = f'm-{worker}-{5 if final else 2 if index >= 2 else 0}'
                polls.append({'schemaVersion': 1, 'cursor': f'replay-{worker}:{index}',
                    'revision': 100 + index, 'changed': True,
                    'thread': {'id': identifier, 'hostId': 'local', 'status': {'type': 'active', 'activeFlags': []}},
                    'latestTurn': {'id': f'turn-{worker}', 'status': 'completed' if final else 'inProgress',
                        'error': None, 'startedAt': 1792547117, 'completedAt': 1792548000 if final else None, 'durationMs': None},
                    'latestAssistantMessageId': message_id,
                    'latestAssistantMessage': {'id': message_id, 'turnId': f'turn-{worker}',
                        'phase': 'final_answer' if final else 'commentary',
                        'text': ('source.py:42; actual caller and test applicability checked; expected output matched. ' * 3)
                            if final else ('定位到新证据，继续核对调用链。' if index >= 2 else '正在核查当前代码和已有验证。')},
                    'latestToolMarkerId': 'failure' if failed else f'exec-{worker}',
                    'latestToolMarker': {'id': 'failure' if failed else f'exec-{worker}', 'turnId': f'turn-{worker}',
                        'type': 'commandExecution', 'name': 'commandExecution', 'status': 'failed' if failed else 'completed'}})
            snapshots.append({'timedOut': index < 5, 'wake': None, 'polls': polls})
        # Frozen d0504cf transport, unchanged dense six-snapshot fixture.
        compact_baseline = '\nif(!Number.isInteger(framingBytes)||framingBytes<0||framingBytes>3900)throw Error("unknown framing");\nif(load("cerPending"))throw Error("pending page");\nconst r=await tools.mcp__codex_app__wait_threads({targets,timeoutMs:50000});store("cerRaw",r);store("cerPending",true);\nlet s;try{s=JSON.parse(r.content.find(c=>c.type==="text").text);let old=load("cerWait")||{};\ns.polls=s.polls.map(p=>{\nlet t=p.latestTurn,m=p.latestAssistantMessage,f=p.latestToolMarker;\nlet a=[p.thread.status,t.id,t.status,t.error,["failed","error"].includes(f?.status)?f:null,m?.phase==="final_answer"?m.id:null];\nlet k=JSON.stringify(a),changed=old[p.thread.id]!==k;old[p.thread.id]=k;\nreturn [p.thread.id,p.cursor,...a,changed,m?.text];\n});store("cerWait",old);}catch{s=null;}\nif(s&&encodeURIComponent(JSON.stringify(s)).replace(/%[0-9A-F]{2}/g,"x").length+2+framingBytes<=4096){store("cerPending",false);text(s);}\nelse text({status:"PARTIAL",detail:"COORDINATION_PAGE_JS"});\n'
        script = r'''
const input=JSON.parse(require('fs').readFileSync(0,'utf8')),Async=Object.getPrototypeOf(async function(){}).constructor;
(async()=>{let all=[];
for(const mode of ['prior','compact_baseline','current']){let memory=new Map(),calls=0,codeBytes=0,returnedBytes=0,requestBytes=0,emits=0,targets=input.ids.map(threadId=>({threadId})),steps=[];
for(const snapshot of input.snapshots){let chunks=[],last,before=codeBytes+returnedBytes;
const text=v=>{returnedBytes+=Buffer.byteLength(typeof v==='string'?v:JSON.stringify(v))+66;emits++;chunks.push(v);last=v;};
const original={content:[{type:'text',text:JSON.stringify(snapshot)}]};
const tools={mcp__codex_app__wait_threads:async()=>{calls++;return original;}},store=(k,v)=>memory.set(k,v),load=k=>memory.get(k);
let code=mode==='prior'?'let r=await tools.mcp__codex_app__wait_threads({targets:'+JSON.stringify(targets)+',timeoutMs:50000});for(let c of r.content||[])if(c.type==="text")text(c.text);\n':'const targets='+JSON.stringify(targets)+';const framingBytes=64;\n'+(mode==='current'?'const parentReady=true;\n'+input.hot:input.compact);
codeBytes+=Buffer.byteLength(code);requestBytes+=Buffer.byteLength(JSON.stringify({code}))+66;await new Async('tools','store','load','text',code)(tools,store,load,text);
let got=mode==='prior'?JSON.parse(last):last,raw=false;
if(mode!=='prior'&&last.status==='PARTIAL'){chunks=[];do{code='const framingBytes=64;\n'+input.page;codeBytes+=Buffer.byteLength(code);requestBytes+=Buffer.byteLength(JSON.stringify({code}))+66;await new Async('tools','store','load','text',code)(tools,store,load,text);}while(last.next!==null);got=JSON.parse(JSON.parse(chunks.map(p=>p.data).join('')).content[0].text);raw=true;}
if(mode!=='prior'&&JSON.stringify(load('cerRaw'))!==JSON.stringify(original))throw Error('original result lost');
if(got.polls.length!==snapshot.polls.length)throw Error('worker lost');
for(let j=0;j<got.polls.length;j++){let p=got.polls[j],q=snapshot.polls[j];if((mode!=='prior'&&!raw?p[1]:p.cursor)!==q.cursor)throw Error('cursor lost');
if(mode!=='prior'&&!raw){if(p[4]!==q.latestTurn.status||p[3]!==q.latestTurn.id||JSON.stringify(p[5])!==JSON.stringify(q.latestTurn.error))throw Error('state/error lost');
if((mode==='compact_baseline'||q.latestAssistantMessage.phase==='final_answer')&&p[9]!==q.latestAssistantMessage.text)throw Error('message/final evidence lost');
if(q.latestAssistantMessage.phase==='final_answer'&&p[7]!==q.latestAssistantMessage.id)throw Error('final identity lost');
if(q.latestToolMarker.status==='failed'&&JSON.stringify(p[6])!==JSON.stringify(q.latestToolMarker))throw Error('failed marker lost');}}
targets=snapshot.polls.map(p=>({threadId:p.thread.id,afterCursor:p.cursor}));steps.push(codeBytes+returnedBytes-before);}
all.push({mode,calls,codeBytes,returnedBytes,requestBytes,wireBytes:requestBytes+returnedBytes,emits,totalBytes:codeBytes+returnedBytes,waitingTotalBytes:steps.slice(0,-1).reduce((a,b)=>a+b,0),finalTotalBytes:steps.at(-1)});}
process.stdout.write(JSON.stringify(all));})().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
'''
        result = subprocess.run([node, '-e', script], input=json.dumps({'ids': ids, 'snapshots': snapshots,
            'hot': self.reader['COORDINATION_JS'], 'compact': compact_baseline,
            'page': self.reader['COORDINATION_PAGE_JS']}),
            capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        prior, baseline, current = json.loads(result.stdout)
        self.assertEqual(prior['calls'], 6)
        self.assertEqual(current['calls'], prior['calls'])
        self.assertLess(current['totalBytes'], prior['totalBytes'])
        self.assertLess(current['waitingTotalBytes'], prior['waitingTotalBytes'])
        self.assertGreater(current['codeBytes'], 0)
        self.assertGreater(current['returnedBytes'], 0)
        self.assertLessEqual(current['totalBytes'], baseline['totalBytes'])
        self.assertLessEqual(current['wireBytes'], baseline['wireBytes'])
        print('COORDINATION_PAIRED_BYTES ' + json.dumps([prior, baseline, current], separators=(',', ':')))

        # Frozen one-hour timeline, already merged in every mode. Commentary/tools
        # never wake native waits. Only error/completion events wake them. Details
        # use the same bounded fixture; the old automatic quiet tail is counted.
        timeline = r'''
const input=JSON.parse(require('fs').readFileSync(0,'utf8')),Async=Object.getPrototypeOf(async function(){}).constructor;
(async()=>{let results=[];
for(const scenario of ['quiet','mixed'])for(const mode of ['baseline','default','adaptive']){
 let memory=new Map(),store=(k,v)=>memory.set(k,v),load=k=>memory.get(k),now=0,calls=0,wakes=0,detailReads=0,tailReads=0,codeBytes=0,requestBytes=0,returnedBytes=0,nativeRequestBytes=0;
 let live=[...input.ids],targets=live.map(threadId=>({threadId})),last,quiet=0,tailCurrent=false,adaptive=false,seen={},reviews=[];
 const events=scenario==='quiet'?[{at:3600000,kind:'complete',ids:input.ids}]:[
  {at:600000,kind:'turn',ids:[input.ids[0]]},{at:900000,kind:'error',ids:[input.ids[1]]},{at:3600000,kind:'complete',ids:[input.ids[0]]}];
 const text=v=>{const encoded=typeof v==='string'?v:JSON.stringify(v);if(Buffer.byteLength(encoded)+66>4096)throw Error('fixture overflow');returnedBytes+=Buffer.byteLength(encoded)+66;last=v;};
 const invoke=async code=>{codeBytes+=Buffer.byteLength(code);requestBytes+=Buffer.byteLength(JSON.stringify({code}))+66;await new Async('tools','store','load','text',code)(tools,store,load,text);};
 let snapshot;
 const tools={mcp__codex_app__wait_threads:async args=>{
  calls++;nativeRequestBytes+=Buffer.byteLength(JSON.stringify(args));if(args.targets.length!==live.length)throw Error('unmerged wait');
  const end=now+args.timeoutMs,wake=events.find(e=>e.at>now&&e.at<=end&&e.kind!=='turn'&&e.ids.some(id=>live.includes(id)));
  now=wake?wake.at:end;if(wake)wakes++;
  const polls=[],errors=[];
  for(const id of live){const failed=events.find(e=>e.at<=now&&e.kind==='error'&&e.ids.includes(id));if(failed){errors.push({threadId:id,error:'not found'});continue;}
   const final=events.some(e=>e.at<=now&&e.kind==='complete'&&e.ids.includes(id));
   const turn=events.some(e=>e.at<=now&&e.kind==='turn'&&e.ids.includes(id))?'t2':'t1';
   polls.push({thread:{id,status:{type:'active'}},cursor:'c:'+id+':'+now,revision:Math.floor(now/30000),changed:true,
    latestTurn:{id:turn,status:final?'completed':'inProgress',error:null},
    latestAssistantMessage:{id:'m:'+now,phase:final?'final_answer':'commentary',text:final?'source.py:42; actual applicability verified.':'正在核查当前代码与测试适用性。'.repeat(3)},
    latestToolMarker:{id:'tool:'+Math.floor(now/30000),status:'completed'}});
  }
  snapshot={timedOut:!wake,wake:wake?{kind:wake.kind}:null,polls,errors};return {content:[{type:'text',text:JSON.stringify(snapshot)}]};
 },mcp__codex_app__read_thread:async args=>({content:[{type:'text',text:'source.py:42; caller, workload and expected result checked. '.repeat(8)}]})};
 while(live.length&&now<3600000){
  let seed='';if(mode==='adaptive'&&!adaptive&&quiet>=2){adaptive=true;seed='store("cerIdle",2);';}
  const body=mode==='baseline'?input.compact:adaptive?input.adaptive:input.hot;
  await invoke('const targets='+JSON.stringify(targets)+';const framingBytes=64;'+(mode==='baseline'?'':'const parentReady=true;')+seed+'\n'+body);
  if(last.status==='PARTIAL')throw Error('small fixture unexpectedly paginated');
  if(JSON.stringify(load('cerRaw').content[0].text)!==JSON.stringify(JSON.stringify(snapshot)))throw Error('raw lost');
  let changed=false,retired=[];
  for(const p of snapshot.polls){let key=JSON.stringify([p.latestTurn.id,p.latestTurn.status,p.latestTurn.error,p.latestAssistantMessage.phase==='final_answer'?p.latestAssistantMessage.id:null]);
   const prior=seen[p.thread.id];if(key!==prior){changed=true;if(prior||p.latestTurn.status==='completed'){
    reviews.push([p.thread.id,p.latestTurn.id,p.latestTurn.status]);detailReads++;
    await invoke('const r=await tools.mcp__codex_app__read_thread({threadId:'+JSON.stringify(p.thread.id)+',turnLimit:1,includeOutputs:true,maxOutputCharsPerItem:1200});text(r);');
   }}seen[p.thread.id]=key;if(p.latestTurn.status==='completed')retired.push(p.thread.id);
  }
  for(const error of snapshot.errors){changed=true;reviews.push([error.threadId,'error',error.error]);retired.push(error.threadId);}
  quiet=changed?0:quiet+1;if(changed)tailCurrent=false;
  if(mode==='baseline'&&quiet>=2&&!tailCurrent){tailReads++;detailReads++;tailCurrent=true;
   await invoke('const r=await tools.mcp__codex_app__read_thread({threadId:'+JSON.stringify(live[0])+',cursor:"saved-offset",turnLimit:1,includeOutputs:true,maxOutputCharsPerItem:1200});text(r);');}
  live=live.filter(id=>!retired.includes(id));targets=live.map(threadId=>({threadId,afterCursor:snapshot.polls.find(p=>p.thread.id===threadId)?.cursor}));
 }
 results.push({scenario,mode,calls,wakes,detailReads,tailReads,codeBytes,requestBytes,returnedBytes,nativeRequestBytes,totalBytes:codeBytes+returnedBytes,wireBytes:requestBytes+returnedBytes,reviews});
}
process.stdout.write(JSON.stringify(results));})().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
'''
        result = subprocess.run([node, '-e', timeline], input=json.dumps({'ids': ids,
            'compact': compact_baseline, 'hot': self.reader['COORDINATION_JS'],
            'adaptive': self.reader['COORDINATION_ADAPTIVE_JS']}),
            capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        for scenario in ('quiet', 'mixed'):
            baseline, default, adaptive = [row for row in observed if row['scenario'] == scenario]
            self.assertEqual(default['calls'], baseline['calls'])
            self.assertLess(adaptive['calls'], baseline['calls'])
            for row in (default, adaptive):
                self.assertEqual(row['reviews'], baseline['reviews'])
                self.assertEqual(row['wakes'], baseline['wakes'])
                self.assertEqual(row['tailReads'], 0)
                self.assertLess(row['wireBytes'], baseline['wireBytes'])
            self.assertLess(adaptive['wireBytes'], default['wireBytes'])
        print('COORDINATION_TIMELINE_BYTES ' + json.dumps(observed, separators=(',', ':')))

    def text(self, request):
        result = self.reader['assignment_preflight'](request)
        self.assertEqual(result['status'], 'VERIFIED', result)
        return self.reader['assignment_message'](result, request['message'])

    def hook(self, target='sol', text=None, name='send_input', data=None, session='parent'):
        event = {'hook_event_name': 'PreToolUse', 'tool_name': name, 'session_id': session,
                 'model': 'gpt-6-astra', 'tool_input': data if data is not None else {
                     'id': target, 'message': text if text is not None else self.text(self.request())}}
        return MODULE['decide'](event, dispatch_only=True, host_directory=self.root, policy_root=self.policy)

    def denied(self, result):
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny', result)

    def test_current_sol61_admission_and_parent_astra_tools(self):
        before = self.database.read_bytes()
        self.assertEqual(self.hook(), {})
        for name in ('Bash', 'exec_command', 'apply_patch', 'functions.exec', 'wait', 'interrupt_agent'):
            self.assertEqual(self.hook(name=name, data={'command': 'owned action'}), {})
        self.assertEqual(self.database.read_bytes(), before)

    def test_caller_projection_lag_does_not_replace_native_event_identity(self):
        with self.connect() as db:
            db.execute('UPDATE threads SET model=NULL, reasoning_effort=NULL WHERE id=?', ('parent',))
        self.assertEqual(self.hook(), {})
        self.denied(self.hook(text='continue'))
        for column in ('model', 'reasoning_effort'):
            with self.connect() as db:
                previous = db.execute('SELECT ' + column + ' FROM threads WHERE id=?', ('sol',)).fetchone()[0]
                db.execute('UPDATE threads SET ' + column + '=NULL WHERE id=?', ('sol',))
            self.denied(self.hook())
            with self.connect() as db:
                db.execute('UPDATE threads SET ' + column + '=? WHERE id=?', (previous, 'sol'))
        with self.connect() as db:
            db.execute('UPDATE threads SET archived=1 WHERE id=?', ('parent',))
        self.denied(self.hook())

    def test_current_astra_dual_reasons_for_every_message(self):
        request = self.request('astra', 'gpt-6-astra')
        self.assertEqual(self.hook('astra', self.text(request)), {})
        self.denied(self.hook('astra', 'continue'))
        for field in ('very_complex', 'sol61_unsuitable_reason'):
            bad = json.loads(json.dumps(request)); bad['signals'].pop(field)
            # Forge an envelope without asking the already strict Reader to admit it.
            text = self.text(request)
            header, body = text.split('\n', 1)
            receipt = json.loads(header[len(MODULE['ASSIGNMENT_PREFIX']):])
            receipt['admission']['signals'] = bad['signals']
            self.denied(self.hook('astra', MODULE['ASSIGNMENT_PREFIX'] + json.dumps(receipt) + '\n' + body))
        bad = self.text(request).replace(request['complexity_reason'], '', 1)
        self.denied(self.hook('astra', bad))

    def test_native_reader_preparation_returns_fresh_envelope_without_shell(self):
        request = self.request()
        result = self.hook(name='prepare_agent_task', data={'request': request})
        hook = result['hookSpecificOutput']
        self.assertNotIn('permissionDecision', hook)  # Native Codex rejects an explicit allow.
        prepared = json.loads(hook['additionalContext'])
        self.assertEqual(prepared['status'], 'VERIFIED')
        self.assertLessEqual(len(hook['additionalContext'].encode('utf-8')), 3500)
        text = self.reader['assignment_message'](prepared, request['message'])
        self.assertEqual(self.hook(text=text), {})
        self.denied(self.hook(text=text + ' extra work'))
        misplaced = dict(request, recipient=dict(request['recipient']))
        misplaced['evidence_ref'] = misplaced['recipient'].pop('evidence_ref')
        self.denied(self.hook(name='prepare_agent_task', data={'request': misplaced}))
        astra = self.request('astra', 'gpt-6-astra')
        prepared_astra = self.hook(name='prepare_agent_task', data={'request': astra})
        self.assertEqual(json.loads(prepared_astra['hookSpecificOutput']['additionalContext'])['status'], 'VERIFIED')
        no_complexity = dict(astra)
        no_complexity.pop('complexity_reason')
        self.denied(self.hook(name='prepare_agent_task', data={'request': no_complexity}))
        no_unsuitable = dict(astra, signals=dict(astra['signals']))
        no_unsuitable['signals'].pop('sol61_unsuitable_reason')
        self.denied(self.hook(name='prepare_agent_task', data={'request': no_unsuitable}))
        for bad in ({'request': dict(request, purpose='continue')},
                    {'request': dict(request, receipt={})},
                    {'request': dict(request, signals={})},
                    {'request': request, 'cmd': 'arbitrary command'},
                    {'request': 'not an object'}):
            self.denied(self.hook(name='prepare_agent_task', data=bad))

    def test_forged_model_old_receipt_controls_and_work_body(self):
        self.denied(self.hook('astra', self.text(self.request())))
        text = self.text(self.request('astra', 'gpt-6-astra'))
        header, body = text.split('\n', 1)
        receipt = json.loads(header[len(MODULE['ASSIGNMENT_PREFIX']):])
        receipt.pop('admission')
        self.denied(self.hook('astra', MODULE['ASSIGNMENT_PREFIX'] + json.dumps(receipt) + '\ncontinue'))
        self.denied(self.hook('astra', text + '\nAdditional unrelated work'))
        self.denied(self.hook(text=self.text(self.request()) + ' changed'))

    def test_target_policy_scope_and_actual_effort_are_bound(self):
        text = self.text(self.request())
        self.denied(self.hook('astra', text))
        header, body = text.split('\n', 1)
        original = json.loads(header[len(MODULE['ASSIGNMENT_PREFIX']):])
        for key in ('policy_sha256', 'scope_sha256', 'unit_id', 'message_sha256'):
            receipt = dict(original); receipt[key] = 'forged'
            self.denied(self.hook(text=MODULE['ASSIGNMENT_PREFIX'] + json.dumps(receipt) + '\n' + body))
        with self.connect() as db:
            db.execute("UPDATE threads SET reasoning_effort='medium' WHERE id='sol'")
        self.denied(self.hook(text=text))

    def test_missing_schema_database_caller_owner_and_path_ambiguity(self):
        self.denied(self.hook(session='unknown-parent'))
        self.row('foreign', 'gpt-6-astra', 'another-parent', '/root/astra')
        self.denied(self.hook('foreign', self.text(self.request('foreign', 'gpt-6-astra'))))
        self.assertEqual(self.hook('/root/sol'), {})
        self.row('duplicate', 'gpt-6.1-sol', 'parent', '/root/sol')
        self.denied(self.hook('/root/sol'))
        with self.connect() as db:
            db.execute('ALTER TABLE threads RENAME COLUMN agent_role TO unsupported_role')
        self.denied(self.hook())
        self.database.unlink()
        self.denied(self.hook())
        self.assertFalse(self.database.exists())

    def test_archived_unknown_model_and_malformed_source_are_denied(self):
        for column, value in (('archived', 1), ('model', 'gpt-6.1-sol-lookalike'),
                              ('source', '{}')):
            with self.connect() as db:
                previous = db.execute('SELECT ' + column + " FROM threads WHERE id='sol'").fetchone()[0]
                db.execute('UPDATE threads SET ' + column + "=? WHERE id='sol'", (value,))
            self.denied(self.hook())
            with self.connect() as db:
                db.execute('UPDATE threads SET ' + column + "=? WHERE id='sol'", (previous,))

    def test_task_aliases_and_application_identity_override(self):
        for name in ('send_input', 'collaboration.send_input', 'functions.send_input',
                     'followup_task', 'send_message', 'collaboration.followup_task', 'collaboration.send_message'):
            key = 'target' if name.endswith(('followup_task', 'send_message')) else 'id'
            self.assertEqual(self.hook(name=name, data={key: '/root/sol', 'message': self.text(self.request())}), {})
            self.denied(self.hook(name=name, data={key: 'astra', 'message': 'new hidden work',
                                                  'model': 'gpt-6.1-sol', 'db': str(self.database)}))
        name = 'mcp__codex_app__send_message_to_thread'
        data = {'threadId': 'sol', 'prompt': self.text(self.request())}
        self.assertEqual(self.hook(name=name, data=data), {})
        for override in ({'model': 'gpt-6-astra'}, {'thinking': 'ultra'}):
            self.denied(self.hook(name=name, data=dict(data, **override)))

    def test_observed_concatenated_followup_alias_checks_current_admission(self):
        name = 'collaborationfollowup_task'
        admitted = self.text(self.request('astra', 'gpt-6-astra'))
        for label, message in (('unadmitted', 'new engineering work'),
                               ('stale-body', admitted + '\nadditional work'), ('continue', 'continue')):
            with self.subTest(case=label):
                result = self.hook(name=name, data={'target': 'astra', 'message': message})
                self.assertEqual(result.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')
        self.assertIsNotNone(re.fullmatch(MODULE['DISPATCH_MATCHER'], name))
        self.assertEqual(MODULE['DISPATCH_ALIASES'][name], 'followup_task')
        self.assertEqual(self.hook(name=name, data={'target': 'sol', 'message': self.text(self.request())}), {})

    def test_observed_concatenated_spawn_alias_preserves_hold_admission(self):
        name = 'collaborationspawn_agent'
        admitted = self.text(self.request('unbound-spawn', 'gpt-6-astra', MODULE['HOLD_MESSAGE']))
        for label, message in (('unadmitted', MODULE['HOLD_MESSAGE']),
                               ('stale-body', admitted + '\nadditional work'), ('continue', 'continue')):
            with self.subTest(case=label):
                result = self.hook(name=name, data={'agent_type': 'astra_architect',
                                   'fork_context': False, 'message': message})
                self.assertEqual(result.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')
        self.assertIsNotNone(re.fullmatch(MODULE['DISPATCH_MATCHER'], name))
        self.assertEqual(MODULE['DISPATCH_ALIASES'][name], 'spawn_agent')
        valid = self.text(self.request('unbound-spawn', 'gpt-6.1-sol', MODULE['HOLD_MESSAGE']))
        self.assertEqual(self.hook(name=name, data={'agent_type': 'sol61_engineer',
                         'fork_context': False, 'message': valid}), {})

    def test_complete_finite_concatenated_dispatch_family_is_exactly_mapped(self):
        expected = {'collaborationfollowup_task': 'followup_task', 'collaborationspawn_agent': 'spawn_agent',
                    'collaborationsend_input': 'send_input', 'collaborationsend_message': 'send_message',
                    'collaborationresume_agent': 'resume_agent'}
        self.assertEqual(set(expected.values()), MODULE['DISPATCH_TOOLS'])
        for name, canonical in expected.items():
            with self.subTest(name=name):
                self.assertIsNotNone(re.fullmatch(MODULE['DISPATCH_MATCHER'], name))
                self.assertEqual(MODULE['DISPATCH_ALIASES'].get(name), canonical)

    def test_concatenated_send_family_requires_current_admission_for_work_and_controls(self):
        admitted = self.text(self.request('astra', 'gpt-6-astra'))
        for name, key in (('collaborationsend_input', 'id'), ('collaborationsend_message', 'target')):
            for label, message in (('unadmitted', 'new engineering work'),
                                   ('stale-body', admitted + '\nadditional work'), ('continue', 'continue')):
                with self.subTest(name=name, case=label):
                    result = self.hook(name=name, data={key: 'astra', 'message': message})
                    self.assertEqual(result.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')
            for message in ('Review the owned source unit', 'continue'):
                valid = self.text(self.request(message=message))
                self.assertEqual(self.hook(name=name, data={key: 'sol', 'message': valid}), {})

    def test_concatenated_resume_is_denied_for_astra_and_sol61(self):
        for target in ('astra', 'sol'):
            with self.subTest(target=target):
                result = self.hook(name='collaborationresume_agent', data={'id': target})
                self.assertEqual(result.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')

    def test_concatenated_dispatch_aliases_do_not_broaden_non_dispatch_matching(self):
        for name in ('collaborationwait_agent', 'collaborationinterrupt_agent', 'exec_command', 'apply_patch',
                     'collaborationsend_message_other', 'collaborationspawn_agent_extra'):
            self.assertIsNone(re.fullmatch(MODULE['DISPATCH_MATCHER'], name))
            self.assertEqual(self.hook(name=name, data={'command': 'owned parent action'}), {})

    def test_spawn_hold_requires_astra_current_admission_and_rejects_work(self):
        data = {'agent_type': 'sol61_engineer', 'fork_turns': 'none', 'message': MODULE['HOLD_MESSAGE']}
        self.assertEqual(self.hook(name='spawn_agent', data=data), {})
        self.denied(self.hook(name='spawn_agent', data=dict(data, message='Review code now')))
        astra = dict(data, agent_type='astra_architect')
        self.denied(self.hook(name='spawn_agent', data=astra))
        request = self.request('unbound-spawn', 'gpt-6-astra', MODULE['HOLD_MESSAGE'])
        astra['message'] = self.text(request)
        self.assertEqual(self.hook(name='collaboration.spawn_agent', data=astra), {})
        request['message'] += ' Also review the code'
        self.denied(self.hook(name='spawn_agent', data=dict(astra, message=self.text(request))))

    def test_observed_native_and_collaboration_no_context_shapes(self):
        base = {'agent_type': 'sol61_engineer', 'message': MODULE['HOLD_MESSAGE']}
        for name, flags in (('spawn_agent', {'fork_context': False}),
                            ('collaboration.spawn_agent', {'fork_turns': 'none'}),
                            ('spawn_agent', {'fork_context': False, 'fork_turns': 'none'})):
            self.assertEqual(self.hook(name=name, data=dict(base, **flags)), {})
        for flags in ({'fork_context': True}, {'fork_context': 'false'}, {'fork_turns': 'all'},
                      {'fork_context': False, 'fork_turns': 'all'}, {'fork_turns': None}, {}):
            self.denied(self.hook(name='spawn_agent', data=dict(base, **flags)))

    def test_spawn_denial_provides_executable_help_with_exact_installed_protocol(self):
        result = self.hook(name='spawn_agent', data={'agent_type': 'astra_architect',
                           'fork_turns': 'none', 'message': '只读核查身份，等待释放'})
        self.denied(result)
        reason = result['hookSpecificOutput']['permissionDecisionReason']
        self.assertIn('assignment', reason)
        self.assertIn('--help', reason)
        command = reason.split(' Help: ', 1)[1]
        argv = ['pwsh', '-NoProfile', '-NonInteractive', '-Command', command] if os.name == 'nt' else ['/bin/sh', '-c', command]
        proc = subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for required in (MODULE['HOLD_MESSAGE'], 'purpose=new_unit', 'unbound-spawn',
                         'complexity_reason', 'sol61_unsuitable_reason', 'prefix + that exact HOLD'):
            self.assertIn(required, proc.stdout)

    def test_resume_agent_aliases_and_extra_task_carriers_are_denied(self):
        for name in ('resume_agent', 'collaboration.resume_agent', 'functions.resume_agent'):
            self.denied(self.hook(name=name, data={'id': 'astra'}))
        for name in ('Agent', 'collaboration.Agent', 'functions.Agent'):
            self.denied(self.hook(name=name, data={'prompt': 'hidden new work', 'subagent_type': 'general'}))
            self.assertEqual(self.hook(name=name, data={'agent_type': 'sol61_engineer',
                'fork_turns': 'none', 'message': MODULE['HOLD_MESSAGE']}), {})
        for carrier in ('items', 'input_items', 'prompt', 'input'):
            self.denied(self.hook(data={'id': 'sol', 'message': self.text(self.request()), carrier: 'extra work'}))
        header, body = self.text(self.request()).split('\n', 1)
        for location in ('envelope', 'admission', 'signals'):
            receipt = json.loads(header[len(MODULE['ASSIGNMENT_PREFIX']):])
            destination = receipt if location == 'envelope' else receipt['admission']
            if location == 'signals': destination = destination['signals']
            destination['hidden_work'] = 'another task'
            self.denied(self.hook(text=MODULE['ASSIGNMENT_PREFIX'] + json.dumps(receipt) + '\n' + body))

    def test_caught_processing_failures_and_cli_argument_errors_return_official_deny(self):
        with mock.patch.dict(MODULE['decide_dispatch'].__globals__, host_recipient=mock.Mock(side_effect=RuntimeError('injected'))):
            self.denied(self.hook())
        for args, raw in ((['--dispatch-only'], '{bad'),
                          (['--dispatch-only', '--policy-root'], '{}'),
                          (['--dispatch-only'], json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': 'send_input'}))):
            proc = subprocess.run([sys.executable, '-I', '-B', str(GUARD), *args], input=raw,
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.denied(json.loads(proc.stdout))


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

    def test_structured_batch_small_files_free_budget_without_reordering_results(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        contents={'large.txt':'L'*1200,'small.txt':'S'*40}
        for name,body in contents.items(): (self.root/name).write_text(body,encoding='utf-8')
        for names in (list(contents),list(reversed(contents))):
            request={'op':'batch','requests':[{'op':'page','path':name} for name in names],
                     'max_bytes':2400,'framing_bytes':300}
            raw=reader['run'](self.root,request); result=json.loads(raw)
            self.assertLessEqual(len(raw.encode())+2+300,2400)
            self.assertEqual(result['status'],'COMPLETE')
            self.assertEqual([row['data'] for row in result['results']],[contents[name] for name in names])
            self.assertTrue(all(row['next_cursor'] is None for row in result['results']))
        def calls_to_finish():
            request={'op':'batch','requests':[{'op':'page','path':name} for name in contents],
                     'max_bytes':2400,'framing_bytes':300}
            for calls in range(1,10):
                result=json.loads(reader['run'](self.root,request))
                pending=[{**item,'cursor':page['next_cursor']}
                         for item,page in zip(request['requests'],result['results']) if page['next_cursor']]
                if not pending: return calls
                request={**request,'requests':pending}
            self.fail('continuations did not finish')
        natural_sorted=sorted
        # Replay the previous capture order with the same current bounds/cursors.
        with mock.patch.dict(reader['run'].__globals__,sorted=lambda values,**kw:
                             list(values) if kw else natural_sorted(values)):
            previous=calls_to_finish()
        self.assertEqual((previous,calls_to_finish()),(2,1))

    def test_native_reads_keep_executor_and_astra_unknown_policy_contrast(self):
        # Guard pass-through is not admission, role permission or a new tool grant.
        for model in ('gpt-6.1-sol','gpt-6-sol','gpt-6-luna'):
            self.assertEqual(self.hook(tool='Bash',model=model,data={'command':'rg --files'}),{})
        for model in ('gpt-6-astra','UNKNOWN','gpt-6.1-sol-unverified'):
            result=self.hook(tool='Bash',model=model,data={'command':'rg --files'})
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'deny')

    def test_small_first_stat_error_retains_other_evidence_and_original_index(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        (self.root/'vanished.txt').write_text('gone',encoding='utf-8')
        request={'op':'batch','requests':[{'op':'page','path':'vanished.txt'},
                 {'op':'page','path':'sentinel.txt'}],'max_bytes':3000,'framing_bytes':400}
        original_preflight=reader['preflight']; original_stat=Path.stat; ready=[False]
        def preflight(root,request):
            checked=original_preflight(root,request); ready[0]=True
            return checked
        def stat(path,*args,**kwargs):
            if ready[0] and path.name=='vanished.txt': raise FileNotFoundError('vanished after preflight')
            return original_stat(path,*args,**kwargs)
        with mock.patch.dict(reader['run'].__globals__,preflight=preflight),mock.patch.object(Path,'stat',stat):
            result=json.loads(reader['run'](self.root,request))
        self.assertEqual(result['status'],'PARTIAL')
        self.assertEqual(result['results'][0]['request_index'],1)
        self.assertEqual(result['results'][0]['status'],'ERROR')
        self.assertEqual(result['results'][1]['data'],'before')

    def test_structured_batch_default_caps_share_budget_without_losing_evidence(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        contents={'sentinel.txt':'A界\\"\r\n'*500,'second.txt':'B🙂\\"\r\n'*500}
        for name,body in contents.items(): (self.root/name).write_text(body,encoding='utf-8',newline='')
        requests=[{'op':'page','path':name} for name in contents]
        request={'op':'batch','requests':requests,'max_bytes':3072,'framing_bytes':400}
        p=subprocess.run([sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py'),'batch',
                          '--root',str(self.root),'--requests',json.dumps(requests),
                          '--max-bytes','3072','--framing-bytes','400'],capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        parts={name:[] for name in contents}; result=json.loads(p.stdout)
        for attempt in range(30):
            self.assertLessEqual(len(json.dumps(result,ensure_ascii=False,separators=(',',':')).encode())+2+400,3072)
            self.assertEqual(len(result['results']),len(request['requests']))
            pending=[]
            for item,page in zip(request['requests'],result['results']):
                self.assertTrue(page['data']); parts[item['path']].append(page['data'])
                if page['next_cursor']: pending.append({**item,'cursor':page['next_cursor']})
            self.assertEqual(result['status'],'PARTIAL' if pending else 'COMPLETE')
            if not pending: break
            request={**request,'requests':pending}; result=json.loads(reader['run'](self.root,request))
        else: self.fail('batch continuations failed to finish')
        self.assertEqual({name:''.join(body) for name,body in parts.items()},contents)

    def test_structured_batch_item_error_retains_other_evidence_and_recovers(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        self.file.write_bytes(b'\xff'); (self.root/'second.txt').write_text('kept',encoding='utf-8')
        request={'op':'batch','requests':[{'op':'page','path':name} for name in ('sentinel.txt','second.txt')],
                 'max_bytes':3072,'framing_bytes':400}
        result=json.loads(reader['run'](self.root,request))
        self.assertEqual(result['status'],'PARTIAL'); self.assertEqual(len(result['results']),2)
        bad,good=result['results']; self.assertEqual(bad['status'],'ERROR')
        self.assertEqual(bad['path'],'sentinel.txt'); self.assertNotIn('data',bad)
        self.assertIn('decode',bad['error']); self.assertEqual(good['data'],'kept')
        self.file.write_text('recovered',encoding='utf-8')
        recovered=json.loads(reader['run'](self.root,{**request,'requests':request['requests'][:1]}))
        self.assertEqual(recovered['status'],'COMPLETE')
        self.assertEqual(recovered['results'][0]['data'],'recovered')

    def test_structured_batch_long_safe_error_keeps_earlier_success(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        long_path=self.root/('safe_'+'x'*160)/'target.txt'
        long_path.parent.mkdir(); long_path.write_text('content'*1000,encoding='utf-8')
        self.assertGreater(len(str(long_path).encode()),160)
        request={'op':'batch','requests':[{'op':'page','path':'sentinel.txt','max_bytes':1024},
                                          {'op':'read','path':str(long_path),'max_bytes':256}],
                 'max_bytes':3072,'framing_bytes':400}
        raw=reader['run'](self.root,request); result=json.loads(raw)
        self.assertLessEqual(len(raw.encode())+2+400,3072)
        self.assertEqual(result['status'],'PARTIAL'); self.assertEqual(len(result['results']),2)
        self.assertEqual(result['results'][0]['data'],'before')
        error=result['results'][1]; self.assertEqual(error['status'],'ERROR')
        self.assertEqual(error['request_index'],2); self.assertTrue(error['path_omitted'])
        self.assertNotIn('path',error); self.assertNotIn('data',error)
        self.assertTrue(error['error'])

    def test_structured_batch_stale_cursor_returns_no_stale_data(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        self.file.write_text('original'*1000,encoding='utf-8')
        first=json.loads(reader['run'](self.root,{'op':'page','path':'sentinel.txt','max_bytes':1024}))
        self.file.write_text('changed'*1000,encoding='utf-8')
        (self.root/'second.txt').write_text('current',encoding='utf-8')
        request={'op':'batch','requests':[{'op':'page','path':'sentinel.txt','cursor':first['next_cursor']},
                                          {'op':'page','path':'second.txt'}],
                 'max_bytes':3072,'framing_bytes':400}
        result=json.loads(reader['run'](self.root,request))
        self.assertEqual(result['status'],'PARTIAL'); self.assertEqual(len(result['results']),2)
        bad,good=result['results']; self.assertEqual(bad['status'],'ERROR')
        self.assertNotIn('data',bad); self.assertRegex(bad['error'],'changed|stale')
        self.assertEqual(good['data'],'current')

    def test_structured_batch_large_os_error_is_explicitly_bounded(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        (self.root/'second.txt').write_text('content',encoding='utf-8')
        original=reader['run'].__globals__['one']; message='界\\"'*10000
        def failing(root,item,path,remaining):
            if path.name=='second.txt': raise OSError(message)
            return original(root,item,path,remaining)
        request={'op':'batch','requests':[{'op':'page','path':'sentinel.txt','max_bytes':1024},
                                          {'op':'page','path':'second.txt','max_bytes':256}],
                 'max_bytes':3072,'framing_bytes':400}
        with mock.patch.dict(reader['run'].__globals__,one=failing): raw=reader['run'](self.root,request)
        result=json.loads(raw); self.assertEqual(result['status'],'PARTIAL')
        self.assertLessEqual(len(raw.encode())+2+400,3072)
        self.assertEqual(result['results'][0]['data'],'before')
        error=result['results'][1]; self.assertEqual(error['request_index'],2)
        self.assertTrue(error['path_omitted']); self.assertTrue(error['error_truncated'])
        self.assertTrue(error['error']); self.assertTrue(message.startswith(error['error']))
        self.assertNotIn('data',error)

    def test_structured_batch_partial_locate_is_explicit_and_keeps_other_results(self):
        if not shutil.which('rg'): self.skipTest('rg unavailable')
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        self.file.write_text('needle\n'*300,encoding='utf-8')
        (self.root/'second.txt').write_text('kept',encoding='utf-8')
        request={'op':'batch','requests':[{'op':'locate','path':'sentinel.txt','query':'needle'},
                                          {'op':'page','path':'second.txt'}],
                 'max_bytes':3072,'framing_bytes':400}
        result=json.loads(reader['run'](self.root,request))
        self.assertEqual(result['status'],'PARTIAL'); self.assertEqual(len(result['results']),2)
        found,good=result['results']; self.assertFalse(found['complete'])
        self.assertEqual(found['status'],'PARTIAL'); self.assertTrue(found['candidates'])
        self.assertIn('narrow',found['hint']); self.assertEqual(good['data'],'kept')

    def test_structured_batch_insufficient_budget_fails_before_capture(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        for index in range(16): (self.root/str(index)).write_text('small',encoding='utf-8')
        request={'op':'batch','requests':[{'op':'page','path':str(index)} for index in range(16)],
                 'max_bytes':512,'framing_bytes':128}
        with mock.patch.dict(reader['run'].__globals__,one=mock.Mock(side_effect=AssertionError('capture before budget preflight'))):
            with self.assertRaisesRegex(ValueError,'budget'): reader['run'](self.root,request)

    def test_reader_batch_stdin_preserves_unicode_and_rejects_invalid_input(self):
        name='读取 界.txt'
        (self.root/name).write_text('界 "quoted"',encoding='utf-8')
        args=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py'),'batch',
              '--root',str(self.root),'--requests','-','--max-bytes','3072','--framing-bytes','256']
        request=json.dumps([{'op':'page','path':name}],ensure_ascii=False).encode('utf-8')
        p=subprocess.run(args,input=request,capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['results'][0]['data'],'界 "quoted"')
        self.assertLessEqual(len(p.stdout)+1+256,3072)
        for bad in (b' '*16385,b'[{"op":"page","op":"read","path":"sentinel.txt"}]',b'\xff'):
            with self.subTest(bad=bad[:40]):
                p=subprocess.run(args,input=bad,capture_output=True,timeout=10)
                self.assertNotEqual(p.returncode,0)
                self.assertEqual(p.stdout,b'')
                self.assertIn(b'CER read failed:',p.stderr)

    def test_reader_batch_powershell_stdin_avoids_native_json_quoting(self):
        shell=shutil.which('pwsh') or shutil.which('powershell')
        if not shell: self.skipTest('PowerShell unavailable')
        name='读取 界.txt'
        (self.root/name).write_text('界 "quoted"',encoding='utf-8')
        env=dict(os.environ,CER_READER_REQUEST=json.dumps([{'op':'page','path':name}],ensure_ascii=False),
                 CER_READER=str(ROOT/'hooks/readonly_reader.py'),CER_PYTHON=sys.executable,CER_ROOT=str(self.root))
        command='$OutputEncoding = New-Object System.Text.UTF8Encoding($false)\n$env:CER_READER_REQUEST | & $env:CER_PYTHON -I -B $env:CER_READER batch --root $env:CER_ROOT --requests - --max-bytes 3072 --framing-bytes 256\nexit $LASTEXITCODE'
        p=subprocess.run([shell,'-NoProfile','-NonInteractive','-Command',command],env=env,
                         capture_output=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['results'][0]['data'],'界 "quoted"')
        self.assertEqual(json.loads(p.stdout)['status'],'COMPLETE')
        self.assertLessEqual(len(p.stdout)+1+256,3072)

    def test_reader_encoded_requests_accept_optional_padding_and_reject_bad_encoding(self):
        args=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py'),str(self.root)]
        for length in range(3):
            request={'op':'search','path':'sentinel.txt','query':'x'*(length+1)}
            # A literal search permits all three Base64 padding lengths.
            encoded=base64.urlsafe_b64encode(json.dumps(request).encode()).decode()
            padded=subprocess.run(args+[encoded],capture_output=True,timeout=10)
            plain=subprocess.run(args+[encoded.rstrip('=')],capture_output=True,timeout=10)
            self.assertEqual(padded.returncode,0,padded.stderr)
            self.assertEqual((plain.returncode,plain.stdout),(padded.returncode,padded.stdout),plain.stderr)
        for bad in ('a','!!!!','eyJvcCI6'):
            p=subprocess.run(args+[bad],capture_output=True,timeout=10)
            self.assertNotEqual(p.returncode,0)
            self.assertEqual(p.stdout,b'')

    def test_structured_batch_cli_counts_complete_json_and_framing(self):
        self.file.write_text('界\\"\r\n'*30,encoding='utf-8',newline='')
        (self.root/'other.json').write_text('{"nested":{"x":"界"}}',encoding='utf-8')
        reader=ROOT/'hooks/readonly_reader.py'
        requests=[{'op':'excerpt','path':'sentinel.txt','start':1,'lines':2,'max_bytes':1024},
                  {'op':'json','path':'other.json','pointer':'/nested','max_bytes':1024}]
        args=[sys.executable,'-I','-B',str(reader),'batch','--root',str(self.root),
              '--requests',json.dumps(requests),'--max-bytes','3072','--framing-bytes','400']
        p=subprocess.run(args,capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertLessEqual(len(p.stdout)+1+400,3072)
        result=json.loads(p.stdout)
        self.assertEqual(result['results'][0]['data'],'界\\"\r\n'*2)
        self.assertEqual(json.loads(result['results'][1]['data']),{'x':'界'})
        self.assertEqual(result['status'],'COMPLETE')
        structured={'op':'batch','requests':requests,'max_bytes':3072,'framing_bytes':400}
        encoded=base64.urlsafe_b64encode(json.dumps(structured).encode()).decode()
        p=subprocess.run([sys.executable,'-I','-B',str(reader),str(self.root),encoded],capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),result)
        # Legacy encoded batch is still text and retains its old restrictions.
        old=base64.urlsafe_b64encode(json.dumps({'op':'batch','requests':[{'op':'read','path':'sentinel.txt','lines':1}]}).encode()).decode()
        p=subprocess.run([sys.executable,'-I','-B',str(reader),str(self.root),old],capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(p.stdout.startswith(b'[1:read]\n'))
        p=subprocess.run([sys.executable,'-I','-B',str(reader),'batch','--help'],capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr); self.assertIn(b'--requests JSON_ARRAY',p.stdout)
        self.assertLessEqual(len(p.stdout)+1,4096)

    def test_structured_batch_retains_independent_page_continuations(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        contents={'sentinel.txt':'A界\\"\n'*1000,'second.txt':'B界\\"\n'*1000}
        for name,body in contents.items(): (self.root/name).write_text(body,encoding='utf-8',newline='')
        requests=[{'op':'page','path':name,'max_bytes':1024} for name in contents]
        request={'op':'batch','requests':requests,'max_bytes':3072,'framing_bytes':400}
        first=json.loads(reader['run'](self.root,request))['results']
        for item,page in zip(requests,first):
            self.assertIsInstance(page['next_cursor'],str)
            item['cursor']=page['next_cursor']
        second=json.loads(reader['run'](self.root,request))['results']
        for name,before,after in zip(contents,first,second):
            offset=len(before['data'])
            self.assertEqual(after['data'],contents[name][offset:offset+len(after['data'])])
            self.assertNotEqual(after['next_cursor'],before['next_cursor'])
        self.file.write_text('changed',encoding='utf-8')
        changed=json.loads(reader['run'](self.root,request))
        self.assertEqual(changed['status'],'PARTIAL')
        self.assertEqual(changed['results'][0]['status'],'ERROR')
        self.assertRegex(changed['results'][0]['error'],'changed|stale')
        self.assertNotIn('data',changed['results'][0])
        self.assertEqual(changed['results'][1],second[1])

    def test_structured_batch_preflights_and_emits_one_complete_envelope(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        request={'op':'batch','requests':[{'op':'page','path':'sentinel.txt','max_bytes':1024}],
                 'max_bytes':3072,'framing_bytes':400}
        for bad in ({'op':'page','path':'../outside'}, {'op':'excerpt','path':'sentinel.txt','start':1,'lines':201}):
            with mock.patch.dict(reader['run'].__globals__,one=mock.Mock(side_effect=AssertionError('read before preflight'))):
                with self.assertRaises(ValueError): reader['run'](self.root,{**request,'requests':[*request['requests'],bad]})
        for changes in ({'framing_bytes':None},{'framing_bytes':True},{'framing_bytes':3000},
                        {'requests':request['requests']*2},{'requests':[request]}):
            with self.assertRaises(ValueError): reader['run'](self.root,{**request,**changes})
        args=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py'),'batch','--root',str(self.root),
              '--requests',json.dumps(request['requests']),'--max-bytes','1024','--framing-bytes','800']
        p=subprocess.run(args,capture_output=True,timeout=10)
        self.assertNotEqual(p.returncode,0); self.assertEqual(p.stdout,b'')
        self.file.write_text('界\\"\n'*1000,encoding='utf-8')
        (self.root/'second.txt').write_text('界\\"\n'*1000,encoding='utf-8')
        requests=[{'op':'page','path':name,'max_bytes':1024} for name in ('sentinel.txt','second.txt')]
        args=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py'),'batch','--root',str(self.root),
              '--requests',json.dumps(requests),'--max-bytes','2048','--framing-bytes','256']
        p=subprocess.run(args,capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertLessEqual(len(p.stdout)+1+256,2048)
        result=json.loads(p.stdout)
        self.assertEqual(result['status'],'PARTIAL'); self.assertEqual(len(result['results']),2)
        for page in result['results']:
            self.assertTrue(page['data']); self.assertIsInstance(page['next_cursor'],str)
        args[-5]=json.dumps([requests[0],{'op':'page','path':'../outside'}])
        p=subprocess.run(args,capture_output=True,timeout=10)
        self.assertNotEqual(p.returncode,0); self.assertEqual(p.stdout,b'')
        self.assertLessEqual(len(p.stderr)+1+256,2048)
        with mock.patch.dict(reader['run'].__globals__,one=lambda *unused: ('git exit=1\nerror',{},False)):
            partial=json.loads(reader['run'](self.root,{**request,'requests':[{'op':'status','path':'.'}]}))
            self.assertEqual(partial['status'],'PARTIAL')
            self.assertEqual(partial['results'][0]['status'],'PARTIAL')
            self.assertIn('incomplete',partial['results'][0]['hint'])
        with mock.patch.dict(reader['run'].__globals__,one=lambda *unused: json.dumps({'op':'locate','complete':False,'status':'PARTIAL'})):
            partial=json.loads(reader['run'](self.root,request))
            self.assertEqual(partial['status'],'PARTIAL')
            self.assertFalse(partial['results'][0]['complete'])

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
        for tool in ('send_input','wait','close_agent','update_plan','completion_check','read_file'):
            self.assertEqual(self.hook(tool),{})

    def test_native_resume_is_denied_before_executor_or_claimed_model_allowance(self):
        for model in ('gpt-6-astra', None, 'unknown', 'gpt-6.1-sol', 'gpt-6-sol',
                      'gpt-6-luna', 'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna'):
            for data in ({'id':'closed-child'},
                         {'id':'closed-child','model':'gpt-6.1-sol','reasoning_effort':'high'}):
                with self.subTest(model=model,data=data):
                    self.assertTrue(self.denied(self.hook('resume_agent',model,data)))
            self.assertEqual(self.hook('send_input',model,{'id':'live-child','message':'continue'}),{})

    def test_spawn_requires_explicit_role_effort_and_no_history_for_every_model(self):
        valid={'agent_type':'cer_auto_sol61_engineer','reasoning_effort':'high',
               'fork_turns':'none','message':'read-only source review'}
        for model in ('gpt-6-astra','gpt-6.1-sol','unknown'):
            self.assertEqual(self.hook('spawn_agent',model,valid),{})
            for bad in ({}, {**valid,'agent_type':'default'}, {**valid,'fork_turns':'all'},
                        {**valid,'fork_turns':'2'}, {k:v for k,v in valid.items() if k!='reasoning_effort'},
                        {**valid,'model':'gpt-6-astra'}, {**valid,'agent_type':'cer_auto_unknown'}):
                with self.subTest(model=model,bad=bad):
                    self.assertTrue(self.denied(self.hook('spawn_agent',model,bad)))

    def test_spawn_preserves_fixed_roles_and_explicit_legacy_model_pins(self):
        for data in ({'agent_type':'sol61_engineer','fork_turns':'none'},
                     {'agent_type':'astra_architect','fork_turns':'none'},
                     {'agent_type':'default','model':'gpt-5.6-sol','reasoning_effort':'high','fork_turns':'none'},
                     {'agent_type':'custom_reader','model':'gpt-6-luna','reasoning_effort':'low','fork_turns':'none'}):
            self.assertEqual(self.hook('spawn_agent','gpt-6-astra',data),{})
        self.assertEqual(self.hook('spawn_agent','gpt-6.1-sol',
                                   {'agent_type':'sol61_engineer','fork_turns':'none','reasoning_effort':'high'}), {})
        for data in ({'agent_type':'sol61_engineer','fork_turns':'none','reasoning_effort':'medium'},
                     {'agent_type':'default','model':'inherit','reasoning_effort':'high','fork_turns':'none'}):
            self.assertTrue(self.denied(self.hook('spawn_agent','gpt-6.1-sol',data)))
        self.assertEqual(self.hook('Agent','gpt-6-astra',{}),{})

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

    def test_guarded_structured_batch_rewrite_runs_actual_reader(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        request={'op':'batch','requests':[{'op':'page','path':'sentinel.txt','max_bytes':1024},
                                         {'op':'excerpt','path':'sentinel.txt','start':1,'lines':1,'max_bytes':1024}],
                 'max_bytes':3072,'framing_bytes':256}
        output=self.hook('Bash',data={'command':'cer-read '+json.dumps(request)})
        specific=output['hookSpecificOutput']
        self.assertEqual(specific['permissionDecision'],'allow')
        command=specific['updatedInput']['command']
        argv=['pwsh','-NoProfile','-NonInteractive','-Command',command] if os.name=='nt' else ['/bin/sh','-c',command]
        p=subprocess.run(argv,cwd=self.root,capture_output=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertLessEqual(len(p.stdout)+1+256,3072)
        result=json.loads(p.stdout)
        self.assertEqual([i['data'] for i in result['results']],['before','before'])
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

    def test_legacy_cli_and_guard_protocol_page_exact_selected_text(self):
        self.file.write_text('界🙂'*3000+'\nlast\n',encoding='utf-8')
        expected='1: '+'界🙂'*3000+'\n2: last'
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        cursor=None;parts=[];seen=set()
        for _ in range(50):
            args=[*cli,'read','--root',str(self.root),'--path','sentinel.txt','--lines','2']
            if cursor:args.extend(['--cursor',cursor])
            result=subprocess.run(args,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertLessEqual(len(result.stdout),4096)
            value=json.loads(result.stdout);self.assertTrue(value['data']);parts.append(value['data'])
            cursor=value['next_cursor']
            if cursor is None:break
            self.assertNotIn(cursor,seen);seen.add(cursor)
        else:self.fail('legacy CLI did not finish')
        self.assertEqual(''.join(parts),expected)
        command=self.hook('Bash',data={'command':'cer-read '+json.dumps({'op':'read','path':'sentinel.txt','lines':2})})['hookSpecificOutput']['updatedInput']['command']
        argv=['pwsh','-NoProfile','-NonInteractive','-Command',command] if os.name=='nt' else ['/bin/sh','-c',command]
        result=subprocess.run(argv,cwd=self.root,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr);self.assertLessEqual(len(result.stdout),4096)
        self.assertIsNotNone(json.loads(result.stdout)['next_cursor'])

    def test_git_capture_limit_remains_partial_after_paging(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        code,captured,truncated=reader['bounded_process']([sys.executable,'-c','import sys;sys.stdout.write("x"*160000)'],self.root,dict(os.environ))
        self.assertEqual(len(captured),reader['LIMIT']);self.assertTrue(truncated)
        fake='界🙂'*10000
        from unittest.mock import patch
        with patch.dict(reader['one'].__globals__,bounded_process=lambda *args,**kwargs:(0,fake.encode(),True)):
            cursor=None;parts=[]
            for _ in range(150):
                request={'op':'diff','path':'sentinel.txt'}
                if cursor:request['cursor']=cursor
                value=json.loads(reader['run'](self.root,request))
                self.assertLessEqual(len(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode())+2,4096)
                self.assertEqual(value['status'],'PARTIAL');self.assertIn('capture',value['hint'])
                self.assertTrue(value['data']);parts.append(value['data']);cursor=value['next_cursor']
                if cursor is None:break
            else:self.fail('git capture did not finish')
        self.assertIn(fake,''.join(parts))

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

    def test_reader_line_range_errors_preserve_cli_failure_and_allow_recovery(self):
        reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))
        expected=''.join(f'line {number}\n' for number in range(1,241))
        self.file.write_text(expected,encoding='utf-8',newline='')
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        for start,lines,message in ((0,1,'start must be an integer >=1'),
                                    (1,0,'lines must be an integer in 1..200'),
                                    (1,201,'lines must be an integer in 1..200'),
                                    (1,212,'lines must be an integer in 1..200'),
                                    (288,60,'file has 240 lines')):
            with self.subTest(start=start,lines=lines):
                result=subprocess.run([*cli,'excerpt',*common,'--start',str(start),
                                       '--lines',str(lines)],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,2)
                self.assertEqual(result.stdout,b'')
                self.assertIn(message,result.stderr.decode('utf-8'))
                self.assertIn('page',result.stderr.decode('utf-8'))
                self.assertLessEqual(len(result.stderr),4096)
        for key in ('start','lines'):
            with self.subTest(boolean=key), self.assertRaisesRegex(ValueError,'integer'):
                reader['validate']({'op':'excerpt','path':'sentinel.txt','start':1,'lines':1,key:True})
        for op,args,wanted in (('excerpt',['--start','1','--lines','200'],
                               ''.join(expected.splitlines(keepends=True)[:200])),
                              ('page',[],expected)):
            chunks=[]
            result=subprocess.run([*cli,op,*common,*args,'--max-bytes','1024'],
                                  capture_output=True,timeout=10)
            for _ in range(20):
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stderr,b'')
                self.assertLessEqual(len(result.stdout)+1,1024)
                value=json.loads(result.stdout)
                chunks.append(value['data'])
                if value['next_cursor'] is None:
                    break
                result=subprocess.run([*cli,'page',*common,'--cursor',value['next_cursor'],
                                       '--max-bytes','1024'],capture_output=True,timeout=10)
            else:
                self.fail('reader did not complete within 20 pages')
            self.assertEqual(''.join(chunks),wanted)

    @unittest.skipUnless(shutil.which('rg'),'rg unavailable')
    def test_reader_out_of_range_recovers_with_locate(self):
        expected=''.join(f'line {number}\n' for number in range(1,241))
        self.file.write_text(expected,encoding='utf-8',newline='')
        cli=[sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py')]
        common=['--root',str(self.root),'--path','sentinel.txt']
        failed=subprocess.run([*cli,'excerpt',*common,'--start','288','--lines','60'],
                              capture_output=True,timeout=10)
        self.assertEqual(failed.returncode,2)
        self.assertEqual(failed.stdout,b'')
        self.assertIn(b'locate',failed.stderr)
        located=subprocess.run([*cli,'locate',*common,'--query','line 225'],
                               capture_output=True,timeout=10)
        self.assertEqual(located.returncode,0,located.stderr)
        line=json.loads(located.stdout)['candidates'][0]['line']
        result=subprocess.run([*cli,'excerpt',*common,'--start',str(line),'--lines','16'],
                              capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout)
        self.assertEqual(value['data'],''.join(expected.splitlines(keepends=True)[224:]))
        self.assertIsNone(value['next_cursor'])

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


class JsonReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.file=self.root/'data.json'
        self.reader=runpy.run_path(str(ROOT/'hooks/readonly_reader.py'))

    def call(self, pointer='', mode='value', **options):
        request={'op':'json','path':'data.json','pointer':pointer,'mode':mode,**options}
        return json.loads(self.reader['run'](self.root,request))

    def test_json_pointer_selects_small_value(self):
        self.file.write_bytes(b'{"a/b":{"~key":[null,{"":42}]}}')
        page=self.call('/a~1b/~0key/1/')
        self.assertEqual(page['data'],'42')
        self.assertIsNone(page['next_cursor'])

    def test_json_large_source_preserves_old_read_limit(self):
        with self.file.open('wb') as stream:
            stream.write(b'{"padding":"')
            for _ in range(17):stream.write(b'x'*(1024*1024))
            stream.write(b'","tail":7}')
        with self.assertRaisesRegex(ValueError,'16 MiB'):
            self.reader['run'](self.root,{'op':'page','path':'data.json'})
        self.assertEqual(self.call('/tail')['data'],'7')

    def cli(self, *args):
        return subprocess.run([sys.executable,'-I','-B',str(ROOT/'hooks/readonly_reader.py'),
                               'json','--root',str(self.root),'--path','data.json',*args],
                              capture_output=True,timeout=30)

    def test_json_cli_and_native_protocol(self):
        self.file.write_text('{"value": [true,null,1e400]}',encoding='utf-8')
        result=self.cli('--pointer','/value/2')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['data'],'1e400')
        event={'hook_event_name':'PreToolUse','model':'gpt-6-astra','session_id':'shared-parent',
               'cwd':str(self.root),'tool_name':'Bash',
               'tool_input':{'command':'cer-read '+json.dumps(
                   {'op':'json','path':'data.json','pointer':'/value','mode':'members'})}}
        hook=subprocess.run([sys.executable,'-I','-B',str(GUARD)],input=json.dumps(event),
                            capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(hook.returncode,0,hook.stderr)
        output=json.loads(hook.stdout)['hookSpecificOutput']
        self.assertNotEqual(output.get('permissionDecision'),'deny')
        self.assertIn('updatedInput',output)
        command=output['updatedInput']['command']
        argv=['pwsh','-NoProfile','-NonInteractive','-Command',command] if os.name=='nt' else ['/bin/sh','-c',command]
        actual=subprocess.run(argv,cwd=self.root,capture_output=True,timeout=15)
        self.assertEqual(actual.returncode,0,actual.stderr)
        self.assertEqual([item['index'] for item in json.loads(actual.stdout)['members']],[0,1,2])
        event['tool_input']['command']='cer-read '+json.dumps({'op':'json','path':'data.json','pointer':'#/value'})
        rejected=subprocess.run([sys.executable,'-I','-B',str(GUARD)],input=json.dumps(event),
                                capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(json.loads(rejected.stdout)['hookSpecificOutput']['permissionDecision'],'deny')

    def test_json_pointer_rfc_boundaries(self):
        self.file.write_text('{"":0,"~1":1,"01":2,"é":3,"a":[4]}',encoding='utf-8')
        for pointer,expected in (('/', '0'),('/~01','1'),('/01','2'),('/é','3'),('/a/0','4')):
            self.assertEqual(self.call(pointer)['data'],expected)
        for pointer in ('#','a','/~','/~2','/a/01','/a/-','/a/+0','/a/０','/a/1','/e\u0301'):
            with self.subTest(pointer=pointer),self.assertRaises(ValueError):self.call(pointer)
        self.assertEqual(self.call()['data'],self.file.read_text(encoding='utf-8'))

    def test_json_value_pages_preserve_utf8_crlf_and_cross_block_escapes(self):
        expected='{\r\n"a":"'+('汉🙂\\\\\\\"\\uD83D\\uDE42'*350)+'"\r\n}'
        padding=b'x'*(65536-len(b'{"padding":"')-1)
        self.file.write_bytes(b'{"padding":"'+padding+b'\xf0\x9f\x99\x82","target":'+
                              expected.encode('utf-8')+b'}')
        page=self.call('/target');parts=[];cursors=set()
        while True:
            encoded=json.dumps(page,ensure_ascii=False,separators=(',',':')).encode('utf-8')
            self.assertLessEqual(len(encoded)+2,4096)
            parts.append(page['data']);cursor=page['next_cursor']
            if cursor is None:break
            self.assertNotIn(cursor,cursors);cursors.add(cursor)
            page=self.call('/target',cursor=cursor)
        self.assertGreater(len(parts),1)
        self.assertEqual(''.join(parts),expected)
        self.file.write_bytes(b'{"x":"'+b'a'*(65536-8)+b'\\uD83D\\uDE42","y":2}')
        self.assertEqual(self.call('/y')['data'],'2')
        self.file.write_text(json.dumps({'x':'a'*20000}),encoding='utf-8')
        page=self.call('/x');cursor=page['next_cursor']
        import base64
        state=json.loads(base64.urlsafe_b64decode(cursor+'='*(-len(cursor)%4)))
        state.pop('check');offset=state.pop('offset');first=state.pop('first');last=state.pop('last')
        enlarged={**page,'data':page['data']+'a',
                  'next_cursor':self.reader['cursor_token'](state,offset+1,first,last)}
        with self.assertRaisesRegex(ValueError,'envelope'):
            self.reader['envelope'](enlarged,4096)

    def test_json_members_paginate_direct_children_only(self):
        value={f'key/{i}~':{'nested':[i]} for i in range(300)}
        self.file.write_text(json.dumps({'root':value}),encoding='utf-8')
        page=self.call('/root','members');members=[];cursors=set()
        while True:
            self.assertLessEqual(len(json.dumps(page,ensure_ascii=False,separators=(',',':')).encode())+2,4096)
            members.extend(page['members']);cursor=page['next_cursor']
            if cursor is None:break
            self.assertTrue(page['members']);self.assertNotIn(cursor,cursors);cursors.add(cursor)
            page=self.call('/root','members',cursor=cursor)
        self.assertEqual([item['key'] for item in members],list(value))
        self.assertTrue(all(item['type']=='object' for item in members))
        self.assertEqual(members[0]['pointer'],'/root/key~10~0')
        self.assertEqual(self.call(members[-1]['pointer'])['data'],'{"nested": [299]}')
        self.file.write_text('[[],{},null,true,"s",2]',encoding='utf-8')
        items=self.call('','members')['members']
        self.assertEqual([item['index'] for item in items],list(range(6)))
        self.assertEqual([item['type'] for item in items],['array','object','null','boolean','string','number'])
        self.file.write_text('{}',encoding='utf-8')
        self.assertEqual(self.call('','members')['members'],[])

    def test_json_invalid_source_is_rejected_even_after_selected_value(self):
        cases=[b'{"ok":1,"later":NaN}',b'{"ok":1,"later":Infinity}',
               b'{"ok":1,"later":01}',b'{"ok":1,"later":1.}',b'{"ok":1,"later":1e+}',
               b'{"ok":1,"later":"\\q"}',b'{"ok":1,"later":"\\uXX00"}',
               b'{"ok":1,"later":"\\uD800"}',b'{"ok":1,"later":"\\uDC00"}',
               b'{"ok":1,"later":"\x00"}',b'{"ok":1,"later":"\xff"}',
               b'{"ok":1,"later":2,}',b'{"ok":1} false',b'{"ok":1',b'{"ok":1,"later":[1,]}']
        for raw in cases:
            with self.subTest(raw=raw):
                self.file.write_bytes(raw)
                result=self.cli('--pointer','/ok')
                self.assertEqual(result.returncode,2,result.stdout)
                self.assertEqual(result.stdout,b'')
                self.assertLessEqual(len(result.stderr)+1,4096)

    def test_json_duplicates_depth_and_key_budgets(self):
        for raw,pointer,mode in ((b'{"x":1,"x":2}','/x','value'),
                                 (b'{"x":{"v":1},"x":{"v":2}}','/x/v','value'),
                                 (b'{"x":1,"x":2}','','members')):
            self.file.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'duplicate'):self.call(pointer,mode)
        self.file.write_bytes(b'{"skip":{"x":1,"x":2},"ok":3}')
        self.assertEqual(self.call('/ok')['data'],'3')
        self.file.write_bytes(b'['*64+b'0'+b']'*64)
        self.assertEqual(self.call()['data'],'['*64+'0'+']'*64)
        self.file.write_bytes(b'['*65+b'0'+b']'*65)
        with self.assertRaisesRegex(ValueError,'depth'):self.call()
        self.file.write_text(json.dumps({'k'*(16*1024):0}),encoding='utf-8')
        self.assertTrue(self.call()['data'])
        self.file.write_text(json.dumps({'k'*(16*1024+1):0}),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'key'):self.call()
        self.file.write_text(json.dumps({str(i):0 for i in range(16385)}),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'16384'):self.call('','members')
        self.file.write_text(json.dumps({str(i)+'k'*6000:0 for i in range(175)}),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'1 MiB'):self.call('','members')
        with self.file.open('wb') as stream:stream.truncate(256*1024*1024+1)
        with self.assertRaisesRegex(ValueError,'256 MiB'):self.call()

    def test_json_cursor_is_bound_to_source_pointer_mode_and_boundary(self):
        raw=json.dumps({'x':'汉🙂'*4000,'y':list(range(400))},ensure_ascii=False).encode('utf-8')
        self.file.write_bytes(raw);cursor=self.call('/x')['next_cursor']
        self.assertIsNotNone(cursor)
        for pointer,mode,token in (('/y','value',cursor),('/x','members',cursor),('/x','value',cursor+'!')):
            with self.subTest(pointer=pointer,mode=mode),self.assertRaises(ValueError):
                self.call(pointer,mode,cursor=token)
        import base64
        state=json.loads(base64.urlsafe_b64decode(cursor+'='*(-len(cursor)%4)))
        state.pop('check');offset=state.pop('offset');first=state.pop('first');last=state.pop('last')
        fake=self.reader['cursor_token'](state,first+2,first,last)
        with self.assertRaises(UnicodeError):self.call('/x',cursor=fake)
        (self.root/'other.json').write_bytes(raw)
        with self.assertRaises(ValueError):
            self.reader['run'](self.root,{'op':'json','path':'other.json','pointer':'/x','cursor':cursor})
        before=self.file.stat();self.file.write_bytes(raw.replace(b', 399]',b', 398]'))
        os.utime(self.file,ns=(before.st_atime_ns,before.st_mtime_ns))
        self.assertEqual(self.file.stat().st_size,before.st_size)
        with self.assertRaisesRegex(ValueError,'cursor'):self.call('/x',cursor=cursor)
        self.file.write_bytes(raw);member_cursor=self.call('/y','members')['next_cursor']
        state=json.loads(base64.urlsafe_b64decode(member_cursor+'='*(-len(member_cursor)%4)))
        state.pop('check');offset=state.pop('offset');first=state.pop('first');last=state.pop('last')
        fake=self.reader['cursor_token'](state,offset+1,first,last)
        with self.assertRaisesRegex(ValueError,'boundary'):self.call('/y','members',cursor=fake)

    def test_json_bad_inputs_paths_batch_and_small_caps_fail_closed(self):
        self.file.write_text('{"x":"'+'a'*5000+'"}',encoding='utf-8')
        for options in ({'max_bytes':256},{'max_bytes':4097},{'max_bytes':True},
                        {'cursor':''},{'cursor':'x'*2049},{'mode':'depth'}, {'depth':1}):
            with self.subTest(options=options),self.assertRaises(ValueError):self.call('/x',**options)
        for path in ('../data.json','*.json','C:/data.json','data\\x.json','.'):
            with self.subTest(path=path),self.assertRaises(ValueError):
                self.reader['run'](self.root,{'op':'json','path':path,'pointer':''})
        with self.assertRaisesRegex(ValueError,'batched'):
            self.reader['run'](self.root,{'op':'batch','requests':[{'op':'json','path':'data.json','pointer':''}]})
        self.file.write_text('{"x":1}',encoding='utf-8')
        for args in (('--pointer','/x','--pointer','/x'),('--pointer','/x','--mode','no'),(),
                     ('--pointer','/x','--max-bytes','256')):
            result=self.cli(*args)
            # A terminal one-byte value fits 256 bytes; unfinished values above do not.
            if args==('--pointer','/x','--max-bytes','256'):
                self.assertEqual(result.returncode,0,result.stderr)
            else:
                self.assertEqual(result.returncode,2,result.stdout);self.assertEqual(result.stdout,b'')

    def test_json_symlink_refused(self):
        self.file.write_text('{}',encoding='utf-8');link=self.root/'link.json'
        try:link.symlink_to(self.file)
        except OSError:self.skipTest('symlink privilege unavailable')
        with self.assertRaisesRegex(ValueError,'symlink|reparse'):
            self.reader['run'](self.root,{'op':'json','path':'link.json','pointer':''})

    def test_json_reparse_refused_without_windows_privilege(self):
        self.file.write_text('{}',encoding='utf-8');original=Path.lstat
        class Reparse:
            st_file_attributes=0x400
        def attributes(path,*args,**kwargs):
            return Reparse() if path==self.file else original(path,*args,**kwargs)
        with mock.patch.object(Path,'is_symlink',return_value=False),mock.patch.object(Path,'lstat',attributes):
            with self.assertRaisesRegex(ValueError,'reparse'):
                self.call()

    def test_json_giant_number_and_skipped_objects_do_not_accumulate(self):
        with self.file.open('wb') as stream:
            stream.write(b'{"number":1')
            for _ in range(32):stream.write(b'9'*65536)
            stream.write(b'.')
            for _ in range(32):stream.write(b'9'*65536)
            stream.write(b'e+')
            for _ in range(32):stream.write(b'9'*65536)
            stream.write(b',"objects":[')
            for index in range(20000):
                if index:stream.write(b',')
                stream.write(b'{"same":0,"same":1}')
            stream.write(b'],"tail":1}')
        tracemalloc.start()
        try:
            self.assertEqual(self.call('/tail')['data'],'1')
            _,peak=tracemalloc.get_traced_memory()
        finally:tracemalloc.stop()
        self.assertLess(peak,8*1024*1024)
        print(f'JSON_NUMBER_RESOURCE source_bytes={self.file.stat().st_size} peak_bytes={peak}')

    def test_json_132_mib_small_values_have_bounded_reads_and_memory(self):
        block=b'x'*(1024*1024)
        with self.file.open('wb') as stream:
            stream.write(b'{"head":1,"catalog":'+json.dumps({str(i):[i] for i in range(300)}).encode()+b',"padding":"')
            for _ in range(66):stream.write(block)
            stream.write(b'","middle":2,"more":"')
            for _ in range(66):stream.write(block)
            stream.write(b'","tail":3}')
        before=self.file.stat();metrics=[];original=Path.open
        class BoundedFile:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def seek(self,*args):return self.stream.seek(*args)
            def read(self,count=-1):
                if not 0<=count<=65536:raise AssertionError(f'unbounded read: {count}')
                data=self.stream.read(count);metrics.append((count,len(data)));return data
        def opening(path,*args,**kwargs):
            stream=original(path,*args,**kwargs)
            return BoundedFile(stream) if path==self.file and args==('rb',) else stream
        started=time.monotonic();tracemalloc.start()
        try:
            with mock.patch.object(Path,'open',opening):
                for pointer,expected in (('/head','1'),('/middle','2'),('/tail','3')):
                    self.assertEqual(self.call(pointer)['data'],expected)
            _,peak=tracemalloc.get_traced_memory()
        finally:tracemalloc.stop()
        self.assertLess(peak,8*1024*1024)
        self.assertEqual(max(count for count,_ in metrics),65536)
        self.assertLessEqual(sum(size for _,size in metrics),3*(before.st_size+4096))
        self.assertEqual((self.file.stat().st_size,self.file.stat().st_mtime_ns),(before.st_size,before.st_mtime_ns))
        print(f'JSON_RESOURCE source_bytes={before.st_size} peak_bytes={peak} '
              f'max_read={max(count for count,_ in metrics)} elapsed_s={time.monotonic()-started:.3f}')
        page=self.call('/catalog','members');members=[];pages=0
        while True:
            self.assertLessEqual(len(json.dumps(page,ensure_ascii=False,separators=(',',':')).encode())+2,4096)
            pages+=1;members.extend(page['members']);cursor=page['next_cursor']
            if cursor is None:break
            self.assertTrue(page['members'])
            page=self.call('/catalog','members',cursor=cursor)
        self.assertGreater(pages,1)
        self.assertEqual([item['key'] for item in members],[str(i) for i in range(300)])
        import io
        from types import SimpleNamespace
        changed=False
        class MutatingFile(BoundedFile):
            def read(self,count=-1):
                nonlocal changed
                data=super().read(count)
                if not data and not changed:
                    changed=True
                    with original(self_path,'r+b') as writer:writer.seek(8);writer.write(b'9')
                    os.utime(self_path,ns=(before.st_atime_ns,before.st_mtime_ns+1000000000))
                return data
        self_path=self.file
        def changing_open(path,*args,**kwargs):
            stream=original(path,*args,**kwargs)
            return MutatingFile(stream) if path==self.file and args==('rb',) else stream
        out=io.BytesIO();err=io.BytesIO()
        with mock.patch.object(Path,'open',changing_open),mock.patch.object(sys,'argv',[
                'reader.py','json','--root',str(self.root),'--path','data.json','--pointer','/tail']),\
                mock.patch.object(sys,'stdout',SimpleNamespace(buffer=out)),\
                mock.patch.object(sys,'stderr',SimpleNamespace(buffer=err)):
            code=self.reader['main']()
        self.assertTrue(changed);self.assertEqual(code,2);self.assertEqual(out.getvalue(),b'')
        self.assertIn(b'changed',err.getvalue());self.assertLessEqual(len(err.getvalue())+1,4096)


if __name__=='__main__':unittest.main()
