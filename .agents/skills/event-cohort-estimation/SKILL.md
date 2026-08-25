---
name: event-cohort-estimation
description: Build or review privacy-safe scenario estimates for rare intergenerational encounters and assess event-presence evidence without turning demographic opportunity, kinship, or recollection into proof of attendance.
---

# Estimate cohorts and assess event presence

Use only public aggregate data or a separately sanitized synthetic projection.

1. Define the event date, birth-year cohort, geography, relationship scope, and age threshold before selecting data.
2. Prefer raw birth years over generation labels. If a label is useful, record the named convention and URL; do not merge Pew, Census, or McCrindle boundaries.
3. Put every numeric filter in a scenario file with a low bound, high bound, evidence level, independence assessment, and source URL.
4. Run `python scripts/estimate_likely_cohort.py <scenario.json> --pretty`.
5. Report the result as a sensitivity interval or Fermi estimate, never as a registry count or a claim of uniqueness.
6. Classify presence evidence with `python scripts/assess_present_during_event.py <evidence.json> --pretty`.
7. Treat census co-residence, date overlap, kinship, geography, and a public event scene as `opportunity_context` only. They cannot identify an attendee.
8. A recollection remains `reported` unless independently corroborated. Infant-memory, ACE, or familial-longevity research must never be used as a numeric accuracy multiplier.
9. Require human review of direct media authentication, a claimed complete roster, contradictions, and any transition to `confirmed`.
10. Stop if the input contains a real name, address, account export, raw DNA, private transcript, private media path, or other living-person identifier.
