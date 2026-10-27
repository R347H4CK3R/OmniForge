# OmniForge for Windows and iPhone

The **Windows Host** runs your model tools and workspace operations. The **iPhone IPA** is the same OmniForge project built using the existing macOS GitHub Actions workflow and installed through LiveContainer. Its existing Models screen supports a privately hosted HTTPS endpoint.

## Windows install

1. Download the latest successful `Build OmniForge Windows Host` GitHub Actions artifact and unzip it.
2. Install [Ollama](https://ollama.com/download) and run `ollama pull qwen3:8b` on Windows.
3. Right-click `Start-OmniForge.ps1` and choose **Run with PowerShell** (or launch it from a PowerShell terminal).
4. The launcher creates a persistent private workspace at `%LOCALAPPDATA%\OmniForge\Workspace`, and a random access key in `%LOCALAPPDATA%\OmniForge\agent-key.txt`. Do not share the key.
5. Install Tailscale on both devices, authenticate them to the same trusted tailnet, and use **Tailscale Serve** for port 8787 on the laptop. For example, following the version-appropriate official Tailscale documentation, enable an HTTPS proxy to localhost:8787. Do **not** use a public Funnel endpoint.
6. In the OmniForge iPhone IPA, open **Models → Use my own online server**, set `https://YOUR-TAILSCALE-HOSTNAME/v1/chat/completions`, save the access key shown in the PowerShell window, and select the same Ollama model. The iPhone can then ask the Windows host to use its tools over cellular data.
7. Keep the laptop awake and online for remote tools. The iPhone's local model remains usable offline, but cannot execute laptop-side actions while disconnected.

**Security:** The agent binds only to 127.0.0.1; authenticated Tailscale HTTPS access is preferred. Do not forward port 8787 on your router. Start with a dedicated workspace containing only projects you authorize the agent to edit. The Windows host executes bounded, workspace-restricted tools. It is not unrestricted access to the computer.

**Scope:** Windows host .exe and iPhone IPA are separate artifacts from one repository, not yet a single shared-install package. GitHub CI compilation and real-device LiveContainer connection tests must succeed before considering them released.
