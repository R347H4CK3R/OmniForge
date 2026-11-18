#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -n "${SWIFT_BIN:-}" ]]; then
 mkdir -p .build/cache .build/config .build/security .build/clang
 export HOME="$PWD/.build" CLANG_MODULE_CACHE_PATH="$PWD/.build/clang" SWIFTPM_MODULECACHE_OVERRIDE="$PWD/.build/clang"
 "$SWIFT_BIN" test --cache-path .build/cache --config-path .build/config --security-path .build/security
else
 swift test
fi
