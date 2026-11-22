# openPR06 workflows

`openpr06-validation.yml` is the active build and validation workflow. Its Windows and
Linux jobs build the engine, dedicated server, GL and Vulkan renderer modules, and the
canonical unified `game_<arch>` module from the in-tree `src/game/`, `src/Prey/` and
`src/preyengine/` sources. It also checks the game source inventory and content pack
table, the `basepr/` runtime layout, the high-risk rebase source contracts, and
openPR06 desktop/icon payloads.

`manual-release.yml` publishes openPR06 releases. It is adapted from openQ4's and
builds openQ4's desktop release set: Windows x64 and ARM64 (zip, Inno Setup installer
and PDB symbols), Linux x64 and ARM64 (`.tar.xz`, AppImage with `.zsync`, and detached
debug symbols; ARM64 is a `-preview`), and macOS ARM64 in OpenGL and Metal-bridge
variants (unsigned `-unsigned.tar.gz` app bundles and dSYMs, or signed, notarized DMGs
once the `MACOS_DEVELOPER_ID_*` and `MACOS_NOTARY_*` secrets exist). Run it by hand
from `main` or a `release/*` branch with `version_override` (for example `0.15.0`).
The metadata job derives the lane matrix and the exact asset list together; the
release job checks that set and every runtime archive's contents, generates the
changelog from `docs/dev/releases/<tag>.md`, and creates the GitHub release as a
draft. Set `draft` to false to publish. openQ4's Android APK, Discord step,
standalone content packs, signed update manifest and assetless runtime smokes are left
out; the file's header says why.

The inherited OpenQ4 commit, push, ARM64, macOS and Universal2
workflows are retained only as static-test/reference fixtures. They are manual-only,
clearly named `DISABLED`, and every job has an unconditional false gate because they
still assume openQ4's split `game-sp`/`game-mp` modules and Quake 4 content. Remove those
gates only after rebuilding source pinning, package assertions, signing, and runtime
smoke tests around the in-tree game library, `game_<arch>`, and `basepr/`.
`android-build.yml` came with the upstream engine merge. openPR06 has no Android
release yet: the native build stops at the GLES renderer, which lacks PREY's
ARB-program hooks, and the host app is still openQ4's, so it is not part of active
validation.

`discord-release.yml` only reacts to an already-published release. It does not build or
publish artifacts. It is off unless the repository variable `DISCORD_RELEASE_ENABLED` is
`true` (with the `DISCORD_RELEASE_WEBHOOK` secret set); 0.15.0 was published without it.
