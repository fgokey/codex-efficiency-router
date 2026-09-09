"""Read-only release identity; disk identity is never evidence of runtime loading."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
GUARD_FILES = ('astra_write_guard.py', 'readonly_reader.py')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def bundle_hash(directory: Path) -> str:
    return sha(canonical({name: sha((directory / name).read_bytes()) for name in GUARD_FILES}))


def policy_hash(skill: Path) -> str:
    # Include every packaged reference; a profile-rendered Skill gets its own hash.
    paths = [skill / 'SKILL.md', *sorted((skill / 'references').glob('*.md'))]
    return sha(canonical({p.relative_to(skill).as_posix(): sha(p.read_bytes()) for p in paths}))


def source_identity(root: Path = ROOT) -> dict:
    version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', version):
        raise ValueError('invalid VERSION')
    # git is only inspected for provenance, never executed on ordinary tool calls.
    commit = 'UNKNOWN'
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS='0')
    try:
        result = subprocess.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                                 '-C', str(root), 'rev-parse', '--verify', 'HEAD'],
                                env=env, capture_output=True, text=True, timeout=3)
        if result.returncode == 0 and re.fullmatch(r'[0-9a-f]{40,64}', result.stdout.strip()):
            commit = result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    manifest = root / 'RELEASE-MANIFEST.json'
    if commit == 'UNKNOWN' and manifest.is_file():
        try:
            value = json.loads(manifest.read_text(encoding='utf-8')).get('base_commit')
            if isinstance(value, str) and re.fullmatch(r'[0-9a-f]{40,64}', value):
                commit = value
        except (OSError, ValueError, AttributeError):
            pass
    return {'version': version, 'base_commit': commit,
            'policy_sha256': policy_hash(root / 'skills/codex-efficiency-router'),
            'guard_sha256': bundle_hash(root / 'hooks')}
