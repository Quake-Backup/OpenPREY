#!/usr/bin/env python3
"""Render openPR06's logo banner and its social preview.

    assets/docs/img/banner.png          the logo on a transparent ground (README)
    assets/docs/img/social-preview.jpg  1280x640, the logo over space (GitHub)

The logo is a variant of openQ4's and openD3's: the "open" lettering is
openQ4's own pixels, kept as a layer in assets/docs/img/src/banner-open.png,
and everything else is drawn here. "PR" is lettered after the PREY menu
wordmark (very wide extended capitals, a dark navy fill, a thin cyan-white
edge and a blue lens streak), extruded and keylined as openD3 letters "D3",
with a small superscript "06". It stands on openQ4's plate, lit teal, with the
hawk Talon's insignia across it where openD3 has its pentagram. The lettering
covers the insignia's body, so its wings and tail show, a little hotter than
the glow around them.

The insignia is the line work of the application icon
(assets/icons/prey_1024.png), kept as assets/docs/img/src/talon-insignia.png.
Letterforms are the polygons below; every texture is procedural.

Usage:
    python tools/assets/build_banner.py
    python tools/assets/build_banner.py --only banner
    python tools/assets/build_banner.py --extract-insignia
    python tools/assets/build_banner.py --extract-open path/to/openQ4/assets/docs/img/banner.png

Requires numpy, opencv-python and Pillow.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
IMG = REPO / "assets" / "docs" / "img"
OPEN_LAYER = IMG / "src" / "banner-open.png"
INSIGNIA_LAYER = IMG / "src" / "talon-insignia.png"
ICON = REPO / "assets" / "icons" / "prey_1024.png"
BANNER = IMG / "banner.png"
SOCIAL = IMG / "social-preview.jpg"   # GitHub takes up to 1 MB

WIDTH, HEIGHT = 1024, 386
LAYER_WIDTH = 1024  # openQ4's banner, and so the "open" layer
SS = 4  # supersampling factor; all geometry below is in final pixels

# The plate, clockwise from top left: openQ4's outline, run out to the right
# to make room for the superscript.
PLATE = ((478.0, 88.0), (1006.0, 80.0), (887.0, 310.0), (343.0, 347.0))

# Lettering. Glyph units: one unit is the capital height.
CAP = 142.0                  # pixels per unit
GLYPH_ORIGIN = (434.0, 128.0)
GLYPH_GAP = 0.13             # between the P and the R, in units
SUPER_SCALE = 0.43           # superscript height, in capitals
SUPER_GAP = 0.09             # R to the superscript, in capitals
SUPER_DIGIT_GAP = 0.10       # between the digits, in superscript units
EXTRUDE = (3.5, 10.0)        # depth of the lettering, towards lower right

# Very wide extended capitals with cut corners, after the PREY wordmark.
P_OUTER = ((0, 0), (1.10, 0), (1.25, 0.13), (1.25, 0.47), (1.10, 0.60), (0.27, 0.60),
           (0.27, 1.0), (0, 1.0))
P_COUNTER = ((0.27, 0.21), (0.98, 0.21), (0.98, 0.39), (0.27, 0.39))
R_OUTER = ((0, 0), (1.15, 0), (1.30, 0.13), (1.30, 0.47), (1.17, 0.60), (1.36, 1.0),
           (1.06, 1.0), (0.88, 0.62), (0.27, 0.62), (0.27, 1.0), (0, 1.0))
R_COUNTER = ((0.27, 0.21), (1.03, 0.21), (1.03, 0.41), (0.27, 0.41))
ZERO_OUTER = ((0.13, 0), (0.95, 0), (1.08, 0.13), (1.08, 0.87), (0.95, 1.0), (0.13, 1.0),
              (0, 0.87), (0, 0.13))
ZERO_COUNTER = ((0.27, 0.23), (0.81, 0.23), (0.81, 0.77), (0.27, 0.77))
SIX_OUTER = ((0.13, 0), (1.04, 0), (1.04, 0.22), (0.27, 0.22), (0.27, 0.39), (0.95, 0.39),
             (1.08, 0.52), (1.08, 0.87), (0.95, 1.0), (0.13, 1.0), (0, 0.87), (0, 0.13))
SIX_COUNTER = ((0.27, 0.60), (0.81, 0.60), (0.81, 0.79), (0.27, 0.79))

# The insignia: centre and height on the banner.
INSIGNIA_CENTRE = (662.0, 220.0)
INSIGNIA_HEIGHT = 248.0
INSIGNIA_STRETCH = 1.75   # widened, as the lettering is
INSIGNIA_LINE = 0.85     # how far the lines move towards the hotter colour
INSIGNIA_BLOOM = 0.22

# Prey's palette (docs/dev/prey-ui-visual-design.md): wordmark fill and edge,
# lens streak, and a teal glow from the nebula's teal to the portal core.
FACE_STOPS = (
    (0.00, (0x16, 0x30, 0x4C)),
    (0.55, (0x01, 0x02, 0x04)),
    (1.00, (0x10, 0x24, 0x3A)),
)
EDGE = (0xAF, 0xFC, 0xFF)
STREAK = (0x33, 0x80, 0xB1)
GLOW_STOPS = (
    (0.00, (1, 3, 4)),
    (0.18, (2, 12, 15)),
    (0.36, (4, 40, 48)),
    (0.54, (8, 88, 100)),
    (0.70, (20, 145, 160)),
    (0.84, (31, 185, 190)),
    (0.94, (110, 228, 232)),
    (1.00, (190, 252, 255)),
)


def ramp(t: np.ndarray, stops) -> np.ndarray:
    xs = [s[0] for s in stops]
    out = np.empty(t.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(t, xs, [s[1][c] for s in stops])
    return out / 255.0


def rgb(c) -> np.ndarray:
    return np.array(c, np.float32) / 255.0


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def fbm(shape, rng, cell, octaves=4, stretch=(1.0, 1.0)) -> np.ndarray:
    """Value noise in roughly [-1, 1]; `cell` is the coarsest feature size."""
    acc = np.zeros(shape, np.float32)
    amp, total = 1.0, 0.0
    for _ in range(octaves):
        gh = max(2, int(shape[0] / (cell * stretch[1])) + 2)
        gw = max(2, int(shape[1] / (cell * stretch[0])) + 2)
        grid = rng.random((gh, gw)).astype(np.float32)
        acc += amp * cv2.resize(grid, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
        total += amp
        amp *= 0.5
        cell /= 2.0
    return acc / total * 2.0 - 1.0


def edge_distance(X, Y, p, q):
    """Signed distance to the line p->q, positive on the inside of a clockwise polygon."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    length = math.hypot(dx, dy)
    return ((Y - p[1]) * dx - (X - p[0]) * dy) / length


def over(dst_rgb, dst_a, src_rgb, src_a):
    """Composite straight-alpha `src` over premultiplied `dst`, in place."""
    src_a = src_a[..., None]
    dst_rgb *= 1.0 - src_a
    dst_rgb += src_rgb * src_a
    dst_a *= 1.0 - src_a[..., 0]
    dst_a += src_a[..., 0]


def fill_polygon(mask, points, value):
    pts = np.round(np.array(points, np.float64) * SS * 16).astype(np.int32)
    cv2.fillPoly(mask, [pts], value, lineType=cv2.LINE_8, shift=4)


def glyph(points, x, y, scale):
    return [(x + px * scale, y + py * scale) for px, py in points]


def glyph_layout():
    """(outer, counter) polygons in banner pixels, and the lettering's box."""
    ox, oy = GLYPH_ORIGIN
    shapes = []
    shapes.append((glyph(P_OUTER, ox, oy, CAP), glyph(P_COUNTER, ox, oy, CAP)))
    rx = ox + (1.25 + GLYPH_GAP) * CAP
    shapes.append((glyph(R_OUTER, rx, oy, CAP), glyph(R_COUNTER, rx, oy, CAP)))
    sx = rx + (1.36 + SUPER_GAP) * CAP
    s = CAP * SUPER_SCALE
    shapes.append((glyph(ZERO_OUTER, sx, oy, s), glyph(ZERO_COUNTER, sx, oy, s)))
    sx += (1.08 + SUPER_DIGIT_GAP) * s
    shapes.append((glyph(SIX_OUTER, sx, oy, s), glyph(SIX_COUNTER, sx, oy, s)))
    right = sx + 1.08 * s
    return shapes, (ox, oy, right, oy + CAP)


def render_plate(X, Y, rng):
    tl, tr, br, bl = PLATE
    d_top = edge_distance(X, Y, tl, tr)
    d_right = edge_distance(X, Y, tr, br)
    d_bottom = edge_distance(X, Y, br, bl)
    d_left = edge_distance(X, Y, bl, tl)

    shape = X.shape
    hard = np.clip(np.minimum(np.minimum(d_top, d_right), d_bottom) + 0.5, 0.0, 1.0)
    # The left edge has no line: the plate dissolves, further towards the bottom.
    down = np.clip((Y - tl[1]) / (bl[1] - tl[1]), 0.0, 1.0)
    alpha = hard * smoothstep(-(62.0 + 58.0 * down), 26.0, d_left)

    across = np.clip(d_left / np.maximum(d_left + d_right, 1e-3), 0.0, 1.0)
    haze = fbm(shape, rng, 150 * SS, octaves=4, stretch=(2.2, 1.0))
    wisps = fbm(shape, rng, 46 * SS, octaves=4, stretch=(3.0, 1.0))
    heat = np.clip(across ** 1.2 + 0.12 * haze + 0.04 * wisps, 0.0, 1.0)
    out = ramp(heat, GLOW_STOPS)
    out *= (1.0 + 0.26 * wisps)[..., None]

    # A hot line along the three hard edges, as on openQ4's plate.
    d_edge = np.minimum(np.minimum(d_top, d_right), d_bottom)
    lit = smoothstep(0.30, 0.85, across)
    rim = np.exp(-((d_edge - 1.2) / 1.5) ** 2) * lit
    inner = np.exp(-np.maximum(d_edge, 0.0) / 13.0) * lit
    out += rim[..., None] * np.array([0.72, 1.0, 1.0], np.float32) * 0.85
    out += inner[..., None] * np.array([0.12, 0.85, 0.90], np.float32) * 0.22
    return out, alpha, heat


def insignia_lines(shape, centre, height, stretch=1.0, warp=None):
    """Line coverage and soft halo of the insignia, both in 0..1, at SS scale.

    `warp` is an optional 3x3 homography applied after placing the insignia."""
    src = np.asarray(Image.open(INSIGNIA_LAYER).convert("L"), np.float32) / 255.0
    sh, sw = src.shape
    scale = height * SS / sh
    cx, cy = centre[0] * SS, centre[1] * SS
    place = np.array([[scale * stretch, 0, cx - sw * scale * stretch / 2], [0, scale, cy - sh * scale / 2], [0, 0, 1]],
                     np.float64)
    if warp is not None:
        s = np.diag([SS, SS, 1.0])
        place = s @ warp @ np.linalg.inv(s) @ place
    core = cv2.warpPerspective(src, place, (shape[1], shape[0]), flags=cv2.INTER_LINEAR)
    halo = cv2.GaussianBlur(core, (0, 0), 6.0 * SS)
    halo /= max(float(halo.max()), 1e-6)
    return np.clip(core, 0.0, 1.0), halo


def unit_gradient(field, sigma):
    smooth = cv2.GaussianBlur(field, (0, 0), sigma)
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    norm = np.maximum(np.hypot(gx, gy), 1e-6)
    return gx / norm, gy / norm


def render_lettering(X, Y, rng):
    shape = X.shape
    face = np.zeros(shape, np.uint8)
    shapes, (left, top, right, bottom) = glyph_layout()
    for outer, counter in shapes:
        fill_polygon(face, outer, 255)
        fill_polygon(face, counter, 0)
    face_b = face > 0

    # Sweep the face along the extrusion to get the solid's silhouette.
    solid = face_b.copy()
    steps = int(max(EXTRUDE) * SS)
    for i in range(1, steps + 1):
        dx = int(round(EXTRUDE[0] * SS * i / steps))
        dy = int(round(EXTRUDE[1] * SS * i / steps))
        solid[dy:, dx:] |= face_b[:shape[0] - dy, :shape[1] - dx]

    d_out = cv2.distanceTransform((~face_b).astype(np.uint8), cv2.DIST_L2, 5) / SS
    d_in = cv2.distanceTransform(face_b.astype(np.uint8), cv2.DIST_L2, 5) / SS
    d_solid = cv2.distanceTransform((~solid).astype(np.uint8), cv2.DIST_L2, 5) / SS

    # --- face: the wordmark's dark navy, top to foot ------------------
    t = np.clip((Y - top) / (bottom - top), 0.0, 1.0)
    out = ramp(t, FACE_STOPS)
    sheen = fbm(shape, rng, 60 * SS, octaves=3, stretch=(3.0, 1.0))
    out *= (1.0 + 0.18 * sheen)[..., None]
    # A faint reflection of the plate's teal in the lower half.
    across = np.clip((X - left) / (right - left), 0.0, 1.0)
    out += (smoothstep(0.55, 1.0, t) * (0.25 + 0.75 * across) * 0.10)[..., None] * rgb((31, 185, 190))
    # The lens streak through the letters' middle.
    mid = top + 0.50 * (bottom - top)
    streak = np.exp(-((Y - mid) / 7.0) ** 2) * (0.55 + 0.45 * across)
    out += (streak * 0.55)[..., None] * rgb(STREAK)

    # Bevel: a thin cyan-white edge lit from the upper left, a dark seam inside.
    nx, ny = unit_gradient(d_in, 1.0 * SS)
    light = np.clip(0.5 + 0.5 * (nx * 0.5 + ny * 0.866), 0.0, 1.0)
    edge = rgb((0x2F, 0x64, 0xDC)) + light[..., None] * (rgb(EDGE) - rgb((0x2F, 0x64, 0xDC)))
    rim = 1.0 - smoothstep(1.6, 2.4, d_in)
    seam = smoothstep(1.6, 2.3, d_in) * (1.0 - smoothstep(2.9, 3.9, d_in))
    out *= (1.0 - 0.6 * seam)[..., None]
    glow = np.exp(-np.maximum(d_in - 2.0, 0.0) / 5.0) * (1.0 - rim) * light
    out += (glow * 0.16)[..., None] * rgb(EDGE)
    out += (edge - out) * rim[..., None]
    face_rgb = np.clip(out, 0.0, 1.0)

    # --- side walls: lit teal from below, slate at the sides ----------
    gx, gy = unit_gradient(d_out, 1.2 * SS)
    depth = np.clip(d_out / math.hypot(*EXTRUDE), 0.0, 1.0)
    below = np.clip(gy, 0.0, 1.0)
    beside = np.clip(gx, 0.0, 1.0)
    weight = below + beside + 1e-4
    lower = rgb((120, 236, 236)) + (depth ** 0.7)[..., None] * (rgb((6, 70, 84)) - rgb((120, 236, 236)))
    side = rgb((0x4A, 0x6F, 0x84)) + depth[..., None] * (rgb((0x0F, 0x17, 0x1B)) - rgb((0x4A, 0x6F, 0x84)))
    wall_rgb = (lower * below[..., None] + side * beside[..., None]) / weight[..., None]

    letter_rgb = np.where(face_b[..., None], face_rgb, np.clip(wall_rgb, 0.0, 1.0))
    solid_f = solid.astype(np.float32)
    outline = np.clip(2.2 - d_solid, 0.0, 1.0)          # black keyline, also covers the solid
    shadow = cv2.GaussianBlur(solid_f, (0, 0), 7.0 * SS)
    shadow = np.roll(np.roll(shadow, 5 * SS, axis=0), 3 * SS, axis=1) * 0.8
    return letter_rgb, solid_f, outline, shadow


def render_logo() -> np.ndarray:
    """The logo as straight-alpha RGBA floats, WIDTH x HEIGHT."""
    rng = np.random.default_rng(2006)
    h, w = HEIGHT * SS, WIDTH * SS
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    X = (xs + 0.5) / SS
    Y = (ys + 0.5) / SS
    del xs, ys

    plate_rgb, plate_a, heat = render_plate(X, Y, rng)
    core, halo = insignia_lines(X.shape, INSIGNIA_CENTRE, INSIGNIA_HEIGHT, INSIGNIA_STRETCH)
    # Hotter than the glow it sits in, and only just: a bright line with a faint bloom.
    hot = ramp(np.clip(heat + 0.38, 0.0, 1.0), GLOW_STOPS)
    plate_rgb += (hot - plate_rgb) * (INSIGNIA_LINE * core + INSIGNIA_BLOOM * halo)[..., None]
    plate_rgb = np.clip(plate_rgb, 0.0, 1.0)

    out_rgb = plate_rgb * plate_a[..., None]     # premultiplied from here on
    alpha = plate_a.copy()

    letter_rgb, solid, outline, shadow = render_lettering(X, Y, rng)
    black = np.zeros_like(letter_rgb)
    over(out_rgb, alpha, black, shadow)
    over(out_rgb, alpha, black, outline)
    over(out_rgb, alpha, letter_rgb, solid)

    out_rgb = cv2.resize(out_rgb, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    alpha = cv2.resize(alpha, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)

    layer = np.asarray(Image.open(OPEN_LAYER).convert("RGBA"), np.float32) / 255.0
    if layer.shape[:2] != (HEIGHT, LAYER_WIDTH):
        raise SystemExit(f"{OPEN_LAYER} is not {LAYER_WIDTH}x{HEIGHT}")
    layer = layer[:, :WIDTH]
    over(out_rgb, alpha, layer[..., :3], layer[..., 3])

    straight = out_rgb / np.maximum(alpha, 1e-5)[..., None]
    out = np.dstack([np.clip(straight, 0.0, 1.0), np.clip(alpha, 0.0, 1.0)])
    out[out[..., 3] < 0.5 / 255.0] = 0.0
    return out


def to_image(rgba: np.ndarray) -> Image.Image:
    return Image.fromarray(np.round(np.clip(rgba, 0.0, 1.0) * 255.0).astype(np.uint8))


def extract_open(source: Path) -> None:
    """Lift the "open" lettering out of openQ4's banner, on the banner's canvas."""
    banner = np.asarray(Image.open(source).convert("RGBA"))
    if banner.shape[:2] != (HEIGHT, LAYER_WIDTH):
        raise SystemExit(f"{source} is not {LAYER_WIDTH}x{HEIGHT}")
    alpha = banner[..., 3].astype(np.float32) / 255.0
    box = np.zeros(alpha.shape, bool)
    box[156:252, 12:398] = True
    fill = (banner[..., :3].min(axis=2) > 150) & (alpha > 0.5) & box
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    near = cv2.dilate(fill.astype(np.uint8), kernel).astype(np.float32)
    near = np.clip((cv2.GaussianBlur(near, (0, 0), 1.2) - 0.25) / 0.5, 0.0, 1.0)
    layer = banner.copy()
    layer[..., 3] = np.round(alpha * near * 255.0).astype(np.uint8)
    layer[layer[..., 3] == 0] = 0
    OPEN_LAYER.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(layer).save(OPEN_LAYER, optimize=True)
    print(f"wrote {OPEN_LAYER.relative_to(REPO)}")


def extract_insignia() -> None:
    """Keep the icon's white line work: Talon's outline and the seams of body and wings."""
    icon = np.asarray(Image.open(ICON).convert("RGBA")).astype(np.int32)
    white = (icon[..., :3].min(axis=2) > 190) & (icon[..., 3] > 128)
    ys, xs = np.nonzero(white)
    crop = white[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32)
    crop = cv2.GaussianBlur(crop, (0, 0), 0.8)
    INSIGNIA_LAYER.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.round(np.clip(crop, 0, 1) * 255).astype(np.uint8)).save(INSIGNIA_LAYER, optimize=True)
    print(f"wrote {INSIGNIA_LAYER.relative_to(REPO)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--extract-open", type=Path, metavar="BANNER",
                        help="rebuild the 'open' layer from openQ4's banner and exit")
    parser.add_argument("--extract-insignia", action="store_true",
                        help="rebuild the insignia layer from the application icon and exit")
    parser.add_argument("--only", choices=("banner", "social"))
    parser.add_argument("--earth-maps", nargs=2, type=Path, metavar=("DAY", "NIGHT"),
                        help="rebuild the social preview's Earth from NASA's day and night maps")
    args = parser.parse_args()
    if args.extract_open:
        extract_open(args.extract_open)
        return
    if args.extract_insignia:
        extract_insignia()
        return
    logo = render_logo()
    if args.only in (None, "banner"):
        to_image(logo).save(BANNER, optimize=True)
        print(f"wrote {BANNER.relative_to(REPO)}")
    if args.only in (None, "social"):
        import build_social_preview  # noqa: PLC0415  (sibling module)
        build_social_preview.render(logo, args.earth_maps).save(SOCIAL, quality=93, subsampling=0, optimize=True)
        print(f"wrote {SOCIAL.relative_to(REPO)}")


if __name__ == "__main__":
    main()
