# Contributing to AAVE

Contributions are welcome when they improve this public AAVE repository while
preserving its evidence, privacy, and provenance boundaries. These terms apply
only to contributions to AAVE; they do not authorize submissions, forks,
issues, or pull requests to any external project or program.

## Copyright and inbound license

You retain copyright in your contribution. By submitting it to this
repository, you agree that your contribution is licensed under the repository's
MIT License, including its permission for use, modification, distribution, and
sublicensing.

By submitting, you also assert that the contribution is your original work or
that you otherwise have the right to provide it under the MIT License. Do not
submit copied code, data, text, media, or other material whose terms are
unknown or incompatible. Cite public research rather than reproducing
copyrighted source material. AAVE does not require a copyright assignment.

## Public contribution boundary

Only public-source documentation, original code, and clearly synthetic test
material belong in this repository. Never submit:

- raw DNA or genotype exports, DNA-match identities or values;
- real GEDCOM files, private family trees, or living-person records;
- authenticated account captures, credentials, session data, or scraped pages;
- family media, residence details, health records, or personal recollections;
- generated artifacts derived from any of the above; or
- data that is merely pseudonymized but remains linkable to a real person.

Ancestry-compatible behavior must be developed and tested with synthetic
fixtures only. The supported workflow is offline parsing of a user-owned
export stored outside the repository; it does not include account access,
browser automation, scraping, or uploads.

## Contribution workflow

1. Keep the change narrowly scoped to AAVE and state its evidence or parser
   objective.
2. Use a short-lived `feat/`, `fix/`, `docs/`, `research/`, or `chore/` branch
   and target `main` for human review.
3. Record provenance, ambiguity, limitations, and claims the source cannot
   support.
4. Add tests for success, malformed input, and privacy-preserving failure
   behavior where applicable.
5. Run `pytest -q` and
   `python -m aave privacy-audit --repo . --out .audit --strict`.
6. Obtain human review before any external write or publication.

## External programs

AAVE is not affiliated with Slop.cash, Eliza, ASI, Delta Star, or any named
track. The repository has not been submitted, has no claimed eligibility, and
makes no promise of acceptance, payment, tokens, points, or other rewards.
The track map is a local, informational fit assessment—not a contribution plan
or authority to contact or contribute to an external project.
