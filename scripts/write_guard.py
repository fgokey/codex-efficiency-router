#!/usr/bin/env python3
"""Explicit native Hook registration, separate from normal Skill installation.

Only an exact owned group is merged/removed in hooks.json. No trust bypass, model
probe, config.toml edit or recursive cleanup. Scope applies even outside this Skill.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
from uuid import uuid4

from manage import reject_links, read_bytes, replace, digest
from package import resolve_targets

OWNER = 'cer-astra-write-guard'
FILES = ('astra_write_guard.py', 'readonly_reader.py')
ROOT = Path(__file__).resolve().parents[1]


def loads(raw):
    def unique(items):
        out = {}
        for key, val in items:
            if key in out:
                raise ValueError('duplicate JSON key')
            out[key] = val
        return out
    return json.loads(raw, object_pairs_hook=unique)


def encode(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def shell_command(args):
    if os.name == 'nt':
        return '& ' + ' '.join("'" + arg.replace("'", "''") + "'" for arg in args)
    return shlex.join(args)


def targets(scope, project_root):
    _, agents, backups = resolve_targets(scope, project_root)
    base = agents.parent
    return base / 'hooks' / OWNER, base / 'hooks.json', backups / OWNER


def group_for(directory):
    return {'matcher': '*', 'hooks': [{'type': 'command',
            'command': shell_command([str(Path(sys.executable).resolve()), '-I', '-B', str(directory / FILES[0])]),
            'timeout': 5, 'statusMessage': 'CER Astra write boundary'}]}


def load_config(raw):
    doc = {} if raw is None else loads(raw)
    if not isinstance(doc, dict) or not isinstance(doc.get('hooks', {}), dict):
        raise ValueError('unsupported hooks.json structure')
    groups = doc.get('hooks', {}).get('PreToolUse', [])
    if not isinstance(groups, list) or any(not isinstance(g, dict) for g in groups):
        raise ValueError('invalid PreToolUse groups')
    return doc


def owned_manifest(directory):
    raw = read_bytes(directory / 'manifest.json')
    if raw is None:
        return None
    doc = loads(raw)
    if (not isinstance(doc, dict) or doc.get('owner') != OWNER or doc.get('schema') != 1
            or set(doc.get('files', {})) != set(FILES) or not isinstance(doc.get('group'), dict)):
        raise ValueError('invalid guard ownership manifest')
    for key, value in doc['files'].items():
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError('invalid guard checksum')
        int(value, 16)
    # No paths from this manifest are used; known constant filenames only.
    return doc


def apply(changes, backup_root, dry_run, expected=None):
    before = {path: read_bytes(path) for path in changes}
    if expected and any(before.get(path) != data for path, data in expected.items()):
        raise ValueError("shared hook configuration changed; retry after reconciliation")
    changes = {p: b for p, b in changes.items() if b != before[p]}
    for path, data in changes.items():
        print(f'{"[dry-run] " if dry_run else ""}{"remove" if data is None else "write"}: {path}')
    if dry_run or not changes:
        return
    reject_links(backup_root)
    backup = backup_root / uuid4().hex
    backup.mkdir(parents=True, mode=0o700)
    journal = []
    for index, (path, after) in enumerate(changes.items()):
        if before[path] is not None:
            (backup / f'{index}.bin').write_bytes(before[path])
        journal.append({'path': str(path), 'before': digest(before[path]), 'after': digest(after)})
    (backup / 'changes.json').write_bytes(encode(journal))
    changed = []
    try:
        for path, data in changes.items():
            if read_bytes(path) != before[path]:
                raise ValueError(f'concurrent modification: {path}')
            replace(path, data)
            changed.append(path)
    except BaseException:
        for path in reversed(changed):
            replace(path, before[path])
        raise
    print(f'guard recovery backup: {backup}')


@contextmanager
def lock(backups):
    reject_links(backups)
    backups.mkdir(parents=True, exist_ok=True)
    path = backups / '.lock'
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(f'guard operation active or stale lock; inspect: {path}') from exc
    os.close(fd)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def lifecycle(action, scope, project_root=None, *, dry_run=False, force=False):
    if action not in ('install', 'remove', 'status'):
        raise ValueError('unknown action')
    directory, config, backups = targets(scope, project_root)
    for path in (directory, config, backups):
        reject_links(path)

    def operation():
        manifest = owned_manifest(directory)
        raw = read_bytes(config)
        doc = load_config(raw)
        groups = doc.get('hooks', {}).get('PreToolUse', [])
        if manifest:
            if groups.count(manifest['group']) != 1:
                raise ValueError('owned hook group changed/missing/duplicated; reconcile without removing other hooks')
            for name, expected in manifest['files'].items():
                if digest(read_bytes(directory / name)) != expected and not force:
                    raise ValueError(f'locally modified guard preserved: {name}')
        if action == 'status':
            print('guard registration: ' + ('PRESENT' if manifest else 'ABSENT'))
            print('native trust/coverage: NOT VERIFIED; inspect /hooks and run live canary')
            return
        if action == 'remove':
            if not manifest:
                print('no owned registration; nothing removed')
                return
            groups.remove(manifest['group'])
            if not groups:
                doc['hooks'].pop('PreToolUse')
            if not doc['hooks']:
                doc.pop('hooks')
            # Remove registration first; independent files last. Preserve foreign config.
            changes = {config: encode(doc)}
            changes.update({directory / name: None for name in FILES})
            changes[directory / 'manifest.json'] = None
            apply(changes, backups, dry_run, expected={config: raw})
            return
        payload = {name: (ROOT / 'hooks' / name).read_bytes() for name in FILES}
        if not manifest:
            for name in (*FILES, 'manifest.json'):
                if (directory / name).exists():
                    raise ValueError(f'unowned guard collision: {name}')
        group = group_for(directory)
        if not manifest and group in groups:
            raise ValueError('unowned identical registration exists; reconcile before claiming it')
        if manifest:
            groups = [group if old == manifest['group'] else old for old in groups]
        else:
            groups = [*groups, group]
        doc.setdefault('hooks', {})['PreToolUse'] = groups
        state = {'owner': OWNER, 'schema': 1, 'files': {n: digest(b) for n, b in payload.items()}, 'group': group}
        changes = {directory / n: b for n, b in payload.items()}
        changes[directory / 'manifest.json'] = encode(state)
        changes[config] = encode(doc)  # Registration last: no dangling hook on normal failure.
        apply(changes, backups, dry_run, expected={config: raw})
        print('Review/trust this exact definition using /hooks. Registration is NOT proof of enforcement.')
        print('Guard applies to Astra/unknown-model calls in this configuration scope, even without the Skill.')
    if dry_run or action == 'status':
        operation()
    else:
        with lock(backups):
            operation()


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('install', 'remove', 'status'))
    p.add_argument('--scope', choices=('user', 'project'), default='project')
    p.add_argument('--project-root', type=Path)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--force', action='store_true', help='only replace/remove edited OWNED guard scripts after backup')
    return p


def main():
    args = build_parser().parse_args()
    try:
        lifecycle(args.action, args.scope, args.project_root, dry_run=args.dry_run, force=args.force)
        return 0
    except (ValueError, OSError, TypeError) as exc:
        print(f'write guard: FAILED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
