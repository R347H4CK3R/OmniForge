# OmniForge: Autonomous Development + Reciprocal Remote Access

Status: proposed integration architecture. Nothing in this document implies successful device testing.

## Scope and platform limitations

- iPhone -> Windows: full Windows desktop viewing and mouse/keyboard control through an explicitly authorized remote desktop session (for example RustDesk). Tailscale provides the private network path; never expose RDP or an unauthenticated control service to the public Internet.
- Windows -> iPhone: screen **viewing** through a user-initiated ReplayKit Broadcast Upload Extension. The viewer uses an authenticated, encrypted transport. This is not equivalent to Windows controlling arbitrary iPhone apps.
- Windows -> OmniForge iPhone app: restricted in-app navigation and commands are possible with an authenticated, opt-in command protocol; no synthetic taps outside OmniForge.
- General-purpose Windows -> iPhone remote touch injection: **not supported** by standard iOS public APIs. Apple's iPhone Mirroring remote control requires a compatible Mac, not a Windows PC. Do not label viewing-only as full control.
- Broadcast and remote-control sessions must display visible session state, permit immediate termination, and require device-owner consent.

## Security and connection design

1. Keep Windows host bound to loopback. Tailscale Serve can expose only the authenticated application endpoint over HTTPS to trusted tailnet devices.
2. Do not reuse the AI-host bearer key for remote desktop access. Use per-session short-lived credentials, explicit user approval and a visible disconnect/stop button.
3. For iPhone screen broadcasts, use ReplayKit picker and a Broadcast Upload Extension; store no frames by default. Protect any optional recording with user opt-in.
4. Require authorization checks on all Windows file mutations and shell invocations. Prefer isolated per-project workspaces, execution deadlines and per-task cancellation.
5. Treat imported IPA binaries and projects as untrusted. Never execute discovered code merely as part of inspection. Redact secrets from logs.
6. Keep audit logs of commands and mutations; support rollback via snapshots and Git branches.

## End-to-end development loop

- **Plan**: turn user request into explicit repository paths, expected changes, tests, build target, and acceptance criteria.
- **Act**: edit project files in authorized workspace, on a unique Git branch, using structured tool calls; differentiate read-only from mutation.
- **Build**: select Windows toolchain or hosted macOS/Xcode for iOS targets, run real compiler and linker, and collect exit codes/artifact checksums.
- **Observe**: parse build logs and test results; apply bounded repairs with before/after diff and reproducible logs.
- **Verify**: run unit, integration and smoke tests, run app on actual iPhone when available, inspect screenshot/video, and separately confirm signing/install.
- **Report**: explicitly distinguish implemented, built, installed and verified. Never claim an arbitrary IPA can be transformed into its original sources.

## IPA reconstruction stages

1. Validate ZIP structure and identify binaries/assets, entitlements, frameworks, architecture, and encrypted segments.
2. Generate reversible extracted resource inventory and Ghidra/LLVM intermediate reports using an authorized desktop or hosted toolchain.
3. Produce a new, independently authored buildable project *scaffold*, importing redistributable resources only with rights.
4. Validate compilation and functional equivalence via user-supplied test cases. Missing logic must remain a reported limitation.
5. Require authorized signing/provisioning and on-device test. Original source reconstruction is not guaranteed.

## Acceptance tests (not yet passed)

- [ ] iPhone sends authenticated request over cellular and Windows host executes a read-only workspace operation.
- [ ] iPhone views Windows desktop with observable frames and sends a click and keyboard input under an active authorized session.
- [ ] Windows viewer receives a user-initiated ReplayKit broadcast from iPhone and stop immediately ends frame delivery.
- [ ] Windows can invoke an authorized command *inside OmniForge* without manipulating other iPhone apps.
- [ ] Windows-to-iPhone general system control is prominently marked **unsupported** rather than simulated.
- [ ] A sample cross-platform project is generated, edited, compiled, test-executed, then rebuilt after an intentionally introduced failure.
- [ ] iOS build creates a checked IPA; separate physical-device launch and offline inference succeed.
- [ ] IPA analysis produces deterministic reports; generated scaffold is labeled original placeholder code and builds independently.
- [ ] Disconnect, token rotation, incorrect credentials, denied permission, and mid-stream cancellation all fail safely.
- [ ] All report claims are linked to collected build/test logs and exact commit SHA.

See `windows/Test-OmniForgeRemoteReadiness.ps1` for a local, read-only prerequisite test. It does not start a remote-control session.
