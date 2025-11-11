$ErrorActionPreference = 'Stop'
$env:BR_PROFILE_STARTUP = '1'
python scripts/profile_startup.py
if (Test-Path 'startup_profile.log') { Get-Content 'startup_profile.log' }
