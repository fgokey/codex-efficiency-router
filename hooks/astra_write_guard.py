"""Codex synchronous PreToolUse guard. Depends on actual hook coverage and trust.

Fail closed inside this process; host hook failure/opt-out paths need live acceptance.
No model call, transcript read, state file, event logging or permission grants.
"""
from __future__ import annotations
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import sqlite3
import sys

VERSION = '0.8.5'

# Exact local read/orchestration tools only, never guess MCP semantics by its name.
READ_TOOLS = frozenset(('read_file', 'list_directory', 'search_files', 'read_thread'))
COORDINATE_TOOLS = frozenset(('spawn_agent', 'Agent', 'send_input', 'wait', 'wait_agent', 'close_agent', 'update_plan'))
EXECUTOR_FAMILIES = ('gpt-6.1-sol', 'gpt-6-sol', 'gpt-6-luna', 'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna')
SPAWN_ROLES = {'luna_worker': ('gpt-6-luna', 'high'), 'terra_executor': ('gpt-5.6-terra', 'medium'),
               'sol_engineer': ('gpt-6-sol', 'medium'), 'sol61_engineer': ('gpt-6.1-sol', 'high'),
               'astra_architect': ('gpt-6-astra', 'high')}
PREFIX = 'cer-read '
HOLD_MESSAGE = 'HOLD. Report only your identity and working directory; do not use tools or accept work until RELEASE.'
ASSIGNMENT_PREFIX = 'CER assignment (caller evidence): '
DISPATCH_TOOLS = frozenset(('spawn_agent', 'resume_agent', 'send_input', 'followup_task', 'send_message'))
DISPATCH_ALIASES = {name: name for name in DISPATCH_TOOLS}
DISPATCH_ALIASES.update({f'collaboration.{name}': name for name in DISPATCH_TOOLS})
DISPATCH_ALIASES.update({'collaborationfollowup_task': 'followup_task',
                         'collaborationspawn_agent': 'spawn_agent',
                         'collaborationsend_input': 'send_input',
                         'collaborationsend_message': 'send_message',
                         'collaborationresume_agent': 'resume_agent'})
DISPATCH_ALIASES.update({f'functions.{name}': name for name in DISPATCH_TOOLS})
DISPATCH_ALIASES.update({name: 'spawn_agent' for name in ('Agent', 'collaboration.Agent', 'functions.Agent')})
DISPATCH_ALIASES.update({name: 'send_message_to_thread' for name in (
    'send_message_to_thread', 'mcp__codex_app__send_message_to_thread', 'mcp__codex_app.send_message_to_thread',
    'functions.mcp__codex_app__send_message_to_thread')})
DISPATCH_MATCHER = '^(?:' + '|'.join(re.escape(name) for name in sorted(DISPATCH_ALIASES)) + ')$'
HOST_DIRECTORY = Path.home() / '.codex'
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


def host_recipient(session_id: object, target: object, directory: Path) -> dict:
    """Adapter for the native state_5 threads schema. No writable connection/cache."""
    if not all(isinstance(value, str) and value and len(value) <= 512
               for value in (session_id, target)):
        raise ValueError('missing host session or recipient')
    database = directory / 'state_5.sqlite'
    # mode=ro observes WAL normally; immutable would silently miss current rows.
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True, timeout=0.2)) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        required = {'id', 'model', 'reasoning_effort', 'source', 'thread_source',
                    'agent_role', 'agent_path', 'archived', 'rollout_path'}
        columns = {row[1] for row in db.execute('PRAGMA table_info(threads)')}
        if not required <= columns:
            raise ValueError('unsupported native state_5 threads schema')
        current = db.execute('SELECT model, reasoning_effort, archived FROM threads WHERE id=? LIMIT 2',
                             (session_id,)).fetchall()
        if len(current) != 1 or current[0][2] != 0 or not all(
                isinstance(value, str) and value for value in current[0][:2]):
            raise ValueError('current host caller identity UNKNOWN')
        rows = db.execute('SELECT id, model, reasoning_effort, source, archived FROM threads '
                          'WHERE id=? LIMIT 2', (target,)).fetchall()
        if not rows:
            # Paths are resolved only inside the current caller's direct children.
            candidates = db.execute('SELECT id, model, reasoning_effort, source, archived '
                                    'FROM threads WHERE agent_path=? LIMIT 1025', (target,)).fetchall()
            if len(candidates) > 1024:
                raise ValueError('recipient path resolution exceeds bounded adapter limit')
            rows = [row for row in candidates if recipient_owner(row[3]) == session_id]
        if len(rows) != 1:
            raise ValueError('recipient identity missing or ambiguous')
        identifier, model, effort, source, archived = rows[0]
        if archived != 0 or recipient_owner(source) != session_id:
            raise ValueError('recipient is archived or belongs to another parent')
        if model not in ('gpt-6.1-sol', 'gpt-6-astra') or effort not in (
                'medium', 'high', 'xhigh', 'max', 'ultra'):
            raise ValueError('recipient model/effort UNKNOWN or outside current admission policy')
        return {'id': identifier, 'model': model, 'effort': effort,
                'evidence_ref': 'native state_5.sqlite threads; current direct-parent ownership'}


def recipient_owner(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    try:
        data = json.loads(raw, object_pairs_hook=duplicate_checked, parse_constant=reject_constant)
        owner = data['subagent']['thread_spawn']['parent_thread_id']
        return owner if isinstance(owner, str) and owner else None
    except (ValueError, TypeError, KeyError):
        return None


def dispatch_message(data: object, name: str) -> tuple[str, str]:
    if not isinstance(data, dict):
        raise ValueError('dispatch arguments must be an object')
    target_key = 'target' if name in ('followup_task', 'send_message') else 'id'
    if name == 'send_message_to_thread':
        target_key = 'threadId'
    allowed = ({'threadId', 'prompt', 'hostId', 'model', 'thinking'} if name == 'send_message_to_thread'
               else {'id', 'message', 'interrupt'} if name == 'send_input' else {'target', 'message'})
    if set(data) - allowed:
        raise ValueError('unsupported dispatch arguments/additional task carriers')
    if 'interrupt' in data and type(data['interrupt']) is not bool:
        raise ValueError('interrupt must be a boolean, not another task carrier')
    if name == 'send_message_to_thread' and data.get('hostId') not in (None, 'local'):
        raise ValueError('remote application dispatch has no current local identity adapter')
    target, message = data.get(target_key), data.get('prompt' if name == 'send_message_to_thread' else 'message')
    if not isinstance(target, str) or not target or not isinstance(message, str) or not message:
        raise ValueError('dispatch requires an exact target and task message')
    return target, message


def admit_text(text: str, receiver: dict, policy_root: Path | None) -> str:
    header, separator, body = text.partition('\n')
    if not separator or not header.startswith(ASSIGNMENT_PREFIX):
        raise ValueError('current assignment envelope required; receipts/continue grant no exemption')
    receipt = json.loads(header[len(ASSIGNMENT_PREFIX):], object_pairs_hook=duplicate_checked,
                         parse_constant=reject_constant)
    if not isinstance(receipt, dict) or not isinstance(receipt.get('admission'), dict):
        raise ValueError('complete current admission fields required')
    if set(receipt) - {'recipient_id', 'unit_id', 'model', 'effort', 'evidence_ref',
                       'scope_sha256', 'message_sha256', 'policy_sha256', 'admission'}:
        raise ValueError('unsupported assignment envelope fields')
    request = dict(receipt['admission'])
    if set(request) - {'unit_id', 'purpose', 'scope', 'signals', 'complexity_reason',
                       'confirmed_simple', 'effort_supported', 'effort_reason'}:
        raise ValueError('unsupported current admission fields')
    signals = request.get('signals')
    if not isinstance(signals, dict) or set(signals) - {
            'spec_complete', 'authority_ready', 'environment_ready', 'observability_ready',
            'force_astra', 'cheap_check_available', 'very_complex', 'reasoning_bound',
            'sol61_unsuitable_reason', 'uncertainty', 'risk', 'coupling', 'evidence_conflict',
            'capability_failure', 'irreversibility', 'novelty'}:
        raise ValueError('unsupported current admission signals')
    if request.get('purpose') != 'new_unit' or 'receipt' in request:
        raise ValueError('native task messages require fresh purpose=new_unit admission')
    if receiver['model'] == 'gpt-6-astra':
        signals = request.get('signals')
        if not isinstance(signals, dict) or not isinstance(request.get('complexity_reason'), str):
            raise ValueError('Astra requires current complexity and Sol61-unsuitable reasons')
        unsuitable = signals.get('sol61_unsuitable_reason')
        if not isinstance(unsuitable, str):
            raise ValueError('Astra requires a current Sol61-unsuitable reason')
        judgment = ('Parent judgment: very complex; ' + request['complexity_reason'].strip()
                    + '\nSol61 unsuitable: ' + unsuitable.strip() + '\n')
        if not body.startswith(judgment):
            raise ValueError('Astra readable reasons differ from current admission')
        body = body[len(judgment):]
    reader = runpy.run_path(str(Path(__file__).resolve().with_name('readonly_reader.py')))
    if policy_root is None or not policy_root.is_absolute():
        raise ValueError('registered policy root UNKNOWN')
    policy = reader['assignment_policy_sha256'](policy_root)
    expected = {'recipient_id': receiver['id'], 'model': receiver['model'], 'effort': receiver['effort'],
                'policy_sha256': policy, 'unit_id': request.get('unit_id'),
                'scope_sha256': hashlib.sha256(request.get('scope', '').encode('utf-8')).hexdigest(),
                'message_sha256': hashlib.sha256(body.encode('utf-8')).hexdigest()}
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError('assignment target/body/identity/policy mismatch')
    request.update(purpose='new_unit', message=body, recipient=receiver)
    request.pop('receipt', None)
    result = reader['assignment_preflight'](request, policy_sha256=policy)
    if result['status'] != 'VERIFIED':
        raise ValueError('current task admission ' + result['status'])
    return body


def decide_dispatch(event: object, *, host_directory: Path = HOST_DIRECTORY,
                    policy_root: Path | None = None) -> dict:
    spawn_call = False
    try:
        if not isinstance(event, dict) or event.get('hook_event_name') != 'PreToolUse':
            raise ValueError('invalid PreToolUse event')
        name, data = event.get('tool_name'), event.get('tool_input')
        if not isinstance(name, str) or not name:
            raise ValueError('missing canonical tool identity')
        canonical = DISPATCH_ALIASES.get(name)
        if canonical is None:
            return {}  # This separate boundary never imposes the Astra write Guard.
        if canonical == 'resume_agent':
            raise ValueError('native resume cannot bind current model/effort; fresh admitted HOLD spawn required')
        if canonical == 'spawn_agent':
            spawn_call = True
            if not isinstance(data, dict):
                raise ValueError('spawn requires explicit parameters')
            spawn = dict(data)
            if 'fork_context' in spawn:
                if spawn.pop('fork_context') is not False or spawn.get('fork_turns', 'none') != 'none':
                    raise ValueError('spawn cannot inherit context or use conflicting context flags')
                spawn['fork_turns'] = 'none'
            model, effort = validate_spawn(spawn)
            if set(data) - {'agent_type', 'model', 'reasoning_effort', 'fork_turns', 'fork_context', 'message', 'task_name'}:
                raise ValueError('unsupported spawn schema/additional task carriers')
            if 'task_name' in data and (not isinstance(data['task_name'], str)
                    or re.fullmatch('[a-z][a-z0-9_]{0,63}', data['task_name']) is None):
                raise ValueError('spawn task name must be an identifier')
            if model not in ('gpt-6.1-sol', 'gpt-6-astra') or effort not in (
                    'medium', 'high', 'xhigh', 'max', 'ultra'):
                raise ValueError('spawn outside current model/effort admission policy')
            text = data.get('message')
            # Astra is admitted even for HOLD creation; requested identity is not a host binding.
            if model == 'gpt-6-astra' or effort != 'high' or text != HOLD_MESSAGE:
                if not isinstance(text, str):
                    raise ValueError('spawn requires the fixed identity HOLD')
                receiver = {'id': 'unbound-spawn', 'model': model, 'effort': effort,
                            'evidence_ref': 'explicit requested spawn pin; no actual host binding yet'}
                text = admit_text(text, receiver, policy_root)
            if text != HOLD_MESSAGE:
                raise ValueError('spawn body must be exactly: ' + HOLD_MESSAGE)
            return {}
        target, text = dispatch_message(data, canonical)
        receiver = host_recipient(event.get('session_id'), target, host_directory)
        if canonical == 'send_message_to_thread' and any(
                key in data and data[key] != receiver[identity] for key, identity in (
                    ('model', 'model'), ('thinking', 'effort'))):
            raise ValueError('application message cannot change the admitted recipient identity')
        admit_text(text, receiver, policy_root)
        return {}
    except Exception as exc:
        hint = ''
        if spawn_call:
            reader = Path(__file__).resolve().with_name('readonly_reader.py')
            installed = policy_root / 'scripts/readonly_reader.py' if isinstance(policy_root, Path) else None
            if installed is not None and installed.is_file():
                reader = installed
            hint = ' Help: ' + command([str(Path(sys.executable).resolve()), '-I', '-B',
                                       str(reader), 'assignment', '--help'])
        return deny('CER dispatch admission denied: ' + str(exc)[:240] + hint)


def decide(event: object, *, dispatch_only: bool = False,
           host_directory: Path = HOST_DIRECTORY, policy_root: Path | None = None) -> dict:
    if dispatch_only:
        return decide_dispatch(event, host_directory=host_directory, policy_root=policy_root)
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
    if name == 'resume_agent':
        return deny('CER native resume cannot bind model/effort. Hand off the owned unit; '
                    'fresh spawn with explicit role/model/effort, verify host binding, then RELEASE.')
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
        args = list(sys.argv[1:])
        dispatch_only = '--dispatch-only' in args
        if dispatch_only:
            args.remove('--dispatch-only')
        policy_root = None
        if '--policy-root' in args:
            index = args.index('--policy-root')
            policy_root = Path(args[index + 1])
            del args[index:index + 2]
        if args:
            if len(args) != 2 or args[0] != '--expected-bundle':
                raise ValueError('unsupported guard arguments')
            directory = Path(__file__).resolve().parent
            files = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                     for name in ('astra_write_guard.py', 'readonly_reader.py')}
            actual = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':'),
                                               ensure_ascii=True).encode()).hexdigest()
            if actual != args[1]:
                raise ValueError('guard bundle changed since review')
        raw = sys.stdin.buffer.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('oversized event')
        event = json.loads(raw, object_pairs_hook=duplicate_checked, parse_constant=reject_constant)
        output = decide(event, dispatch_only=dispatch_only, policy_root=policy_root)
    except Exception:
        output = deny('CER: guard input/processing failed; do not execute this call.')
    if output:
        print(json.dumps(output, separators=(',', ':'), ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
