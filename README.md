# OmniForge

**Your AI. Your Device. Your Rules.**

OmniForge is an open-source project for a native, fully offline iPhone AI assistant and developer toolkit. The goal is to provide useful local intelligence and user-controlled tools **without subscriptions, paid AI APIs, telemetry, daily message quotas, or deliberately locked features**.

> **Status: early source prototype.** GitHub Actions builds unsigned IPA artifacts; successful launch and on-device offline inference still require testing. Runtime functionality, iOS compilation, signing, and physical-device tests must be completed and verified before claiming a working release.

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
6. The bundled GGUF should load automatically when the app opens; confirm this with airplane mode enabled. Importing a different compatible GGUF is optional.

Building may use free GitHub Actions minutes subject to GitHub's current quotas and runner availability. The GitHub Actions workflow now downloads a Qwen2.5 0.5B Instruct Q4_K_M GGUF model during the build and embeds it in the IPA. This makes the installed app self-contained for basic local chat. The model is approximately 400 MB and is distributed under Apache-2.0; see https://huggingface.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF . Other imported models retain their own licenses.

## Privacy and legal scope

OmniForge is designed to avoid subscriptions and paid hosted APIs. File access should follow iOS's permission and document-picker mechanisms. Repackaging, reverse engineering, or modifying binaries must respect applicable law and rights. Running arbitrary downloaded code in the iOS sandbox is not equivalent to full access to iOS or Xcode.

## Roadmap

- [ ] Publish the renamed OmniForge source tree and build configuration
- [ ] Pass reproducible Xcode/iOS compile checks
- [x] Add a GitHub Actions unsigned IPA packaging workflow\n- [x] Add build-time download and inclusion of a starter GGUF model\n- [ ] Verify that the all-in-one IPA passes GitHub Actions
- [ ] Verify app launch, local model import, and streamed offline chat on a physical device
- [ ] Verify each local plugin with tests and representative files
- [ ] Add opt-in offline voice support
- [ ] Improve accessibility, troubleshooting and plugin documentation


## IPA workbench (in development)

In Chat, tap **+ → Inspect IPA**, and choose Metadata, File inventory, Mach-O report, Signing structure, or Export supported resources. The export command saves selected non-executable files to the app's Documents/IPAExports directory (visible in Files → On My iPhone → OmniForge after file sharing is enabled). All processing is local. Files larger than 1 MB remain attachable when recognized as IPA archives; ordinary text chat attachments remain limited to 1 MB.

**Security/technical limits:** archive-path checks, entry count/size limits and bounded resource export are built in. Code-signature reports describe the presence of related files only, not validity. The application does not execute imported IPAs or establish that they can be installed. Reconstructed source cannot be assumed identical to original source. Arbitrary repackaging, binary rewriting, full disassembly, cryptographic signature verification and signing are not yet implemented. Modified apps need valid re-signing to install.


## Optional GitHub Actions IPA workbench

The separate **IPA Workbench (macOS)** workflow accepts an IPA stored as an asset on a GitHub Release in this repository. Start the workflow manually from Actions, provide the exact release tag and IPA asset name, and retrieve the analysis artifact. It uses macOS `otool`, `codesign` and a bounded Python ZIP inspector; it **does not** reconstruct exact original source code.

To make a modified unsigned IPA, additionally provide a replacement resource asset name and its exact path inside the IPA (for example `Payload/Example.app/settings.json`). Only known non-executable file extensions are permitted. Do not publish proprietary IPA assets to a public release unless you have redistribution rights. Private repositories or authorized self-hosted workflows are preferable for sensitive app packages.

The iPhone interface includes an offline reconstruction **report** under **+ → Inspect IPA → Create reconstruction report**; it saves metadata and the file inventory to the app Documents folder. This is not a compilable project or decompiler.

Signing requires a legitimately controlled Apple signing identity and provisioning profile. This workflow deliberately does not accept or store signing credentials and produces unsigned/invalidated-signature repackaged IPAs. The official app build workflow still runs separately and requires a real-device launch test.

## Advanced macOS workflows

The `IPA Workbench (macOS)` manual workflow provides capped Mach-O disassembly excerpts using `llvm-objdump`, `otool` dependency inspection, code signature diagnostics, safe resource modification, and a **new clean-room SwiftUI scaffold** generated from basic IPA metadata. The scaffold is original placeholder code, **not recovered source or a functioning clone**, and compilation must be independently validated.

The separate `Sign authorized IPA (macOS)` manual workflow needs a valid Apple signing identity and an appropriately matching provisioning profile. Configure these in GitHub repository settings: Actions secrets `IOS_SIGNING_CERT_BASE64` (base64 .p12), `IOS_SIGNING_CERT_PASSWORD` and `IOS_PROVISIONING_PROFILE_BASE64` (base64 .mobileprovision), and Actions variable `IOS_SIGNING_IDENTITY` (identity string from `security find-identity -v -p codesigning`). Supply a release tag and IPA asset filename when running the workflow. Never place signing secrets in a public issue, commit, or release.

These flows are optional and require GitHub network access and macOS runners. A successful macOS codesign check does not guarantee installability: the selected certificate, app identifier, entitlements, target device and provisioning profile must all be compatible. This has not been tested with an actual signing identity.

## Contributing

Issues and pull requests are welcome. Keep default functionality offline, avoid paid API dependencies, disclose third-party licenses, and include reproduction steps or tests with bug reports.

## License

Intended project code license: **MIT** (add a LICENSE file with the source). Dependencies, Apple frameworks, and downloaded model weights retain their respective terms.

---

**Repository:** https://github.com/R347H4CK3R/OmniForge
