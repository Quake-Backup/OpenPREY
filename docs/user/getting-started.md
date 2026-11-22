# Getting Started with openPR06

This guide gets openPR06 running against your copy of PREY (2006).

> [!IMPORTANT]
> openPR06's first release is [0.15.0](https://github.com/themuffinator/openPR06/releases/tag/v0.15.0): Windows installers and zips (x64 and ARM64), Linux `.tar.xz` archives and AppImages (x64, and an ARM64 preview), and a macOS preview for Apple silicon. You can also build it yourself from this repository. The nightly builds from April 2026 further down the Releases page predate openPR06's move onto the openQ4 engine and don't match these guides. [Release status](release-status.md) lists what works today on each platform.

## What You Need

- **PREY (2006)**, installed from the original discs or another legitimate source. openPR06 reads the retail `base/` files from your install and ships none of them.
- A **Windows**, **Linux** or **macOS** computer that meets the [system requirements](#system-requirements).
- To build it yourself instead of using a release: the compiler and tools listed in [BUILDING.md](../../BUILDING.md).

## System Requirements

| Component | Requirement |
|---|---|
| Operating system | Windows 10 or 11, a 64-bit Linux desktop comparable to Ubuntu 24.04 or newer running Wayland or X11, or macOS 11 or newer on Apple silicon |
| CPU | 64-bit x86 (x64) or 64-bit Arm (ARM64). Download the package that matches your CPU |
| Graphics | An OpenGL driver with the ARB2-era vertex and fragment program support PREY's renderer path relies on. The optional Vulkan renderer needs a working Vulkan driver |
| Game files | The official retail PREY (2006) `base/` packs, left unmodified so startup validation can recognise them |
| Input and audio | Keyboard and mouse and a working audio device. Controllers are optional |

Windows x64 gets most of the runtime testing. Linux x64 is built in CI on every push.

Windows on Arm, Linux ARM64 and macOS packages are built, staged and checked by the release workflow, but nobody has played PREY on them yet. Linux ARM64 and macOS are previews; please report how they run.

If the game runs slowly, the console command `autoDetectPerformancePreset` picks one of the inherited performance presets for your hardware. The presets come from openQ4 and haven't been checked against PREY yet.

## Install and Launch

1. Install PREY (2006). Leave it where it is; openPR06 keeps to its own folder.
2. Download the [latest release](https://github.com/themuffinator/openPR06/releases/latest) for your platform and CPU:
   - **Windows:** `openpr06-<version>-windows-x64-setup.exe` (or `-arm64-setup.exe`), or the matching `.zip` extracted into a folder of its own.
   - **Linux:** the `.AppImage` (`x86_64`, or the `-preview-aarch64` one on ARM64), or the matching `.tar.xz` extracted into a folder of its own. Mark an AppImage executable with `chmod +x openpr06-*.AppImage` first. It bundles openPR06's runtime libraries but still reads your separately installed Prey (2006) assets; it never contains them.
   - **macOS:** `openpr06-<version>-macos-arm64-opengl-unsigned.tar.gz` (or the `-metal-` variant). Extract it and move `openPR06.app` wherever you like. See [macOS](#macos) before the first launch.
3. Launch `openPR06-client_x64` (`.exe` on Windows, `_arm64` on ARM64), the AppImage, or `openPR06.app`.
4. openPR06 looks for your PREY install by itself. If it can't find it, see [If Auto-Detection Fails](#if-auto-detection-fails).

To build it yourself instead, follow [BUILDING.md](../../BUILDING.md). The staged package lands in `.install/`: the client, the dedicated server, the renderer modules, and `basepr/` with the game module and openPR06's own packs.

On a Steam Deck or another SteamOS device, a Linux build also stages an `openPR06-steamdeck` launcher. See the [Steam Deck guide](steam-deck.md).

## How openPR06 Finds PREY

openPR06 uses the first of these locations that contains PREY's `base/` folder:

1. An `fs_basepath` you set on the command line.
2. The folder openPR06 was started from.
3. On Windows, the registry: the Human Head Studios, 2K Games and 3D Realms install keys, the `prey.exe` App Paths entry, and uninstall entries.
4. The usual install folders. On Windows that means `Human Head Studios\Prey`, `2K Games\Prey`, `3D Realms\Prey` and `Prey` under Program Files, and `Games\Prey` on the system drive. On Linux it means `~/Games/Prey`.
5. Steam and GOG library folders, if you have them. openPR06 doesn't need either one.

## Folder Layout

### Recommended

- Leave PREY in its original install folder.
- Keep openPR06 in its own folder, such as the staged `.install/`.
- Let openPR06 find the retail `base/` folder by itself.

### Portable

If you'd rather keep everything in one place, put these side by side in the same folder and start openPR06 from there:

- `base/`, copied from your PREY install
- `basepr/` and the executables from openPR06's `.install/`

> [!IMPORTANT]
> Don't copy retail `.pk4` files into `basepr/`. That folder is for openPR06's own files.

## Where Your Files Go

Configs, saves and logs go to a per-user folder, not to the PREY install:

| Platform | Default folder |
|---|---|
| Windows | `%LOCALAPPDATA%\openPR06` |
| Linux | `$XDG_DATA_HOME/openpr06`, or `~/.local/share/openpr06` when `XDG_DATA_HOME` isn't set |
| macOS | `~/Library/Application Support/openPR06` |

openPR06's files sit in the `basepr/` folder inside it. To keep a separate set, for example while testing, launch with `+set fs_savepath "<folder>"`.

## Platform Notes

### Windows

- The staged package carries everything it needs: the static runtime, so no Visual C++ redistributable, and the `OpenAL32.dll` that [BUILDING.md](../../BUILDING.md#windows-openal-runtime) has you prepare before staging.
- If openPR06 crashes, look in the `crashes/` folder beside the executable for the crash log and minidump.

### Linux

- SDL3 picks native Wayland or X11 automatically. Set `OPENPR06_FORCE_X11=1` to force the XWayland fallback.
- If a Wayland compositor has trouble with window decorations at startup, set `OPENPR06_WAYLAND_DISABLE_LIBDECOR=1` for that launch.
- Install the system development packages listed in [BUILDING.md](../../BUILDING.md) before you build.
- The AppImage and the `.tar.xz` hold the same files. Use the `.tar.xz` if your system can't run AppImages (they need FUSE, or `--appimage-extract-and-run`).

### macOS

- The macOS packages are previews for Apple silicon on macOS 11 or newer. The OpenGL variant uses Apple's OpenGL; the Metal variant draws the same OpenGL renderer through a Metal bridge. It is not a native Metal renderer. Vulkan runs through the bundled MoltenVK.
- They are not signed or notarized, so Gatekeeper blocks the first launch. Right-click `openPR06.app`, choose **Open**, then confirm; or run `xattr -dr com.apple.quarantine openPR06.app`.
- If openPR06 doesn't find your PREY folder, pass it at launch: `open openPR06.app --args +set fs_basepath "/path/to/Prey"`, pointing at the folder that contains `base`. [macOS Support Data](macos-support-data.md) explains how to send a report.

## If Auto-Detection Fails

Point openPR06 at the **PREY root folder**, the one that contains `base/`:

```text
openPR06-client_x64 +set fs_basepath "C:\path\to\Prey"
```

Don't point it at `base/` or `basepr/` themselves.

For more on paths and file layout, see the [Technical Reference](../../TECHNICAL.md#file-system-and-validation).

## Reporting a Problem

Open an [issue](https://github.com/themuffinator/openPR06/issues) with your setup and a log. Launch with `+set logFile 2`, reproduce the problem, and attach the `qconsole.log` it writes to `basepr/` in your save folder. On Windows, attach anything new in `crashes/` too.

## Next Steps

- [Client Settings](client-settings.md): where the most useful options live
- [Display Settings](display-settings.md): window modes, resolution, monitors and anti-aliasing
- [Input Settings](input-settings.md): bindings, mouse and controllers
- [Server Setup](server-setup.md): hosting a multiplayer game
- [Release Status](release-status.md): platform and feature support today
