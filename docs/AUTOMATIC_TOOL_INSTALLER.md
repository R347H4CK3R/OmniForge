# OmniForge automatic dependency installer (experimental)

The iPhone app's **Install** tab communicates with a user-configured Windows installation bridge. This is **not** a shell exposed to model prompts.

## Design
- Built-in allowlist: GitHub CLI, Git, Python 3, 7-Zip
- Checks for existing installations before invoking WinGet
- Uses fixed package IDs, no arbitrary commands or prompt-to-shell conversion
- Executes one installation at a time, with a 10-minute timeout and result reporting
- Checks for the expected executable after installation
- Explicit in-app approval before installing
- Requires a session authorization token and HTTPS from the iPhone
- Local Windows listener binds **only** to `127.0.0.1`; do not expose that port directly
- Windows prompts/UAC may still require interactive approval

## Windows bridge
1. Install Python 3 and WinGet on the authorized Windows PC.
2. Set `OMNIFORGE_INSTALL_TOKEN` to a long random secret (at least 32 characters). Do not put it in source or screenshots.
3. Run `python bridge/omniforge_installer.py` on the Windows PC.
4. Provide a **trusted private HTTPS reverse proxy** to the loopback service. Prefer Tailscale with a protected endpoint and restricted device access. This repository does not automatically provision TLS, Tailscale, a reverse proxy, or device authentication.
5. In OmniForge > **Install**, enter the private HTTPS bridge URL and the token, then select **Check installation** or **Install and verify**.

The token is held in the current iOS view's state and is not written into persistent settings. Never publish the bridge or forward the loopback HTTP port to the public internet.

## Current limitations
This is the first functional installer UI and bridge implementation. It has **not** passed an iPhone build or paired-host integration test in this feature branch. It does not automatically discover every possible tool, evaluate or execute arbitrary installers, restart the original AI request, or install host programs from the offline iOS sandbox. Auto-retry and per-package manifests are future integration tasks. A remote bridge must first be deployed and reached from the iPhone.

## Verification checklist
- Confirm an unsigned IPA build succeeds with `OmniInstallerView.swift` included.
- Confirm status request is rejected without a valid token.
- Confirm GET /install is rejected.
- Confirm unknown package names are rejected.
- Confirm installed tool is recognized without invoking WinGet.
- Install a missing allowlisted tool and verify it is executable.
- Verify invalid HTTPS configuration produces an actionable error.
- Validate disconnected/reconnected host and privilege elevation behavior.
