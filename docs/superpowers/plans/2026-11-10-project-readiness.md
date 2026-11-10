# Project Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe read-only project, build-prerequisite and queue report to the existing OmniForge host.

**Architecture:** A standard-library module inspects bounded workspace markers and reads queue metadata without touching the queue implementation. The existing HTTP handler supplies authentication. A local CLI emits the same JSON.

**Tech Stack:** Python stdlib and existing HTTP server/SQLite.

**Spec:** `docs/superpowers/specs/2026-11-10-project-readiness-design.md`

## Global Constraints

- No dependencies, network access, credential changes or live-service replacement.
- At most 100 immediate directories and 30 job rows; never report a build as verified from detection.
- Preserve native IDs/data and existing queue state.

## Review Focus

- A directory or queue symlink pointing outside the workspace must not expose external metadata.
- An absent/corrupt database must not be created, repaired or requeued.
- Missing toolchains and non-macOS hosts must show blockers, not build success.
- Unauthorized requests must not inspect projects or disclose names.
- Large workspaces must remain bounded and explicitly indicate truncation.

### Task 1: Read-only report and endpoint

**Files:** Create `server/project_dashboard.py`, `server/test_project_dashboard.py`; modify `server/agent_server.py`, `docs/platforms.md`.

**Interfaces:** `project_dashboard.build_report(workspace) -> dict`; authenticated `GET /v1/projects` returns the dict. `python server/project_dashboard.py <workspace>` prints it without starting a server.

- [x] Write tests for mixed project markers, absent toolchains, false verification, queue preservation/redaction, missing/corrupt queue, symlink confinement, truncation and HTTP authentication/no-store.
- [x] Run `python -m unittest server.test_project_dashboard -v`; confirm failure because the report/route is missing.
- [x] Implement report and route. Use read-only SQLite connection, bounded metadata and no subprocess execution.
- [x] Run targeted tests and Python suites in `server`, `scripts` and `tests`, plus compileall. Record every failure.
- [x] Document common client API and deliberate native-UI deferral; commit locally and request independent code review.

## Execution record

Ruling: use an isolated source snapshot because the pre-existing catalog folder has no Git metadata and is shared with other work. All existing files edited in this increment are blob-verified against upstream commit `28b25998f14bfebe0a9caa93339cb2ec6980aa50`.

Baseline: 49 server tests passed. Native compile checks cannot run in this Linux environment; the connected laptop is Windows and no Mac environment is listed. No native code will be modified.

Independent review identified four important defects: SQLite WAL sidecar creation in read-only mode, hidden entries escaping the scan budget, dropped child-scan truncation, and BLOB queue fields breaking JSON. Each was reproduced with a failing test and corrected. Additional active-WAL and external-journal tests pass. Ruling: WAL/pending-journal queues return unavailable rather than using immutable mode and risking stale statuses. The default rollback-journal queue remains supported.

Final checks: 66 server tests and 46 script tests pass; the standalone installer bridge smoke check, shared-platform identity contract, compileall and diff whitespace check pass. CLI executed successfully on Linux and on GamingLaptop using existing JDK 17/Gradle 8.9/Android SDK 35. The laptop's existing AndroidHostSmoke `assembleDebug` also passed offline (31 tasks up to date, not a fresh compilation), producing the existing debug APK with SHA-256 `87eb94d31099e93c2f19ce7c263abf47be87526de0d935b9aa70f3218db745fc`.

Delivery: source changes stay in this isolated branch; only the standalone read-only report is staged in a separate laptop preview directory. No host/worker service restarted or replaced. Native Android lint/unit/app build and iOS compile for this revision remain unrun, so this is not a verified mobile release. No remote Mac dispatcher, repository checkout execution or mobile UI is implemented yet.
