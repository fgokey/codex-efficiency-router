# Regression coverage for existing wait/read paths; no model calls.
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

class ExistingReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.path = self.root / 'source.txt'

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
