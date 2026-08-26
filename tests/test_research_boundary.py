from __future__ import annotations

import json
from pathlib import Path

from aave.research_boundary import audit_research_boundary


def test_boundary_audit_passes_isolated_scaffold(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Synthetic isolated research repo.", encoding="utf-8")

    result = audit_research_boundary(tmp_path, tmp_path / "audit")

    assert result.boundary_ready is True
    assert result.finding_count == 0


def test_boundary_audit_blocks_forbidden_repository_reference(tmp_path: Path) -> None:
    forbidden_name = "1v1" + "-edit-arena"
    (tmp_path / "config.json").write_text(
        json.dumps({"dependency": f"https://example.invalid/{forbidden_name}"}),
        encoding="utf-8",
    )

    result = audit_research_boundary(tmp_path, tmp_path / "audit")

    assert result.boundary_ready is False
    assert result.finding_count == 1
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload["findings"][0]["kind"] == "file_content"
