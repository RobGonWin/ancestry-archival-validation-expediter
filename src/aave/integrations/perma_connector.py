"""Perma.cc integration skeleton with disabled-by-default dry runs."""

from __future__ import annotations

import os
from pathlib import Path

from aave.integrations.common import IntegrationDryRunResult, build_disabled_payload, write_json

CONNECTOR_NAME = "perma"


def build_perma_dry_run(
    output_directory: Path,
    enabled: bool = False,
) -> IntegrationDryRunResult:
    """Write a disabled-by-default Perma dry-run payload."""
    output_path = output_directory / "perma_dry_run.json"
    if not enabled:
        payload = build_disabled_payload(
            CONNECTOR_NAME,
            "Perma.cc integration is disabled by default; no API call was made.",
        )
    else:
        payload = {
            "connector": CONNECTOR_NAME,
            "enabled": True,
            "dry_run": True,
            "api_key_env_var": "AAVE_PERMA_API_KEY",
            "api_key_present": bool(os.getenv("AAVE_PERMA_API_KEY")),
            "payloads": [],
            "notes": [
                "Dry-run only. No Perma.cc link was created.",
                "Future implementations must require explicit enablement.",
            ],
        }

    write_json(payload, output_path)
    return IntegrationDryRunResult(
        connector=CONNECTOR_NAME,
        enabled=enabled,
        dry_run=True,
        payload_count=len(payload["payloads"]),
        output_path=output_path,
    )
