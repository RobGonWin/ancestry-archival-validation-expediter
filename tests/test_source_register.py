"""Tests for public source-register and discovery-question integrity."""

from __future__ import annotations

import json
from pathlib import Path

from aave.source_register import (
    audit_source_registers,
    check_discovery_questions,
    check_source_registers,
    find_ambiguous_identifiers,
    resolve_reference,
)


def write_register(root: Path, name: str, sources: list[dict[str, object]]) -> None:
    data_directory = root / "data"
    data_directory.mkdir(parents=True, exist_ok=True)
    (data_directory / name).write_text(
        json.dumps({"schema_version": "test/1.0", "sources": sources}, indent=2),
        encoding="utf-8",
    )


def write_questions(root: Path, questions: list[dict[str, object]]) -> None:
    data_directory = root / "data"
    data_directory.mkdir(parents=True, exist_ok=True)
    (data_directory / "discovery-questions.json").write_text(
        json.dumps({"schema_version": "test/1.0", "questions": questions}, indent=2),
        encoding="utf-8",
    )


def make_source(identifier: str, **overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": identifier,
        "title": "A source title",
        "source_type": "journal_article",
        "urls": ["https://doi.org/10.0000/example"],
        "evidence_role": "population_context",
        "supports": ["A narrow supported statement"],
        "cannot_support": ["An explicit limit"],
    }
    record.update(overrides)
    return record


def make_question(identifier: str, refs: list[str], **overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": identifier,
        "question": "Does the declared exposure relate to the declared outcome?",
        "falsifier": "An interval covering the null closes the question as a null.",
        "source_refs": refs,
        "status": "open",
        "cannot_support": ["No individual conclusion", "No causal reading"],
    }
    record.update(overrides)
    return record


def test_complete_register_has_no_findings(tmp_path: Path) -> None:
    write_register(tmp_path, "longevity-sources.json", [make_source("A-1")])
    assert check_source_registers(tmp_path) == []


def test_source_without_cannot_support_is_flagged(tmp_path: Path) -> None:
    write_register(tmp_path, "longevity-sources.json", [make_source("A-1", cannot_support=[])])
    findings = check_source_registers(tmp_path)
    assert [f.field for f in findings] == ["cannot_support"]


def test_non_https_url_is_flagged(tmp_path: Path) -> None:
    write_register(
        tmp_path, "longevity-sources.json", [make_source("A-1", urls=["http://example.org"])]
    )
    assert any(f.field == "urls" for f in check_source_registers(tmp_path))


def test_duplicate_within_one_register_is_flagged(tmp_path: Path) -> None:
    write_register(
        tmp_path, "longevity-sources.json", [make_source("A-1"), make_source("A-1")]
    )
    assert any(f.field == "id" for f in check_source_registers(tmp_path))


def test_cross_register_listing_is_recorded_not_flagged(tmp_path: Path) -> None:
    write_register(tmp_path, "longevity-sources.json", [make_source("SHARED")])
    write_register(
        tmp_path,
        "generation-cohort-sources.json",
        [make_source("SHARED", evidence_role="survival_context")],
    )
    assert check_source_registers(tmp_path) == []

    ambiguous = find_ambiguous_identifiers(tmp_path)
    assert len(ambiguous) == 1
    assert ambiguous[0]["id"] == "SHARED"
    assert ambiguous[0]["identical"] is False
    assert "evidence_role" in ambiguous[0]["differing_fields"]


def test_question_citing_unknown_source_is_flagged(tmp_path: Path) -> None:
    write_register(tmp_path, "longevity-sources.json", [make_source("A-1")])
    write_questions(tmp_path, [make_question("Q-1", ["DOES-NOT-EXIST"])])
    findings = check_discovery_questions(tmp_path)
    assert any("no register declares" in f.problem for f in findings)


def test_question_citing_cross_listed_source_must_qualify(tmp_path: Path) -> None:
    write_register(tmp_path, "longevity-sources.json", [make_source("SHARED")])
    write_register(tmp_path, "generation-cohort-sources.json", [make_source("SHARED")])
    write_questions(tmp_path, [make_question("Q-1", ["SHARED"])])

    findings = check_discovery_questions(tmp_path)
    assert any("Qualify it as one of" in f.problem for f in findings)

    write_questions(tmp_path, [make_question("Q-1", ["longevity-sources:SHARED"])])
    assert check_discovery_questions(tmp_path) == []


def test_qualified_reference_to_wrong_register_is_flagged(tmp_path: Path) -> None:
    write_register(tmp_path, "longevity-sources.json", [make_source("A-1")])
    write_questions(tmp_path, [make_question("Q-1", ["generation-cohort-sources:A-1"])])
    assert any("is declared by" in f.problem for f in check_discovery_questions(tmp_path))


def test_unknown_question_status_is_flagged(tmp_path: Path) -> None:
    write_register(tmp_path, "longevity-sources.json", [make_source("A-1")])
    write_questions(tmp_path, [make_question("Q-1", ["A-1"], status="probably_fine")])
    assert any(f.field == "status" for f in check_discovery_questions(tmp_path))


def test_resolve_reference_handles_single_and_missing() -> None:
    identifiers = {"A-1": ["data/longevity-sources.json"]}
    assert resolve_reference("A-1", identifiers) == (True, None)
    resolved, problem = resolve_reference("NOPE", identifiers)
    assert resolved is False
    assert problem is not None


def test_audit_payload_is_wellformed_and_nonpromoting(tmp_path: Path) -> None:
    write_register(tmp_path, "longevity-sources.json", [make_source("A-1")])
    write_questions(tmp_path, [make_question("Q-1", ["A-1"])])
    payload = audit_source_registers(tmp_path, output_directory=tmp_path / "out")

    assert payload["registers_ready"] is True
    assert payload["declared_sources"] == 1
    assert payload["declared_questions"] == 1
    assert payload["evidence_class"] == "register_integrity_nonpromoting"
    assert len(payload["cannot_support"]) >= 3
    assert (tmp_path / "out" / "discovery_audit.json").is_file()


def test_missing_question_file_is_not_an_error(tmp_path: Path) -> None:
    write_register(tmp_path, "longevity-sources.json", [make_source("A-1")])
    assert check_discovery_questions(tmp_path) == []
