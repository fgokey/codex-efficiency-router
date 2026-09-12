"""Bounded read-only adapter. Batches preflight in full; no arbitrary commands.

Limits are byte limits, not character counts. Local trusted filesystem only: this
is not protection against a malicious process racing a validated path.
"""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import threading

VERSION = '0.7.0-rc.10'
LIMIT = 131072
INPUT_LIMIT = 16384
READ_LIMIT = 16 * 1024 * 1024
BATCH_LIMIT = 16
OPS = frozenset(('read', 'list', 'search', 'diff', 'status'))


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
            validate(item)
        return request
    if not isinstance(op, str) or op not in OPS:
        raise ValueError('reader needs read/list/search/diff/status or batch')
    fields = {'op', 'path'} | {
        'read': {'start', 'lines'}, 'search': {'query', 'lines'},
        'diff': {'staged'}, 'status': set(), 'list': set(),
    }[op]
    if set(request) - fields:
        raise ValueError('unknown reader field')
    path = request.get('path', '.')
    if not isinstance(path, str) or any(c in path for c in '\x00\r\n'):
        raise ValueError('invalid path')
    for key, default in (('start', 1), ('lines', 120)):
        value = request.get(key, default)
        if type(value) is not int or value < 1 or (key == 'lines' and value > 200):
            raise ValueError('invalid line range')
    if op == 'search' and (not isinstance(request.get('query'), str) or not request['query']):
        raise ValueError('search requires a nonempty literal query')
    if type(request.get('staged', False)) is not bool:
        raise ValueError('staged must be boolean')
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
        if item['op'] in ('read', 'search'):
            if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
                raise ValueError('read/search require one regular file, not a directory')
            total += path.stat().st_size
            if total > READ_LIMIT:
                raise ValueError('aggregate file read budget exceeds 16 MiB')
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


def one(root: Path, request: dict, path: Path, remaining: list[int]) -> str:
    # Revalidate before each operation as well as the full-batch preflight.
    resolve(root, str(path))
    op = request['op']
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


def main() -> int:
    try:
        if len(sys.argv) != 3 or len(sys.argv[2]) > (INPUT_LIMIT + 2) // 3 * 4:
            raise ValueError('expected workspace and bounded encoded request')
        raw = base64.b64decode(sys.argv[2], altchars=b'-_', validate=True)
        request = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=reject_constant)
        print(run(Path(sys.argv[1]), request))
        return 0
    except (ValueError, OSError, TypeError, RecursionError, subprocess.SubprocessError) as exc:
        print(f'CER read failed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
