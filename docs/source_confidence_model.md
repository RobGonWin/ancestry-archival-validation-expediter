# Source Confidence Model

AAVE tracks source confidence separately from privacy. A file can be private and well supported, public and weakly supported, or anywhere between. v0.6 preserves source confidence labels through manifests, links, exports, and packets. It does not upgrade confidence automatically.

## Default Label

The default source confidence label is:

```text
needs_review
```

## Labels

- `confirmed`: direct evidence is clearly represented by records or explicit user-provided documentation.
- `probable`: evidence is strong but still needs careful review.
- `family_identified`: identified by family-held knowledge or labels.
- `personal_recollection`: based on personal memory or narrative.
- `needs_review`: not yet reviewed or insufficiently classified.
- `public_secondary`: based on public secondary references.
- `private_artifact`: based on a private family-held artifact.

## Conservative Handling

Do not upgrade a source to `confirmed` unless the evidence is direct and clearly represented. Ambiguous dates, identities, relationships, and source claims should remain in review state.

Research packets should keep cautious wording such as `family-identified as`, `apparent date stamp`, and `pending scan verification` when artifact claims have not been independently verified.
