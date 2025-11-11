$ErrorActionPreference = 'Stop'
$env:BR_PROFILE_STARTUP = '1'
$env:BR_AUTO_QUIT_MS = '1500'
python main.py
if (Test-Path 'startup_profile.log') { Get-Content 'startup_profile.log' }