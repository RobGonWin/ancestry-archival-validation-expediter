# Privacy Model

AAVE is privacy-first by default. v0.6 creates local manifests, people indexes, source links, export manifests, archive-format metadata, and Markdown research packets. It does not publish files, copy source media into packets, parse raw DNA data, or infer living-person safety.

## Default Label

The default privacy label is:

```text
private_family_only
```

## Labels

- `public_ok`: suitable for public use after human review.
- `public_summary_only`: only a high-level summary should be public.
- `private_family_only`: limited to private family research contexts.
- `expert_review_only`: intended for limited review by trusted experts.
- `do_not_share`: should not be shared.
- `living_person_redacted`: living-person details must be redacted.
- `raw_dna_never_export`: raw DNA or genotype data that must never be publicly exported.

## Public Export And Packet Rules

Public exports and public packets must exclude living or potentially living people, raw DNA files, genotypes, private notes, `do_not_share` artifacts, and unverified personal recollections unless they are summarized safely.

Private packets may include sensitive non-DNA metadata for local private review, but raw DNA remains excluded by default.

## Hard Boundaries

AAVE must not bypass logins, CAPTCHAs, paywalls, DRM, or platform access controls. It must process only local user-owned files, user exports, saved pages, and explicitly supplied public materials.

AAVE must not make medical, diagnostic, health, fitness, longevity-deterministic, institutional endorsement, or biological relationship claims.
