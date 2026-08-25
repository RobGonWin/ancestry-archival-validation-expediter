"""Zotero integration skeleton with dry-run metadata payloads only."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from aave.integrations.common import (
    IntegrationDryRunResult,
    build_disabled_payload,
    load_json_list,
    write_json,
)

CONNECTOR_NAME = "zotero"


def build_zotero_dry_run(
    output_directory: Path,
    manifest_path: Path | None = None,
    enabled: bool = False,
) -> IntegrationDryRunResult:
    """Write a disabled-by-default Zotero dry-run payload."""
    output_path = output_directory / "zotero_dry_run.json"
    if not enabled:
        payload = build_disabled_payload(
            CONNECTOR_NAME,
            "Zotero integration is disabled by default; no API call was made.",
        )
    else:
        rows = load_json_list(manifest_path) if manifest_path else []
        payloads = [build_zotero_payload(row) for row in rows]
        payload = {
            "connector": CONNECTOR_NAME,
            "enabled": True,
            "dry_run": True,
            "api_key_env_var": "AAVE_ZOTERO_API_KEY",
            "library_id_env_var": "AAVE_ZOTERO_LIBRARY_ID",
            "api_key_present": bool(os.getenv("AAVE_ZOTERO_API_KEY")),
            "library_id_present": bool(os.getenv("AAVE_ZOTERO_LIBRARY_ID")),
            "payloads": payloads,
            "notes": ["Dry-run only. No Zotero item was created or updated."],
        }

    write_json(payload, output_path)
    return IntegrationDryRunResult(
        connector=CONNECTOR_NAME,
        enabled=enabled,
        dry_run=True,
        payload_count=len(payload["payloads"]),
        output_path=output_path,
    )


def build_zotero_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Build a conservative Zotero item payload from manifest metadata."""
    title = row.get("artifact_id") or row.get("filename") or row.get("relative_path")
    payload = {
        "itemType": "document",
        "title": title,
        "archiveLocation": row.get("relative_path"),
        "extra": {
            "sha256": row.get("sha256"),
            "privacy_label": row.get("privacy_label"),
            "source_confidence": row.get("source_confidence"),
        },
        "note": "Prepared only; not submitted to Zotero.",
    }
    return payload
