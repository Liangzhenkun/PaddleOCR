param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$InnoCandidates = @(
    (Join-Path $RepoRoot ".tools\InnoSetup\ISCC.exe"),
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)

$InnoExe = $InnoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $InnoExe) {
    throw "Inno Setup 6 not found. Install it first, for example with: choco install innosetup -y"
}

& (Join-Path $PSScriptRoot "build_exe.ps1") @PSBoundParameters

Push-Location $RepoRoot
try {
    & $InnoExe "installer\PaddleOCRDesktop.iss"
    Write-Host ""
    Write-Host "Installer build completed:"
    Write-Host "  $RepoRoot\installer\Output"
}
finally {
    Pop-Location
}
