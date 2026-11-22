// Copyright (C) 2026 DarkMatter Productions. GPL-3.0-or-later.
// The retained menus' pointer picture (src/ui/retained/PointerArt.cpp).
#include "src/ui/retained/PointerArt.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <limits>
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"line %d: %s\n",__LINE__,#x); std::exit(1); } } while (0)
using namespace openq4::ui;

static const unsigned char* Pixel(const PointerImage& image, int x, int y) {
	CHECK(x >= 0 && y >= 0 && x < image.width && y < image.height);
	return image.pixels.data()+(static_cast<size_t>(y)*image.width+x)*4;
}
// The pixel whose square holds the point `texels` from the hotspot.
static const unsigned char* At(const PointerImage& image, float unit, double tx, double ty) {
	return Pixel(image,image.hotspotX+static_cast<int>(std::floor(tx*unit)),image.hotspotY+static_cast<int>(std::floor(ty*unit)));
}

int main() {
	PointerImage untouched; untouched.width = 7;
	for (float bad : {0.f,.2f,16.5f,-1.f,std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity()}) {
		CHECK(!RasterizePointer(PointerShape::Arrow,bad,untouched) && untouched.width == 7 && untouched.pixels.empty());
	}
	int lastWidth = 0;
	for (float unit : {.25f,.5f,1.125f,2.25f,16.f}) {
		for (PointerShape shape : {PointerShape::Arrow,PointerShape::Text}) {
			PointerImage image, again;
			CHECK(RasterizePointer(shape,unit,image) && RasterizePointer(shape,unit,again));
			CHECK(image.pixels == again.pixels && image.width == again.width && image.hotspotY == again.hotspotY);
			CHECK(image.width > 0 && image.height > 0 && image.pixels.size() == static_cast<size_t>(image.width)*image.height*4);
			CHECK(image.hotspotX > 0 && image.hotspotY > 0 && image.hotspotX < image.width && image.hotspotY < image.height);
			// Premultiplied: no channel exceeds coverage.
			for (size_t i = 0; i < image.pixels.size(); i += 4) {
				const unsigned char* p = image.pixels.data()+i;
				CHECK(p[0] <= p[3] && p[1] <= p[3] && p[2] <= p[3]);
			}
			// The picture holds the whole shadow: its border is all but empty.
			for (int x = 0; x < image.width; ++x) CHECK(Pixel(image,x,0)[3] <= 2 && Pixel(image,x,image.height-1)[3] <= 2);
			for (int y = 0; y < image.height; ++y) CHECK(Pixel(image,0,y)[3] <= 2 && Pixel(image,image.width-1,y)[3] <= 2);
			if (shape == PointerShape::Arrow) {
				CHECK(image.width > lastWidth); lastWidth = image.width;
				if (unit < 1) continue;
				// The tip is on the hotspot: its pixel is drawn, the ones above
				// and to the left of it hold at most a trace of the shadow.
				CHECK(Pixel(image,image.hotspotX,image.hotspotY)[3] > 64);
				CHECK(Pixel(image,image.hotspotX-1,image.hotspotY)[3] < 16 && Pixel(image,image.hotspotX,image.hotspotY-1)[3] < 16);
				// The upper right face is bright and opaque, the face over the
				// notch darker, and the rim along the left edge dark.
				const unsigned char* bright = At(image,unit,9,11);
				const unsigned char* notch = At(image,unit,4.5,22.5);
				CHECK(bright[3] == 255 && bright[0] > 180 && bright[2] >= bright[0]);
				CHECK(notch[3] == 255 && notch[0] < bright[0]-40);
				if (unit >= 2) { const unsigned char* rim = At(image,unit,.3,13); CHECK(rim[3] == 255 && rim[0] < 80); }
				// Past the right edge only the faint shadow remains.
				CHECK(At(image,unit,16,8)[3] < 128);
			} else if (unit >= 1) {
				// The I-beam's stem is lit on its right half, shaded on its left.
				const unsigned char* lit = At(image,unit,.6,0), * shade = At(image,unit,-.6,0);
				CHECK(lit[3] == 255 && shade[3] == 255 && lit[0] > shade[0]+30);
				CHECK(At(image,unit,4,0)[3] < 128); // beside the stem
				CHECK(At(image,unit,3.5,-11)[3] == 255); // the top serif
			}
		}
	}
	std::puts("pointer art: ok");
	return 0;
}
