"""Parse a supplied Codex model/list export; never discover accounts or call APIs."""
from __future__ import annotations


def parse_catalog(data: object) -> dict[str, frozenset[str]]:
    if not isinstance(data, dict):
        raise ValueError("expected a model/list JSON object")
    payload = data.get("result", data)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("expected a model/list data array")
    if "nextCursor" not in payload or payload["nextCursor"] is not None:
        raise ValueError("catalog is incomplete: export every page with nextCursor=null")
    found = {}
    for entry in payload["data"]:
        if not isinstance(entry, dict):
            raise ValueError("invalid catalog entry")
        model, efforts = entry.get("model"), entry.get("supportedReasoningEfforts")
        if not isinstance(model, str) or not model.strip() or not isinstance(efforts, list):
            raise ValueError("invalid model or supportedReasoningEfforts")
        if model in found:
            raise ValueError(f"ambiguous duplicate catalog model: {model}")
        values = []
        for effort in efforts:
            value = effort.get("reasoningEffort") if isinstance(effort, dict) else None
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"invalid effort for {model}")
            values.append(value)
        found[model] = frozenset(values)
    return found
