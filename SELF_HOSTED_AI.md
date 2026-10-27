# OmniForge self-hosted AI (Windows 11)

No AI subscription, API credits, or hosted-model bill. Hardware, storage, electricity and ordinary internet costs remain. This is for a computer you control.

1. Install [Ollama](https://ollama.com/download/windows) and [Tailscale](https://tailscale.com/download/windows) on the Windows laptop. Install Tailscale on your iPhone and log in to the same tailnet.
2. In Windows PowerShell, run the single line below:

```powershell
ollama pull qwen3:8b; tailscale serve --bg 11434; tailscale serve status
```

3. Copy the HTTPS URL shown by Tailscale Serve, append `/v1/chat/completions`.
4. In OmniForge → Models, enable **Use my own online server**. Paste that HTTPS endpoint and set Model ID `qwen3:8b`.
5. Send a test chat. Disable the toggle to return to on-device GGUF inference.

Ollama implements OpenAI-compatible chat completions at `/v1/chat/completions`. Tailscale Serve makes localhost services reachable only to authorized devices on your private tailnet using HTTPS. You may be asked to enable HTTPS certificates for the tailnet. Leave **Funnel** off: this service should not be exposed to the public internet.

You can select a smaller model (such as `qwen3:4b`) if your laptop runs out of RAM. Model selection depends on your computer's capabilities.

**Privacy:** Online mode sends chat messages to the configured server. Offline mode does not call the server. The endpoint is saved in local app settings; optional API credentials use iOS Keychain. Ollama's local server normally needs no API key. The app does not manage server setup or keep your Windows PC awake.

**Limits:** Tailscale has its own plan terms, device limits and availability. Running a local AI on your own hardware has no per-token provider billing, but it is not limitless. If your PC is shut down or the tailnet is unavailable, online chat will fail until you select offline mode. The app cannot run Ghidra or Xcode on your laptop solely by changing the model endpoint.
