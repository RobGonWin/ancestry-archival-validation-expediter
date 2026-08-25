param(
    [string]$OutputDirectory = ".\out",
    [string]$ExportDirectory = ".\out\public_export"
)

$ErrorActionPreference = "Stop"

function Require-File {
    param([string]$PathValue)
    if (-not (Test-Path -LiteralPath $PathValue -PathType Leaf)) {
        throw "Required pipeline output not found: $PathValue"
    }
}

$ManifestPath = Join-Path $OutputDirectory "archive_manifest.json"
$PeoplePath = Join-Path $OutputDirectory "people_index.json"
$LinksPath = Join-Path $OutputDirectory "source_links.json"

Require-File $ManifestPath
Require-File $PeoplePath
Require-File $LinksPath

& aave export --profile public_redacted --manifest $ManifestPath --people $PeoplePath --links $LinksPath --out $ExportDirectory
if ($LASTEXITCODE -ne 0) {
    throw "Public export failed."
}

Write-Host "Public redacted export written to $ExportDirectory"
