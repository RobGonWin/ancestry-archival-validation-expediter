"""File extension recognition and local archive-format metadata inspection."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from aave.models import ArchiveFormatMetadata, ArchiveInspectionResult

ARCHIVE_METADATA_EXTENSIONS = {".html", ".htm", ".pdf", ".warc", ".warc.gz", ".wacz"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".doc", ".docx"}
WEB_SNAPSHOT_EXTENSIONS = {".html", ".htm"}
ARCHIVE_EXTENSIONS = {".warc", ".warc.gz", ".wacz", ".zip"}
GENEALOGY_EXTENSIONS = {".ged"}
SIDECAR_EXTENSIONS = {".json", ".yaml", ".yml", ".csv"}

FILE_CATEGORY_BY_EXTENSION = {
    **{extension: "image" for extension in IMAGE_EXTENSIONS},
    **{extension: "document" for extension in DOCUMENT_EXTENSIONS},
    **{extension: "web_snapshot" for extension in WEB_SNAPSHOT_EXTENSIONS},
    **{extension: "archive" for extension in ARCHIVE_EXTENSIONS},
    **{extension: "genealogy" for extension in GENEALOGY_EXTENSIONS},
    **{extension: "sidecar" for extension in SIDECAR_EXTENSIONS},
}


def get_archive_extension(path: Path) -> str:
    """Return a normalized extension, preserving compound ``.warc.gz`` files."""
    path_name = path.name.lower()
    if path_name.endswith(".warc.gz"):
        extension = ".warc.gz"
        return extension

    extension = path.suffix.lower()
    return extension


def classify_file(path: Path) -> str:
    """Return the archive category for a path, or ``unknown``."""
    extension = get_archive_extension(path)
    file_category = FILE_CATEGORY_BY_EXTENSION.get(extension, "unknown")
    return file_category


class SavedHtmlMetadataParser(HTMLParser):
    """Extract title and likely source URL hints from saved local HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.probable_source_url: str | None = None
        self._is_in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_attrs = {name.lower(): value for name, value in attrs if value is not None}
        if tag.lower() == "title":
            self._is_in_title = True
        if tag.lower() == "meta":
            self._capture_meta_url(normalized_attrs)
        if tag.lower() == "link":
            self._capture_link_url(normalized_attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._is_in_title = False

    def handle_data(self, data: str) -> None:
        if self._is_in_title:
            self.title_parts.append(data)

    def _capture_meta_url(self, attrs: dict[str, str]) -> None:
        if self.probable_source_url:
            return
        key = attrs.get("property") or attrs.get("name") or ""
        if key.lower() in {"og:url", "twitter:url", "original-url", "source-url"}:
            self.probable_source_url = attrs.get("content")

    def _capture_link_url(self, attrs: dict[str, str]) -> None:
        if self.probable_source_url:
            return
        if attrs.get("rel", "").lower() == "canonical":
            self.probable_source_url = attrs.get("href")

    def get_title(self) -> str | None:
        """Return normalized title text when present."""
        title = " ".join(part.strip() for part in self.title_parts if part.strip())
        title = re.sub(r"\s+", " ", title).strip()
        return title or None


def inspect_archive_formats(manifest_path: Path, output_directory: Path) -> ArchiveInspectionResult:
    """Inspect saved local HTML/PDF/WARC/WACZ references from a manifest."""
    manifest_rows = load_manifest_rows(manifest_path)
    output_directory.mkdir(parents=True, exist_ok=True)

    metadata_rows = [
        inspect_manifest_row(manifest_row=manifest_row, manifest_path=manifest_path)
        for manifest_row in manifest_rows
        if str(manifest_row.get("extension", "")).lower() in ARCHIVE_METADATA_EXTENSIONS
    ]

    write_json(
        [asdict(metadata_row) for metadata_row in metadata_rows],
        output_directory / "archive_format_metadata.json",
    )
    write_archive_format_report(metadata_rows, output_directory / "archive_format_report.md")

    inspection_result = ArchiveInspectionResult(
        inspected_count=len(metadata_rows),
        output_directory=output_directory,
    )
    return inspection_result


def inspect_manifest_row(
    manifest_row: dict[str, Any],
    manifest_path: Path,
) -> ArchiveFormatMetadata:
    """Inspect one manifest row when it references a supported local archive format."""
    extension = str(manifest_row.get("extension", "")).lower()
    relative_path = str(manifest_row.get("relative_path", ""))
    local_path = resolve_manifest_relative_path(manifest_path, relative_path)
    notes: list[str] = []
    html_title = None
    probable_source_url = None
    pdf_page_count = None
    package_format = None

    if extension in {".warc", ".warc.gz"}:
        package_format = "warc"
        notes.append("WARC recognized as a local archival reference; replay is not implemented.")
    elif extension == ".wacz":
        package_format = "wacz"

    if local_path is None:
        notes.append("Local file could not be resolved from manifest path.")
    elif extension in {".html", ".htm"}:
        html_title, probable_source_url = inspect_html_file(local_path)
    elif extension == ".pdf":
        pdf_page_count = inspect_pdf_page_count(local_path)
        if pdf_page_count is None:
            notes.append("PDF page count unavailable; optional parser dependency not required.")
    elif extension == ".wacz":
        notes.extend(inspect_wacz_package(local_path))

    metadata = ArchiveFormatMetadata(
        relative_path=relative_path,
        artifact_id=normalize_optional_text(manifest_row.get("artifact_id")),
        file_type=extension.lstrip("."),
        size_bytes=int(manifest_row.get("size_bytes") or 0),
        sha256=str(manifest_row.get("sha256") or ""),
        html_title=html_title,
        probable_source_url=probable_source_url,
        pdf_page_count=pdf_page_count,
        package_format=package_format,
        inspection_notes=notes,
    )
    return metadata


def inspect_html_file(local_path: Path) -> tuple[str | None, str | None]:
    """Extract a saved HTML title and probable source URL without fetching anything."""
    html_text = local_path.read_text(encoding="utf-8-sig", errors="replace")
    parser = SavedHtmlMetadataParser()
    parser.feed(html_text)
    probable_source_url = parser.probable_source_url or find_probable_source_url(html_text)
    return parser.get_title(), probable_source_url


def find_probable_source_url(html_text: str) -> str | None:
    """Find source URL hints common in saved pages and SingleFile metadata."""
    patterns = [
        r"<!--\s*saved from url=\(\d+\)(?P<url>https?://[^ ]+)\s*-->",
        r'"url"\s*:\s*"(?P<url>https?://[^"]+)"',
        r"source_url\s*[:=]\s*[\"'](?P<url>https?://[^\"']+)[\"']",
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE)
        if match:
            return match.group("url")
    return None


def inspect_pdf_page_count(local_path: Path) -> int | None:
    """Extract a lightweight PDF page count by counting page object markers."""
    pdf_bytes = local_path.read_bytes()
    if not pdf_bytes.startswith(b"%PDF"):
        return None
    page_markers = re.findall(rb"/Type\s*/Page\b", pdf_bytes)
    if not page_markers:
        return None
    return len(page_markers)


def inspect_wacz_package(local_path: Path | None) -> list[str]:
    """Inspect WACZ as a package without replaying archived content."""
    if local_path is None:
        return ["WACZ package file could not be resolved."]
    notes = ["WACZ recognized as a local package; replay is not implemented."]
    if zipfile.is_zipfile(local_path):
        with zipfile.ZipFile(local_path) as package:
            member_count = len(package.namelist())
        notes.append(f"WACZ ZIP member count: {member_count}.")
    else:
        notes.append("WACZ file is not readable as a ZIP package.")
    return notes


def resolve_manifest_relative_path(manifest_path: Path, relative_path: str) -> Path | None:
    """Resolve a manifest relative path without assuming one archive root layout."""
    candidate_paths = [
        manifest_path.parent / relative_path,
        manifest_path.parent.parent / relative_path,
        Path(relative_path),
    ]
    for candidate_path in candidate_paths:
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path

    search_root = manifest_path.parent.parent
    if search_root.exists():
        for child_directory in sorted(search_root.iterdir()):
            if not child_directory.is_dir():
                continue
            candidate_path = child_directory / relative_path
            if candidate_path.exists() and candidate_path.is_file():
                return candidate_path
    return None


def load_manifest_rows(manifest_path: Path) -> list[dict[str, Any]]:
    """Load archive manifest rows."""
    raw_data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {manifest_path}")
    rows = [row for row in raw_data if isinstance(row, dict)]
    return rows


def write_json(data: list[dict[str, Any]], output_path: Path) -> None:
    """Write formatted JSON metadata for archive inspection."""
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(data, output_file, indent=2)
        output_file.write("\n")


def write_archive_format_report(
    metadata_rows: list[ArchiveFormatMetadata],
    output_path: Path,
) -> None:
    """Write a Markdown archive format inspection report."""
    lines = [
        "# Archive Format Report",
        "",
        f"Supported local archive/reference files inspected: {len(metadata_rows)}",
        "",
        "## Summary",
        "",
    ]
    if not metadata_rows:
        lines.append("- No supported archive-format files found.")
    else:
        for metadata in metadata_rows:
            title = metadata.html_title or metadata.package_format or metadata.file_type
            lines.append(f"- `{metadata.relative_path}`: {title}")

    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- This inspection reads saved local files only.",
            "- No network access, crawling, replay, login automation, or bypassing is performed.",
            "- WARC/WACZ entries are recognized as archival references, not authenticity proof.",
            "- PDF page count is best-effort and may be unavailable.",
            "",
        ]
    )
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))


def normalize_optional_text(value: object) -> str | None:
    """Normalize optional text from manifest fields."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
