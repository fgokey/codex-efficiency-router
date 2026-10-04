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

VERSION = '0.8.4'
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
PAGE_BYTES = 4096
EXCLUDED_DIRS = ('.git', 'node_modules', 'dist', 'build', '.next', 'temp')
HELP = """CER read (UTF-8; each JSON response <=4096 bytes including CRLF)
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
        if set(request) != {'op', 'requests'}:
            raise ValueError('batch only accepts op and requests')
        items = request['requests']
        if not isinstance(items, list) or not 1 <= len(items) <= BATCH_LIMIT:
            raise ValueError('batch requires 1..16 operations')
        for item in items:
            if not isinstance(item, dict) or item.get('op') == 'batch':
                raise ValueError('nested batches are not supported')
            if item.get('op') in ('index', 'page', 'excerpt', 'locate', 'json'):
                raise ValueError('index/page/excerpt/locate/json cannot be batched')
            validate(item)
        return request
    if not isinstance(op, str) or op not in OPS:
        raise ValueError('reader needs read/list/search/diff/status/index/page/excerpt/locate/json or batch')
    fields = {'op', 'path'} | {
        'read': {'start', 'lines'}, 'search': {'query', 'lines'},
        'diff': {'staged'}, 'status': set(), 'list': set(),
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
    if op in ('index', 'page', 'excerpt', 'locate', 'json'):
        cap = request.get('max_bytes', PAGE_BYTES)
        if type(cap) is not int or not 256 <= cap <= PAGE_BYTES:
            raise ValueError('max_bytes must be 256..4096')
        if op in ('page', 'json') and 'cursor' in request and (not isinstance(request['cursor'], str)
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
    total = 0
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
            if path.stat().st_size > JSON_SCAN_LIMIT:
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
                'mtime_ns': after.st_mtime_ns, 'dev': after.st_dev, 'ino': after.st_ino,
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
    complete = page(last)
    try:
        return envelope(complete, cap)
    except ValueError:
        pass
    low, high, end = start + 1, last - 1, start
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


def one(root: Path, request: dict, path: Path, remaining: list[int]) -> str:
    # Revalidate before each operation as well as the full-batch preflight.
    resolve(root, str(path))
    op = request['op']
    if op in ('index', 'page', 'excerpt'):
        return indexed_page(root, request, path)
    if op == 'locate':
        return locate(root, request, path)
    if op == 'json':
        return json_page(root, request, path)
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
        return clip(result)
    if op == 'list':
        names = []
        with os.scandir(path) as entries:
            for item in entries:
                if len(names) == 200:
                    names.append('[truncated; first 200 directory entries]')
                    break
                suffix = '@' if item.is_symlink() else '/' if item.is_dir(follow_symlinks=False) else ''
                names.append(item.name + suffix)
        return clip('\n'.join(sorted(names)))
    # Enforce the aggregate budget on actual bytes as well as preflight sizes.
    # At most one extra detection byte is read, then the whole request fails.
    with path.open('rb') as stream:
        raw = stream.read(remaining[0] + 1)
    if len(raw) > remaining[0]:
        raise ValueError('files grew beyond aggregate read budget')
    remaining[0] -= len(raw)
    output = []
    for number, line in enumerate(raw.decode('utf-8', errors='replace').splitlines(), 1):
        if op == 'read' and number < request.get('start', 1):
            continue
        if op == 'search' and request['query'] not in line:
            continue
        output.append(f'{number}: {line[:4096]}')
        if len(output) >= request.get('lines', 120):
            break
    return clip('\n'.join(output))


def run(root: Path, request: dict) -> str:
    checked = preflight(root, request)  # ALL invalid paths fail before any read/git.
    root = root.resolve(strict=True)
    results = []
    size = 0
    remaining = [READ_LIMIT]
    for index, (item, path) in enumerate(checked):
        text = one(root, item, path, remaining)
        if request['op'] == 'batch':
            text = f'[{index + 1}:{item["op"]}]\n' + text
        size += len(text.encode('utf-8')) + (1 if results else 0)
        if size > LIMIT:
            # No partial batch output is emitted. All operations are read-only.
            raise ValueError('aggregate output exceeds 128 KiB; split batch')
        results.append(text)
    return '\n'.join(results)


def cli_request(args: list[str]) -> tuple[Path, dict]:
    if not args or args[0] not in ('index', 'page', 'excerpt', 'locate', 'json') or len(args[1:]) % 2:
        raise ValueError('usage: excerpt|locate|index|page|json --root ROOT --path RELATIVE [options]; use --help')
    values = {}
    for key, value in zip(args[1::2], args[2::2]):
        if key not in ('--root', '--path', '--cursor', '--max-bytes',
                       '--start', '--lines', '--query', '--glob', '--pointer', '--mode') or key in values:
            raise ValueError('unknown or duplicate reader CLI option')
        values[key] = value
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
    for key in ('query', 'glob', 'pointer', 'mode'):
        if '--' + key in values:
            request[key] = values['--' + key]
    for key in ('start', 'lines'):
        if '--' + key in values:
            request[key] = int(values['--' + key])
    validate(request)
    return root, request


def main() -> int:
    cap = PAGE_BYTES
    try:
        if sys.argv[1:] == ['--help'] or (len(sys.argv) == 3 and sys.argv[2] == '--help'
                                         and sys.argv[1] in ('index', 'page', 'excerpt', 'locate', 'json')):
            sys.stdout.buffer.write(HELP.encode('utf-8'))
            return 0
        if len(sys.argv) > 1 and sys.argv[1] in ('index', 'page', 'excerpt', 'locate', 'json'):
            root, request = cli_request(sys.argv[1:])
            cap = request.get('max_bytes', PAGE_BYTES)
        else:
            if len(sys.argv) != 3 or len(sys.argv[2]) > (INPUT_LIMIT + 2) // 3 * 4:
                raise ValueError('expected workspace and bounded encoded request')
            raw = base64.b64decode(sys.argv[2], altchars=b'-_', validate=True)
            request = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=reject_constant)
            root = Path(sys.argv[1])
        sys.stdout.buffer.write(run(root, request).encode('utf-8') + b'\n')
        return 0
    except (ValueError, OSError, TypeError, UnicodeError, RecursionError, subprocess.SubprocessError) as exc:
        message = clip(f'CER read failed: {exc}', cap - 2)
        sys.stderr.buffer.write(message.encode('utf-8', errors='backslashreplace') + b'\n')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
