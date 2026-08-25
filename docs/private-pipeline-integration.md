# Private Pipeline Integration Boundary

Public AAVE can validate a small public-projection receipt created after a
separate private AAVE workflow has produced and human-reviewed a public-safe
derivative. Public AAVE does not read a private timeline, genotype bundle,
source image, browser capture, account export, or local vault.

```text
private local pipeline
  -> separate human-reviewed redaction/projection step
  -> P0 public derivative + public-projection receipt
  -> public AAVE receipt validation
  -> ordinary public release review
```

The closed receipt schema accepts only bounded identifiers, public projection
metadata, a hash of the public projection itself, and fixed limitation codes.
It rejects unknown fields and requires every private-content flag to be false.
The receipt cannot contain:

- private source values or totals;
- raw artifacts, source images, account captures, or narratives;
- names, account identifiers, local paths, or personal recollections;
- genotypes, health measurements, or raw-source hashes; or
- an R4/R3 privacy classification.

Validate a reviewed receipt locally:

```powershell
python -m aave bridge validate-receipt `
  --input .\reviewed-public-output\projection-receipt.json
```

The `public_projection_sha256` value commits only to the already reviewed
public projection. It must never be the hash of a private source artifact. A
receipt proves deterministic correspondence to that public projection; it does
not prove identity, source authenticity, a private claim, a biological
relationship, or a medical/genetic interpretation.

The public repository includes only the schema implementation and a synthetic
example. Creation of an owner-specific public derivative remains a separate
human decision outside this repository.
