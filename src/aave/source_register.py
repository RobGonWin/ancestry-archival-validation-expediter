"""Public source-register and discovery-question integrity checks.

The public research registers under `data/` are the substrate for discovery.
A question is only as good as the sources it names, so this module checks two
things and nothing more:

1. Each register record is complete. Every source carries an identifier, a
   role, at least one support statement, and at least one `cannot_support`
   statement. A source that claims support without stating its limits is the
   failure mode this repository exists to avoid.
2. Every discovery question refers to source identifiers that actually exist.
   Referential integrity is what stops a question from citing a literature
   impression instead of a declared source.

Neither check evaluates scientific merit. A register can be perfectly
well-formed and still describe weak evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SOURCE_REGISTER_FILES: tuple[str, ...] = (
    "data/longevity-sources.json",
    "data/generation-cohort-sources.json",
)
DISCOVERY_QUESTION_FILE = "data/discovery-questions.json"

REQUIRED_SOURCE_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "source_type",
    "urls",
    "evidence_role",
    "supports",
    "cannot_support",
)

REQUIRED_QUESTION_FIELDS: tuple[str, ...] = (
    "id",
    "question",
    "falsifier",
    "source_refs",
    "status",
    "cannot_support",
)

ALLOWED_QUESTION_STATUS: frozenset[str] = frozenset(
    {"open", "designed", "blocked", "withdrawn", "answered_null"}
)

PLACEHOLDER_VALUES: frozenset[str] = frozenset({"", "tbd", "todo", "n/a", "na", "?", "-"})


@dataclass(frozen=True)
class RegisterFinding:
    """One problem found in a register or question file."""

    file: str
    record_id: str
    field: str
    problem: str

    def as_dict(self) -> dict[str, str]:
        return {
            "file": self.file,
            "record_id": self.record_id,
            "field": self.field,
            "problem": self.problem,
        }


def is_placeholder(value: object) -> bool:
    """True when a value is missing or is filler standing in for an answer."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in PLACEHOLDER_VALUES
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def load_json_file(repository_path: Path, relative_path: str) -> dict[str, Any] | None:
    """Load one JSON object, or None when the file is absent."""
    candidate = repository_path / relative_path
    if not candidate.is_file():
        return None
    loaded = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{relative_path} must contain a JSON object")
    return loaded


def register_name(relative_path: str) -> str:
    """Short register name used to qualify an ambiguous source reference."""
    return Path(relative_path).stem


def collect_source_ids(repository_path: Path) -> dict[str, list[str]]:
    """Map every declared source identifier to the files that declare it.

    A source may legitimately appear in more than one register, because its
    evidence role depends on the question being asked. The mapping therefore
    keeps every declaring file rather than the first one.
    """
    identifiers: dict[str, list[str]] = {}
    for relative_path in SOURCE_REGISTER_FILES:
        payload = load_json_file(repository_path, relative_path)
        if payload is None:
            continue
        for record in payload.get("sources", []):
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                identifiers.setdefault(record["id"], []).append(relative_path)
    return identifiers


def collect_source_records(repository_path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Map (register name, identifier) to the record that register declares."""
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for relative_path in SOURCE_REGISTER_FILES:
        payload = load_json_file(repository_path, relative_path)
        if payload is None:
            continue
        for record in payload.get("sources", []):
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                records[(register_name(relative_path), record["id"])] = record
    return records


def resolve_reference(
    reference: str, identifiers: dict[str, list[str]]
) -> tuple[bool, str | None]:
    """Resolve a possibly qualified `register:id` reference.

    Returns (resolved, problem). A bare identifier declared by more than one
    register is deliberately treated as unresolved, because the registers give
    it different `cannot_support` constraints and a question must say which
    constraint set it accepted.
    """
    if ":" in reference:
        wanted_register, _, wanted_id = reference.partition(":")
        declaring = identifiers.get(wanted_id, [])
        if not declaring:
            return False, f"cites {reference!r}, which no register declares"
        if wanted_register not in {register_name(path) for path in declaring}:
            return False, (
                f"cites {reference!r}, but {wanted_id!r} is declared by "
                f"{sorted(register_name(p) for p in declaring)}"
            )
        return True, None

    declaring = identifiers.get(reference, [])
    if not declaring:
        return False, f"cites {reference!r}, which no register declares"
    if len(declaring) > 1:
        names = sorted(register_name(path) for path in declaring)
        return False, (
            f"cites {reference!r}, which {len(declaring)} registers declare with different "
            f"evidence roles and constraints. Qualify it as one of "
            f"{[name + ':' + reference for name in names]}"
        )
    return True, None


def check_source_registers(repository_path: Path) -> list[RegisterFinding]:
    """Check that every register record is complete and internally consistent."""
    findings: list[RegisterFinding] = []
    seen: dict[str, str] = {}

    for relative_path in SOURCE_REGISTER_FILES:
        payload = load_json_file(repository_path, relative_path)
        if payload is None:
            continue
        if is_placeholder(payload.get("schema_version")):
            findings.append(
                RegisterFinding(relative_path, "<file>", "schema_version", "missing")
            )
        for index, record in enumerate(payload.get("sources", [])):
            if not isinstance(record, dict):
                findings.append(
                    RegisterFinding(relative_path, f"#{index}", "<record>", "not an object")
                )
                continue
            record_id = record.get("id") if isinstance(record.get("id"), str) else f"#{index}"
            for field in REQUIRED_SOURCE_FIELDS:
                if is_placeholder(record.get(field)):
                    findings.append(
                        RegisterFinding(
                            relative_path,
                            record_id,
                            field,
                            "missing, empty, or placeholder",
                        )
                    )
            for url in record.get("urls", []) or []:
                if not isinstance(url, str) or not url.startswith("https://"):
                    findings.append(
                        RegisterFinding(relative_path, record_id, "urls", f"not https: {url!r}")
                    )
            if record_id in seen and seen[record_id] == relative_path:
                findings.append(
                    RegisterFinding(
                        relative_path,
                        record_id,
                        "id",
                        "duplicate identifier within the same register",
                    )
                )
            else:
                seen.setdefault(record_id, relative_path)
    return findings


def find_ambiguous_identifiers(repository_path: Path) -> list[dict[str, Any]]:
    """Identifiers declared by more than one register.

    Cross-listing is legitimate: the same paper carries a different evidence
    role depending on the question. It is recorded rather than treated as an
    error. What it does mean is that a question citing the bare identifier has
    not said which constraint set it accepted, so `resolve_reference` requires
    such a citation to be qualified.
    """
    identifiers = collect_source_ids(repository_path)
    records = collect_source_records(repository_path)
    ambiguous: list[dict[str, Any]] = []
    for identifier, paths in sorted(identifiers.items()):
        if len(paths) < 2:
            continue
        names = [register_name(path) for path in paths]
        variants = [records[(name, identifier)] for name in names if (name, identifier) in records]
        differing = sorted(
            {
                field
                for field in {key for variant in variants for key in variant}
                if len({json.dumps(v.get(field), sort_keys=True) for v in variants}) > 1
            }
        )
        ambiguous.append(
            {
                "id": identifier,
                "declared_by": names,
                "identical": not differing,
                "differing_fields": differing,
                "qualified_forms": [f"{name}:{identifier}" for name in names],
            }
        )
    return ambiguous


def check_discovery_questions(repository_path: Path) -> list[RegisterFinding]:
    """Check question completeness and that every cited source identifier exists."""
    findings: list[RegisterFinding] = []
    payload = load_json_file(repository_path, DISCOVERY_QUESTION_FILE)
    if payload is None:
        return findings

    known_ids = collect_source_ids(repository_path)
    seen: set[str] = set()

    for index, record in enumerate(payload.get("questions", [])):
        if not isinstance(record, dict):
            findings.append(
                RegisterFinding(DISCOVERY_QUESTION_FILE, f"#{index}", "<record>", "not an object")
            )
            continue
        record_id = record.get("id") if isinstance(record.get("id"), str) else f"#{index}"
        for field in REQUIRED_QUESTION_FIELDS:
            if is_placeholder(record.get(field)):
                findings.append(
                    RegisterFinding(
                        DISCOVERY_QUESTION_FILE,
                        record_id,
                        field,
                        "missing, empty, or placeholder",
                    )
                )
        status = record.get("status")
        if isinstance(status, str) and status not in ALLOWED_QUESTION_STATUS:
            findings.append(
                RegisterFinding(
                    DISCOVERY_QUESTION_FILE,
                    record_id,
                    "status",
                    f"unknown status {status!r}; allowed: {sorted(ALLOWED_QUESTION_STATUS)}",
                )
            )
        for reference in record.get("source_refs", []) or []:
            resolved, problem = resolve_reference(str(reference), known_ids)
            if not resolved and problem is not None:
                findings.append(
                    RegisterFinding(
                        DISCOVERY_QUESTION_FILE, record_id, "source_refs", problem
                    )
                )
        if record_id in seen:
            findings.append(
                RegisterFinding(DISCOVERY_QUESTION_FILE, record_id, "id", "duplicate identifier")
            )
        seen.add(record_id)
    return findings


def audit_source_registers(
    repository_path: Path,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    """Run both checks and return a machine-readable payload."""
    register_findings = check_source_registers(repository_path)
    question_findings = check_discovery_questions(repository_path)
    all_findings = register_findings + question_findings
    known_ids = collect_source_ids(repository_path)
    questions = load_json_file(repository_path, DISCOVERY_QUESTION_FILE) or {}

    ambiguous = find_ambiguous_identifiers(repository_path)
    payload: dict[str, Any] = {
        "schema_version": "aave.discovery-audit/1.0",
        "evidence_class": "register_integrity_nonpromoting",
        "declared_sources": len(known_ids),
        "ambiguous_identifiers": ambiguous,
        "declared_questions": len(questions.get("questions", [])),
        "register_findings": [finding.as_dict() for finding in register_findings],
        "question_findings": [finding.as_dict() for finding in question_findings],
        "finding_count": len(all_findings),
        "registers_ready": not all_findings,
        "cannot_support": [
            "This audit checks completeness and referential integrity only.",
            "It does not assess source quality, study design, or whether a question is worth asking.",
            "A well-formed register can still describe weak or contested evidence.",
            "Cross-listing an identifier is legitimate and is recorded, not penalised; only an "
            "unqualified citation of a cross-listed identifier is refused.",
        ],
    }

    if output_directory is not None:
        output_directory.mkdir(parents=True, exist_ok=True)
        write_json(payload, output_directory / "discovery_audit.json")
    return payload


def write_json(data: object, output_path: Path) -> None:
    """Write one JSON document with a trailing newline."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
