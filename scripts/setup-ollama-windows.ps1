#Requires -Version 5.1
$ErrorActionPreference = "Stop"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Install Ollama from https://ollama.com/download/windows and reopen PowerShell"; exit 1
}
if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) {
    Write-Host "Install Tailscale from https://tailscale.com/download/windows and reopen PowerShell"; exit 1
}
ollama pull qwen3:8b
tailscale serve --bg 11434
tailscale serve status
Write-Host "Copy the HTTPS address above and append /v1/chat/completions in OmniForge → Models."
