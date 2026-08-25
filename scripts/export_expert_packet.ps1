param(
    [string]$OutputDirectory = ".\out",
    [string]$ExportDirectory = ".\out\expert_review",
    [string]$PacketPerson = "",
    [string]$PacketDirectory = ".\out\packets"
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
$FamiliesPath = Join-Path $OutputDirectory "families_index.json"
$LinksPath = Join-Path $OutputDirectory "source_links.json"

Require-File $ManifestPath
Require-File $PeoplePath
Require-File $LinksPath

& aave export --profile expert_review_packet --manifest $ManifestPath --people $PeoplePath --links $LinksPath --out $ExportDirectory
if ($LASTEXITCODE -ne 0) {
    throw "Expert review export failed."
}

if ($PacketPerson.Trim()) {
    Require-File $FamiliesPath
    & aave packet `
        --person $PacketPerson `
        --profile expert_review_packet `
        --people $PeoplePath `
        --families $FamiliesPath `
        --manifest $ManifestPath `
        --links $LinksPath `
        --out $PacketDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Expert review packet generation failed."
    }
}
else {
    Write-Host "Skipping expert packet generation because -PacketPerson was not provided."
}

Write-Host "Expert review export written to $ExportDirectory"
