# Discovery architecture

This repository holds public research registers. This document describes how a
question gets from those registers to somewhere it could become a contribution,
and what each step is allowed to claim.

Nothing here is a submission, an application, or an eligibility claim, and this
document does not schedule any external engagement.

## The path

```
data/*-sources.json          public source registers, 47 declared sources
        |
        v
data/discovery-questions.json  falsifiable questions, each citing declared source ids
        |                      `aave discovery-audit` enforces referential integrity
        v
private working repository     analysis on public or authorised cohort data
        |                      no private case record enters a public question
        v
clean-room target repository   target-specific contribution, gated separately
        |                      the clean-room's own contribution gate applies
        v
upstream review                other people decide, not us
```

Each arrow is a place where a claim can quietly get stronger than its evidence.
The registers exist so that the first arrow cannot.

## What `aave discovery-audit` checks

```bash
python -m aave discovery-audit --repo . --strict
```

Two things, and deliberately nothing more:

**Register completeness.** Every source needs an id, title, source type, https
urls, an evidence role, at least one `supports` entry, and at least one
`cannot_support` entry. A source that states what it supports without stating
its limits is the exact failure this repository exists to prevent, so an empty
`cannot_support` is a finding rather than a default.

**Referential integrity.** Every `source_refs` entry in a discovery question
must name a source some register actually declares. This is what stops a
question citing a literature impression. A question that cannot name its
sources is not yet a question.

The audit does not judge source quality, study design, or whether a question is
worth asking. A perfectly well-formed register can describe weak or contested
evidence, and the audit will say nothing about that.

## Cross-listed sources must be cited by register

The same paper can legitimately appear in more than one register, because its
evidence role depends on the question being asked. `YOUNG-2010-AGE115` is
`scholarly_age_validation` in the longevity register and
`age_validation_methodology` in the generation-cohort register, and the two
records carry **different `cannot_support` lists**.

That is fine as a research practice and the audit records it rather than
penalising it. What it is not fine as is a citation target. A question citing
the bare identifier has not said which set of limits it accepted, so the audit
refuses it and asks for a qualified form:

```
"source_refs": ["longevity-sources:YOUNG-2010-AGE115"]
```

Three identifiers are currently cross-listed this way. `discovery_audit.json`
lists them under `ambiguous_identifiers` with their differing fields and the
qualified forms available.

## Question status

`open` means registered and not yet designed. `designed` means an analysis plan
exists. `blocked` means a named gate prevents progress. `answered_null` means it
was run and did not find what it looked for, which is a result worth keeping.
`withdrawn` means it was abandoned, and the record stays so the abandonment is
visible.

An empty question list is the correct resting state. A repository with no open
questions is honest; one with questions it cannot source is not.

## Automation posture

Repository Actions are currently **disabled** for this repository. That is
deliberate. The discovery path above ends in contribution to other people's
projects, and no step of it should run automatically before a human has read
what it would do.

`discovery-audit` is wired into `verify.yml` so that it runs when Actions are
re-enabled. Until then, run it locally. Re-enabling Actions is a human decision,
not a consequence of merging anything.

## What this cannot support

- Registration is not a finding. A question in this file is a question.
- The audit passing does not mean a question is feasible, powered, licensed, or
  answerable with data anyone can actually obtain.
- Nothing here establishes a claim about any individual, family, or maintainer.
- Nothing here creates eligibility, acceptance, ranking, award, or payment in
  any external programme, and no such programme is addressed by this document.
