"""Bounded read-only adapter. Batches preflight in full; no arbitrary commands.

Limits are byte limits, not character counts. Local trusted filesystem only: this
is not protection against a malicious process racing a validated path.
"""
from __future__ import annotations
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import threading

VERSION = '0.8.0'
LIMIT = 131072
INPUT_LIMIT = 16384
READ_LIMIT = 16 * 1024 * 1024
BATCH_LIMIT = 16
OPS = frozenset(('read', 'list', 'search', 'diff', 'status', 'index', 'page', 'excerpt', 'locate'))
PAGE_BYTES = 4096
EXCLUDED_DIRS = ('.git', 'node_modules', 'dist', 'build', '.next', 'temp')
HELP = """CER read (UTF-8; each JSON response <=4096 bytes including CRLF)
  excerpt --root ABS --path RELFILE --start N --lines N [--max-bytes N]
    One snapshot, first bounded page of lines N..N+lines-1 (lines 1..200).
    Continue with page --root ABS --path RELFILE --cursor TOKEN if next_cursor is not null.
  locate --root ABS --path RELDIR_OR_FILE --query LITERAL [--glob FILE_GLOB] [--max-bytes N]
    Literal rg search; returns path/line candidates only. complete applies to the chosen
    path/glob under rg default ignore/hidden rules and 16 MiB max file size,
    excluding .git,node_modules,dist,build,.next,temp. PARTIAL means narrow scope.
  index --root ABS --path RELFILE [--start N --lines N] [--max-bytes N]
    Returns cursor, size and SHA; omit range for complete rules/full-file reads.
  page --root ABS --path RELFILE --cursor TOKEN [--max-bytes N]
    Repeats until next_cursor is null; rejects changed files or stale cursors.
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
            if item.get('op') in ('index', 'page', 'excerpt', 'locate'):
                raise ValueError('index/page/excerpt/locate cannot be batched')
            validate(item)
        return request
    if not isinstance(op, str) or op not in OPS:
        raise ValueError('reader needs read/list/search/diff/status/index/page/excerpt/locate or batch')
    fields = {'op', 'path'} | {
        'read': {'start', 'lines'}, 'search': {'query', 'lines'},
        'diff': {'staged'}, 'status': set(), 'list': set(),
        'index': {'max_bytes', 'start', 'lines'}, 'page': {'max_bytes', 'cursor'},
        'excerpt': {'max_bytes', 'start', 'lines'},
        'locate': {'max_bytes', 'query', 'glob'},
    }[op]
    if set(request) - fields:
        raise ValueError('unknown reader field')
    path = request.get('path', '.')
    if not isinstance(path, str) or any(c in path for c in '\x00\r\n'):
        raise ValueError('invalid path')
    if op in ('index', 'page', 'excerpt', 'locate'):
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
            raise ValueError('invalid line range')
    if op == 'search' and (not isinstance(request.get('query'), str) or not request['query']):
        raise ValueError('search requires a nonempty literal query')
    if type(request.get('staged', False)) is not bool:
        raise ValueError('staged must be boolean')
    if op in ('index', 'page', 'excerpt', 'locate'):
        cap = request.get('max_bytes', PAGE_BYTES)
        if type(cap) is not int or not 256 <= cap <= PAGE_BYTES:
            raise ValueError('max_bytes must be 256..4096')
        if op == 'page' and (not isinstance(request.get('cursor'), str) or not request['cursor']):
            raise ValueError('page requires a cursor from index/previous page')
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


def envelope(value: dict, cap: int) -> str:
    output = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if len(output.encode('utf-8')) + 2 > cap:  # Reserve CRLF for PowerShell re-emission.
        raise ValueError('complete JSON envelope exceeds max_bytes')
    return output


def indexed_page(root: Path, request: dict, path: Path) -> str:
    raw, identity = snapshot(root, path)
    cap = request.get('max_bytes', PAGE_BYTES)
    content = raw.decode('utf-8')  # Never replace invalid bytes or normalize CRLF.
    if request['op'] in ('index', 'excerpt'):
        first, last = 0, len(content)
        if 'start' in request:
            lines = content.splitlines(keepends=True)
            if request['start'] > max(1, len(lines)):
                raise ValueError('start exceeds file line count')
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
    if not args or args[0] not in ('index', 'page', 'excerpt', 'locate') or len(args[1:]) % 2:
        raise ValueError('usage: excerpt|locate|index|page --root ROOT --path RELATIVE [options]; use --help')
    values = {}
    for key, value in zip(args[1::2], args[2::2]):
        if key not in ('--root', '--path', '--cursor', '--max-bytes',
                       '--start', '--lines', '--query', '--glob') or key in values:
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
    for key in ('query', 'glob'):
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
                                         and sys.argv[1] in ('index', 'page', 'excerpt', 'locate')):
            sys.stdout.buffer.write(HELP.encode('utf-8'))
            return 0
        if len(sys.argv) > 1 and sys.argv[1] in ('index', 'page', 'excerpt', 'locate'):
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
