from __future__ import annotations

import statistics
from typing import Iterable

from phase2c.analysis_plan import FROZEN_METRICS, FROZEN_THRESHOLDS


def summarize(values: Iterable[float]) -> dict[str, float | int | None]:
    items = [float(value) for value in values]
    if not items:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {
        "count": len(items),
        "min": min(items),
        "mean": statistics.fmean(items),
        "max": max(items),
    }


def analysis_contract() -> dict[str, object]:
    return {
        "metrics": list(FROZEN_METRICS),
        "thresholds": dict(FROZEN_THRESHOLDS),
    }
