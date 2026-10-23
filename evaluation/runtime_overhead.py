"""Paired Hook subprocess timing and deterministic wait transport replay.

No models, credentials, user config or background services. Simulated wait time
and model-visible tool returns are not measured model tokens or task speed.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import platform
import runpy
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def bundle(root):
    files = {n: hashlib.sha256((root / 'hooks' / n).read_bytes()).hexdigest()
             for n in ('astra_write_guard.py', 'readonly_reader.py')}
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def percentiles(values):
    import math
    values = sorted(values)
    return {'samples': len(values), 'p50_ms': values[math.ceil(.5 * len(values)) - 1],
            'p95_ms': values[math.ceil(.95 * len(values)) - 1]}


def hook_benchmark(roots, iterations):
    if type(iterations) is not int or not 3 <= iterations <= 100:
        raise ValueError('iterations must be 3..100')
    samples = {name: {k: [] for k in ('deny_write', 'executor', 'spawn', 'dispatch')}
               for name in roots}
    loads = {}
    with tempfile.TemporaryDirectory(prefix='cer-hook-replay-') as tmp:
        host = Path(tmp).resolve()
        dbpath = host / 'state_5.sqlite'
        with closing(sqlite3.connect(dbpath)) as db, db:
            db.execute('CREATE TABLE threads (id TEXT, model TEXT, reasoning_effort TEXT, '
                       'source TEXT, thread_source TEXT, agent_role TEXT, agent_path TEXT, '
                       'archived INTEGER, rollout_path TEXT)')
            source = json.dumps({'subagent': {'thread_spawn': {'parent_thread_id': 'parent'}}})
            db.executemany('INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)', [
                ('parent','gpt-6-astra','high','{}','','','/parent',0,''),
                ('child','gpt-6.1-sol','high',source,'','sol61_engineer','/child',0,'')])
        before = dbpath.read_bytes()
        commands = {}
        for name, root in roots.items():
            reader = runpy.run_path(str(root / 'hooks/readonly_reader.py'))
            guard = runpy.run_path(str(root / 'hooks/astra_write_guard.py'))
            policy = root / 'skills/codex-efficiency-router'
            request = {'unit_id':'fixture','purpose':'new_unit','scope':'src/example.py',
                       'message':'Review the owned source only.',
                       'recipient':{'id':'child','model':'gpt-6.1-sol','effort':'high','evidence_ref':'test fixture'},
                       'signals':dict.fromkeys(('spec_complete','authority_ready','environment_ready','observability_ready'),True)}
            prepared = reader['assignment_preflight'](request, policy_sha256=reader['assignment_policy_sha256'](policy))
            work = reader['assignment_message'](prepared, request['message'])
            common = {'hook_event_name':'PreToolUse','session_id':'parent','model':'gpt-6-astra','cwd':str(host)}
            events = {
                'deny_write': {**common,'tool_name':'apply_patch','tool_input':{}},
                'executor': {**common,'model':'gpt-6.1-sol','tool_name':'apply_patch','tool_input':{}},
                'spawn': {**common,'tool_name':'spawn_agent','tool_input':{
                    'agent_type':'cer_auto_sol61_engineer','reasoning_effort':'high',
                    'fork_turns':'none','message':guard['HOLD_MESSAGE']}},
                'dispatch': {**common,'tool_name':'send_input','tool_input':{'id':'child','message':work}},
            }
            base = [sys.executable,'-I','-B',str(root / 'hooks/astra_write_guard.py'), '--expected-bundle',bundle(root)]
            commands[name] = {k:(base + (['--dispatch-only','--host-directory',str(host),'--policy-root',str(policy)]
                              if k=='dispatch' else []),json.dumps(event)) for k,event in events.items()}
            from unittest.mock import patch
            original = runpy.run_path
            with patch.object(runpy, 'run_path', wraps=original) as loader:
                result = guard['decide_dispatch'](events['dispatch'],host_directory=host,policy_root=policy)
            if result != {}:
                raise ValueError('in-process dispatch did not pass')
            loads[name] = sum(Path(c.args[0]).name=='readonly_reader.py' for c in loader.call_args_list)
        for index in range(iterations):
            names = list(roots) if index % 2 == 0 else list(reversed(roots))
            kinds = list(samples[names[0]])
            kinds = kinds[index % len(kinds):] + kinds[:index % len(kinds)]
            for kind in kinds:
                for name in names:
                    args, payload = commands[name][kind]
                    start = time.perf_counter()
                    p = subprocess.run(args,input=payload,text=True,encoding='utf-8',capture_output=True,timeout=10,check=True)
                    elapsed = (time.perf_counter()-start)*1000
                    out = json.loads(p.stdout) if p.stdout.strip() else {}
                    decision = out.get('hookSpecificOutput',{}).get('permissionDecision')
                    if decision != ('deny' if kind=='deny_write' else None):
                        raise ValueError('Hook decision changed during measurement')
                    if kind!='deny_write' and out!={}:
                        raise ValueError('successful Hook unexpectedly injects model context')
                    samples[name][kind].append(elapsed)
        if dbpath.read_bytes()!=before:
            raise ValueError('read-only fixture database changed')
    return {'iterations':iterations,'order':'alternating variant order; rotated cases',
            'includes':'fresh Python startup, reviewed bundle hashes and the actual guard process',
            'reader_code_loads_per_dispatch':loads,
            'measurements':{n:{k:percentiles(v) for k,v in m.items()} for n,m in samples.items()}}


REPLAY = r'''
const input=JSON.parse(require('fs').readFileSync(0,'utf8')),Async=Object.getPrototypeOf(async function(){}).constructor;
(async()=>{let results=[];for(const [name,code]of Object.entries(input.codes)){
 let now=0,calls=0,returns=0,codeBytes=0,outputBytes=0,last;
 const status=[{type:'active'},'turn','inProgress',null,null,null];
 const memory=new Map([['cerWait',{worker:JSON.stringify(status)}],['cerIdle',2]]);
 const store=(k,v)=>memory.set(k,v),load=k=>memory.get(k),original=Date.now;Date.now=()=>now;
 const tools={mcp__codex_app__wait_threads:async args=>{
  calls++;now=Math.min(input.end,now+args.timeoutMs);const done=now===input.end;
  return{content:[{type:'text',text:JSON.stringify({timedOut:!done,wake:done?{type:'completed'}:null,
   polls:[{thread:{id:'worker',status:{type:'active'}},cursor:'c'+now,
    latestTurn:{id:'turn',status:done?'completed':'inProgress',error:null},
    latestAssistantMessage:{id:'m',phase:done?'final_answer':'commentary',text:done?'fixture evidence':'working'},latestToolMarker:null}]})}]};
 }};
 while(now<input.end&&returns<100){returns++;codeBytes+=Buffer.byteLength(code);
  await new Async('tools','targets','framingBytes','store','load','text','parentReady','waitCapabilities',code)(
    tools,[{threadId:'worker'}],64,store,load,v=>{last=v;outputBytes+=Buffer.byteLength(JSON.stringify(v));},true,
    {execYieldMs:120000,nativeTimeoutMs:60000});
  if(load('cerPending')||last.status==='PARTIAL')throw Error('unexpected pagination');
 }
 Date.now=original;
 const raw=JSON.parse(load('cerRaw').content[0].text);
 if(now!==input.end||raw.polls[0].latestTurn.status!=='completed'||last.polls[0][9]!=='fixture evidence')throw Error('completion lost');
 results.push({name,native_waits:calls,model_visible_returns:returns,simulated_wall_ms:now,
  adapter_source_bytes_sent:codeBytes,result_bytes:outputBytes,final_text:last.polls[0][9]});
}process.stdout.write(JSON.stringify(results));})().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
'''


def wait_replay(baseline, candidate):
    node = shutil.which('node')
    if not node:
        return {'status':'UNKNOWN','reason':'Node.js unavailable; no results invented'}
    old = runpy.run_path(str(baseline / 'hooks/readonly_reader.py'))
    new = runpy.run_path(str(candidate / 'hooks/readonly_reader.py'))
    p = subprocess.run([node,'-e',REPLAY],input=json.dumps({'end':600000,'codes':{
        'baseline_default':old['COORDINATION_JS'],'baseline_adaptive':old['COORDINATION_ADAPTIVE_JS'],
        'candidate_quiet':new['COORDINATION_QUIET_JS']}}),text=True,encoding='utf-8',capture_output=True,check=True,timeout=10)
    return {'status':'EXECUTED_SIMULATION','scenario':'ten-minute quiet worker; seeded known state; event wakes on completion',
            'rows':json.loads(p.stdout),'limitation':'Adapter bytes counted; no inference, billing or real application time measured'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root',type=Path,required=True)
    parser.add_argument('--candidate-root',type=Path,default=ROOT)
    parser.add_argument('--iterations',type=int,default=30)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        roots={'baseline':args.baseline_root.resolve(strict=True),'candidate':args.candidate_root.resolve(strict=True)}
        if args.output.exists():
            raise ValueError('output exists; use a new report path')
        report={'evidence_kind':'offline process measurement + deterministic transport replay',
                'platform':platform.platform(),'python':platform.python_version(),
                'guard_bundle_sha256':{k:bundle(p) for k,p in roots.items()},
                'hook_processes':hook_benchmark(roots,args.iterations),
                'wait_replay':wait_replay(roots['baseline'],roots['candidate']),
                'model_calls':0,'live_model_tokens':None,'live_task_speed':None,'live_task_quality':None}
        text=json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        with args.output.open('x',encoding='utf-8') as f:f.write(text)
        print(text)
        return 0
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        print(f'overhead replay failed: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
