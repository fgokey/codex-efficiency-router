"""Manifest-owned, backed-up installation; explicit child defaults are reversible.

Per-file replacement is atomic. Ordinary write failures roll back; a process/OS
crash across different directories is not atomic. Retained backups support recovery.
Run only in a trusted, quiescent local configuration directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import tomllib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

from package import AGENT_FILES, MANAGED_AGENT_FILES, MANIFEST, PROJECT, resolve_targets
from profiles import Profile, from_manifest, render_payload, select_profile

# Exact text blobs from the published v0.1.0 tree. Adoption is always explicit.
LEGACY = {
    "skill/SKILL.md": "0822cf0862672210dd6430a529b2016c4ca568fe",
    "agents/luna-worker.toml": "db605c8b343ff224e4d296cf5e1e57e1f9b9bd19",
    "agents/terra-executor.toml": "09a7acd43144f669226a9bf0ffe3dc6f70e14707",
    "agents/sol-engineer.toml": "8af1dd2b1760e90515e1e046252de621223a04d7",
    "agents/astra-architect.toml": "386c6f05628bdea3e460329f59b3c80f0361d6c2",
}

CONFIG_KEY = "config/config.toml"
SUBAGENT_DEFAULTS = {"default_subagent_model": "gpt-6.1-sol",
                    "default_subagent_reasoning_effort": "high"}
DEFAULTS_MARKER = "# codex-efficiency-router: child defaults"


def subagent_defaults(raw: bytes | None, owned: dict | None = None, *, remove=False,
                      migrate=False, _legacy=False):
    """Own only inserted scalars; preserve existing equal values and unrelated bytes."""
    text = (raw or b"").decode("utf-8")
    parsed = tomllib.loads(text)
    values = parsed.get("agents", {})
    if not isinstance(values, dict):
        raise ValueError("agents must be a TOML table")
    defaults = dict(SUBAGENT_DEFAULTS)
    if _legacy:
        defaults['default_subagent_reasoning_effort'] = 'medium'
    if (migrate and not _legacy and isinstance(owned, dict)
            and defaults['default_subagent_reasoning_effort'] == 'high'
            and isinstance(owned.get('fields'), list)
            and ('default_subagent_reasoning_effort' in owned['fields'] or remove)
            and values.get('default_subagent_reasoning_effort') == 'medium'):
        subagent_defaults(raw, owned, _legacy=True)  # Validate old ownership before changing any byte.
        if remove:
            return subagent_defaults(raw, owned, remove=True, _legacy=True)
        old_block = owned['block']
        new_block = old_block.replace('default_subagent_reasoning_effort = "medium"',
                                      'default_subagent_reasoning_effort = "high"', 1)
        migrated = text.replace(old_block, new_block, 1).encode('utf-8')
        return subagent_defaults(migrated, {**owned, 'block': new_block})
    for key, expected in defaults.items():
        if key in values and values[key] != expected:
            raise ValueError(f"conflicting agents.{key}; existing customization preserved")
    if owned is not None:
        if (not isinstance(owned, dict) or set(owned) != {"fields", "block", "header", "prefix", "created"}
                or not isinstance(owned["fields"], list)
                or any(not isinstance(key, str) for key in owned["fields"])
                or owned["fields"] != [key for key in SUBAGENT_DEFAULTS if key in owned["fields"]]
                or any(not isinstance(owned[key], str) for key in ("block", "header", "prefix"))
                or type(owned["created"]) is not bool):
            raise ValueError("invalid child-default ownership")
        if any(values.get(key) != value for key, value in defaults.items()):
            raise ValueError("managed child defaults missing or modified")
        block = owned["block"]
        forms = []
        for newline in ("\n", "\r\n"):
            canonical = DEFAULTS_MARKER + newline + "".join(
                f'{key} = "{defaults[key]}"{newline}' for key in owned["fields"])
            canonical += "# end codex-efficiency-router: child defaults" + newline
            forms.extend((canonical, newline + canonical))
        if ((owned["fields"] and block not in forms)
                or (not owned["fields"] and any((block, owned["header"], owned["prefix"], owned["created"])))
                or owned["header"] not in ("", "[agents]\n", "[agents]\r\n")
                or owned["prefix"] not in ("", "\n", "\r\n")
                or (owned["prefix"] and not owned["header"])
                or (owned["created"] and (not owned["header"] or owned["prefix"]))
                or (owned["header"] and not block.startswith(DEFAULTS_MARKER + owned["header"][8:]))
                or (owned["prefix"] and not owned["header"].endswith(owned["prefix"]))):
            raise ValueError("invalid child-default ownership text")
        if block and text.count(block) != 1:
            raise ValueError("managed child-default block missing or modified")
        if not remove or not block:
            return raw, owned
        text = text.replace(block, "", 1)
        header = owned["header"]
        if header and not tomllib.loads(text).get("agents"):
            segment = owned["prefix"] + header
            if text.count(segment) != 1:
                raise ValueError("managed agents table changed; config preserved")
            suffix = text[text.index(segment) + len(segment):]
            text = text.replace(segment if not suffix else header, "", 1)
        expected = dict(parsed)
        expected["agents"] = {key: value for key, value in values.items() if key not in owned["fields"]}
        if header and not expected["agents"]:
            del expected["agents"]
        if tomllib.loads(text) != expected:
            raise ValueError("child-default removal changed unrelated config; config preserved")
        return (None if owned["created"] and not text else text.encode("utf-8")), None
    missing = [key for key in SUBAGENT_DEFAULTS if key not in values]
    record = {"fields": missing, "block": "", "header": "", "prefix": "", "created": raw is None}
    if not missing:
        return raw, record
    if DEFAULTS_MARKER in text:
        raise ValueError("unowned child-default marker; config preserved")
    newline = "\r\n" if "\r\n" in text else "\n"
    block = DEFAULTS_MARKER + newline + "".join(
        f'{key} = "{defaults[key]}"{newline}' for key in missing)
    block += "# end codex-efficiency-router: child defaults" + newline
    record["block"] = block
    match = re.search(r"(?m)^[ \t]*\[agents\][ \t]*(?:#[^\r\n]*)?\r?$", text)
    if match:
        offset = match.end()
        if text[offset:offset + 1] == "\n":
            offset += 1
        else:
            block = newline + block
            record["block"] = block
        text = text[:offset] + block + text[offset:]
    elif "agents" in parsed:
        raise ValueError("child defaults require a plain [agents] table; config preserved")
    else:
        record["prefix"] = newline if text and not text.endswith("\n") else ""
        record["header"] = "[agents]" + newline
        text += record["prefix"] + record["header"] + block
    result = text.encode("utf-8")
    if any(tomllib.loads(text)["agents"].get(k) != v for k, v in defaults.items()):
        raise ValueError("child-default insertion failed validation")
    return result, record


def installed_defaults(skill: Path, agents: Path, *, allow_legacy=False, remove=False) -> dict | None:
    raw = read_bytes(skill / MANIFEST)
    record = json.loads(raw).get("subagent_defaults") if raw is not None else None
    if record is not None:
        subagent_defaults(read_bytes(target(CONFIG_KEY, skill, agents)), record,
                          migrate=allow_legacy, remove=remove)
    return record


def digest(data: bytes | None) -> str | None:
    return None if data is None else hashlib.sha256(data).hexdigest()


def reject_links(path: Path) -> None:
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError(f"symlink is not supported for managed paths: {item}")
        if item.exists():
            flags = getattr(item.lstat(), "st_file_attributes", 0)
            if flags & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise ValueError(f"reparse point/junction is not supported: {item}")


def target(key: str, skill: Path, agents: Path) -> Path:
    p = PurePosixPath(key)
    if (p.is_absolute() or len(p.parts) < 2 or str(p) != key
            or any(v in ("", ".", "..") for v in p.parts) or "\\" in key or ":" in key):
        raise ValueError(f"unsafe managed path: {key!r}")
    if key == CONFIG_KEY:
        out = agents.parent / "config.toml"
    elif p.parts[0] == "agents" and len(p.parts) == 2 and p.name in MANAGED_AGENT_FILES:
        out = agents / p.name
    elif p.parts[0] == "skill":
        out = skill.joinpath(*p.parts[1:])
    else:
        raise ValueError(f"unowned target: {key}")
    reject_links(out)
    if out.exists() and not out.is_file():
        raise ValueError(f"expected regular file: {out}")
    return out


def read_bytes(path: Path) -> bytes | None:
    reject_links(path)
    return path.read_bytes() if path.exists() else None


def load_manifest(skill: Path, agents: Path) -> dict[str, str]:
    raw = read_bytes(skill / MANIFEST)
    if raw is None:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("owner") != PROJECT or data.get("schema") != 1 or not isinstance(data.get("files"), dict):
        raise ValueError("invalid ownership manifest")
    from_manifest(data)  # Validate persisted mode before any lifecycle operation.
    for key, value in data["files"].items():
        target(key, skill, agents)
        if key in (f"skill/{MANIFEST}", CONFIG_KEY) or not isinstance(value, str) or len(value) != 64:
            raise ValueError("invalid manifest entry")
        int(value, 16)
    if 'skill/SKILL.md' not in data['files']:
        raise ValueError('incomplete ownership manifest: skill/SKILL.md')
    return data["files"]


def installed_profile(skill: Path, agents: Path) -> Profile:
    load_manifest(skill, agents)
    raw = read_bytes(skill / MANIFEST)
    return from_manifest(json.loads(raw)) if raw is not None else Profile()


def required_ownership(profile: Profile) -> set[str]:
    required = {'skill/' + name for name in ('SKILL.md', 'agents/openai.yaml', 'cer.ps1',
                'scripts/readonly_reader.py', 'references/dispatch.md', 'references/effort.md',
                'references/quality.md', 'references/routing.md')}
    required.update('agents/' + name for name in
                    (MANAGED_AGENT_FILES if profile.mode == 'auto' else AGENT_FILES))
    return required


def source_files(root: Path) -> dict[str, bytes]:
    from doctor import validate_tree
    src = root / "skills" / PROJECT
    errors = validate_tree(src / "SKILL.md", root / "agents")
    if errors:
        raise ValueError("source validation failed: " + "; ".join(errors))
    files = {}
    for p in sorted(src.rglob("*")):
        reject_links(p)
        if p.is_file():
            if p.name == MANIFEST or "__pycache__" in p.parts:
                raise ValueError(f"unexpected source payload: {p}")
            files["skill/" + p.relative_to(src).as_posix()] = p.read_bytes()
    for name in AGENT_FILES:
        p = root / "agents" / name
        reject_links(p)
        files["agents/" + name] = p.read_bytes()
    for key, p in (("skill/scripts/readonly_reader.py", root / "hooks" / "readonly_reader.py"),
                   ("skill/cer.ps1", root / "cer.ps1")):
        reject_links(p)
        if key in files:
            raise ValueError(f"duplicate source payload: {key}")
        files[key] = p.read_bytes()
    return files


def legacy_files(skill: Path, agents: Path) -> dict[str, str]:
    if not (skill / "SKILL.md").is_file():
        raise ValueError("--adopt-v01 requires the known v0.1.0 Skill")
    owned = {}
    for key, expected in LEGACY.items():
        raw = read_bytes(target(key, skill, agents))
        if raw is None:
            continue
        normalized = raw.replace(b"\r\n", b"\n")
        git_blob = hashlib.sha1(f"blob {len(normalized)}\0".encode() + normalized).hexdigest()
        if git_blob != expected:
            raise ValueError(f"unknown or locally edited legacy file; preserve and review: {key}")
        owned[key] = digest(raw)
    return owned


def replace(path: Path, data: bytes | None) -> None:
    reject_links(path)
    if data is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".cer-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


@contextmanager
def lock(backup_root: Path):
    reject_links(backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)
    path = backup_root / ".lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(f"another operation or stale lock exists: {path}") from exc
    os.close(fd)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def apply(changes: dict[str, bytes | None], skill: Path, agents: Path, backup_root: Path,
          dry_run: bool) -> Path | None:
    before = {k: read_bytes(target(k, skill, agents)) for k in changes}
    changes = {k: v for k, v in changes.items() if v != before[k]}
    if not changes:
        print("no changes")
        return None
    for key, value in changes.items():
        print(f"{'[dry-run] ' if dry_run else ''}{'remove' if value is None else 'write'}: {target(key, skill, agents)}")
    if dry_run:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid4().hex[:8]
    backup = backup_root / stamp
    backup.mkdir(mode=0o700)
    records = {}
    for key, value in changes.items():
        records[key] = {"before": digest(before[key]), "after": digest(value)}
        if before[key] is not None:
            saved = backup / "files" / key
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(before[key])
    journal = {"owner": PROJECT, "schema": 1, "skill": str(skill), "agents": str(agents), "files": records}
    (backup / "backup.json").write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")
    written = []
    try:
        for key, value in changes.items():
            path = target(key, skill, agents)
            if read_bytes(path) != before[key]:
                raise ValueError(f"file changed during operation: {path}")
            replace(path, value)
            written.append(key)
    except BaseException:
        for key in reversed(written):
            path = target(key, skill, agents)
            try:
                if read_bytes(path) == changes[key]:
                    replace(path, before[key])
                else:
                    print(f"rollback preserved concurrent change: {path}")
            except (OSError, ValueError) as rollback_error:
                print(f"rollback requires manual recovery: {path}: {rollback_error}")
        print(f"write failed; restored unchanged owned writes; inspect backup: {backup}")
        raise
    print(f"backup: {backup}")
    return backup


def install(root: Path, scope: str, project_root: Path | None, dry_run: bool = False,
            force: bool = False, adopt_v01: bool = False, *,
            mode: str | None = None, allow_low: bool | None = None,
            set_subagent_defaults: bool = False) -> int:
    skill, agents, backup_root = resolve_targets(scope, project_root)
    canonical = source_files(root)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()

    def operation():
        manifest_exists = (skill / MANIFEST).exists()
        owned = load_manifest(skill, agents)
        previous = installed_profile(skill, agents) if manifest_exists else None
        profile = select_profile(previous, mode, allow_low)
        if previous is not None and previous.legacy and mode is None:
            print(f"migration: legacy {previous.mode} -> auto; existing managed bytes will be backed up")
        payload = render_payload(canonical, profile)
        print(f"profile: {profile.mode}; automatic low: {profile.allow_low}; no live capability probe")
        if adopt_v01 and not manifest_exists:
            owned = legacy_files(skill, agents)
        for key in set(owned) | set(payload):
            path = target(key, skill, agents)
            raw = read_bytes(path)
            if raw is not None and key not in owned:
                raise ValueError(f"refusing to overwrite unowned file: {path}; use --adopt-v01 only for a known legacy install")
            if key in owned and digest(raw) != owned[key] and not force:
                raise ValueError(f"managed file was changed or removed: {path}; review before --force")
        changes = {key: None for key in owned if key not in payload}
        changes.update(payload)
        defaults = installed_defaults(skill, agents, allow_legacy=True)
        if set_subagent_defaults or defaults is not None:
            config, defaults = subagent_defaults(read_bytes(target(CONFIG_KEY, skill, agents)), defaults, migrate=True)
            changes[CONFIG_KEY] = config
        from release_identity import source_identity, sha, canonical as canonical_json
        identity = source_identity(root)
        policy_parts = {key[len("skill/"):]: digest(value) for key, value in payload.items()
                        if key == "skill/SKILL.md" or key.startswith("skill/references/")}
        manifest = {"schema": 1, "owner": PROJECT, "version": version,
                    "base_commit": identity["base_commit"],
                    "policy_sha256": sha(canonical_json(policy_parts)),
                    "mode": profile.mode, "allow_low": profile.allow_low, "profile_schema": 2,
                    "files": {key: digest(value) for key, value in sorted(payload.items())}}
        if defaults is not None:
            manifest["subagent_defaults"] = defaults
        changes[f"skill/{MANIFEST}"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        apply(changes, skill, agents, backup_root, dry_run)
    if dry_run:
        operation()
    else:
        with lock(backup_root):
            operation()
    print("installation preview complete" if dry_run else f"installed; invoke ${PROJECT}; reload Codex if needed")
    return 0


def uninstall(scope: str, project_root: Path | None, dry_run: bool = False, force: bool = False) -> int:
    skill, agents, backup_root = resolve_targets(scope, project_root)

    def operation():
        if not (skill / MANIFEST).exists():
            if (skill / "SKILL.md").exists():
                raise ValueError("no ownership manifest; migrate the known v0.1.0 install with --adopt-v01 first")
            print("no managed installation found; nothing removed")
            return
        owned = load_manifest(skill, agents)
        for key in required_ownership(installed_profile(skill, agents)) - owned.keys():
            if target(key, skill, agents).exists():
                raise ValueError(f'incomplete ownership manifest; unowned standard path preserved: {key}')
        for key, expected in owned.items():
            raw = read_bytes(target(key, skill, agents))
            if raw is not None and digest(raw) != expected and not force:
                raise ValueError(f"locally edited file preserved: {key}; review before --force")
        changes = {key: None for key in owned}
        defaults = installed_defaults(skill, agents, allow_legacy=True, remove=True)
        if defaults is not None:
            changes[CONFIG_KEY], _ = subagent_defaults(
                read_bytes(target(CONFIG_KEY, skill, agents)), defaults, remove=True, migrate=True)
        changes[f"skill/{MANIFEST}"] = None
        apply(changes, skill, agents, backup_root, dry_run)
        if not dry_run and skill.exists():
            # Never recursively delete: untracked user files survive uninstall.
            parents = set()
            for key in owned:
                if key.startswith("skill/"):
                    path = target(key, skill, agents).parent
                    while path != skill:
                        parents.add(path)
                        path = path.parent
            for path in sorted(parents, key=lambda p: len(p.parts), reverse=True):
                try:
                    path.rmdir()
                except OSError:
                    pass
            try:
                skill.rmdir()
            except OSError:
                pass
    if dry_run:
        operation()
    else:
        with lock(backup_root):
            operation()
    return 0


def restore(backup: Path, scope: str, project_root: Path | None, dry_run: bool = False,
            force: bool = False) -> int:
    skill, agents, backup_root = resolve_targets(scope, project_root)
    reject_links(backup)
    reject_links(backup / "backup.json")
    journal = json.loads((backup / "backup.json").read_text(encoding="utf-8"))
    if (not isinstance(journal, dict) or journal.get("owner") != PROJECT or journal.get("schema") != 1
            or journal.get("skill") != str(skill) or journal.get("agents") != str(agents)
            or not isinstance(journal.get("files"), dict)):
        raise ValueError("backup belongs to different package, scope, or target paths")

    def operation():
        changes = {}
        for key, record in journal["files"].items():
            if not isinstance(record, dict) or set(record) != {"before", "after"}:
                raise ValueError("invalid backup record")
            for value in record.values():
                if value is not None and (not isinstance(value, str) or len(value) != 64):
                    raise ValueError("invalid backup checksum")
                if value is not None:
                    int(value, 16)
            current = read_bytes(target(key, skill, agents))
            if (key == CONFIG_KEY or not force) and digest(current) not in (record["after"], record["before"]):
                raise ValueError(f"newer local change preserved: {key}")
            data = None
            if record["before"] is not None:
                saved = backup / "files" / key
                reject_links(saved)
                data = saved.read_bytes()
                if digest(data) != record["before"]:
                    raise ValueError(f"corrupt backup file: {key}")
            changes[key] = data
        apply(changes, skill, agents, backup_root, dry_run)
    if dry_run:
        operation()
    else:
        with lock(backup_root):
            operation()
    return 0
