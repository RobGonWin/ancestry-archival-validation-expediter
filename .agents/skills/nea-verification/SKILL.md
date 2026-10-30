---
name: nea-verification
description: Resolve NEA recipient identities, historical age bounds, ensemble memberships and memorial evidence in resumable verification slices. Use for roster-wide research and ranking closure, with separate private family-record reconciliation.
---

# NEA verification

Use the canonical roster and existing source ledger before searching. Preserve distinct award and person IDs; an award to an ensemble is not a resolved person universe. This workflow applies to any recipient or comparison subject.

Choose the slice needed for the current blocker:

- Identity, dates, age bounds, or ranking: read [age-and-identity.md](references/age-and-identity.md).
- Stale death caps, Wikipedia/WikiTree leads or comparison-table corrections: read [the tiered correction and provider checklist](../exa-public-search/references/person-records.md#tiered-age-correction-and-ranking-replay).
- Source search or burial evidence: read [discovery-and-memorials.md](references/discovery-and-memorials.md).
- Locally supplied obituary, census, or tree reconciliation: read [private-records.md](references/private-records.md).

Before retrieval, compute a fingerprint with `nea_archiver.nea_verification.slice_fingerprint`: include input hashes, predecessor decision hashes, cutoff and rules version. Reuse completed or blocked slices while that fingerprint matches. A new source, corrected identity, changed cutoff or explicit access-state revision reopens the affected slice; unrelated slices stay reusable. Persist `slice_id`, fingerprint, status, source roles, decision and blockers using `save_slice`. A completed search may still leave its historical claim unresolved.

Use `nea-archiver nea all --offline --out <local output>` for deterministic replay. Local extraction requires `--out` beneath `local-vault`. Search queries are plans until an explicitly enabled host adapter executes them. No browser/platform access or publication is authorized by this skill.

Stop a slice after its bounded retrieval/retry budget, preserve the next actionable lead, and continue independent unresolved slices. Never convert a missing result into a negative historical fact. Use synthetic tests for arithmetic, identity conflicts, privacy boundaries and resumption; follow the project's independent-checker requirement before accepting ranking closure.
