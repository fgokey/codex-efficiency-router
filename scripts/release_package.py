#!/usr/bin/env python3
"""Offline release consistency checks and deterministic source/plugin ZIP packaging.

Creates artifacts only when requested. Never installs, calls models, tags, commits
or publishes. A candidate build is not a release-gate PASS.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

from release_identity import ROOT, source_identity, sha, canonical


def plugin_hooks(identity):
    suffix = ' --expected-bundle ' + identity['guard_sha256']
    return {'description': 'Explicit native write guardrail; review /hooks before use.',
            'hooks': {'PreToolUse': [{'matcher': '*', 'hooks': [{
                'type': 'command',
                'command': 'python3 -I -B "${PLUGIN_ROOT}/hooks/astra_write_guard.py"' + suffix,
                'commandWindows': 'python -I -B "$env:PLUGIN_ROOT/hooks/astra_write_guard.py"' + suffix,
                'timeout': 5, 'statusMessage': f"CER {identity['version']} Astra write boundary"}]}]}}


def validate_release(root=ROOT, *, schema=False):
    from write_guard import loads
    errors = []
    try:
        identity = source_identity(root); version = identity['version']
        manifest = loads((root / 'plugin.json').read_bytes())
        if manifest.get('$schema') != 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json':
            errors.append('plugin schema identity mismatch')
        if manifest.get('name') != 'codex-efficiency-router' or manifest.get('version') != version:
            errors.append('plugin name/version mismatch')
        if manifest.get('extensions', {}).get('com.openai', {}).get('hooks') != './hooks/hooks.json':
            errors.append('plugin hook path mismatch')
        if loads((root / 'hooks/hooks.json').read_bytes()) != plugin_hooks(identity):
            errors.append('plugin hook command/version/hash drift; regenerate through --sync-hooks')
        core = (root / 'skills/codex-efficiency-router/SKILL.md').read_text(encoding='utf-8')
        if re.findall(r'<!-- CER version: ([^ ]+) -->', core) != [version]:
            errors.append('Skill release marker mismatch')
        for name in ('astra_write_guard.py', 'readonly_reader.py'):
            tree = ast.parse((root / 'hooks' / name).read_text(encoding='utf-8'))
            values = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'VERSION' for t in node.targets)]
            if values != [version]:
                errors.append('Hook VERSION mismatch: ' + name)
        if loads((root / 'policy/routing-policy.json').read_bytes()).get('version') != version:
            errors.append('routing policy version mismatch')
        if f'## {version}' not in (root / 'CHANGELOG.md').read_text(encoding='utf-8'):
            errors.append('CHANGELOG entry missing')
        if schema:
            import jsonschema
            jsonschema.Draft202012Validator(loads((root / 'schemas/plugin.schema.json').read_bytes())).validate(manifest)
    except ImportError:
        errors.append('jsonschema unavailable; schema validation NOT RUN')
    except Exception as exc:
        errors.append(str(exc))
    return errors


def source_payload(root=ROOT):
    # Explicit distribution roots. Never include .git, credentials, backups,
    # previous evaluation logs or compiled bytecode from an uploaded worktree.
    directories = ('agents', 'config', 'docs', 'evaluation', 'hooks', 'policy', 'scripts', 'skills', 'tests', 'schemas', '.github')
    extensions = {'.py', '.json', '.toml', '.md', '.yaml', '.yml', '.sh', '.ps1'}
    payload = {}
    for directory in directories:
        for p in sorted((root / directory).rglob('*')):
            if '__pycache__' not in p.parts and p.is_file() and p.suffix in extensions:
                if p.is_symlink():
                    raise ValueError('distribution refuses symlinks')
                payload[p.relative_to(root).as_posix()] = p.read_bytes()
    for name in ('VERSION', 'LICENSE', 'README.md', 'README.zh-CN.md', 'CHANGELOG.md', 'AGENTS.md',
                 'CONTRIBUTING.md', 'SECURITY.md', 'SUPPORT.md', 'CODE_OF_CONDUCT.md',
                 '.editorconfig', '.gitattributes', '.gitignore', 'plugin.json',
                 'install.sh', 'install.ps1', 'uninstall.sh', 'uninstall.ps1', 'cer.ps1'):
        payload[name] = (root / name).read_bytes()
    return payload


def build(output: Path, root=ROOT):
    from manage import reject_links
    errors = validate_release(root)
    if errors:
        raise ValueError('; '.join(errors))
    reject_links(output)
    if output.exists():
        raise ValueError('package output already exists; choose a new path')
    payload = source_payload(root)
    identity = source_identity(root)
    manifest = {'schema': 1, **identity, 'release_state': 'candidate-unpublished',
                'source_tree_sha256': sha(canonical({n: sha(b) for n, b in payload.items()})),
                'files': {n: sha(b) for n, b in sorted(payload.items())},
                'live_canary': 'NOT_RUN', 'windows_ci': 'NOT_RUN', 'git_tag': 'NOT_CREATED'}
    payload['RELEASE-MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo('codex-efficiency-router/' + name, date_time=(2026, 9, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if name.endswith('.sh') else 0o100644) << 16
            z.writestr(info, data)
    return {'path': str(output), 'sha256': sha(output.read_bytes()), 'files': len(payload),
            'source_tree_sha256': manifest['source_tree_sha256'], 'release_state': manifest['release_state']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true'); p.add_argument('--schema', action='store_true')
    p.add_argument('--sync-hooks', action='store_true', help='explicitly regenerate OWN source hooks/hooks.json only')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    try:
        if args.sync_hooks:
            from manage import replace
            replace(ROOT / 'hooks/hooks.json', (json.dumps(plugin_hooks(source_identity()), indent=2) + '\n').encode())
        errors = validate_release(schema=args.schema)
        if errors:
            print(json.dumps({'status': 'FAIL', 'errors': errors}, indent=2)); return 1
        print(json.dumps(build(args.output) if args.output else {'status': 'STATIC_PASS', 'live': 'NOT_VERIFIED'}, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f'package: FAILED: {exc}', file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
