# Minimal first-time installer. Uses official OmniForge GitHub Releases.
$ErrorActionPreference='Stop'
$Updater=Join-Path $env:TEMP ('OmniForge-Update-'+[guid]::NewGuid().ToString('N')+'.ps1')
try {
  Invoke-WebRequest 'https://raw.githubusercontent.com/R347H4CK3R/OmniForge/main/windows/Update-OmniForge.ps1' -OutFile $Updater
  & $Updater
  if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw "Updater failed: $LASTEXITCODE"}
  $Start=Join-Path $env:LOCALAPPDATA 'OmniForge\App\Start-OmniForge.ps1'
  if(Test-Path $Start){Write-Host "Installed. Launch with: $Start"}
} finally {Remove-Item $Updater -ErrorAction SilentlyContinue}
