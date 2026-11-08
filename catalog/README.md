# Chris's Apps

One source, separately installable apps. Add the catalog URL to a compatible iOS source browser:

https://raw.githubusercontent.com/R347H4CK3R/OmniForge/main/unified-source.json

## OmniForge
**Offline AI developer workbench**

Import local GGUF models, inspect IPA files and work with development projects. Models are supplied separately. Requires iOS 17 or later and a configured LiveContainer or supported signing method. Release packaging is inspected; physical-device operation is not certified by this catalog.

[Original source](../livecontainer-source.json) · [Releases](https://github.com/R347H4CK3R/OmniForge/releases)

## VoiceMatrix
**Offline character speech and voice tools**

Import your own character folders, generate offline speech and convert recordings with local neural engines. No stock characters are bundled. Requires iOS 26. This is an experimental character-test edition: diagnostic speech and simulator conversion checks pass, while physical iPhone behavior and character likeness remain unverified.

[Original source](https://github.com/R347H4CK3R/Ghostline/blob/main/strata-source.json) · [Releases](https://github.com/R347H4CK3R/Ghostline/releases)

## AI assistant / Veyra
A source entry will appear after its verified public IPA and SideStore source are published. Build artifacts and placeholder downloads are not installable catalog releases.

## Screenshots
VoiceMatrix previews below are genuine automated iOS simulator captures of the development UI, using an empty character library and default demonstration text. They illustrate speech and conversion screens, not physical-device performance or an exact release certification. No imported character audio or private conversation is shown.

![VoiceMatrix speech simulator preview](screenshots/voicematrix-speech-simulator.png)
![VoiceMatrix conversion simulator preview](screenshots/voicematrix-conversion-simulator.png)

OmniForge screenshots are not yet available. No screenshots are fabricated.

## Versions, updates and live logs
The catalog lists each app's actual IPA version, build number, minimum iOS, download size and release notes. Icons come from each app's published source. Apps keep their own bundle IDs and data containers. This is a curated source, not Apple's App Store and not a promise that every app supports every installer.

The refresh workflow runs hourly and on registry changes. It validates public release assets, reads actual IPA metadata and checks supported release evidence before changing an entry. A failed update leaves the previous good entry in place. Experimental limitations remain visible.

[Live refresh runs and step logs](https://github.com/R347H4CK3R/OmniForge/actions/workflows/unified-source.yml). Open the newest running workflow to follow its steps. The downloadable verification report lists accepted and skipped entries; no credentials are used to fetch app feeds or binaries.

Other projects are excluded until their public IPA and verification evidence are ready. Android APKs, Windows downloads, private analysis inputs and blank source placeholders never enter this iOS catalog.
