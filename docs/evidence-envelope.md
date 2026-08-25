# Evidence Envelope and Claim Graph

AAVE uses a versioned evidence envelope to keep observations, recollections,
documents, inferences, and hypotheses in distinct evidentiary roles. The
envelope is an **offline import format** for user-owned exports and explicitly
captured material. It does not log in to, crawl, or automate Ancestry or any
other private service.

## Privacy tiers

- `R4`: genetic, health, or raw physiological material; encrypted local vault only.
- `R3`: account captures, vital records, and identity-bearing records.
- `R2`: family photographs, interviews, and memorabilia under private review.
- `R1`: independently public archival sources; citations are preferred to copies.
- `P0`: specifically reviewed and approved public derivative.

The existing AAVE privacy labels remain authoritative. A public preview is
eligible to contain a summary only when all three conditions are true:

1. privacy tier is `P0`;
2. privacy label is `public_ok`; and
3. consent scope explicitly contains `public_release`.

Anything else produces a withheld metadata stub. `R4` and `R3` envelopes are
not permitted to grant public-release consent.

## Claims remain human reviewed

A claim links to evidence with one of three relations: `supports`,
`contradicts`, or `contextualizes`. The graph reports the presence of support,
contradiction, mixed evidence, or context-only evidence. It never computes
`proved`, never infers biological relationships, and never promotes a draft
hypothesis automatically.

## Local workflow

```powershell
aave evidence validate --input .\local-vault\capture.json
aave evidence import-capture --input .\local-vault\capture.json --out .\local-vault\normalized
aave claims build --evidence-dir .\local-vault\normalized --claims .\local-vault\claims.json --out .\local-vault\graph
aave privacy-audit --repo . --out .\out\boundary --strict
```

Keep `local-vault`, browser/account captures, local path maps, keys, and raw
artifacts outside Git. Commit only schemas, synthetic examples, methodology,
and derivatives that passed explicit review.
