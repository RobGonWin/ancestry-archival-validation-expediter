"""Static public metadata output skeleton for GitHub Pages or Notion copy-paste."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aave.integrations.common import IntegrationDryRunResult, load_json_list, write_json

CONNECTOR_NAME = "static_site"
PUBLIC_ALLOWED_PRIVACY_LABELS = {"public_ok", "public_summary_only"}


def build_static_site_dry_run(
    output_directory: Path,
    export_manifest_path: Path,
    enabled: bool = False,
) -> IntegrationDryRunResult:
    """Write static public metadata files from an already-redacted export manifest."""
    rows = load_json_list(export_manifest_path)
    public_rows = [row for row in rows if is_public_row(row)]
    blocked_count = len(rows) - len(public_rows)
    output_path = output_directory / "static_site_dry_run.json"
    payload = {
        "connector": CONNECTOR_NAME,
        "enabled": enabled,
        "dry_run": True,
        "source_export_manifest": str(export_manifest_path),
        "payload_count": len(public_rows),
        "blocked_count": blocked_count,
        "payloads": [build_static_public_payload(row) for row in public_rows],
        "notes": [
            "Static output is dry-run metadata only.",
            "Only public_ok and public_summary_only rows are eligible.",
            "No source files, raw DNA, or genotypes are copied.",
        ],
    }
    write_json(payload, output_path)
    write_static_public_markdown(output_directory / "PUBLIC_EXPORT_PREVIEW.md", public_rows)
    return IntegrationDryRunResult(
        connector=CONNECTOR_NAME,
        enabled=enabled,
        dry_run=True,
        payload_count=len(public_rows),
        output_path=output_path,
    )


def is_public_row(row: dict[str, Any]) -> bool:
    """Return whether a row is eligible for static public metadata output."""
    privacy_label = str(row.get("privacy_label") or "")
    relative_path = str(row.get("relative_path") or "").lower()
    has_raw_dna_text = any(
        term in relative_path for term in ["ancestrydna", "raw_dna", "raw-dna", "genotype"]
    )
    is_public = privacy_label in PUBLIC_ALLOWED_PRIVACY_LABELS and not has_raw_dna_text
    return is_public


def build_static_public_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Build a public-safe static metadata payload."""
    payload = {
        "relative_path": row.get("relative_path"),
        "artifact_id": row.get("artifact_id"),
        "display_name": row.get("display_name"),
        "privacy_label": row.get("privacy_label"),
        "source_confidence": row.get("source_confidence"),
        "note": "Metadata-only public preview; source files are not copied.",
    }
    return payload


def write_static_public_markdown(output_path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a Markdown preview for public-safe metadata rows."""
    lines = [
        "# Public Export Preview",
        "",
        "This preview contains metadata only. Source files are not copied.",
        "",
        "```json",
        json.dumps([build_static_public_payload(row) for row in rows], indent=2),
        "```",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))
        output_file.write("\n")
