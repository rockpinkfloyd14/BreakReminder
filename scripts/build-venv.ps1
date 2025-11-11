param(
  [switch]$UseUPX
)

# Build in a clean virtual environment for a smaller EXE
$ErrorActionPreference = 'Stop'

$venv = ".venv-build"
$python = (Get-Command python).Source

if (-not (Test-Path $venv)) {
  & $python -m venv $venv
}

$py = Join-Path $venv 'Scripts/python.exe'
$pip = Join-Path $venv 'Scripts/pip.exe'
$pyi = Join-Path $venv 'Scripts/pyinstaller.exe'

& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
& $py -m pip install pyinstaller

# Ensure assets exist (icon/header)
& $py scripts/generate_assets.py

# Clean previous artifacts
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path BreakReminder.spec) { Remove-Item -Force BreakReminder.spec }

$common = @('--noconsole','--onefile','--name','BreakReminder','--icon','assets/logo.ico','--strip')
$excludes = @('--exclude-module','numpy','--exclude-module','scipy','--exclude-module','pandas','--exclude-module','matplotlib','--exclude-module','numba','--exclude-module','IPython','--exclude-module','notebook','--exclude-module','jupyter','--exclude-module','pytest')

$upxDir = $null
if ($UseUPX) {
  # Try to find upx.exe or download it
  $upx = (Get-Command upx -ErrorAction SilentlyContinue)
  if ($upx) {
    $upxDir = Split-Path -Parent $upx.Source
  } else {
    $tmp = Join-Path $PWD '.upx'
    if (-not (Test-Path $tmp)) { New-Item -ItemType Directory -Force -Path $tmp | Out-Null }
    $zip = Join-Path $tmp 'upx.zip'
    $url = 'https://github.com/upx/upx/releases/latest/download/upx-win64.zip'
    try {
      Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
      Expand-Archive -LiteralPath $zip -DestinationPath $tmp -Force
      $candidates = Get-ChildItem -Recurse -Filter upx.exe -Path $tmp
      if ($candidates) { $upxDir = Split-Path -Parent $candidates[0].FullName }
    } catch {
      Write-Warning "UPX download failed, proceeding without UPX."
    }
  }
}

$args = @($common + $excludes + @('main.py','--noconfirm'))
if ($upxDir) {
  $args = @($common + @('--upx-dir', $upxDir) + $excludes + @('main.py','--noconfirm'))
}

& $pyi @args
Write-Host "Build complete (venv): dist/BreakReminder.exe"
