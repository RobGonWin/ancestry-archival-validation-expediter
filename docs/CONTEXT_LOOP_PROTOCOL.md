# Context and loop engineering protocol

This protocol turns an open-ended family-history question into a bounded,
reviewable run. It adapts public context/loop-engineering ideas to AAVE's local
privacy and evidence model; it does not copy private data into an agent prompt
or grant a tool broader authority.

## Run contract

Before collection, create a context manifest with:

- a single question and explicit non-goals;
- allowed sources and the maximum privacy label;
- evidence roles expected in the run;
- allowed tools and external-write policy;
- a context budget and search/time ceiling;
- required schema, test, branch-policy, and boundary checks;
- stop conditions; and
- the intended private output plus any separately reviewed public derivative.

The manifest belongs in an ignored local vault or, when it must be versioned,
the authorized private research lane. A public branch receives only a new,
purpose-built derivative after review.

## Loop

```text
question -> minimal context -> classify -> one bounded action -> validate
    ^                                                        |
    |---- contradiction/null result <- skeptic review <------|
                              |
                         checkpoint/stop
```

1. **Question:** define one falsifiable or documentable claim.
2. **Minimal context:** select only the records needed for the next action.
3. **Classify:** label observation, record, artifact, recollection, inference,
   hypothesis, contradiction, and review decision separately.
4. **Act:** perform one local transformation, comparison, or authorized source
   lookup. Do not broaden the run invisibly.
5. **Validate:** check structure, provenance, privacy propagation, and the
   applicable repository gates.
6. **Skeptic review:** search for conflicting dates, duplicate identities,
   dependent sources, alternative relationships, and cue contamination.
7. **Checkpoint:** record hashes, decisions, null results, remaining
   uncertainty, and the exact next question.
8. **Stop:** end when the question is answered to its declared threshold, the
   context budget is reached, or a stop condition is met.

## Hard stops

Stop for unclear consent; a requested privacy downgrade; raw DNA or private
media entering a model/log; an external write not declared in the manifest; a
biological, medical, cognitive, or longevity conclusion unsupported by the
evidence role; source terms that prohibit the intended reuse; or validation
failure. A human must deliberately authorize a new run with a revised scope.

## Graph projection

Graph output is a view. Nodes keep opaque identifiers, privacy labels,
evidence roles, source hashes, and review status. Edges describe support,
contradiction, context, and derivation; they do not manufacture identity,
kinship, causation, cognition, or inheritance.
