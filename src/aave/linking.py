"""Conservative source/media linking for archive artifacts and GEDCOM people."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from aave.config import load_config
from aave.models import LinkingResult, SourceLinkEntry
from aave.privacy import (
    DEFAULT_PRIVACY_LABEL,
    PRIVACY_LABELS,
    SOURCE_CONFIDENCE_LABELS,
)

REVIEW_CONFIDENCE = "needs_review"
SIDECAR_EXTENSIONS = {".json", ".yaml", ".yml", ".csv"}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
YEAR_PATTERN = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")


def link_sources(
    manifest_path: Path,
    people_path: Path,
    config_path: Path,
    output_directory: Path,
) -> LinkingResult:
    """Link scanned artifacts to people using conservative local metadata."""
    manifest_rows = load_json_list(manifest_path)
    people_rows = load_json_list(people_path)
    config = load_config(config_path)
    output_directory.mkdir(parents=True, exist_ok=True)

    people_by_person_id = {str(person["person_id"]): person for person in people_rows}
    people_by_gedcom_id = {
        str(person["gedcom_id"]): person for person in people_rows if person.get("gedcom_id")
    }
    sidecar_links = load_sidecar_links(
        manifest_rows=manifest_rows,
        manifest_path=manifest_path,
        people_by_person_id=people_by_person_id,
        people_by_gedcom_id=people_by_gedcom_id,
    )
    manual_links = build_manual_links(
        manual_source_links=config.manual_source_links,
        people_by_person_id=people_by_person_id,
        people_by_gedcom_id=people_by_gedcom_id,
    )

    source_links = [
        build_source_link(
            manifest_row=manifest_row,
            people_rows=people_rows,
            people_by_person_id=people_by_person_id,
            people_by_gedcom_id=people_by_gedcom_id,
            manual_links=manual_links,
            sidecar_links=sidecar_links,
            default_privacy_label=config.default_privacy_label,
            default_source_confidence=config.default_source_confidence,
        )
        for manifest_row in manifest_rows
    ]

    write_json(
        [asdict(source_link) for source_link in source_links],
        output_directory / "source_links.json",
    )
    write_linking_report(source_links, output_directory / "linking_report.md")

    linked_count = sum(1 for source_link in source_links if source_link.person_id)
    needs_review_count = sum(
        1 for source_link in source_links if source_link.match_confidence == REVIEW_CONFIDENCE
    )
    linking_result = LinkingResult(
        link_count=len(source_links),
        linked_count=linked_count,
        needs_review_count=needs_review_count,
        output_directory=output_directory,
    )
    return linking_result


def build_source_link(
    manifest_row: dict[str, Any],
    people_rows: list[dict[str, Any]],
    people_by_person_id: dict[str, dict[str, Any]],
    people_by_gedcom_id: dict[str, dict[str, Any]],
    manual_links: dict[str, dict[str, Any]],
    sidecar_links: dict[str, dict[str, Any]],
    default_privacy_label: str,
    default_source_confidence: str,
) -> SourceLinkEntry:
    """Build one source link entry following configured precedence."""
    relative_path = str(manifest_row.get("relative_path", ""))
    artifact_id = normalize_optional_text(manifest_row.get("artifact_id"))
    artifact_keys = build_artifact_keys(relative_path, artifact_id)

    manual_match = find_first_keyed_match(artifact_keys, manual_links)
    if manual_match:
        source_link = build_link_from_match(
            manifest_row=manifest_row,
            match=manual_match,
            match_method="manual_config",
            match_confidence=manual_match.get("source_confidence", "confirmed"),
            default_privacy_label=default_privacy_label,
            default_source_confidence=default_source_confidence,
            review_notes=["Manual config mapping applied."],
        )
        return source_link

    sidecar_match = find_first_keyed_match(artifact_keys, sidecar_links)
    if sidecar_match:
        source_link = build_link_from_match(
            manifest_row=manifest_row,
            match=sidecar_match,
            match_method="sidecar_metadata",
            match_confidence=sidecar_match.get("source_confidence", "family_identified"),
            default_privacy_label=default_privacy_label,
            default_source_confidence=default_source_confidence,
            review_notes=["Sidecar metadata mapping applied."],
        )
        return source_link

    artifact_match = match_by_artifact_id(artifact_id, people_rows)
    if artifact_match:
        source_link = build_link_from_person(
            manifest_row=manifest_row,
            person=artifact_match,
            match_method="artifact_id",
            match_confidence="probable",
            default_privacy_label=default_privacy_label,
            default_source_confidence=default_source_confidence,
            review_notes=["Artifact ID matched a person identifier token."],
        )
        return source_link

    filename_match = match_by_filename_tokens(manifest_row, people_rows)
    if filename_match["status"] == "matched":
        source_link = build_link_from_person(
            manifest_row=manifest_row,
            person=filename_match["person"],
            match_method="filename_tokens",
            match_confidence=filename_match["confidence"],
            default_privacy_label=default_privacy_label,
            default_source_confidence=default_source_confidence,
            review_notes=filename_match["review_notes"],
        )
        return source_link

    source_link = build_review_link(
        manifest_row=manifest_row,
        default_privacy_label=default_privacy_label,
        default_source_confidence=default_source_confidence,
        review_notes=filename_match["review_notes"],
    )
    return source_link


def build_link_from_match(
    manifest_row: dict[str, Any],
    match: dict[str, Any],
    match_method: str,
    match_confidence: str,
    default_privacy_label: str,
    default_source_confidence: str,
    review_notes: list[str],
) -> SourceLinkEntry:
    """Build a source link from explicit manual or sidecar metadata."""
    privacy_label = choose_valid_label(
        match.get("privacy_label"),
        manifest_row.get("privacy_label"),
        default_privacy_label,
        allowed_labels=PRIVACY_LABELS,
    )
    source_confidence = choose_valid_label(
        match.get("source_confidence"),
        manifest_row.get("source_confidence"),
        default_source_confidence,
        allowed_labels=SOURCE_CONFIDENCE_LABELS,
    )
    confidence = validate_label(
        match_confidence,
        allowed_labels=SOURCE_CONFIDENCE_LABELS,
        fallback=source_confidence,
    )
    person_id = normalize_optional_text(match.get("person_id"))
    gedcom_id = normalize_optional_text(match.get("gedcom_id"))

    source_link = SourceLinkEntry(
        link_id=build_link_id(str(manifest_row.get("relative_path", "")), person_id),
        artifact_id=normalize_optional_text(manifest_row.get("artifact_id")),
        relative_path=str(manifest_row.get("relative_path", "")),
        person_id=person_id,
        gedcom_id=gedcom_id,
        match_method=match_method,
        match_confidence=confidence,
        privacy_label=privacy_label,
        source_confidence=source_confidence,
        review_notes=[*review_notes, *normalize_notes(match.get("notes"))],
    )
    return source_link


def build_link_from_person(
    manifest_row: dict[str, Any],
    person: dict[str, Any],
    match_method: str,
    match_confidence: str,
    default_privacy_label: str,
    default_source_confidence: str,
    review_notes: list[str],
) -> SourceLinkEntry:
    """Build a source link from an inferred person match."""
    privacy_label = choose_valid_label(
        manifest_row.get("privacy_label"),
        default_privacy_label,
        allowed_labels=PRIVACY_LABELS,
    )
    source_confidence = choose_valid_label(
        manifest_row.get("source_confidence"),
        default_source_confidence,
        allowed_labels=SOURCE_CONFIDENCE_LABELS,
    )
    person_id = str(person.get("person_id"))

    source_link = SourceLinkEntry(
        link_id=build_link_id(str(manifest_row.get("relative_path", "")), person_id),
        artifact_id=normalize_optional_text(manifest_row.get("artifact_id")),
        relative_path=str(manifest_row.get("relative_path", "")),
        person_id=person_id,
        gedcom_id=normalize_optional_text(person.get("gedcom_id")),
        match_method=match_method,
        match_confidence=match_confidence,
        privacy_label=privacy_label,
        source_confidence=source_confidence,
        review_notes=review_notes,
    )
    return source_link


def build_review_link(
    manifest_row: dict[str, Any],
    default_privacy_label: str,
    default_source_confidence: str,
    review_notes: list[str],
) -> SourceLinkEntry:
    """Build a needs-review source link when no conservative match is available."""
    privacy_label = choose_valid_label(
        manifest_row.get("privacy_label"),
        default_privacy_label,
        allowed_labels=PRIVACY_LABELS,
    )
    source_confidence = choose_valid_label(
        manifest_row.get("source_confidence"),
        default_source_confidence,
        allowed_labels=SOURCE_CONFIDENCE_LABELS,
    )

    source_link = SourceLinkEntry(
        link_id=build_link_id(str(manifest_row.get("relative_path", "")), None),
        artifact_id=normalize_optional_text(manifest_row.get("artifact_id")),
        relative_path=str(manifest_row.get("relative_path", "")),
        person_id=None,
        gedcom_id=None,
        match_method="needs_review",
        match_confidence=REVIEW_CONFIDENCE,
        privacy_label=privacy_label,
        source_confidence=source_confidence,
        review_notes=review_notes,
    )
    return source_link


def load_sidecar_links(
    manifest_rows: list[dict[str, Any]],
    manifest_path: Path,
    people_by_person_id: dict[str, dict[str, Any]],
    people_by_gedcom_id: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Load sidecar JSON/YAML/CSV metadata mappings from resolvable local files."""
    sidecar_links: dict[str, dict[str, Any]] = {}
    for manifest_row in manifest_rows:
        relative_path = str(manifest_row.get("relative_path", ""))
        extension = str(manifest_row.get("extension", "")).lower()
        if extension not in SIDECAR_EXTENSIONS:
            continue

        sidecar_path = resolve_manifest_relative_path(manifest_path, relative_path)
        if sidecar_path is None:
            continue

        for sidecar_record in read_sidecar_records(sidecar_path):
            normalized_match = normalize_explicit_match(
                raw_match=sidecar_record,
                people_by_person_id=people_by_person_id,
                people_by_gedcom_id=people_by_gedcom_id,
            )
            if not normalized_match:
                continue

            target_keys = build_artifact_keys(
                normalize_optional_text(sidecar_record.get("relative_path"))
                or normalize_optional_text(sidecar_record.get("local_path"))
                or relative_path,
                normalize_optional_text(sidecar_record.get("artifact_id")),
            )
            for target_key in target_keys:
                sidecar_links[target_key] = normalized_match

    return sidecar_links


def read_sidecar_records(sidecar_path: Path) -> list[dict[str, Any]]:
    """Read JSON, YAML, or CSV sidecar metadata as dictionaries."""
    extension = sidecar_path.suffix.lower()
    if extension == ".json":
        raw_data = json.loads(sidecar_path.read_text(encoding="utf-8-sig"))
        records = normalize_sidecar_data(raw_data)
        return records
    if extension in {".yaml", ".yml"}:
        raw_data = yaml.safe_load(sidecar_path.read_text(encoding="utf-8-sig")) or {}
        records = normalize_sidecar_data(raw_data)
        return records
    if extension == ".csv":
        with sidecar_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            records = [dict(row) for row in csv.DictReader(csv_file)]
        return records

    return []


def normalize_sidecar_data(raw_data: Any) -> list[dict[str, Any]]:
    """Normalize supported sidecar data shapes into a record list."""
    if isinstance(raw_data, list):
        return [record for record in raw_data if isinstance(record, dict)]
    if isinstance(raw_data, dict):
        records = raw_data.get("records")
        if isinstance(records, list):
            return [record for record in records if isinstance(record, dict)]
        return [raw_data]
    return []


def build_manual_links(
    manual_source_links: list[dict[str, Any]],
    people_by_person_id: dict[str, dict[str, Any]],
    people_by_gedcom_id: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build keyed manual mappings from config."""
    manual_links: dict[str, dict[str, Any]] = {}
    for manual_source_link in manual_source_links:
        normalized_match = normalize_explicit_match(
            raw_match=manual_source_link,
            people_by_person_id=people_by_person_id,
            people_by_gedcom_id=people_by_gedcom_id,
        )
        if not normalized_match:
            continue

        artifact_keys = build_artifact_keys(
            normalize_optional_text(manual_source_link.get("relative_path"))
            or normalize_optional_text(manual_source_link.get("local_path")),
            normalize_optional_text(manual_source_link.get("artifact_id")),
        )
        for artifact_key in artifact_keys:
            manual_links[artifact_key] = normalized_match

    return manual_links


def normalize_explicit_match(
    raw_match: dict[str, Any],
    people_by_person_id: dict[str, dict[str, Any]],
    people_by_gedcom_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Resolve explicit person identifiers from manual config or sidecars."""
    person = None
    person_id = normalize_optional_text(raw_match.get("person_id")) or normalize_optional_text(
        raw_match.get("person_slug")
    )
    gedcom_id = normalize_optional_text(raw_match.get("gedcom_id"))

    if person_id and person_id in people_by_person_id:
        person = people_by_person_id[person_id]
    elif gedcom_id and gedcom_id in people_by_gedcom_id:
        person = people_by_gedcom_id[gedcom_id]

    if person is None:
        return None

    normalized_match = {
        "person_id": person.get("person_id"),
        "gedcom_id": person.get("gedcom_id"),
        "privacy_label": raw_match.get("privacy_label"),
        "source_confidence": raw_match.get("source_confidence"),
        "notes": raw_match.get("notes"),
    }
    return normalized_match


def match_by_artifact_id(
    artifact_id: str | None,
    people_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Match artifact IDs that explicitly contain a person ID token."""
    if not artifact_id:
        return None

    artifact_tokens = tokenize(artifact_id)
    matches = [
        person
        for person in people_rows
        if set(tokenize(str(person.get("person_id", "")))).issubset(artifact_tokens)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def match_by_filename_tokens(
    manifest_row: dict[str, Any],
    people_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Conservatively match filenames to exactly one person name."""
    filename = str(manifest_row.get("filename") or manifest_row.get("relative_path") or "")
    filename_tokens = tokenize(filename)
    matched_people = []
    for person in people_rows:
        given_name = normalize_optional_text(person.get("given_name"))
        surname = normalize_optional_text(person.get("surname"))
        if not given_name or not surname:
            continue

        required_tokens = {slug_token(given_name), slug_token(surname)}
        if required_tokens.issubset(filename_tokens):
            matched_people.append(person)

    if len(matched_people) == 1:
        person = matched_people[0]
        review_notes = ["Filename tokens matched exactly one person."]
        confidence = "probable"
        if has_conservative_year_overlap(manifest_row, person):
            review_notes.append("Artifact year overlaps the person's known date range.")
        return {
            "status": "matched",
            "person": person,
            "confidence": confidence,
            "review_notes": review_notes,
        }

    if len(matched_people) > 1:
        return {
            "status": "ambiguous",
            "person": None,
            "confidence": REVIEW_CONFIDENCE,
            "review_notes": ["Ambiguous filename match; multiple people matched."],
        }

    return {
        "status": "unmatched",
        "person": None,
        "confidence": REVIEW_CONFIDENCE,
        "review_notes": ["No conservative person match found."],
    }


def has_conservative_year_overlap(manifest_row: dict[str, Any], person: dict[str, Any]) -> bool:
    """Return whether an artifact year falls inside a known person date range."""
    artifact_years = extract_years(
        " ".join(
            [
                str(manifest_row.get("filename", "")),
                str(manifest_row.get("relative_path", "")),
                str(manifest_row.get("artifact_id", "")),
            ]
        )
    )
    birth_years = extract_years(str(person.get("birth_date", "")))
    death_years = extract_years(str(person.get("death_date", "")))
    if not artifact_years or not birth_years or not death_years:
        return False

    birth_year = min(birth_years)
    death_year = max(death_years)
    has_overlap = any(birth_year <= artifact_year <= death_year for artifact_year in artifact_years)
    return has_overlap


def extract_years(value: str) -> list[int]:
    """Extract plausible four-digit years from a text value."""
    years = [int(match) for match in YEAR_PATTERN.findall(value)]
    return years


def resolve_manifest_relative_path(manifest_path: Path, relative_path: str) -> Path | None:
    """Resolve a manifest relative path without assuming a single archive root layout."""
    candidate_paths = [
        manifest_path.parent / relative_path,
        manifest_path.parent.parent / relative_path,
        Path(relative_path),
    ]
    for candidate_path in candidate_paths:
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path
    return None


def build_artifact_keys(relative_path: str | None, artifact_id: str | None) -> list[str]:
    """Build lookup keys for an artifact."""
    artifact_keys: list[str] = []
    if relative_path:
        artifact_keys.append(f"path:{normalize_path_key(relative_path)}")
    if artifact_id:
        artifact_keys.append(f"artifact:{artifact_id}")
    return artifact_keys


def find_first_keyed_match(
    artifact_keys: list[str],
    keyed_matches: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Find the first keyed mapping in precedence order."""
    for artifact_key in artifact_keys:
        if artifact_key in keyed_matches:
            return keyed_matches[artifact_key]
    return None


def choose_valid_label(*labels: object, allowed_labels: set[str]) -> str:
    """Choose the first valid label from candidates."""
    fallback = next((str(label) for label in reversed(labels) if label), DEFAULT_PRIVACY_LABEL)
    for label in labels:
        if isinstance(label, str) and label in allowed_labels:
            return label
    return fallback


def validate_label(label: object, allowed_labels: set[str], fallback: str) -> str:
    """Return a label only when it is in the allowed vocabulary."""
    if isinstance(label, str) and label in allowed_labels:
        return label
    return fallback


def normalize_notes(raw_notes: object) -> list[str]:
    """Normalize manual or sidecar notes into a list of strings."""
    if isinstance(raw_notes, list):
        return [str(note) for note in raw_notes if str(note).strip()]
    if isinstance(raw_notes, str) and raw_notes.strip():
        return [raw_notes]
    return []


def normalize_optional_text(value: object) -> str | None:
    """Normalize optional text values from JSON/YAML/CSV."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def normalize_path_key(relative_path: str) -> str:
    """Normalize path keys to POSIX-style lower-case values."""
    normalized_path = relative_path.replace("\\", "/").strip().lower()
    return normalized_path


def tokenize(value: str) -> set[str]:
    """Tokenize text for conservative filename/name comparisons."""
    tokens = {match.group(0) for match in TOKEN_PATTERN.finditer(value.lower())}
    return tokens


def slug_token(value: str) -> str:
    """Normalize one name token for matching."""
    tokens = tokenize(value)
    if not tokens:
        return ""
    token = sorted(tokens)[0]
    return token


def build_link_id(relative_path: str, person_id: str | None) -> str:
    """Build a stable link ID from artifact path and optional person ID."""
    path_slug = re.sub(r"[^a-zA-Z0-9]+", "-", relative_path.lower()).strip("-")
    person_slug = person_id or "needs-review"
    link_id = f"{path_slug}--{person_slug}"
    return link_id


def load_json_list(path: Path) -> list[dict[str, Any]]:
    """Load a JSON file that must contain a list of objects."""
    raw_data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    rows = [row for row in raw_data if isinstance(row, dict)]
    return rows


def write_json(data: list[dict[str, Any]], output_path: Path) -> None:
    """Write formatted JSON."""
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(data, output_file, indent=2)
        output_file.write("\n")


def write_linking_report(source_links: list[SourceLinkEntry], output_path: Path) -> None:
    """Write a concise Markdown source linking report."""
    method_counts = Counter(source_link.match_method for source_link in source_links)
    confidence_counts = Counter(source_link.match_confidence for source_link in source_links)
    linked_count = sum(1 for source_link in source_links if source_link.person_id)
    needs_review_count = sum(
        1 for source_link in source_links if source_link.match_confidence == REVIEW_CONFIDENCE
    )

    lines = [
        "# Source/Media Linking Report",
        "",
        f"Total artifacts reviewed: {len(source_links)}",
        f"Linked artifacts: {linked_count}",
        f"Needs review: {needs_review_count}",
        "",
        "## Match Methods",
        "",
        *format_counter_lines(method_counts),
        "",
        "## Match Confidence",
        "",
        *format_counter_lines(confidence_counts),
        "",
        "## Safety Notes",
        "",
        "- This linking run used local files only.",
        "- Manual mappings take precedence over inferred matches.",
        "- Weak or ambiguous matches remain in `needs_review`.",
        "- Privacy and source confidence labels are preserved for later export/redaction logic.",
        "",
    ]
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))


def format_counter_lines(counter: Counter[str]) -> list[str]:
    """Format counter values as Markdown bullet lines."""
    if not counter:
        return ["- None"]
    return [f"- `{name}`: {count}" for name, count in sorted(counter.items())]
