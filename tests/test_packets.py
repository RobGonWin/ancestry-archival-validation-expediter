from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from aave.cli import main
from aave.packets import generate_packet


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_packet_fixture(tmp_path: Path) -> Path:
    pipeline_out = tmp_path / "out"
    write_json(
        pipeline_out / "people_index.json",
        [
            build_person("john-smith-i1", "I1", "John Smith", False, ["Private note"]),
            build_person("jane-smith-i2", "I2", "Jane Smith", False, []),
            build_person("living-child-i3", "I3", "Living Child", True, ["Sensitive note"]),
        ],
    )
    write_json(
        pipeline_out / "families_index.json",
        [
            {
                "family_id": "family-f1",
                "gedcom_id": "F1",
                "husband_id": "I1",
                "wife_id": "I2",
                "spouse_ids": ["I1", "I2"],
                "child_ids": ["I3"],
                "marriage_date": "14 FEB 1925",
                "marriage_place": "Example City",
                "source_refs": [],
                "notes": [],
            }
        ],
    )
    manifest_rows = [
        build_manifest("public/photo.jpg", "PUBLIC-001", "public_ok"),
        build_manifest("private/letter.md", "PRIVATE-001", "private_family_only"),
        build_manifest("expert/review.pdf", "EXPERT-001", "expert_review_only"),
        build_manifest("private/do-not-share.txt", "DNS-001", "do_not_share"),
        build_manifest("sensitive/raw-dna-export.txt", "DNA-001", "raw_dna_never_export"),
    ]
    write_json(pipeline_out / "archive_manifest.json", manifest_rows)
    write_json(
        pipeline_out / "source_links.json",
        [
            build_link("public/photo.jpg", "john-smith-i1", "I1", "public_ok", "family_identified"),
            build_link(
                "private/letter.md",
                "john-smith-i1",
                "I1",
                "private_family_only",
                "private_artifact",
            ),
            build_link(
                "expert/review.pdf",
                "john-smith-i1",
                "I1",
                "expert_review_only",
                "needs_review",
            ),
            build_link(
                "private/do-not-share.txt",
                "john-smith-i1",
                "I1",
                "do_not_share",
                "personal_recollection",
            ),
            build_link(
                "sensitive/raw-dna-export.txt",
                "john-smith-i1",
                "I1",
                "raw_dna_never_export",
                "private_artifact",
            ),
        ],
    )
    write_json(
        pipeline_out / "config.json",
        {
            "packet_default_profile": "private_full",
            "packet_citation_note": "Synthetic citation note for packet tests.",
        },
    )
    return pipeline_out


def build_person(
    person_id: str,
    gedcom_id: str,
    display_name: str,
    is_potentially_living: bool,
    notes: list[str],
) -> dict[str, object]:
    return {
        "person_id": person_id,
        "gedcom_id": gedcom_id,
        "display_name": display_name,
        "given_name": display_name.split()[0],
        "surname": display_name.split()[-1],
        "birth_date": "1900",
        "birth_place": "Example City",
        "death_date": None if is_potentially_living else "1980",
        "death_place": "Example City" if not is_potentially_living else None,
        "gender_or_sex": None,
        "family_links": {},
        "source_refs": [],
        "privacy_label": "private_family_only",
        "notes": notes,
        "is_potentially_living": is_potentially_living,
    }


def build_manifest(relative_path: str, artifact_id: str, privacy_label: str) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "filename": Path(relative_path).name,
        "extension": Path(relative_path).suffix,
        "file_category": "document",
        "mime_guess": "text/plain",
        "size_bytes": 1,
        "sha256": f"sha-{artifact_id}",
        "modified_time_iso": "2026-06-19T00:00:00+00:00",
        "artifact_id": artifact_id,
        "privacy_label": privacy_label,
        "source_confidence": "needs_review",
    }


def build_link(
    relative_path: str,
    person_id: str,
    gedcom_id: str,
    privacy_label: str,
    source_confidence: str,
) -> dict[str, object]:
    return {
        "link_id": f"{relative_path}--{person_id}",
        "artifact_id": None,
        "relative_path": relative_path,
        "person_id": person_id,
        "gedcom_id": gedcom_id,
        "match_method": "manual_config",
        "match_confidence": "confirmed",
        "privacy_label": privacy_label,
        "source_confidence": source_confidence,
        "review_notes": ["Sensitive review note"],
    }


def read_sources_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def test_packet_writes_markdown_and_sources_with_required_sections(tmp_path: Path) -> None:
    pipeline_out = build_packet_fixture(tmp_path)
    packet_out = pipeline_out / "packets"

    packet_result = generate_packet("john-smith-i1", packet_out)

    markdown = packet_result.markdown_path.read_text()
    sources = read_sources_csv(packet_result.sources_csv_path)

    assert packet_result.linked_source_count == 4
    assert packet_result.markdown_path.name == "john-smith-i1.md"
    assert packet_result.sources_csv_path.name == "john-smith-i1_sources.csv"
    for section in [
        "## Summary",
        "## Identity/Facts Table",
        "## Relationship Summary",
        "## Timeline",
        "## Sources",
        "## Linked Media/Artifacts",
        "## Confidence Labels",
        "## Privacy/Share Status",
        "## Open Questions",
        "## Citation-Ready Notes",
        "## Audit Notes",
    ]:
        assert section in markdown
    assert "family-identified as" in markdown
    assert "apparent date stamp" in markdown
    assert "pending scan verification" in markdown
    assert "PDF output is not generated automatically" in markdown
    assert len(sources) == 4
    assert "sensitive/raw-dna-export.txt" not in markdown


def test_public_packet_excludes_sensitive_artifacts(tmp_path: Path) -> None:
    pipeline_out = build_packet_fixture(tmp_path)
    packet_out = pipeline_out / "packets"

    generate_packet("john-smith-i1", packet_out, profile="public_redacted")

    markdown = (packet_out / "john-smith-i1.md").read_text()
    sources = read_sources_csv(packet_out / "john-smith-i1_sources.csv")

    assert "public/photo.jpg" in markdown
    assert "private/letter.md" not in markdown
    assert "expert/review.pdf" not in markdown
    assert "private/do-not-share.txt" not in markdown
    assert "sensitive/raw-dna-export.txt" not in markdown
    assert "Private note" not in markdown
    assert "Sensitive review note" not in markdown
    assert len(sources) == 1


def test_public_packet_rejects_potentially_living_person(tmp_path: Path) -> None:
    pipeline_out = build_packet_fixture(tmp_path)

    with pytest.raises(ValueError, match="potentially living"):
        generate_packet("living-child-i3", pipeline_out / "packets", profile="public_redacted")


def test_expert_packet_includes_warning_and_expert_review_artifact(tmp_path: Path) -> None:
    pipeline_out = build_packet_fixture(tmp_path)
    packet_out = pipeline_out / "packets"

    generate_packet("john-smith-i1", packet_out, profile="expert_review_packet")

    markdown = (packet_out / "john-smith-i1.md").read_text()

    assert "Expert review packet" in markdown
    assert "expert/review.pdf" in markdown
    assert "private/letter.md" not in markdown


def test_private_packet_includes_full_non_dna_metadata(tmp_path: Path) -> None:
    pipeline_out = build_packet_fixture(tmp_path)
    packet_out = pipeline_out / "packets"

    generate_packet("john-smith-i1", packet_out, profile="private_full")

    markdown = (packet_out / "john-smith-i1.md").read_text()

    assert "private/letter.md" in markdown
    assert "private/do-not-share.txt" in markdown
    assert "expert/review.pdf" in markdown
    assert "sensitive/raw-dna-export.txt" not in markdown


def test_cli_packet_uses_default_input_discovery(tmp_path: Path) -> None:
    pipeline_out = build_packet_fixture(tmp_path)
    packet_out = pipeline_out / "packets"

    exit_code = main(["packet", "--person", "john-smith-i1", "--out", str(packet_out)])

    assert exit_code == 0
    assert (packet_out / "john-smith-i1.md").exists()
    assert (packet_out / "john-smith-i1_sources.csv").exists()
