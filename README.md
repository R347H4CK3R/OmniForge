# OmniForge

**Your AI. Your Device. Your Rules.**

OmniForge is an open-source project for a native, fully offline iPhone AI assistant and developer toolkit. The goal is to provide useful local intelligence and user-controlled tools **without subscriptions, paid AI APIs, telemetry, daily message quotas, or deliberately locked features**.

> **Status: early source prototype.** This repository does not yet contain a verified, installable OmniForge IPA. Runtime functionality, iOS compilation, signing, and physical-device tests must be completed and verified before claiming a working release.

## Design principles

- **Offline-first:** conversations, AI inference, files, and tool execution stay on the device.
- **No artificial usage caps:** no account, subscription, daily message cap, credit system, or cloud key to enable core features.
- **User-controlled tooling:** tools operate on user-selected files, and no hidden cloud calls are required.
- **Open source:** source code can be inspected, modified, and built independently.
- **Honest engineering:** do not claim unsupported abilities, successful builds, or completed features.

No artificial restrictions does **not** mean bypassing iOS entitlements, code signing, device sandboxing, model memory/context limitations, third-party licenses, or applicable law. Some operations require software or hardware not available in an offline iOS sandbox. No local model can be guaranteed to match ChatGPT's capabilities.

## Intended capabilities

| Area | Design |
| --- | --- |
| Offline chat | GGUF-based local model inference via llama.cpp / SwiftLlama |
| Models | Import user-owned, appropriately licensed GGUF models from Files |
| History | Local conversation storage and deletion |
| Programming | Code assistance, explanation, analysis and generation |
| IPA analysis | Inspect authorized IPA/ZIP packaging, metadata, and logs |
| Build diagnostics | Analyze saved Xcode and GitHub Actions log files |
| File utilities | JSON/plist formatting, SHA-256, text/CFG/INI/Markdown inspection |
| Images | Apple Vision OCR and image metadata where implemented |
| Security | Redact likely secrets in user-selected text |
| Future extensions | Local speech recognition, text-to-speech, enhanced code/project tooling |

**Not yet available or not guaranteed:** autonomous on-device Xcode toolchain builds, reconstruction of original source code from arbitrary IPA binaries, downloading or searching web content while offline, full-access filesystem operations, or unlimited hardware resources. A practical offline assistant should clearly report when a tool or task is unsupported.

## Planned technology

- SwiftUI native iOS interface (iPhone-first, iOS 17+ target)
- [llama.cpp](https://github.com/ggml-org/llama.cpp) via [SwiftLlama](https://github.com/pgorzelany/swift-llama-cpp)
- Apple Vision, CryptoKit, UniformTypeIdentifiers and native Files picker
- XcodeGen project generation; GitHub Actions macOS runner for unsigned IPA builds

## Build and installation plan

1. Add the complete Swift source tree, `project.yml`, license, and `.github/workflows/ios-unsigned.yml` to this repository.
2. On a Mac with compatible Xcode and [XcodeGen](https://github.com/yonaskolb/XcodeGen), run `xcodegen generate`.
3. Compile for a physical iPhone target and resolve any actual compiler or package errors.
4. Alternatively, start the provided GitHub Actions iOS workflow **after it has been committed**. Its outcome must be checked; an artifact is not proof of an app that launches.
5. A successful build may produce an **unsigned** IPA. Sign/provision it through a valid method supported on your device before installing. An unsigned IPA is not directly installable.
6. Import a compatible, legally acquired instruction-tuned GGUF model (a small quantized model is a sensible initial test), then validate inference with the phone offline.

Building may use free GitHub Actions minutes subject to GitHub's current quotas and runner availability. Model weights are separate from the app; review their own license and size before use.

## Privacy and legal scope

OmniForge is designed to avoid subscriptions and paid hosted APIs. File access should follow iOS's permission and document-picker mechanisms. Repackaging, reverse engineering, or modifying binaries must respect applicable law and rights. Running arbitrary downloaded code in the iOS sandbox is not equivalent to full access to iOS or Xcode.

## Roadmap

- [ ] Publish the renamed OmniForge source tree and build configuration
- [ ] Pass reproducible Xcode/iOS compile checks
- [ ] Produce an unsigned IPA using GitHub Actions
- [ ] Verify app launch, local model import, and streamed offline chat on a physical device
- [ ] Verify each local plugin with tests and representative files
- [ ] Add opt-in offline voice support
- [ ] Improve accessibility, troubleshooting and plugin documentation

## Contributing

Issues and pull requests are welcome. Keep default functionality offline, avoid paid API dependencies, disclose third-party licenses, and include reproduction steps or tests with bug reports.

## License

Intended project code license: **MIT** (add a LICENSE file with the source). Dependencies, Apple frameworks, and downloaded model weights retain their respective terms.

---

**Repository:** https://github.com/R347H4CK3R/OmniForge
