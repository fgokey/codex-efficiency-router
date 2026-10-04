"""Codex synchronous PreToolUse guard. Depends on actual hook coverage and trust.

Fail closed inside this process; host hook failure/opt-out paths need live acceptance.
No model call, transcript read, state file, event logging or permission grants.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import runpy
import shlex
import sys

VERSION = '0.8.5'

# Exact local read/orchestration tools only, never guess MCP semantics by its name.
READ_TOOLS = frozenset(('read_file', 'list_directory', 'search_files', 'read_thread'))
COORDINATE_TOOLS = frozenset(('spawn_agent', 'Agent', 'send_input', 'wait', 'wait_agent', 'close_agent', 'update_plan'))
EXECUTOR_FAMILIES = ('gpt-6.1-sol', 'gpt-6-sol', 'gpt-6-luna', 'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna')
SPAWN_ROLES = {'luna_worker': ('gpt-6-luna', 'high'), 'terra_executor': ('gpt-5.6-terra', 'medium'),
               'sol_engineer': ('gpt-6-sol', 'medium'), 'sol61_engineer': ('gpt-6.1-sol', 'medium'),
               'astra_architect': ('gpt-6-astra', 'high')}
PREFIX = 'cer-read '
REASON = ('CER strict Guard: Astra/unknown identity cannot write, build, format or run tests. '
          'Reuse an authorized exact-model executor owner or wait. Continue read-only diagnosis; '
          'for source inspection use cer-read {"op":"read","path":"..."}.')


def deny(reason: str = REASON) -> dict:
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny', 'permissionDecisionReason': reason}}


def duplicate_checked(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError('duplicate JSON key')
        data[key] = value
    return data


def reject_constant(value):
    raise ValueError('non-finite JSON value')


def command(argv: list[str], windows: bool | None = None) -> str:
    if windows is None:
        windows = os.name == 'nt'
    if windows:
        return '& ' + ' '.join("'" + arg.replace("'", "''") + "'" for arg in argv)
    return shlex.join(argv)


def validate_spawn(data: object) -> tuple[str, str]:
    """Check requested parameters only; grants no host identity or delegation authority."""
    if not isinstance(data, dict): raise ValueError('spawn requires explicit parameters')
    role = data.get('agent_type')
    automatic = isinstance(role, str) and role.startswith('cer_auto_')
    base = role.removeprefix('cer_auto_') if isinstance(role, str) else None
    if data.get('fork_turns') != 'none':
        raise ValueError('spawn requires fork_turns=none; hand off only necessary unit context')
    if base in SPAWN_ROLES:
        model, fixed_effort = SPAWN_ROLES[base]
        if 'model' in data and data['model'] != model:
            raise ValueError('spawn role/model mismatch')
        effort = data.get('reasoning_effort') if automatic else fixed_effort
        if not automatic and 'reasoning_effort' in data and data['reasoning_effort'] != effort:
            raise ValueError('spawn fixed-role effort mismatch')
    else:
        model, effort = data.get('model'), data.get('reasoning_effort')
        if model not in EXECUTOR_FAMILIES + ('gpt-6-astra',):
            raise ValueError('spawn default/inherit requires an explicit exact model pin')
    if effort not in ('low', 'medium', 'high', 'xhigh', 'max', 'ultra'):
        raise ValueError('spawn requires a bound reasoning_effort')
    return model, effort


def decide(event: object) -> dict:
    if not isinstance(event, dict) or event.get('hook_event_name') != 'PreToolUse':
        return deny('CER: invalid PreToolUse event; no tool execution authorized.')
    name = event.get('tool_name')
    if not isinstance(name, str) or not name:
        return deny('CER: missing canonical tool identity.')
    # Transported fields are trusted only when sent by the native host, not a worker.
    model = event.get('model')
    executor = isinstance(model, str) and model in EXECUTOR_FAMILIES
    # Snapshot aliases require an explicit audited addition, never prefix matching.
    data = event.get('tool_input')
    if name == 'spawn_agent':
        try: validate_spawn(data)
        except (ValueError, TypeError) as exc:
            return deny(f'CER spawn preflight: {exc}. No child binding or authority inferred.')
        return {}  # Other host/user policy still applies; parent must verify the new binding.
    marker = name == 'Bash' and isinstance(data, dict) and isinstance(data.get('command'), str) and data['command'].startswith(PREFIX)
    if marker:
        # This is a virtual request protocol, not a shell binary. Rewrite before shell.
        try:
            request = json.loads(data['command'][len(PREFIX):], object_pairs_hook=duplicate_checked, parse_constant=reject_constant)
            reader = Path(__file__).resolve().with_name('readonly_reader.py')
            runpy.run_path(str(reader))['validate'](request)
            cwd = event.get('cwd')
            if not isinstance(cwd, str) or not Path(cwd).is_absolute() or any(c in cwd for c in '\x00\r\n'):
                raise ValueError('invalid host workspace')
            encoded = base64.urlsafe_b64encode(json.dumps(request).encode()).decode()
            # Python ignores startup/import environment and does not write bytecode.
            argv = [str(Path(sys.executable).resolve()), '-I', '-B', str(reader), cwd, encoded]
            return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'allow',
                    'updatedInput': {'command': command(argv)}}}
        except (ValueError, OSError, KeyError, TypeError):
            return deny('CER: invalid guarded-read request; do not fall back to an arbitrary shell.')
    if executor:
        # Empty output does NOT grant permission or bypass other hooks/sandbox.
        return {}
    if name in READ_TOOLS or name in COORDINATE_TOOLS:
        return {}
    # Includes apply_patch, all ordinary Bash, build/test scripts, MCP, nested execution
    # wrappers and unknown tools. A dry-run label or claimed tool_input.model is irrelevant.
    return deny()


def main() -> int:
    try:
        if sys.argv[1:]:
            if len(sys.argv) != 3 or sys.argv[1] != '--expected-bundle':
                raise ValueError('unsupported guard arguments')
            directory = Path(__file__).resolve().parent
            files = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                     for name in ('astra_write_guard.py', 'readonly_reader.py')}
            actual = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':'),
                                               ensure_ascii=True).encode()).hexdigest()
            if actual != sys.argv[2]:
                raise ValueError('guard bundle changed since review')
        raw = sys.stdin.buffer.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('oversized event')
        event = json.loads(raw, object_pairs_hook=duplicate_checked, parse_constant=reject_constant)
        output = decide(event)
    except Exception:
        output = deny('CER: guard input/processing failed; do not execute this call.')
    if output:
        print(json.dumps(output, separators=(',', ':'), ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
