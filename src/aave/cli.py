"""Command-line interface for AAVE."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aave.archive_formats import inspect_archive_formats
from aave.evidence import (
    build_claim_graph,
    import_evidence_envelope,
    load_json_object,
    validate_evidence_envelope,
)
from aave.exports import EXPORT_PROFILES, export_bundle
from aave.gedcom_parser import parse_gedcom_file
from aave.genome import crossref_snp_hits, parse_ancestrydna_file
from aave.integrations.archivebox_connector import build_archivebox_dry_run
from aave.integrations.perma_connector import build_perma_dry_run
from aave.integrations.static_site_export import build_static_site_dry_run
from aave.integrations.zotero_connector import build_zotero_dry_run
from aave.linking import link_sources
from aave.manifest import scan_archive
from aave.packets import generate_packet
from aave.privacy_audit import audit_repository_privacy
from aave.research_boundary import audit_research_boundary
from aave.research_program import (
    ResearchProgramValidationError,
    validate_research_program,
)
from aave.source_register import audit_source_registers
from aave.private_bridge import load_public_projection_receipt
from aave.zip_archives import inspect_zip_archive


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        prog="aave",
        description="Local-first archival validation tools for genealogy archives.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a local archive folder and write manifest outputs.",
    )
    scan_parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Local archive folder to scan.",
    )
    scan_parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="JSON config file with conservative defaults.",
    )
    scan_parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output folder for archive_manifest.json, archive_manifest.csv, and audit_summary.md.",
    )

    gedcom_parser = subparsers.add_parser(
        "parse-gedcom",
        help="Parse a local GEDCOM file and write person and family indexes.",
    )
    gedcom_parser.add_argument(
        "--gedcom",
        required=True,
        type=Path,
        help="Local GEDCOM file to parse.",
    )
    gedcom_parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help=(
            "Output folder for people_index.json, families_index.json, "
            "and gedcom_parse_report.md."
        ),
    )

    link_parser = subparsers.add_parser(
        "link",
        help="Link scanned artifacts to parsed people using conservative local metadata.",
    )
    link_parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="Path to archive_manifest.json.",
    )
    link_parser.add_argument(
        "--people",
        required=True,
        type=Path,
        help="Path to people_index.json.",
    )
    link_parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="JSON config file with defaults and optional manual source links.",
    )
    link_parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output folder for source_links.json and linking_report.md.",
    )

    export_parser = subparsers.add_parser(
        "export",
        help="Build public, private, or expert-review metadata export bundles.",
    )
    export_parser.add_argument(
        "--profile",
        required=True,
        choices=sorted(EXPORT_PROFILES),
        help="Export profile to build.",
    )
    export_parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output folder for export_manifest.json, export_manifest.csv, and README_EXPORT.md.",
    )
    export_parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional path to archive_manifest.json. Defaults to the parent of --out.",
    )
    export_parser.add_argument(
        "--people",
        type=Path,
        default=None,
        help="Optional path to people_index.json. Defaults to the parent of --out when present.",
    )
    export_parser.add_argument(
        "--links",
        type=Path,
        default=None,
        help="Optional path to source_links.json. Defaults to the parent of --out when present.",
    )
    export_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write export manifests and mark README_EXPORT.md as a dry run.",
    )

    inspect_parser = subparsers.add_parser(
        "inspect-archives",
        help="Inspect saved HTML/PDF/WARC/WACZ metadata from a local manifest.",
    )
    inspect_parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="Path to archive_manifest.json.",
    )
    inspect_parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output folder for archive_format_report.md and archive_format_metadata.json.",
    )

    packet_parser = subparsers.add_parser(
        "packet",
        help="Generate a Markdown research packet and source CSV for one person.",
    )
    packet_parser.add_argument(
        "--person",
        required=True,
        help="Person ID from people_index.json, such as synthetic-person-001.",
    )
    packet_parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output folder for <person_id>.md and <person_id>_sources.csv.",
    )
    packet_parser.add_argument(
        "--profile",
        choices=sorted(EXPORT_PROFILES),
        default="private_full",
        help="Packet profile to apply.",
    )
    packet_parser.add_argument(
        "--people",
        type=Path,
        default=None,
        help="Optional path to people_index.json. Defaults to the parent of --out.",
    )
    packet_parser.add_argument(
        "--families",
        type=Path,
        default=None,
        help="Optional path to families_index.json. Defaults to the parent of --out.",
    )
    packet_parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional path to archive_manifest.json. Defaults to the parent of --out.",
    )
    packet_parser.add_argument(
        "--links",
        type=Path,
        default=None,
        help="Optional path to source_links.json. Defaults to the parent of --out.",
    )
    packet_parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional path to config.json. Defaults to the parent of --out when present.",
    )

    zip_parser = subparsers.add_parser(
        "inspect-zip",
        help="Inspect local ZIP members and apply optional family-member context.",
    )
    zip_parser.add_argument(
        "--zip",
        required=True,
        type=Path,
        help="Local ZIP file to inspect without extracting.",
    )
    zip_parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output folder for zip_member_manifest.json/csv and zip_inspection_report.md.",
    )
    zip_parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional config file with zip_member_contexts.",
    )
    zip_parser.add_argument(
        "--people",
        type=Path,
        default=None,
        help="Optional people_index.json for resolving person_id or gedcom_id.",
    )

    genome_parser = subparsers.add_parser(
        "genome",
        help="Offline whitelist-only parsing for a user-owned AncestryDNA export.",
    )
    genome_subparsers = genome_parser.add_subparsers(dest="genome_command", required=True)
    ancestrydna_parser = genome_subparsers.add_parser(
        "parse-ancestrydna",
        help="Parse a local export against a reviewed local SNP whitelist.",
    )
    ancestrydna_parser.add_argument("--input", required=True, type=Path)
    ancestrydna_parser.add_argument("--whitelist", required=True, type=Path)
    ancestrydna_parser.add_argument("--out", required=True, type=Path)
    crossref_parser = genome_subparsers.add_parser(
        "crossref",
        help="Annotate local SNP hits using the same reviewed local whitelist.",
    )
    crossref_parser.add_argument("--hits", required=True, type=Path)
    crossref_parser.add_argument("--whitelist", required=True, type=Path)
    crossref_parser.add_argument("--out", required=True, type=Path)

    integrations_parser = subparsers.add_parser(
        "integrations",
        help="Disabled-by-default optional integration dry-run skeletons.",
    )
    integration_subparsers = integrations_parser.add_subparsers(
        dest="integration_command",
        required=True,
    )

    archivebox_parser = integration_subparsers.add_parser(
        "archivebox",
        help="Write an ArchiveBox dry-run payload without calling ArchiveBox.",
    )
    archivebox_parser.add_argument("--out", required=True, type=Path)
    archivebox_parser.add_argument("--mode", choices=["cli", "rest"], default="cli")
    archivebox_parser.add_argument("--enable", action="store_true")
    archivebox_parser.add_argument("--dry-run", action="store_true", default=True)

    zotero_parser = integration_subparsers.add_parser(
        "zotero",
        help="Write a Zotero dry-run payload without calling Zotero.",
    )
    zotero_parser.add_argument("--out", required=True, type=Path)
    zotero_parser.add_argument("--manifest", type=Path, default=None)
    zotero_parser.add_argument("--enable", action="store_true")
    zotero_parser.add_argument("--dry-run", action="store_true", default=True)

    perma_parser = integration_subparsers.add_parser(
        "perma",
        help="Write a Perma.cc dry-run payload without calling Perma.cc.",
    )
    perma_parser.add_argument("--out", required=True, type=Path)
    perma_parser.add_argument("--enable", action="store_true")
    perma_parser.add_argument("--dry-run", action="store_true", default=True)

    static_parser = integration_subparsers.add_parser(
        "static-site",
        help="Write static public metadata dry-run files from an export manifest.",
    )
    static_parser.add_argument("--out", required=True, type=Path)
    static_parser.add_argument("--export-manifest", required=True, type=Path)
    static_parser.add_argument("--enable", action="store_true")
    static_parser.add_argument("--dry-run", action="store_true", default=True)

    privacy_audit_parser = subparsers.add_parser(
        "privacy-audit",
        help="Audit tracked repository paths before GitHub/publication workflows.",
    )
    privacy_audit_parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Local Git repository path to audit.",
    )
    privacy_audit_parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output folder for privacy_audit.json and privacy_audit_report.md.",
    )
    privacy_audit_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when any blocker or review finding is present.",
    )

    discovery_parser = subparsers.add_parser(
        "discovery-audit",
        help="Check public source registers and discovery questions for integrity.",
    )
    discovery_parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Local repository path containing the data/ registers.",
    )
    discovery_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output folder for discovery_audit.json.",
    )
    discovery_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when any finding is present.",
    )

    research_parser = subparsers.add_parser(
        "research",
        help="Validate a private hypothesis research program without promoting claims.",
    )
    research_subparsers = research_parser.add_subparsers(
        dest="research_command",
        required=True,
    )
    research_validate_parser = research_subparsers.add_parser(
        "validate",
        help="Write a private, path-free validation receipt for a manifest and register.",
    )
    research_validate_parser.add_argument("--manifest", required=True, type=Path)
    research_validate_parser.add_argument("--register", required=True, type=Path)
    research_validate_parser.add_argument("--out", required=True, type=Path)
    research_validate_parser.add_argument(
        "--private-root",
        required=True,
        type=Path,
        help="Existing private root that must contain the output directory.",
    )
    research_validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 unless every promotion gate is ready for independent review.",
    )

    boundary_parser = subparsers.add_parser(
        "boundary-audit",
        help="Audit tracked text, paths, and remotes for forbidden project coupling.",
    )
    boundary_parser.add_argument("--repo", type=Path, default=Path("."))
    boundary_parser.add_argument("--out", required=True, type=Path)
    boundary_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when a forbidden reference is present.",
    )
    evidence_parser = subparsers.add_parser(
        "evidence",
        help="Validate or normalize an offline, user-owned evidence envelope.",
    )
    evidence_subparsers = evidence_parser.add_subparsers(
        dest="evidence_command",
        required=True,
    )
    evidence_validate_parser = evidence_subparsers.add_parser(
        "validate",
        help="Validate one local evidence envelope without writing output.",
    )
    evidence_validate_parser.add_argument("--input", required=True, type=Path)
    evidence_import_parser = evidence_subparsers.add_parser(
        "import-capture",
        help="Normalize an explicitly captured or exported local evidence envelope.",
    )
    evidence_import_parser.add_argument("--input", required=True, type=Path)
    evidence_import_parser.add_argument("--out", required=True, type=Path)

    claims_parser = subparsers.add_parser(
        "claims",
        help="Build a human-reviewed claim/evidence graph from local envelopes.",
    )
    claims_subparsers = claims_parser.add_subparsers(
        dest="claims_command",
        required=True,
    )
    claims_build_parser = claims_subparsers.add_parser(
        "build",
        help="Build a graph preserving support, contradiction, and context edges.",
    )
    claims_build_parser.add_argument("--evidence-dir", required=True, type=Path)
    claims_build_parser.add_argument("--claims", required=True, type=Path)
    claims_build_parser.add_argument("--out", required=True, type=Path)

    bridge_parser = subparsers.add_parser(
        "bridge",
        help="Validate public-safe receipts from a separately reviewed private pipeline.",
    )
    bridge_subparsers = bridge_parser.add_subparsers(
        dest="bridge_command",
        required=True,
    )
    bridge_validate_parser = bridge_subparsers.add_parser(
        "validate-receipt",
        help="Validate one closed-schema public projection receipt without reading sources.",
    )
    bridge_validate_parser.add_argument("--input", required=True, type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the AAVE CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        scan_result = scan_archive(
            input_directory=args.input,
            config_path=args.config,
            output_directory=args.out,
        )
        print(f"Scanned {scan_result.file_count} files.")
        print(f"Wrote {scan_result.output_directory}")
        return 0

    if args.command == "parse-gedcom":
        parse_result = parse_gedcom_file(
            gedcom_path=args.gedcom,
            output_directory=args.out,
        )
        print(
            f"Parsed {parse_result.person_count} people "
            f"and {parse_result.family_count} families."
        )
        print(f"Wrote {parse_result.output_directory}")
        return 0

    if args.command == "link":
        linking_result = link_sources(
            manifest_path=args.manifest,
            people_path=args.people,
            config_path=args.config,
            output_directory=args.out,
        )
        print(
            f"Linked {linking_result.linked_count} of {linking_result.link_count} artifacts; "
            f"{linking_result.needs_review_count} need review."
        )
        print(f"Wrote {linking_result.output_directory}")
        return 0

    if args.command == "export":
        export_result = export_bundle(
            profile=args.profile,
            output_directory=args.out,
            manifest_path=args.manifest,
            people_path=args.people,
            links_path=args.links,
            is_dry_run=args.dry_run,
        )
        print(
            f"Exported {export_result.exported_count} rows for {export_result.profile}; "
            f"excluded {export_result.excluded_count} rows."
        )
        print(f"Wrote {export_result.output_directory}")
        return 0

    if args.command == "inspect-archives":
        inspection_result = inspect_archive_formats(
            manifest_path=args.manifest,
            output_directory=args.out,
        )
        print(f"Inspected {inspection_result.inspected_count} archive-format files.")
        print(f"Wrote {inspection_result.output_directory}")
        return 0

    if args.command == "packet":
        packet_result = generate_packet(
            person_id=args.person,
            output_directory=args.out,
            profile=args.profile,
            people_path=args.people,
            families_path=args.families,
            manifest_path=args.manifest,
            links_path=args.links,
            config_path=args.config,
        )
        print(f"Wrote packet {packet_result.markdown_path}")
        print(f"Wrote sources {packet_result.sources_csv_path}")
        return 0

    if args.command == "inspect-zip":
        zip_result = inspect_zip_archive(
            zip_path=args.zip,
            output_directory=args.out,
            config_path=args.config,
            people_path=args.people,
        )
        print(
            f"Inspected {zip_result.member_count} ZIP members; "
            f"{zip_result.linked_member_count} associated with people."
        )
        print(f"Wrote {zip_result.output_directory}")
        return 0

    if args.command == "genome":
        if args.genome_command == "parse-ancestrydna":
            genome_result = parse_ancestrydna_file(
                input_path=args.input,
                whitelist_path=args.whitelist,
                output_directory=args.out,
            )
            print(
                f"Parsed {genome_result.rows_read} rows; "
                f"{genome_result.hit_count} whitelist hits and "
                f"{genome_result.missing_count} missing/not tested."
            )
            print(f"Wrote controlled local outputs to {genome_result.output_directory}")
            return 0
        if args.genome_command == "crossref":
            crossref_result = crossref_snp_hits(
                hits_path=args.hits,
                whitelist_path=args.whitelist,
                output_directory=args.out,
            )
            print(
                f"Annotated {crossref_result.annotated_count} of "
                f"{crossref_result.hit_count} local SNP hits."
            )
            print(f"Wrote controlled local outputs to {crossref_result.output_directory}")
            return 0

    if args.command == "integrations":
        if args.integration_command == "archivebox":
            integration_result = build_archivebox_dry_run(
                output_directory=args.out,
                enabled=args.enable,
                mode=args.mode,
            )
        elif args.integration_command == "zotero":
            integration_result = build_zotero_dry_run(
                output_directory=args.out,
                manifest_path=args.manifest,
                enabled=args.enable,
            )
        elif args.integration_command == "perma":
            integration_result = build_perma_dry_run(
                output_directory=args.out,
                enabled=args.enable,
            )
        elif args.integration_command == "static-site":
            integration_result = build_static_site_dry_run(
                output_directory=args.out,
                export_manifest_path=args.export_manifest,
                enabled=args.enable,
            )
        else:
            parser.error(f"Unknown integrations command: {args.integration_command}")
            return 2

        print(
            f"Wrote {integration_result.connector} dry-run payload "
            f"with {integration_result.payload_count} prepared rows."
        )
        print(f"Wrote {integration_result.output_path}")
        return 0

    if args.command == "discovery-audit":
        discovery_result = audit_source_registers(
            repository_path=args.repo,
            output_directory=args.out,
        )
        print(
            f"Audited {discovery_result['declared_sources']} declared sources and "
            f"{discovery_result['declared_questions']} discovery question(s); "
            f"{discovery_result['finding_count']} finding(s)."
        )
        print(f"Registers ready: {str(discovery_result['registers_ready']).lower()}")
        for finding in (
            discovery_result["register_findings"] + discovery_result["question_findings"]
        ):
            print(f"  {finding['file']} {finding['record_id']} {finding['field']}: "
                  f"{finding['problem']}")
        if args.strict and not discovery_result["registers_ready"]:
            return 1
        return 0

    if args.command == "research":
        if args.research_command == "validate":
            try:
                research_result = validate_research_program(
                    manifest_path=args.manifest,
                    register_path=args.register,
                    output_directory=args.out,
                    private_root=args.private_root,
                )
            except (OSError, ResearchProgramValidationError):
                print(
                    "Research validation failed without exposing input paths or values.",
                    file=sys.stderr,
                )
                return 1
            print(
                f"Research validation status: {research_result.status}; "
                f"{research_result.hypothesis_count} hypotheses; "
                f"{research_result.finding_count} findings."
            )
            print(f"Wrote private receipt {research_result.output_path.name}")
            if args.strict and not research_result.promotion_ready:
                return 1
            return 0

    if args.command == "boundary-audit":
        boundary_result = audit_research_boundary(
            repository_path=args.repo,
            output_directory=args.out,
        )
        print(
            f"Scanned {boundary_result.scanned_file_count} text files; "
            f"{boundary_result.finding_count} forbidden references."
        )
        print(f"Boundary ready: {str(boundary_result.boundary_ready).lower()}")
        print(f"Wrote {boundary_result.output_path}")
        if args.strict and not boundary_result.boundary_ready:
            return 1
        return 0
    if args.command == "privacy-audit":
        audit_result = audit_repository_privacy(
            repository_path=args.repo,
            output_directory=args.out,
        )
        print(
            f"Audited {audit_result.tracked_path_count} tracked paths; "
            f"{audit_result.flagged_path_count} flagged."
        )
        print(f"Publish ready: {str(audit_result.publish_ready).lower()}")
        print(f"Wrote {audit_result.output_directory}")
        if args.strict and not audit_result.publish_ready:
            return 1
        return 0

    if args.command == "evidence":
        if args.evidence_command == "validate":
            envelope_payload = load_json_object(args.input)
            validate_evidence_envelope(envelope_payload)
            print(f"Valid evidence envelope: {envelope_payload['envelope_id']}")
            return 0
        if args.evidence_command == "import-capture":
            import_result = import_evidence_envelope(
                input_path=args.input,
                output_directory=args.out,
            )
            print(f"Imported evidence envelope {import_result.envelope_id}.")
            print(f"Wrote reviewed envelope {import_result.private_envelope_path}")
            print(f"Wrote public preview {import_result.public_preview_path}")
            return 0

    if args.command == "claims" and args.claims_command == "build":
        graph_result = build_claim_graph(
            evidence_directory=args.evidence_dir,
            claims_path=args.claims,
            output_directory=args.out,
        )
        print(
            f"Built claim graph with {graph_result.claim_count} claims, "
            f"{graph_result.evidence_count} evidence nodes, and "
            f"{graph_result.edge_count} edges."
        )
        print(f"Wrote {graph_result.output_path}")
        return 0

    if args.command == "bridge" and args.bridge_command == "validate-receipt":
        load_public_projection_receipt(args.input)
        print("Valid public projection receipt.")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
