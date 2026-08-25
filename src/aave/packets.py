"""Markdown research packet generation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from aave.config import AaveConfig, load_config
from aave.exports import (
    EXPERT_ALLOWED_PRIVACY_LABELS,
    EXPERT_PROFILE,
    EXPORT_PROFILES,
    PRIVATE_PROFILE,
    PUBLIC_ALLOWED_PRIVACY_LABELS,
    PUBLIC_PROFILE,
    RAW_DNA_PRIVACY_LABEL,
    get_effective_privacy_label,
    is_raw_dna_artifact,
)
from aave.models import PacketResult

SOURCE_CSV_FIELDS = [
    "relative_path",
    "artifact_id",
    "file_category",
    "privacy_label",
    "source_confidence",
    "match_method",
    "match_confidence",
    "citation_note",
]


def generate_packet(
    person_id: str,
    output_directory: Path,
    profile: str = PRIVATE_PROFILE,
    people_path: Path | None = None,
    families_path: Path | None = None,
    manifest_path: Path | None = None,
    links_path: Path | None = None,
    config_path: Path | None = None,
) -> PacketResult:
    """Generate a Markdown research packet and source CSV for one person."""
    if profile not in EXPORT_PROFILES:
        valid_profiles = ", ".join(sorted(EXPORT_PROFILES))
        raise ValueError(f"Unknown packet profile `{profile}`. Expected one of: {valid_profiles}")

    input_directory = output_directory.parent
    resolved_people_path = people_path or input_directory / "people_index.json"
    resolved_families_path = families_path or input_directory / "families_index.json"
    resolved_manifest_path = manifest_path or input_directory / "archive_manifest.json"
    resolved_links_path = links_path or input_directory / "source_links.json"
    resolved_config_path = config_path or input_directory / "config.json"

    config = load_optional_config(resolved_config_path)
    people = load_json_list(resolved_people_path)
    families = load_optional_json_list(resolved_families_path)
    manifest_rows = load_optional_json_list(resolved_manifest_path)
    source_links = load_optional_json_list(resolved_links_path)

    people_by_id = {
        str(person["person_id"]): person for person in people if person.get("person_id")
    }
    person = people_by_id.get(person_id)
    if person is None:
        raise ValueError(f"Person `{person_id}` was not found in {resolved_people_path}")
    if profile == PUBLIC_PROFILE and person.get("is_potentially_living") is True:
        raise ValueError(
            "Public packets cannot be generated for living or potentially living people."
        )

    manifest_by_path = {
        str(manifest_row.get("relative_path")): manifest_row for manifest_row in manifest_rows
    }
    linked_artifacts = select_linked_artifacts(
        person=person,
        profile=profile,
        source_links=source_links,
        manifest_by_path=manifest_by_path,
    )

    output_directory.mkdir(parents=True, exist_ok=True)
    markdown_path = output_directory / f"{person_id}.md"
    sources_csv_path = output_directory / f"{person_id}_sources.csv"

    markdown_text = build_packet_markdown(
        person=person,
        profile=profile,
        people_by_id=people_by_id,
        families=families,
        linked_artifacts=linked_artifacts,
        config=config,
    )
    markdown_path.write_text(markdown_text, encoding="utf-8", newline="\n")
    write_sources_csv(linked_artifacts, sources_csv_path, config.packet_citation_note)

    packet_result = PacketResult(
        person_id=person_id,
        profile=profile,
        markdown_path=markdown_path,
        sources_csv_path=sources_csv_path,
        linked_source_count=len(linked_artifacts),
    )
    return packet_result


def select_linked_artifacts(
    person: dict[str, Any],
    profile: str,
    source_links: list[dict[str, Any]],
    manifest_by_path: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Select linked artifacts visible under the packet profile."""
    person_id = str(person.get("person_id"))
    selected_artifacts = []
    for source_link in source_links:
        if source_link.get("person_id") != person_id:
            continue
        manifest_row = manifest_by_path.get(str(source_link.get("relative_path")), {})
        if should_include_linked_artifact(profile, source_link, manifest_row):
            selected_artifacts.append(
                {
                    "source_link": source_link,
                    "manifest_row": manifest_row,
                }
            )

    selected_artifacts = sorted(
        selected_artifacts,
        key=lambda row: str(row["source_link"].get("relative_path", "")),
    )
    return selected_artifacts


def should_include_linked_artifact(
    profile: str,
    source_link: dict[str, Any],
    manifest_row: dict[str, Any],
) -> bool:
    """Return whether a linked artifact can appear in a packet profile."""
    privacy_label = get_effective_privacy_label(manifest_row, source_link)
    if privacy_label == RAW_DNA_PRIVACY_LABEL or is_raw_dna_artifact(manifest_row):
        return False
    if profile == PUBLIC_PROFILE:
        return privacy_label in PUBLIC_ALLOWED_PRIVACY_LABELS
    if profile == EXPERT_PROFILE:
        return privacy_label in EXPERT_ALLOWED_PRIVACY_LABELS
    if profile == PRIVATE_PROFILE:
        return True
    return False


def build_packet_markdown(
    person: dict[str, Any],
    profile: str,
    people_by_id: dict[str, dict[str, Any]],
    families: list[dict[str, Any]],
    linked_artifacts: list[dict[str, dict[str, Any]]],
    config: AaveConfig,
) -> str:
    """Build Markdown packet text."""
    display_name = get_display_name(person, profile)
    lines = [
        f"# Research Packet: {display_name}",
        "",
        "## Summary",
        "",
        build_summary(person, profile),
        "",
    ]
    if profile == EXPERT_PROFILE:
        lines.extend(
            [
                "> Expert review packet: do not publish or redistribute "
                "without explicit human review.",
                "",
            ]
        )

    lines.extend(build_identity_section(person, profile))
    lines.extend(build_relationship_section(person, people_by_id, families))
    lines.extend(build_timeline_section(person, families))
    lines.extend(build_sources_section(linked_artifacts))
    lines.extend(build_media_section(linked_artifacts))
    lines.extend(build_confidence_section(person, linked_artifacts))
    lines.extend(build_privacy_section(person, profile, linked_artifacts))
    lines.extend(build_open_questions_section(person, linked_artifacts, profile))
    lines.extend(build_citation_section(linked_artifacts, config.packet_citation_note))
    lines.extend(build_audit_section(profile))

    markdown_text = "\n".join(lines).rstrip() + "\n"
    return markdown_text


def build_summary(person: dict[str, Any], profile: str) -> str:
    """Build a conservative one-paragraph person summary."""
    display_name = get_display_name(person, profile)
    birth = format_fact(person.get("birth_date"), person.get("birth_place"))
    death = format_fact(person.get("death_date"), person.get("death_place"))
    living_note = (
        " Potentially living details are redacted."
        if is_public_redacted(person, profile)
        else ""
    )
    summary = (
        f"This packet summarizes locally supplied records for {display_name}. "
        f"Identity details are family-identified as supplied in the local person index. "
        f"Birth: {birth}. Death: {death}.{living_note}"
    )
    return summary


def build_identity_section(person: dict[str, Any], profile: str) -> list[str]:
    """Build identity and facts table."""
    display_name = get_display_name(person, profile)
    notes_value = (
        "Redacted for public profile."
        if profile == PUBLIC_PROFILE
        else "; ".join(person.get("notes", []))
    )
    lines = [
        "## Identity/Facts Table",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Person ID | `{person.get('person_id', '')}` |",
        f"| GEDCOM ID | `{person.get('gedcom_id', '')}` |",
        f"| Display name | {display_name} |",
        f"| Given name | {redact_if_public(person.get('given_name'), profile, person)} |",
        f"| Surname | {redact_if_public(person.get('surname'), profile, person)} |",
        f"| Birth | {format_fact(person.get('birth_date'), person.get('birth_place'))} |",
        f"| Death | {format_fact(person.get('death_date'), person.get('death_place'))} |",
        f"| Potentially living | `{str(person.get('is_potentially_living', False)).lower()}` |",
        f"| Notes | {notes_value or 'None'} |",
        "",
    ]
    return lines


def build_relationship_section(
    person: dict[str, Any],
    people_by_id: dict[str, dict[str, Any]],
    families: list[dict[str, Any]],
) -> list[str]:
    """Build explicit GEDCOM relationship summary."""
    person_id = str(person.get("gedcom_id") or person.get("person_id"))
    related_lines = []
    for family in families:
        spouse_ids = [str(value) for value in family.get("spouse_ids", [])]
        child_ids = [str(value) for value in family.get("child_ids", [])]
        if person_id in spouse_ids:
            child_summary = ", ".join(child_ids) or "None"
            related_lines.append(
                f"- Spouse family `{family.get('gedcom_id')}` "
                f"with children: {child_summary}."
            )
        if person_id in child_ids:
            spouse_summary = ", ".join(spouse_ids) or "None"
            related_lines.append(
                f"- Child in family `{family.get('gedcom_id')}` "
                f"with parents/spouses: {spouse_summary}."
            )

    if not related_lines:
        related_lines = ["- No explicit family links were found in the supplied family index."]

    lines = [
        "## Relationship Summary",
        "",
        "Relationships are listed only when represented by local GEDCOM family links.",
        "",
        *related_lines,
        "",
    ]
    return lines


def build_timeline_section(person: dict[str, Any], families: list[dict[str, Any]]) -> list[str]:
    """Build a simple timeline from person and family facts."""
    timeline_rows = [
        ("Birth", format_fact(person.get("birth_date"), person.get("birth_place"))),
        ("Death", format_fact(person.get("death_date"), person.get("death_place"))),
    ]
    gedcom_id = person.get("gedcom_id")
    for family in families:
        if gedcom_id in family.get("spouse_ids", []):
            timeline_rows.append(
                ("Marriage", format_fact(family.get("marriage_date"), family.get("marriage_place")))
            )

    lines = ["## Timeline", "", "| Event | Details |", "| --- | --- |"]
    lines.extend(
        f"| {event} | {details} |"
        for event, details in timeline_rows
        if details != "Unknown"
    )
    if len(lines) == 4:
        lines.append("| Pending review | No dated timeline facts supplied. |")
    lines.append("")
    return lines


def build_sources_section(linked_artifacts: list[dict[str, dict[str, Any]]]) -> list[str]:
    """Build sources section."""
    lines = ["## Sources", ""]
    if not linked_artifacts:
        lines.extend(["- No linked sources are available for this packet profile.", ""])
        return lines
    for artifact in linked_artifacts:
        source_link = artifact["source_link"]
        manifest_row = artifact["manifest_row"]
        lines.append(
            f"- `{source_link.get('relative_path')}` "
            f"({source_link.get('source_confidence') or manifest_row.get('source_confidence')})"
        )
    lines.append("")
    return lines


def build_media_section(linked_artifacts: list[dict[str, dict[str, Any]]]) -> list[str]:
    """Build linked media/artifacts section."""
    lines = [
        "## Linked Media/Artifacts",
        "",
        "Artifacts are family-identified as linked to this person. "
        "Any apparent date stamp remains pending scan verification.",
        "",
    ]
    if not linked_artifacts:
        lines.extend(["- No linked media or artifacts are available for this profile.", ""])
        return lines
    for artifact in linked_artifacts:
        manifest_row = artifact["manifest_row"]
        source_link = artifact["source_link"]
        lines.append(
            f"- `{source_link.get('relative_path')}` | "
            f"artifact `{manifest_row.get('artifact_id') or 'unknown'}` | "
            f"privacy `{source_link.get('privacy_label') or manifest_row.get('privacy_label')}`"
        )
    lines.append("")
    return lines


def build_confidence_section(
    person: dict[str, Any],
    linked_artifacts: list[dict[str, dict[str, Any]]],
) -> list[str]:
    """Build confidence labels section."""
    labels = sorted({get_artifact_source_confidence(artifact) for artifact in linked_artifacts})
    label_summary = ", ".join(f"`{label}`" for label in labels if label) or "`none`"
    lines = [
        "## Confidence Labels",
        "",
        f"- Person privacy label: `{person.get('privacy_label', 'private_family_only')}`",
        f"- Source confidence labels in packet: {label_summary}",
        "- Labels are preserved from local metadata and are not upgraded automatically.",
        "",
    ]
    return lines


def build_privacy_section(
    person: dict[str, Any],
    profile: str,
    linked_artifacts: list[dict[str, dict[str, Any]]],
) -> list[str]:
    """Build privacy and share status section."""
    artifact_labels = sorted(
        {get_artifact_privacy_label(artifact) for artifact in linked_artifacts}
    )
    label_summary = ", ".join(f"`{label}`" for label in artifact_labels if label) or "`none`"
    lines = [
        "## Privacy/Share Status",
        "",
        f"- Packet profile: `{profile}`",
        f"- Potentially living: `{str(person.get('is_potentially_living', False)).lower()}`",
        f"- Artifact privacy labels in packet: {label_summary}",
        "- Review this packet before sharing outside the intended privacy context.",
        "",
    ]
    return lines


def build_open_questions_section(
    person: dict[str, Any],
    linked_artifacts: list[dict[str, dict[str, Any]]],
    profile: str,
) -> list[str]:
    """Build open questions section."""
    questions = []
    if not linked_artifacts:
        questions.append("Confirm whether additional source artifacts should be linked.")
    if person.get("is_potentially_living") is True:
        questions.append("Confirm living-person status before any public sharing.")
    if profile == PUBLIC_PROFILE:
        questions.append("Confirm all public facts are safe summaries and not private notes.")
    questions.append("Verify apparent date stamp details against source scans.")
    questions.append("Resolve any pending scan verification items before citation use.")
    lines = ["## Open Questions", "", *[f"- {question}" for question in questions], ""]
    return lines


def build_citation_section(
    linked_artifacts: list[dict[str, dict[str, Any]]],
    citation_note: str,
) -> list[str]:
    """Build citation-ready notes section."""
    lines = ["## Citation-Ready Notes", "", citation_note, ""]
    if not linked_artifacts:
        lines.extend(["- No citation candidates are available for this profile.", ""])
        return lines
    for artifact in linked_artifacts:
        source_link = artifact["source_link"]
        manifest_row = artifact["manifest_row"]
        lines.append(
            f"- `{source_link.get('relative_path')}`: "
            f"family-identified as source/media; apparent date stamp pending scan verification; "
            f"SHA-256 `{manifest_row.get('sha256', '')}`."
        )
    lines.append("")
    return lines


def build_audit_section(profile: str) -> list[str]:
    """Build audit notes section."""
    lines = [
        "## Audit Notes",
        "",
        "- Generated from local AAVE JSON metadata only.",
        "- Source files are not copied into packets in v0.6.",
        "- No network calls, crawling, WARC replay, login automation, or access-control bypassing.",
        "- No medical, genetic-deterministic, institutional endorsement, or validation claims.",
        "- PDF output is not generated automatically; "
        "convert Markdown manually after review if needed.",
        f"- Profile policy applied: `{profile}`.",
        "",
    ]
    return lines


def write_sources_csv(
    linked_artifacts: list[dict[str, dict[str, Any]]],
    output_path: Path,
    citation_note: str,
) -> None:
    """Write source CSV for linked packet artifacts."""
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=SOURCE_CSV_FIELDS)
        writer.writeheader()
        for artifact in linked_artifacts:
            source_link = artifact["source_link"]
            manifest_row = artifact["manifest_row"]
            writer.writerow(
                {
                    "relative_path": source_link.get("relative_path"),
                    "artifact_id": manifest_row.get("artifact_id"),
                    "file_category": manifest_row.get("file_category"),
                    "privacy_label": source_link.get("privacy_label")
                    or manifest_row.get("privacy_label"),
                    "source_confidence": source_link.get("source_confidence")
                    or manifest_row.get("source_confidence"),
                    "match_method": source_link.get("match_method"),
                    "match_confidence": source_link.get("match_confidence"),
                    "citation_note": citation_note,
                }
            )


def load_optional_config(config_path: Path) -> AaveConfig:
    """Load config when present, otherwise return safe defaults."""
    if config_path.exists():
        return load_config(config_path)
    return AaveConfig()


def get_artifact_source_confidence(artifact: dict[str, dict[str, Any]]) -> str:
    """Return effective source confidence for a linked artifact."""
    source_link = artifact["source_link"]
    manifest_row = artifact["manifest_row"]
    source_confidence = source_link.get("source_confidence") or manifest_row.get(
        "source_confidence"
    )
    return str(source_confidence or "")


def get_artifact_privacy_label(artifact: dict[str, dict[str, Any]]) -> str:
    """Return effective privacy label for a linked artifact."""
    source_link = artifact["source_link"]
    manifest_row = artifact["manifest_row"]
    privacy_label = source_link.get("privacy_label") or manifest_row.get("privacy_label")
    return str(privacy_label or "")


def load_json_list(path: Path) -> list[dict[str, Any]]:
    """Load a required JSON list of objects."""
    raw_data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return [row for row in raw_data if isinstance(row, dict)]


def load_optional_json_list(path: Path) -> list[dict[str, Any]]:
    """Load an optional JSON list of objects."""
    if not path.exists():
        return []
    return load_json_list(path)


def format_fact(date_value: object, place_value: object) -> str:
    """Format a date/place pair for Markdown."""
    date_text = str(date_value).strip() if date_value else ""
    place_text = str(place_value).strip() if place_value else ""
    if date_text and place_text:
        return f"{date_text}, {place_text}"
    if date_text:
        return date_text
    if place_text:
        return place_text
    return "Unknown"


def get_display_name(person: dict[str, Any], profile: str) -> str:
    """Return display name, redacted when public policy requires it."""
    if is_public_redacted(person, profile):
        return "Redacted potentially living person"
    return str(person.get("display_name") or person.get("person_id") or "Unknown person")


def redact_if_public(value: object, profile: str, person: dict[str, Any]) -> str:
    """Redact a value when public policy requires living-person redaction."""
    if is_public_redacted(person, profile):
        return "Redacted"
    return str(value) if value else "Unknown"


def is_public_redacted(person: dict[str, Any], profile: str) -> bool:
    """Return whether person details should be redacted for public profile."""
    return profile == PUBLIC_PROFILE and person.get("is_potentially_living") is True
