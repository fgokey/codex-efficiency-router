"""Pure fixed/adaptive payload generation; no host probes or filesystem writes."""
from __future__ import annotations

from dataclasses import dataclass
import re
import tomllib
from typing import Literal

from package import EXPECTED, PROJECT

Mode = Literal["fixed", "adaptive"]
MODES = ("fixed", "adaptive")
CORE_KEY = f"skill/SKILL.md"
MARKER = re.compile(r"^Installation: (fixed|adaptive); automatic low: (disabled|enabled)\.$", re.M)


@dataclass(frozen=True)
class Profile:
    mode: Mode = "fixed"
    allow_low: bool = False

    def __post_init__(self) -> None:
        if self.mode not in MODES or type(self.allow_low) is not bool:
            raise ValueError("invalid installation profile")
        if self.mode == "fixed" and self.allow_low:
            raise ValueError("automatic low requires --mode adaptive")

    @property
    def marker(self) -> str:
        return f"Installation: {self.mode}; automatic low: {'enabled' if self.allow_low else 'disabled'}."


def from_manifest(data: dict) -> Profile:
    """Legacy manifests describe fixed installs; never infer adaptive from absence."""
    if not isinstance(data, dict):
        raise ValueError("manifest must be an object")
    if "mode" not in data and "allow_low" not in data:
        return Profile()
    if "mode" not in data or "allow_low" not in data:
        raise ValueError("manifest profile is incomplete")
    return Profile(data["mode"], data["allow_low"])


def select_profile(previous: Profile, mode: Mode | None = None,
                   allow_low: bool | None = None) -> Profile:
    chosen = previous.mode if mode is None else mode
    # A deliberate switch to fixed disables low, but explicit invalid requests fail.
    low = (previous.allow_low if chosen == "adaptive" else False) if allow_low is None else allow_low
    return Profile(chosen, low)


def render_payload(payload: dict[str, bytes], profile: Profile) -> dict[str, bytes]:
    """Render one canonical FIXED source into exactly four installed role files."""
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
        if profile.mode == "adaptive":
            # Match only the exact shipped top-level setting, never instruction text.
            line = f'model_reasoning_effort = "{effort}"\n'
            if source.count(line) != 1:
                raise ValueError(f"ambiguous effort declaration: {filename}")
            source = source.replace(line, "", 1)
            rendered = tomllib.loads(source)
            expected = {k: v for k, v in config.items() if k != "model_reasoning_effort"}
            if rendered != expected:
                raise ValueError(f"render changed fields other than effort: {filename}")
            output[key] = source.encode("utf-8")
    return output
