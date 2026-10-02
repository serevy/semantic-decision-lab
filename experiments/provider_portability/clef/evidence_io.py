from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping


def _serialized(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=str,
    ) + "\n"


def reserve_evidence(path: Path, payload: Mapping[str, Any]) -> None:
    """Create the first-run evidence file exclusively.

    The exclusive create is both an overwrite guard and a concurrency guard:
    a second run targeting the same evidence path fails before external work.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(_serialized(payload))


def update_evidence(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically update evidence while preserving the last complete JSON."""

    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(_serialized(payload), encoding="utf-8")
    os.replace(temp, path)
