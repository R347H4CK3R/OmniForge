# OmniForge two-platform release verification — November 3, 2026

One repository: R347H4CK3R/OmniForge. Swift iOS client in App/, native Kotlin Android client in android/, shared contracts in shared/, private host services in server/ and windows/.

## Delivered artifacts

- Android 1.0.17: https://github.com/R347H4CK3R/OmniForge/releases/download/android-17/OmniForge-Android.apk
- Android source: https://raw.githubusercontent.com/R347H4CK3R/OmniForge/main/android-source.json
- iOS 1.1.56: https://github.com/R347H4CK3R/OmniForge/releases/download/lc-156/OmniForge-LiveContainer.ipa
- LiveContainer source: https://raw.githubusercontent.com/R347H4CK3R/OmniForge/main/livecontainer-source.json

Android APK SHA-256: `6dbac3d56a1087d891786c399bfa66c4c1cf3c9bae40f00d59c995a68c6c0b0f`.

## Evidence

- 49 Python server tests, 9 Android host/catalog tests, 9 Android JVM policy tests, and 3 Android 15 instrumentation tests passed.
- Android build/lint/native ABI compilation, local GGUF inference, missing-model handling, and actual full-screen landscape geometry for both remote modes passed: https://github.com/R347H4CK3R/OmniForge/actions/runs/41674022085
- The exact signed Android 1.0.17 APK installed, launched, opened both remote modes in landscape, and produced screenshots: https://github.com/R347H4CK3R/OmniForge/actions/runs/41676149240
- Downloaded APK hash matches its catalog. `apksigner verify` passed and its certificate matches the stable release keystore. ARM64, ARMv7, x86-64 native libraries, shared assets and 16 KiB ZIP alignment were checked.
- iOS LiveContainer build and publication passed: https://github.com/R347H4CK3R/OmniForge/actions/runs/41672228642 . Intel macOS runners resolve the observed hosted ARM runner acquisition failure.
- Private HTTPS Android host rejected unauthenticated requests. Source ZIP upload/extraction, real Android SDK build, authenticated APK download and hash verification passed on the Windows laptop.
- A deliberately introduced Java compiler error was detected; source was repaired via the API and the next SDK build passed. This verifies the build/error/edit/rebuild pipeline, not universal AI reasoning.
- JADX decompilation, apktool resource decoding/rebuilding and separate development-key signing passed on an authorized generated sample APK. Apktool is pinned to 2.11.1 after a 3.0.3 resource-link failure.
- Online model connection and structured Android-owned agent replies passed against the installed qwen2.5-coder:1.5b model. Actual model tool selection for workspace listing and host SDK build passed. The Android-specific endpoint avoids nesting the old Windows agent loop.
- VNC authentication and a 1920×1080 desktop initialization passed through private HTTPS/WebSocket.
- Terminal login, WebSocket PTY and an actual computed PowerShell result passed through private HTTPS. The startup task was repaired; it uses a process-scoped policy for the owned startup script.

## Runtime boundaries and setup

The onn 100135925 Android 15 tablet was identified from the supplied photo, but no physical tablet was connected through ADB. Emulator evidence does not establish its memory, touch, rotation, or model performance. The iPhone's new landscape behavior also requires its physical-device check. CI is outside the user's Tailscale network, so remote-view screenshots verify layout while the laptop verifies the authenticated services.

Import a compatible GGUF for offline inference, or configure the private online API key. Workspace edits remain a user-controlled setting. Private laptop services require Tailscale on the mobile device. Android installation/update confirmation remains an OS requirement.

SDK builds and advanced APK decompilation/rebuilds use the laptop. APK decompilation does not recover exact original source, and a successful build does not prove an arbitrary imported app's functional equivalence. Native UI changes still require deliberate equivalent edits on both platforms; AGENTS.md and both-platform CI enforce the review/check workflow, not automatic Swift/Kotlin translation.

Stable Android release signing material is kept in repository secrets and the owner's protected laptop backup; none is committed. Resource rebuilds use a separate development key. Model service weights unload after 30 seconds idle; the private workbench itself measured about 26 MiB idle before adding the terminal/model service processes.
