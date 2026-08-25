from __future__ import annotations

import json
import zipfile
from pathlib import Path

from aave.cli import main
from aave.zip_archives import inspect_zip_archive


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_zip_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    zip_path = tmp_path / "Synthetic Family Tree.zip"
    people_path = tmp_path / "people_index.json"
    config_path = tmp_path / "config.json"
    output_directory = tmp_path / "out"

    with zipfile.ZipFile(zip_path, "w") as package:
        package.writestr("people/john-smith/source-note.txt", "synthetic note")
        package.writestr("people/john-smith/photo.jpg", b"synthetic image")
        package.writestr("unmapped/tree.ged", "0 HEAD\n0 TRLR\n")

    write_json(
        people_path,
        [
            {
                "person_id": "john-smith-i1",
                "gedcom_id": "I1",
                "display_name": "John Smith",
            }
        ],
    )
    write_json(
        config_path,
        {
            "default_privacy_label": "private_family_only",
            "default_source_confidence": "needs_review",
            "zip_member_contexts": [
                {
                    "zip_filename": "Synthetic Family Tree.zip",
                    "member_prefix": "people/john-smith/",
                    "person_id": "john-smith-i1",
                    "family_context": "Synthetic John Smith folder",
                    "source_confidence": "family_identified",
                    "privacy_label": "private_family_only",
                    "notes": "Synthetic folder-level association.",
                }
            ],
        },
    )
    return zip_path, people_path, config_path, output_directory


def load_member_rows(output_directory: Path) -> dict[str, dict[str, object]]:
    rows = json.loads((output_directory / "zip_member_manifest.json").read_text())
    return {row["member_path"]: row for row in rows}


def test_inspect_zip_associates_members_by_subfolder_context(tmp_path: Path) -> None:
    zip_path, people_path, config_path, output_directory = build_zip_fixture(tmp_path)

    result = inspect_zip_archive(
        zip_path=zip_path,
        output_directory=output_directory,
        config_path=config_path,
        people_path=people_path,
    )

    rows = load_member_rows(output_directory)

    assert result.member_count == 3
    assert result.linked_member_count == 2
    assert rows["people/john-smith/source-note.txt"]["person_id"] == "john-smith-i1"
    assert rows["people/john-smith/photo.jpg"]["family_context"] == "Synthetic John Smith folder"
    assert rows["unmapped/tree.ged"]["person_id"] is None
    assert "No ZIP member family context" in " ".join(rows["unmapped/tree.ged"]["review_notes"])


def test_inspect_zip_writes_csv_and_report(tmp_path: Path) -> None:
    zip_path, people_path, config_path, output_directory = build_zip_fixture(tmp_path)

    inspect_zip_archive(
        zip_path=zip_path,
        output_directory=output_directory,
        config_path=config_path,
        people_path=people_path,
    )

    assert (output_directory / "zip_member_manifest.json").exists()
    assert (output_directory / "zip_member_manifest.csv").exists()
    report = (output_directory / "zip_inspection_report.md").read_text()
    assert "ZIP members were read locally without extraction" in report
    assert "does not parse raw DNA" in report


def test_cli_inspect_zip_command_writes_outputs(tmp_path: Path) -> None:
    zip_path, people_path, config_path, output_directory = build_zip_fixture(tmp_path)

    exit_code = main(
        [
            "inspect-zip",
            "--zip",
            str(zip_path),
            "--people",
            str(people_path),
            "--config",
            str(config_path),
            "--out",
            str(output_directory),
        ]
    )

    assert exit_code == 0
    assert (output_directory / "zip_member_manifest.json").exists()
