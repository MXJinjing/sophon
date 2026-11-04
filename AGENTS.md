# Repository guidelines

- `sophon-client/src/sophon_client/`: Python CLI with Rich terminal progress, hk4e only.
- `sophon-server/src/`: FastAPI server and downloader modules; preserve legacy interfaces.
- Each component's `tests/` contains tests; no test modules in `src/`.
- `sophon-server/proto/`: protobuf schemas; generated Python modules stay in server `src/`.
- Build scripts and source launchers live at repository root.
- `third_party/hpatchz/`: intentionally vendored native tools and their license.
- Generated environments, caches, build output, distributions and downloaded game files are ignored.
- All current APIs are documented in the API reference in sophon-server/README.md. Update it when changing APIs; do not split extensions into another document.
- Do not run full test suites automatically. Run focused checks when needed and full suites only when explicitly requested.
- Use Conventional Commits. Do not mention real game or game company names in commit messages.

## Launcher source copy

- This repository is the canonical home for shared server code. The sibling launcher keeps a source copy, not a Git submodule.
- When changing shared server behavior, implement and test it here first, then use the launcher's `scripts/sync-sophon.py --source ../sophon --apply` to update its copy and revision lock.
- Shared source, protobuf schemas, license and server tests are synchronized. Generated protobuf, environments and build output are excluded. The standalone release packaging test is excluded from the launcher.
- Launcher UI, build adapters, dependency/test configuration, API integration README and `test_launcher_*.py` remain launcher-owned. Update both API references when changing shared events.
