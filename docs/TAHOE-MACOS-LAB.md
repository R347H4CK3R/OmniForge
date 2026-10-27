# OmniForge macOS Tahoe IPA Toolchain Lab

**Status:** GitHub Actions workflow added; execution and built artifacts must be verified separately.

## Why this architecture
Apple's macOS Tahoe license limits macOS to Apple-branded computers. This repository therefore uses GitHub's hosted Apple macOS 26 (Tahoe) runner for an authentic Xcode environment, rather than bundling a Hackintosh VM on a Windows PC.

The Tahoe runner is an **ephemeral virtualized build environment**, not an interactive permanent macOS desktop on your Windows laptop. It runs on GitHub infrastructure only while a job is scheduled. It is not an iPhone emulator, and no claim is made that a physical iPhone was tested.

## Tools available through the job
- Xcode, iOS SDK, Swift, Clang and linker
- Apple command line tools: `xcrun`, `codesign`, `otool`, `lipo`, `plutil`
- iOS Simulator inventory via `simctl`
- Optional XcodeGen installation, iOS compilation and unsigned IPA packaging
- Logs and results uploaded as an Actions artifact

## Use
Go to **Actions → macOS Tahoe IPA Toolchain Lab → Run workflow**. Leave optional build off to get an environment inventory or turn it on to attempt an OmniForge unsigned IPA build. Download the artifact when the run has completed successfully.

The existing **Build OmniForge iPhone IPA** and **Publish OmniForge LiveContainer Update** workflows remain unchanged. This lab build deliberately omits the very large offline GGUF bundle; it is for compile verification. The existing full workflow is still needed for the bundled-model IPA.

The workflow does not automatically connect to your local Windows files; upload only files you own or are authorized to process, and avoid public releases for third-party IPAs. The existing IPA Workbench workflow is intended for release assets and includes static analysis workflows.

### Future
Connect the Windows job queue with authenticated GitHub workflow dispatch, status monitoring, artifact retrieval and tool-specific diagnostics. A Windows GUI can show macOS build logs. The iPhone app can command the same jobs through the authenticated Windows agent. Real desktop virtualization is only supported on compatible Apple hosts subject to Apple's license.
