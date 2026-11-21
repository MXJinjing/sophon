# Sophon

Swift library and `SophonCLI` for installation, incremental updates, repair, and the launcher JSON-RPC sidecar. The old Python server and client have been removed.

Source, tests, and the CLI live in [`sophon-swift/`](sophon-swift/README.md). The launcher RPC methods are documented in [`sophon-swift/YAAGLM_RPC.md`](sophon-swift/YAAGLM_RPC.md).

## Build

Swift 6.3 or newer is required. The package supports macOS 13 or newer.

```sh
swift build --package-path sophon-swift --product SophonCLI
swift test --package-path sophon-swift --force-resolved-versions
```

## Release

Push a `vX.Y.Z` tag, or `vX.Y.Z-alpha`, `vX.Y.Z-beta`, or `vX.Y.Z-rc` with an optional number. The release workflow tests the package, then publishes:

- `SophonCLI-darwin-arm64.tar.gz`
- `SophonCLI-darwin-x64.tar.gz`
- `SHA256SUMS`

Each archive contains `SophonCLI`, its license, and the Swift compatibility libraries needed on macOS.
