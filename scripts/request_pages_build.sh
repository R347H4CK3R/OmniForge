#!/usr/bin/env bash
set -euo pipefail

# GITHUB_TOKEN commits do not automatically start branch-based Pages builds.
# Explicitly request a build after publishing the verified catalog.
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must identify the current repository}"
: "${GH_TOKEN:?GH_TOKEN is required to request the Pages build}"
target_commit=$(git rev-parse HEAD)
latest=$(gh api "repos/${GITHUB_REPOSITORY}/pages/builds/latest" --jq '[.commit, .status] | join(" ")' || true)
if [[ "${GITHUB_EVENT_NAME:-}" != workflow_dispatch ]]; then
  case "$latest" in
    "$target_commit built"|"$target_commit building"|"$target_commit queued")
      echo 'GitHub Pages already has this commit built or in progress.'
      exit 0
      ;;
  esac
fi
# Checking on every verified refresh recovers from a failed request or build,
# even if that refresh does not produce another catalog commit.
gh api --method POST "repos/${GITHUB_REPOSITORY}/pages/builds" --jq '.status'
