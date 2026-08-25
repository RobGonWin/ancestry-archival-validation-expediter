param(
    [string]$InputDirectory = ".\family_archive",
    [string]$GedcomPath = ".\tree.ged",
    [string]$ConfigPath = ".\examples\config.example.json",
    [string]$OutputDirectory = ".\out",
    [string]$PacketPerson = "",
    [ValidateSet("public_redacted", "private_full", "expert_review_packet")]
    [string]$PacketProfile = "private_full"
)

$ErrorActionPreference = "Stop"

function Resolve-RequiredPath {
    param(
        [string]$PathValue,
        [string]$Description
    )

    if (-not (Test-Path -LiteralPath $PathValue)) {
        throw "$Description not found: $PathValue"
    }
    return (Resolve-Path -LiteralPath $PathValue).Path
}

function Invoke-Aave {
    param([string[]]$Arguments)

    Write-Host "aave $($Arguments -join ' ')"
    & aave @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: aave $($Arguments -join ' ')"
    }
}

$ResolvedInputDirectory = Resolve-RequiredPath $InputDirectory "Input archive directory"
$ResolvedGedcomPath = Resolve-RequiredPath $GedcomPath "GEDCOM file"
$ResolvedConfigPath = Resolve-RequiredPath $ConfigPath "Config file"

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

Invoke-Aave @("scan", "--input", $ResolvedInputDirectory, "--config", $ResolvedConfigPath, "--out", $OutputDirectory)
Invoke-Aave @("parse-gedcom", "--gedcom", $ResolvedGedcomPath, "--out", $OutputDirectory)
Invoke-Aave @(
    "link",
    "--manifest", (Join-Path $OutputDirectory "archive_manifest.json"),
    "--people", (Join-Path $OutputDirectory "people_index.json"),
    "--config", $ResolvedConfigPath,
    "--out", $OutputDirectory
)
Invoke-Aave @("inspect-archives", "--manifest", (Join-Path $OutputDirectory "archive_manifest.json"), "--out", $OutputDirectory)
Invoke-Aave @("export", "--profile", "public_redacted", "--out", (Join-Path $OutputDirectory "public_export"))
Invoke-Aave @("export", "--profile", "private_full", "--out", (Join-Path $OutputDirectory "private_export"))
Invoke-Aave @("export", "--profile", "expert_review_packet", "--out", (Join-Path $OutputDirectory "expert_review"))

if ($PacketPerson.Trim()) {
    Invoke-Aave @(
        "packet",
        "--person", $PacketPerson,
        "--profile", $PacketProfile,
        "--out", (Join-Path $OutputDirectory "packets")
    )
}
else {
    Write-Host "Skipping packet generation because -PacketPerson was not provided."
}

Write-Host "AAVE pipeline completed. Output: $OutputDirectory"
