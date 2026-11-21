# Repository guidelines

- `sophon-swift/` is the only implementation. It contains the Swift library, `SophonCLI`, protobuf schemas, tests, and the launcher RPC reference.
- Tests live in `sophon-swift/Tests/`. Do not put test modules in `Sources/`.
- Generated environments, caches, build output, and downloaded game files are ignored.
- Do not run full test suites automatically. Run focused checks when needed and full suites only when explicitly requested.
- Use Conventional Commits. Do not mention real game or game company names in commit messages.
- Do not restore the removed Python server, Python client, or their packaging. The launcher downloads the macOS `SophonCLI` archives published by this repository.
