# Two native apps, one repository

| Feature | iOS | Android |
|---|---|---|
| Native UI | SwiftUI in App/ | Kotlin platform views in android/ |
| Package workbench | IPA metadata/Mach-O/resource tools | APK manifest/dex/ABI/permission inventory |
| Source and SDK build | Existing macOS workflows | Authorized laptop Gradle/Android SDK project build |
| Decompilation | Existing IPA analysis workflows | Laptop JADX; Java-like output is not original source |
| Local AI | Existing SwiftLlama integration | Pinned llama.cpp JNI, imported GGUF |
| Agent | Local tools / private compatible host | Local JSON tools / private compatible host |
| Desktop and terminal | Full-screen landscape sessions | Full-screen sensor landscape sessions |
| Installation | Existing LiveContainer source | Stable signed APK + android-source.json |

The same repository houses both clients, shared/features.json, and server/. Native clients do not automatically translate each other's edits. AGENTS.md requires matching shared behavior changes in both clients; shared-platforms.yml compiles iOS on either client/common changes, and android.yml builds/tests Android on common changes. Add device acceptance evidence before claiming parity.

Android source URL after the first successful publish:
https://raw.githubusercontent.com/R347H4CK3R/OmniForge/main/android-source.json

Install the release APK, then use Settings → Check APK updates. SHA-256, application ID, version and installed signer are checked. Android confirmation is required. Store the release keystore securely; repository secrets ANDROID_KEYSTORE_BASE64 and ANDROID_KEYSTORE_PASSWORD preserve the identity across builds. Never publish a debug APK as the stable release.

## Tablet setup
Import a small instruct GGUF (0.5B Q4 recommended to begin) in Settings. Files are copied into app-private storage. Enable offline mode for local inference. Context, token output and tool iterations are bounded to fit tablet resources, not subscription quotas. Chat history and files are local; backups are disabled so API tokens do not enter ordinary Android backups.

Online mode supports compatible HTTPS completion servers. The configured private laptop Android endpoint is /android-api/v1/android/completions; it returns structured model replies to Android’s own tool loop instead of nesting the Windows host agent. The installed qwen2.5-coder:1.5b model is the default. Supply its API token in Settings. No public AI provider is required. For remote desktop/terminal, connect Tailscale on the tablet and enter the private endpoint. The noVNC password is entered into its own page.

Laptop Android tools require JDK 17, Android SDK, Gradle and optionally JADX. Start the updated server/agent_server.py from a workspace with OMNIFORGE_AGENT_KEY and expose through existing private Tailscale HTTPS. Android Workbench operates on host-workspace paths. Gradle builds run project-supplied code, so select only trusted authorized projects. Generated APK paths and actual compiler errors are reported. The standalone server/android_host.py listener on 127.0.0.1:8791 can be exposed privately under /android-api without replacing OmniForgeHost.exe. scripts/setup_android_host.py installs portable tools; scripts/run_android_host.py loads the existing private API key.

The Android APK does not bundle a complete on-device SDK/compiler.

No installed app, local inference, reconstructed source, signing or physical-device behavior is called verified until its corresponding check has actually run. Emulator launch is separate from onn 100135925 physical-device verification.


The Android JSON tool agent can use `host_build_source` to upload its local Gradle workspace, run the actual host compiler, observe its errors, edit source and try again. Successful artifacts are downloaded into BuildOutputs/. `host_analyze_apk` transfers local APKs for host inspection/decompilation/resource decoding; `host_action` can list/read permitted source text and edit it only when the app's workspace-edit setting is enabled. Android installation still requires an explicit system confirmation. These are implemented tool calls, not a claim that a small local model reliably solves arbitrary development tasks.

## Project-manager foundation (read-only)

The host now exposes `GET /v1/projects` using the same Bearer key as its other protected endpoints. It reports local project markers, build-tool detection and stored job statuses without running project code or mutating the queue. Run `python server/project_dashboard.py <authorized-workspace>` locally for the same report without credentials or a server. Results are private to the configured workspace; do not publish the report if project names are private.

Both native clients include a manually refreshed host-readiness view in Projects, using their existing authenticated host connection. The standalone Android listener exposes the same path under its configured private proxy prefix. The clients preserve that prefix, reject redirects, bound response size and deadlines, and cancel pending requests when leaving the view or backgrounding the app. Empty, partial, unsupported-host and authentication failures remain explicit. No app identifiers, signed packages, saved settings or data containers change. Existing installed host binaries do not automatically gain this endpoint and must not be replaced while jobs run. These changes require a new client build and a separately deployed compatible host before installed apps can use the screen.

Only the workspace and up to 100 immediate entries are inspected, with hidden entries counting toward the budget but never inspected as projects. Per-project marker enumeration has the same bound, and any truncated scan is flagged. Deeper or external repositories are not automatically searched. `prerequisites_detected` is not a successful build: dependencies, SDK versions, licenses, tests, signing and physical installation still require separate verification. Queue status is stored metadata, not proof that a worker is alive. Prompts/results are excluded, and merely viewing the report never requeues a running job. WAL-mode or pending-journal queues are reported unavailable rather than risking sidecar writes or presenting a stale snapshot; the existing default rollback-journal queue is supported.

### Secure laptop coordinator and Mac workers

The Windows laptop can host the private coordinator, edit authorized repository worktrees, run Android/web/Python checks, and collect logs/artifact checksums. The separate local-only `ProjectWorkspace` module now supports an explicit private project allowlist, bounded source reads, hash-checked replacement of existing files with private backups, and one fixed Python unittest recipe. Its registry is absent by default, so no project is enabled. It is not connected to HTTP, the native UI, the queue or Git push. See [the workspace contract](project-workspace.md) for the authorization boundary, process containment and remaining limitations. A future dispatcher still needs isolated branches/worktrees, fixed build recipes and per-job commit IDs. Project scripts are executable code and must be trusted before dispatch; the check runner is not a filesystem or network sandbox. Keep uncommitted user edits and live jobs intact. Do not grant pull-request code access to persistent host credentials.

iOS compilation must run on a real, authorized Mac with Xcode. The laptop may send an approved commit/build recipe to that Mac and track its result; a Windows runner cannot become a Mac runner. The report deliberately marks remote Mac dispatch as not configured. A provider's advertised free tier is not a verified account allowance or unlimited capacity. No account, runner registration token, persistent credential or paid usage is created by this increment. Existing credentials stay in their existing stores and must never be embedded in app bundles, repository files or logs.

Before enabling dispatch: confirm the Mac is accessible, its exact zero-cost capacity, repository access scope, artifact return path, and cancellation behavior. If new persistent access is needed, obtain the required approval before provisioning it. Verify build/tests for the exact commit before publishing; installation still follows each platform's signed update flow and preserves the existing data container.
