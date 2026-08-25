from __future__ import annotations

import csv
import json
from pathlib import Path

from aave.archive_formats import classify_file, get_archive_extension
from aave.cli import main
from aave.manifest import infer_artifact_id, scan_archive


def write_fixture_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def build_sample_archive(tmp_path: Path) -> Path:
    archive_directory = tmp_path / "sample_archive"
    write_fixture_file(archive_directory / "photos" / "ART-1994-SRC-001 portrait.jpg", b"image")
    write_fixture_file(archive_directory / "docs" / "source.pdf", b"%PDF-1.4")
    write_fixture_file(archive_directory / "web" / "saved_page.html", b"<html></html>")
    write_fixture_file(archive_directory / "archives" / "capture.warc", b"WARC/1.1")
    write_fixture_file(archive_directory / "archives" / "capture.warc.gz", b"compressed")
    write_fixture_file(archive_directory / "archives" / "bundle.wacz", b"wacz")
    write_fixture_file(archive_directory / "tree" / "sample_tree.ged", b"0 HEAD\n0 TRLR\n")
    write_fixture_file(archive_directory / "sidecars" / "metadata.json", b"{}")
    write_fixture_file(archive_directory / "sidecars" / "metadata.yaml", b"version: 1\n")
    write_fixture_file(archive_directory / "sidecars" / "metadata.csv", b"artifact_id,title\n")
    write_fixture_file(archive_directory / "skip_me" / "ignored.txt", b"ignored")
    return archive_directory


def test_scan_archive_writes_manifest_outputs(tmp_path: Path) -> None:
    archive_directory = build_sample_archive(tmp_path)
    config_path = Path("tests/fixtures/sample_config.json")
    output_directory = tmp_path / "out"

    scan_result = scan_archive(
        input_directory=archive_directory,
        config_path=config_path,
        output_directory=output_directory,
    )

    assert scan_result.file_count == 10
    assert (output_directory / "archive_manifest.json").exists()
    assert (output_directory / "archive_manifest.csv").exists()
    assert (output_directory / "audit_summary.md").exists()

    manifest_data = json.loads((output_directory / "archive_manifest.json").read_text())
    assert len(manifest_data) == 10
    assert manifest_data[0]["relative_path"] == "archives/bundle.wacz"
    assert manifest_data[0]["privacy_label"] == "private_family_only"
    assert manifest_data[0]["source_confidence"] == "needs_review"
    assert all("sha256" in row for row in manifest_data)
    assert "skip_me/ignored.txt" not in {row["relative_path"] for row in manifest_data}


def test_scan_archive_csv_shape_matches_json(tmp_path: Path) -> None:
    archive_directory = build_sample_archive(tmp_path)
    config_path = Path("tests/fixtures/sample_config.json")
    output_directory = tmp_path / "out"

    scan_archive(
        input_directory=archive_directory,
        config_path=config_path,
        output_directory=output_directory,
    )

    manifest_data = json.loads((output_directory / "archive_manifest.json").read_text())
    with (output_directory / "archive_manifest.csv").open(newline="", encoding="utf-8") as csv_file:
        csv_rows = list(csv.DictReader(csv_file))

    assert len(csv_rows) == len(manifest_data)
    assert csv_rows[0]["relative_path"] == manifest_data[0]["relative_path"]
    assert csv_rows[0]["privacy_label"] == "private_family_only"


def test_archive_format_recognition() -> None:
    expected_categories = {
        "photo.jpg": "image",
        "photo.jpeg": "image",
        "photo.png": "image",
        "photo.tiff": "image",
        "photo.webp": "image",
        "source.pdf": "document",
        "notes.txt": "document",
        "notes.md": "document",
        "document.doc": "document",
        "document.docx": "document",
        "page.html": "web_snapshot",
        "page.htm": "web_snapshot",
        "capture.warc": "archive",
        "capture.warc.gz": "archive",
        "bundle.wacz": "archive",
        "bundle.zip": "archive",
        "tree.ged": "genealogy",
        "metadata.json": "sidecar",
        "metadata.yaml": "sidecar",
        "metadata.yml": "sidecar",
        "metadata.csv": "sidecar",
        "unknown.bin": "unknown",
    }

    for filename, expected_category in expected_categories.items():
        assert classify_file(Path(filename)) == expected_category

    assert get_archive_extension(Path("capture.warc.gz")) == ".warc.gz"


def test_artifact_id_inference_is_conservative() -> None:
    assert infer_artifact_id("ART-1994-SRC-001 portrait") == "ART-1994-SRC-001"
    assert infer_artifact_id("COLLECTION_IMAGE_001") == "COLLECTION-IMAGE-001"
    assert infer_artifact_id("family portrait") is None


def test_cli_scan_command_writes_outputs(tmp_path: Path) -> None:
    archive_directory = build_sample_archive(tmp_path)
    config_path = Path("tests/fixtures/sample_config.json")
    output_directory = tmp_path / "out"

    exit_code = main(
        [
            "scan",
            "--input",
            str(archive_directory),
            "--config",
            str(config_path),
            "--out",
            str(output_directory),
        ]
    )

    assert exit_code == 0
    assert (output_directory / "archive_manifest.json").exists()
