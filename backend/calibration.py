"""Out-of-sample probability calibration using a user-supplied historical CSV.

Required columns:
market_category,sub_market,time_window,model_version,predicted_probability,outcome,predicted_at,kickoff_at,settled_at

Each row must be a genuinely out-of-sample forecast recorded before the event
settled. The module refuses small samples and returns no calibrated estimate.
"""
from __future__ import annotations

import csv
import math
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path


MIN_TOTAL_SAMPLES = int(os.getenv("T24_CALIBRATION_MIN_TOTAL", "200"))
MIN_BIN_SAMPLES = int(os.getenv("T24_CALIBRATION_MIN_BIN", "30"))
BIN_WIDTH = 0.05


def _parse_time(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=4)
def _load_rows(path: str, mtime: float) -> tuple[dict, ...]:
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"market_category", "sub_market", "time_window", "model_version", "predicted_probability", "outcome", "predicted_at", "kickoff_at", "settled_at"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"Calibration CSV must contain columns: {', '.join(sorted(required))}")
        for row in reader:
            predicted_at = _parse_time(row.get("predicted_at", ""))
            kickoff_at = _parse_time(row.get("kickoff_at", ""))
            settled = _parse_time(row.get("settled_at", ""))
            if (
                predicted_at is None or kickoff_at is None or settled is None
                or predicted_at >= kickoff_at or kickoff_at >= settled
                or settled > datetime.now(timezone.utc)
            ):
                continue
            try:
                p = float(row["predicted_probability"])
                y = int(row["outcome"])
            except (TypeError, ValueError):
                continue
            if not 0 < p < 1 or y not in (0, 1):
                continue
            rows.append({
                "market_category": row["market_category"].strip().lower(),
                "sub_market": row["sub_market"].strip().lower(),
                "time_window": row["time_window"].strip(),
                "model_version": row["model_version"].strip(),
                "p": p,
                "y": y,
            })
    return tuple(rows)


def _wilson_lower(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    rate = successes / total
    denom = 1 + z * z / total
    centre = rate + z * z / (2 * total)
    margin = z * math.sqrt((rate * (1 - rate) + z * z / (4 * total)) / total)
    return max(0.0, (centre - margin) / denom)


def calibrate_probability(
    market_category: str,
    sub_market: str,
    time_window: str,
    predicted_probability: float,
    model_version: str = "tactica24-poisson-v2",
) -> tuple[float | None, int]:
    path = os.getenv("T24_CALIBRATION_FILE", "data/historical_outcomes.csv")
    file_path = Path(path)
    if not file_path.exists():
        return None, 0
    rows = _load_rows(str(file_path.resolve()), file_path.stat().st_mtime)
    matched = [
        row for row in rows
        if row["market_category"] == market_category.lower()
        and row["sub_market"] == sub_market.lower()
        and row["time_window"] == time_window
        and row["model_version"] == model_version
    ]
    if len(matched) < MIN_TOTAL_SAMPLES:
        return None, len(matched)
    low = max(0.0, math.floor(predicted_probability / BIN_WIDTH) * BIN_WIDTH)
    high = min(1.0, low + BIN_WIDTH)
    in_bin = [r for r in matched if low <= r["p"] < high or (high == 1.0 and r["p"] == 1.0)]
    if len(in_bin) < MIN_BIN_SAMPLES:
        return None, len(in_bin)
    wins = sum(r["y"] for r in in_bin)
    # Use the lower 95% Wilson confidence bound rather than the raw hit rate.
    # This is intentionally conservative and is not a guarantee of future wins.
    return round(_wilson_lower(wins, len(in_bin)), 4), len(in_bin)


def calibration_dataset_status() -> dict:
    path = Path(os.getenv("T24_CALIBRATION_FILE", "data/historical_outcomes.csv"))
    if not path.exists():
        return {"ready": False, "rows": 0, "profiles": 0}
    try:
        rows = _load_rows(str(path.resolve()), path.stat().st_mtime)
    except (OSError, ValueError):
        return {"ready": False, "rows": 0, "profiles": 0}
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        key = (row["market_category"], row["sub_market"], row["time_window"], row["model_version"])
        groups.setdefault(key, []).append(row)
    profiles = 0
    for values in groups.values():
        if len(values) < MIN_TOTAL_SAMPLES:
            continue
        bins: dict[int, int] = {}
        for row in values:
            bucket = min(19, int(row["p"] / BIN_WIDTH))
            bins[bucket] = bins.get(bucket, 0) + 1
        if any(count >= MIN_BIN_SAMPLES for count in bins.values()):
            profiles += 1
    return {"ready": profiles > 0, "rows": len(rows), "profiles": profiles}
