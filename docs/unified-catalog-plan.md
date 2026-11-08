# Unified source implementation plan

Goal: a public, additional iOS catalog; existing app feeds and identities stay unchanged.
Architecture: Python standard-library refresh command, explicit registry, immutable public release validation, inspected IPA metadata, atomic output and last-good retention. A scheduled GitHub workflow refreshes the catalog without cross-repository credentials.

1. Write failing tests for IPA metadata extraction, executable presence, URL/release validation, duplicate IDs, version rollback and last-good retention.
2. Implement isolated catalog generation in scripts/unified_catalog.py. Do not run app code or unzip arbitrary paths.
3. Register only current VoiceMatrix and OmniForge feeds, with their current release-channel restrictions. Keep additional candidates excluded until their artifacts and gates have been inspected.
4. Add manual/hourly refresh workflow, docs and an additional unified-source.json; keep updates separate from native application code.
5. Run new and existing Python suites, inspect real release IPAs, then review the branch. Publication is permitted by the user's Proceed instruction, but promotion to an established stable app feed remains separate.

Checks focus on redirects and credentials, private assets, malformed archives, cross-workflow counters, failed partial refreshes and retaining known-good entries.
