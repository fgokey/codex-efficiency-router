"""Execute the shipped JavaScript against deterministic native-tool timelines.

No model calls. Simulated transport timing is not a measured token/speed saving.
"""
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
READER = runpy.run_path(str(ROOT / 'hooks/readonly_reader.py'))

HARNESS = r'''
const input=JSON.parse(require('fs').readFileSync(0,'utf8'));
const Async=Object.getPrototypeOf(async function(){}).constructor;
(async()=>{
 let now=0,calls=[],outputs=[],memory=new Map(Object.entries(input.memory||{}));
 const originalNow=Date.now;Date.now=()=>now;
 const store=(k,v)=>memory.set(k,v),load=k=>memory.get(k);
 const text=v=>{if(Buffer.byteLength(JSON.stringify(v))+2+input.framing>4096)throw Error('output overflow');outputs.push(v);};
 const tools={mcp__codex_app__wait_threads:async args=>{
  calls.push(args);let row=input.responses[calls.length-1];
  if(!row)throw Error('unexpected extra native wait');
  now+=row.duration;
  if(row.throws)throw Error(row.throws);
  return row.raw||{content:[{type:'text',text:JSON.stringify(row.snapshot)}]};
 }};
 let error=null;
 try{await new Async('tools','targets','framingBytes','store','load','text','parentReady','waitCapabilities',input.code)(
  tools,input.targets,input.framing,store,load,text,input.ready,input.caps);}catch(e){error=e.message;}
 const beforeDrain=Object.fromEntries(memory);
 let pages=[],rawRecovered=null;
 if(input.drain&&load('cerPending')){
  let raw='',offset=0,last;
  do{await new Async('framingBytes','store','load','text',input.page)(input.framing,store,load,v=>{
   if(Buffer.byteLength(JSON.stringify(v))+2+input.framing>4096)throw Error('page overflow');
   if(v.offset!==offset)throw Error('page gap');raw+=v.data;offset+=v.data.length;last=v;pages.push(v);
  });}while(last.next!==null);
  rawRecovered=JSON.parse(raw);
 }
 Date.now=originalNow;
 const pageSizes=pages.map(p=>Buffer.byteLength(JSON.stringify(p))+2+input.framing);
 const pageSummary=pages.length?Object.fromEntries(['polls','errors','offset','next','total'].map(k=>[k,pages[0][k]])):null;
 process.stdout.write(JSON.stringify({calls,outputs,error,now,memory:beforeDrain,rawRecovered,pageCount:pages.length,
  pageBytes:pageSizes.reduce((a,b)=>a+b,0),maxPageBytes:Math.max(0,...pageSizes),pageSummary}));
})().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
'''


def snapshot(*, status='inProgress', turn='t1', cursor='c1', error=None, wake=None,
             timed_out=True, text='working', phase='commentary', marker=None):
    return dict(timedOut=timed_out, wake=wake, polls=[dict(
        thread={'id':'worker','status':{'type':'active'}}, cursor=cursor,
        latestTurn={'id':turn,'status':status,'error':error},
        latestAssistantMessage={'id':'message','phase':phase,'text':text},
        latestToolMarker=marker)])


def cached():
    return {'cerWait': {'worker': json.dumps(
        [{'type':'active'}, 't1', 'inProgress', None, None, None], separators=(',', ':'))},
        'cerCursors': {'worker':'prior'}, 'cerIdle':2}


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable for code-mode adapter replay')
class QuietCoordinationTests(unittest.TestCase):
    def run_adapter(self, responses=(), **changes):
        args=dict(code=READER['COORDINATION_QUIET_JS'],page=READER['COORDINATION_PAGE_JS'],
                  responses=list(responses),targets=[{'threadId':'worker'}],framing=64,
                  caps={'execYieldMs':120000,'nativeTimeoutMs':60000},ready=True,memory=cached())
        args.update(changes)
        p=subprocess.run([shutil.which('node'),'-e',HARNESS],input=json.dumps(args),
                         text=True,encoding='utf-8',capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        return json.loads(p.stdout)

    def reply(self, **kw):
        return dict(duration=50000,snapshot=snapshot(**kw))

    def test_quiet_wait_batches_two_native_timeouts_into_one_model_return(self):
        r=self.run_adapter([self.reply(cursor='next1'),self.reply(cursor='next2')])
        self.assertIsNone(r['error']);self.assertEqual(len(r['calls']),2)
        self.assertEqual(len(r['outputs']),1);self.assertEqual(r['now'],100000)
        self.assertEqual(r['outputs'][0]['polls'],[])
        self.assertEqual([c['timeoutMs'] for c in r['calls']],[50000,50000])
        self.assertNotIn('cerQuietActive',r['memory'])

    def test_explicit_initial_cursor_then_latest_saved_cursor(self):
        r=self.run_adapter([self.reply(cursor='next1'),self.reply(cursor='next2')],
                           targets=[{'threadId':'worker','afterCursor':'explicit'}])
        self.assertEqual([c['targets'][0]['afterCursor'] for c in r['calls']],['explicit','next1'])
        self.assertEqual(r['memory']['cerCursors']['worker'],'next2')

    def test_completion_is_not_delayed_to_checkpoint(self):
        r=self.run_adapter([dict(duration=3000,snapshot=snapshot(status='completed',phase='final_answer',
                            text='check result',timed_out=False,wake={'type':'completed'}))])
        self.assertEqual(len(r['calls']),1);self.assertEqual(r['now'],3000)
        self.assertEqual(r['outputs'][0]['polls'][0][9],'check result')

    def test_error_approval_new_turn_and_unknown_wake_return_immediately(self):
        examples=[snapshot(error={'message':'blocked'}),snapshot(turn='t2'),
                  snapshot(wake={'type':'user_steering'},timed_out=False),
                  snapshot(marker={'id':'e1','status':'failed'})]
        approval=snapshot();approval['polls'][0]['thread']['status']['type']='waitingOnApproval'
        examples.append(approval)
        for s in examples:
            with self.subTest(snapshot=s):
                r=self.run_adapter([dict(duration=50000,snapshot=s)])
                self.assertIsNone(r['error']);self.assertEqual(len(r['calls']),1)
                self.assertEqual(len(r['outputs']),1)

    def test_immediate_unchanged_response_does_not_busy_poll(self):
        r=self.run_adapter([dict(duration=10,snapshot=snapshot())])
        self.assertEqual(len(r['calls']),1)

    def test_missing_and_duplicate_targets_stop_with_recoverable_raw_data(self):
        examples=[dict(timedOut=True,wake=None,polls=[]),snapshot()]
        examples[1]['polls']*=2
        for s in examples:
            r=self.run_adapter([dict(duration=50000,snapshot=s)],drain=True)
            self.assertEqual(len(r['calls']),1)
            self.assertEqual(r['outputs'][0]['status'],'PARTIAL')
            self.assertEqual(json.loads(r['rawRecovered']['content'][0]['text']),s)

    def test_raw_errors_schema_changes_and_extra_content_are_not_discarded(self):
        raws=[{'isError':True,'content':[{'type':'text','text':'rate limited'}]},
              {'content':[{'type':'text','text':'not JSON'}]},
              {'content':[{'type':'text','text':json.dumps(snapshot())},
                          {'type':'text','text':'additional evidence'}]}]
        for raw in raws:
            r=self.run_adapter([dict(duration=50000,raw=raw)],drain=True)
            self.assertEqual(r['rawRecovered'],raw);self.assertEqual(len(r['calls']),1)

    def test_output_overflow_retains_final_evidence_and_pagination(self):
        s=snapshot(status='completed',phase='final_answer',text='结果😀'*6000)
        r=self.run_adapter([dict(duration=100,snapshot=s)],drain=True)
        self.assertEqual(r['outputs'][0]['status'],'PARTIAL')
        self.assertEqual(json.loads(r['memory']['cerRaw']['content'][0]['text']),s)
        self.assertEqual(r['rawRecovered']['polls'][0][9],s['polls'][0]['latestAssistantMessage']['text'])
        self.assertGreater(r['pageCount'],1)

    def test_parent_work_or_pending_page_does_not_start_another_wait(self):
        r=self.run_adapter(ready=False,caps=None)
        self.assertEqual(r['outputs'],[{'action':'WORK'}]);self.assertEqual(r['calls'],[])
        for state,reason in [({'cerPending':True},'pending page')]:
            r=self.run_adapter(memory=state)
            self.assertIn(reason,r['error']);self.assertEqual(r['calls'],[])

    def test_unavailable_capability_fails_without_probing(self):
        for caps in [None,{},dict(execYieldMs=30000,nativeTimeoutMs=60000),
                     dict(execYieldMs=120000,nativeTimeoutMs=10000)]:
            r=self.run_adapter(caps=caps)
            self.assertIn('observed',r['error']);self.assertEqual(r['calls'],[])

    def test_target_errors_and_thrown_errors_are_not_retried(self):
        r=self.run_adapter([dict(duration=100,snapshot=dict(timedOut=False,wake=None,polls=[],
                                errors=[{'threadId':'worker','error':'not found'}]))])
        self.assertEqual(len(r['calls']),1);self.assertEqual(r['outputs'][0]['errors'][0]['error'],'not found')
        r=self.run_adapter([dict(duration=100,throws='native failure')])
        self.assertEqual(r['error'],'native failure');self.assertEqual(len(r['calls']),1)
        self.assertNotIn('cerQuietActive',r['memory'])

    def test_overlong_native_response_does_not_start_another_fifty_second_wait(self):
        r=self.run_adapter([dict(duration=65000,snapshot=snapshot())])
        self.assertEqual(len(r['calls']),1);self.assertEqual(r['now'],65000)

    def test_full_target_set_is_preserved_on_every_wait(self):
        a=snapshot();b=snapshot(cursor='c2')['polls'][0];b['thread']['id']='second'
        a['polls'].append(b)
        old=cached();old['cerWait']['second']=old['cerWait']['worker']
        r=self.run_adapter([dict(duration=50000,snapshot=a)]*2,
            targets=[{'threadId':'worker'},{'threadId':'second'}],memory=old)
        self.assertEqual(len(r['calls']),2)
        self.assertTrue(all([t['threadId'] for t in c['targets']]==['worker','second'] for c in r['calls']))

    def test_invalid_targets_rejected_before_any_call(self):
        for targets in [[],[{'threadId':'worker'}]*2,[{'threadId':'a','model':'fake'}],
                        [{'threadId':'worker','afterCursor':None}]]:
            r=self.run_adapter(targets=targets);self.assertEqual(r['calls'],[])
            self.assertIn('invalid wait targets',r['error'])

    def test_first_snapshot_is_surfaced_not_assumed_unchanged(self):
        r=self.run_adapter([self.reply()],memory={})
        self.assertEqual(len(r['calls']),1);self.assertTrue(r['outputs'][0]['polls'][0][8])

    def test_unknown_top_level_evidence_is_returned_instead_of_suppressed(self):
        s=snapshot();s['newWarning']={'reason':'schema changed'}
        r=self.run_adapter([dict(duration=50000,snapshot=s)],drain=True)
        self.assertEqual(len(r['calls']),1)
        self.assertEqual(json.loads(r['rawRecovered']['content'][0]['text']),s)

    def test_no_persistent_execution_lock_can_poison_a_later_cell(self):
        self.assertNotIn('cerQuietActive', READER['COORDINATION_QUIET_JS'])
        # Actual yielded cell IDs are owned by the host, not inferred from a saved boolean.
        quality=(ROOT/'skills/codex-efficiency-router/references/quality.md').read_text()
        self.assertIn('never start another wait cell',quality)

    def test_second_wait_returns_completion_without_a_third_wait(self):
        done=snapshot(status='completed',phase='final_answer',text='finished',
                      timed_out=False,wake={'type':'completed'})
        r=self.run_adapter([self.reply(),dict(duration=7000,snapshot=done)])
        self.assertEqual(len(r['calls']),2)
        self.assertEqual(r['now'],57000)
        self.assertEqual(r['outputs'][0]['polls'][0][9],'finished')

    def test_runtime_rules_preserve_boundaries_and_remove_unchanged_probes(self):
        quality=(ROOT/'skills/codex-efficiency-router/references/quality.md').read_text()
        dispatch=(ROOT/'skills/codex-efficiency-router/references/dispatch.md').read_text()
        for phrase in ('WHOLE wait', 'never start another wait cell',
                       'No status/admission/completion polling while unchanged',
                       'required gaps remain PARTIAL/BLOCKED'):
            self.assertIn(phrase,quality)
        for phrase in ('one implementation owner plus an on-demand reviewer',
                       'Delegate that whole unit, not each command',
                       'An authorized writer updates it, not Astra',
                       'UNKNOWN/MISMATCH blocks writes'):
            self.assertIn(phrase,dispatch)

    def test_pragma_is_first_and_wait_only_no_mutating_tools(self):
        code=READER['COORDINATION_QUIET_JS']
        directive=json.loads(code.splitlines()[0].removeprefix('// @exec: '))
        self.assertEqual(directive['yield_time_ms'],120000)
        self.assertGreaterEqual(directive['max_output_tokens'],4096)
        for forbidden in ('send_input(', 'spawn_agent(', 'apply_patch(', 'write_stdin(',
                          'completion_check(', 'eval(', 'new Function', 'setTimeout('):
            self.assertNotIn(forbidden,code)


if __name__=='__main__':unittest.main()
