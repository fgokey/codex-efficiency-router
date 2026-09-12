#!/usr/bin/env python3
"""Explicit native Hook lifecycle and read-only diagnostics. No automatic trust.

Only owned files and the exact owned hook group may change. Use a quiescent config
scope; compare-before-write is not an OS transaction against malicious local races.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse
from contextlib import contextmanager, redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tomllib
from uuid import uuid4

from manage import reject_links, read_bytes, replace, digest
from package import resolve_targets, MANIFEST
from release_identity import GUARD_FILES, bundle_hash, source_identity, canonical, sha, policy_hash

OWNER = 'cer-astra-write-guard'
FILES = GUARD_FILES
ROOT = Path(__file__).resolve().parents[1]


def loads(raw):
    def unique(items):
        out = {}
        for key, val in items:
            if key in out:
                raise ValueError('duplicate JSON key')
            out[key] = val
        return out
    def constant(value):
        raise ValueError('non-finite JSON value')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=constant)


def encode(data):
    return (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def shell_command(args):
    if os.name == 'nt':
        return '& ' + ' '.join("'" + arg.replace("'", "''") + "'" for arg in args)
    return shlex.join(args)


def targets(scope, project_root):
    _, agents, backups = resolve_targets(scope, project_root)
    base = agents.parent
    return base / 'hooks' / OWNER, base / 'hooks.json', backups / OWNER


def group_for(directory):
    identity = source_identity(ROOT)
    return {'matcher': '*', 'hooks': [{'type': 'command',
            'command': shell_command([str(Path(sys.executable).resolve()), '-I', '-B',
                       str(directory / FILES[0]), '--expected-bundle', identity['guard_sha256']]),
              'timeout': 5, 'statusMessage': f"CER {identity['version']} strict Astra write boundary"}]}


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
            or not isinstance(doc.get('files'), dict) or set(doc['files']) != set(FILES)
            or not isinstance(doc.get('group'), dict)):
        raise ValueError('invalid guard ownership manifest')
    for value in doc['files'].values():
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            raise ValueError('invalid guard checksum')
    return doc


def apply(changes, backup_root, dry_run, expected=None):
    before = {path: read_bytes(path) for path in changes}
    if expected and any(before.get(path) != data for path, data in expected.items()):
        raise ValueError('shared hook configuration changed; retry after reconciliation')
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
        # Do not overwrite a concurrent edit made AFTER this operation wrote a file.
        for path in reversed(changed):
            try:
                if read_bytes(path) == changes[path]:
                    replace(path, before[path])
                else:
                    print(f'rollback preserved concurrent change: {path}', file=sys.stderr)
            except (OSError, ValueError) as exc:
                print(f'rollback requires manual recovery: {path}: {exc}', file=sys.stderr)
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


def inspect_status(scope='project', project_root=None):
    """Inspect only this config layer. Do not execute any command found in config."""
    directory, config, _ = targets(scope, project_root)
    identity = source_identity(ROOT)
    result = {'registration_kind': 'standalone-native',
              'plugin_registration': 'UNKNOWN', 'other_config_layers': 'UNKNOWN','schema': 1, 'router': identity, 'installation_mode': 'policy-only',
              'scope': scope, 'registration_path': str(config), 'guard_directory': str(directory),
              'registration': 'ABSENT', 'registered_version': 'UNKNOWN',
              'trust': 'UNKNOWN', 'live_verification': 'NOT_RUN', 'runtime_loaded_version': 'UNKNOWN',
              'interpreter': 'UNKNOWN', 'interpreter_exists': None, 'interpreter_runnable': 'UNKNOWN',
              'guard_sha256': None, 'config_sha256': None, 'fingerprint': None,
              'overlapping_groups': [], 'errors': [], 'warnings': [],
              'coverage': {'native_hooked_paths': 'NOT_LIVE_VERIFIED', 'write_stdin': 'UNPROTECTED',
                           'hosted_tools': 'UNPROTECTED', 'specialized_paths': 'UNKNOWN',
                           'other_config_layers': 'UNKNOWN'}}
    try:
        reject_links(directory)
        reject_links(config)
        raw = read_bytes(config)
        result['config_sha256'] = digest(raw)
        doc = load_config(raw)
        manifest = owned_manifest(directory)
        groups = doc.get('hooks', {}).get('PreToolUse', [])
        result['config_parse'] = 'PASS'
        if not manifest:
            leftovers = any((directory / name).exists() for name in (*FILES, 'manifest.json'))
            result['registration'] = 'BROKEN' if leftovers else 'ABSENT'
            if leftovers:
                result['errors'].append('guard files without a valid ownership manifest')
        else:
            result['installation_mode'] = 'guarded'
            result['registration'] = 'PRESENT'
            result['registered_version'] = manifest.get('version', 'UNKNOWN')
            result['registered_base_commit'] = manifest.get('base_commit', 'UNKNOWN')
            result['registered_policy_sha256'] = manifest.get('policy_sha256', 'UNKNOWN')
            count = groups.count(manifest['group'])
            if count != 1:
                result['errors'].append('owned hook group missing/changed/duplicated')
            file_hashes = {name: digest(read_bytes(directory / name)) for name in FILES}
            result['file_sha256'] = file_hashes
            if file_hashes != manifest['files']:
                result['errors'].append('owned guard files are missing or modified')
            else:
                result['guard_sha256'] = bundle_hash(directory)
            interpreter = manifest.get('interpreter')
            if isinstance(interpreter, str) and Path(interpreter).is_absolute():
                result['interpreter'] = interpreter
                result['interpreter_exists'] = Path(interpreter).is_file()
                if not result['interpreter_exists']:
                    result['errors'].append('registered Python interpreter is missing')
                else:
                    expected = shell_command([interpreter, '-I', '-B', str(directory / FILES[0]),
                                              '--expected-bundle', manifest.get('guard_sha256', '')])
                    handler = manifest['group'].get('hooks', [{}])[0]
                    if handler.get('command') != expected:
                        result['errors'].append('registered command differs from the declared interpreter/scripts')
                    if os.name != 'nt' and not os.access(interpreter, os.X_OK):
                        result['errors'].append('registered interpreter is not executable')
            else:
                result['warnings'].append('legacy interpreter binding UNKNOWN; update then review /hooks')
            if (manifest.get('version') != identity['version']
                    or result['guard_sha256'] != identity['guard_sha256']
                    or not interpreter):
                result['registration'] = 'OUTDATED'
            if result['errors']:
                result['registration'] = 'BROKEN'
            for index, group in enumerate(groups):
                if group != manifest['group'] or count > 1:
                    # Ours is '*': ANY other matcher can overlap; no regex guessing.
                    result['overlapping_groups'].append({'index': index, 'matcher': group.get('matcher', '*')})
            if result['overlapping_groups']:
                result['warnings'].append('overlapping PreToolUse definitions; preserved, not disabled')
        skill, _, _ = resolve_targets(scope, project_root)
        skill_raw = read_bytes(skill / MANIFEST)
        installed = loads(skill_raw) if skill_raw else {}
        result['skill_version'] = installed.get('version', 'UNKNOWN')
        result['routing_mode'] = installed.get('mode', 'UNKNOWN')
        result['automatic_low'] = installed.get('allow_low', 'UNKNOWN')
        actual_policy = policy_hash(skill) if (skill / 'SKILL.md').is_file() else None
        result['installed_policy_sha256'] = actual_policy
        if installed and installed.get('policy_sha256') not in (None, actual_policy):
            result['warnings'].append('installed Skill/reference bytes changed after installation')
        if installed and manifest and result['skill_version'] != result['registered_version']:
            result['warnings'].append('installed Skill/Guard version drift')
        # Include inline hooks in the SAME layer, without reporting unrelated config.
        cfg = read_bytes(config.with_name('config.toml'))
        if cfg:
            cfg_doc = tomllib.loads(cfg.decode('utf-8'))
            inline = cfg_doc.get('hooks', {}).get('PreToolUse', [])
            if inline:
                result['warnings'].append('same-layer config.toml also defines PreToolUse; overlap possible')
            if cfg_doc.get('features', {}).get('hooks') is False or cfg_doc.get('features', {}).get('codex_hooks') is False:
                result['warnings'].append('same-layer hooks feature disabled; effective host state UNKNOWN')
        result['fingerprint'] = sha(canonical({'scope': scope, 'config_path': str(config),
                     'config_sha256': result['config_sha256'], 'guard_sha256': result['guard_sha256'],
                     'interpreter': result['interpreter'], 'config_toml_sha256': digest(cfg),
                     'skill_manifest_sha256': digest(skill_raw), 'actual_policy_sha256': actual_policy}))
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        result['registration'] = 'BROKEN'
        result['errors'].append(str(exc))
    if result['registration'] in ('ABSENT', 'BROKEN'):
        result['installation_mode'] = 'policy-only'
    return result


def lifecycle(action, scope, project_root=None, *, dry_run=False, force=False):
    if action not in ('install', 'update', 'remove', 'status', 'doctor'):
        raise ValueError('unknown action')
    if action in ('status', 'doctor'):
        result = inspect_status(scope, project_root)
        print('guard registration: ' + result['registration'])
        print('native trust/coverage: UNKNOWN; inspect /hooks and run live canary')
        for message in result['errors'] + result['warnings']:
            print('- ' + message)
        return result
    directory, config, backups = targets(scope, project_root)
    for path in (directory, config, backups):
        reject_links(path)

    def operation():
        manifest = owned_manifest(directory)
        raw = read_bytes(config)
        doc = load_config(raw)
        groups = doc.get('hooks', {}).get('PreToolUse', [])
        if action == 'update' and not manifest:
            raise ValueError('no owned Guard to update; use explicit install')
        if manifest:
            if groups.count(manifest['group']) != 1:
                raise ValueError('owned hook group changed/missing/duplicated; reconcile without removing other hooks')
            for name, expected in manifest['files'].items():
                if digest(read_bytes(directory / name)) != expected and not force:
                    raise ValueError(f'locally modified guard preserved: {name}')
        if action == 'remove':
            if not manifest:
                print('no owned registration; nothing removed')
                return
            groups.remove(manifest['group'])
            if not groups:
                doc['hooks'].pop('PreToolUse')
            if not doc['hooks']:
                doc.pop('hooks')
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
        identity = source_identity(ROOT)
        state = {'owner': OWNER, 'schema': 1, 'version': identity['version'],
                 'base_commit': identity['base_commit'], 'policy_sha256': identity['policy_sha256'],
                 'guard_sha256': identity['guard_sha256'], 'interpreter': str(Path(sys.executable).resolve()),
                 'files': {n: digest(b) for n, b in payload.items()}, 'group': group}
        changes = {directory / n: b for n, b in payload.items()}
        changes[directory / 'manifest.json'] = encode(state)
        changes[config] = encode(doc)
        apply(changes, backups, dry_run, expected={config: raw})
        print('Review/trust this exact definition using /hooks. Registration is NOT proof of enforcement.')
        print('Guard applies to Astra/unknown-model calls in this configuration scope, even without the Skill.')
    if dry_run:
        operation()
    else:
        with lock(backups):
            operation()


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('install', 'update', 'remove', 'status', 'doctor'))
    p.add_argument('--scope', choices=('user', 'project'), default='project')
    p.add_argument('--project-root', type=Path)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--json', action='store_true', dest='as_json')
    p.add_argument('--canary-report', type=Path, help='explicit operator-witnessed native Canary report')
    p.add_argument('--codex-version', help='observed current Codex version, never inferred from old report')
    p.add_argument('--force', action='store_true', help='only replace/remove edited OWNED scripts after backup')
    return p


def main():
    args = build_parser().parse_args()
    try:
        if args.action in ('status', 'doctor'):
            result = inspect_status(args.scope, args.project_root)
            if args.canary_report:
                from canary import evaluate_saved_report
                result = evaluate_saved_report(result, loads(args.canary_report.read_bytes()), args.codex_version)
            if args.as_json:
                print(json.dumps(result, indent=2, allow_nan=False))
            else:
                print(f"guard registration: {result['registration']}; mode: {result['installation_mode']}")
                print(f"trust: {result['trust']}; live: {result['live_verification']}; runtime loaded: UNKNOWN")
                for message in result['errors'] + result['warnings']:
                    print('- ' + message)
            return 1 if args.action == 'doctor' and result['registration'] in ('BROKEN', 'OUTDATED') else 0
        if args.as_json:
            output = io.StringIO()
            with redirect_stdout(output):
                lifecycle(args.action, args.scope, args.project_root, dry_run=args.dry_run, force=args.force)
            print(json.dumps({'action': args.action, 'dry_run': args.dry_run, 'status': 'PASS',
                              'operations': output.getvalue().splitlines()}, indent=2))
        else:
            lifecycle(args.action, args.scope, args.project_root, dry_run=args.dry_run, force=args.force)
        return 0
    except (ValueError, OSError, TypeError) as exc:
        if args.as_json:
            print(json.dumps({'status': 'FAIL', 'error': str(exc)}))
        else:
            print(f'write guard: FAILED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
