$ErrorActionPreference='Stop'
$root=Join-Path $env:LOCALAPPDATA 'OmniForgeTerminal'
$wetty=Join-Path $env:APPDATA 'npm\wetty.cmd'
$node='C:\Program Files\nodejs\node.exe'
$origin='https://gaminglaptop-1.tail54e01b.ts.net'
if (-not (Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue)) {
  Start-Process -FilePath $wetty -ArgumentList @('--host','127.0.0.1','--port','8788','--base','/terminal','--command','powershell.exe','--allowed-origin',$origin) -WindowStyle Hidden
}
Start-Sleep -Seconds 2
if (-not (Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8789 -State Listen -ErrorAction SilentlyContinue)) {
  Start-Process -FilePath $node -ArgumentList @((Join-Path $root 'auth-proxy.js')) -WindowStyle Hidden
}

