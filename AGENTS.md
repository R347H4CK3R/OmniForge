# OmniForge platform maintenance
Keep one repository, two native apps. App/ is iOS and android/ is Android. Do not rename the existing iOS app ID, data container or update catalog.
When changing shared services, prompts, protocols, diagnostics, workspace behavior, remote desktop/terminal, chat or updates, inspect both clients. Apply equivalent behavior where meaningful in the same change. Explain deliberate platform differences in docs/platforms.md. Never claim automatic Swift/Kotlin translation or parity from a build alone.
Run Python server/script tests, Android unit tests/lint/build, and iOS compile for common changes. Never publish a failed build. Preserve stable Android signing secrets; never check in keys/passwords. Artifact success does not prove a physical device works.
