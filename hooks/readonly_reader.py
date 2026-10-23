"""Bounded read-only adapter. Batches preflight in full; no arbitrary commands.

Limits are byte limits, not character counts. Local trusted filesystem only: this
is not protection against a malicious process racing a validated path.
"""
from __future__ import annotations
import base64
import binascii
import codecs
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import threading

VERSION = '0.8.5'
LIMIT = 131072
INPUT_LIMIT = 16384
READ_LIMIT = 16 * 1024 * 1024
JSON_SCAN_LIMIT = 256 * 1024 * 1024
JSON_CHUNK = 64 * 1024
JSON_DEPTH = 64
JSON_KEY_BYTES = 16 * 1024
JSON_MEMBER_LIMIT = 16384
JSON_KEYS_BYTES = 1024 * 1024
BATCH_LIMIT = 16
OPS = frozenset(('read', 'list', 'search', 'diff', 'status', 'index', 'page', 'excerpt', 'locate', 'json'))
LEGACY_OPS = frozenset(('read', 'list', 'search', 'diff', 'status'))
PAGE_BYTES = 4096
EXCLUDED_DIRS = ('.git', 'node_modules', 'dist', 'build', '.next', 'temp')
# Copy COORDINATION_JS into functions.exec for short/dense work; supply targets,
# framingBytes and parentReady. parentReady=true is a caller contract: finish all
# available substantive parent code/evidence/test-applicability work first, and
# review each actionable child turn/error/final result before passive waiting.
# Bind that declaration to the current evidence, never an old worker-ID receipt.
# This is not native proof of work/review. False readiness returns WORK, no wait.
# Merge ALL relevant live targets (native max eight) into one call. Resolve/retire
# target-specific errors only after review; omitted targets are caller decisions.
# Reuse explicit cursors. For prolonged quiet work, opt into ADAPTIVE after two
# unchanged snapshots (seed store("cerIdle",2) when switching); it reuses per-target
# cursors, omits unchanged detail and
# extends 50s waits to 60s, preserving native async wake/error/completion. New
# substantive state resets backoff; commentary/tools alone do not. Host support
# for 60s is required; UNKNOWN is a gap, never bypass an actual host restriction.
# Raw MCP results stay in cerRaw. On overflow/schema failure use PAGE, draining
# every next offset before any new wait. Stored values are data, never code.
# Rows: id,cursor,threadStatus,turnId,turnStatus,error,failedMarker,finalMessageId,changed,finalText.
# Detect revised final text even when the message ID is reused.
COORDINATION_JS = r'''
let b=framingBytes;
if(!Number.isInteger(b)||b<0||b>3900)throw Error("unknown framing");
if(load("cerPending"))throw Error("pending page");
if(parentReady!==true)text({action:"WORK"});else{
const r=await tools.mcp__codex_app__wait_threads({targets,timeoutMs:50000});store("cerRaw",r);store("cerPending",true);
let s;try{s=JSON.parse(r.content.find(c=>c.type==="text").text);let old=load("cerWait")||{};
s.polls=s.polls.map(p=>{
let id=p.thread.id,t=p.latestTurn,m=p.latestAssistantMessage,f=p.latestToolMarker;
let a=[p.thread.status,t.id,t.status,t.error,["failed","error"].includes(f?.status)?f:null,m?.phase==="final_answer"?m.id:null];
let k=JSON.stringify(a[5]?[a,m.text]:a),delta=old[id]!==k;old[id]=k;
return [id,p.cursor,...a,delta,a[5]?m.text:null];
});store("cerWait",old);}catch{s=null;}
if(s&&encodeURIComponent(JSON.stringify(s)).replace(/%[0-9A-F]{2}/g,"x").length+2+b<=4096){store("cerPending",false);text(s);}
else text({status:"PARTIAL",detail:"COORDINATION_PAGE_JS"});
}
'''

# Optional quiet-work variant, derived from the same transport rather than a
# second review protocol. Copy the evaluated string; no executable-code storage.
COORDINATION_ADAPTIVE_JS = COORDINATION_JS.replace(
    'const r=await', 'const cursors=load("cerCursors")||{};const r=await').replace(
    '{targets,timeoutMs:50000}',
    '{targets:targets.map(t=>({...t,afterCursor:t.afterCursor||cursors[t.threadId]})),timeoutMs:load("cerIdle")>=2?60000:50000}').replace(
    '});store("cerWait",old);',
    '});store("cerWait",old);store("cerIdle",s.polls.some(p=>p[8])||s.errors?.length?0:(load("cerIdle")||0)+1);'
    'for(const p of s.polls)cursors[p[0]]=p[1];store("cerCursors",cursors);'
    'let n=s.polls.length;s.polls=s.polls.filter(p=>p[8]||p[5]||p[6]);s.unchanged=n-s.polls.length;')

# Bounded default for quiet work on hosts advertising the required Code Mode
# yield and native wait fields. Reuses the tested projection/pagination above.
# Keep the pragma FIRST; insert caller declarations immediately after it. caps
# are observed tool limits, not permission or identity evidence. Only waiting is
# batched; no task dispatch, write, acceptance decision or permission retry here.
COORDINATION_QUIET_JS = r'''// @exec: {"yield_time_ms": 120000, "max_output_tokens": 4096}
if(parentReady!==true)text({action:"WORK"});else{
if(typeof waitCapabilities!=="object"||waitCapabilities===null||
 !Number.isSafeInteger(waitCapabilities.execYieldMs)||waitCapabilities.execYieldMs<120000||
 !Number.isSafeInteger(waitCapabilities.nativeTimeoutMs)||waitCapabilities.nativeTimeoutMs<50000)
 throw Error("quiet wait needs observed exec yield 120000 and native timeout 50000; use supported native wait");
if(!Array.isArray(targets)||!targets.length||targets.length>8||
 targets.some(t=>!t||typeof t.threadId!=="string"||!t.threadId||t.threadId.length>128||
 Object.keys(t).some(k=>!["threadId","afterCursor"].includes(k))||
 t.afterCursor!==undefined&&(typeof t.afterCursor!=="string"||!t.afterCursor))||
 new Set(targets.map(t=>t.threadId)).size!==targets.length)throw Error("invalid wait targets");
let current=targets.map(t=>({...t})),out,shape=true,started=Date.now();
const once=async(tools,targets,text)=>{
''' + COORDINATION_ADAPTIVE_JS + r'''
};
for(let n=0;n<2;n++){
 if(n&&Date.now()-started>60000)break;
 const before=Date.now();
 const wrapped={mcp__codex_app__wait_threads:async args=>{
  const r=await tools.mcp__codex_app__wait_threads({...args,timeoutMs:50000});
  try{
   if(r.isError||!Array.isArray(r.content)||r.content.length!==1||r.content[0].type!=="text")throw Error("result");
   const s=JSON.parse(r.content[0].text),ids=new Set();
   if(!s||Object.keys(s).some(k=>!["timedOut","wake","polls","errors"].includes(k))||
    !Array.isArray(s.polls)||typeof s.timedOut!=="boolean"||
    s.errors!==undefined&&!Array.isArray(s.errors))throw Error("schema");
   for(const p of s.polls){
    const id=p?.thread?.id;
    if(!current.some(t=>t.threadId===id)||ids.has(id)||typeof p.cursor!=="string"||!p.cursor||
     !p.latestTurn||typeof p.latestTurn.id!=="string"||
     !["inProgress","completed","failed","interrupted"].includes(p.latestTurn.status))throw Error("row");
    ids.add(id);
   }
   if(!s.errors?.length&&ids.size!==current.length)throw Error("missing target");
  }catch{shape=false;}
  return r;
 }};
 await once(wrapped,current,v=>{out=v;});
 if(!shape){store("cerPending",true);out={status:"PARTIAL",detail:"COORDINATION_PAGE_JS"};}
 if(!shape||out.status==="PARTIAL"||out.action||out.polls?.length||out.errors?.length||
  out.wake||out.timedOut!==true||Date.now()-before<48000||Date.now()-started>=100000)break;
 // Do not resend the caller's initial cursor on the next native wait.
 current=current.map(t=>({threadId:t.threadId}));
}
text(out);
}
'''

# Explicit data pagination only, also recovers the original result after schema errors.
COORDINATION_PAGE_JS = r'''
if(!Number.isInteger(framingBytes)||framingBytes<0)throw Error("unknown framing");
let raw=load("cerPage"),offset=load("cerOffset")||0;
if(!raw){raw=JSON.stringify(load("cerRaw"));if(!raw)throw Error("missing snapshot");offset=0;}
if(typeof raw!=="string"||!Number.isSafeInteger(offset)||offset<0||offset>raw.length)throw Error("invalid page state");
const make=end=>({status:end<raw.length?"PARTIAL":"PASS",offset,next:end<raw.length?end:null,data:raw.slice(offset,end)});
const fits=p=>encodeURIComponent(JSON.stringify(p)).replace(/%[0-9A-F]{2}/g,"x").length+2+framingBytes<=4096;
let end=offset,page=null;
if(raw.length-offset<=4096){const p=make(raw.length);if(fits(p)){page=p;end=raw.length;}}
if(!page){let lo=offset+1,hi=Math.min(raw.length-1,offset+4096);
while(lo<=hi){const mid=lo+Math.floor((hi-lo)/2),p=make(mid);
if(fits(p)){page=p;end=mid;lo=mid+1;}else hi=mid-1;}}
if(!page)throw Error("framing exceeds page budget");
store("cerPage",end===raw.length?null:raw);store("cerOffset",end);store("cerPending",end<raw.length);text(page);
'''

HELP = """CER read (UTF-8; each JSON response <=4096 bytes including CRLF)
  batch --root ABS --requests JSON_ARRAY --max-bytes N --framing-bytes N
    Independent requests; full path/schema preflight before capture, one JSON results envelope.
    Total JSON+CRLF+explicit outer framing <=max-bytes; shares budget within member upper caps.
    Per-item ERROR retains other results; PARTIAL means errors, incomplete evidence or cursors.
    ERROR request_index is 1-based; path_omitted/error_truncated explicitly mark reductions.
    Preserve each continuation separately. Legacy encoded batches retain text/restrictions.
    Example: batch --root ABS --requests '[{"op":"page","path":"a.txt"},{"op":"page","path":"b.txt"}]' --max-bytes 3072 --framing-bytes 256
    Declare actual host framing; the example's 256 is not a host measurement.
    Budget too small for member metadata: narrow batch. Retry only failed/pending items.
    PowerShell: pipe UTF-8 JSON_ARRAY to --requests -; avoids native argument quote removal.
    ROOT BASE64_URLSAFE_JSON also accepts the batch object; padding is optional.
    Use physical roots/paths; symlink and reparse checks remain strict.
  read|search|list|diff|status --root ABS --path PATH [--cursor TOKEN] [--max-bytes N]
    Pages retain selected-request semantics; read/search keep line numbers. search needs --query.
    Git capture <=128 KiB; PARTIAL means narrow scope. Encoded small legacy results stay text;
    larger results return JSON pages. Encoded batches fit 4096 bytes incl frames/CRLF or fail.
  json --root ABS --path RELFILE --pointer POINTER [--mode value|members] [--cursor TOKEN]
    String-form JSON Pointer; value returns exact JSON text pages, members lists direct children.
    Every page validates/hashes the whole source (<=256 MiB), using 64 KiB reads; no DOM/cache.
    Depth <=64, keys <=16 KiB; member directories <=16384 keys/1 MiB decoded keys.
    Continue with the same pointer/mode and cursor; check exit before parsing output.
  excerpt --root ABS --path RELFILE --start N --lines N [--max-bytes N]
    One snapshot, first bounded page of lines N..N+lines-1 (lines 1..200).
    Continue with page --root ABS --path RELFILE --cursor TOKEN if next_cursor is not null.
  locate --root ABS --path RELDIR_OR_FILE --query LITERAL [--glob FILE_GLOB] [--max-bytes N]
    Literal rg search; returns path/line candidates only. complete applies to the chosen
    path/glob under rg default ignore/hidden rules and 16 MiB max file size,
    excluding .git,node_modules,dist,build,.next,temp. PARTIAL means narrow scope.
  index --root ABS --path RELFILE [--start N --lines N] [--max-bytes N]
    Returns cursor, size and SHA; omit range for complete rules/full-file reads.
  page --root ABS --path RELFILE [--cursor TOKEN] [--max-bytes N]
    Omit cursor for the first full-file page. Continue until next_cursor is null;
    rejects changed files or stale cursors.
Paths are literal and relative to ABS. max-bytes is 256..4096, default 4096.
Use a verified Python executable with -I -B and this script for repeated reads.
"""


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non-finite JSON value')


def validate(request: object) -> dict:
    if not isinstance(request, dict):
        raise ValueError('reader request must be an object')
    if len(json.dumps(request, ensure_ascii=True, allow_nan=False).encode()) > INPUT_LIMIT:
        raise ValueError('reader input exceeds 16 KiB')
    op = request.get('op')
    if op == 'batch':
        structured = 'framing_bytes' in request or 'max_bytes' in request
        fields = {'op', 'requests', 'max_bytes', 'framing_bytes'} if structured else {'op', 'requests'}
        if set(request) != fields:
            raise ValueError('batch requires op/requests; JSON batch also needs max_bytes/framing_bytes')
        if structured:
            cap, framing = request['max_bytes'], request['framing_bytes']
            if (type(cap) is not int or not 256 <= cap <= PAGE_BYTES
                    or type(framing) is not int or framing < 0 or cap - framing < 256):
                raise ValueError('batch needs max_bytes 256..4096 and known framing leaving >=256 bytes')
        items = request['requests']
        if not isinstance(items, list) or not 1 <= len(items) <= BATCH_LIMIT:
            raise ValueError('batch requires 1..16 operations')
        seen = set()
        for item in items:
            if not isinstance(item, dict) or item.get('op') == 'batch':
                raise ValueError('nested batches are not supported')
            if not structured and item.get('op') in ('index', 'page', 'excerpt', 'locate', 'json'):
                raise ValueError('index/page/excerpt/locate/json cannot be batched')
            if not structured and ('cursor' in item or 'max_bytes' in item):
                raise ValueError('batch members cannot request pages; split batch')
            validate(item)
            if structured:
                key = json.dumps(item, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
                if key in seen: raise ValueError('duplicate batch request; reuse its result')
                seen.add(key)
        return request
    if not isinstance(op, str) or op not in OPS:
        raise ValueError('reader needs read/list/search/diff/status/index/page/excerpt/locate/json or batch')
    fields = {'op', 'path'} | {
        'read': {'start', 'lines', 'cursor', 'max_bytes'},
        'search': {'query', 'lines', 'cursor', 'max_bytes'},
        'diff': {'staged', 'cursor', 'max_bytes'},
        'status': {'cursor', 'max_bytes'}, 'list': {'cursor', 'max_bytes'},
        'index': {'max_bytes', 'start', 'lines'}, 'page': {'max_bytes', 'cursor'},
        'excerpt': {'max_bytes', 'start', 'lines'},
        'locate': {'max_bytes', 'query', 'glob'},
        'json': {'max_bytes', 'pointer', 'mode', 'cursor'},
    }[op]
    if set(request) - fields:
        raise ValueError('unknown reader field')
    path = request.get('path', '.')
    if not isinstance(path, str) or any(c in path for c in '\x00\r\n'):
        raise ValueError('invalid path')
    if op in ('index', 'page', 'excerpt', 'locate', 'json'):
        if ('path' not in request or not path or Path(path).is_absolute() or '\\' in path
                or ':' in path or any(c in path for c in '*?[]')
                or (path != '.' and any(part in ('', '.', '..') for part in path.split('/')))):
            raise ValueError('reader CLI requires one literal relative path')
        if op != 'locate' and path == '.':
            raise ValueError('file reads require a literal relative file path')
        if op == 'locate' and (len(path.encode('utf-8')) > 1024
                               or any(part in EXCLUDED_DIRS for part in path.split('/'))):
            raise ValueError('locate path is too long or excluded')
    for key, default in (('start', 1), ('lines', 120)):
        value = request.get(key, default)
        if type(value) is not int or value < 1 or (key == 'lines' and value > 200):
            limit = 'an integer >=1' if key == 'start' else 'an integer in 1..200'
            raise ValueError(f'{key} must be {limit}; use page for a full file, '
                             'or locate before excerpt with current line numbers')
    if op == 'search' and (not isinstance(request.get('query'), str) or not request['query']):
        raise ValueError('search requires a nonempty literal query')
    if type(request.get('staged', False)) is not bool:
        raise ValueError('staged must be boolean')
    if op in OPS:
        cap = request.get('max_bytes', PAGE_BYTES)
        if type(cap) is not int or not 256 <= cap <= PAGE_BYTES:
            raise ValueError('max_bytes must be 256..4096')
        if op in LEGACY_OPS | {'page', 'json'} and 'cursor' in request and (not isinstance(request['cursor'], str)
                                                   or not request['cursor']):
            raise ValueError('page cursor must be a nonempty string')
        if op == 'index' and ('lines' in request) != ('start' in request):
            raise ValueError('index range requires both start and lines')
        if op == 'excerpt' and not {'start', 'lines'} <= set(request):
            raise ValueError('excerpt requires start and lines')
        if op == 'locate':
            query = request.get('query')
            if not isinstance(query, str) or not query or any(c in query for c in '\x00\r\n'):
                raise ValueError('locate requires one nonempty line of literal query')
            glob = request.get('glob')
            if glob is not None and (not isinstance(glob, str) or not glob
                                     or len(glob.encode('utf-8')) > 256
                                     or any(c in glob for c in '\x00\r\n')):
                raise ValueError('invalid locate glob')
        if op == 'json':
            pointer_parts(request.get('pointer'))
            if request.get('mode', 'value') not in ('value', 'members'):
                raise ValueError('json mode must be value or members')
    return request


def reject_link(path: Path) -> None:
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError('reader refuses symlinks')
        if item.exists() and getattr(item.lstat(), 'st_file_attributes', 0) & 0x400:
            raise ValueError('reader refuses reparse points/junctions')


def resolve(root: Path, value: str) -> Path:
    candidate = root / value
    reject_link(candidate)
    path = candidate.resolve()
    if not path.is_relative_to(root):
        raise ValueError('path outside hook workspace')
    return path


def preflight(root: Path, request: dict) -> list[tuple[dict, Path]]:
    validate(request)
    reject_link(root)
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('workspace must be a directory')
    items = request['requests'] if request['op'] == 'batch' else [request]
    total = json_total = 0
    checked = []
    for item in items:
        path = resolve(root, item.get('path', '.'))
        if item['op'] in ('read', 'search', 'index', 'page', 'excerpt'):
            if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
                raise ValueError('read/search require one regular file, not a directory')
            total += path.stat().st_size
            if total > READ_LIMIT:
                raise ValueError('aggregate file read budget exceeds 16 MiB')
        elif item['op'] == 'json':
            if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
                raise ValueError('json requires one regular file')
            json_total += path.stat().st_size
            if json_total > JSON_SCAN_LIMIT:
                raise ValueError('json source exceeds 256 MiB scan budget')
        elif item['op'] == 'locate' and not (path.is_file() or path.is_dir()):
            raise ValueError('locate requires one file or directory')
        elif item['op'] == 'list' and not path.is_dir():
            raise ValueError('list requires a directory')
        checked.append((item, path))
    return checked


def clip(text: str, cap: int = LIMIT) -> str:
    raw = text.encode('utf-8')
    if len(raw) <= cap:
        return text
    marker = b'\n[truncated; request a narrower range]'
    return raw[:max(0, cap - len(marker))].decode('utf-8', errors='ignore') + marker.decode()


def snapshot(root: Path, path: Path) -> tuple[bytes, dict]:
    """Read at most 16 MiB and bind later pages to this exact file snapshot."""
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > READ_LIMIT:
        raise ValueError('page requires a regular UTF-8 file of at most 16 MiB')
    with path.open('rb') as stream:
        raw = stream.read(READ_LIMIT + 1)
    after = path.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')
    if len(raw) > READ_LIMIT or len(raw) != after.st_size or any(
            getattr(before, field) != getattr(after, field) for field in fields):
        raise ValueError('file changed while being read or exceeds 16 MiB')
    identity = {'path': path.relative_to(root).as_posix(), 'size': after.st_size,
                'mtime_ns': after.st_mtime_ns, 'dev': before.st_dev, 'ino': after.st_ino,
                'sha256': hashlib.sha256(raw).hexdigest()}
    return raw, identity


def cursor_token(identity: dict, offset: int, first: int, last: int) -> str:
    state = {**identity, 'offset': offset, 'first': first, 'last': last}
    raw = json.dumps(state, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    state['check'] = hashlib.sha256(raw).hexdigest()[:16]
    token = base64.urlsafe_b64encode(json.dumps(state, sort_keys=True, separators=(',', ':'),
                                                ensure_ascii=True).encode()).rstrip(b'=').decode()
    if len(token) > 2048:
        raise ValueError('file path exceeds supported cursor size')
    return token


def cursor_offset(token: str, identity: dict, length: int) -> tuple[int, int, int]:
    if len(token) > 2048:
        raise ValueError('invalid page cursor')
    try:
        raw = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
        state = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                           parse_constant=reject_constant)
        if not isinstance(state, dict) or set(state) != set(identity) | {'offset', 'first', 'last', 'check'}:
            raise ValueError('invalid page cursor')
        check = state.pop('check')
        source = json.dumps(state, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        if (not isinstance(check, str) or check != hashlib.sha256(source).hexdigest()[:16]
                or any(state[key] != value for key, value in identity.items())
                or any(type(state[key]) is not int for key in ('offset', 'first', 'last'))
                or not 0 <= state['first'] <= state['offset'] <= state['last'] <= length):
            raise ValueError('cursor/file mismatch or invalid offset')
        return state['offset'], state['first'], state['last']
    except (ValueError, UnicodeError, TypeError, KeyError, binascii.Error) as exc:
        raise ValueError('invalid or stale page cursor') from exc


def pointer_parts(pointer: object) -> tuple[str, ...]:
    if not isinstance(pointer, str) or (pointer and not pointer.startswith('/')):
        raise ValueError('json requires a string-form JSON Pointer (empty or starting with /)')
    if re.search(r'~(?![01])', pointer):
        raise ValueError('invalid JSON Pointer escape')
    pointer.encode('utf-8')  # Refuse unpaired surrogate characters in requests.
    return tuple(part.replace('~1', '/').replace('~0', '~') for part in pointer.split('/')[1:])


class JsonScan:
    """Validate one JSON stream while retaining only bounded keys and one member page."""
    special = re.compile(rb'["\\\x00-\x1f]')
    non_digit = re.compile(rb'[^0-9]')
    non_space = re.compile(rb'[^ \r\n\t]')

    def __init__(self, stream, parts: tuple[str, ...], members: bool, position: int):
        self.stream, self.parts, self.members, self.resume = stream, parts, members, position
        self.block = b''; self.at = 0; self.base = 0; self.read_bytes = 0
        self.decoder = codecs.getincrementaldecoder('utf-8')('strict')
        self.sha = hashlib.sha256(); self.eof = False
        self.target = None; self.items = []; self.items_bytes = 0
        self.member_count = 0; self.resume_seen = position == 0

    def position(self) -> int:
        return self.base + self.at

    def peek(self) -> int:
        if self.at == len(self.block) and not self.eof:
            self.base += self.at; self.at = 0
            self.block = self.stream.read(min(JSON_CHUNK, JSON_SCAN_LIMIT + 1 - self.read_bytes))
            self.read_bytes += len(self.block)
            if self.read_bytes > JSON_SCAN_LIMIT:
                raise ValueError('json source grew beyond 256 MiB scan budget')
            self.eof = not self.block
            self.decoder.decode(self.block, final=self.eof)
            self.sha.update(self.block)
        return self.block[self.at] if self.at < len(self.block) else -1

    def take(self) -> int:
        value = self.peek()
        if value < 0: raise ValueError('unexpected end of JSON')
        self.at += 1
        return value

    def expect(self, value: bytes) -> None:
        for byte in value:
            if self.take() != byte: raise ValueError('invalid JSON token')

    def space(self) -> None:
        while self.peek() in (9, 10, 13, 32):
            match = self.non_space.search(self.block, self.at)
            self.at = match.start() if match else len(self.block)

    def digits(self) -> None:
        while 48 <= self.peek() <= 57:
            match = self.non_digit.search(self.block, self.at)
            self.at = match.start() if match else len(self.block)

    def string(self, key: bool = False) -> str | None:
        self.expect(b'"'); raw = bytearray(b'"') if key else None
        def keep(value: bytes) -> None:
            if raw is not None:
                if len(raw) + len(value) > JSON_KEY_BYTES * 6 + 2:
                    raise ValueError('json key exceeds 16 KiB')
                raw.extend(value)
        while True:
            if self.peek() < 0: raise ValueError('unterminated JSON string')
            match = self.special.search(self.block, self.at)
            stop = match.start() if match else len(self.block)
            keep(self.block[self.at:stop]); self.at = stop
            if not match: continue
            byte = self.take(); keep(bytes((byte,)))
            if byte == 34: break
            if byte != 92: raise ValueError('control character in JSON string')
            escaped = self.take(); keep(bytes((escaped,)))
            if escaped in b'"\\/bfnrt': continue
            if escaped != 117: raise ValueError('invalid JSON escape')
            digits = bytes(self.take() for _ in range(4)); keep(digits)
            if any(c not in b'0123456789abcdefABCDEF' for c in digits):
                raise ValueError('invalid JSON unicode escape')
            code = int(digits, 16)
            if 0xD800 <= code <= 0xDBFF:
                self.expect(b'\\u'); keep(b'\\u')
                low = bytes(self.take() for _ in range(4)); keep(low)
                if (any(c not in b'0123456789abcdefABCDEF' for c in low)
                        or not 0xDC00 <= int(low, 16) <= 0xDFFF):
                    raise ValueError('invalid JSON surrogate pair')
            elif 0xDC00 <= code <= 0xDFFF:
                raise ValueError('unpaired JSON surrogate')
        if raw is None: return None
        value = json.loads(raw.decode('utf-8'))
        if len(value.encode('utf-8')) > JSON_KEY_BYTES:
            raise ValueError('json key exceeds 16 KiB')
        return value

    def number(self) -> None:
        if self.peek() == 45: self.at += 1
        if self.peek() == 48: self.at += 1
        elif 49 <= self.peek() <= 57:
            self.digits()
        else: raise ValueError('invalid JSON number')
        if self.peek() == 46:
            self.at += 1
            if not 48 <= self.peek() <= 57: raise ValueError('invalid JSON fraction')
            self.digits()
        if self.peek() in (69, 101):
            self.at += 1
            if self.peek() in (43, 45): self.at += 1
            if not 48 <= self.peek() <= 57: raise ValueError('invalid JSON exponent')
            self.digits()

    def member(self, name: str | int, kind: str, position: int) -> None:
        self.member_count += 1
        if self.member_count > JSON_MEMBER_LIMIT:
            raise ValueError('json members directory exceeds 16384 entries')
        if position == self.resume: self.resume_seen = True
        if position < self.resume or self.items_bytes >= PAGE_BYTES: return
        pointer = '/' + str(name).replace('~', '~0').replace('/', '~1')
        item = {'key' if isinstance(name, str) else 'index': name, 'type': kind,
                'pointer': pointer}
        size = len(json.dumps(item, ensure_ascii=False).encode('utf-8'))
        self.items.append((position, item)); self.items_bytes += size

    def value(self, depth: int, parts: tuple[str, ...] | None) -> tuple[int, int, str]:
        self.space(); start = self.position(); byte = self.peek()
        selected = parts == (); listing = selected and self.members
        if byte in (123, 91):
            if depth >= JSON_DEPTH: raise ValueError('json exceeds depth 64')
            obj = byte == 123; kind = 'object' if obj else 'array'
            close = 125 if obj else 93; self.at += 1; self.space()
            keys = set() if listing and obj else None; keys_bytes = 0
            index = 0; matches = 0
            if parts and not obj and not re.fullmatch(r'0|[1-9][0-9]*', parts[0]):
                raise ValueError('JSON Pointer array index does not exist')
            while self.peek() != close:
                self.space(); position = self.position()
                if obj:
                    name = self.string(True); self.space(); self.expect(b':')
                    if keys is not None:
                        if name in keys: raise ValueError('duplicate JSON member in directory')
                        keys_bytes += len(name.encode('utf-8'))
                        if len(keys) >= JSON_MEMBER_LIMIT or keys_bytes > JSON_KEYS_BYTES:
                            raise ValueError('json members key budget exceeds 16384 keys/1 MiB')
                        keys.add(name)
                else: name = index
                child = None
                if parts and str(name) == parts[0]:
                    matches += 1
                    if matches > 1: raise ValueError('duplicate referenced JSON member')
                    child = parts[1:]
                _, _, child_kind = self.value(depth + 1, child)
                if listing: self.member(name, child_kind, position)
                index += 1; self.space()
                if self.peek() == close: break
                self.expect(b','); self.space()
                if self.peek() == close: raise ValueError('trailing JSON comma')
            self.expect(bytes((close,)))
        elif byte == 34:
            kind = 'string'; self.string()
        elif byte in (45, *range(48, 58)):
            kind = 'number'; self.number()
        elif byte == 116:
            kind = 'boolean'; self.expect(b'true')
        elif byte == 102:
            kind = 'boolean'; self.expect(b'false')
        elif byte == 110:
            kind = 'null'; self.expect(b'null')
        else: raise ValueError('invalid JSON value')
        end = self.position()
        if selected:
            if listing and kind not in ('object', 'array'):
                raise ValueError('json members requires an object or array')
            self.target = (start, end, kind)
            if self.resume in (start, end): self.resume_seen = True
        return start, end, kind


def json_page(root: Path, request: dict, path: Path) -> str:
    cap = request.get('max_bytes', PAGE_BYTES); mode = request.get('mode', 'value')
    pointer = request['pointer']; parts = pointer_parts(pointer); position = 0
    token = request.get('cursor')
    if token:
        # This tentative position cannot produce output until full identity validation below.
        try:
            if len(token) > 2048: raise ValueError('invalid json cursor')
            state = json.loads(base64.b64decode(token + '=' * (-len(token) % 4),
                                              altchars=b'-_', validate=True))
            position = state['offset']
            if type(position) is not int or not 0 <= position <= JSON_SCAN_LIMIT:
                raise ValueError('invalid json cursor position')
        except (ValueError, TypeError, KeyError, binascii.Error) as exc:
            raise ValueError('invalid json cursor') from exc
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > JSON_SCAN_LIMIT:
            raise ValueError('json source exceeds 256 MiB scan budget or is not regular')
        scan = JsonScan(stream, parts, mode == 'members', position)
        scan.value(0, parts); scan.space()
        if scan.peek() != -1: raise ValueError('trailing JSON data')
        if scan.target is None: raise ValueError('JSON Pointer does not exist')
        first, last, kind = scan.target
        identity = {'path': path.relative_to(root).as_posix(), 'size': before.st_size,
                    'mtime_ns': before.st_mtime_ns, 'dev': before.st_dev, 'ino': before.st_ino,
                    'sha256': scan.sha.hexdigest(), 'op': 'json', 'mode': mode, 'pointer': pointer}
        if token:
            position, bound_first, bound_last = cursor_offset(token, identity, before.st_size)
            if (bound_first, bound_last) != (first, last): raise ValueError('json cursor span mismatch')
        else: position = first
        cursor_token(identity, last, first, last)
        common = {'op': 'json', 'mode': mode, 'pointer': pointer, 'type': kind,
                  'sha256': identity['sha256']}
        def page(data, end):
            return {**common, 'data' if mode == 'value' else 'members': data,
                    'next_cursor': cursor_token(identity, end, first, last) if end < last else None}
        if mode == 'value':
            stream.seek(position)
            raw = stream.read(min(PAGE_BYTES, last - position))
            data = codecs.getincrementaldecoder('utf-8')('strict').decode(raw, final=False)
            fit = None; best = 0
            try:
                fit = envelope(page(data, position + len(data.encode('utf-8'))), cap)
                best = len(data)
            except ValueError:
                low, high = 0, len(data) - 1
                while low <= high:
                    mid = (low + high) // 2
                    end = position + len(data[:mid].encode('utf-8'))
                    try:
                        fit = envelope(page(data[:mid], end), cap); best = mid; low = mid + 1
                    except ValueError: high = mid - 1
            if fit is None or (best == 0 and position < last):
                raise ValueError('max_bytes cannot hold one character and its cursor')
            result = fit
        else:
            if token and not scan.resume_seen: raise ValueError('json cursor is not a member boundary')
            result = None
            for count in range(len(scan.items), -1, -1):
                data = [{**item, 'pointer': pointer + item['pointer']} for _, item in scan.items[:count]]
                end = scan.items[count][0] if count < len(scan.items) else last
                if count == len(scan.items) and scan.items_bytes >= PAGE_BYTES:
                    continue  # At least the retained final item is a continuation boundary.
                try: result = envelope(page(data, end), cap)
                except ValueError: continue
                if not count and end < last: result = None
                break
            if result is None: raise ValueError('max_bytes cannot hold one member and its cursor')
        after = os.fstat(stream.fileno()); current = path.stat()
        if scan.read_bytes != before.st_size or any(
                getattr(before, field) != getattr(after, field)
                or getattr(before, field) != getattr(current, field) for field in fields):
            raise ValueError('json source changed while being read')
    return result


def envelope(value: dict, cap: int) -> str:
    output = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if len(output.encode('utf-8')) + 2 > cap:  # Reserve CRLF for PowerShell re-emission.
        raise ValueError('complete JSON envelope exceeds max_bytes')
    return output


def indexed_page(root: Path, request: dict, path: Path) -> str:
    raw, identity = snapshot(root, path)
    cap = request.get('max_bytes', PAGE_BYTES)
    content = raw.decode('utf-8')  # Never replace invalid bytes or normalize CRLF.
    if request['op'] in ('index', 'excerpt') or 'cursor' not in request:
        first, last = 0, len(content)
        if 'start' in request:
            lines = content.splitlines(keepends=True)
            if request['start'] > max(1, len(lines)):
                raise ValueError(f'start exceeds file line count (file has {len(lines)} lines); '
                                 'use page for the full file or locate current lines before excerpt')
            first = sum(map(len, lines[:request['start'] - 1]))
            last = first + sum(map(len, lines[request['start'] - 1:
                                               request['start'] - 1 + request['lines']]))
        cursor_token(identity, last, first, last)  # Reject a cursor that later pages cannot accept.
        if request['op'] == 'index':
            return envelope({'op': 'index', 'path': identity['path'], 'size_bytes': identity['size'],
                             'mtime_ns': identity['mtime_ns'], 'sha256': identity['sha256'],
                             'cursor': cursor_token(identity, first, first, last)}, cap)
        start = first
    else:
        start, first, last = cursor_offset(request['cursor'], identity, len(content))
    def page(end: int) -> dict:
        return {'op': request['op'] if request['op'] == 'excerpt' else 'page',
                'data': content[start:end],
                'next_cursor': cursor_token(identity, end, first, last) if end < last else None,
                'sha256': identity['sha256']}
    # Bound serialization, not verification: snapshot() still hashes the whole file.
    # A JSON data character needs at least one UTF-8 byte.
    if last - start <= cap:
        try:
            return envelope(page(last), cap)
        except ValueError:
            pass
    low, high, end = start + 1, min(last - 1, start + cap), start
    while low <= high:
        mid = (low + high) // 2
        try:
            envelope(page(mid), cap)
            end, low = mid, mid + 1
        except ValueError:
            high = mid - 1
    if end == start:
        raise ValueError('max_bytes cannot hold one character and its cursor')
    return envelope(page(end), cap)


def bounded_process(args: list[str], root: Path, env: dict) -> tuple[int, bytes, bool]:
    # Drain output without ever accumulating more than LIMIT bytes. Kill on overflow
    # or timeout. PIPE output is not written to disk, even in a temporary file.
    proc = subprocess.Popen(args, cwd=root, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    data = bytearray()
    truncated = False
    def drain():
        nonlocal truncated
        assert proc.stdout is not None
        while True:
            block = proc.stdout.read(8192)
            if not block:
                break
            remaining = LIMIT - len(data)
            data.extend(block[:remaining])
            if len(block) > remaining:
                truncated = True
                proc.kill()
                break
    worker = threading.Thread(target=drain, daemon=True)
    worker.start()
    try:
        code = proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise ValueError('git exceeded reader timeout')
    finally:
        worker.join(timeout=2)
        if proc.stdout is not None:
            proc.stdout.close()
    return code, bytes(data), truncated


def locate(root: Path, request: dict, path: Path) -> str:
    cap = request.get('max_bytes', PAGE_BYTES)
    result = {'op': 'locate', 'path': request['path'], 'glob': request.get('glob'),
              'scope': 'rg-default-ignore-max-16MiB',
              'excluded': EXCLUDED_DIRS, 'complete': False, 'candidates': []}
    # rg's --max-filesize does not filter an explicitly named file.
    if path.is_file() and path.stat().st_size > READ_LIMIT:
        return envelope({**result, 'status': 'PARTIAL',
                         'hint': 'file exceeds 16 MiB; narrow scope'}, cap)
    reason = None
    binary = shutil.which('rg')
    if binary is None:
        reason = 'rg unavailable'
        data, code, truncated = b'', 2, False
    else:
        args = [binary, '--no-config', '--max-filesize', str(READ_LIMIT), '--with-filename',
                '--null', '--line-number', '--only-matching', '--fixed-strings',
                '--no-messages', '--color', 'never']
        if request.get('glob'):
            args += ['--glob', request['glob']]
        for name in EXCLUDED_DIRS:
            args += ['--glob', f'!**/{name}/**']
        args += ['--', request['query'], str(path.relative_to(root))]
        try:
            code, data, truncated = bounded_process(args, root, os.environ.copy())
        except (OSError, ValueError) as exc:
            code, data, truncated = 2, b'', False
            reason = f'rg failed: {type(exc).__name__}'
    if truncated:
        reason = 'rg output limit'
    elif code not in (0, 1):
        reason = reason or f'rg exit {code}'
    records = data.split(b'\n')
    if records[-1]:
        reason = reason or 'incomplete rg record'
    records = records[:-1]
    seen = set()
    for record in records:
        try:
            raw_path, separator, rest = record.partition(b'\0')
            number, colon, _ = rest.partition(b':')
            if not separator or not colon or not number.isdigit():
                raise ValueError('invalid rg record')
            candidate = {'path': Path(raw_path.decode('utf-8')).as_posix(),
                         'line': int(number)}
            if candidate['line'] < 1:
                raise ValueError('invalid rg line')
        except (UnicodeError, ValueError):
            reason = reason or 'invalid rg record'
            break
        key = (candidate['path'], candidate['line'])
        if key in seen:
            continue
        seen.add(key)
        trial = {**result, 'complete': True, 'status': 'COMPLETE',
                 'candidates': [*result['candidates'], candidate]}
        try:
            envelope(trial, cap)
        except ValueError:
            reason = reason or 'candidate output limit'
            break
        result['candidates'].append(candidate)
    result['complete'] = reason is None
    result['status'] = 'COMPLETE' if result['complete'] else 'PARTIAL'
    if reason:
        result['hint'] = f'{reason}; narrow --path/--glob/--query'
        while result['candidates']:
            try:
                return envelope(result, cap)
            except ValueError:
                result['candidates'].pop()
    return envelope(result, cap)


def one(root: Path, request: dict, path: Path, remaining: list[int]) -> str | tuple[str, dict, bool]:
    # Revalidate before each operation as well as the full-batch preflight.
    resolve(root, str(path))
    op = request['op']
    if op in ('index', 'page', 'excerpt'):
        return indexed_page(root, request, path)
    if op == 'locate':
        return locate(root, request, path)
    if op == 'json':
        return json_page(root, request, path)
    before = path.stat() if path.exists() else None
    source = {'path': path.relative_to(root).as_posix(), 'exists': before is not None}
    if before is not None:
        source.update(dev=before.st_dev, ino=before.st_ino, mtime_ns=before.st_mtime_ns, size=before.st_size)
    if op in ('diff', 'status'):
        binary = shutil.which('git')
        if not binary:
            raise ValueError('git unavailable; ask executor for diff evidence')
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', LC_ALL='C')
        args = [binary, '--no-pager', '--no-optional-locks', '--literal-pathspecs',
                '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=' + os.devnull]
        if op == 'diff':
            args += ['diff', '--no-ext-diff', '--no-textconv', '--no-color', '--ignore-submodules=all']
            if request.get('staged'):
                args += ['--cached']
        else:
            args += ['status', '--porcelain=v1', '--untracked-files=normal', '--ignore-submodules=all']
        args += ['--', str(path)]
        code, data, truncated = bounded_process(args, root, env)
        result = f'git exit={code}\n' + data.decode('utf-8', errors='replace')
        if truncated:
            result += '\n[truncated; request a narrower path]'
        return result, source, not truncated and code == 0
    if op == 'list':
        names = []; complete = True
        with os.scandir(path) as entries:
            for item in entries:
                if len(names) == 200:
                    names.append('[truncated; first 200 directory entries]')
                    complete = False
                    break
                suffix = '@' if item.is_symlink() else '/' if item.is_dir(follow_symlinks=False) else ''
                names.append(item.name + suffix)
        if path.stat().st_mtime_ns != before.st_mtime_ns:
            raise ValueError('directory changed while being read')
        return '\n'.join(sorted(names)), source, complete
    # Enforce the aggregate budget on actual bytes as well as preflight sizes.
    # At most one extra detection byte is read, then the whole request fails.
    with path.open('rb') as stream:
        raw = stream.read(remaining[0] + 1)
    if len(raw) > remaining[0]:
        raise ValueError('files grew beyond aggregate read budget')
    after = path.stat()
    if len(raw) != before.st_size or any(getattr(before, field) != getattr(after, field)
            for field in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')):
        raise ValueError('file changed while being read')
    source['source_sha256'] = hashlib.sha256(raw).hexdigest()
    remaining[0] -= len(raw)
    output = []
    for number, line in enumerate(raw.decode('utf-8', errors='replace').splitlines(), 1):
        if op == 'read' and number < request.get('start', 1):
            continue
        if op == 'search' and request['query'] not in line:
            continue
        output.append(f'{number}: {line}')
        if len(output) >= request.get('lines', 120):
            break
    return '\n'.join(output), source, True


def legacy_page(root: Path, request: dict, result: tuple[str, dict, bool], json_output: bool) -> str:
    text, source, complete = result; cap = request.get('max_bytes', PAGE_BYTES)
    if complete and not json_output and 'cursor' not in request and len(text.encode('utf-8')) + 2 <= cap:
        return text
    selected = {key: value for key, value in request.items() if key not in ('cursor', 'max_bytes')}
    identity = {**source, 'root': root.as_posix(),
                'request_sha256': hashlib.sha256(json.dumps(selected, sort_keys=True,
                    separators=(',', ':'), ensure_ascii=True).encode()).hexdigest(),
                'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()}
    start, first, last = (0, 0, len(text))
    if 'cursor' in request:
        start, first, last = cursor_offset(request['cursor'], identity, len(text))
        if (first, last) != (0, len(text)): raise ValueError('legacy cursor range mismatch')
    cursor_token(identity, last, first, last)
    def page(end):
        value = {'op': request['op'], 'data': text[start:end],
                 'status': 'COMPLETE' if complete else 'PARTIAL', 'scope': 'selected-request',
                 'next_cursor': cursor_token(identity, end, first, last) if end < last else None,
                 'sha256': identity['sha256']}
        if not complete: value['hint'] = 'capture incomplete; narrow path/query; do not infer omitted evidence'
        return value
    end = min(last, start + PAGE_BYTES)
    try: return envelope(page(end), cap)
    except ValueError: pass
    low, high, best = start + 1, end - 1, start
    while low <= high:
        mid = (low + high) // 2
        try: envelope(page(mid), cap); best = mid; low = mid + 1
        except ValueError: high = mid - 1
    if best == start: raise ValueError('max_bytes cannot hold one character and its cursor')
    return envelope(page(best), cap)


def run(root: Path, request: dict, *, json_output: bool = False) -> str:
    checked = preflight(root, request)  # ALL invalid paths fail before any read/git.
    root = root.resolve(strict=True)
    results = []
    remaining = [READ_LIMIT]
    structured = request['op'] == 'batch' and 'framing_bytes' in request
    if structured:
        cap = request['max_bytes'] - request['framing_bytes']
        captured = {}
        def packed():
            return {'op':'batch','results':[captured[i] for i in sorted(captured)],'status':'COMPLETE'}
        overhead = len(envelope(packed(), cap).encode('utf-8')) + 2
        if (cap - overhead - len(checked) + 1) // len(checked) + 2 < 256:
            raise ValueError('batch budget cannot reserve 256 bytes per request; narrow batch')
        # Capture known-small complete files first; emit in the caller's order.
        def priority(entry):
            item, path = entry[1]
            if item['op'] == 'page' and 'cursor' not in item:
                try:
                    return path.stat().st_size
                except OSError:
                    pass  # one() retains this item's error alongside other evidence.
            return READ_LIMIT
        pending = sorted(enumerate(checked), key=priority)
        for position, (index, (item, path)) in enumerate(pending):
            count = len(checked) - position
            used = len(envelope(packed(), cap).encode('utf-8')) + 2
            commas = count if captured else count - 1
            member = {**item, 'max_bytes':min(item.get('max_bytes', PAGE_BYTES),
                                             (cap - used - commas) // count + 2)}
            try:
                result = one(root, member, path, remaining)
                if item['op'] in LEGACY_OPS:
                    result = legacy_page(root, member, result, True)
                value = json.loads(result)
            except (ValueError, OSError) as error:
                value = {'op':item['op'],'path':item.get('path','.'),
                         'request_index':index + 1,'status':'ERROR','error':str(error)}
                while True:
                    try:
                        envelope(value, member['max_bytes'])
                        break
                    except ValueError:
                        if 'path' in value:
                            del value['path']; value['path_omitted'] = True
                        elif value['error']:
                            value['error_truncated'] = True
                            value['error'] = value['error'][:len(value['error']) // 2]
                        else:
                            raise
            captured[index] = value
            envelope(packed(), cap)  # Capture and budget every member before emitting anything.
        value = packed()
        if any(row.get('next_cursor') is not None or row.get('complete') is False
               or row.get('status') in ('PARTIAL', 'ERROR') for row in captured.values()):
            value['status'] = 'PARTIAL'
        return envelope(value, cap)
    size = 0
    for index, (item, path) in enumerate(checked):
        result = one(root, item, path, remaining)
        if request['op'] != 'batch':
            return legacy_page(root, item, result, json_output) if item['op'] in LEGACY_OPS else result
        text, _, complete = result
        if not complete: raise ValueError('batch capture is PARTIAL; narrow scope and read separately')
        if request['op'] == 'batch':
            text = f'[{index + 1}:{item["op"]}]\n' + text
        size += len(text.encode('utf-8')) + (1 if results else 0)
        if size + 2 > PAGE_BYTES:
            # No partial batch output is emitted. All operations are read-only.
            raise ValueError('aggregate output exceeds 4 KiB including frames/CRLF; split batch')
        results.append(text)
    return '\n'.join(results)


def cli_request(args: list[str]) -> tuple[Path, dict]:
    if not args or args[0] not in OPS | {'batch'} or len(args[1:]) % 2:
        raise ValueError('usage: read|search|list|diff|status|excerpt|locate|index|page|json --root ROOT --path RELATIVE [options]; use --help')
    values = {}
    for key, value in zip(args[1::2], args[2::2]):
        if key not in ('--root', '--path', '--cursor', '--max-bytes',
                       '--start', '--lines', '--query', '--glob', '--pointer', '--mode', '--staged',
                       '--requests', '--framing-bytes') or key in values:
            raise ValueError('unknown or duplicate reader CLI option')
        values[key] = value
    if args[0] == 'batch':
        if set(values) != {'--root','--requests','--max-bytes','--framing-bytes'}:
            raise ValueError('JSON batch needs root/requests/max-bytes/framing-bytes')
        request_text = values['--requests']
        if request_text == '-':
            raw = sys.stdin.buffer.read(INPUT_LIMIT + 1)
            if len(raw) > INPUT_LIMIT:
                raise ValueError('reader input exceeds 16 KiB')
            request_text = raw.decode('utf-8-sig')
        if len(request_text.encode('utf-8')) > INPUT_LIMIT:
            raise ValueError('reader input exceeds 16 KiB')
        root = Path(values['--root'])
        if not root.is_absolute(): raise ValueError('root must be an absolute directory')
        request = {'op':'batch','requests':json.loads(request_text, object_pairs_hook=unique,
                                                     parse_constant=reject_constant),
                   'max_bytes':int(values['--max-bytes']), 'framing_bytes':int(values['--framing-bytes'])}
        validate(request)
        return root, request
    if '--requests' in values or '--framing-bytes' in values:
        raise ValueError('requests/framing-bytes are batch-only')
    if '--root' not in values or '--path' not in values:
        raise ValueError('root and path are required')
    root = Path(values['--root'])
    if not root.is_absolute():
        raise ValueError('root must be an absolute directory')
    request = {'op': args[0], 'path': values['--path']}
    if '--max-bytes' in values:
        request['max_bytes'] = int(values['--max-bytes'])
    if '--cursor' in values:
        request['cursor'] = values['--cursor']
    if '--staged' in values:
        if values['--staged'] not in ('true', 'false'): raise ValueError('staged must be true or false')
        request['staged'] = values['--staged'] == 'true'
    for key in ('query', 'glob', 'pointer', 'mode'):
        if '--' + key in values:
            request[key] = values['--' + key]
    for key in ('start', 'lines'):
        if '--' + key in values:
            request[key] = int(values['--' + key])
    validate(request)
    return root, request


ASSIGNMENT_HELP = '''CER existing-worker assignment preflight (caller evidence, not host authentication)
  Verified Python -I -B <Skill>/scripts/readonly_reader.py assignment
  UTF-8 JSON stdin <=16 KiB; output <=4 KiB. Exit 0: VERIFIED, with prefix/body_sha256/
  receipt/dispatch_arguments. Exit 1: MISMATCH or UNKNOWN, no execution parameters.
  Exit 2: invalid input. Check exit/status, then send prefix + the exact checked body;
  verify body_sha256 before merging. Do not mirror the work prompt into tool output.
  admitted_agent_task: use admitted_dispatch_arguments plus body=prefix+message;
  never inherit its Sol61/high defaults for another receiver. Raw sends use dispatch_arguments.
Minimal engineering review input (replace recipient/evidence with observed values):
{"unit_id":"review-1","purpose":"new_unit","scope":"Conan review","message":"Review Conan configuration","recipient":{"id":"observed-child","model":"gpt-6.1-sol","effort":"high","evidence_ref":"session_meta/current turn_context"},"signals":{"spec_complete":true,"authority_ready":true,"environment_ready":true,"observability_ready":true}}
  Astra new work: signals.very_complex=true, complexity_reason, and
  signals.sol61_unsuitable_reason; both readable reasons appear in the prefix.
  force_astra alone is not a user authorization. Missing/unknown binding: no task send.
  Medium: confirmed_simple=true + current simple uncertainty/risk/coupling <=1,
  no conflict/failure/irreversibility, novelty <=1; admitted Astra floor remains high.
  xhigh/max/ultra: effort_supported=true + effort_reason; no support is inferred.
  Pure purpose/message continue/status/stop (or exact Chinese control word): same
  unit/scope/recipient/current-policy receipt may cache admission; added work text
  re-admits, even with unchanged IDs. Wait needs none. New spawn: explicit role/effort,
  HOLD identity report; verify binding before this existing-worker entry releases work.
Native dispatch mode (independent trusted registration):
  New work requires purpose=new_unit and current admission. Exact continue/status/stop
  retain the original receipt and work hash; current host binding is rechecked.
  Controls cannot release new work, expand scope or hide added instructions.
  Spawn body must be exactly this fixed identity HOLD, with no additional work:
  HOLD. Report only your identity and working directory; do not use tools or accept work until RELEASE.
  Known executor medium/high may spawn with that plain body. For Astra creation, run
  assignment with recipient.id="unbound-spawn", the explicitly requested model/effort,
  purpose=new_unit, scope="identity HOLD", and message equal to the fixed HOLD above.
  Supply all readiness signals plus very_complex=true, complexity_reason, and
  sol61_unsuitable_reason. Check VERIFIED/exit 0, then send prefix + that exact HOLD.
  Requested spawn parameters are not an actual binding; verify host identity before work.
  Current callers prepend this exact line to the checked work message (not signals):
  CER execution (caller evidence): {"effects":["read"],"permission":"read-only","role_read_only":true,"parent_released":false}
  Check permission/role against current host binding; writes/build/tests require writable
  permission, a non-readonly role and parent release. Declarations grant no authority.
  Existing message_sha256 binds the complete declaration/work body; scope_sha256 binds
  its admitted scope. Keep the existing readiness signals unchanged; no new envelope fields.
  Legacy envelopes remain compatible; install validator/rules together, never live-edit guards.
'''

EXECUTION_PREFIX = 'CER execution (caller evidence): '
ASSIGNMENT_ROLES = {
    'luna_worker': ('gpt-6-luna', 'high'),
    'terra_executor': ('gpt-5.6-terra', 'medium'),
    'sol_engineer': ('gpt-6.1-sol', 'medium'),
    'sol61_engineer': ('gpt-6.1-sol', 'high'),
    'astra_architect': ('gpt-6-astra', 'high'),
}
ASSIGNMENT_LEGACY_MODELS = ('gpt-5.6-luna',)
ASSIGNMENT_EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max', 'ultra')
CONTROL_WORDS = {'continue': ('continue', '继续'),
                 'status': ('status', '状态'), 'stop': ('stop', '停止')}


def assignment_pair_known(model: object, effort: object) -> bool:
    """Recognize exact configured identities, never infer a permission grant."""
    models = tuple(pair[0] for pair in ASSIGNMENT_ROLES.values()) + ASSIGNMENT_LEGACY_MODELS
    return (isinstance(model, str) and model in models
            and isinstance(effort, str) and effort in ASSIGNMENT_EFFORTS
            and not (effort == 'ultra' and model in
                     ('gpt-6-luna', 'gpt-5.6-luna', 'gpt-5.6-terra')))


def assignment_simple(request: dict, signals: dict) -> bool:
    """Require explicit classification; bools/strings are not numerical risk scores."""
    return (request.get('confirmed_simple') is True
            and all(type(signals.get(key, 1)) is int and 0 <= signals.get(key, 1) <= 1
                    for key in ('uncertainty', 'risk', 'coupling', 'novelty'))
            and type(signals.get('irreversibility', 0)) is int
            and signals.get('irreversibility', 0) == 0
            and all(signals.get(key, False) is False
                    for key in ('evidence_conflict', 'capability_failure', 'very_complex')))


def assignment_policy_sha256(skill_root: Path | None = None) -> str:
    """Fingerprint this installed validator and its current rules, not host identity."""
    here = Path(__file__).resolve()
    skill = skill_root if skill_root is not None else here.parents[1]
    if skill_root is None and not (skill / 'SKILL.md').is_file():
        skill = skill / 'skills/codex-efficiency-router'
    manifest = skill / '.cer-install.json'
    if manifest.is_file():
        with manifest.open('rb') as stream:
            raw = stream.read(INPUT_LIMIT + 1)
        if len(raw) > INPUT_LIMIT:
            raise ValueError('installed policy manifest exceeds input limit')
        installed = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(installed, dict):
            raise ValueError('installed policy manifest must be an object')
        schema = installed.get('profile_schema')
        host = installed.get('host_mode', 'full')
        if (host != 'full' or schema is not None and (type(schema) is not int or schema not in (2, 3))
                or schema == 3 and 'host_mode' not in installed):
            raise ValueError('full admission requires full host mode; compat grants no full routing')
    digest = hashlib.sha256(here.read_bytes())
    for path in (skill / 'SKILL.md', *sorted((skill / 'references').glob('*.md'))):
        rules = path.read_bytes()
        if path.name == 'SKILL.md' and b'Host mode: compat.' in rules:
            raise ValueError('compat does not provide full admission')
        digest.update(rules)
    return digest.hexdigest()


def assignment_astra_admitted(signals: dict) -> bool:
    prerequisites = ('spec_complete', 'authority_ready', 'environment_ready', 'observability_ready')
    return (all(signals.get(key, True) is True for key in prerequisites)
            and (signals.get('force_astra') is True or
                 (signals.get('cheap_check_available', False) is False
                  and signals.get('very_complex') is True
                  and signals.get('reasoning_bound', True) is True
                  and isinstance(signals.get('sol61_unsuitable_reason'), str)
                  and bool(signals['sol61_unsuitable_reason'].strip()))))


def assignment_boundary(*, recipient_id, model, effort, unit_id, purpose,
                        scope=None, message=None, signals=None, prior=None, policy_sha256=None) -> dict:
    """Caller evidence only. Work hidden in a control message needs fresh admission."""
    result = {'status': 'UNKNOWN', 'effective_purpose': purpose}
    if not all(isinstance(value, str) and value for value in (recipient_id, model, effort, unit_id)):
        return result
    if not assignment_pair_known(model, effort):
        return result
    controls = CONTROL_WORDS
    if purpose not in ('new_unit', *controls):
        return result
    if purpose in controls and message in controls[purpose]:
        if not isinstance(scope, str) or not scope or not isinstance(prior, dict):
            return result
        expected = {'recipient_id': recipient_id, 'unit_id': unit_id, 'model': model, 'effort': effort,
                    'scope_sha256': hashlib.sha256(scope.encode('utf-8')).hexdigest(),
                    'policy_sha256': policy_sha256 or assignment_policy_sha256()}
        if not all(isinstance(prior.get(key), str) and prior[key] for key in expected):
            return result
        fingerprint = prior.get('message_sha256')
        if not isinstance(fingerprint, str) or re.fullmatch('[0-9a-f]{64}', fingerprint) is None:
            return result
        result['status'] = 'VERIFIED' if all(prior[key] == value for key, value in expected.items()) else 'MISMATCH'
        return result
    result['effective_purpose'] = 'new_unit'
    if not isinstance(signals, dict):
        return result
    if model == 'gpt-6-astra' and not assignment_astra_admitted(dict(signals, force_astra=False)):
        result['status'] = 'MISMATCH'
        return result
    result['status'] = 'READY'  # Configuration/effort still requires checking by the consumer.
    return result


def execution_admission(execution: object, model: str) -> str:
    """Check caller-declared effects/permissions; never authenticate or grant authority."""
    if not isinstance(execution, dict) or set(execution) != {
            'effects', 'permission', 'role_read_only', 'parent_released'}:
        return 'UNKNOWN'
    effects = execution['effects']
    if (not isinstance(effects, list) or not effects
            or any(not isinstance(item, str) or item not in ('read', 'write', 'build', 'test') for item in effects)
            or len(set(effects)) != len(effects)
            or execution['permission'] not in ('read-only', 'workspace-write', 'full-access')
            or type(execution['role_read_only']) is not bool
            or type(execution['parent_released']) is not bool):
        return 'UNKNOWN'
    if set(effects) != {'read'}:
        if (model == 'gpt-6-astra' or execution['role_read_only']
                or execution['permission'] == 'read-only'):
            return 'MISMATCH'
        if not execution['parent_released']:
            return 'UNKNOWN'
    return 'VERIFIED'


def assignment_preflight(request: dict, *, policy_sha256: str | None = None) -> dict:
    """Installed pre-dispatch entry; never authenticates supplied recipient evidence."""
    if not isinstance(request, dict):
        raise ValueError('assignment object required')
    receiver = request.get('recipient', {})
    if not isinstance(receiver, dict):
        receiver = {}
    scope, message = request.get('scope'), request.get('message')
    boundary = assignment_boundary(recipient_id=receiver.get('id'), model=receiver.get('model'),
        effort=receiver.get('effort'), unit_id=request.get('unit_id'), purpose=request.get('purpose'),
        scope=scope, message=message, signals=request.get('signals'), prior=request.get('receipt'),
        policy_sha256=policy_sha256)
    result = {'status': boundary['status'], 'effective_purpose': boundary['effective_purpose'],
              'evidence_basis': 'caller-supplied; not host authentication'}
    if (not isinstance(scope, str) or not scope or not isinstance(message, str) or not message
            or not isinstance(receiver.get('evidence_ref'), str) or not receiver['evidence_ref']):
        result['status'] = 'UNKNOWN'
        return result
    if not assignment_pair_known(receiver.get('model'), receiver.get('effort')):
        result['status'] = 'UNKNOWN'
        return result
    if boundary['status'] not in ('READY', 'VERIFIED'):
        return result
    signals = request.get('signals', {})
    if not isinstance(signals, dict):
        result['status'] = 'UNKNOWN'
        return result
    # The current native guard rejects additional signals. Bind capability metadata
    # to the existing checked message body instead; never broaden its allowlist.
    if 'execution' in signals:
        result['status'] = 'MISMATCH'
        return result
    # Legacy bodies keep their admitted authority; current guidance requires the
    # declaration for new work. This is caller evidence, not host authentication.
    if message.startswith(EXECUTION_PREFIX):
        header, separator, work = message.partition('\n')
        try:
            declaration = json.loads(header[len(EXECUTION_PREFIX):], object_pairs_hook=unique,
                                     parse_constant=reject_constant)
        except (ValueError, TypeError):
            declaration = None
        execution = execution_admission(declaration, receiver['model']) if separator and work.strip() else 'UNKNOWN'
        if execution != 'VERIFIED':
            result['status'] = execution
            return result
    if boundary['status'] == 'READY':
        model, effort = receiver['model'], receiver['effort']
        prerequisites = ('spec_complete', 'authority_ready', 'environment_ready', 'observability_ready')
        if not all(signals.get(key) is True for key in prerequisites):
            result['status'] = 'UNKNOWN'
            return result
        simple = assignment_simple(request, signals)
        bounded_model = model in ('gpt-6-luna', 'gpt-5.6-luna', 'gpt-5.6-terra')
        if ((bounded_model and not simple)
                or (effort == 'medium' and (not simple or model == 'gpt-6-astra'))
                or (effort == 'low' and (not simple or model not in
                                        ('gpt-6-luna', 'gpt-5.6-luna')))):
            result['status'] = 'MISMATCH'
            return result
        if effort == 'low' and not (request.get('effort_supported') is True
                and isinstance(request.get('effort_reason'), str) and request['effort_reason'].strip()):
            result['status'] = 'UNKNOWN'
            return result
        if effort in ('xhigh', 'max', 'ultra') and not (
                request.get('effort_supported') is True and isinstance(request.get('effort_reason'), str)
                and request['effort_reason'].strip()):
            result['status'] = 'UNKNOWN'
            return result
        if model == 'gpt-6-astra':
            reason = request.get('complexity_reason')
            # A self-reported pin is not evidence of an actual user instruction.
            if not assignment_astra_admitted(dict(signals, force_astra=False)):
                result['status'] = 'MISMATCH'
                return result
            if not isinstance(reason, str) or not reason.strip():
                result['status'] = 'UNKNOWN'
                return result
    receipt = {'recipient_id': receiver['id'], 'unit_id': request['unit_id'],
               'model': receiver['model'], 'effort': receiver['effort'], 'evidence_ref': receiver['evidence_ref'],
               'scope_sha256': hashlib.sha256(scope.encode('utf-8')).hexdigest(),
               'message_sha256': hashlib.sha256(message.encode('utf-8')).hexdigest(),
               'policy_sha256': policy_sha256 or assignment_policy_sha256()}
    if boundary['effective_purpose'] == 'new_unit':
        # Current admission inputs, never an identity signature or cached permission.
        receipt['admission'] = {key: request[key] for key in (
            'unit_id', 'purpose', 'scope', 'signals', 'complexity_reason',
            'confirmed_simple', 'effort_supported', 'effort_reason') if key in request}
    if boundary['effective_purpose'] != 'new_unit':
        # Retain the work hash and original admission, not a newly authorized unit.
        # Exact control words cannot carry extra work. This is still not a signature.
        receipt = dict(request['receipt'])
        receipt['control'] = boundary['effective_purpose']
        if not isinstance(receipt.get('admission'), dict):
            result['status'] = 'UNKNOWN'
            return result
    prefix = 'CER assignment (caller evidence): ' + json.dumps(receipt, ensure_ascii=False, separators=(',', ':')) + '\n'
    if boundary['effective_purpose'] == 'new_unit' and receiver['model'] == 'gpt-6-astra':
        prefix += ('Parent judgment: very complex; ' + request['complexity_reason'].strip()
                   + '\nSol61 unsuitable: ' + signals['sol61_unsuitable_reason'].strip() + '\n')
    result.update(status='VERIFIED', receipt=receipt, prefix=prefix,
                  body_sha256=hashlib.sha256(message.encode('utf-8')).hexdigest(),
                  dispatch_arguments={'id': receiver['id']},
                  admitted_dispatch_arguments={'operation': 'assign', 'target': receiver['id'],
                      'model': receiver['model'], 'reasoning_effort': receiver['effort']})
    return result


def assignment_message(result: dict, message: str) -> str:
    """Merge only the exact checked body; callers must send this returned message."""
    if (result.get('status') != 'VERIFIED' or not isinstance(message, str)
            or result.get('body_sha256') != hashlib.sha256(message.encode('utf-8')).hexdigest()):
        raise ValueError('unchecked or changed assignment body')
    return result['prefix'] + message


def main() -> int:
    cap = PAGE_BYTES
    json_output = False
    try:
        if sys.argv[1:] == ['assignment', '--help']:
            sys.stdout.buffer.write(ASSIGNMENT_HELP.encode('utf-8'))
            return 0
        if sys.argv[1:] == ['assignment']:
            raw = sys.stdin.buffer.read(INPUT_LIMIT + 1)
            if len(raw) > INPUT_LIMIT:
                raise ValueError('assignment input exceeds limit')
            request = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique, parse_constant=reject_constant)
            result = assignment_preflight(request)
            output = json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode('utf-8') + b'\n'
            if len(output) > PAGE_BYTES:
                raise ValueError('assignment result exceeds limit')
            sys.stdout.buffer.write(output)
            return 0 if result['status'] == 'VERIFIED' else 1
        if sys.argv[1:] == ['--help'] or (len(sys.argv) == 3 and sys.argv[2] == '--help'
                                         and sys.argv[1] in OPS | {'batch'}):
            sys.stdout.buffer.write(HELP.encode('utf-8'))
            return 0
        if len(sys.argv) > 1 and sys.argv[1] in OPS | {'batch'}:
            root, request = cli_request(sys.argv[1:])
            json_output = True
            cap = request.get('max_bytes', PAGE_BYTES) - request.get('framing_bytes', 0)
        else:
            if len(sys.argv) != 3 or len(sys.argv[2]) > (INPUT_LIMIT + 2) // 3 * 4:
                raise ValueError('expected workspace and bounded encoded request')
            token = sys.argv[2]
            raw = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
            request = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique, parse_constant=reject_constant)
            root = Path(sys.argv[1])
            validate(request)
            cap = request.get('max_bytes', PAGE_BYTES) - request.get('framing_bytes', 0)
        sys.stdout.buffer.write(run(root, request, json_output=json_output).encode('utf-8') + b'\n')
        return 0
    except (ValueError, OSError, TypeError, UnicodeError, RecursionError, subprocess.SubprocessError) as exc:
        message = clip(f'CER read failed: {exc}', cap - 2)
        sys.stderr.buffer.write(message.encode('utf-8', errors='backslashreplace') + b'\n')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
