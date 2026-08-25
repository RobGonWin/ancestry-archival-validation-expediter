"""Small filesystem utilities for local archive processing."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path


def iter_files(input_directory: Path, excluded_directory_names: set[str]) -> list[Path]:
    """Return local files in deterministic relative path order."""
    file_paths: list[Path] = []
    for file_path in input_directory.rglob("*"):
        if should_skip_path(file_path, excluded_directory_names):
            continue
        if file_path.is_file():
            file_paths.append(file_path)

    sorted_file_paths = sorted(
        file_paths,
        key=lambda path: path.relative_to(input_directory).as_posix(),
    )
    return sorted_file_paths


def should_skip_path(path: Path, excluded_directory_names: set[str]) -> bool:
    """Return whether a path is inside an excluded directory name."""
    should_skip = any(path_part in excluded_directory_names for path_part in path.parts)
    return should_skip


def calculate_sha256(file_path: Path) -> str:
    """Calculate a SHA-256 digest for a local file."""
    digest = hashlib.sha256()
    with file_path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)

    sha256 = digest.hexdigest()
    return sha256


def format_modified_time(timestamp: float) -> str:
    """Format a filesystem timestamp as a UTC ISO-8601 string."""
    modified_time = datetime.fromtimestamp(timestamp, tz=UTC)
    modified_time_iso = modified_time.isoformat()
    return modified_time_iso
