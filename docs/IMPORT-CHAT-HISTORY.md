# Import ChatGPT / Codex history privately

1. Export your conversations using the official ChatGPT export feature, then extract `conversations.json` to a folder under `OMNIFORGE_WORKSPACE`.
2. For supported Codex logs, copy JSONL files into the same authorized workspace. The importer handles generic records with `content` or `messages`; native Codex session formats can differ, and some may require adapters.
3. Start the Windows agent: `python server/agent_server.py`, with `OMNIFORGE_AGENT_KEY` set to a random secret and Ollama running.
4. In the remote agent chat, ask: "Import my conversations.json from this workspace, then search for my IPA build history." The agent uses `knowledge_import` and `knowledge_search` tools.
5. Keep your workspace private; don't commit the exported files or database. The imported content is local and may include sensitive information.

The repository does not automatically have access to every prior conversation. Only the exported/imported records become searchable. The SQLite database is located at `OMNIFORGE_WORKSPACE/.omniforge-private/knowledge.sqlite3`.

To run tests: `python -m unittest discover -s server -p 'test_*.py'`.

**Security:** Local agent tools are not a trust boundary against malicious code already running under your account. Use a private workspace and review imported material before giving it elevated permissions.
