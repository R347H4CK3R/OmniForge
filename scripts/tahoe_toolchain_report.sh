#!/usr/bin/env bash
set -euo pipefail
echo "=== OS ==="
sw_vers
uname -m
echo "=== Xcode ==="
xcode-select -p
xcodebuild -version
echo "=== SDKs ==="
xcodebuild -showsdks
echo "=== Available simulator devices ==="
xcrun simctl list devices available
echo "=== IPA, debugging and binary analysis tooling ==="
for program in xcrun swift clang git python3 ruby codesign otool lipo plutil xcodebuild; do
  if command -v "$program" >/dev/null 2>&1; then
    printf "%s: %s\n" "$program" "$(command -v "$program")"
  else
    printf "%s: not installed\n" "$program"
  fi
done
echo "=== Disassembly support ==="
xcrun --find llvm-objdump || true
echo "=== Xcode iOS SDK info ==="
xcrun --sdk iphoneos --show-sdk-path
echo "=== Setup complete (not a device installation test) ==="
