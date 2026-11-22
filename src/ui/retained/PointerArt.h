// Copyright (C) 2026 DarkMatter Productions. GPL-3.0-or-later.
#pragma once

#include <vector>

namespace openq4::ui {

// The retained menus' pointer as a finished picture: the stock Prey arrow (a
// silver-blue bevelled arrowhead, guicursor_arrow) and an I-beam in the same
// finish, redrawn as vector art and rasterized once for one size. The host
// uploads the picture and draws it as a single quad at whole pixels.
enum class PointerShape { Arrow, Text };

struct PointerImage {
	int width = 0, height = 0;
	// The pixel corner the hotspot sits on (the arrow's tip, the I-beam's
	// centre), from the picture's top-left.
	int hotspotX = 0, hotspotY = 0;
	// Premultiplied RGBA8, rows top-down.
	std::vector<unsigned char> pixels;
};

// `pixelsPerTexel` is the size: output pixels per texel of the stock 32-texel
// cursor box. Pure and deterministic: no engine, renderer or allocation state.
// False, with the result untouched, for a size that is not finite or outside
// 0.25 to 16.
bool RasterizePointer(PointerShape shape, float pixelsPerTexel, PointerImage& result);

} // namespace openq4::ui
