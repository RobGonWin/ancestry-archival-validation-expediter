#!/usr/bin/env python3
"""Create a transparent Fermi interval for a rare-cohort scenario."""

from __future__ import annotations

import argparse
import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ALLOWED_EVIDENCE_LEVELS = {"observed", "derived", "assumption"}
ALLOWED_INDEPENDENCE = {"independent", "overlapping", "unknown"}
DISALLOWED_FACTOR_ROLES = {
    "ace_exposure",
    "event_presence",
    "genetic_memory",
    "memory_accuracy",
    "recollection_accuracy",
}


class ScenarioError(ValueError):
    """Raised when a cohort scenario would produce an unsafe or opaque estimate."""


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ScenarioError(f"{label} must be numeric") from exc
    if not result.is_finite():
        raise ScenarioError(f"{label} must be finite")
    return result


def _interval(
    item: dict[str, Any], label: str, maximum: Decimal | None = None
) -> tuple[Decimal, Decimal]:
    low = _decimal(item.get("low"), f"{label}.low")
    high = _decimal(item.get("high"), f"{label}.high")
    if low < 0 or high < low:
        raise ScenarioError(f"{label} requires 0 <= low <= high")
    if maximum is not None and high > maximum:
        raise ScenarioError(f"{label}.high must be <= {maximum}")
    return low, high


def _require_source_url(item: dict[str, Any], label: str) -> None:
    url = item.get("source_url")
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise ScenarioError(f"{label}.source_url must be an HTTP(S) URL")


def _generation_matches(payload: dict[str, Any]) -> list[dict[str, str]]:
    birth_year = payload.get("birth_year")
    if birth_year is None:
        return []
    if not isinstance(birth_year, int):
        raise ScenarioError("birth_year must be an integer")

    matches: list[dict[str, str]] = []
    for index, convention in enumerate(payload.get("generation_conventions", [])):
        label = f"generation_conventions[{index}]"
        _require_source_url(convention, label)
        name = convention.get("convention")
        ranges = convention.get("ranges")
        if not isinstance(name, str) or not isinstance(ranges, list):
            raise ScenarioError(f"{label} requires convention and ranges")
        for range_index, cohort in enumerate(ranges):
            start = cohort.get("start_year")
            end = cohort.get("end_year")
            cohort_name = cohort.get("label")
            if not isinstance(start, int) or not isinstance(end, int) or start > end:
                raise ScenarioError(f"{label}.ranges[{range_index}] has an invalid year range")
            if not isinstance(cohort_name, str):
                raise ScenarioError(f"{label}.ranges[{range_index}].label is required")
            if start <= birth_year <= end:
                matches.append(
                    {
                        "convention": name,
                        "label": cohort_name,
                        "source_url": convention["source_url"],
                    }
                )
    return matches


def estimate_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    base = payload.get("base_population")
    if not isinstance(base, dict):
        raise ScenarioError("base_population is required")
    _require_source_url(base, "base_population")
    base_low, base_high = _interval(base, "base_population")

    factors = payload.get("factors")
    if not isinstance(factors, list) or not factors:
        raise ScenarioError("at least one factor is required")

    product_low = Decimal("1")
    product_high = Decimal("1")
    warnings: list[str] = []
    factor_summary: list[dict[str, Any]] = []

    for index, factor in enumerate(factors):
        if not isinstance(factor, dict):
            raise ScenarioError(f"factors[{index}] must be an object")
        label = f"factors[{index}]"
        _require_source_url(factor, label)
        factor_id = factor.get("id")
        role = factor.get("role")
        level = factor.get("evidence_level")
        independence = factor.get("independence")
        if not isinstance(factor_id, str) or not factor_id:
            raise ScenarioError(f"{label}.id is required")
        if role in DISALLOWED_FACTOR_ROLES:
            raise ScenarioError(f"{factor_id} uses prohibited numeric role {role}")
        if level not in ALLOWED_EVIDENCE_LEVELS:
            raise ScenarioError(f"{factor_id} has invalid evidence_level")
        if independence not in ALLOWED_INDEPENDENCE:
            raise ScenarioError(f"{factor_id} has invalid independence")
        low, high = _interval(factor, label, Decimal("1"))
        product_low *= low
        product_high *= high
        factor_summary.append(
            {
                "id": factor_id,
                "role": role,
                "low": float(low),
                "high": float(high),
                "evidence_level": level,
                "independence": independence,
                "source_url": factor["source_url"],
            }
        )
        if level == "assumption":
            warnings.append(f"{factor_id} is an assumption, not an observed rate")
        if independence != "independent":
            warnings.append(
                f"{factor_id} may overlap other factors; multiplication can overstate precision"
            )

    raw_low = base_low * product_low
    raw_high = base_high * product_high
    return {
        "schema_version": "aave.likely-cohort-estimate/1.0",
        "scenario_id": payload.get("scenario_id", "unnamed-scenario"),
        "estimate_type": "fermi_sensitivity_interval_not_registry_count",
        "birth_year": payload.get("birth_year"),
        "generation_matches": _generation_matches(payload),
        "base_population": {
            "low": float(base_low),
            "high": float(base_high),
            "source_url": base["source_url"],
        },
        "factors": factor_summary,
        "raw_interval": {"low": float(raw_low), "high": float(raw_high)},
        "integer_display_interval": {
            "low": math.floor(raw_low),
            "high": math.ceil(raw_high),
        },
        "warnings": sorted(set(warnings)),
        "statement": (
            "This is a scenario estimate. It does not identify people, prove uniqueness, "
            "or establish event attendance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path, help="JSON scenario using public or synthetic aggregates"
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = estimate_scenario(payload)
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
