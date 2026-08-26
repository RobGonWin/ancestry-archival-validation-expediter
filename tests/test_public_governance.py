from __future__ import annotations

import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COPYRIGHT_HOLDER = "RobGonWin and AAVE contributors"
LOCAL_SKILLS = ("contribute-to-aave", "review-aave-contributions")


def _skill_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    frontmatter, body = text[4:].split("\n---\n", 1)
    fields = dict(line.split(":", 1) for line in frontmatter.splitlines())
    assert body.strip()
    return {key.strip(): value.strip() for key, value in fields.items()}


def test_repository_uses_standard_mit_license_everywhere() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
    release_policy = (ROOT / "configs" / "public_release_policy.yaml").read_text(
        encoding="utf-8"
    )

    assert license_text.startswith("MIT License\n")
    assert f"Copyright (c) 2026 {COPYRIGHT_HOLDER}" in license_text
    assert "Permission is hereby granted, free of charge" in license_text
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in license_text
    assert pyproject["project"]["license"] == {"text": "MIT"}
    assert pyproject["project"]["authors"] == [{"name": COPYRIGHT_HOLDER}]
    assert project["license"] == {"spdx": "MIT", "state": "open-source"}
    assert "license_status: MIT\n" in release_policy
    assert "all_rights_reserved" not in release_policy


def test_contribution_terms_preserve_rights_and_public_boundary() -> None:
    terms = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    for required in (
        "retain copyright",
        "licensed under the repository's\nMIT License",
        "original work",
        "synthetic test",
        "not affiliated with Slop.cash",
        "no claimed eligibility",
        "no promise",
        "only to contributions to AAVE",
    ):
        assert required in terms


def test_aave_contribution_skills_have_valid_local_structure() -> None:
    for skill_name in LOCAL_SKILLS:
        path = ROOT / ".agents" / "skills" / skill_name / "SKILL.md"
        fields = _skill_frontmatter(path)

        assert fields["name"] == skill_name
        assert fields["description"]
        text = path.read_text(encoding="utf-8")
        assert "CONTRIBUTING.md" in text
        assert "this AAVE repository" in text


def test_cross_agent_compatibility_is_local_and_prerelease_cautious() -> None:
    guide = (ROOT / "docs" / "AGENT_SKILLS_COMPATIBILITY.md").read_text(
        encoding="utf-8"
    )

    assert "`.agents/skills/` is AAVE's canonical skill directory" in guide
    assert "@elizaos/plugin-agent-skills@2.0.3-beta.7" in guide
    assert "SKILLS_DIR=.agents/skills" in guide
    assert "automatic local skill loading: true" in guide
    assert "remote catalog synchronization: false" in guide
    assert "not a runtime\ncertification" in guide
    assert "no runnable Eliza app" in guide


def test_evidence_envelope_uses_supported_privacy_audit_command() -> None:
    guide = (ROOT / "docs" / "evidence-envelope.md").read_text(encoding="utf-8")

    assert "aave privacy-audit --repo . --out .\\out\\boundary --strict" in guide
    assert "boundary-audit" not in guide


def test_slop_track_map_is_conceptual_only_and_not_submitted() -> None:
    mapping = json.loads((ROOT / "slop-track-map.json").read_text(encoding="utf-8"))
    assessment = mapping["assessment"]
    tracks = {track["id"]: track for track in mapping["tracks"]}

    assert assessment == {
        "kind": "informational-conceptual-fit",
        "source": "self-assessed",
        "submission": "not-submitted",
        "affiliation": "none",
        "authority": "none",
        "eligibility": "not-claimed",
        "rewards": "not-promised",
        "planned_contribution": "none",
    }
    assert tracks["eliza"]["conceptual_fit"] == "primary"
    assert tracks["asi"]["conceptual_fit"] == "secondary"
    assert tracks["delta-star"]["conceptual_fit"] == "not-applicable"
    assert all(track["contribution_status"] == "none" for track in tracks.values())

    # The prose companion was removed; the boundary guarantee it carried is
    # asserted against the machine-readable map so nothing is weakened.
    boundary = mapping["boundary"]
    assert "not an application, affiliation, eligibility claim" in boundary
    assert "contribution plan" in boundary
    assert mapping["separate_preparation"]["relationship_to_aave"] == "none"
    assert (
        mapping["separate_preparation"]["status"]
        == "no upstream contribution has been made, submitted, or authorized"
    )
