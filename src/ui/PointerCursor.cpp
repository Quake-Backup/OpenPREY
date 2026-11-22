// Copyright (C) 2026 DarkMatter Productions. GPL-3.0-or-later.
#include "../idlib/precompiled.h"
#include "PointerCursor.h"

#ifndef ID_DEDICATED
#include "retained/PointerArt.h"
#include <cmath>

namespace {

// The pointer is a picture rasterized once per shape and size
// (retained/PointerArt.cpp), uploaded to a small image and drawn as one quad
// at whole pixels, its texels on the frame's pixels. Four pictures stay
// resident, so the menus, the console and a resized window never trade one
// image back and forth; a video restart rebuilds them.
struct PointerPicture {
	pointerCursor_t shape = POINTER_ARROW;
	float unit = 0;
	int restart = -1;
	unsigned lastUse = 0;
	int width = 0, height = 0, hotspotX = 0, hotspotY = 0;
	// Null with `used` set: this shape and size could not be built here.
	const idMaterial* material = nullptr;
	bool used = false;
};
constexpr int PointerPictures = 4;
PointerPicture pictures[PointerPictures];
unsigned pictureClock = 0;

bool Build( PointerPicture& picture, int slot ) {
	openq4::ui::PointerImage image;
	if ( !openq4::ui::RasterizePointer( picture.shape == POINTER_TEXT ? openq4::ui::PointerShape::Text : openq4::ui::PointerShape::Arrow,
			picture.unit, image ) ) {
		return false;
	}
	const int maximum = renderSystem->GetGLConfig().maxTextureSize;
	if ( maximum > 0 && ( image.width > maximum || image.height > maximum ) ) {
		return false;
	}
	idImageOpts options;
	options.width = image.width; options.height = image.height;
	options.format = FMT_RGBA8; options.numLevels = 1; options.isPersistant = true;
	const idStr name = va( "_retainedPointerImage%d", slot );
	if ( !renderSystem->CreateImage( name.c_str(), &options, TF_LINEAR ) ||
			!renderSystem->UploadImage( name.c_str(), image.pixels.data(), image.width, image.height ) ) {
		return false;
	}
	const idMaterial* material = declManager->FindMaterial( va( "_retainedPointer/%d", slot ) );
	if ( material == NULL || material->GetState() == DS_DEFAULTED ) {
		return false;
	}
	picture.width = image.width; picture.height = image.height;
	picture.hotspotX = image.hotspotX; picture.hotspotY = image.hotspotY;
	picture.material = material;
	return true;
}

const PointerPicture* Picture( pointerCursor_t shape, float unit ) {
	const int restart = renderSystem->GetVideoRestartCount();
	PointerPicture* replace = &pictures[0];
	for ( PointerPicture& picture : pictures ) {
		if ( picture.used && picture.restart == restart && picture.shape == shape && picture.unit == unit ) {
			picture.lastUse = ++pictureClock;
			return picture.material ? &picture : nullptr;
		}
		// An empty slot first, then one left from before a restart, then the
		// least recently drawn.
		const auto rank = []( const PointerPicture& p, int now ) { return !p.used ? 0 : p.restart != now ? 1 : 2; };
		if ( rank( picture, restart ) < rank( *replace, restart ) ||
				( rank( picture, restart ) == rank( *replace, restart ) && picture.lastUse < replace->lastUse ) ) {
			replace = &picture;
		}
	}
	*replace = {};
	replace->shape = shape; replace->unit = unit; replace->restart = restart;
	replace->used = true; replace->lastUse = ++pictureClock;
	if ( !Build( *replace, static_cast<int>( replace-pictures ) ) ) {
		common->DPrintf( "pointer cursor: no %s picture at %g pixels a texel; drawing the stock arrow\n",
			shape == POINTER_TEXT ? "text" : "arrow", unit );
		replace->material = nullptr;
		return nullptr;
	}
	return replace;
}

} // namespace

void UI_DrawPointerCursor( pointerCursor_t shape, float x, float y, float frameWidth, float frameHeight, float unit ) {
	if ( !( frameWidth > 0 ) || !( frameHeight > 0 ) || !( unit > 0 ) || !std::isfinite( x ) || !std::isfinite( y ) ||
			!std::isfinite( unit ) ) {
		return;
	}
	// Sizes a sixty-fourth of a pixel apart share a picture.
	unit = idMath::ClampFloat( .25f, 16.f, idMath::Floor( unit*64.f+.5f )/64.f );
	const float px = idMath::Floor( x+.5f ), py = idMath::Floor( y+.5f );
	const float sx = SCREEN_WIDTH / frameWidth, sy = SCREEN_HEIGHT / frameHeight;
	renderSystem->SetColor4( 1, 1, 1, 1 );
	const PointerPicture* picture = Picture( shape, unit );
	if ( picture == nullptr ) {
		// The stock arrow, its tip (a texel right and two down of its box's
		// corner) on the hotspot.
		const idMaterial* stock = declManager->FindMaterial( "guis/assets/guicursor_arrow.tga" );
		if ( stock != NULL ) {
			renderSystem->DrawStretchPic( ( px-unit )*sx, ( py-2*unit )*sy, 32*unit*sx, 32*unit*sy, 0, 0, 1, 1, stock );
		}
		return;
	}
	const float left = px-picture->hotspotX, top = py-picture->hotspotY;
	const float corners[4][4] = {
		{ left, top, 0, 0 }, { left+picture->width, top, 1, 0 },
		{ left+picture->width, top+picture->height, 1, 1 }, { left, top+picture->height, 0, 1 }
	};
	idDrawVert vertices[4];
	for ( int i = 0; i < 4; ++i ) {
		idDrawVert& v = vertices[i];
		v.Clear();
		v.xyz.Set( corners[i][0]*sx, corners[i][1]*sy, 0 );
		v.st.Set( corners[i][2], corners[i][3] );
		v.normal.Set( 0, 0, 1 ); v.tangents[0].Set( 1, 0, 0 ); v.tangents[1].Set( 0, 1, 0 );
		for ( int channel = 0; channel < 4; ++channel ) {
			v.color[channel] = v.color2[channel] = 255;
		}
	}
	static const glIndex_t indices[6] = { 0, 1, 2, 0, 2, 3 };
	renderSystem->DrawStretchPic( vertices, indices, 4, 6, picture->material, false );
}

#else

void UI_DrawPointerCursor( pointerCursor_t, float, float, float, float, float ) {}

#endif
