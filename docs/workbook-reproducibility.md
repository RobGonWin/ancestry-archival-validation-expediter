# Deterministic workbook packaging

The authoring exporter assigns random OOXML relationship IDs. `canonicalize_workbook.py` replaces only relationship identifiers and matching references with deterministic identifiers derived from the relationship location, type, target and mode, then fixes ZIP member order and timestamps. Cell values, styles, tables, validation rules and worksheet contents remain intact. The authoring script runs this step automatically.

Two independently authored packages and the published workbook produce the same final byte hash after normalization. Regression tests verify target preservation, unchanged cell content, idempotence and equality across differing input IDs/timestamps. The public verifier also checks all33 columns across584subjects and473namedfellows against CSV/JSON after normalization.
