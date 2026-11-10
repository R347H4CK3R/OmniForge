# Project/build readiness, first increment

Extend OmniForge rather than creating another app. The user delegated engineering choices and requires a completely free solution. This increment gives its existing authenticated host a truthful, read-only picture of nearby projects, local build prerequisites and the existing durable queue. It does not launch builds, create accounts, dispatch paid runners, install updates, or change jobs, credentials or application identities.

## Approach

A new native project-manager screen is the eventual destination, but immediately wiring execution into the old queue is unsafe: constructing `JobQueue` requeues running work. A separate new service would duplicate authentication. The chosen first step is a standard-library report attached to the existing authenticated host, also usable as a local CLI. Both native clients can consume the same JSON API. No native-client changes ship in this increment.

## Contract

- Inspect the workspace itself and at most 100 immediate directory entries. Hidden entries count toward the budget but are not inspected. Project marker scans have the same bound and propagate truncation. Do not recursively search the user's computer or follow symbolic links outside the workspace.
- Recognize Android, Node/web, Python and Xcode project markers without executing or reading project-supplied code.
- Report detected local prerequisites separately from verified compilation. Local iOS requires macOS/Xcode; no remote Mac is presumed available. All build verification and remote-runner states begin unverified/not configured.
- Read at most 30 queue records using SQLite read-only mode. Never instantiate `JobQueue`, reset running jobs, create a database, or expose prompts/results. Reject WAL/pending-journal databases rather than creating sidecars or ignoring uncheckpointed data. Reject malformed metadata with a sanitized blocker.
- Reuse the current Bearer authentication for `GET /v1/projects`; cache-control is no-store. Keep `/health` unchanged. Invalid/missing queue data becomes a visible sanitized blocker rather than a server crash.
- No SDK installs, downloads, network checks, token changes, service restarts, app update, or billing changes.

## Non-goals and constraints

This is the dashboard backend, not an autonomous all-project manager. Build dispatch, per-project authorization, job ownership/recovery, mobile UI and verified Mac-runner integration remain later work. A detected compiler does not prove an SDK is licensed, configured or functional. Existing Android and iOS data containers and installed services are unchanged.
