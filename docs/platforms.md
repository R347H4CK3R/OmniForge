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

Online mode supports your own HTTPS /v1/chat/completions server, including the existing private laptop agent. Supply its API token in Settings. No public AI provider is required. For remote desktop/terminal, connect Tailscale on the tablet and enter the private endpoint. The noVNC password is entered into its own page.

Laptop Android tools require JDK 17, Android SDK, Gradle and optionally JADX. Start the updated server/agent_server.py from a workspace with OMNIFORGE_AGENT_KEY and expose through existing private Tailscale HTTPS. Android Workbench operates on host-workspace paths. Gradle builds run project-supplied code, so select only trusted authorized projects. Generated APK paths and actual compiler errors are reported. The standalone server/android_host.py listener on 127.0.0.1:8791 can be exposed privately under /android-api without replacing OmniForgeHost.exe. scripts/setup_android_host.py installs portable tools; scripts/run_android_host.py loads the existing private API key.

The Android APK does not bundle a complete on-device SDK/compiler.

No installed app, local inference, reconstructed source, signing or physical-device behavior is called verified until its corresponding check has actually run. Emulator launch is separate from onn 100135925 physical-device verification.
