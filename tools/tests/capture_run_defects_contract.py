#!/usr/bin/env python3
"""Static regression contract for four defects found by a scripted capture run.

1. Tiled captures: the glow overlay's helpers must take the tile offset through
   RB_TileOffsetX/Y, which is zero while a capture-sized render target is
   bound. With tr.viewportOffset they copied and composited a rect off the
   target and every tile of `screenshot 2560 1440` but the first came out black.
2. Bots: the scoreboard ping of an hhArtificialPlayer slot is 0, not the 99999
   the async server reports for a slot it never connected.
3. Message events: parameters travel as bytes with -1 mapped to 0xFF, so a
   frag-limit win no longer trips idBitMsg's "value overflow -1 8" warning.
4. Retained Options: the Quality Preset row follows com_performancePreset each
   frame the page is up, so `applyPerformancePreset` from the console moves it.

Verified in windowed runs on 2026-11-21; this pins the source shape.
"""
from __future__ import annotations

import re

from async_drop_client_contract import function_body, read, require


def check_glow_tile_offset() -> None:
    draw = read("src/renderer/draw_common.cpp")
    for signature in (
        "static void RB_GlowSetScreenRect",
        "static void RB_GlowCornerOrigin",
        "static void RB_GlowSetCornerRect",
        "static void RB_GlowCopyViewToImage",
    ):
        body = function_body(draw, signature)
        if "tr.viewportOffset" in body:
            raise AssertionError(f"{signature} must take the tile offset through RB_TileOffsetX/Y")
    for signature in ("static void RB_GlowSetScreenRect", "static void RB_GlowCornerOrigin"):
        body = function_body(draw, signature)
        require(body, "RB_TileOffsetX()", signature)
        require(body, "RB_TileOffsetY()", signature)
    corner = function_body(draw, "static void RB_GlowCornerOrigin")
    require(corner, "Max( 0,", "RB_GlowCornerOrigin keeps the corner on the window")


def check_bot_ping() -> None:
    mp = read("src/game/MultiplayerGame.cpp")
    run = function_body(mp, "void idMultiplayerGame::Run")
    ping = run.index("ServerGetClientPing( i )")
    bot = run.rfind("hhArtificialPlayer::Type", 0, ping)
    if bot < 0 or ping - bot > 400:
        raise AssertionError("the ping update must give bots (hhArtificialPlayer) a ping before ServerGetClientPing")
    require(run[bot:ping], "playerState[i].ping = 0;", "bot ping")


def check_event_parm_bytes() -> None:
    header = read("src/game/MultiplayerGame.h")
    require(header, "ID_INLINE int MP_EventParmToByte( int parm ) { return parm < 0 ? 0xFF : parm; }", "MultiplayerGame.h")
    require(header, "ID_INLINE int MP_EventParmFromByte( int value ) { return value == 0xFF ? -1 : value; }", "MultiplayerGame.h")
    mp = read("src/game/MultiplayerGame.cpp")
    for signature in ("void idMultiplayerGame::PrintMessageEvent", "void idMultiplayerGame::PrintDeathMessageEvent"):
        body = function_body(mp, signature)
        if re.search(r"WriteByte\( parm[12] \)", body):
            raise AssertionError(f"{signature} writes a raw parameter byte")
        require(body, "WriteByte( MP_EventParmToByte( parm1 ) )", signature)
        require(body, "WriteByte( MP_EventParmToByte( parm2 ) )", signature)
    network = read("src/game/Game_network.cpp")
    if network.count("MP_EventParmFromByte( msg.ReadByte( ) )") != 4:
        raise AssertionError("both message event readers must map 0xFF back to -1")


def check_preset_row_sync() -> None:
    menu = read("src/framework/Session_menu.cpp")
    # A forward declaration precedes GuiFrameEvents; take the definition.
    definition = menu.find("static void Session_SyncPreyOptionsVideoPreset( idUserInterface *page ) {")
    if definition < 0:
        raise AssertionError("Missing Session_SyncPreyOptionsVideoPreset's definition")
    sync = function_body(menu[definition:], "static void Session_SyncPreyOptionsVideoPreset")
    require(sync, "Session_PreyVideoPresetIndex()", "Session_SyncPreyOptionsVideoPreset")
    require(sync, "StateChanged", "Session_SyncPreyOptionsVideoPreset")
    frame = function_body(menu, "void idSessionLocal::GuiFrameEvents")
    require(frame, "Session_SyncPreyOptionsVideoPreset( guiActive );", "GuiFrameEvents")


def main() -> None:
    check_glow_tile_offset()
    check_bot_ping()
    check_event_parm_bytes()
    check_preset_row_sync()
    print("capture run defects contract: OK")


if __name__ == "__main__":
    main()
