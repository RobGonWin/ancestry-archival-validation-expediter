"""ArchiveBox integration skeleton.

This module deliberately performs no ArchiveBox CLI or REST calls. It only
builds a dry-run payload so a reviewer can inspect intended local inputs.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from aave.integrations.common import IntegrationDryRunResult, build_disabled_payload, write_json

CONNECTOR_NAME = "archivebox"


def build_archivebox_dry_run(
    output_directory: Path,
    enabled: bool = False,
    mode: str = "cli",
) -> IntegrationDryRunResult:
    """Write a disabled-by-default ArchiveBox dry-run payload."""
    output_path = output_directory / "archivebox_dry_run.json"
    if not enabled:
        payload = build_disabled_payload(
            CONNECTOR_NAME,
            "ArchiveBox integration is disabled by default; no CLI or REST call was made.",
        )
    else:
        payload = {
            "connector": CONNECTOR_NAME,
            "enabled": True,
            "dry_run": True,
            "mode": mode,
            "token_env_var": "AAVE_ARCHIVEBOX_TOKEN",
            "token_present": bool(os.getenv("AAVE_ARCHIVEBOX_TOKEN")),
            "payloads": [],
            "notes": [
                "Dry-run only. This skeleton does not call ArchiveBox.",
                "Future implementations must require explicit enablement and dry-run support.",
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


def build_archivebox_payload_from_url(source_url: str, title: str | None = None) -> dict[str, Any]:
    """Build a future ArchiveBox payload without sending it."""
    payload = {
        "url": source_url,
        "title": title,
        "note": "Prepared only; not submitted to ArchiveBox.",
    }
    return payload
