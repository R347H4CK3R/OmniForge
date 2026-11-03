# Private Windows terminal

The deployed terminal uses WeTTY 4.2.1 on loopback port 8788, with the authenticated proxy on loopback port 8789. Tailscale Serve mounts it at `/terminal`. The iOS and Android clients open the same private HTTPS endpoint.

For a new host: install Node.js and `npm install --global wetty@4.2.1`, copy these source files to `%LOCALAPPDATA%\OmniForgeTerminal`, and run `npm ci` there. Provide a user-chosen `terminal-password.txt` in that private folder; the proxy generates its session secret if absent. Never commit either credential file. Match the private origin in `auth-proxy.js` and `start-terminal.ps1` to the host's Tailscale HTTPS address.

Run `register-task.ps1` to register the startup task. Its process-scoped execution-policy argument fixes the observed task failure without changing the machine's PowerShell policy.

`verify-command.js` authenticates over private HTTPS, opens the WebSocket PTY, and checks a computed PowerShell result rather than treating echoed input as command execution. It reads the private password file and does not print credentials.
