from __future__ import annotations

import json
from pathlib import Path

from aave.cli import main
from aave.integrations.archivebox_connector import build_archivebox_dry_run
from aave.integrations.perma_connector import build_perma_dry_run
from aave.integrations.static_site_export import build_static_site_dry_run
from aave.integrations.zotero_connector import build_zotero_dry_run


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_archivebox_perma_and_zotero_are_disabled_by_default(tmp_path: Path) -> None:
    output_directory = tmp_path / "integrations"

    archivebox_result = build_archivebox_dry_run(output_directory)
    perma_result = build_perma_dry_run(output_directory)
    zotero_result = build_zotero_dry_run(output_directory)

    archivebox_payload = load_json(archivebox_result.output_path)
    perma_payload = load_json(perma_result.output_path)
    zotero_payload = load_json(zotero_result.output_path)

    assert archivebox_payload["enabled"] is False
    assert perma_payload["enabled"] is False
    assert zotero_payload["enabled"] is False
    assert archivebox_payload["payloads"] == []
    assert perma_payload["payloads"] == []
    assert zotero_payload["payloads"] == []
    assert "no CLI or REST call was made" in archivebox_payload["notes"][0]
    assert "no API call was made" in perma_payload["notes"][0]
    assert "no API call was made" in zotero_payload["notes"][0]


def test_zotero_enabled_mode_is_still_dry_run_only(tmp_path: Path) -> None:
    manifest_path = tmp_path / "archive_manifest.json"
    write_json(
        manifest_path,
        [
            {
                "relative_path": "public/source.pdf",
                "filename": "source.pdf",
                "artifact_id": "SRC-001",
                "sha256": "abc",
                "privacy_label": "public_ok",
                "source_confidence": "needs_review",
            }
        ],
    )

    result = build_zotero_dry_run(tmp_path / "integrations", manifest_path, enabled=True)
    payload = load_json(result.output_path)

    assert payload["enabled"] is True
    assert payload["dry_run"] is True
    assert payload["payloads"][0]["title"] == "SRC-001"
    assert payload["payloads"][0]["note"] == "Prepared only; not submitted to Zotero."


def test_static_site_output_filters_to_public_metadata_only(tmp_path: Path) -> None:
    export_manifest_path = tmp_path / "export_manifest.json"
    write_json(
        export_manifest_path,
        [
            build_export_row("public/photo.jpg", "public_ok"),
            build_export_row("private/note.md", "private_family_only"),
            build_export_row("sensitive/raw-dna-export.txt", "public_summary_only"),
        ],
    )

    result = build_static_site_dry_run(
        tmp_path / "static_public",
        export_manifest_path,
        enabled=True,
    )
    payload = load_json(result.output_path)

    assert result.payload_count == 1
    assert payload["blocked_count"] == 2
    assert payload["payloads"][0]["relative_path"] == "public/photo.jpg"
    assert (tmp_path / "static_public" / "PUBLIC_EXPORT_PREVIEW.md").exists()


def test_cli_integrations_commands_write_dry_run_outputs(tmp_path: Path) -> None:
    export_manifest_path = tmp_path / "export_manifest.json"
    write_json(export_manifest_path, [build_export_row("public/photo.jpg", "public_ok")])

    archivebox_exit = main(["integrations", "archivebox", "--out", str(tmp_path / "a")])
    zotero_exit = main(["integrations", "zotero", "--out", str(tmp_path / "z")])
    perma_exit = main(["integrations", "perma", "--out", str(tmp_path / "p")])
    static_exit = main(
        [
            "integrations",
            "static-site",
            "--export-manifest",
            str(export_manifest_path),
            "--out",
            str(tmp_path / "s"),
        ]
    )

    assert archivebox_exit == 0
    assert zotero_exit == 0
    assert perma_exit == 0
    assert static_exit == 0
    assert (tmp_path / "a" / "archivebox_dry_run.json").exists()
    assert (tmp_path / "z" / "zotero_dry_run.json").exists()
    assert (tmp_path / "p" / "perma_dry_run.json").exists()
    assert (tmp_path / "s" / "static_site_dry_run.json").exists()


def build_export_row(relative_path: str, privacy_label: str) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "artifact_id": "ART-001",
        "person_id": "john-smith-i1",
        "gedcom_id": "I1",
        "display_name": "John Smith",
        "privacy_label": privacy_label,
        "source_confidence": "needs_review",
        "export_profile": "public_redacted",
        "export_decision": "included",
        "exclusion_reasons": "",
    }
