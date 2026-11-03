# This policy setting applies only to this task process; it does not change Windows policy.
$ErrorActionPreference='Stop'
$root=Join-Path $env:LOCALAPPDATA 'OmniForgeTerminal'
$script=Join-Path $root 'start-terminal.ps1'
if (-not (Test-Path $script)) { throw 'Copy the terminal source and install its dependencies first.' }
$exe=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$action=New-ScheduledTaskAction -Execute $exe -Argument ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$script+'"') -WorkingDirectory $root
$user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$trigger=New-ScheduledTaskTrigger -AtLogOn -User $user
Register-ScheduledTask -TaskName OmniForgeWebTerminal -Action $action -Trigger $trigger -Description 'Private authenticated OmniForge web terminal' -Force
Start-ScheduledTask -TaskName OmniForgeWebTerminal
