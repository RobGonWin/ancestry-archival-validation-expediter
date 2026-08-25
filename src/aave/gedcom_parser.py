"""GEDCOM parsing and person graph indexing.

The v0.2 parser preserves explicit GEDCOM links only. It does not infer biological
relationships from names, dates, sex tags, or household proximity.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from aave.models import (
    FamilyIndexEntry,
    FamilyLinks,
    GedcomParseResult,
    LifeEvent,
    PersonIndexEntry,
)
from aave.privacy import DEFAULT_PRIVACY_LABEL


@dataclass
class GedcomNode:
    """A simple GEDCOM syntax tree node."""

    level: int
    tag: str
    value: str
    pointer: str | None = None
    children: list[GedcomNode] = field(default_factory=list)


def parse_gedcom_file(gedcom_path: Path, output_directory: Path) -> GedcomParseResult:
    """Parse a local GEDCOM file and write person, family, and report outputs."""
    if not gedcom_path.exists():
        raise FileNotFoundError(f"GEDCOM file does not exist: {gedcom_path}")
    if not gedcom_path.is_file():
        raise IsADirectoryError(f"GEDCOM path must be a file: {gedcom_path}")

    output_directory.mkdir(parents=True, exist_ok=True)

    root_nodes = read_gedcom_nodes(gedcom_path)
    individual_nodes = [node for node in root_nodes if node.tag == "INDI"]
    family_nodes = [node for node in root_nodes if node.tag == "FAM"]

    family_entries = build_family_entries(family_nodes)
    person_entries = build_person_entries(individual_nodes, family_entries)

    write_json([asdict(entry) for entry in person_entries], output_directory / "people_index.json")
    write_json(
        [asdict(entry) for entry in family_entries],
        output_directory / "families_index.json",
    )
    write_parse_report(
        person_entries=person_entries,
        family_entries=family_entries,
        gedcom_path=gedcom_path,
        output_path=output_directory / "gedcom_parse_report.md",
    )

    parse_result = GedcomParseResult(
        person_count=len(person_entries),
        family_count=len(family_entries),
        output_directory=output_directory,
    )
    return parse_result


def read_gedcom_nodes(gedcom_path: Path) -> list[GedcomNode]:
    """Read GEDCOM records with ged4py when available, otherwise use the local reader."""
    try:
        root_nodes = read_gedcom_nodes_with_ged4py(gedcom_path)
    except ImportError:
        root_nodes = read_gedcom_nodes_from_text(gedcom_path)

    return root_nodes


def read_gedcom_nodes_with_ged4py(gedcom_path: Path) -> list[GedcomNode]:
    """Read GEDCOM records through ged4py and adapt them to AAVE nodes."""
    from ged4py.parser import GedcomReader

    with GedcomReader(str(gedcom_path)) as parser:
        root_nodes = [convert_ged4py_record(record) for record in parser.records0()]

    return root_nodes


def convert_ged4py_record(record: object) -> GedcomNode:
    """Convert a ged4py model record into an internal AAVE node."""
    node = GedcomNode(
        level=record.level,
        tag=record.tag,
        value=format_ged4py_value(record.value),
        pointer=normalize_optional_pointer(record.xref_id),
        children=[convert_ged4py_record(child) for child in record.sub_records],
    )
    return node


def format_ged4py_value(value: object) -> str:
    """Convert ged4py record values to stable text values for AAVE JSON."""
    if value is None:
        return ""

    if isinstance(value, tuple) and len(value) == 3:
        given_name, surname, suffix = value
        formatted_name = f"{given_name} /{surname}/ {suffix}".strip()
        return formatted_name

    formatted_value = str(value)
    return formatted_value


def read_gedcom_nodes_from_text(gedcom_path: Path) -> list[GedcomNode]:
    """Read GEDCOM lines into top-level syntax tree nodes."""
    lines = gedcom_path.read_text(encoding="utf-8-sig").splitlines()
    root_nodes: list[GedcomNode] = []
    node_stack: list[GedcomNode] = []

    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue

        node = parse_gedcom_line(raw_line, line_number)
        while node_stack and node_stack[-1].level >= node.level:
            node_stack.pop()

        if node_stack:
            node_stack[-1].children.append(node)
        else:
            root_nodes.append(node)

        node_stack.append(node)

    return root_nodes


def parse_gedcom_line(raw_line: str, line_number: int) -> GedcomNode:
    """Parse one GEDCOM line into level, optional pointer, tag, and value."""
    parts = raw_line.strip().split(maxsplit=2)
    if len(parts) < 2:
        raise ValueError(f"Invalid GEDCOM line {line_number}: {raw_line}")

    try:
        level = int(parts[0])
    except ValueError as exc:
        raise ValueError(f"Invalid GEDCOM level on line {line_number}: {raw_line}") from exc

    pointer: str | None = None
    tag: str
    value = ""

    if len(parts) >= 3 and is_pointer(parts[1]):
        pointer = normalize_gedcom_id(parts[1])
        tag = parts[2].split(maxsplit=1)[0]
        value_parts = parts[2].split(maxsplit=1)
        if len(value_parts) == 2:
            value = value_parts[1]
    else:
        tag = parts[1]
        if len(parts) == 3:
            value = parts[2]

    gedcom_node = GedcomNode(level=level, tag=tag, value=value, pointer=pointer)
    return gedcom_node


def build_person_entries(
    individual_nodes: list[GedcomNode],
    family_entries: list[FamilyIndexEntry],
) -> list[PersonIndexEntry]:
    """Build stable person index entries from INDI nodes."""
    families_by_id = {family.gedcom_id: family for family in family_entries}
    child_family_ids_by_person = defaultdict(list)
    spouse_family_ids_by_person = defaultdict(list)
    parent_ids_by_person = defaultdict(list)
    spouse_ids_by_person = defaultdict(list)
    child_ids_by_person = defaultdict(list)

    for family in family_entries:
        spouse_ids = family.spouse_ids
        for child_id in family.child_ids:
            child_family_ids_by_person[child_id].append(family.gedcom_id)
            parent_ids_by_person[child_id].extend(spouse_ids)
        for spouse_id in spouse_ids:
            spouse_family_ids_by_person[spouse_id].append(family.gedcom_id)
            spouse_ids_by_person[spouse_id].extend(
                other_spouse_id for other_spouse_id in spouse_ids if other_spouse_id != spouse_id
            )
            child_ids_by_person[spouse_id].extend(family.child_ids)

    person_entries: list[PersonIndexEntry] = []
    for individual_node in individual_nodes:
        gedcom_id = individual_node.pointer or ""
        name_node = find_first_child(individual_node, "NAME")
        display_name, given_name, surname = parse_name(name_node.value if name_node else "")
        birth_event = extract_event(individual_node, "BIRT")
        death_event = extract_event(individual_node, "DEAT")

        famc = normalize_pointer_values(find_child_values(individual_node, "FAMC"))
        fams = normalize_pointer_values(find_child_values(individual_node, "FAMS"))
        parent_family_ids = sorted_unique([*famc, *child_family_ids_by_person[gedcom_id]])
        spouse_family_ids = sorted_unique([*fams, *spouse_family_ids_by_person[gedcom_id]])
        parent_ids = sorted_unique(parent_ids_by_person[gedcom_id])
        spouse_ids = sorted_unique(spouse_ids_by_person[gedcom_id])
        child_ids = sorted_unique(child_ids_by_person[gedcom_id])

        family_links = FamilyLinks(
            famc=sorted_unique(famc),
            fams=sorted_unique(fams),
            parent_family_ids=parent_family_ids,
            spouse_family_ids=[
                family_id for family_id in spouse_family_ids if family_id in families_by_id
            ],
            parent_ids=parent_ids,
            spouse_ids=spouse_ids,
            child_ids=child_ids,
        )
        person_entry = PersonIndexEntry(
            person_id=build_person_slug(display_name, gedcom_id),
            gedcom_id=gedcom_id,
            display_name=display_name,
            given_name=given_name,
            surname=surname,
            birth_date=birth_event.date,
            birth_place=birth_event.place,
            death_date=death_event.date,
            death_place=death_event.place,
            gender_or_sex=find_first_child_value(individual_node, "SEX"),
            family_links=family_links,
            source_refs=extract_source_refs(individual_node),
            privacy_label=DEFAULT_PRIVACY_LABEL,
            notes=extract_notes(individual_node),
            is_potentially_living=death_event.date is None,
        )
        person_entries.append(person_entry)

    sorted_person_entries = sorted(person_entries, key=lambda entry: entry.person_id)
    return sorted_person_entries


def build_family_entries(family_nodes: list[GedcomNode]) -> list[FamilyIndexEntry]:
    """Build stable family index entries from FAM nodes."""
    family_entries: list[FamilyIndexEntry] = []
    for family_node in family_nodes:
        gedcom_id = family_node.pointer or ""
        husband_id = normalize_optional_pointer(find_first_child_value(family_node, "HUSB"))
        wife_id = normalize_optional_pointer(find_first_child_value(family_node, "WIFE"))
        spouse_ids = sorted_unique([person_id for person_id in [husband_id, wife_id] if person_id])
        child_ids = sorted_unique(normalize_pointer_values(find_child_values(family_node, "CHIL")))
        marriage_event = extract_event(family_node, "MARR")

        family_entry = FamilyIndexEntry(
            family_id=build_family_slug(gedcom_id),
            gedcom_id=gedcom_id,
            husband_id=husband_id,
            wife_id=wife_id,
            spouse_ids=spouse_ids,
            child_ids=child_ids,
            marriage_date=marriage_event.date,
            marriage_place=marriage_event.place,
            source_refs=extract_source_refs(family_node),
            notes=extract_notes(family_node),
        )
        family_entries.append(family_entry)

    sorted_family_entries = sorted(family_entries, key=lambda entry: entry.family_id)
    return sorted_family_entries


def extract_event(node: GedcomNode, tag: str) -> LifeEvent:
    """Extract DATE and PLAC details from a GEDCOM event node."""
    event_node = find_first_child(node, tag)
    if event_node is None:
        life_event = LifeEvent()
        return life_event

    life_event = LifeEvent(
        date=find_first_child_value(event_node, "DATE"),
        place=find_first_child_value(event_node, "PLAC"),
    )
    return life_event


def extract_notes(node: GedcomNode) -> list[str]:
    """Extract NOTE text from a node and its direct event children."""
    notes: list[str] = []
    for child in node.children:
        if child.tag == "NOTE":
            notes.append(collect_text(child))
        elif child.tag in {"BIRT", "DEAT", "BURI", "MARR"}:
            notes.extend(
                collect_text(grandchild)
                for grandchild in child.children
                if grandchild.tag == "NOTE"
            )

    cleaned_notes = [note for note in notes if note]
    return cleaned_notes


def extract_source_refs(node: GedcomNode) -> list[str]:
    """Extract SOUR references from a node and its direct event children."""
    source_refs: list[str] = []
    for child in node.children:
        if child.tag == "SOUR":
            source_refs.append(collect_text(child))
        elif child.tag in {"BIRT", "DEAT", "BURI", "MARR"}:
            source_refs.extend(
                collect_text(grandchild)
                for grandchild in child.children
                if grandchild.tag == "SOUR"
            )

    normalized_source_refs = sorted_unique(source_ref for source_ref in source_refs if source_ref)
    return normalized_source_refs


def collect_text(node: GedcomNode) -> str:
    """Collect GEDCOM text, including CONC and CONT continuations."""
    text = normalize_optional_pointer(node.value) or node.value
    for child in node.children:
        if child.tag == "CONC":
            text = concatenate_gedcom_text(text, child.value)
        elif child.tag == "CONT":
            text = f"{text}\n{child.value}"

    collected_text = text.strip()
    return collected_text


def concatenate_gedcom_text(current_text: str, continuation_text: str) -> str:
    """Concatenate GEDCOM CONC text without accidentally merging adjacent words."""
    if current_text and continuation_text:
        needs_word_space = current_text[-1].isalnum() and continuation_text[0].isalnum()
        if needs_word_space:
            concatenated_text = f"{current_text} {continuation_text}"
            return concatenated_text

    concatenated_text = f"{current_text}{continuation_text}"
    return concatenated_text


def parse_name(raw_name: str) -> tuple[str, str | None, str | None]:
    """Parse a GEDCOM NAME value into display, given, and surname fields."""
    if not raw_name:
        return "Unknown", None, None

    surname_match = re.search(r"/([^/]*)/", raw_name)
    surname = surname_match.group(1).strip() if surname_match else None
    given_name = raw_name.split("/", maxsplit=1)[0].strip() or None
    display_name = raw_name.replace("/", " ").strip()
    display_name = re.sub(r"\s+", " ", display_name)

    return display_name, given_name, surname


def build_person_slug(display_name: str, gedcom_id: str) -> str:
    """Build a stable readable person slug."""
    name_slug = slugify(display_name) or "unknown-person"
    id_slug = slugify(gedcom_id) or "unknown-id"
    person_slug = f"{name_slug}-{id_slug}"
    return person_slug


def build_family_slug(gedcom_id: str) -> str:
    """Build a stable readable family slug."""
    id_slug = slugify(gedcom_id) or "unknown-id"
    family_slug = f"family-{id_slug}"
    return family_slug


def slugify(value: str) -> str:
    """Convert a label into a lowercase ASCII slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug


def find_first_child(node: GedcomNode, tag: str) -> GedcomNode | None:
    """Find the first direct child with a GEDCOM tag."""
    for child in node.children:
        if child.tag == tag:
            return child
    return None


def find_first_child_value(node: GedcomNode, tag: str) -> str | None:
    """Find the first direct child value for a GEDCOM tag."""
    child = find_first_child(node, tag)
    if child is None:
        return None

    child_value = collect_text(child)
    return child_value


def find_child_values(node: GedcomNode, tag: str) -> list[str]:
    """Find all direct child values for a GEDCOM tag."""
    values = [collect_text(child) for child in node.children if child.tag == tag]
    return values


def normalize_pointer_values(values: list[str]) -> list[str]:
    """Normalize GEDCOM pointer values by stripping pointer markers."""
    normalized_values = [normalize_gedcom_id(value) for value in values if value]
    return normalized_values


def normalize_optional_pointer(value: str | None) -> str | None:
    """Normalize a GEDCOM pointer-like value when present."""
    if value is None:
        return None
    normalized_value = normalize_gedcom_id(value)
    return normalized_value


def normalize_gedcom_id(value: str) -> str:
    """Strip GEDCOM pointer markers from an ID-like value."""
    normalized_id = value.strip()
    if is_pointer(normalized_id):
        normalized_id = normalized_id[1:-1]
    return normalized_id


def is_pointer(value: str) -> bool:
    """Return whether a value is a GEDCOM pointer token."""
    is_pointer_value = value.startswith("@") and value.endswith("@")
    return is_pointer_value


def sorted_unique(values: list[str] | object) -> list[str]:
    """Return sorted unique string values while preserving deterministic output."""
    unique_values = sorted({value for value in values if isinstance(value, str) and value})
    return unique_values


def write_json(data: list[dict[str, object]], output_path: Path) -> None:
    """Write formatted JSON with deterministic key order from dataclass dictionaries."""
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(data, output_file, indent=2)
        output_file.write("\n")


def write_parse_report(
    person_entries: list[PersonIndexEntry],
    family_entries: list[FamilyIndexEntry],
    gedcom_path: Path,
    output_path: Path,
) -> None:
    """Write a concise Markdown report for GEDCOM parsing."""
    potentially_living_count = sum(1 for person in person_entries if person.is_potentially_living)
    lines = [
        "# GEDCOM Parse Report",
        "",
        f"GEDCOM file: `{gedcom_path}`",
        f"People parsed: {len(person_entries)}",
        f"Families parsed: {len(family_entries)}",
        f"Potentially living people: {potentially_living_count}",
        "",
        "## Safety Notes",
        "",
        "- This parse used a local GEDCOM file only.",
        "- Relationships are represented only when explicit GEDCOM family links exist.",
        "- Source and note text is preserved for audit; "
        "it is not treated as verified proof by itself.",
        "- Redaction and public export behavior are not implemented in v0.2.",
        "",
    ]

    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))
