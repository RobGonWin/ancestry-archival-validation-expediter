from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aave.cli import main
from aave.privacy_audit import audit_repository_privacy


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "AAVE Test"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def git_add(path: Path, *tracked_paths: str) -> None:
    subprocess.run(
        ["git", "add", *tracked_paths],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def test_privacy_audit_flags_tracked_raw_dna_without_reading_content(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo)
    (repo / "README.md").write_text("# Example\n", encoding="utf-8")
    (repo / "raw-dna-export.txt").write_text("synthetic blocked fixture\n", encoding="utf-8")
    git_add(repo, "README.md", "raw-dna-export.txt")

    output_directory = tmp_path / "audit"
    audit_result = audit_repository_privacy(repo, output_directory)
    payload = json.loads((output_directory / "privacy_audit.json").read_text())
    report = (output_directory / "privacy_audit_report.md").read_text()

    assert audit_result.publish_ready is False
    assert payload["blocker_count"] == 1
    assert payload["findings"][0]["path"] == "raw-dna-export.txt"
    assert payload["findings"][0]["rule_id"] == "raw_dna_file"
    assert "does not read file contents" in report


@pytest.mark.parametrize(
    "filename",
    [
        "AncestryDNA.txt",
        "ancestrydn.txt",
        "dna-data-2026-08-24.txt",
        "DNA_DATA_2026.csv",
        "consumer-genotype.tsv",
    ],
)
def test_privacy_audit_blocks_common_raw_dna_export_names(
    tmp_path: Path,
    filename: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo)
    (repo / filename).write_text("synthetic blocked fixture\n", encoding="utf-8")
    git_add(repo, filename)

    output_directory = tmp_path / "audit"
    audit_result = audit_repository_privacy(repo, output_directory)
    payload = json.loads((output_directory / "privacy_audit.json").read_text())

    assert audit_result.publish_ready is False
    assert payload["blocker_count"] == 1
    assert payload["findings"][0]["rule_id"] == "raw_dna_file"


def test_privacy_audit_blocks_controlled_folder_and_reviews_media(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo)
    controlled_file = repo / "account-captures" / "page.json"
    controlled_file.parent.mkdir()
    controlled_file.write_text("{}\n", encoding="utf-8")
    image_file = repo / "docs" / "public-photo.jpg"
    image_file.parent.mkdir()
    image_file.write_bytes(b"synthetic image fixture")
    git_add(repo, "account-captures/page.json", "docs/public-photo.jpg")

    output_directory = tmp_path / "audit"
    audit_result = audit_repository_privacy(repo, output_directory)
    payload = json.loads((output_directory / "privacy_audit.json").read_text())

    assert audit_result.publish_ready is False
    assert payload["blocker_count"] == 1
    assert payload["review_count"] == 1
    assert {finding["rule_id"] for finding in payload["findings"]} == {
        "controlled_evidence_folder",
        "media_or_document_file",
    }


def test_privacy_audit_blocks_real_gedcom_but_allows_exact_synthetic_fixture(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo)
    real_export = repo / "family-tree.ged"
    real_export.write_text("0 HEAD\n0 TRLR\n", encoding="utf-8")
    synthetic_fixture = repo / "tests" / "fixtures" / "sample_tree.synthetic.ged"
    synthetic_fixture.parent.mkdir(parents=True)
    synthetic_fixture.write_text("0 HEAD\n1 SOUR AAVE_SYNTHETIC\n0 TRLR\n", encoding="utf-8")
    git_add(repo, "family-tree.ged", "tests/fixtures/sample_tree.synthetic.ged")

    output_directory = tmp_path / "audit"
    audit_result = audit_repository_privacy(repo, output_directory)
    payload = json.loads((output_directory / "privacy_audit.json").read_text())

    assert audit_result.publish_ready is False
    assert payload["blocker_count"] == 1
    assert payload["findings"] == [
        {
            "path": "family-tree.ged",
            "rule_id": "genealogy_export",
            "severity": "blocker",
            "description": "Real GEDCOM exports must stay outside the public repository.",
        }
    ]


def test_privacy_audit_clean_repo_is_publish_ready(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo)
    (repo / "README.md").write_text("# Example\n", encoding="utf-8")
    (repo / ".env.example").write_text("AAVE_TOKEN=\n", encoding="utf-8")
    docs_dir = repo / "docs"
    docs_dir.mkdir()
    (docs_dir / "ANCESTRYDNA_PARSER_PROMPT.md").write_text("Docs only\n", encoding="utf-8")
    git_add(repo, "README.md", ".env.example", "docs/ANCESTRYDNA_PARSER_PROMPT.md")

    output_directory = tmp_path / "audit"
    audit_result = audit_repository_privacy(repo, output_directory)

    assert audit_result.publish_ready is True
    assert audit_result.flagged_path_count == 0


def test_cli_privacy_audit_strict_returns_one_when_findings_exist(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo)
    (repo / "raw-dna-export.txt").write_text("synthetic blocked fixture\n", encoding="utf-8")
    git_add(repo, "raw-dna-export.txt")

    exit_code = main(
        [
            "privacy-audit",
            "--repo",
            str(repo),
            "--out",
            str(tmp_path / "audit"),
            "--strict",
        ]
    )

    assert exit_code == 1
    assert (tmp_path / "audit" / "privacy_audit_report.md").exists()
