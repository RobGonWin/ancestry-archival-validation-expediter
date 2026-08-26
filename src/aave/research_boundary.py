"""Repository boundary checks for isolated personal-research projects."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_REPOSITORY_TERMS = (
    "1v1" + "-edit-arena",
    "1v1" + " edit arena",
    "doolittle-" + "1v1-arena",
)
TEXT_SUFFIXES = {
    ".bat",
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
MAX_TEXT_FILE_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class ResearchBoundaryAuditResult:
    """Summary of a local repository isolation audit."""

    scanned_file_count: int
    finding_count: int
    boundary_ready: bool
    output_path: Path


def audit_research_boundary(
    repository_path: Path,
    output_directory: Path,
) -> ResearchBoundaryAuditResult:
    """Reject forbidden repository references in tracked text, paths, or remotes."""
    tracked_paths = list_tracked_or_local_paths(repository_path)
    findings: list[dict[str, str]] = []
    scanned_file_count = 0

    for relative_path in tracked_paths:
        normalized_path = str(relative_path).replace("\\", "/")
        path_finding = find_forbidden_term(normalized_path)
        if path_finding:
            findings.append(
                {
                    "location": normalized_path,
                    "kind": "tracked_path",
                    "term": path_finding,
                }
            )

        file_path = repository_path / relative_path
        if not should_scan_text_file(file_path):
            continue
        scanned_file_count += 1
        try:
            file_text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        content_finding = find_forbidden_term(file_text)
        if content_finding:
            findings.append(
                {
                    "location": normalized_path,
                    "kind": "file_content",
                    "term": content_finding,
                }
            )

    for remote_line in list_git_remotes(repository_path):
        remote_finding = find_forbidden_term(remote_line)
        if remote_finding:
            findings.append(
                {
                    "location": "git remote -v",
                    "kind": "remote",
                    "term": remote_finding,
                }
            )

    boundary_ready = not findings
    payload = {
        "repository_path": str(repository_path),
        "scanned_file_count": scanned_file_count,
        "finding_count": len(findings),
        "boundary_ready": boundary_ready,
        "findings": findings,
        "policy": {
            "external_uploads": "not_implemented",
            "upstream_pull_requests": "not_implemented",
            "forbidden_repository_isolation": "required",
        },
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / "research_boundary_audit.json"
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(payload, output_file, indent=2)
        output_file.write("\n")
    return ResearchBoundaryAuditResult(
        scanned_file_count=scanned_file_count,
        finding_count=len(findings),
        boundary_ready=boundary_ready,
        output_path=output_path,
    )


def list_tracked_or_local_paths(repository_path: Path) -> list[Path]:
    """List tracked paths, falling back to local files for an uninitialized scaffold."""
    completed_process = subprocess.run(
        ["git", "ls-files"],
        cwd=repository_path,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed_process.returncode == 0:
        return sorted(
            Path(line.strip())
            for line in completed_process.stdout.splitlines()
            if line.strip()
        )

    ignored_directory_names = {".git", ".pytest_cache", ".ruff_cache", "__pycache__"}
    return sorted(
        file_path.relative_to(repository_path)
        for file_path in repository_path.rglob("*")
        if file_path.is_file()
        and not any(part in ignored_directory_names for part in file_path.parts)
    )


def list_git_remotes(repository_path: Path) -> list[str]:
    """Return configured Git remote lines, or an empty list outside a Git repository."""
    completed_process = subprocess.run(
        ["git", "remote", "-v"],
        cwd=repository_path,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed_process.returncode != 0:
        return []
    return [line.strip() for line in completed_process.stdout.splitlines() if line.strip()]


def should_scan_text_file(file_path: Path) -> bool:
    """Return whether a small local file is safe and useful for a boundary text scan."""
    try:
        file_size = file_path.stat().st_size
    except FileNotFoundError:
        return False
    return file_size <= MAX_TEXT_FILE_BYTES and file_path.suffix.lower() in TEXT_SUFFIXES


def find_forbidden_term(text: str) -> str | None:
    """Return the first forbidden repository term found in case-insensitive text."""
    normalized_text = text.lower()
    for forbidden_term in FORBIDDEN_REPOSITORY_TERMS:
        if forbidden_term in normalized_text:
            return forbidden_term
    return None
