# Build a portable one-folder distribution into dist/AudioBook-Manager/
# Does not modify or overwrite project source files.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing .venv. Create it first: py -3.12 -m venv .venv"
}

Write-Host "Installing build dependencies..."
& $python -m pip install --upgrade pip pyinstaller | Out-Host

Write-Host "Building portable app into dist\AudioBook-Manager\ ..."
& $python -m PyInstaller audiobook-manager.spec --noconfirm --clean | Out-Host

Write-Host "Staging data folders and FFmpeg..."
& $python packaging\stage_portable.py | Out-Host

Write-Host ""
Write-Host "Done. Portable build:"
Write-Host "  $PSScriptRoot\dist\AudioBook-Manager\AudioBook Manager.exe"