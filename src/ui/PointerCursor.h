// Copyright (C) 2026 DarkMatter Productions. GPL-3.0-or-later.
#pragma once

// The pointer the retained menus and the console draw: the stock
// guicursor_arrow's silver-blue bevelled arrowhead redrawn as vector art (a
// dark slate rim and a soft shadow added), and an I-beam in the same finish
// over text a click would edit. Each shape and size is rasterized once and
// drawn as one textured quad.
enum pointerCursor_t {
	POINTER_ARROW,
	POINTER_TEXT
};

// Draws the pointer's hotspot (the arrow's tip, the I-beam's centre) at
// (x, y) pixels of the frame the 2D pass's 640x480 screen spans, frameWidth by
// frameHeight pixels. `unit` is the pixels in a texel of the stock 32-texel
// cursor box (retail draws the box at 16 units of the 480-unit menu, half a
// unit a texel). The caller owns the 2D viewport mode and flushes the GUI model.
void UI_DrawPointerCursor( pointerCursor_t shape, float x, float y, float frameWidth, float frameHeight, float unit );
