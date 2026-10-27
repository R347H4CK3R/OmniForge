param([switch]$SkipWorker)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Data = Join-Path $env:LOCALAPPDATA 'OmniForge'
New-Item -ItemType Directory -Force -Path $Data | Out-Null
$Workspace = Join-Path $Data 'Workspace'
New-Item -ItemType Directory -Force -Path $Workspace | Out-Null
$KeyPath = Join-Path $Data 'agent-key.txt'
if (-not (Test-Path $KeyPath)) {
  $bytes = New-Object byte[] 32
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  [Convert]::ToBase64String($bytes) | Set-Content -Path $KeyPath -NoNewline
}
$env:OMNIFORGE_WORKSPACE = $Workspace
$env:OMNIFORGE_AGENT_KEY = (Get-Content $KeyPath -Raw).Trim()
if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = 'qwen3:8b' }
$HostExe = Join-Path $PSScriptRoot 'OmniForgeHost.exe'
$WorkerExe = Join-Path $PSScriptRoot 'OmniForgeWorker.exe'
$Python = Get-Command py -ErrorAction SilentlyContinue
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { Write-Warning 'Ollama is missing; install it from ollama.com/download before chatting.' }
Write-Host 'OmniForge workspace:' $Workspace
Write-Host 'Remote iPhone setup: install Tailscale on Windows and iPhone, then enable HTTPS Tailscale Serve for localhost:8787.'
Write-Host 'Agent key (enter in iPhone Models > private agent access key):' $env:OMNIFORGE_AGENT_KEY
if (-not $SkipWorker) {
  if (Test-Path $WorkerExe) {
    Start-Process -FilePath $WorkerExe -WindowStyle Minimized -WorkingDirectory $Root
  } elseif ($Python) {
    Start-Process -FilePath 'py' -ArgumentList '-3','server/job_worker.py' -WindowStyle Minimized -WorkingDirectory $Root
  } else { Write-Warning 'No queue worker available.' }
}
if (Test-Path $HostExe) { & $HostExe }
elseif ($Python) { & py -3 server/agent_server.py }
else { throw 'Neither the packaged OmniForgeHost.exe nor Python 3 was found.' }
