# Build script for smaller, optimized EXE
# Usage (PowerShell):
#   pwsh -File scripts/build.ps1
# Produces dist/BreakReminder.exe

# Ensure assets exist (icon/header)
python scripts/generate_assets.py

# Clean previous artifacts
try {
  if (Get-Process BreakReminder -ErrorAction SilentlyContinue) {
    Get-Process BreakReminder | Stop-Process -Force
    Start-Sleep -Seconds 1
  }
} catch {}
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path BreakReminder.spec) { Remove-Item -Force BreakReminder.spec }

# Build with stripping and some excludes for size reduction
$common = @(
  '--noconsole', '--onefile', '--name', 'BreakReminder',
  '--icon', 'assets/logo.ico',
  '--strip'
)
# Exclude common heavy libs when present (not used by this app)
$excludes = @(
  '--exclude-module', 'numpy',
  '--exclude-module', 'scipy',
  '--exclude-module', 'pandas',
  '--exclude-module', 'matplotlib',
  '--exclude-module', 'numba',
  '--exclude-module', 'IPython',
  '--exclude-module', 'notebook',
  '--exclude-module', 'jupyter',
  '--exclude-module', 'pytest'
)

pyinstaller @common @excludes main.py --noconfirm

Write-Host "Build complete: dist/BreakReminder.exe"
