# IPA project pipeline

Audit snapshot: 8 November 2026. Public projects only; private repository contents are not listed.

The catalog installs separately versioned apps from public release URLs. These additional projects currently have CI artifacts, not permanent public IPA release downloads. They remain pending archive, identity, dependency and content checks plus release publication. Successful compilation is not proof of working gameplay.

- **PocketForge**: [successful build run](https://github.com/R347H4CK3R/PocketForge/actions/runs/42518096757); metadata fixed and fresh native build passed. New IPA still needs archive inspection before public release.
- **madeira-cod-test**: [successful build run](https://github.com/R347H4CK3R/madeira-cod-test/actions/runs/40346816186); obsolete PocketForge artifact sharing the PocketForge identity, not a separate Madeira app. Current Madeira development must be reviewed independently.
- **BO2-IOS-CS**: [successful build run](https://github.com/R347H4CK3R/BO2-IOS-CS/actions/runs/36003097069); BO2IOSCS-Xash-integrated-IPA. Not yet promoted into a permanent public release; required notices and provenance are under review.
- **BO2CS**: [successful build run](https://github.com/R347H4CK3R/BO2CS/actions/runs/35542001636); the final GameName-unsigned-IPA passed structural validation; original MIT prototype with SDL/JSON notices. Simulator receipt and release readiness are under review.
- **CSNZ-iOS**: [successful build run](https://github.com/R347H4CK3R/CSNZ-iOS/actions/runs/36201512410); CSNZ-iOS-ARM64-runtime. Not yet promoted into a permanent public release; required notices and provenance are under review.
- **Hijacked-Quake3-iOS-**: [successful build run](https://github.com/R347H4CK3R/Hijacked-Quake3-iOS-/actions/runs/35221891882); Hijacked-Quake3-iOS-stabilized-v2-unsigned-IPA. Not yet promoted into a permanent public release; required notices and provenance are under review.
- **-Native-Zombies-iOS**: [reviewed prototype release](https://github.com/R347H4CK3R/-Native-Zombies-iOS/releases/tag/prototype-1.0-build1) is now public; catalog admission is gated on automated verification. Twenty simulator unit tests passed; physical-device gameplay remains untested.
- **COD4iOS-COD4NS**: [successful build run](https://github.com/R347H4CK3R/COD4iOS-COD4NS/actions/runs/38847728229); cod4ios-mw3-diagnostics-unsigned. Diagnostic build, not verified full-game behavior.

DukeX has historical successful IPA runs but no retained artifacts in the latest inspected run; its copied source references an upstream project rather than this fork. BO2-Native-iOS currently reports source checks without an IPA. Madeira's canonical release feed is empty. StrataForge-Playport and piper-objc have no successful app-release run in this audit. Android packages are separate from the iOS catalog.

The current installable catalog and detailed app cards are in [Chris's Apps](APPS.md). This pipeline is not an install source and does not publish build-artifact download URLs.
