from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from aave.archive_formats import inspect_archive_formats
from aave.cli import main


def write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def build_manifest_row(path: Path, root: Path, artifact_id: str) -> dict[str, object]:
    relative_path = path.relative_to(root).as_posix()
    extension = ".warc.gz" if path.name.endswith(".warc.gz") else path.suffix.lower()
    return {
        "relative_path": relative_path,
        "filename": path.name,
        "extension": extension,
        "file_category": "archive",
        "mime_guess": None,
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "modified_time_iso": "2026-06-19T00:00:00+00:00",
        "artifact_id": artifact_id,
        "privacy_label": "private_family_only",
        "source_confidence": "needs_review",
    }


def build_archive_fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "archive"
    html_path = root / "saved" / "page.html"
    pdf_path = root / "docs" / "sample.pdf"
    warc_path = root / "captures" / "sample.warc"
    warc_gz_path = root / "captures" / "sample.warc.gz"
    wacz_path = root / "captures" / "sample.wacz"

    write_bytes(
        html_path,
        b"""<!doctype html>
<html>
<head>
  <title> Example Saved Page </title>
  <meta property="og:url" content="https://example.org/source-page">
</head>
<body>Saved locally.</body>
</html>
""",
    )
    write_bytes(
        pdf_path,
        b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nendobj\n2 0 obj\n<< /Type /Page >>\nendobj\n",
    )
    write_bytes(warc_path, b"WARC/1.1\r\nWARC-Type: warcinfo\r\n\r\n")
    write_bytes(warc_gz_path, b"\x1f\x8bsynthetic")
    wacz_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wacz_path, "w") as package:
        package.writestr("datapackage.json", "{}")
        package.writestr("archive/index.cdx", "")

    manifest_path = tmp_path / "out" / "archive_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        build_manifest_row(html_path, root, "HTML-001"),
        build_manifest_row(pdf_path, root, "PDF-001"),
        build_manifest_row(warc_path, root, "WARC-001"),
        build_manifest_row(warc_gz_path, root, "WARCGZ-001"),
        build_manifest_row(wacz_path, root, "WACZ-001"),
    ]
    manifest_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return manifest_path, manifest_path.parent


def load_metadata(output_directory: Path) -> dict[str, dict[str, object]]:
    rows = json.loads((output_directory / "archive_format_metadata.json").read_text())
    return {row["relative_path"]: row for row in rows}


def test_inspect_archives_extracts_html_title_and_source_url(tmp_path: Path) -> None:
    manifest_path, output_directory = build_archive_fixture(tmp_path)

    inspect_archive_formats(manifest_path=manifest_path, output_directory=output_directory)

    metadata = load_metadata(output_directory)
    html_metadata = metadata["saved/page.html"]

    assert html_metadata["html_title"] == "Example Saved Page"
    assert html_metadata["probable_source_url"] == "https://example.org/source-page"
    assert html_metadata["file_type"] == "html"


def test_inspect_archives_extracts_pdf_page_count_when_possible(tmp_path: Path) -> None:
    manifest_path, output_directory = build_archive_fixture(tmp_path)

    inspect_archive_formats(manifest_path=manifest_path, output_directory=output_directory)

    metadata = load_metadata(output_directory)

    assert metadata["docs/sample.pdf"]["pdf_page_count"] == 2


def test_inspect_archives_recognizes_warc_and_wacz_without_replay(tmp_path: Path) -> None:
    manifest_path, output_directory = build_archive_fixture(tmp_path)

    inspect_archive_formats(manifest_path=manifest_path, output_directory=output_directory)

    metadata = load_metadata(output_directory)

    assert metadata["captures/sample.warc"]["package_format"] == "warc"
    assert metadata["captures/sample.warc.gz"]["package_format"] == "warc"
    assert metadata["captures/sample.wacz"]["package_format"] == "wacz"
    assert "WACZ ZIP member count: 2." in metadata["captures/sample.wacz"]["inspection_notes"]
    report = (output_directory / "archive_format_report.md").read_text()
    assert "No network access, crawling, replay" in report


def test_cli_inspect_archives_command_writes_outputs(tmp_path: Path) -> None:
    manifest_path, output_directory = build_archive_fixture(tmp_path)

    exit_code = main(
        [
            "inspect-archives",
            "--manifest",
            str(manifest_path),
            "--out",
            str(output_directory),
        ]
    )

    assert exit_code == 0
    assert (output_directory / "archive_format_report.md").exists()
    assert (output_directory / "archive_format_metadata.json").exists()
