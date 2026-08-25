# Windows Automation

AAVE includes simple Windows scripts for running the local pipeline. They call existing `aave` commands only. They do not make network calls, use API keys, scrape websites, automate logins, bypass CAPTCHAs/paywalls/DRM/access controls, parse raw DNA, or make medical or endorsement claims.

## Prerequisites

Install the package in editable mode from the repository root:

```powershell
python -m pip install -e .
```

Confirm the CLI is available:

```powershell
aave --help
```

## Full Pipeline

```powershell
.\scripts\run_pipeline.ps1 `
  -InputDirectory .\family_archive `
  -GedcomPath .\tree.ged `
  -ConfigPath .\examples\config.example.json `
  -OutputDirectory .\out `
  -PacketPerson john-smith-i1
```

The BAT wrapper runs the same PowerShell script with `ExecutionPolicy Bypass` for that script invocation only:

```bat
scripts\run_pipeline.bat -InputDirectory .\family_archive -GedcomPath .\tree.ged -ConfigPath .\examples\config.example.json -OutputDirectory .\out
```

## Tests

```powershell
.\scripts\run_tests.ps1
```

Use `-SkipRuff` only when Ruff is not installed:

```powershell
.\scripts\run_tests.ps1 -SkipRuff
```

## Export Helpers

Public redacted metadata export:

```powershell
.\scripts\export_public.ps1 -OutputDirectory .\out -ExportDirectory .\out\public_export
```

Expert review metadata export, with optional expert packet:

```powershell
.\scripts\export_expert_packet.ps1 `
  -OutputDirectory .\out `
  -ExportDirectory .\out\expert_review `
  -PacketPerson john-smith-i1 `
  -PacketDirectory .\out\packets
```

## Outputs

The full pipeline can write:

- `archive_manifest.json`
- `people_index.json`
- `families_index.json`
- `source_links.json`
- `archive_format_report.md`
- `export_manifest.json`
- `README_EXPORT.md`
- `<person_id>.md`
- `<person_id>_sources.csv`

Review all outputs before sharing. Public exports and packets are designed to be conservative, but human review is still required.
