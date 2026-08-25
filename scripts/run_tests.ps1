param(
    [switch]$SkipRuff
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$CommandName,
        [string[]]$Arguments
    )

    Write-Host "$CommandName $($Arguments -join ' ')"
    & $CommandName @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $CommandName $($Arguments -join ' ')"
    }
}

Invoke-Checked "python" @("-m", "pytest", "-q")

if (-not $SkipRuff) {
    Invoke-Checked "python" @("-m", "ruff", "check", ".")
}

Write-Host "AAVE tests completed."
