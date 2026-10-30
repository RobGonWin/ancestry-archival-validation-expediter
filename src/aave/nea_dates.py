"""Conservative calendar intervals for historical recipient screening."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

DEFAULT_CUTOFF = date(2026, 10, 23)


@dataclass(frozen=True)
class DateInterval:
    """Inclusive earliest/latest dates; partial dates remain intervals."""

    earliest: date
    latest: date


def parse_date_interval(value: str) -> DateInterval:
    """Parse exact ISO, year-month, year, or explicit inclusive year range.

    Approximate words are rejected: their uncertainty needs a reviewed interval.
    """
    if re.fullmatch(r"\d{4}", value):
        year = int(value)
        interval = DateInterval(date(year, 1, 1), date(year, 12, 31))
    elif re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = map(int, value.split("-"))
        interval = DateInterval(date(year, month, 1),
                                date(year, month, calendar.monthrange(year, month)[1]))
    elif re.fullmatch(r"\d{4}/\d{4}", value):
        first, last = map(int, value.split("/"))
        interval = DateInterval(date(first, 1, 1), date(last, 12, 31))
    else:
        exact = date.fromisoformat(value)
        interval = DateInterval(exact, exact)
    if interval.earliest > interval.latest:
        raise ValueError("Date interval is reversed")
    return interval


def attained_age(birth: date, endpoint: date) -> tuple[int, int]:
    """Return completed years and days; use February 28 for leap-day anniversaries."""
    if endpoint < birth:
        raise ValueError("Age endpoint precedes birth")
    years = endpoint.year - birth.year
    anniversary = date(endpoint.year, birth.month,
                       min(birth.day, calendar.monthrange(endpoint.year, birth.month)[1]))
    if anniversary > endpoint:
        years -= 1
        anniversary = date(endpoint.year - 1, birth.month,
                           min(birth.day, calendar.monthrange(endpoint.year - 1, birth.month)[1]))
    additional_days = (endpoint - anniversary).days
    return years, additional_days


def age_label(age: tuple[int, int]) -> str:
    """Format a calendar age without implying date validation."""
    label = f"{age[0]} years, {age[1]} days"
    return label


def compare_age(birth: DateInterval, death: DateInterval | None,
                cutoff: date = DEFAULT_CUTOFF) -> dict:
    """Bound age at min(death, cutoff); compare calendar years/days, not elapsed days.

    Total elapsed days can differ across birth cohorts with different leap days.
    No result predicts the eventual lifespan of a living person.
    """
    endpoint = min(death.latest, cutoff) if death else cutoff
    upper = attained_age(birth.earliest, endpoint)
    reference = (107, 307)
    is_exact = (birth.earliest == birth.latest and death is not None
                and death.earliest == death.latest and death.latest <= cutoff)
    if upper < reference:
        status = "verified_below_roma" if is_exact else "bounded_below_roma_at_cutoff"
    elif is_exact:
        status = "verified_equal_roma" if upper == reference else "verified_above_roma"
    else:
        status = "possible_competitor"
    result = {"status": status, "upper_age": list(upper), "upper_age_calendar": age_label(upper),
              "endpoint": endpoint.isoformat(), "cutoff": cutoff.isoformat(),
              "completed_lifespan_documented": is_exact, "future_lifespan": "not_inferred"}
    return result
