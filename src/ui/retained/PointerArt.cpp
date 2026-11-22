// Copyright (C) 2026 DarkMatter Productions. GPL-3.0-or-later.
#include "PointerArt.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <utility>

namespace openq4::ui {
namespace {

struct Point { double x, y; };
struct Colour { double r, g, b; };

constexpr Colour Hex(unsigned value) {
	return {((value>>16)&255)/255.0,((value>>8)&255)/255.0,(value&255)/255.0};
}
Colour Mix(Colour a, Colour b, double t) {
	t = std::clamp(t,0.0,1.0);
	return {a.r+(b.r-a.r)*t,a.g+(b.g-a.g)*t,a.b+(b.b-a.b)*t};
}
double Cross(Point o, Point a, Point b) { return (a.x-o.x)*(b.y-o.y)-(a.y-o.y)*(b.x-o.x); }
double SegmentDistance(Point p, Point a, Point b) {
	const double dx = b.x-a.x, dy = b.y-a.y, length = dx*dx+dy*dy;
	const double t = length > 0 ? std::clamp(((p.x-a.x)*dx+(p.y-a.y)*dy)/length,0.0,1.0) : 0.0;
	const double ex = a.x+dx*t-p.x, ey = a.y+dy*t-p.y;
	return std::sqrt(ex*ex+ey*ey);
}

// The art is in texels of the stock 32-texel cursor box with the hotspot at
// the origin. Each silhouette is a simple polygon.
//
// The arrow is guicursor_arrow's arrowhead, its tip on the hotspot (the stock
// bitmap's tip sat a texel right and two down of it): a vertical left edge, a
// 45-degree right edge to a blunt corner, a shallow return to the notch and a
// 45-degree edge down to a rounded foot. Its bevel rises to a peak low on the
// body; the faces round it are lit from above as the stock art is: the upper
// right face near white, the left face silver, the lower right face in half
// shade and the face over the notch dark.
constexpr Point ArrowSilhouette[] = {
	{0,0},{17.3,17.3},{17.65,17.75},{17.5,18.15},{8.8,20.3},{1.5,27.2},{.75,27.55},{.2,27.15},{0,26.4}
};
constexpr int ArrowPoints = sizeof(ArrowSilhouette)/sizeof(ArrowSilhouette[0]);
constexpr Point ArrowPeak = {5.4,16.4};
// The face each silhouette edge (point i to point i+1) bounds.
enum Face { UpperRight, LowerRight, Notch, Left };
constexpr Face ArrowFace[ArrowPoints] = {UpperRight,LowerRight,LowerRight,LowerRight,Notch,Notch,Notch,Left,Left};
struct FaceShade { Colour peak, edge; };
constexpr FaceShade ArrowShade[] = {
	{Hex(0xFFFFFF),Hex(0xD5DCE5)}, // UpperRight
	{Hex(0xDCE1E8),Hex(0xA4B0C0)}, // LowerRight
	{Hex(0xA3AEBE),Hex(0x6A7585)}, // Notch
	{Hex(0xE8EBF0),Hex(0xC0C8D3)}, // Left
};

// The I-beam: chamfered serifs stepping into the stem at 45 degrees, its lit
// right half bright and its left half in shade, about nine tenths of the
// arrow's height. Its stem and serifs keep a few pixels of light inside the
// rim at the smallest sizes.
std::vector<Point> TextSilhouette(double unit) {
	const double stem = std::max(1.6,1.75/unit), serif = std::max(2.4,2.6/unit), reach = stem+3, step = 1, chamfer = .8;
	const double inner = 12-serif;
	const Point quarter[] = {
		{reach-chamfer,-12},{reach,-12+chamfer},{reach,-inner},{stem+step,-inner},{stem,-inner+step}
	};
	std::vector<Point> points;
	// Clockwise from the top serif's left end, mirroring one quarter.
	for (const Point& p : quarter) points.push_back(p);
	for (int i = 4; i >= 0; --i) points.push_back({quarter[i].x,-quarter[i].y});
	for (const Point& p : quarter) points.push_back({-p.x,-p.y});
	for (int i = 4; i >= 0; --i) points.push_back({-quarter[i].x,quarter[i].y});
	return points;
}

// A dark slate outline round both, never black, as the stock arrow's rim.
constexpr Colour Rim = Hex(0x29303A);
// The soft shadow: cast down and to the right, blurred, at most this dark.
constexpr double ShadowX = .8, ShadowY = 1.2, ShadowSigma = .8, ShadowOpacity = .45;
// Pixels near an edge, the rim's inner edge or a face boundary take this many
// samples a side; elsewhere one sample at the centre is exact.
constexpr int Samples = 8;

struct Shape {
	std::vector<Point> points;
	int count;
	bool arrow;
	// Texels; the rim is at least a pixel wide at any size.
	double rim;

	bool Inside(Point p) const {
		bool inside = false;
		for (int i = 0, j = count-1; i < count; j = i++) {
			const Point a = points[i], b = points[j];
			if ((a.y > p.y) != (b.y > p.y) && p.x < (b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x) inside = !inside;
		}
		return inside;
	}
	double EdgeDistance(Point p) const {
		double best = 1e30;
		for (int i = 0; i < count; ++i) best = std::min(best,SegmentDistance(p,points[i],points[(i+1)%count]));
		return best;
	}
	// Distance to the boundaries between faces, where the shading steps.
	double FaceDistance(Point p) const {
		if (!arrow) return std::abs(p.x);
		double best = 1e30;
		for (int i = 0; i < count; ++i) {
			if (ArrowFace[i] != ArrowFace[(i+count-1)%count]) best = std::min(best,SegmentDistance(p,ArrowPeak,points[i]));
		}
		return best;
	}
	// The colour of a point inside the silhouette. `rimTest` is 1 where the
	// point is known to be on the rim, 0 where it is known to be inside it,
	// and -1 where the edge distance decides.
	Colour Shade(Point p, int rimTest = -1) const {
		if (rimTest > 0 || (rimTest < 0 && EdgeDistance(p) < rim)) return Rim;
		if (!arrow) {
			const double t = (p.y+12)/24;
			return p.x < 0 ? Mix(Hex(0xC7CED9),Hex(0x8390A3),t) : Mix(Hex(0xFFFFFF),Hex(0xBEC7D3),t);
		}
		// Each face is fanned from the peak; along the fan the shade runs
		// from the face's peak colour to its edge colour. The peak's
		// barycentric weight is continuous across one face's triangles.
		Face face = Left; double toEdge = 1;
		for (int i = 0; i < count; ++i) {
			const Point a = points[i], b = points[(i+1)%count];
			const double whole = Cross(ArrowPeak,a,b);
			if (whole <= 0) continue;
			const double wa = Cross(p,b,ArrowPeak)/whole, wb = Cross(p,ArrowPeak,a)/whole, wp = Cross(p,a,b)/whole;
			if (wa >= -1e-9 && wb >= -1e-9 && wp >= -1e-9) { face = ArrowFace[i]; toEdge = 1-wp; break; }
		}
		const FaceShade& shade = ArrowShade[face];
		Colour colour = Mix(shade.peak,shade.edge,toEdge);
		// The bevel's ridges catch the light: the long one from the peak to
		// the tip most, the one to the corner less.
		const auto ridge = [&](const Point& end, double strength, double width) {
			const double d = SegmentDistance(p,ArrowPeak,end)/width;
			return d < 3 ? strength*std::exp(-d*d) : 0.0;
		};
		colour = Mix(colour,Hex(0xFFFFFF),std::max(ridge(points[0],.6,.5),ridge(points[1],.3,.45)));
		// A little darker towards the foot, as the stock body is.
		const double fall = 1-.1*std::clamp(p.y/27.5,0.0,1.0);
		return {colour.r*fall,colour.g*fall,colour.b*fall};
	}
};

} // namespace

bool RasterizePointer(PointerShape kind, float pixelsPerTexel, PointerImage& result) {
	if (!std::isfinite(pixelsPerTexel) || pixelsPerTexel < .25f || pixelsPerTexel > 16.f) return false;
	const double unit = pixelsPerTexel;
	const bool arrow = kind == PointerShape::Arrow;
	Shape shape{arrow ? std::vector<Point>(ArrowSilhouette,ArrowSilhouette+ArrowPoints) : TextSilhouette(unit),0,arrow,
		arrow ? std::max(.85,1.0/unit) : std::max(.7,.8/unit)};
	shape.count = static_cast<int>(shape.points.size());

	double minX = 1e30, minY = 1e30, maxX = -1e30, maxY = -1e30;
	for (int i = 0; i < shape.count; ++i) {
		minX = std::min(minX,shape.points[i].x); maxX = std::max(maxX,shape.points[i].x);
		minY = std::min(minY,shape.points[i].y); maxY = std::max(maxY,shape.points[i].y);
	}
	const double sigma = std::max(ShadowSigma*unit,.6), shiftX = ShadowX*unit, shiftY = ShadowY*unit;
	const int radius = static_cast<int>(std::ceil(3*sigma));
	// Room for the whole blur on every side, the cast included: the kernel's
	// tail reaches back past the body above and to the left.
	const int left = static_cast<int>(std::floor(std::min(minX*unit,minX*unit+shiftX-radius)))-1;
	const int top = static_cast<int>(std::floor(std::min(minY*unit,minY*unit+shiftY-radius)))-1;
	const int right = static_cast<int>(std::ceil(maxX*unit+shiftX))+radius+1;
	const int bottom = static_cast<int>(std::ceil(maxY*unit+shiftY))+radius+1;
	const int width = right-left, height = bottom-top;

	// The body: premultiplied colour and coverage per pixel.
	std::vector<double> colour(static_cast<size_t>(width)*height*3,0.0), coverage(static_cast<size_t>(width)*height,0.0);
	const double reach = .75/unit; // a pixel's half-diagonal, in texels
	for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
		const Point centre{(x+left+.5)/unit,(y+top+.5)/unit};
		const bool inside = shape.Inside(centre);
		const double edge = shape.EdgeDistance(centre);
		const size_t at = static_cast<size_t>(y)*width+x;
		if (edge >= reach && !inside) continue;
		Colour sum{0,0,0}; int covered = 0;
		// The pixel's centre settles what its whole square shares: whether
		// all of it is inside, and whether all of it is on or off the rim.
		const bool crossesEdge = edge < reach, crossesRim = std::abs(edge-shape.rim) < reach;
		const int rimTest = crossesEdge || crossesRim ? -1 : edge < shape.rim ? 1 : 0;
		if (crossesEdge || crossesRim || shape.FaceDistance(centre) < reach) {
			for (int sy = 0; sy < Samples; ++sy) for (int sx = 0; sx < Samples; ++sx) {
				const Point p{(x+left+(sx+.5)/Samples)/unit,(y+top+(sy+.5)/Samples)/unit};
				if (crossesEdge && !shape.Inside(p)) continue;
				const Colour c = shape.Shade(p,rimTest);
				sum.r += c.r; sum.g += c.g; sum.b += c.b; ++covered;
			}
			const double scale = 1.0/(Samples*Samples);
			sum = {sum.r*scale,sum.g*scale,sum.b*scale};
			coverage[at] = covered*scale;
		} else {
			sum = shape.Shade(centre,rimTest); coverage[at] = 1;
		}
		colour[at*3] = sum.r; colour[at*3+1] = sum.g; colour[at*3+2] = sum.b;
	}

	// The shadow: the coverage moved by the cast and blurred, in two passes
	// whose kernels carry the cast's fraction of a pixel.
	const auto kernel = [&](double shift, int& first) {
		first = static_cast<int>(std::floor(shift))-radius;
		std::vector<double> weights(static_cast<size_t>(2*radius+2));
		double total = 0;
		for (size_t i = 0; i < weights.size(); ++i) {
			const double d = first+static_cast<int>(i)-shift;
			total += weights[i] = std::exp(-d*d/(2*sigma*sigma));
		}
		for (double& w : weights) w /= total;
		return weights;
	};
	int firstX = 0, firstY = 0;
	const std::vector<double> kx = kernel(shiftX,firstX), ky = kernel(shiftY,firstY);
	std::vector<double> across(coverage.size(),0.0), shadow(coverage.size(),0.0);
	for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
		double sum = 0;
		for (size_t i = 0; i < kx.size(); ++i) {
			const int from = x-(firstX+static_cast<int>(i));
			if (from >= 0 && from < width) sum += coverage[static_cast<size_t>(y)*width+from]*kx[i];
		}
		across[static_cast<size_t>(y)*width+x] = sum;
	}
	for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
		double sum = 0;
		for (size_t i = 0; i < ky.size(); ++i) {
			const int from = y-(firstY+static_cast<int>(i));
			if (from >= 0 && from < height) sum += across[static_cast<size_t>(from)*width+x]*ky[i];
		}
		shadow[static_cast<size_t>(y)*width+x] = sum;
	}

	PointerImage image;
	image.width = width; image.height = height; image.hotspotX = -left; image.hotspotY = -top;
	image.pixels.resize(static_cast<size_t>(width)*height*4);
	const auto byteOf = [](double v) { return static_cast<unsigned char>(std::clamp(v,0.0,1.0)*255.0+.5); };
	for (size_t at = 0; at < coverage.size(); ++at) {
		// The body over its shadow; the shadow is black, so it adds only alpha.
		const double alpha = coverage[at]+ShadowOpacity*shadow[at]*(1-coverage[at]);
		unsigned char* pixel = image.pixels.data()+at*4;
		pixel[0] = byteOf(colour[at*3]); pixel[1] = byteOf(colour[at*3+1]); pixel[2] = byteOf(colour[at*3+2]);
		pixel[3] = std::max({byteOf(alpha),pixel[0],pixel[1],pixel[2]});
	}
	result = std::move(image);
	return true;
}

} // namespace openq4::ui
