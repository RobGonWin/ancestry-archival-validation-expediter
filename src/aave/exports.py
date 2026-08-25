"""Public/private metadata export bundle generation."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aave.models import ExportResult

PUBLIC_PROFILE = "public_redacted"
PRIVATE_PROFILE = "private_full"
EXPERT_PROFILE = "expert_review_packet"
EXPORT_PROFILES = {PUBLIC_PROFILE, PRIVATE_PROFILE, EXPERT_PROFILE}

RAW_DNA_PRIVACY_LABEL = "raw_dna_never_export"
DO_NOT_SHARE_PRIVACY_LABEL = "do_not_share"
LIVING_REDACTED_PRIVACY_LABEL = "living_person_redacted"

PUBLIC_ALLOWED_PRIVACY_LABELS = {"public_ok", "public_summary_only"}
EXPERT_ALLOWED_PRIVACY_LABELS = {"public_ok", "public_summary_only", "expert_review_only"}

EXPORT_FIELD_NAMES = [
    "relative_path",
    "artifact_id",
    "person_id",
    "gedcom_id",
    "display_name",
    "privacy_label",
    "source_confidence",
    "export_profile",
    "export_decision",
    "exclusion_reasons",
]


@dataclass(frozen=True)
class ExportDecision:
    """Decision for one artifact in one export profile."""

    should_export: bool
    reasons: list[str]


def export_bundle(
    profile: str,
    output_directory: Path,
    manifest_path: Path | None = None,
    people_path: Path | None = None,
    links_path: Path | None = None,
    is_dry_run: bool = False,
) -> ExportResult:
    """Build a metadata-only export bundle for a configured profile."""
    if profile not in EXPORT_PROFILES:
        valid_profiles = ", ".join(sorted(EXPORT_PROFILES))
        raise ValueError(f"Unknown export profile `{profile}`. Expected one of: {valid_profiles}")

    input_directory = output_directory.parent
    resolved_manifest_path = manifest_path or input_directory / "archive_manifest.json"
    resolved_people_path = people_path or input_directory / "people_index.json"
    resolved_links_path = links_path or input_directory / "source_links.json"

    manifest_rows = load_json_list(resolved_manifest_path)
    people_rows = load_optional_json_list(resolved_people_path)
    link_rows = load_optional_json_list(resolved_links_path)

    people_by_person_id = {str(person.get("person_id")): person for person in people_rows}
    links_by_path = {str(link.get("relative_path")): link for link in link_rows}

    export_rows = []
    excluded_count = 0
    for manifest_row in manifest_rows:
        source_link = links_by_path.get(str(manifest_row.get("relative_path", "")), {})
        person = people_by_person_id.get(str(source_link.get("person_id")), {})
        decision = decide_export(profile, manifest_row, source_link, person)
        if decision.should_export:
            export_rows.append(
                build_export_row(profile, manifest_row, source_link, person, decision)
            )
        else:
            excluded_count += 1

    output_directory.mkdir(parents=True, exist_ok=True)
    write_json(export_rows, output_directory / "export_manifest.json")
    write_csv(export_rows, output_directory / "export_manifest.csv")
    write_export_readme(
        profile=profile,
        export_rows=export_rows,
        excluded_count=excluded_count,
        output_path=output_directory / "README_EXPORT.md",
        is_dry_run=is_dry_run,
    )

    export_result = ExportResult(
        profile=profile,
        exported_count=len(export_rows),
        excluded_count=excluded_count,
        output_directory=output_directory,
        is_dry_run=is_dry_run,
    )
    return export_result


def decide_export(
    profile: str,
    manifest_row: dict[str, Any],
    source_link: dict[str, Any],
    person: dict[str, Any],
) -> ExportDecision:
    """Decide whether an artifact belongs in the selected export profile."""
    privacy_label = get_effective_privacy_label(manifest_row, source_link)
    reasons = []

    if privacy_label == RAW_DNA_PRIVACY_LABEL or is_raw_dna_artifact(manifest_row):
        return ExportDecision(False, ["Raw DNA artifacts are excluded by default."])

    if privacy_label == DO_NOT_SHARE_PRIVACY_LABEL:
        return ExportDecision(False, ["Artifact is labeled do_not_share."])

    if profile == PUBLIC_PROFILE:
        if privacy_label not in PUBLIC_ALLOWED_PRIVACY_LABELS:
            reasons.append(
                "Public exports include only public_ok or public_summary_only artifacts."
            )
        if person.get("is_potentially_living") is True:
            reasons.append("Linked person is living or potentially living.")
        if privacy_label == LIVING_REDACTED_PRIVACY_LABEL:
            reasons.append("Artifact is labeled living_person_redacted.")
        return ExportDecision(not reasons, reasons)

    if profile == EXPERT_PROFILE:
        if privacy_label not in EXPERT_ALLOWED_PRIVACY_LABELS:
            reasons.append("Expert review exports include public and expert_review_only artifacts.")
        return ExportDecision(not reasons, reasons)

    if profile == PRIVATE_PROFILE:
        return ExportDecision(True, [])

    return ExportDecision(False, ["Unknown export profile."])


def build_export_row(
    profile: str,
    manifest_row: dict[str, Any],
    source_link: dict[str, Any],
    person: dict[str, Any],
    decision: ExportDecision,
) -> dict[str, Any]:
    """Build a stable export manifest row."""
    row = {
        "relative_path": manifest_row.get("relative_path"),
        "artifact_id": manifest_row.get("artifact_id"),
        "person_id": source_link.get("person_id"),
        "gedcom_id": source_link.get("gedcom_id") or person.get("gedcom_id"),
        "display_name": get_export_display_name(profile, person),
        "privacy_label": get_effective_privacy_label(manifest_row, source_link),
        "source_confidence": source_link.get("source_confidence")
        or manifest_row.get("source_confidence"),
        "export_profile": profile,
        "export_decision": "included",
        "exclusion_reasons": "; ".join(decision.reasons),
    }
    return row


def get_export_display_name(profile: str, person: dict[str, Any]) -> str | None:
    """Return display name when profile permits person metadata."""
    if not person:
        return None
    if profile == PUBLIC_PROFILE and person.get("is_potentially_living") is True:
        return None
    display_name = person.get("display_name")
    return str(display_name) if display_name else None


def get_effective_privacy_label(
    manifest_row: dict[str, Any],
    source_link: dict[str, Any],
) -> str:
    """Prefer link-level privacy labels over manifest-level labels."""
    privacy_label = source_link.get("privacy_label") or manifest_row.get("privacy_label")
    return str(privacy_label or "private_family_only")


def is_raw_dna_artifact(manifest_row: dict[str, Any]) -> bool:
    """Detect obvious raw DNA artifacts by label, path, or filename."""
    text = " ".join(
        [
            str(manifest_row.get("relative_path", "")),
            str(manifest_row.get("filename", "")),
            str(manifest_row.get("artifact_id", "")),
        ]
    ).lower()
    raw_dna_terms = {"raw_dna", "raw-dna", "ancestrydna", "genotype", "genotypes"}
    has_raw_dna_term = any(term in text for term in raw_dna_terms)
    return has_raw_dna_term


def load_json_list(path: Path) -> list[dict[str, Any]]:
    """Load a required JSON list of objects."""
    raw_data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    rows = [row for row in raw_data if isinstance(row, dict)]
    return rows


def load_optional_json_list(path: Path) -> list[dict[str, Any]]:
    """Load an optional JSON list of objects."""
    if not path.exists():
        return []
    rows = load_json_list(path)
    return rows


def write_json(data: list[dict[str, Any]], output_path: Path) -> None:
    """Write formatted JSON."""
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(data, output_file, indent=2)
        output_file.write("\n")


def write_csv(data: list[dict[str, Any]], output_path: Path) -> None:
    """Write export rows as CSV."""
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=EXPORT_FIELD_NAMES)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def write_export_readme(
    profile: str,
    export_rows: list[dict[str, Any]],
    excluded_count: int,
    output_path: Path,
    is_dry_run: bool,
) -> None:
    """Write export bundle guidance and warnings."""
    title = get_profile_title(profile)
    lines = [
        f"# {title}",
        "",
        f"Profile: `{profile}`",
        f"Dry run: `{str(is_dry_run).lower()}`",
        f"Exported metadata rows: {len(export_rows)}",
        f"Excluded metadata rows: {excluded_count}",
        "",
        "## Contents",
        "",
        "- `export_manifest.json`",
        "- `export_manifest.csv`",
        "",
        "## Safety Notes",
        "",
        "- This export contains metadata only; source files are not copied in v0.4.",
        "- Raw DNA artifacts are excluded by default.",
        "- Review all output before sharing outside a private research context.",
    ]
    if profile == PUBLIC_PROFILE:
        lines.extend(
            [
                "- Public exports exclude living or potentially living linked people.",
                "- Public exports include only `public_ok` and `public_summary_only` artifacts.",
                "- Private notes are not exported.",
            ]
        )
    if profile == EXPERT_PROFILE:
        lines.extend(
            [
                "",
                "## Expert Review Warning",
                "",
                "This packet may include sensitive `expert_review_only` metadata.",
                "Do not publish or redistribute it without explicit human review.",
            ]
        )

    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))
        output_file.write("\n")


def get_profile_title(profile: str) -> str:
    """Return a human-readable export title."""
    titles = {
        PUBLIC_PROFILE: "Public Redacted Export",
        PRIVATE_PROFILE: "Private Full Export",
        EXPERT_PROFILE: "Expert Review Packet",
    }
    return titles[profile]
