"""Configuration loading for local archive scans."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aave.privacy import DEFAULT_PRIVACY_LABEL, DEFAULT_SOURCE_CONFIDENCE


@dataclass(frozen=True)
class AaveConfig:
    """Runtime configuration for conservative local archive processing."""

    default_privacy_label: str = DEFAULT_PRIVACY_LABEL
    default_source_confidence: str = DEFAULT_SOURCE_CONFIDENCE
    artifact_id_patterns: list[str] = field(default_factory=list)
    excluded_directory_names: list[str] = field(default_factory=lambda: [".git", "__pycache__"])
    manual_source_links: list[dict[str, Any]] = field(default_factory=list)
    packet_default_profile: str = "private_full"
    packet_citation_note: str = "Citation-ready notes require human review before publication."
    zip_member_contexts: list[dict[str, Any]] = field(default_factory=list)


def load_config(config_path: Path) -> AaveConfig:
    """Load a JSON config file and merge it with safe defaults."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file does not exist: {config_path}")

    with config_path.open("r", encoding="utf-8-sig") as config_file:
        raw_config = json.load(config_file)

    if not isinstance(raw_config, dict):
        raise ValueError("Config file must contain a JSON object.")

    config = build_config(raw_config)
    return config


def build_config(raw_config: dict[str, Any]) -> AaveConfig:
    """Build an ``AaveConfig`` from parsed JSON data."""
    config = AaveConfig(
        default_privacy_label=str(
            raw_config.get("default_privacy_label", DEFAULT_PRIVACY_LABEL)
        ),
        default_source_confidence=str(
            raw_config.get("default_source_confidence", DEFAULT_SOURCE_CONFIDENCE)
        ),
        artifact_id_patterns=list(raw_config.get("artifact_id_patterns", [])),
        excluded_directory_names=list(
            raw_config.get("excluded_directory_names", [".git", "__pycache__"])
        ),
        manual_source_links=list(raw_config.get("manual_source_links", [])),
        packet_default_profile=str(raw_config.get("packet_default_profile", "private_full")),
        packet_citation_note=str(
            raw_config.get(
                "packet_citation_note",
                "Citation-ready notes require human review before publication.",
            )
        ),
        zip_member_contexts=list(raw_config.get("zip_member_contexts", [])),
    )
    return config
