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
CORE_KEY = f"skill/SKILL.md"
MARKER = re.compile(r"^Installation: (auto|fixed|adaptive); automatic low: (disabled|enabled)\.$", re.M)


@dataclass(frozen=True)
class Profile:
    mode: Mode = "fixed"
    allow_low: bool = False
    # Old manifests cannot distinguish an intentional override from the old default.
    # Read/restore them literally; an ordinary update visibly migrates them to auto.
    legacy: bool = field(default=False, compare=False)

    def __post_init__(self) -> None:
        if self.mode not in MODES or type(self.allow_low) is not bool or type(self.legacy) is not bool:
            raise ValueError("invalid installation profile")
        if self.mode == "fixed" and self.allow_low:
            raise ValueError("automatic low requires auto or adaptive policy")

    @property
    def marker(self) -> str:
        return f"Installation: {self.mode}; automatic low: {'enabled' if self.allow_low else 'disabled'}."


def from_manifest(data: dict) -> Profile:
    """Legacy manifests describe fixed installs; never infer adaptive from absence."""
    if not isinstance(data, dict):
        raise ValueError("manifest must be an object")
    if "profile_schema" in data and (type(data["profile_schema"]) is not int or data["profile_schema"] != 2):
        raise ValueError("unknown profile schema")
    if "mode" not in data and "allow_low" not in data:
        if "profile_schema" in data:
            raise ValueError("profile schema requires mode and allow_low")
        return Profile(legacy=True)
    if "mode" not in data or "allow_low" not in data:
        raise ValueError("manifest profile is incomplete")
    return Profile(data["mode"], data["allow_low"], legacy="profile_schema" not in data)


def select_profile(previous: Profile | None, mode: Mode | None = None,
                   allow_low: bool | None = None) -> Profile:
    if previous is not None and not isinstance(previous, Profile):
        raise ValueError("previous profile must be Profile or None")
    chosen = ("auto" if previous is None or previous.legacy else previous.mode) if mode is None else mode
    # A deliberate switch to fixed disables low, but explicit invalid requests fail.
    low = (bool(previous and previous.allow_low) if chosen != "fixed" else False) if allow_low is None else allow_low
    return Profile(chosen, low)


def render_payload(payload: dict[str, bytes], profile: Profile) -> dict[str, bytes]:
    """Generate native bindings, preserving permissions and instruction content.

    Auto installs four pinned compatibility roles plus four unpinned aliases.
    Only ONE binding is chosen per child; files are not running agents. This avoids
    rewriting configurations, inheriting unknown effort, or asking users to switch.
    Legacy overrides still install only the original four roles.
    """
    output = dict(payload)
    text = output[CORE_KEY].decode("utf-8")
    if MARKER.findall(text) != [("fixed", "disabled")]:
        raise ValueError("source must contain exactly one canonical fixed installation marker")
    output[CORE_KEY] = MARKER.sub(profile.marker, text).encode("utf-8")
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
