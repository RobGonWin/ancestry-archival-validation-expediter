"""Local ZIP member inspection and family-context association."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from aave.archive_formats import classify_file, get_archive_extension
from aave.config import AaveConfig, load_config
from aave.models import ZipInspectionResult, ZipMemberEntry
from aave.privacy import DEFAULT_PRIVACY_LABEL, DEFAULT_SOURCE_CONFIDENCE

ZIP_MEMBER_FIELD_NAMES = [
    "zip_path",
    "member_path",
    "filename",
    "extension",
    "file_category",
    "size_bytes",
    "compressed_size_bytes",
    "sha256",
    "crc32",
    "person_id",
    "gedcom_id",
    "family_context",
    "privacy_label",
    "source_confidence",
    "review_notes",
]


def inspect_zip_archive(
    zip_path: Path,
    output_directory: Path,
    config_path: Path | None = None,
    people_path: Path | None = None,
) -> ZipInspectionResult:
    """Inspect ZIP member metadata and associate members to configured people."""
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP file does not exist: {zip_path}")
    if not zip_path.is_file():
        raise IsADirectoryError(f"ZIP path must be a file: {zip_path}")
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"File is not a readable ZIP archive: {zip_path}")

    config = load_config(config_path) if config_path else AaveConfig()
    people = load_optional_json_list(people_path) if people_path else []
    people_by_person_id = {str(person.get("person_id")): person for person in people}
    people_by_gedcom_id = {
        str(person.get("gedcom_id")): person for person in people if person.get("gedcom_id")
    }

    output_directory.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as package:
        member_entries = [
            build_zip_member_entry(
                zip_path=zip_path,
                package=package,
                member_info=member_info,
                config=config,
                people_by_person_id=people_by_person_id,
                people_by_gedcom_id=people_by_gedcom_id,
            )
            for member_info in package.infolist()
            if not member_info.is_dir()
        ]

    write_json(
        [asdict(member_entry) for member_entry in member_entries],
        output_directory / "zip_member_manifest.json",
    )
    write_csv(member_entries, output_directory / "zip_member_manifest.csv")
    write_zip_report(member_entries, output_directory / "zip_inspection_report.md")

    result = ZipInspectionResult(
        member_count=len(member_entries),
        linked_member_count=sum(1 for member_entry in member_entries if member_entry.person_id),
        output_directory=output_directory,
    )
    return result


def build_zip_member_entry(
    zip_path: Path,
    package: zipfile.ZipFile,
    member_info: zipfile.ZipInfo,
    config: AaveConfig,
    people_by_person_id: dict[str, dict[str, Any]],
    people_by_gedcom_id: dict[str, dict[str, Any]],
) -> ZipMemberEntry:
    """Build one ZIP member metadata entry without extracting the archive."""
    member_path = member_info.filename.replace("\\", "/")
    member_filename = Path(member_path).name
    extension = get_archive_extension(Path(member_filename))
    context = find_best_context_match(
        zip_path=zip_path,
        member_path=member_path,
        contexts=config.zip_member_contexts,
    )
    resolved_context = resolve_context_people(
        context=context,
        people_by_person_id=people_by_person_id,
        people_by_gedcom_id=people_by_gedcom_id,
    )
    member_sha256 = calculate_zip_member_sha256(package, member_info)
    review_notes = build_review_notes(context, resolved_context)

    entry = ZipMemberEntry(
        zip_path=str(zip_path),
        member_path=member_path,
        filename=member_filename,
        extension=extension,
        file_category=classify_file(Path(member_filename)),
        size_bytes=member_info.file_size,
        compressed_size_bytes=member_info.compress_size,
        sha256=member_sha256,
        crc32=f"{member_info.CRC:08x}",
        person_id=resolved_context.get("person_id"),
        gedcom_id=resolved_context.get("gedcom_id"),
        family_context=resolved_context.get("family_context"),
        privacy_label=str(
            resolved_context.get("privacy_label")
            or config.default_privacy_label
            or DEFAULT_PRIVACY_LABEL
        ),
        source_confidence=str(
            resolved_context.get("source_confidence")
            or config.default_source_confidence
            or DEFAULT_SOURCE_CONFIDENCE
        ),
        review_notes=review_notes,
    )
    return entry


def find_best_context_match(
    zip_path: Path,
    member_path: str,
    contexts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find the longest matching ZIP member prefix context."""
    normalized_member_path = normalize_zip_path(member_path)
    normalized_zip_name = zip_path.name.lower()
    matches = []
    for context in contexts:
        context_zip_name = str(context.get("zip_filename") or context.get("zip_path") or "").lower()
        if context_zip_name and Path(context_zip_name).name.lower() != normalized_zip_name:
            continue
        member_prefix = normalize_zip_path(str(context.get("member_prefix") or ""))
        if member_prefix and not normalized_member_path.startswith(member_prefix):
            continue
        matches.append((len(member_prefix), context))

    if not matches:
        return None

    best_match = sorted(matches, key=lambda item: item[0], reverse=True)[0][1]
    return best_match


def resolve_context_people(
    context: dict[str, Any] | None,
    people_by_person_id: dict[str, dict[str, Any]],
    people_by_gedcom_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Resolve person IDs and GEDCOM IDs from a configured ZIP context."""
    if context is None:
        return {}

    person_id = normalize_optional_text(context.get("person_id"))
    gedcom_id = normalize_optional_text(context.get("gedcom_id"))
    person = None
    if person_id and person_id in people_by_person_id:
        person = people_by_person_id[person_id]
    elif gedcom_id and gedcom_id in people_by_gedcom_id:
        person = people_by_gedcom_id[gedcom_id]

    if person:
        person_id = normalize_optional_text(person.get("person_id"))
        gedcom_id = normalize_optional_text(person.get("gedcom_id"))

    resolved_context = {
        "person_id": person_id,
        "gedcom_id": gedcom_id,
        "family_context": normalize_optional_text(context.get("family_context")),
        "privacy_label": normalize_optional_text(context.get("privacy_label")),
        "source_confidence": normalize_optional_text(context.get("source_confidence")),
        "notes": context.get("notes"),
    }
    return resolved_context


def build_review_notes(
    context: dict[str, Any] | None,
    resolved_context: dict[str, Any],
) -> list[str]:
    """Build conservative review notes for a ZIP member association."""
    notes = [
        "ZIP member inspected locally without extraction.",
        "Association is folder/config metadata only and needs human review.",
    ]
    if context is None:
        notes.append("No ZIP member family context matched this member.")
    elif not resolved_context.get("person_id") and not resolved_context.get("gedcom_id"):
        notes.append("ZIP context matched, but no known person identifier was resolved.")

    configured_notes = context.get("notes") if context else None
    if isinstance(configured_notes, list):
        notes.extend(str(note) for note in configured_notes if str(note).strip())
    elif isinstance(configured_notes, str) and configured_notes.strip():
        notes.append(configured_notes)

    return notes


def calculate_zip_member_sha256(
    package: zipfile.ZipFile,
    member_info: zipfile.ZipInfo,
) -> str:
    """Calculate SHA-256 for a ZIP member stream without extracting it."""
    digest = hashlib.sha256()
    with package.open(member_info, "r") as member_file:
        for chunk in iter(lambda: member_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(data: list[dict[str, Any]], output_path: Path) -> None:
    """Write ZIP member metadata as JSON."""
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(data, output_file, indent=2)
        output_file.write("\n")


def write_csv(member_entries: list[ZipMemberEntry], output_path: Path) -> None:
    """Write ZIP member metadata as CSV."""
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=ZIP_MEMBER_FIELD_NAMES)
        writer.writeheader()
        for member_entry in member_entries:
            row = asdict(member_entry)
            row["review_notes"] = " | ".join(member_entry.review_notes)
            writer.writerow(row)


def write_zip_report(member_entries: list[ZipMemberEntry], output_path: Path) -> None:
    """Write a Markdown ZIP inspection report."""
    extension_counts = Counter(member.extension or "<none>" for member in member_entries)
    linked_count = sum(1 for member in member_entries if member.person_id)
    lines = [
        "# ZIP Inspection Report",
        "",
        f"ZIP file members inspected: {len(member_entries)}",
        f"Members associated with people: {linked_count}",
        "",
        "## Extension Summary",
        "",
    ]
    if extension_counts:
        lines.extend(
            f"- `{extension}`: {count}" for extension, count in sorted(extension_counts.items())
        )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- ZIP members were read locally without extraction.",
            "- Member-person associations come from config/folder context and require review.",
            "- This command does not parse raw DNA, call APIs, scrape websites, "
            "or bypass access controls.",
            "",
        ]
    )
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))


def load_optional_json_list(path: Path | None) -> list[dict[str, Any]]:
    """Load an optional JSON list of objects."""
    if path is None or not path.exists():
        return []
    raw_data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return [row for row in raw_data if isinstance(row, dict)]


def normalize_zip_path(path_value: str) -> str:
    """Normalize ZIP member path matching to lowercase POSIX prefixes."""
    normalized_path = path_value.replace("\\", "/").strip().lower()
    if normalized_path and not normalized_path.endswith("/"):
        normalized_path = f"{normalized_path}/"
    return normalized_path


def normalize_optional_text(value: object) -> str | None:
    """Normalize optional text values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
