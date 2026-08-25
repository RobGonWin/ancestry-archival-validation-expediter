"""Shared helpers for optional integration dry runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class IntegrationDryRunResult:
    """Summary of a disabled-by-default integration dry run."""

    connector: str
    enabled: bool
    dry_run: bool
    payload_count: int
    output_path: Path


def load_json_list(path: Path) -> list[dict[str, Any]]:
    """Load a JSON list of dictionaries."""
    raw_data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    rows = [row for row in raw_data if isinstance(row, dict)]
    return rows


def write_json(data: object, output_path: Path) -> None:
    """Write stable formatted JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(data, output_file, indent=2)
        output_file.write("\n")


def build_disabled_payload(connector: str, reason: str) -> dict[str, Any]:
    """Build a payload showing that a connector stayed disabled."""
    return {
        "connector": connector,
        "enabled": False,
        "dry_run": True,
        "payloads": [],
        "notes": [reason],
    }
