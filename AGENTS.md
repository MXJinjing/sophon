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
