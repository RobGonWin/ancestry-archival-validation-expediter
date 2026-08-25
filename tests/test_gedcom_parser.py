from __future__ import annotations

import json
from pathlib import Path

from aave.cli import main
from aave.gedcom_parser import parse_gedcom_file


def test_parse_gedcom_writes_expected_outputs(tmp_path: Path) -> None:
    gedcom_path = Path("tests/fixtures/sample_tree.synthetic.ged")
    output_directory = tmp_path / "out"

    parse_result = parse_gedcom_file(gedcom_path=gedcom_path, output_directory=output_directory)

    assert parse_result.person_count == 3
    assert parse_result.family_count == 1
    assert (output_directory / "people_index.json").exists()
    assert (output_directory / "families_index.json").exists()
    assert (output_directory / "gedcom_parse_report.md").exists()


def test_people_index_preserves_stable_shape_and_privacy_defaults(tmp_path: Path) -> None:
    gedcom_path = Path("tests/fixtures/sample_tree.synthetic.ged")
    output_directory = tmp_path / "out"

    parse_gedcom_file(gedcom_path=gedcom_path, output_directory=output_directory)

    people = json.loads((output_directory / "people_index.json").read_text())
    people_by_gedcom_id = {person["gedcom_id"]: person for person in people}

    assert people_by_gedcom_id["I1"]["person_id"] == "john-smith-i1"
    assert people_by_gedcom_id["I1"]["display_name"] == "John Smith"
    assert people_by_gedcom_id["I1"]["given_name"] == "John"
    assert people_by_gedcom_id["I1"]["surname"] == "Smith"
    assert people_by_gedcom_id["I1"]["birth_date"] == "12 JAN 1900"
    assert people_by_gedcom_id["I1"]["death_date"] == "5 MAY 1980"
    assert people_by_gedcom_id["I1"]["privacy_label"] == "private_family_only"
    assert people_by_gedcom_id["I1"]["is_potentially_living"] is False

    assert people_by_gedcom_id["I2"]["is_potentially_living"] is True
    assert people_by_gedcom_id["I2"]["notes"] == [
        "Synthetic mother record with a long continued note."
    ]
    assert people_by_gedcom_id["I3"]["is_potentially_living"] is True


def test_family_links_are_explicit_from_gedcom_records(tmp_path: Path) -> None:
    gedcom_path = Path("tests/fixtures/sample_tree.synthetic.ged")
    output_directory = tmp_path / "out"

    parse_gedcom_file(gedcom_path=gedcom_path, output_directory=output_directory)

    people = json.loads((output_directory / "people_index.json").read_text())
    people_by_gedcom_id = {person["gedcom_id"]: person for person in people}

    assert people_by_gedcom_id["I1"]["family_links"]["fams"] == ["F1"]
    assert people_by_gedcom_id["I1"]["family_links"]["spouse_ids"] == ["I2"]
    assert people_by_gedcom_id["I1"]["family_links"]["child_ids"] == ["I3"]

    assert people_by_gedcom_id["I3"]["family_links"]["famc"] == ["F1"]
    assert people_by_gedcom_id["I3"]["family_links"]["parent_ids"] == ["I1", "I2"]
    assert people_by_gedcom_id["I3"]["family_links"]["spouse_ids"] == []


def test_families_index_preserves_spouse_child_and_marriage_links(tmp_path: Path) -> None:
    gedcom_path = Path("tests/fixtures/sample_tree.synthetic.ged")
    output_directory = tmp_path / "out"

    parse_gedcom_file(gedcom_path=gedcom_path, output_directory=output_directory)

    families = json.loads((output_directory / "families_index.json").read_text())

    assert families == [
        {
            "family_id": "family-f1",
            "gedcom_id": "F1",
            "husband_id": "I1",
            "wife_id": "I2",
            "spouse_ids": ["I1", "I2"],
            "child_ids": ["I3"],
            "marriage_date": "14 FEB 1925",
            "marriage_place": "Example City, Example State",
            "source_refs": ["S1"],
            "notes": ["Synthetic marriage note."],
        }
    ]


def test_cli_parse_gedcom_command_writes_outputs(tmp_path: Path) -> None:
    gedcom_path = Path("tests/fixtures/sample_tree.synthetic.ged")
    output_directory = tmp_path / "out"

    exit_code = main(
        [
            "parse-gedcom",
            "--gedcom",
            str(gedcom_path),
            "--out",
            str(output_directory),
        ]
    )

    assert exit_code == 0
    assert (output_directory / "people_index.json").exists()
