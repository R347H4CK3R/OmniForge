# Release automation and minimal setup

## Windows
1. Once the **Publish OmniForge Windows Update** workflow has succeeded, download and execute the repository's `windows/Install-OmniForge.ps1` from a trusted copy of the repository. It downloads the latest published Windows ZIP and verifies its release SHA-256 before installing under `%LOCALAPPDATA%\OmniForge\App`.
2. Install Ollama and pull an appropriate model. Start `%LOCALAPPDATA%\OmniForge\App\Start-OmniForge.ps1`.
3. Set up Tailscale on laptop and phone and configure private HTTPS Serve. Paste the server endpoint and generated access token in the iPhone app.
4. For later releases, run `Update-OmniForge.ps1` with host processes stopped; `-CheckOnly` only checks. Automatic in-app downloads are a future step; current updates do **not** install while binaries are running.

## iPhone
Add the existing LiveContainer source **once**:
https://raw.githubusercontent.com/R347H4CK3R/OmniForge/main/livecontainer-source.json

The existing publish workflow compiles a small unsigned IPA, creates a tagged GitHub Release, then updates the LiveContainer catalog **only after a successful release**. Refreshing the source exposes new versions. An iOS app cannot silently replace its own executable; use LiveContainer's installation control for new versions. The app's existing Updates screen currently checks builds, not a one-click installer.

## Release reliability
Windows releases require passing server tests. LiveContainer source entries are release-backed; build successes alone are not installs. Verify actual Windows launching and real LiveContainer running before labeling an end-to-end release stable. The published Windows EXE is currently a console-backed agent, not a full native Windows GUI.

**Remaining setup work:** bundle or detect Ollama, first-run guided setup, background updater with safe staging/rollback, tray GUI, native job status screen, source-catalog install deep-link only if supported by LiveContainer, and remote pairing UX.

**Privacy:** user conversation exports and model/workspace databases stay local and must never be committed as public release assets.
