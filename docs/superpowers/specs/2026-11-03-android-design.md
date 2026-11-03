# OmniForge Android companion

Approved direction: two independently installable native apps in R347H4CK3R/OmniForge. Swift iOS remains IPA/iOS focused; Kotlin Android targets Android apps, first tested on Android 15 (onn 100135925). Existing iOS location stays App/ to preserve build workflows.

Use native Kotlin with platform views to keep tablet memory/dependency cost low. Reuse the private OpenAI-compatible agent service, remote HTTPS desktop and terminal, shared feature contract and release infrastructure. Keep GGUF inference local through pinned llama.cpp JNI; import models through Android's document picker. Keep secrets private and never include passwords in a public catalog.

Android delivers persisted chat/settings/workspace, local JSON tool loop, GGUF import and offline generation, APK metadata/dex/resource/signature inspection, editable source projects, authenticated laptop APK analysis/rebuild jobs, full-screen landscape desktop/terminal, diagnostics, and a signed APK catalog/update installer. Decompilation cannot recover exact original source and compilation is not behavioral equivalence. SDK-based builds use a host; the APK must accurately report this dependency.

Shared changes require both platform checks. Common service/contract changes have one implementation where possible. Native UI behavior requires explicit matching platform edits; CI cannot automatically translate Swift into Kotlin. An AGENTS.md rule and feature matrix document the coupling. Android updates must preserve application ID and signing identity, verify SHA-256 and signer before installation, and require Android confirmation. The existing iOS install channel remains intact.

Alternatives considered: replacing iOS with a cross-platform rewrite risks established behavior; two unrelated repositories violate the requested maintenance model. Native apps plus shared backend/contracts preserve working iOS while adding Android-specific tooling.

Verification: host Python suite, JVM tests for archive traversal/URL/update validation, Android lint and assemble, ARM64/ARMv7 native compile, emulator launch and remote-layout checks where runner resources permit. Actual onn and iPhone touch/rotation/model behavior remain explicit device checks.
