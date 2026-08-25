from __future__ import annotations

import json
from pathlib import Path

from aave.cli import main
from aave.exports import export_bundle


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_export_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    pipeline_out = tmp_path / "out"
    manifest_path = pipeline_out / "archive_manifest.json"
    people_path = pipeline_out / "people_index.json"
    links_path = pipeline_out / "source_links.json"

    write_json(
        manifest_path,
        [
            build_manifest_row("public/doc.jpg", "public_ok", "DOC-001"),
            build_manifest_row("living/doc.jpg", "public_ok", "DOC-002"),
            build_manifest_row("sensitive/raw-dna-export.txt", "raw_dna_never_export", "DNA-001"),
            build_manifest_row("private/note.md", "do_not_share", "NOTE-001"),
            build_manifest_row("expert/review.pdf", "expert_review_only", "EXP-001"),
            build_manifest_row("private/full.pdf", "private_family_only", "PRIV-001"),
        ],
    )
    write_json(
        people_path,
        [
            build_person_row("john-smith-i1", "I1", "John Smith", False),
            build_person_row("living-person-i2", "I2", "Living Person", True),
        ],
    )
    write_json(
        links_path,
        [
            build_link_row("public/doc.jpg", "john-smith-i1", "I1", "public_ok"),
            build_link_row("living/doc.jpg", "living-person-i2", "I2", "public_ok"),
            build_link_row("sensitive/raw-dna-export.txt", "john-smith-i1", "I1", "raw_dna_never_export"),
            build_link_row("private/note.md", "john-smith-i1", "I1", "do_not_share"),
            build_link_row("expert/review.pdf", "john-smith-i1", "I1", "expert_review_only"),
            build_link_row("private/full.pdf", "john-smith-i1", "I1", "private_family_only"),
        ],
    )
    return manifest_path, people_path, links_path, pipeline_out


def build_manifest_row(
    relative_path: str,
    privacy_label: str,
    artifact_id: str,
) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "filename": Path(relative_path).name,
        "extension": Path(relative_path).suffix,
        "file_category": "document",
        "mime_guess": "application/octet-stream",
        "size_bytes": 1,
        "sha256": "abc",
        "modified_time_iso": "2026-06-19T00:00:00+00:00",
        "artifact_id": artifact_id,
        "privacy_label": privacy_label,
        "source_confidence": "needs_review",
    }


def build_person_row(
    person_id: str,
    gedcom_id: str,
    display_name: str,
    is_potentially_living: bool,
) -> dict[str, object]:
    return {
        "person_id": person_id,
        "gedcom_id": gedcom_id,
        "display_name": display_name,
        "given_name": display_name.split()[0],
        "surname": display_name.split()[-1],
        "birth_date": "1900",
        "birth_place": None,
        "death_date": None if is_potentially_living else "1980",
        "death_place": None,
        "gender_or_sex": None,
        "family_links": {},
        "source_refs": [],
        "privacy_label": "private_family_only",
        "notes": ["Private note should not appear in export rows."],
        "is_potentially_living": is_potentially_living,
    }


def build_link_row(
    relative_path: str,
    person_id: str,
    gedcom_id: str,
    privacy_label: str,
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
        "source_confidence": "confirmed",
        "review_notes": [],
    }


def load_export_rows(output_directory: Path) -> list[dict[str, object]]:
    return json.loads((output_directory / "export_manifest.json").read_text())


def test_public_export_excludes_living_raw_dna_and_do_not_share(tmp_path: Path) -> None:
    manifest_path, people_path, links_path, _pipeline_out = build_export_fixture(tmp_path)
    output_directory = tmp_path / "out" / "public_export"

    export_result = export_bundle(
        profile="public_redacted",
        output_directory=output_directory,
        manifest_path=manifest_path,
        people_path=people_path,
        links_path=links_path,
    )

    rows = load_export_rows(output_directory)
    exported_paths = {row["relative_path"] for row in rows}

    assert export_result.exported_count == 1
    assert exported_paths == {"public/doc.jpg"}
    assert "living/doc.jpg" not in exported_paths
    assert "sensitive/raw-dna-export.txt" not in exported_paths
    assert "private/note.md" not in exported_paths
    assert "notes" not in rows[0]


def test_expert_export_includes_expert_review_warning(tmp_path: Path) -> None:
    manifest_path, people_path, links_path, _pipeline_out = build_export_fixture(tmp_path)
    output_directory = tmp_path / "out" / "expert_review"

    export_bundle(
        profile="expert_review_packet",
        output_directory=output_directory,
        manifest_path=manifest_path,
        people_path=people_path,
        links_path=links_path,
    )

    rows = load_export_rows(output_directory)
    exported_paths = {row["relative_path"] for row in rows}
    readme = (output_directory / "README_EXPORT.md").read_text()

    assert "expert/review.pdf" in exported_paths
    assert "Expert Review Warning" in readme
    assert "Do not publish or redistribute" in readme


def test_private_full_excludes_raw_dna_by_default(tmp_path: Path) -> None:
    manifest_path, people_path, links_path, _pipeline_out = build_export_fixture(tmp_path)
    output_directory = tmp_path / "out" / "private_export"

    export_bundle(
        profile="private_full",
        output_directory=output_directory,
        manifest_path=manifest_path,
        people_path=people_path,
        links_path=links_path,
    )

    rows = load_export_rows(output_directory)
    exported_paths = {row["relative_path"] for row in rows}

    assert "private/full.pdf" in exported_paths
    assert "expert/review.pdf" in exported_paths
    assert "sensitive/raw-dna-export.txt" not in exported_paths


def test_export_defaults_to_parent_of_output_directory(tmp_path: Path) -> None:
    _manifest_path, _people_path, _links_path, pipeline_out = build_export_fixture(tmp_path)
    output_directory = pipeline_out / "public_export"

    export_bundle(profile="public_redacted", output_directory=output_directory)

    assert (output_directory / "export_manifest.json").exists()
    assert (output_directory / "export_manifest.csv").exists()
    assert (output_directory / "README_EXPORT.md").exists()


def test_cli_export_command_writes_outputs(tmp_path: Path) -> None:
    manifest_path, people_path, links_path, _pipeline_out = build_export_fixture(tmp_path)
    output_directory = tmp_path / "out" / "public_export"

    exit_code = main(
        [
            "export",
            "--profile",
            "public_redacted",
            "--manifest",
            str(manifest_path),
            "--people",
            str(people_path),
            "--links",
            str(links_path),
            "--out",
            str(output_directory),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert (output_directory / "export_manifest.json").exists()
    assert "`true`" in (output_directory / "README_EXPORT.md").read_text()
