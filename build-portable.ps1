# Build a portable one-folder distribution into dist/AudioBook-Manager/
# Does not modify or overwrite project source files.

param([string]$DistRoot = "dist")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$distPath = if ([System.IO.Path]::IsPathRooted($DistRoot)) {
    [System.IO.Path]::GetFullPath($DistRoot)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot $DistRoot))
}
$portablePath = Join-Path $distPath "AudioBook-Manager"
# PyInstaller replaces the output folder. Never erase a used portable profile.
foreach ($folder in @("data", "cache")) {
    $savedFolder = Join-Path $portablePath $folder
    if ((Test-Path -LiteralPath $savedFolder) -and
        (Get-ChildItem -LiteralPath $savedFolder -File -Recurse -Force | Select-Object -First 1)) {
        throw "Portable output contains saved data in $savedFolder. Use -DistRoot with a fresh folder, then copy your data and cache into the new build."
    }
}

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing .venv. Create it first: py -3.12 -m venv .venv"
}

Write-Host "Installing build dependencies..."
& $python -m pip install -r requirements-build.txt | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Build dependency installation failed (exit $LASTEXITCODE)." }

Write-Host "Building portable app into dist\AudioBook-Manager\ ..."
& $python -m PyInstaller audiobook-manager.spec --noconfirm --clean --distpath $distPath | Out-Host
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)." }

Write-Host "Staging data folders and FFmpeg..."
& $python packaging\stage_portable.py --dist-dir $portablePath | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Portable staging failed (exit $LASTEXITCODE)." }

Write-Host ""
Write-Host "Done. Portable build:"
Write-Host "  $portablePath\AudioBook Manager.exe"
