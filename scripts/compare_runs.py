#!/usr/bin/env python3
"""Compare normalized paired runs, without any model/API calls or automatic tuning.

Input is a JSON array. Each row describes one whole task, not one tool/child turn.
See docs/BENCHMARKING.md. Missing measurements are unknown, never zero.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

METRICS = ("total_tokens", "expensive_model_tokens", "elapsed_seconds")


def compare(rows: list[dict]) -> dict:
    if not isinstance(rows, list) or not rows:
        raise ValueError("expected a nonempty array of paired run records")
    pairs = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each record must be an object")
        for key in ("task_id", "trial_id", "environment_id", "acceptance_id"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"{key} must be a nonempty string")
        variant = row.get("variant")
        if variant not in ("baseline", "router"):
            raise ValueError("variant must be baseline or router")
        if row.get("outcome") not in ("pass", "fail", "unknown"):
            raise ValueError("outcome must be pass, fail, or unknown")
        for metric in METRICS:
            value = row.get(metric)
            if value is None:
                continue
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{metric} must be a finite nonnegative number or null")
            if metric.endswith("tokens") and type(value) is not int:
                raise ValueError(f"{metric} must be an integer or null")
        total, expensive = row.get("total_tokens"), row.get("expensive_model_tokens")
        if total is not None and expensive is not None and expensive > total:
            raise ValueError("expensive-model tokens cannot exceed total tokens")
        key = (row["task_id"], row["trial_id"])
        pair = pairs.setdefault(key, {})
        if variant in pair:
            raise ValueError(f"duplicate run: {key}/{variant}")
        pair[variant] = row
    regressions, unknowns = [], []
    for key, pair in pairs.items():
        if set(pair) != {"baseline", "router"}:
            raise ValueError(f"unpaired task/trial: {key}")
        a, b = pair["baseline"], pair["router"]
        if any(a[k] != b[k] for k in ("environment_id", "acceptance_id")):
            raise ValueError(f"comparison conditions differ: {key}")
        if a["outcome"] == "unknown" or b["outcome"] == "unknown":
            unknowns.append(list(key))
        if a["outcome"] == "pass" and b["outcome"] == "fail":
            regressions.append(list(key))
    measurements = {}
    for metric in METRICS:
        complete = all(p[v].get(metric) is not None for p in pairs.values() for v in ("baseline", "router"))
        if not complete:
            measurements[metric] = {"status": "unknown"}
            continue
        base = sum(p["baseline"][metric] for p in pairs.values())
        routed = sum(p["router"][metric] for p in pairs.values())
        measurements[metric] = {"status": "measured", "baseline": base, "router": routed,
                                "reduction_fraction": None if base == 0 else 1 - routed / base}
    return {"paired_trials": len(pairs), "regressions": regressions, "unknown_outcomes": unknowns,
            "baseline_passes": sum(p["baseline"]["outcome"] == "pass" for p in pairs.values()),
            "router_passes": sum(p["router"]["outcome"] == "pass" for p in pairs.values()),
            "router_acceptance": "pass" if all(p["router"]["outcome"] == "pass" for p in pairs.values()) else "incomplete",
            "efficiency_claim_eligible": all(p[v]["outcome"] == "pass" for p in pairs.values() for v in ("baseline", "router")) and all(m["status"] == "measured" for m in measurements.values()),
            "quality_status": "regression" if regressions else "unknown" if unknowns else "no_observed_regression",
            "measurements": measurements,
            "limitation": "Descriptive paired sample only; not proof of non-inferiority or future quality."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    args = parser.parse_args()
    try:
        result = compare(json.loads(args.runs.read_text(encoding="utf-8")))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result["quality_status"] == "no_observed_regression" and result["router_acceptance"] == "pass" else 1
    except (OSError, ValueError, TypeError) as exc:
        print(f"invalid comparison: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
