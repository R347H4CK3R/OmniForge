# Unified install source proposal

## Outcome
One stable public JSON source lists separately installable iOS apps from the user's repositories. It does not combine app binaries or change bundle identifiers, containers, signing, or existing catalogs.

## Approaches
1. Recommended: aggregate an explicit allowlist of existing release feeds into an additional catalog. Preserve their original immutable asset URLs and app identities. This minimizes changes to active projects.
2. Scan every repository and publish every newest IPA. Rejected: private analysis inputs, prototypes, and failed builds could become install suggestions.
3. Combine apps into one IPA. Rejected: incompatible app identities, signing and runtime requirements; does not meet the source-catalog goal.

## Proposed implementation
- Add a separate unified-source.json; preserve livecontainer-source.json and android-source.json unchanged.
- Maintain an explicit registry of eligible repositories, bundle IDs, source paths, release channels, and required evidence.
- Accept only accessible public release assets with valid IPA structure and matching actual Info.plist bundle ID, version, build and minimum OS. Verify asset byte count and available SHA-256/provenance evidence.
- Require each app's existing verification gates. Preserve explicit experimental/device-testing limitations; do not call simulator verification physical-device validation.
- Select versions using actual app metadata and approved channel, not repository-wide latest release or counters from different workflows.
- Preserve the last-good app entry if its proposed update fails verification. Publish atomically only after catalog regression checks pass.
- Deduplicate by bundle ID; exclude APKs, Windows packages, private analysis inputs, source-only projects and empty download placeholders.
- Public polling can use the existing repository workflow token, without creating new credentials or granting cross-repository write access. A scheduled refresh is eventually consistent, not instantaneous.

## Evidence and starting scope
VoiceMatrix has a current public 0.4.1 character-test feed with matching release size but physical iPhone verification pending. OmniForge has a public feed and post-release updater, and its 1.1.56/build 156 IPA metadata was inspected and matches the existing feed. The current workflow's future marketing-version setting differs, so the aggregate always reads actual IPA metadata. Veyra/GhostAI has no default-branch feed or public releases at audit time. Madeira apps.json is intentionally empty. BOZ is experimental and its newer prerelease must not be automatically promoted without verification. DukeX's copied source targets an upstream project, not the user's fork.

Other candidates (Afterlight, CS2, Zombies) have public IPA releases but no inspected release feed; require artifact-level checks and explicit channel designation. Private workbench input IPAs are excluded.

## Validation
Unit tests must cover duplicate IDs, missing/invalid assets, failed gates, partial refresh, monotonic per-app updates, cross-workflow version counters, immutable URL matching, private source exclusion and last-good preservation. Integration checks inspect actual public IPA metadata and source refresh behavior. Existing app build checks are required if their build/version logic changes; this catalog-only addition does not modify native clients.

## Publication choices
The additional public catalog is hosted in OmniForge. Existing feeds remain unchanged. User requested proceeding with the combined source, descriptions, screenshots where genuine reviewed media is available, and live activity logs. Experimental VoiceMatrix limitations remain visible; missing screenshots are stated honestly.
