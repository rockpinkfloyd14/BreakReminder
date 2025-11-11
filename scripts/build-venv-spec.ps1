param(
  [switch]$UseUPX
)

$ErrorActionPreference = 'Stop'

$venv = ".venv-build"
$python = (Get-Command python).Source
if (-not (Test-Path $venv)) {
  & $python -m venv $venv
}
$py = Join-Path $venv 'Scripts/python.exe'
$pyi = Join-Path $venv 'Scripts/pyinstaller.exe'

& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
& $py -m pip install pyinstaller

# Ensure assets exist
& $py scripts/generate_assets.py

# Clean previous artifacts
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }

$upxDir = $null
if ($UseUPX) {
  $upx = (Get-Command upx -ErrorAction SilentlyContinue)
  if ($upx) { $upxDir = Split-Path -Parent $upx.Source }
}

$extra = @('--noconfirm','--clean')
if ($upxDir) { $extra += @('--upx-dir', $upxDir) }

& $pyi 'BreakReminder.spec' @extra
Write-Host "Spec build complete: dist/BreakReminder.exe"