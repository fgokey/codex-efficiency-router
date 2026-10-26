# Regression coverage for existing wait/read paths; no model calls.
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import test_quiet_coordination as quiet

ROOT = Path(__file__).resolve().parents[1]
R = runpy.run_path(str(ROOT / 'hooks/readonly_reader.py'))

@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable for adapter replay')
class ExistingWaitTests(unittest.TestCase):
    def run_adapter(self, *args, **kwargs):
        return quiet.QuietCoordinationTests.run_adapter(self, *args, **kwargs)

    def mixed(self):
        result = quiet.snapshot(status='completed', phase='final_answer', text='verified result')
        other = quiet.snapshot()['polls'][0]
        other['thread']['id'] = 'second'
        result['polls'].append(other)
        return result

    def test_short_native_errors_and_non_single_text_results_require_raw_recovery(self):
        result = quiet.snapshot(status='completed', phase='final_answer', text='short final')
        content = {'type': 'text', 'text': json.dumps(result)}
        cases = [dict(isError=True, content=[content]),
                 dict(content=[content, {'type': 'text', 'text': 'other evidence'}]),
                 dict(content=[dict(content, type='image')])]
        for code in (R['COORDINATION_JS'], R['COORDINATION_QUIET_JS']):
            for raw in cases:
                replay = self.run_adapter([dict(duration=10, raw=raw)], memory={}, code=code, drain=True)
                self.assertEqual(replay['outputs'][0]['status'], 'PARTIAL')
                self.assertTrue(replay['memory']['cerPending'])
                self.assertEqual(replay['rawRecovered'], raw)
                blocked = self.run_adapter([], memory=replay['memory'], code=code)
                self.assertEqual(blocked['calls'], [])
                self.assertIn('pending page', blocked['error'])

    def test_short_final_requires_nonempty_text_identity_and_text_body(self):
        for field, value in (('id', None), ('id', ''), ('id', 1), ('text', None), ('text', {})):
            response = quiet.snapshot(status='completed', phase='final_answer', text='short final')
            response['polls'][0]['latestAssistantMessage'][field] = value
            for code in (R['COORDINATION_JS'], R['COORDINATION_QUIET_JS']):
                replay = self.run_adapter([dict(duration=10, snapshot=response)], memory={}, code=code, drain=True)
                self.assertEqual(replay['outputs'][0]['status'], 'PARTIAL')
                self.assertEqual(json.loads(replay['rawRecovered']['content'][0]['text']), response)

    def test_basic_wait_does_not_repeat_unchanged_final_evidence(self):
        response = quiet.snapshot(status='completed', phase='final_answer', text='evidence' * 200)
        first = self.run_adapter([dict(duration=10, snapshot=response)], memory={},
                                 code=R['COORDINATION_JS'])
        response['polls'][0]['cursor'] = 'next-cursor'
        again = self.run_adapter([dict(duration=10, snapshot=response)], memory=first['memory'],
                                 code=R['COORDINATION_JS'])
        row = again['outputs'][0]['polls'][0]
        self.assertEqual(row[1], 'next-cursor')
        self.assertFalse(row[8])
        self.assertTrue(row[9] is None, 'unchanged final must use its existing evidence')
        self.assertLess(len(json.dumps(again['outputs'][0])), len(json.dumps(first['outputs'][0])))

    def test_overflow_summary_counts_all_targets_and_errors_without_losing_raw_evidence(self):
        response = self.mixed()
        response['polls'][0]['latestAssistantMessage']['text'] = 'evidence😀' * 2000
        response['errors'] = [{'threadId': 'third', 'error': 'native failure'}]
        result = self.run_adapter([dict(duration=10, snapshot=response)], memory={}, drain=True,
                                  targets=[{'threadId': 'worker'}, {'threadId': 'second'}])
        summary = result['outputs'][0]
        self.assertEqual(summary['status'], 'PARTIAL')
        page = result['pageSummary']
        self.assertEqual((page['polls'], page['errors'], page['offset']), (2, 1, 0))
        self.assertIsNotNone(page['next'])
        self.assertEqual(json.loads(result['memory']['cerRaw']['content'][0]['text']), response)
        self.assertEqual(result['rawRecovered']['errors'], response['errors'])
        rows = result['rawRecovered']['polls']
        self.assertEqual([row[1] for row in rows], [p['cursor'] for p in response['polls']])
        self.assertEqual(rows[0][9], response['polls'][0]['latestAssistantMessage']['text'])
        self.assertGreater(result['pageCount'], 1)

    def test_valid_overflow_pages_selected_evidence_instead_of_raw_metadata(self):
        response = quiet.snapshot(status='completed', phase='final_answer',
                                  error={'message': 'failed😀' * 1000}, text='final😀' * 1000)
        response['polls'][0]['thread']['metadata'] = 'irrelevant history' * 10000
        result = self.run_adapter([dict(duration=10, snapshot=response)], memory={}, drain=True)
        projected = result['rawRecovered']
        self.assertIn('polls', projected)
        row = projected['polls'][0]
        source = response['polls'][0]
        self.assertEqual(row[:6], ['worker', 'c1', source['thread']['status'], 't1',
                                  'completed', source['latestTurn']['error']])
        self.assertEqual(row[9], source['latestAssistantMessage']['text'])
        self.assertEqual(json.loads(result['memory']['cerRaw']['content'][0]['text']), response)
        self.assertNotIn('metadata', json.dumps(projected))
        self.assertLess(len(json.dumps(projected)), len(json.dumps(response)) // 4)

    def test_quiet_schema_failure_discards_candidate_projection_only(self):
        for code in (R['COORDINATION_JS'], R['COORDINATION_QUIET_JS']):
            for missing_id in (False, True):
                response = quiet.snapshot(status='completed', phase='final_answer', text='evidence' * 3000)
                if missing_id:
                    del response['polls'][0]['latestAssistantMessage']['id']
                else:
                    response['polls'][0]['latestTurn']['status'] = 'unsupported'
                result = self.run_adapter([dict(duration=10, snapshot=response)], memory={}, drain=True, code=code)
                self.assertEqual(len(result['calls']), 1)
                self.assertEqual(json.loads(result['rawRecovered']['content'][0]['text']), response)

    def test_completed_report_not_repeated_while_another_worker_runs(self):
        targets = [{'threadId':'worker'}, {'threadId':'second'}]
        first = self.run_adapter([dict(duration=10, snapshot=self.mixed())], targets=targets, memory={})
        self.assertEqual(first['outputs'][0]['polls'][0][9], 'verified result')
        following = self.run_adapter([dict(duration=50000, snapshot=self.mixed())] * 2,
                                     targets=targets, memory=first['memory'])
        self.assertIsNone(following['error'])
        self.assertEqual(len(following['calls']), 2)
        self.assertEqual(following['outputs'][0]['polls'], [])
        self.assertEqual(following['outputs'][0]['unchanged'], 2)

    def test_changed_final_text_with_same_message_id_is_visible(self):
        first = self.run_adapter([dict(duration=10, snapshot=quiet.snapshot(
            status='completed', phase='final_answer', text='first'))], memory={})
        result = self.run_adapter([dict(duration=10, snapshot=quiet.snapshot(
            status='completed', phase='final_answer', text='corrected'))], memory=first['memory'])
        self.assertEqual(result['outputs'][0]['polls'][0][9], 'corrected')
        self.assertTrue(result['outputs'][0]['polls'][0][8])

    def test_repeated_error_still_returns_immediately(self):
        response = quiet.snapshot(error={'message':'validation failed'})
        first = self.run_adapter([dict(duration=10, snapshot=response)], memory={})
        again = self.run_adapter([dict(duration=50000, snapshot=response)], memory=first['memory'])
        self.assertEqual(len(again['calls']), 1)
        self.assertTrue(again['outputs'][0]['polls'][0][5])

    def test_overflow_requires_draining_evidence_before_wait(self):
        response = quiet.snapshot(status='completed', phase='final_answer', text='evidence' * 10000)
        first = self.run_adapter([dict(duration=10, snapshot=response)], memory={})
        self.assertEqual(first['outputs'][0]['status'], 'PARTIAL')
        blocked = self.run_adapter([], memory=first['memory'])
        self.assertEqual(blocked['calls'], [])
        self.assertIn('pending page', blocked['error'])

    def test_pages_fill_budget_and_preserve_unicode_escaping(self):
        harness = r'''
const input=JSON.parse(require('fs').readFileSync(0,'utf8'));
const Async=Object.getPrototypeOf(async function(){}).constructor;
(async()=>{for(const raw of input.samples){
 const mem=new Map([['cerRaw',raw]]),load=k=>mem.get(k),store=(k,v)=>mem.set(k,v);
 let pages=[],recovered='',offset=0,last;
 do{await new Async('framingBytes','store','load','text',input.code)(64,store,load,p=>{
   const size=Buffer.byteLength(JSON.stringify(p))+66;
   if(size>4096||p.offset!==offset)throw Error('size or offset');
   if(p.total!==JSON.stringify(raw).length)throw Error('missing total');
   if(p.next!==null&&size<4080)throw Error('page underfilled');
   recovered+=p.data;offset+=p.data.length;last=p;pages.push(size);
 });if(pages.length>200)throw Error('no progress');}while(last.next!==null);
 if(JSON.stringify(JSON.parse(recovered))!==JSON.stringify(raw))throw Error('evidence changed');
 if(load('cerPending')!==false||load('cerPage')!==null)throw Error('not drained');
 if(raw==='x'.repeat(20000)&&pages.length!==6)throw Error('too many pages');
}process.stdout.write('ok');})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        samples = ['x' * 20000, {'report': '证据😀\\\"\r\n' * 4000}, {'empty': ''}]
        p = subprocess.run([shutil.which('node'), '-e', harness],
            input=json.dumps({'code': R['COORDINATION_PAGE_JS'], 'samples': samples}),
            text=True, encoding='utf-8', capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, 'ok')

@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable for adapter replay')
class ExistingThreadExampleTests(unittest.TestCase):
    def test_shipped_thread_example_pages_selected_evidence_and_keeps_native_cursors(self):
        source = (ROOT / 'hooks/readonly_reader.py').read_text(encoding='utf-8')
        example = source.split('# ```javascript\n', 1)[1].split('# ```', 1)[0]
        code = '\n'.join(line.removeprefix('# ') for line in example.splitlines())
        original = 'source and failure 证据😀\r\n' * 4000
        harness = r"""
const input=JSON.parse(require('fs').readFileSync(0,'utf8'));
const Async=Object.getPrototypeOf(async function(){}).constructor;
(async()=>{
 const wrap=s=>({content:[{type:'text',text:JSON.stringify(s)}]});
 const failure={type:'commandExecution',id:'bad',status:'failed',exitCode:2,
  output:{text:input.original,truncated:false,originalChars:input.original.length}};
 const final={type:'agentMessage',id:'final',phase:'final_answer',text:'最终证据😀'.repeat(800)};
 const requiredItemIds=[...Array.from({length:20},(_,i)=>'ok'+i),'bad','final'];
 const snapshot=(id,cursor)=>({schemaVersion:1,thread:{id:'worker',status:{type:'idle'},futureThread:{evidence:'retain'}},
  futureTop:{evidence:'retain'},page:{order:'newest_first',limit:1,nextCursor:cursor,hasMore:cursor!==null},
  turns:[{id,status:'completed',error:null,futureTurn:{evidence:'retain'},items:[
   ...Array.from({length:1200},(_,i)=>({type:'agentMessage',id:'comment'+i,phase:'commentary',text:'old context'.repeat(100)})),
   ...Array.from({length:20},(_,i)=>({type:'commandExecution',id:'ok'+i,status:'completed',exitCode:0,
    futureItem:{evidence:'retain'},output:{text:i===0?input.original:i===1?'actual source diff':i===2?'Ran 3 tests; OK':'successful evidence '+i,
     truncated:false,originalChars:i===0?input.original.length:40}})),failure,final]}]});
 const server=(s,cap)=>{const copy=JSON.parse(JSON.stringify(s));for(const t of copy.turns)for(const i of t.items){
  if(i.output&&i.output.text.length>cap)i.output={...i.output,text:i.output.text.slice(0,cap),truncated:true,originalChars:i.output.text.length};
 }return wrap(copy);};
 const first=server(snapshot('t2','older-page'),1800),second=server(snapshot('t1',null),1800);
 const mem=new Map(),load=k=>mem.get(k),store=(k,v)=>mem.set(k,v),calls=[];
 let outputs=[];
 const text=v=>{const n=Buffer.byteLength(JSON.stringify(v))+66;if(n>4096)throw Error('native truncation risk');outputs.push(v);};
 const baseline='const r=await tools.mcp__codex_app__read_thread({threadId,cursor,turnLimit:1,includeOutputs:true,maxOutputCharsPerItem:1800});text(r);';
 let beforeOverflows=0;
 for(const raw of [first,second]){try{await new Async('tools','threadId','cursor','text',baseline)(
  {mcp__codex_app__read_thread:async()=>raw},'worker',undefined,text);}catch(e){if(e.message!=='native truncation risk')throw e;beforeOverflows++;}}
 if(beforeOverflows!==2)throw Error('baseline did not reproduce whole-result overflow');
 const run=new Async('tools','threadId','cursor','requiredItemIds','load','store','text',input.code);
 const drain=async()=>{
  let recovered='',last,offset=0,pageCount=0,pageBytes=0,maxPageBytes=0;
  do{await new Async('framingBytes','load','store','text',input.page)(64,load,store,p=>{
   const n=Buffer.byteLength(JSON.stringify(p))+66;
   if(n>4096||p.offset!==offset)throw Error('size/offset');
   maxPageBytes=Math.max(maxPageBytes,n);pageBytes+=n;
   recovered+=p.data;offset+=p.data.length;last=p;
  });if(++pageCount>1000)throw Error('no progress');}while(last.next!==null);
  if(load('cerPending')!==false||load('cerPage')!==null)throw Error('not drained');
  return {value:JSON.parse(recovered),pages:pageCount,pageBytes,maxPageBytes};
 };
 const tools={mcp__codex_app__read_thread:async args=>{calls.push(args);return calls.length===1?first:second;}};
 await run(tools,'worker',undefined,requiredItemIds,load,store,text);
 if(outputs.length!==1||outputs[0].status!=='PARTIAL')throw Error('raw result emitted');
 let blocked=false;try{await run(tools,'worker',undefined,requiredItemIds,load,store,text);}catch(e){blocked=e.message==='pending page';}
 if(!blocked||calls.length!==1)throw Error('pending evidence reread');
 const firstReplay=await drain(),selected=firstReplay.value,turn=selected.snapshot.turns[0];
 const originalFirst=JSON.parse(first.content[0].text);
 if(selected.selection.availableItems!==1222||turn.items.length!==22)throw Error('counts lost');
 const required=originalFirst.turns[0].items.filter(i=>requiredItemIds.includes(i.id));
 if(JSON.stringify(turn.items)!==JSON.stringify(required))throw Error('successful source/diff/test or failure/final evidence lost');
 if(turn.items.filter(i=>i.type==='commandExecution').some((i,n)=>i.exitCode!==(n===20?2:0)))throw Error('exit lost');
 if(selected.selection.status!=='PARTIAL'||selected.selection.missing.length||JSON.stringify(selected.selection.truncated)!==JSON.stringify(['ok0','bad']))throw Error('missing evidence hidden');
 if(turn.items[0].output.text.length!==1800||turn.items[0].output.text===input.original||turn.items[0].output.originalChars!==input.original.length)throw Error('server cap not modeled');
 if(JSON.stringify(selected.snapshot.futureTop)!==JSON.stringify(originalFirst.futureTop)||
  JSON.stringify(selected.snapshot.thread)!==JSON.stringify(originalFirst.thread)||JSON.stringify(turn.futureTurn)!==JSON.stringify(originalFirst.turns[0].futureTurn))throw Error('unknown nested evidence lost');
 await run(tools,'worker',selected.snapshot.page.nextCursor,requiredItemIds,load,store,text);
 const secondReplay=await drain(),older=secondReplay.value;
 if(calls.length!==2||calls[1].cursor!=='older-page'||older.snapshot.turns[0].id!=='t1'||older.snapshot.page.hasMore!==false)throw Error('sequential page request');
 const actual=snapshot('native-shape',null),all=actual.turns[0].items;
 const nonempty={type:'reasoning',id:'reasoning-evidence',summary:['required evidence'],content:['retain actual reasoning content']};
 actual.turns[0].items=[{type:'reasoning',id:'empty0',summary:[],content:[]},all[1200],
  {type:'reasoning',id:'empty1',summary:[],content:[]},all[1201],
  {type:'reasoning',id:'empty2',summary:[],content:[]},all[1202],nonempty,all[1220],all[1221]];
 const actualRaw=server(actual,1800),actualIds=['ok0','ok1','ok2','reasoning-evidence','bad','final'];
 await run({mcp__codex_app__read_thread:async()=>actualRaw},'worker',undefined,actualIds,load,store,text);
 const actualReplay=await drain(),actualItems=JSON.parse(actualRaw.content[0].text).turns[0].items.filter(i=>actualIds.includes(i.id));
 if(JSON.stringify(actualReplay.value.snapshot.turns[0].items)!==JSON.stringify(actualItems)||
  actualReplay.value.selection.availableItems!==9||actualReplay.value.selection.status!=='PARTIAL')throw Error('actual reasoning/content/source/diff/test shape lost');
 const unknownItem=JSON.parse(first.content[0].text);unknownItem.turns[0].items[0].futureEvidence={data:'unknown commentary field'};
 const unselected=JSON.parse(first.content[0].text);unselected.turns[0].items.push({type:'commandExecution',id:'unrequested',status:'completed',exitCode:0,output:{text:'new source evidence'}});
 const unselectedReasoning=JSON.parse(first.content[0].text);unselectedReasoning.turns[0].items.push(nonempty);
 const unknownReasoning=JSON.parse(first.content[0].text);unknownReasoning.turns[0].items.push({type:'reasoning',id:'unknown-reasoning',summary:[],content:[],futureEvidence:'retain'});
 const errors=[['nativeError',{isError:true,content:[{type:'text',text:'native error 证据'.repeat(800)}]}],
  ['malformedJSON',{content:[{type:'text',text:'malformed native JSON'}]}],
  ['extraContent',{content:[...first.content,{type:'text',text:'extra evidence'}]}],
  ['schemaVersion',wrap({...originalFirst,schemaVersion:2})],['missingCursor',wrap({...originalFirst,page:{hasMore:true}})],
  ['unknownNestedItem',wrap(unknownItem)],['unselectedSuccessfulEvidence',wrap(unselected)],
  ['unselectedNonemptyReasoning',wrap(unselectedReasoning)],['unknownReasoningField',wrap(unknownReasoning)]],recoveries=[];
 const codeBytes=Buffer.byteLength(input.code),pageCodeBytes=Buffer.byteLength(input.page),markerBytes=Buffer.byteLength(JSON.stringify(outputs[0]))+66;
 for(const [name,raw] of errors){
  await run({mcp__codex_app__read_thread:async()=>raw},'worker',undefined,requiredItemIds,load,store,text);
  const replay=await drain();
  if(JSON.stringify(replay.value)!==JSON.stringify(raw))throw Error('native error/schema evidence discarded');
  const {value,...metrics}=replay;
  recoveries.push({name,beforeBytes:Buffer.byteLength(JSON.stringify(raw))+66,...metrics,
   totalBytes:codeBytes+pageCodeBytes*metrics.pages+metrics.pageBytes+markerBytes});
 }
 await run({mcp__codex_app__read_thread:async()=>first},'worker',undefined,[...requiredItemIds,'missing-id'],load,store,text);
 const missing=await drain();if(missing.value.selection.status!=='PARTIAL'||missing.value.selection.missing[0]!=='missing-id')throw Error('missing item accepted');
 const pages=firstReplay.pages+secondReplay.pages,pageBytes=firstReplay.pageBytes+secondReplay.pageBytes;
 const beforeResultBytes=[first,second].reduce((n,r)=>n+Buffer.byteLength(JSON.stringify(r))+66,0);
 process.stdout.write(JSON.stringify({principal:{beforeResultBytes,beforeTotalBytes:beforeResultBytes+Buffer.byteLength(baseline)*2,
  selectedBytes:Buffer.byteLength(JSON.stringify(selected))+Buffer.byteLength(JSON.stringify(older)),pages,pageBytes,
  codeBytes:codeBytes*2+pageCodeBytes*pages,totalBytes:codeBytes*2+pageCodeBytes*pages+pageBytes+markerBytes*2,
  maxPageBytes:Math.max(firstReplay.maxPageBytes,secondReplay.maxPageBytes),nativeCalls:calls.length,beforeOverflows},
  actualShape:{beforeResultBytes:Buffer.byteLength(JSON.stringify(actualRaw))+66,
   beforeTotalBytes:Buffer.byteLength(JSON.stringify(actualRaw))+66+Buffer.byteLength(baseline),
   codeBytes:codeBytes+pageCodeBytes*actualReplay.pages,pageBytes:actualReplay.pageBytes,pages:actualReplay.pages,
   totalBytes:codeBytes+pageCodeBytes*actualReplay.pages+actualReplay.pageBytes+markerBytes,maxPageBytes:actualReplay.maxPageBytes},recoveries}));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        p = subprocess.run([shutil.which('node'), '-e', harness],
            input=json.dumps({'code': code, 'page': R['COORDINATION_PAGE_JS'], 'original': original}),
            text=True, encoding='utf-8', capture_output=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.measurements = json.loads(p.stdout)
        principal = self.measurements['principal']
        self.assertLess(principal['totalBytes'], principal['beforeTotalBytes'])
        self.assertLessEqual(principal['maxPageBytes'], 4096)
        self.assertEqual(principal['nativeCalls'], 2)
        self.assertEqual(principal['beforeOverflows'], 2)
        self.assertLessEqual(self.measurements['actualShape']['maxPageBytes'], 4096)
        self.assertEqual(len(self.measurements['recoveries']), 9)
        for recovery in self.measurements['recoveries']:
            self.assertLessEqual(recovery['maxPageBytes'], 4096)
        # The server-limited snapshot cannot recover these bytes. Use the known
        # original artifact through the existing Reader, not another thread cursor.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'original.txt').write_bytes(original.encode('utf-8'))
            request = {'op': 'page', 'path': 'original.txt'}
            parts, page_bytes = [], []
            while True:
                raw = R['run'](root, request)
                self.assertLessEqual(len(raw.encode('utf-8')) + 2, 4096)
                page = json.loads(raw)
                parts.append(page['data'])
                page_bytes.append(len(raw.encode('utf-8')) + 2)
                if page['next_cursor'] is None:
                    break
                request = {**request, 'cursor': page['next_cursor']}
            self.assertEqual(''.join(parts), original)
            self.measurements['originalArtifact'] = {'bytes': len(original.encode('utf-8')),
                'pages': len(parts), 'pageBytes': sum(page_bytes), 'maxPageBytes': max(page_bytes)}


class ExistingReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.path = self.root / 'source.txt'

    def test_batched_required_rules_continue_without_losing_content(self):
        pending = []
        expected = {}
        actual = {}
        for index in range(3):
            name = f'rules-{index}.md'
            data = ((f'{index}: 必读规则 "\\"\r\n' * 240) + 'END\r\n').encode('utf-8')
            (self.root / name).write_bytes(data)
            expected[name] = hashlib.sha256(data).hexdigest()
            actual[name] = hashlib.sha256()
            pending.append({'op':'page','path':name})
        for _ in range(100):
            raw = R['run'](self.root, {'op':'batch','requests':pending,
                'max_bytes':4096,'framing_bytes':128})
            self.assertLessEqual(len(raw.encode('utf-8')) + 2 + 128, 4096)
            page = json.loads(raw)
            following = []
            for request, row in zip(pending, page['results']):
                actual[request['path']].update(row['data'].encode('utf-8'))
                if row['next_cursor'] is not None:
                    following.append({**request,'cursor':row['next_cursor']})
            self.assertEqual(len(page['results']), len(pending))
            self.assertEqual(page['status'], 'PARTIAL' if following else 'COMPLETE')
            pending = following
            if not pending:
                break
        else:
            self.fail('required-rule continuation did not finish')
        self.assertEqual({name:value.hexdigest() for name,value in actual.items()}, expected)

    def test_test_result_projection_keeps_both_exits_and_failure_cursor(self):
        # Representative captured-result data, not a claim about a live model run.
        red = {'exit':1,'tests':199,'failures':5,'errors':0}
        green = {'exit':0,'tests':198,'failures':0,'errors':0}
        detail = 'assertion failed: expected retained owner\n' * 200
        source = {'red':{'summary':red,'details':detail},
                  'green':{'summary':green},'verbose_log':'noise\n' * 10000}
        self.path.write_text(json.dumps(source), encoding='utf-8')
        requests = [{'op':'json','path':'source.txt','pointer':pointer}
                    for pointer in ('/red/summary','/green/summary','/red/details')]
        raw = R['run'](self.root, {'op':'batch','requests':requests,
            'max_bytes':4096,'framing_bytes':128})
        self.assertLessEqual(len(raw.encode('utf-8')) + 2 + 128, 4096)
        page = json.loads(raw)
        self.assertEqual([json.loads(row['data']) for row in page['results'][:2]], [red,green])
        self.assertEqual(page['status'], 'PARTIAL')
        row = page['results'][2]
        self.assertIsNotNone(row['next_cursor'])
        parts = [row['data']]
        while row['next_cursor'] is not None:
            raw = R['run'](self.root, {**requests[2],'cursor':row['next_cursor']})
            self.assertLessEqual(len(raw.encode('utf-8')) + 2, 4096)
            row = json.loads(raw)
            parts.append(row['data'])
        self.assertEqual(json.loads(''.join(parts)), detail)

    def test_large_file_serialization_is_page_bounded(self):
        self.path.write_text('a' * (2 * 1024 * 1024), encoding='utf-8')
        original = R['envelope']
        lengths = []
        def tracked(value, cap):
            lengths.append(len(value.get('data', '')))
            return original(value, cap)
        with patch.dict(R['indexed_page'].__globals__, envelope=tracked):
            result = json.loads(R['run'](self.root, {'op':'page','path':'source.txt'}))
        self.assertTrue(result['data'])
        self.assertIsNotNone(result['next_cursor'])
        self.assertLessEqual(max(lengths), 4096)

    def test_unicode_and_crlf_pages_reconstruct_exactly(self):
        text = 'header\r\n' + ('中😀\\\"\t\r\n' * 140) + 'tail\r\n'
        self.path.write_bytes(text.encode('utf-8'))
        for cap in (1024, 2048, 4096):
            req = {'op':'page','path':'source.txt','max_bytes':cap}
            parts=[]
            for _ in range(100):
                raw=R['run'](self.root,req)
                self.assertLessEqual(len(raw.encode('utf-8'))+2,cap)
                page=json.loads(raw);parts.append(page['data'])
                if page['next_cursor'] is None: break
                req={**req,'cursor':page['next_cursor']}
            else: self.fail('no pagination progress')
            self.assertEqual(''.join(parts), text)

    def test_excerpt_continuation_keeps_original_range(self):
        self.path.write_bytes(('before\n' + 'x' * 6000 + '\nafter\n').encode())
        first=json.loads(R['run'](self.root,{'op':'excerpt','path':'source.txt','start':2,'lines':1}))
        data=first['data']; cursor=first['next_cursor']
        while cursor:
            result=json.loads(R['run'](self.root,{'op':'page','path':'source.txt','cursor':cursor}))
            data+=result['data'];cursor=result['next_cursor']
        self.assertEqual(data,'x'*6000+'\n')

    def test_stale_cursor_and_invalid_utf8_remain_rejected(self):
        self.path.write_text('x'*8000,encoding='utf-8')
        first=json.loads(R['run'](self.root,{'op':'page','path':'source.txt'}))
        self.path.write_text('y'*8000,encoding='utf-8')
        with self.assertRaises(ValueError):
            R['run'](self.root,{'op':'page','path':'source.txt','cursor':first['next_cursor']})
        self.path.write_bytes(b'\xff')
        with self.assertRaises(UnicodeError):
            R['run'](self.root,{'op':'page','path':'source.txt'})

if __name__ == '__main__':
    unittest.main()
