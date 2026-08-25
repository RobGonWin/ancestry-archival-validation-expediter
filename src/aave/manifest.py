"""Local folder manifest generation."""

from __future__ import annotations

import csv
import json
import mimetypes
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from aave.archive_formats import classify_file, get_archive_extension
from aave.config import load_config
from aave.models import MANIFEST_FIELD_NAMES, ArchiveManifestRow, ScanResult
from aave.utils import calculate_sha256, format_modified_time, iter_files

ARTIFACT_ID_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+){2,}\b")


def scan_archive(input_directory: Path, config_path: Path, output_directory: Path) -> ScanResult:
    """Scan a local archive folder and write manifest outputs."""
    if not input_directory.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_directory}")
    if not input_directory.is_dir():
        raise NotADirectoryError(f"Input path must be a directory: {input_directory}")

    config = load_config(config_path)
    output_directory.mkdir(parents=True, exist_ok=True)

    manifest_rows = [
        build_manifest_row(
            file_path=file_path,
            input_directory=input_directory,
            default_privacy_label=config.default_privacy_label,
            default_source_confidence=config.default_source_confidence,
        )
        for file_path in iter_files(input_directory, set(config.excluded_directory_names))
    ]

    write_manifest_json(manifest_rows, output_directory / "archive_manifest.json")
    write_manifest_csv(manifest_rows, output_directory / "archive_manifest.csv")
    write_audit_summary(manifest_rows, output_directory / "audit_summary.md")

    scan_result = ScanResult(file_count=len(manifest_rows), output_directory=output_directory)
    return scan_result


def build_manifest_row(
    file_path: Path,
    input_directory: Path,
    default_privacy_label: str,
    default_source_confidence: str,
) -> ArchiveManifestRow:
    """Build one manifest row for a local file."""
    relative_path = file_path.relative_to(input_directory).as_posix()
    extension = get_archive_extension(file_path)
    mime_guess = mimetypes.guess_type(file_path.name)[0]
    file_category = classify_file(file_path)
    file_stat = file_path.stat()
    artifact_id = infer_artifact_id(file_path.stem)

    manifest_row = ArchiveManifestRow(
        relative_path=relative_path,
        filename=file_path.name,
        extension=extension,
        file_category=file_category,
        mime_guess=mime_guess,
        size_bytes=file_stat.st_size,
        sha256=calculate_sha256(file_path),
        modified_time_iso=format_modified_time(file_stat.st_mtime),
        artifact_id=artifact_id,
        privacy_label=default_privacy_label,
        source_confidence=default_source_confidence,
    )
    return manifest_row


def infer_artifact_id(filename_stem: str) -> str | None:
    """Infer a stable-looking artifact ID from an uppercase hyphenated filename token."""
    normalized_stem = filename_stem.replace("_", "-")
    match = ARTIFACT_ID_PATTERN.search(normalized_stem)
    artifact_id = match.group(0) if match else None
    return artifact_id


def write_manifest_json(manifest_rows: list[ArchiveManifestRow], output_path: Path) -> None:
    """Write manifest rows as formatted JSON."""
    manifest_data = [asdict(manifest_row) for manifest_row in manifest_rows]
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(manifest_data, output_file, indent=2)
        output_file.write("\n")


def write_manifest_csv(manifest_rows: list[ArchiveManifestRow], output_path: Path) -> None:
    """Write manifest rows as CSV."""
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=MANIFEST_FIELD_NAMES)
        writer.writeheader()
        for manifest_row in manifest_rows:
            writer.writerow(asdict(manifest_row))


def write_audit_summary(manifest_rows: list[ArchiveManifestRow], output_path: Path) -> None:
    """Write a concise Markdown audit summary for a scan."""
    category_counts = Counter(row.file_category for row in manifest_rows)
    privacy_counts = Counter(row.privacy_label for row in manifest_rows)
    confidence_counts = Counter(row.source_confidence for row in manifest_rows)

    lines = [
        "# Archive Scan Audit Summary",
        "",
        f"Total files scanned: {len(manifest_rows)}",
        "",
        "## File Categories",
        "",
    ]
    lines.extend(format_counter_lines(category_counts))
    lines.extend(["", "## Privacy Labels", ""])
    lines.extend(format_counter_lines(privacy_counts))
    lines.extend(["", "## Source Confidence Labels", ""])
    lines.extend(format_counter_lines(confidence_counts))
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- This scan used local files only.",
            "- This scan did not scrape websites or automate access-controlled systems.",
            "- This scan did not parse raw DNA files or make medical claims.",
            "",
        ]
    )

    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))


def format_counter_lines(counter: Counter[str]) -> list[str]:
    """Format counter values as Markdown bullet lines."""
    if not counter:
        empty_lines = ["- None"]
        return empty_lines

    counter_lines = [f"- `{name}`: {count}" for name, count in sorted(counter.items())]
    return counter_lines
