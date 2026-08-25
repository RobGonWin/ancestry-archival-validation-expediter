"""Typed data models for archive manifest and GEDCOM index generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArchiveManifestRow:
    """One local file entry in an archive manifest."""

    relative_path: str
    filename: str
    extension: str
    file_category: str
    mime_guess: str | None
    size_bytes: int
    sha256: str
    modified_time_iso: str
    artifact_id: str | None
    privacy_label: str
    source_confidence: str


MANIFEST_FIELD_NAMES = [
    "relative_path",
    "filename",
    "extension",
    "file_category",
    "mime_guess",
    "size_bytes",
    "sha256",
    "modified_time_iso",
    "artifact_id",
    "privacy_label",
    "source_confidence",
]


@dataclass(frozen=True)
class ScanResult:
    """Summary of a completed local archive scan."""

    file_count: int
    output_directory: Path


@dataclass(frozen=True)
class LifeEvent:
    """Date and place details for a GEDCOM life event."""

    date: str | None = None
    place: str | None = None


@dataclass(frozen=True)
class FamilyLinks:
    """Explicit family links preserved from GEDCOM records."""

    famc: list[str]
    fams: list[str]
    parent_family_ids: list[str]
    spouse_family_ids: list[str]
    parent_ids: list[str]
    spouse_ids: list[str]
    child_ids: list[str]


@dataclass(frozen=True)
class PersonIndexEntry:
    """One person entry derived from an INDI GEDCOM record."""

    person_id: str
    gedcom_id: str
    display_name: str
    given_name: str | None
    surname: str | None
    birth_date: str | None
    birth_place: str | None
    death_date: str | None
    death_place: str | None
    gender_or_sex: str | None
    family_links: FamilyLinks
    source_refs: list[str]
    privacy_label: str
    notes: list[str]
    is_potentially_living: bool


@dataclass(frozen=True)
class FamilyIndexEntry:
    """One family entry derived from a FAM GEDCOM record."""

    family_id: str
    gedcom_id: str
    husband_id: str | None
    wife_id: str | None
    spouse_ids: list[str]
    child_ids: list[str]
    marriage_date: str | None
    marriage_place: str | None
    source_refs: list[str]
    notes: list[str]


@dataclass(frozen=True)
class GedcomParseResult:
    """Summary of a completed GEDCOM parse."""

    person_count: int
    family_count: int
    output_directory: Path


@dataclass(frozen=True)
class SourceLinkEntry:
    """One conservative source/media link decision for a scanned artifact."""

    link_id: str
    artifact_id: str | None
    relative_path: str
    person_id: str | None
    gedcom_id: str | None
    match_method: str
    match_confidence: str
    privacy_label: str
    source_confidence: str
    review_notes: list[str]


@dataclass(frozen=True)
class LinkingResult:
    """Summary of a completed source/media linking run."""

    link_count: int
    linked_count: int
    needs_review_count: int
    output_directory: Path


@dataclass(frozen=True)
class ExportResult:
    """Summary of a completed export bundle build."""

    profile: str
    exported_count: int
    excluded_count: int
    output_directory: Path
    is_dry_run: bool


@dataclass(frozen=True)
class ArchiveFormatMetadata:
    """Lightweight metadata for a saved local archive/reference file."""

    relative_path: str
    artifact_id: str | None
    file_type: str
    size_bytes: int
    sha256: str
    html_title: str | None
    probable_source_url: str | None
    pdf_page_count: int | None
    package_format: str | None
    inspection_notes: list[str]


@dataclass(frozen=True)
class ArchiveInspectionResult:
    """Summary of a completed archive format inspection."""

    inspected_count: int
    output_directory: Path


@dataclass(frozen=True)
class PacketResult:
    """Summary of a completed research packet build."""

    person_id: str
    profile: str
    markdown_path: Path
    sources_csv_path: Path
    linked_source_count: int


@dataclass(frozen=True)
class ZipMemberEntry:
    """One local ZIP member metadata row with optional person context."""

    zip_path: str
    member_path: str
    filename: str
    extension: str
    file_category: str
    size_bytes: int
    compressed_size_bytes: int
    sha256: str
    crc32: str
    person_id: str | None
    gedcom_id: str | None
    family_context: str | None
    privacy_label: str
    source_confidence: str
    review_notes: list[str]


@dataclass(frozen=True)
class ZipInspectionResult:
    """Summary of a completed ZIP member inspection."""

    member_count: int
    linked_member_count: int
    output_directory: Path


@dataclass(frozen=True)
class SnpWhitelistEntry:
    """One curated SNP whitelist entry for private local genome checks."""

    rsid: str
    gene: str | None
    label: str | None
    category: str | None
    source_url: str | None
    evidence_note: str | None
    limitations: str | None
    public_summary_allowed: bool


@dataclass(frozen=True)
class AncestryDnaParseResult:
    """Summary of a completed local AncestryDNA whitelist parse."""

    rows_read: int
    malformed_row_count: int
    duplicate_rsid_count: int
    hit_count: int
    missing_count: int
    output_directory: Path


@dataclass(frozen=True)
class SnpCrossrefResult:
    """Summary of a completed local SNP cross-reference annotation run."""

    hit_count: int
    annotated_count: int
    output_directory: Path


@dataclass(frozen=True)
class PrivacyAuditResult:
    """Summary of a local repository privacy preflight audit."""

    tracked_path_count: int
    flagged_path_count: int
    publish_ready: bool
    output_directory: Path


@dataclass(frozen=True)
class IdentityAssertionResult:
    """Summary of a redaction-safe identity assertion build."""

    assertion_id: str
    profile: str
    output_directory: Path
    public_summary_path: Path
    private_assertion_path: Path


@dataclass(frozen=True)
class BranchPolicyAuditResult:
    """Summary of a branch-specific publication policy audit."""

    mode: str
    tracked_path_count: int
    finding_count: int
    required_rule_count: int
    policy_ready: bool
    output_directory: Path
