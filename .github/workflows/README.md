# openPR06 workflows

`openpr06-validation.yml` is the active build and validation workflow. Its Windows and
Linux jobs build the engine, dedicated server, GL and Vulkan renderer modules, and the
canonical unified `game_<arch>` module from the in-tree `src/game/`, `src/Prey/` and
`src/preyengine/` sources. It also checks the game source inventory and content pack
table, the `basepr/` runtime layout, the high-risk rebase source contracts, and
openPR06 desktop/icon payloads.

`manual-release.yml` publishes openPR06 releases. It is adapted from openQ4's for
Windows x64 and Linux x64: run it by hand from `main` or a `release/*` branch with
`version_override` (for example `0.15.0`), and it builds, verifies and packages both
platforms (Windows zip, installer and PDB symbols; Linux `.tar.xz` and detached debug
symbols), generates the changelog from `docs/dev/releases/<tag>.md`, and creates the
GitHub release as a draft. Set `draft` to false to publish. openQ4's Discord, Android,
macOS, ARM64, AppImage, standalone content-pack and signed update-manifest steps are
left out; the file's header says why.

The inherited OpenQ4 commit, push, ARM64, macOS and Universal2
workflows are retained only as static-test/reference fixtures. They are manual-only,
clearly named `DISABLED`, and every job has an unconditional false gate because they
still assume openQ4's split `game-sp`/`game-mp` modules and Quake 4 content. Remove those
gates only after rebuilding source pinning, package assertions, signing, and runtime
smoke tests around the in-tree game library, `game_<arch>`, and `basepr/`.
`android-build.yml` came with the upstream engine merge; openPR06 does not target
Android, so it is likewise not part of active validation.

`discord-release.yml` only reacts to an already-published release. It does not build or
publish artifacts. It is off unless the repository variable `DISCORD_RELEASE_ENABLED` is
`true` (with the `DISCORD_RELEASE_WEBHOOK` secret set); 0.15.0 was published without it.
