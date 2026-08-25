"""Local repository privacy preflight checks for safe publication workflows."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from aave.models import PrivacyAuditResult


@dataclass(frozen=True)
class SensitivePathRule:
    """One path-based privacy audit rule."""

    rule_id: str
    description: str
    severity: str


SENSITIVE_PATH_RULES = [
    SensitivePathRule(
        rule_id="raw_dna_file",
        description="Raw DNA/genotype files must not be tracked or published.",
        severity="blocker",
    ),
    SensitivePathRule(
        rule_id="genealogy_export",
        description="Real GEDCOM exports must stay outside the public repository.",
        severity="blocker",
    ),
    SensitivePathRule(
        rule_id="private_archive_bundle",
        description="Private ZIP/WARC/WACZ archive bundles require explicit review.",
        severity="review",
    ),
    SensitivePathRule(
        rule_id="secret_or_environment_file",
        description="Secrets and local environment files must not be tracked.",
        severity="blocker",
    ),
    SensitivePathRule(
        rule_id="local_output_folder",
        description="Generated local outputs should not be published accidentally.",
        severity="review",
    ),
    SensitivePathRule(
        rule_id="controlled_evidence_folder",
        description="Controlled evidence, account captures, and local vaults are not public.",
        severity="blocker",
    ),
    SensitivePathRule(
        rule_id="media_or_document_file",
        description="Media and document files require an explicit provenance and rights review.",
        severity="review",
    ),
]


def audit_repository_privacy(
    repository_path: Path,
    output_directory: Path,
) -> PrivacyAuditResult:
    """Audit tracked repository paths for publication-blocking sensitive filenames."""
    tracked_paths = list_tracked_paths(repository_path)
    findings = build_privacy_findings(tracked_paths)
    blocker_count = sum(1 for finding in findings if finding["severity"] == "blocker")
    review_count = sum(1 for finding in findings if finding["severity"] == "review")
    publish_ready = blocker_count == 0 and review_count == 0

    audit_payload = {
        "repository_path": str(repository_path),
        "tracked_path_count": len(tracked_paths),
        "flagged_path_count": len(findings),
        "blocker_count": blocker_count,
        "review_count": review_count,
        "publish_ready": publish_ready,
        "findings": findings,
        "notes": [
            "This audit checks tracked path names only and does not read sensitive file content.",
            "A clean audit does not prove content is public-safe; human review is still required.",
            (
                "Raw DNA files, genotypes, secrets, and private archive bundles must stay "
                "out of public repos."
            ),
        ],
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    write_json(audit_payload, output_directory / "privacy_audit.json")
    write_privacy_audit_report(audit_payload, output_directory / "privacy_audit_report.md")

    audit_result = PrivacyAuditResult(
        tracked_path_count=len(tracked_paths),
        flagged_path_count=len(findings),
        publish_ready=publish_ready,
        output_directory=output_directory,
    )
    return audit_result


def list_tracked_paths(repository_path: Path) -> list[str]:
    """Return tracked Git paths without reading file contents."""
    completed_process = subprocess.run(
        ["git", "ls-files"],
        cwd=repository_path,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_paths = [
        path.strip().replace("\\", "/")
        for path in completed_process.stdout.splitlines()
        if path.strip()
    ]
    return sorted(tracked_paths)


def build_privacy_findings(tracked_paths: list[str]) -> list[dict[str, str]]:
    """Build path-only privacy findings for tracked files."""
    findings: list[dict[str, str]] = []
    for tracked_path in tracked_paths:
        for rule in SENSITIVE_PATH_RULES:
            if does_path_match_rule(tracked_path, rule):
                findings.append(
                    {
                        "path": tracked_path,
                        "rule_id": rule.rule_id,
                        "severity": rule.severity,
                        "description": rule.description,
                    }
                )
                break
    return findings


def does_path_match_rule(tracked_path: str, rule: SensitivePathRule) -> bool:
    """Return whether a tracked path matches a sensitive publication rule."""
    normalized_path = tracked_path.lower().replace("\\", "/")
    filename = Path(normalized_path).name
    suffix = Path(normalized_path).suffix

    if rule.rule_id == "raw_dna_file":
        dna_extensions = {".txt", ".csv", ".tsv", ".zip"}
        dna_filename_terms = (
            "ancestrydna",
            "ancestrydn",
            "ancestry-dna",
            "ancestry_dna",
            "dna-data",
            "dna_data",
            "rawdata",
            "raw-data",
            "raw_data",
            "raw_dna",
            "raw-dna",
            "genotype",
            "genotypes",
        )
        return suffix in dna_extensions and any(term in filename for term in dna_filename_terms)

    if rule.rule_id == "genealogy_export":
        synthetic_fixture = "tests/fixtures/sample_tree.synthetic.ged"
        return suffix in {".ged", ".gedcom"} and normalized_path != synthetic_fixture

    if rule.rule_id == "private_archive_bundle":
        archive_suffixes = (".zip", ".warc", ".wacz", ".7z", ".rar")
        return normalized_path.endswith(archive_suffixes)

    if rule.rule_id == "secret_or_environment_file":
        if filename == ".env.example":
            return False
        secret_suffixes = (".pem", ".key", ".p12", ".pfx")
        return (
            filename == ".env"
            or filename.startswith(".env.")
            or filename.endswith(secret_suffixes)
        )

    if rule.rule_id == "local_output_folder":
        output_parts = {"out", "outputs", "exports", "packets", "genome-output"}
        return any(part in output_parts for part in Path(normalized_path).parts)

    if rule.rule_id == "controlled_evidence_folder":
        controlled_parts = {
            "account-captures",
            "browser-captures",
            "local-vault",
            "raw",
            "raw-data",
            "raw-vault",
            "private-archive",
            "private_archive",
            "private-evidence",
        }
        return any(part in controlled_parts for part in Path(normalized_path).parts)

    if rule.rule_id == "media_or_document_file":
        review_suffixes = (
            ".avi",
            ".heic",
            ".jpeg",
            ".jpg",
            ".mkv",
            ".mov",
            ".mp4",
            ".pdf",
            ".png",
            ".tif",
            ".tiff",
            ".webp",
        )
        return normalized_path.endswith(review_suffixes)

    return False


def write_json(data: object, output_path: Path) -> None:
    """Write stable formatted JSON."""
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(data, output_file, indent=2)
        output_file.write("\n")


def write_privacy_audit_report(audit_payload: dict[str, object], output_path: Path) -> None:
    """Write a Markdown publication preflight report."""
    findings = audit_payload["findings"]
    assert isinstance(findings, list)
    lines = [
        "# Privacy Audit Report",
        "",
        "This is a local path-only publication preflight. It does not read file contents.",
        "",
        "## Summary",
        "",
        f"- Tracked paths checked: {audit_payload['tracked_path_count']}",
        f"- Flagged paths: {audit_payload['flagged_path_count']}",
        f"- Blockers: {audit_payload['blocker_count']}",
        f"- Review items: {audit_payload['review_count']}",
        f"- Publish ready: `{str(audit_payload['publish_ready']).lower()}`",
        "",
        "## Findings",
        "",
    ]
    if findings:
        for finding in findings:
            assert isinstance(finding, dict)
            lines.append(
                "- "
                f"`{finding['path']}` "
                f"({finding['severity']}, {finding['rule_id']}): "
                f"{finding['description']}"
            )
    else:
        lines.append("No sensitive tracked path names were detected.")

    lines.extend(
        [
            "",
            "## Required Human Review",
            "",
            "- Confirm README commands match implemented CLI behavior.",
            (
                "- Confirm public exports contain no raw DNA, genotypes, private notes, "
                "or living-person data."
            ),
            (
                "- Confirm no institutional endorsement, medical, diagnostic, or health "
                "claims are made."
            ),
            (
                "- Confirm optional integrations remain disabled unless explicitly enabled "
                "and dry-run reviewed."
            ),
        ]
    )
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))
        output_file.write("\n")
