"""Bounded read-only adapter for the CER PreToolUse guard. No arbitrary commands."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

LIMIT = 131072


def validate(request: object) -> dict:
    if not isinstance(request, dict) or request.get('op') not in ('read', 'list', 'search', 'diff', 'status'):
        raise ValueError('reader needs read/list/search/diff/status')
    fields = {'op', 'path', 'start', 'lines', 'query', 'staged'}
    if set(request) - fields:
        raise ValueError('unknown reader field')
    if not isinstance(request.get('path', '.'), str) or '\x00' in request.get('path', ''):
        raise ValueError('invalid path')
    for key, default in (('start', 1), ('lines', 120)):
        value = request.get(key, default)
        if type(value) is not int or value < 1 or (key == 'lines' and value > 200):
            raise ValueError('invalid line range')
    if request['op'] == 'search' and (not isinstance(request.get('query'), str) or not request['query']):
        raise ValueError('search requires a nonempty literal query')
    if type(request.get('staged', False)) is not bool:
        raise ValueError('staged must be boolean')
    return request


def resolve(root: Path, value: str) -> Path:
    candidate = root / value
    # No symlinks within the scope, directories included. Trusted local FS only.
    for item in (candidate, *candidate.parents):
        if item == root.parent:
            break
        if item.is_symlink():
            raise ValueError('reader refuses symlinks')
    path = candidate.resolve()
    if not path.is_relative_to(root):
        raise ValueError('path outside hook workspace')
    return path


def run(root: Path, request: dict) -> str:
    validate(request)
    root = root.resolve(strict=True)
    path = resolve(root, request.get('path', '.'))
    op = request['op']
    if op in ('diff', 'status'):
        binary = shutil.which('git')
        if not binary:
            raise ValueError('git unavailable; ask executor for diff evidence')
        # No shell, no pager, optional locks, fsmonitor, textconv or external diff.
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', LC_ALL='C')
        args = [binary, '--no-pager', '--no-optional-locks', '--literal-pathspecs', '-c', 'core.fsmonitor=false']
        if op == 'diff':
            args += ['diff', '--no-ext-diff', '--no-textconv', '--no-color']
            if request.get('staged'):
                args += ['--cached']
        else:
            args += ['status', '--porcelain=v1', '--untracked-files=normal']
        args += ['--', str(path)]
        result = subprocess.run(args, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10, check=False)
        output = result.stdout[:LIMIT].decode('utf-8', errors='replace')
        if len(result.stdout) > LIMIT:
            output += '\n[truncated; request a narrower path]'
        return f'git exit={result.returncode}\n' + output
    if op == 'list':
        return '\n'.join(p.name + ('/' if p.is_dir() else '') for p in sorted(path.iterdir())[:200])
    if not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('read/search require one regular file up to 16 MiB')
    output = []
    with path.open(encoding='utf-8', errors='replace') as stream:
        for number, line in enumerate(stream, 1):
            if op == 'read' and number < request.get('start', 1):
                continue
            if op == 'search' and request['query'] not in line:
                continue
            output.append(f'{number}: {line.rstrip()[:4096]}')
            if len(output) >= request.get('lines', 120):
                break
    return '\n'.join(output)[:LIMIT]


def main() -> int:
    try:
        if len(sys.argv) != 3:
            raise ValueError('expected workspace and encoded request')
        request = json.loads(base64.urlsafe_b64decode(sys.argv[2]).decode('utf-8'))
        print(run(Path(sys.argv[1]), request))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f'CER read failed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
