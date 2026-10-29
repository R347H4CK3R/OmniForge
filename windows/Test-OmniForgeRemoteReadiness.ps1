# Read-only environment inventory; never starts a service or changes settings.
$ErrorActionPreference='Continue'
$checks=[System.Collections.Generic.List[object]]::new()
function Add-Check([string]$Name,[bool]$Pass,[string]$Detail) { $checks.Add([pscustomobject]@{Check=$Name;Pass=$Pass;Detail=$Detail}) }
if ($env:OS -ne 'Windows_NT') { Write-Error 'Requires Windows'; exit 2 }
$tail=Get-Command tailscale -ErrorAction SilentlyContinue
Add-Check 'Tailscale executable' ($null -ne $tail) $(if($tail){$tail.Source}else{'Not on PATH'})
if ($tail) { $status=& tailscale status --json 2>$null | ConvertFrom-Json -ErrorAction SilentlyContinue; Add-Check 'Tailscale connected' ($null -ne $status -and $status.BackendState -eq 'Running') $(if($status){[string]$status.BackendState}else{'Status unavailable'}) }
$ollama=Get-Command ollama -ErrorAction SilentlyContinue
Add-Check 'Ollama executable' ($null -ne $ollama) $(if($ollama){$ollama.Source}else{'Not on PATH'})
$rust=Get-Command rustdesk -ErrorAction SilentlyContinue
if(-not $rust){ $rust=Get-Item "$env:ProgramFiles\RustDesk\rustdesk.exe" -ErrorAction SilentlyContinue }
Add-Check 'Optional RustDesk client' ($null -ne $rust) $(if($rust){[string]$rust.FullName}else{'Install and authorize a remote desktop tool separately'})
$hostPort=Test-NetConnection -ComputerName '127.0.0.1' -Port 8787 -WarningAction SilentlyContinue -InformationLevel Quiet
Add-Check 'OmniForge host local port 8787' ([bool]$hostPort) 'Connectivity only; does not verify authentication'
$report=[pscustomobject]@{Timestamp=(Get-Date).ToString('o');Device=$env:COMPUTERNAME;Checks=@($checks);Passed=@($checks|Where-Object Pass).Count;Total=$checks.Count}
$report | ConvertTo-Json -Depth 6
if(@($checks|Where-Object {$_.Check -eq 'Tailscale connected' -and -not $_.Pass}).Count -gt 0){exit 1}
