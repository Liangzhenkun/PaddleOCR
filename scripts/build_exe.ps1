param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Virtual environment Python not found: $PythonExe"
}

Push-Location $RepoRoot
try {
    if ($Clean) {
        if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
        if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
    }

    & $PythonExe -m pip install -r requirements.txt
    & $PythonExe -m pip install -r requirements-dev.txt
    & $PythonExe -m PyInstaller --noconfirm PaddleOCRDesktop.spec

    Write-Host ""
    Write-Host "EXE build completed:"
    Write-Host "  $RepoRoot\dist\PaddleOCRDesktopTool"
}
finally {
    Pop-Location
}
