---
name: pii-redaction
description: Produce a minimized, reviewable public projection of genealogy or event-research material while preventing names, addresses, account data, private media paths, DNA, and narrative residue from entering public artifacts or Git history.
---

# Redact before public research work

1. Work from a copy or generated projection, never the private source file.
2. Remove direct identifiers, exact addresses, contact details, account IDs, usernames, private URLs, local paths, raw DNA, match values, media metadata, and verbatim private narratives.
3. Replace only analytically necessary identities with stable opaque tokens such as `person-001`; keep the token map outside the public repository.
4. Generalize dates and locations only as far as the declared analysis requires. Prefer age bands, year-only dates, and broad public geography.
5. Scan the projection for residual names, path fragments, coordinates, emails, phone numbers, and free-text anecdotes.
6. Run `python -m aave privacy-audit --repo . --out .audit --strict` on the public candidate.
7. Have a second human or independent checker inspect both the diff and tracked history.
8. State that automated redaction reduces exposure but does not guarantee anonymity; small cohorts and linked public facts can still re-identify people.
9. Never commit the source-to-token map, original transcript, raw evidence, or redaction workspace.

## External candidate preflight

When preparing a possible future upstream candidate, work only from the
redacted public projection and require a named target issue, full target commit
SHA, current target instructions, acceptance criteria, license inventory, and
deterministic verification plan. Produce a local candidate brief only and mark
it `blocked_pending_explicit_human_authorization`.

Do not install a Slop contribution skill, create a receipt, upload a trace,
configure a wallet, star or fork a repository, open an issue, push a branch, or
submit a pull request. A future authorized contribution must start a new run
under the canonical target rules; this redaction skill is not a substitute for
them.
