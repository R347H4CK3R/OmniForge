# OmniForge next: unified assistant roadmap

## Existing capabilities (not presumed production-verified)
- Native SwiftUI iOS client, local GGUF inference, LiveContainer release automation
- IPA workbench and authorized static analysis
- Python Ollama agent and workspace-limited tools
- GitHub Actions builds

## New foundation in this change
- Persistent local SQLite/FTS5 knowledge
- Import of ChatGPT `conversations.json`, generic Codex-compatible JSONL records
- On-demand search through Ollama tool calling
- No private messages committed to GitHub

## Expansion priorities
1. Real-world test of current unsigned IPA on LiveContainer; retain original bundle identity.
2. Add Knowledge screen to native app: import exports via Files, search, delete and reindex.
3. Device pairing with authenticated laptop agent over an authenticated private HTTPS tunnel.
4. Long-running, resumable autonomous jobs with checkpointing, logs, explicit stop, and budgets.
5. Project integrations for GitHub: repository selection, branches, PRs, workflow runs, log triage, build artifact download.
6. IPA reverse-engineering pipelines: ZIP/plist/Mach-O inspection, permission-based decompiler invocation on laptop, resource patching, macOS-hosted compilation.
7. Tool installer with package-manifest checks and rollback; never silently elevate privileges.
8. Optional browsing/research ingestion with citations, timestamps and deduplication.
9. Automated integration tests on Windows plus GitHub macOS runners; physical iPhone acceptance testing.

## Knowledge source strategy
Past project details should be **imported from user-owned exports locally**, not copied into a public GitHub repository. Prioritized skill areas: ARM64 iOS development, unsigned IPA workflows, LiveContainer, GitHub Actions, Pythonista, Windows/PowerShell automation, gaming project diagnostics, source recovery limits, local models and networking.

A private knowledge database is not the same as retraining a model. Retrieval improves continuity but doesn't guarantee ChatGPT-level reasoning, proprietary tools, unlimited context or unrestricted iOS capabilities.

## Privacy and security
Keep exports, secrets, tokens, and proprietary game files outside tracked files. Never expose the agent HTTP port publicly. Require authorization for writes, external changes, installs and destructive operations. Treat retrieved chat messages as data rather than instructions.
