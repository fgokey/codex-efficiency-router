"""Pure auto/fixed/adaptive payload generation; no host probes or filesystem writes."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
import tomllib
from typing import Literal

from package import AUTO_DESCRIPTION_PREFIX, EXPECTED, AUTO_EXPECTED, PROJECT

Mode = Literal["auto", "fixed", "adaptive"]
MODES = ("auto", "fixed", "adaptive")
HOST_MODES = ("full", "compat")
CORE_KEY = f"skill/SKILL.md"
MARKER = re.compile(r"^Installation: (auto|fixed|adaptive); automatic low: (disabled|enabled)\.$", re.M)


@dataclass(frozen=True)
class Profile:
    mode: Mode = "fixed"
    allow_low: bool = False
    # Old manifests cannot distinguish an intentional override from the old default.
    # Read/restore them literally; an ordinary update visibly migrates them to auto.
    legacy: bool = field(default=False, compare=False)
    host_mode: Literal["full", "compat"] = "full"

    def __post_init__(self) -> None:
        if self.mode not in MODES or type(self.allow_low) is not bool or type(self.legacy) is not bool:
            raise ValueError("invalid installation profile")
        if self.host_mode not in HOST_MODES or (self.host_mode == "compat" and self.allow_low):
            raise ValueError("invalid host mode or automatic low in compat")
        if self.mode == "fixed" and self.allow_low:
            raise ValueError("automatic low requires auto or adaptive policy")

    @property
    def marker(self) -> str:
        return f"Installation: {self.mode}; automatic low: {'enabled' if self.allow_low else 'disabled'}."


def from_manifest(data: dict) -> Profile:
    """Legacy manifests describe fixed installs; never infer adaptive from absence."""
    if not isinstance(data, dict):
        raise ValueError("manifest must be an object")
    if "profile_schema" in data and (type(data["profile_schema"]) is not int or data["profile_schema"] not in (2, 3)):
        raise ValueError("unknown profile schema")
    host_mode = data.get("host_mode", "full")
    if (data.get("profile_schema") == 3 and "host_mode" not in data
            or host_mode != "full" and data.get("profile_schema") != 3
            or host_mode == "compat" and "subagent_defaults" in data):
        raise ValueError("invalid host mode manifest")
    if "mode" not in data and "allow_low" not in data:
        if "profile_schema" in data:
            raise ValueError("profile schema requires mode and allow_low")
        return Profile(legacy=True)
    if "mode" not in data or "allow_low" not in data:
        raise ValueError("manifest profile is incomplete")
    return Profile(data["mode"], data["allow_low"], legacy="profile_schema" not in data,
                   host_mode=host_mode)


def select_profile(previous: Profile | None, mode: Mode | None = None,
                   allow_low: bool | None = None, host_mode: str | None = None) -> Profile:
    if previous is not None and not isinstance(previous, Profile):
        raise ValueError("previous profile must be Profile or None")
    chosen = ("auto" if previous is None or previous.legacy else previous.mode) if mode is None else mode
    # A deliberate switch to fixed disables low, but explicit invalid requests fail.
    low = (bool(previous and previous.allow_low) if chosen != "fixed" else False) if allow_low is None else allow_low
    host = host_mode if host_mode is not None else previous.host_mode if previous else "full"
    return Profile(chosen, low, host_mode=host)


def render_payload(payload: dict[str, bytes], profile: Profile) -> dict[str, bytes]:
    """Generate native bindings, preserving permissions and instruction content.

    Auto installs five pinned compatibility roles plus five unpinned aliases.
    Only ONE binding is chosen per child; files are not running agents. This avoids
    rewriting configurations, inheriting unknown effort, or asking users to switch.
    Fixed/adaptive overrides install only the five source roles.
    """
    output = dict(payload)
    text = output[CORE_KEY].decode("utf-8")
    if MARKER.findall(text) != [("fixed", "disabled")]:
        raise ValueError("source must contain exactly one canonical fixed installation marker")
    output[CORE_KEY] = MARKER.sub(profile.marker, text).encode("utf-8")
    if profile.host_mode == "compat":
        prefix = output[CORE_KEY].decode("utf-8").split(profile.marker, 1)[0] + profile.marker + '\n\n'
        output = {k: v for k, v in output.items() if k in {
            CORE_KEY, 'skill/agents/openai.yaml', 'skill/scripts/readonly_reader.py'}}
        output[CORE_KEY] = (prefix + """Host mode: compat.

At task start, check available host tools, existing permissions, read-only roles and Hook prohibitions. Report missing model/binding metadata as UNKNOWN; it does not block the current executor's already authorized work. Never authenticate configuration, directories, caller claims or old receipts as current identity.
Explicit compatibility provides planning, context reduction and review. The current executor works only within existing host/user authority. No forced model delegation or model-based write restriction. No parent model change; no new write authority. Actual sandbox/read-only/Hook restrictions prevail; deployment/publication needs separate authority.
Reuse loaded unchanged rules; fully read necessary new/changed rules. Prefer available bounded helpers; Python/Reader/completion_check are optional. If absent, use native bounded reads and appropriate validation within existing authority. Batch fitting independent reads; preserve every cursor/status/error. No full-file slicing/merging pages/files. Capture/select/count before output; JSON+CRLF+framing<=4KiB; retain successful results and retry failed/pending only. Unknown framing is an evidence gap.

## Completion

Requirements win. Before writes check scope, platforms/macros, consumers and validation. Use a faithful failure signal, meaningful negative cases and applicable repository checks; never weaken assertions. Review/integrate available work before waiting. Preserve attempts and disclose unrun checks, uncertainty and remaining work. Before final compare evidence with the actual user objective; a child ending does not complete the parent goal. Never claim model identity, Guard enforcement or Token savings without current proof.

## Routing

Do not activate full routing/admission references or create children to obtain missing identity.

## Delegate

Compatibility cannot release a prohibited executor. Stop affected work when actual host/user authority is insufficient; lack of model metadata alone is not a prohibition.

## Handoff

## Recovery

## Context and reporting

Report loaded CER version, explicit compat selection, host permissions and Guard evidence; gaps UNKNOWN.
""").encode("utf-8")
        return output
    for filename, (_, _, effort) in EXPECTED.items():
        key = "agents/" + filename
        source = output[key].decode("utf-8")
        config = tomllib.loads(source)
        if config.get("model_reasoning_effort") != effort:
            raise ValueError(f"source role is not canonical: {filename}")
        if profile.mode in ("auto", "adaptive"):
            # Match only the exact shipped top-level setting, never instruction text.
            line = f'model_reasoning_effort = "{effort}"\n'
            if source.count(line) != 1:
                raise ValueError(f"ambiguous effort declaration: {filename}")
            source = source.replace(line, "", 1)
            rendered = tomllib.loads(source)
            expected = {k: v for k, v in config.items() if k != "model_reasoning_effort"}
            if rendered != expected:
                raise ValueError(f"render changed fields other than effort: {filename}")
            if profile.mode == "auto":
                alias_file = "cer-auto-" + filename
                alias_name = AUTO_EXPECTED[alias_file][0]
                line = f'name = "{config["name"]}"\n'
                if source.count(line) != 1:
                    raise ValueError(f"ambiguous role name: {filename}")
                source = source.replace(line, f'name = "{alias_name}"\n', 1)
                expected["name"] = alias_name
                line = "description = " + json.dumps(config["description"]) + "\n"
                if source.count(line) != 1:
                    raise ValueError(f"ambiguous role description: {filename}")
                description = AUTO_DESCRIPTION_PREFIX + config["description"]
                source = source.replace(line, "description = " + json.dumps(description) + "\n", 1)
                expected["description"] = description
                if tomllib.loads(source) != expected:
                    raise ValueError(f"alias changed protected settings: {filename}")
                key = "agents/" + alias_file
            output[key] = source.encode("utf-8")
    return output
