#!/usr/bin/env python3
"""Pin openPR06 identity in active release and developer-facing helpers."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(text: str, token: str, label: str) -> None:
    if token not in text:
        raise AssertionError(f"{label} is missing {token!r}")


def reject(text: str, token: str, label: str) -> None:
    if token in text:
        raise AssertionError(f"{label} still contains {token!r}")


def validate_common_runtime_copy() -> None:
    common = read("src/framework/Common.cpp")
    require(common, 'fileName = "logs/openpr06_%Y%m%d_%H%M%S.log";', "automatic log naming")
    require(common, '"openPR06 Warning"', "runtime warning title")
    require(common, '"applies the selected openPR06 performance preset"', "console help")
    reject(common, '"logs/openq4_%Y%m%d_%H%M%S.log"', "automatic log naming")
    reject(common, '"openQ4 Warning"', "runtime warning title")
    reject(common, '"applies the selected openQ4 performance preset"', "console help")


def validate_discord_release_copy() -> None:
    announcer = read(".github/scripts/announce-release-discord.mjs")
    workflow = read(".github/workflows/discord-release.yml")

    for token in (
        'return unbrandedName ? `openPR06 ${unbrandedName}` : "openPR06";',
        "The new openPR06 ${mode} is ready",
        "original Prey (2006) assets",
        'username: "openPR06 Releases"',
        'footer: { text: "openPR06 - open-source engine and game code for Prey (2006)" }',
        "themuffinator/openPR06/main/assets/img/avatar.png",
    ):
        require(announcer, token, "Discord release announcer")

    for token in (
        "The new openQ4",
        "original Quake 4 assets",
        'username: "openQ4 Releases"',
        "open-source Quake 4 engine and game code",
        "themuffinator/OpenQ4/main/assets/img/avatar.png",
    ):
        reject(announcer, token, "Discord release announcer")

    require(workflow, "vars.DISCORD_RELEASE_MENTIONS || ''", "Discord release workflow")
    require(workflow, "the openPR06 community channels", "Discord release workflow")
    reject(workflow, "1425985498693898260", "Discord release workflow")
    reject(workflow, "1509926146018513077", "Discord release workflow")


def validate_listen_server_helper() -> None:
    helper = read("tools/debug/start_listen_server_client.ps1")
    for token in (
        '[string]$Map = "game/dmroadhouse"',
        '[string]$BasePath = ""',
        "function New-openPR06CommonArgs",
        '"openPR06-client_x64.exe"',
        '"r_fullscreen", "0"',
        '"fs_game", "basepr"',
        '"si_gameType", "deathmatch"',
        '"basepr\\logs\\listen-server.log"',
    ):
        require(helper, token, "listen-server helper")

    for token in ("openQ4-client", "baseoq4", "q4base", "Steam\\steamapps", "[switch]$Fullscreen"):
        reject(helper, token, "listen-server helper")


def validate_renderdoc_helper() -> None:
    helper = read("tools/debug/renderdoc_capture.ps1")
    for token in (
        '[string]$BasePath = ""',
        '"openPR06-client_x64.exe"',
        '".home\\basepr\\renderdoc\\openpr06"',
        '"logs/openpr06.log"',
        '"fs_game", "basepr"',
        '"si_gameType", "deathmatch"',
        '-Filter "openpr06*.rdc"',
    ):
        require(helper, token, "RenderDoc helper")

    for token in ("openQ4-client", "baseoq4", "q4base", "logs/openq4.log", "Steam\\steamapps"):
        reject(helper, token, "RenderDoc helper")


def validate_linux_desktop_helper() -> None:
    helper = read("tools/linux/install_desktop_launcher.sh")
    for token in (
        'OPENPR06_INSTALL_ROOT:-${OPENQ4_INSTALL_ROOT:-',
        'OPENPR06_BASEPATH:-${OPENQ4_BASEPATH:-',
        "openPR06-client_${arch}",
        "openpr06.svg",
        "assets/icons/prey.svg",
        "Name=openPR06",
        "Prey (2006)",
        "Keywords=prey;idtech;fps;multiplayer;",
    ):
        require(helper, token, "Linux desktop helper")

    for token in (
        "openQ4-client_",
        "Name=openQ4",
        "replacement for Quake 4",
        "q4base/",
        "assets/icons/quake4",
    ):
        reject(helper, token, "Linux desktop helper")


def main() -> None:
    validate_common_runtime_copy()
    validate_discord_release_copy()
    validate_listen_server_helper()
    validate_renderdoc_helper()
    validate_linux_desktop_helper()
    print("openPR06 active-tool branding checks passed")


if __name__ == "__main__":
    main()
