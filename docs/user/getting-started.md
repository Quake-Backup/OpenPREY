# Getting Started with openPR06

This guide gets openPR06 running against your copy of PREY (2006).

> [!IMPORTANT]
> openPR06's first release is [0.15.0](https://github.com/themuffinator/openPR06/releases/tag/v0.15.0): a Windows x64 installer and zip, and a Linux x64 `.tar.xz`. You can also build it yourself from this repository. The nightly builds from April 2026 further down the Releases page predate openPR06's move onto the openQ4 engine and don't match these guides. [Release status](release-status.md) lists what works today on each platform.

## What You Need

- **PREY (2006)**, installed from the original discs or another legitimate source. openPR06 reads the retail `base/` files from your install and ships none of them.
- A **Windows x64** or **Linux x64** PC that meets the [system requirements](#system-requirements).
- To build it yourself instead of using a release: the compiler and tools listed in [BUILDING.md](../../BUILDING.md).

## System Requirements

| Component | Requirement |
|---|---|
| Operating system | Windows 10 or 11 (x64), or a 64-bit Linux desktop comparable to Ubuntu 24.04 or newer, running Wayland or X11 |
| CPU | 64-bit x86 (x64) |
| Graphics | An OpenGL driver with the ARB2-era vertex and fragment program support PREY's renderer path relies on. The optional Vulkan renderer needs a working Vulkan driver |
| Game files | The official retail PREY (2006) `base/` packs, left unmodified so startup validation can recognise them |
| Input and audio | Keyboard and mouse and a working audio device. Controllers are optional |

Windows x64 gets most of the runtime testing. Linux x64 is built in CI on every push.

macOS, Windows on Arm and Linux ARM64 aren't supported yet. Parts of the build files still cover them, but nothing builds or tests them for openPR06.

If the game runs slowly, the console command `autoDetectPerformancePreset` picks one of the inherited performance presets for your hardware. The presets come from openQ4 and haven't been checked against PREY yet.

## Build and Launch

1. Install PREY (2006). Leave it where it is; openPR06 keeps to its own folder.
2. Build and stage openPR06 by following [BUILDING.md](../../BUILDING.md). The staged package lands in `.install/`: the client, the dedicated server, the renderer modules, and `basepr/` with the game module and openPR06's own packs.
3. Launch `openPR06-client_x64` from `.install/` (`openPR06-client_x64.exe` on Windows).
4. openPR06 looks for your PREY install by itself. If it can't find it, see [If Auto-Detection Fails](#if-auto-detection-fails).

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

openPR06's files sit in the `basepr/` folder inside it. To keep a separate set, for example while testing, launch with `+set fs_savepath "<folder>"`.

## Platform Notes

### Windows

- The staged package carries everything it needs: the static runtime, so no Visual C++ redistributable, and the `OpenAL32.dll` that [BUILDING.md](../../BUILDING.md#windows-openal-runtime) has you prepare before staging.
- If openPR06 crashes, look in the `crashes/` folder beside the executable for the crash log and minidump.

### Linux

- SDL3 picks native Wayland or X11 automatically. Set `OPENPR06_FORCE_X11=1` to force the XWayland fallback.
- If a Wayland compositor has trouble with window decorations at startup, set `OPENPR06_WAYLAND_DISABLE_LIBDECOR=1` for that launch.
- Install the system development packages listed in [BUILDING.md](../../BUILDING.md) before you build.
- There's no openPR06 `.AppImage` yet. Run the client staged in `.install/`.

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
