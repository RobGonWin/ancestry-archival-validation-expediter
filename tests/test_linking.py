from __future__ import annotations

import json
from pathlib import Path

from aave.cli import main
from aave.linking import link_sources


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_manifest_row(
    relative_path: str,
    filename: str,
    artifact_id: str | None = None,
    extension: str = ".jpg",
) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "filename": filename,
        "extension": extension,
        "file_category": "image",
        "mime_guess": "image/jpeg",
        "size_bytes": 10,
        "sha256": "abc123",
        "modified_time_iso": "2026-06-19T00:00:00+00:00",
        "artifact_id": artifact_id,
        "privacy_label": "private_family_only",
        "source_confidence": "needs_review",
    }


def build_people_rows() -> list[dict[str, object]]:
    return [
        {
            "person_id": "john-smith-i1",
            "gedcom_id": "I1",
            "display_name": "John Smith",
            "given_name": "John",
            "surname": "Smith",
            "birth_date": "1900",
            "birth_place": None,
            "death_date": "1980",
            "death_place": None,
            "gender_or_sex": "M",
            "family_links": {},
            "source_refs": [],
            "privacy_label": "private_family_only",
            "notes": [],
            "is_potentially_living": False,
        },
        {
            "person_id": "jane-smith-i2",
            "gedcom_id": "I2",
            "display_name": "Jane Smith",
            "given_name": "Jane",
            "surname": "Smith",
            "birth_date": "1905",
            "birth_place": None,
            "death_date": "1990",
            "death_place": None,
            "gender_or_sex": "F",
            "family_links": {},
            "source_refs": [],
            "privacy_label": "private_family_only",
            "notes": [],
            "is_potentially_living": False,
        },
    ]


def build_link_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    manifest_path = tmp_path / "archive_manifest.json"
    people_path = tmp_path / "people_index.json"
    config_path = tmp_path / "config.json"
    output_directory = tmp_path / "out"

    manifest_rows = [
        build_manifest_row("photos/john-smith-1970.jpg", "john-smith-1970.jpg", "PHOTO-001"),
        build_manifest_row("photos/manual-john-smith.jpg", "manual-john-smith.jpg", "MANUAL-001"),
        build_manifest_row("photos/sidecar-json.jpg", "sidecar-json.jpg", "JSON-001"),
        build_manifest_row("photos/sidecar-yaml.jpg", "sidecar-yaml.jpg", "YAML-001"),
        build_manifest_row("photos/sidecar-csv.jpg", "sidecar-csv.jpg", "CSV-001"),
        build_manifest_row("photos/unknown.jpg", "unknown.jpg", "UNKNOWN-001"),
        build_manifest_row("metadata/photo.json", "photo.json", None, ".json"),
        build_manifest_row("metadata/photo.yaml", "photo.yaml", None, ".yaml"),
        build_manifest_row("metadata/photo.csv", "photo.csv", None, ".csv"),
    ]
    write_json(manifest_path, manifest_rows)
    write_json(people_path, build_people_rows())
    write_json(
        config_path,
        {
            "default_privacy_label": "private_family_only",
            "default_source_confidence": "needs_review",
            "manual_source_links": [
                {
                    "relative_path": "photos/manual-john-smith.jpg",
                    "person_id": "jane-smith-i2",
                    "source_confidence": "personal_recollection",
                    "privacy_label": "do_not_share",
                    "notes": "Manual mapping beats filename tokens.",
                }
            ],
        },
    )
    write_json(
        tmp_path / "metadata/photo.json",
        {
            "relative_path": "photos/sidecar-json.jpg",
            "person_slug": "john-smith-i1",
            "source_confidence": "family_identified",
            "privacy_label": "private_family_only",
        },
    )
    (tmp_path / "metadata/photo.yaml").write_text(
        "\n".join(
            [
                "relative_path: photos/sidecar-yaml.jpg",
                "gedcom_id: I2",
                "source_confidence: private_artifact",
                "privacy_label: expert_review_only",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "metadata/photo.csv").write_text(
        "\n".join(
            [
                "local_path,person_id,source_confidence,privacy_label",
                "photos/sidecar-csv.jpg,john-smith-i1,public_secondary,public_summary_only",
            ]
        ),
        encoding="utf-8",
    )

    return manifest_path, people_path, config_path, output_directory


def load_links(output_directory: Path) -> dict[str, dict[str, object]]:
    source_links = json.loads((output_directory / "source_links.json").read_text())
    links_by_path = {source_link["relative_path"]: source_link for source_link in source_links}
    return links_by_path


def test_link_sources_applies_manual_mapping_before_filename_match(tmp_path: Path) -> None:
    manifest_path, people_path, config_path, output_directory = build_link_fixture(tmp_path)

    link_sources(
        manifest_path=manifest_path,
        people_path=people_path,
        config_path=config_path,
        output_directory=output_directory,
    )

    links_by_path = load_links(output_directory)
    manual_link = links_by_path["photos/manual-john-smith.jpg"]

    assert manual_link["person_id"] == "jane-smith-i2"
    assert manual_link["match_method"] == "manual_config"
    assert manual_link["source_confidence"] == "personal_recollection"
    assert manual_link["privacy_label"] == "do_not_share"


def test_link_sources_uses_json_yaml_and_csv_sidecars(tmp_path: Path) -> None:
    manifest_path, people_path, config_path, output_directory = build_link_fixture(tmp_path)

    link_sources(
        manifest_path=manifest_path,
        people_path=people_path,
        config_path=config_path,
        output_directory=output_directory,
    )

    links_by_path = load_links(output_directory)

    assert links_by_path["photos/sidecar-json.jpg"]["person_id"] == "john-smith-i1"
    assert links_by_path["photos/sidecar-json.jpg"]["match_method"] == "sidecar_metadata"
    assert links_by_path["photos/sidecar-yaml.jpg"]["person_id"] == "jane-smith-i2"
    assert links_by_path["photos/sidecar-yaml.jpg"]["privacy_label"] == "expert_review_only"
    assert links_by_path["photos/sidecar-csv.jpg"]["person_id"] == "john-smith-i1"
    assert links_by_path["photos/sidecar-csv.jpg"]["source_confidence"] == "public_secondary"


def test_link_sources_uses_conservative_filename_match(tmp_path: Path) -> None:
    manifest_path, people_path, config_path, output_directory = build_link_fixture(tmp_path)

    link_sources(
        manifest_path=manifest_path,
        people_path=people_path,
        config_path=config_path,
        output_directory=output_directory,
    )

    filename_link = load_links(output_directory)["photos/john-smith-1970.jpg"]

    assert filename_link["person_id"] == "john-smith-i1"
    assert filename_link["match_method"] == "filename_tokens"
    assert filename_link["match_confidence"] == "probable"
    assert "Artifact year overlaps" in " ".join(filename_link["review_notes"])


def test_link_sources_marks_ambiguous_filename_match_for_review(tmp_path: Path) -> None:
    manifest_path = tmp_path / "archive_manifest.json"
    people_path = tmp_path / "people_index.json"
    config_path = tmp_path / "config.json"
    output_directory = tmp_path / "out"

    write_json(
        manifest_path,
        [build_manifest_row("photos/john-smith-group.jpg", "john-smith-group.jpg")],
    )
    people = build_people_rows()
    people.append({**people[0], "person_id": "john-smith-i9", "gedcom_id": "I9"})
    write_json(people_path, people)
    write_json(config_path, {})

    link_sources(
        manifest_path=manifest_path,
        people_path=people_path,
        config_path=config_path,
        output_directory=output_directory,
    )

    ambiguous_link = load_links(output_directory)["photos/john-smith-group.jpg"]

    assert ambiguous_link["person_id"] is None
    assert ambiguous_link["match_confidence"] == "needs_review"
    assert ambiguous_link["match_method"] == "needs_review"
    assert "Ambiguous filename match" in ambiguous_link["review_notes"][0]


def test_link_sources_marks_no_match_for_review(tmp_path: Path) -> None:
    manifest_path, people_path, config_path, output_directory = build_link_fixture(tmp_path)

    link_sources(
        manifest_path=manifest_path,
        people_path=people_path,
        config_path=config_path,
        output_directory=output_directory,
    )

    unknown_link = load_links(output_directory)["photos/unknown.jpg"]

    assert unknown_link["person_id"] is None
    assert unknown_link["match_confidence"] == "needs_review"
    assert unknown_link["review_notes"] == ["No conservative person match found."]


def test_cli_link_command_writes_outputs(tmp_path: Path) -> None:
    manifest_path, people_path, config_path, output_directory = build_link_fixture(tmp_path)

    exit_code = main(
        [
            "link",
            "--manifest",
            str(manifest_path),
            "--people",
            str(people_path),
            "--config",
            str(config_path),
            "--out",
            str(output_directory),
        ]
    )

    assert exit_code == 0
    assert (output_directory / "source_links.json").exists()
    assert (output_directory / "linking_report.md").exists()
