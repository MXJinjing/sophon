#!/bin/bash
# Package the macOS SophonCLI sidecar the launcher downloads from a release.
set -euo pipefail

arch="${1:?architecture arm64 or x64}"
case "$arch" in
  arm64)
    triple=arm64-apple-macosx13.0
    lipo_arch=arm64
    ;;
  x64)
    triple=x86_64-apple-macosx13.0
    lipo_arch=x86_64
    ;;
  *)
    echo "Unsupported architecture: $arch" >&2
    exit 1
    ;;
esac

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
source="$root/sophon-swift"
stage="${RUNNER_TEMP:-/tmp}/SophonCLI-$arch"
archive="${2:-$root/dist/SophonCLI-darwin-$arch.tar.gz}"

swift build --package-path "$source" --force-resolved-versions \
  --configuration release --triple "$triple" --product SophonCLI -j "${SOPHON_BUILD_JOBS:-6}"
bin="$(swift build --package-path "$source" --force-resolved-versions \
  --configuration release --triple "$triple" --show-bin-path)"

rm -rf "$stage"
mkdir -p "$stage" "$(dirname "$archive")"
install -m 755 "$bin/SophonCLI" "$stage/SophonCLI"
install -m 644 "$source/LICENSE" "$stage/LICENSE"
xcrun swift-stdlib-tool --copy --platform macosx \
  --scan-executable "$stage/SophonCLI" --destination "$stage"
xcrun lipo "$stage/SophonCLI" -verify_arch "$lipo_arch"
tar -C "$stage" -czf "$archive" .
echo "$archive"
