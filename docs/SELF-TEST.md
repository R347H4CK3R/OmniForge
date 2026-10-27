# OmniForge /self-test

In the **iPhone OmniForge chat**, send `/self-test` (or `/selftest`). Local file write/read/JSON and bundle checks run first. If the laptop's HTTPS endpoint and access key are configured, the iPhone also requests a full host report over the existing authenticated channel.

From **Windows PowerShell**, run this single line from the cloned OmniForge folder:

```powershell
py -3 server/self_test.py
```

Or send `/self-test` as a user message to the Windows agent's existing `/v1/chat/completions` endpoint. The host also exposes authenticated `GET /v1/self-test`.

Report statuses:
- **PASS** = that check completed successfully
- **FAIL** = the check detected an issue
- **SKIP** = dependency unavailable or configuration missing
- **PARTIAL** = no failures, but checks were skipped

Tests cover workspace read/write, database integrity, Ollama model availability, access-key configuration and installed tools. Remote iPhone requests show both local and host results. Tests are deliberately bounded and avoid performing package installs or modifying user projects.

**Limitations:** A smoke test cannot conclusively verify every UI, a real LiveContainer launch, every available IPA, macOS Tahoe runner health or an external GitHub build. Those need separate integration and physical-device checks. A PASS result means only the listed tests passed, not that the entire program has been exhaustively verified.
