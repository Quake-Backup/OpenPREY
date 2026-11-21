#!/usr/bin/env python3
"""Render openPR06's social preview, assets/docs/img/social-preview.jpg.

Called by build_banner.py, which renders the logo first. A 1280x640 view from
just above the Sphere: its armoured, living hull curves away to a horizon with
light rising behind it; Earth hangs out of focus to the upper left; a blue and
teal nebula and a star field fill the sky; the hawk Talon's insignia is drawn
faintly across the back, out of focus and receding from the right edge. The
logo stands in front and the tagline sits under it between bracket marks, as
on openQ4's preview.

Everything is rendered here, in raster: the Sphere is ray-traced against a
height field and shaded, the stars are point sources with a soft spread, the
nebula is layered emission and dust. Earth starts from NASA's public-domain
maps ("Whole world - land and oceans" and "The earth at night", Wikimedia
Commons), regraded and given painted clouds, twilight, atmosphere and glint;
the rendered globe is kept as assets/docs/img/src/social-earth.png so a build
does not need the maps. Rebuild it with --earth-maps DAY NIGHT.

Usage:
    python tools/assets/build_banner.py --only social
    python tools/assets/build_banner.py --only social --earth-maps day.jpg night.jpg
"""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import build_banner as bb

WIDTH, HEIGHT = 1280, 640
SS = 2                                   # supersampling of the rendered layers
W, H = WIDTH * SS, HEIGHT * SS
EARTH_LAYER = bb.IMG / "src" / "social-earth.png"

TAGLINE = ("The modern way to play ", "PREY")
FONT = "C:/Windows/Fonts/GOTHICI.TTF"   # Century Gothic Italic: a plain geometric sans
FONT_FALLBACKS = ("C:/Windows/Fonts/GOTHIC.TTF", "DejaVuSans-Oblique.ttf", "DejaVuSans.ttf")

LOGO_WIDTH = 860.0
LOGO_CENTRE_Y = 258.0
TAGLINE_Y = 446.0

# Earth, in output pixels; it is rendered at this size and then defocused.
EARTH_CENTRE = (96.0, 88.0)
EARTH_RADIUS = 172.0
EARTH_VIEW = (24.0, 18.0, -16.0)         # latitude, longitude and roll at the disc's centre, degrees
EARTH_LIGHT = (0.62, -0.50, -0.30)      # towards the light, view space (x right, y up, z out)
EARTH_DEFOCUS = 4.2                      # output pixels
EARTH_HAZE = 0.34

# The Sphere: camera height over a hull of radius R; horizon at HORIZON of the frame.
SPHERE_R = 1000.0
CAMERA_HEIGHT = 260.0
HFOV = math.radians(68.0)
HORIZON = 0.815
SUN_AZIMUTH = math.radians(1.5)
SUN_ABOVE_HORIZON = math.radians(0.6)

TALON_QUAD = ((660, 140), (1420, -120), (1420, 700), (660, 470))
TALON_BLUR = 3.0

TEAL = bb.rgb((0x1B, 0xDD, 0xEF))
CORE = bb.rgb((0xAF, 0xFC, 0xFF))
STREAK = bb.rgb((0x33, 0x80, 0xB1))
BIO = bb.rgb((0x3C, 0xE0, 0x9A))


# --- noise at arbitrary coordinates -----------------------------------------

def _hash(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFFFF).astype(np.float32) / 16777216.0


def vnoise(u, v, seed):
    """Smooth value noise in [0, 1] at float coordinates."""
    iu, iv = np.floor(u), np.floor(v)
    fu, fv = u - iu, v - iv
    iu, iv = iu.astype(np.int64), iv.astype(np.int64)
    su, sv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    a, b = _hash(iu, iv, seed), _hash(iu + 1, iv, seed)
    c, d = _hash(iu, iv + 1, seed), _hash(iu + 1, iv + 1, seed)
    return (a + (b - a) * su) + ((c + (d - c) * su) - (a + (b - a) * su)) * sv


def fbm(u, v, seed, octaves, lacunarity=2.03, gain=0.5):
    total, amp, norm = np.zeros_like(u), 1.0, 0.0
    for o in range(octaves):
        total += amp * vnoise(u, v, seed + o * 17)
        norm += amp
        amp *= gain
        u, v = u * lacunarity + 11.7, v * lacunarity - 5.3
    return total / norm


def worley(u, v, seed, jitter=0.9):
    """Distances to the nearest and second nearest feature point, and the cell's random id."""
    iu, iv = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    f1 = np.full(u.shape, 9.0, np.float32)
    f2 = np.full(u.shape, 9.0, np.float32)
    cid = np.zeros(u.shape, np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = iu + dx, iv + dy
            px = cx + 0.5 + (_hash(cx, cy, seed) - 0.5) * jitter
            py = cy + 0.5 + (_hash(cx, cy, seed + 1) - 0.5) * jitter
            d = np.hypot(u - px, v - py).astype(np.float32)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            cid = np.where(closer, _hash(cx, cy, seed + 2), cid)
            f1 = np.where(closer, d, f1)
    return f1, f2, cid


def smoothstep(a, b, x):
    return bb.smoothstep(a, b, x)


# --- the sky -----------------------------------------------------------------

def render_nebula(rng):
    """Layered emission and dust, at half resolution; returned at W x H (HDR, linear)."""
    h, w = H // 2, W // 2
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xs / w * 4.0, ys / h * 2.0
    # Domain warp gives the gas its swirl.
    wu = fbm(u * 0.9, v * 0.9, 301, 4) - 0.5
    wv = fbm(u * 0.9 + 4.1, v * 0.9 - 2.2, 307, 4) - 0.5
    gu, gv = u + wu * 1.6, v + wv * 1.6
    gas = fbm(gu, gv, 311, 6)
    filaments = 1 - np.abs(fbm(gu * 2.2, gv * 2.2, 331, 5) * 2 - 1)
    dust = fbm(gu * 1.4 + 9, gv * 1.4, 351, 6)
    # A broad band across the frame, low on the left and high on the right.
    band_y = 0.62 - 0.38 * (xs / w)
    band = np.exp(-((ys / h - band_y) / 0.30) ** 2)
    density = np.clip((gas - 0.38) * 2.2, 0, 1) ** 1.6 * (0.35 + 0.65 * band)
    across = (xs / w)[..., None]
    colour = (bb.rgb((0x5B, 0x2E, 0xA6)) * np.clip(1.0 - across * 2.2, 0, 1) * 0.9
              + bb.rgb((0x1F, 0x4F, 0xB8)) * 1.0
              + bb.rgb((0x14, 0x97, 0xB8)) * np.clip(across * 1.6 - 0.4, 0, 1) * 1.3)
    emission = colour * (density * 0.10 + density * filaments ** 6 * 0.20)[..., None]
    emission += bb.rgb((150, 205, 255)) * (density ** 3 * filaments ** 10 * 0.35)[..., None]
    # Dust lanes absorb the emission in front of it.
    absorb = np.clip((dust - 0.46) * 3.0, 0, 1) * (0.4 + 0.6 * band)
    transmit = np.exp(-absorb * 2.4)
    emission *= transmit[..., None]
    emission = cv2.GaussianBlur(emission, (0, 0), 1.2)
    out = cv2.resize(emission, (W, H), interpolation=cv2.INTER_CUBIC)
    trans = cv2.resize(transmit, (W, H), interpolation=cv2.INTER_CUBIC)
    band_full = cv2.resize(band, (W, H), interpolation=cv2.INTER_CUBIC)
    return np.clip(out, 0, None), trans, band_full


def render_stars(rng, density_map, transmit) -> np.ndarray:
    """Point stars with a soft spread, coloured by temperature, denser along the band."""
    out = np.zeros((H, W, 3), np.float32)
    n = 26000
    xs = rng.random(n * 3) * W
    ys = rng.random(n * 3) * H
    keep = rng.random(n * 3) < (0.25 + 0.75 * density_map[ys.astype(int), xs.astype(int)])
    xs, ys = xs[keep][:n], ys[keep][:n]
    n = len(xs)
    flux = (rng.pareto(1.35, n) + 1) * 0.010
    flux = np.minimum(flux, 6.0)
    flux *= transmit[ys.astype(int), xs.astype(int)] ** 0.7
    temps = rng.choice(4, n, p=[0.30, 0.42, 0.20, 0.08])
    palette = np.array([[0.70, 0.80, 1.00], [0.92, 0.95, 1.00], [1.00, 0.93, 0.80], [1.00, 0.78, 0.58]], np.float32)
    col = palette[temps] * flux[:, None]
    # Splat with bilinear weights so stars sit between pixels.
    x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
    fx, fy = (xs - x0)[:, None], (ys - y0)[:, None]
    for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        xi, yi = np.clip(x0 + dx, 0, W - 1), np.clip(y0 + dy, 0, H - 1)
        np.add.at(out, (yi, xi), (col * wgt).astype(np.float32))
    core = cv2.GaussianBlur(out, (0, 0), 0.62 * SS) * (2 * math.pi * (0.62 * SS) ** 2)
    halo = cv2.GaussianBlur(out, (0, 0), 2.6 * SS) * (2 * math.pi * (2.6 * SS) ** 2) * 0.035
    stars = core * 0.9 + halo
    # A few faint, short diffraction spikes on the brightest.
    spikes = np.zeros((H, W), np.float32)
    for i in np.argsort(flux)[-5:]:
        length = int((10 + 22 * min(flux[i], 3.0)) * SS)
        x, y = int(xs[i]), int(ys[i])
        for ddx, ddy in ((1, 0), (0, 1)):
            for t in range(-length, length + 1):
                px, py = x + ddx * t, y + ddy * t
                if 0 <= px < W and 0 <= py < H:
                    spikes[py, px] += flux[i] * 0.03 * math.exp(-abs(t) / (length * 0.35))
    spikes = cv2.GaussianBlur(spikes, (0, 0), 0.6 * SS)
    stars += spikes[..., None] * bb.rgb((215, 228, 255))
    return stars


# --- Earth --------------------------------------------------------------------

def render_earth_layer(day_path: Path, night_path: Path) -> None:
    """Render Earth once from NASA's maps into EARTH_LAYER (premultiplied RGBA, 16-bit)."""
    r = EARTH_RADIUS * SS
    margin = int(r * 0.12)
    size = int(2 * r) + 2 * margin
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    dx = (xs + 0.5 - size / 2) / r
    dy = -(ys + 0.5 - size / 2) / r
    rr = dx * dx + dy * dy
    nz = np.sqrt(np.clip(1 - rr, 0, 1))

    lat0, lon0, roll = (math.radians(a) for a in EARTH_VIEW)
    cr, sr = math.cos(roll), math.sin(roll)
    x1, y1 = dx * cr - dy * sr, dx * sr + dy * cr
    ca, sa = math.cos(lat0), math.sin(lat0)
    y2 = y1 * ca + nz * sa
    z2 = -y1 * sa + nz * ca
    lat = np.arcsin(np.clip(y2, -1, 1))
    lon = np.arctan2(x1, z2) + lon0

    def sample(img):
        mh, mw = img.shape[:2]
        mx = ((lon + math.pi) / (2 * math.pi) % 1.0) * mw
        my = (math.pi / 2 - lat) / math.pi * mh
        return cv2.remap(img, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_WRAP)

    day = (np.asarray(Image.open(day_path).convert("RGB"), np.float32) / 255.0) ** 2.2
    night = (np.asarray(Image.open(night_path).convert("RGB"), np.float32) / 255.0) ** 2.2

    # Grade the base: oceans deeper and a touch teal, land a little warmer and calmer.
    dmh, dmw = day.shape[:2]
    lum = day @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    water = ((day[..., 2] > day[..., 0] * 1.25) & (lum < 0.12)).astype(np.float32)
    water = cv2.GaussianBlur(water, (0, 0), 1.5)
    ocean = day * np.array([0.55, 0.85, 1.25], np.float32) * 0.85
    land = day ** 1.08 * np.array([1.06, 1.0, 0.86], np.float32)
    base = ocean * water[..., None] + land * (1 - water[..., None])
    detail = base - cv2.GaussianBlur(base, (0, 0), 3)
    base = np.clip(base + detail * 0.6, 0, 1).astype(np.float32)

    # Painted clouds: zonal streaks and swirls, banded by latitude.
    cy, cx = np.mgrid[0:dmh // 2, 0:dmw // 2].astype(np.float32)
    u, v = cx / (dmw // 2) * 24.0, cy / (dmh // 2) * 12.0
    wu = fbm(u * 0.5, v * 0.5, 901, 4) - 0.5
    wv = fbm(u * 0.5 + 3, v * 0.5, 907, 4) - 0.5
    swirl = fbm(u * 0.55 + wu * 3.0, v * 1.4 + wv * 2.2, 911, 7)
    clat = (0.5 - cy / (dmh // 2)) * 180.0
    cover = (0.10 + 0.22 * np.exp(-(clat / 9.0) ** 2)
             + 0.26 * np.exp(-((np.abs(clat) - 56.0) / 13.0) ** 2)
             - 0.16 * np.exp(-((np.abs(clat) - 24.0) / 9.0) ** 2))
    clouds = smoothstep(0.56, 0.82, swirl + cover)
    wisps = smoothstep(0.58, 0.88, fbm(u * 1.9 + wu * 4, v * 4.0, 921, 6) + cover * 0.8) * 0.35
    clouds = np.clip(clouds + wisps, 0, 1).astype(np.float32)
    clouds = cv2.resize(clouds, (dmw, dmh), interpolation=cv2.INTER_CUBIC)

    albedo = sample(base)
    lights = sample(night.astype(np.float32))
    cloud = sample(clouds)
    water_v = sample(water.astype(np.float32))

    L = np.array(EARTH_LIGHT, np.float32)
    L /= np.linalg.norm(L)
    ndl = dx * L[0] + dy * L[1] + nz * L[2]
    day_w = smoothstep(-0.06, 0.22, ndl)
    lit = np.clip(ndl, 0, 1)
    sun = np.array([1.0, 0.96, 0.90], np.float32)

    surface = albedo * (1 - cloud[..., None] * 0.92) + np.array([0.92, 0.94, 0.98], np.float32) * cloud[..., None] * 0.92
    colour = surface * (lit ** 0.85)[..., None] * sun * 1.15
    # Twilight: a warm band where day turns to night.
    twilight = np.exp(-((ndl - 0.03) / 0.045) ** 2)
    colour += twilight[..., None] * np.array([0.60, 0.26, 0.12], np.float32) * 0.12 * (0.4 + 0.6 * cloud)[..., None]
    # Sun glint on open water.
    V = np.array([0, 0, 1], np.float32)
    Hh = (L + V) / np.linalg.norm(L + V)
    ndh = np.clip(dx * Hh[0] + dy * Hh[1] + nz * Hh[2], 0, 1)
    glint = ndh ** 90 * water_v * (1 - cloud) * day_w
    colour += glint[..., None] * np.array([1.0, 0.95, 0.85], np.float32) * 1.4
    # City lights on the night side, warm, dimmed under cloud.
    night_w = 1 - smoothstep(-0.12, 0.08, ndl)
    city = np.clip(lights * 1.6 - 0.02, 0, None) * np.array([1.0, 0.72, 0.42], np.float32)
    colour += city * (night_w * (1 - cloud * 0.75))[..., None] * 0.9
    # Atmosphere inside the disc: blue scattering towards the limb, mostly on the day side.
    limb = (1 - nz) ** 2.6
    colour = (colour * (1 - limb[..., None] * 0.35)
              + np.array([0.20, 0.45, 1.0], np.float32) * (limb * (0.03 + 0.55 * smoothstep(-0.25, 0.5, ndl)))[..., None])

    dist = np.sqrt(rr)
    edge = np.clip((1 - dist) * r / 1.2, 0, 1)
    nd_limb = (dx * L[0] + dy * L[1]) / np.maximum(dist, 1e-4)
    side = smoothstep(-0.35, 0.75, nd_limb)
    halo = (np.exp(-np.maximum(dist - 1, 0) / 0.022) * 0.9 + np.exp(-np.maximum(dist - 1, 0) / 0.05) * 0.2) * side
    halo *= 1 - smoothstep(1.06, 1.11, dist)          # gone before the layer's edge
    halo_col = np.array([0.25, 0.55, 1.0], np.float32)
    premult = colour * edge[..., None] + halo_col * (halo * (1 - edge))[..., None]
    rgba = np.dstack([np.clip(premult, 0, 4) / 4.0, edge])   # stored /4 to keep HDR headroom
    EARTH_LAYER.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(EARTH_LAYER), cv2.cvtColor(np.round(rgba * 65535).astype(np.uint16), cv2.COLOR_RGBA2BGRA))
    print(f"wrote {EARTH_LAYER.relative_to(bb.REPO)}")


def composite_earth(out: np.ndarray) -> None:
    raw = cv2.imread(str(EARTH_LAYER), cv2.IMREAD_UNCHANGED)
    rgba = cv2.cvtColor(raw, cv2.COLOR_BGRA2RGBA).astype(np.float32) / 65535.0
    premult, alpha = rgba[..., :3] * 4.0, rgba[..., 3]
    sigma = EARTH_DEFOCUS * SS
    premult = cv2.GaussianBlur(premult, (0, 0), sigma)
    alpha = cv2.GaussianBlur(alpha, (0, 0), sigma)
    # Atmospheric depth: haze it towards the sky's deep blue.
    premult = premult * (1 - EARTH_HAZE) + bb.rgb((6, 14, 34)) * alpha[..., None] * EARTH_HAZE
    size = alpha.shape[0]
    x0 = int(round(EARTH_CENTRE[0] * SS - size / 2))
    y0 = int(round(EARTH_CENTRE[1] * SS - size / 2))
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    w = min(size - sx0, W - dx0)
    h = min(size - sy0, H - dy0)
    a = alpha[sy0:sy0 + h, sx0:sx0 + w, None]
    region = out[dy0:dy0 + h, dx0:dx0 + w]
    region[:] = region * (1 - a) + premult[sy0:sy0 + h, sx0:sx0 + w]


# --- the Sphere ---------------------------------------------------------------

def render_sphere(out: np.ndarray) -> None:
    """Ray-trace the camera's view of the Sphere's hull and shade it over `out`."""
    f = (W / 2) / math.tan(HFOV / 2)
    vfov_half = math.atan((H / 2) / f)
    dip = math.acos(SPHERE_R / (SPHERE_R + CAMERA_HEIGHT))
    pitch = dip - math.atan((HORIZON - 0.5) * 2 * math.tan(vfov_half))   # positive looks down

    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    dxc = (xs + 0.5 - W / 2) / f
    dyc = -(ys + 0.5 - H / 2) / f
    cp, sp = math.cos(pitch), math.sin(pitch)
    dX = dxc
    dY = dyc * cp - sp
    dZ = dyc * sp + cp
    norm = np.sqrt(dX * dX + dY * dY + dZ * dZ)
    dX, dY, dZ = dX / norm, dY / norm, dZ / norm

    oc = SPHERE_R + CAMERA_HEIGHT           # camera above the centre, along +y
    b = dY * oc
    c = oc * oc - SPHERE_R * SPHERE_R
    disc = b * b - c
    hit = (disc > 0) & (b < 0)
    t = np.where(hit, -b - np.sqrt(np.maximum(disc, 0)), 0.0).astype(np.float32)
    px, py, pz = dX * t, dY * t, dZ * t
    Nx, Ny, Nz = px / SPHERE_R, (py + oc) / SPHERE_R, pz / SPHERE_R

    el = -dip + SUN_ABOVE_HORIZON
    sun = np.array([math.sin(SUN_AZIMUTH) * math.cos(el), math.sin(el), math.cos(SUN_AZIMUTH) * math.cos(el)], np.float32)
    sun /= np.linalg.norm(sun)

    # Surface coordinates: latitude and longitude about a tilted axis, so features wrap the globe.
    axis = np.array([0.35, 0.55, 0.76], np.float32)
    axis /= np.linalg.norm(axis)
    ref = np.cross(axis, np.array([1.0, 0.0, 0.0], np.float32))
    ref /= np.linalg.norm(ref)
    ref2 = np.cross(axis, ref)
    s_ax = Nx * axis[0] + Ny * axis[1] + Nz * axis[2]
    lat = np.arcsin(np.clip(s_ax, -1, 1))
    lon = np.arctan2(Nx * ref2[0] + Ny * ref2[1] + Nz * ref2[2], Nx * ref[0] + Ny * ref[1] + Nz * ref[2])
    k = 26.0
    u, v = lon * k * np.cos(lat) + 50.0, lat * k + 50.0
    # How much surface one pixel covers: grows towards the limb, where the globe is foreshortened.
    ndv0 = np.clip(-(Nx * dX + Ny * dY + Nz * dZ), 0.02, 1)
    footprint = t / f * k / SPHERE_R / ndv0
    sharp = np.clip(1.0 - footprint * 5.0, 0, 1)

    # Armoured plates, and trenches between some of them that glow.
    f1, f2, cid = worley(u * 1.0, v * 1.0, 71)
    edge = f2 - f1
    width = 0.025 + footprint * 0.8
    trench = 1 - smoothstep(0.0, width, edge)
    pulse = fbm(u * 0.9, v * 0.9, 75, 3)
    lit_trench = trench * smoothstep(0.55, 0.70, fbm(u * 0.30, v * 0.30, 73, 3)) * (0.25 + 0.75 * smoothstep(0.35, 0.75, pulse))
    # Larger cells: a few ringed orifices.
    g1, _, gid = worley(u * 0.22, v * 0.22, 79)
    ring = np.exp(-((g1 - 0.16) / (0.018 + footprint * 0.2)) ** 2) * smoothstep(0.86, 0.92, gid)
    pit = (1 - smoothstep(0.05, 0.13, g1)) * smoothstep(0.86, 0.92, gid)
    # Living tissue over the plates in broad, warped regions.
    wu = fbm(u * 0.08, v * 0.08, 81, 3) - 0.5
    wv = fbm(u * 0.08 + 9, v * 0.08, 83, 3) - 0.5
    tissue = smoothstep(0.48, 0.66, fbm(u * 0.11 + wu * 3, v * 0.11 + wv * 3, 85, 5))
    veins = (1 - np.abs(fbm(u * 0.6 + wu * 4, v * 0.6 + wv * 4, 87, 4) * 2 - 1)) ** 8 * tissue

    shell = bb.rgb((0x0F, 0x17, 0x1B))
    plate = bb.rgb((0x1C, 0x2C, 0x42))
    flesh = bb.rgb((0x12, 0x24, 0x22))
    albedo = shell + (plate - shell) * ((1 - trench) * (0.4 + 0.6 * cid))[..., None]
    albedo = albedo * (1 - tissue[..., None]) + flesh * tissue[..., None]

    # Light: from behind, so only a crescent along the limb is lit, plus a faint fill.
    ndl = np.clip(Nx * sun[0] + Ny * sun[1] + Nz * sun[2], 0, 1)
    wrap = smoothstep(-0.12, 0.25, Nx * sun[0] + Ny * sun[1] + Nz * sun[2])
    ndv = ndv0
    fresnel = 0.04 + 0.96 * (1 - ndv) ** 5
    Hx, Hy, Hz = sun[0] - dX, sun[1] - dY, sun[2] - dZ
    hl = np.sqrt(Hx * Hx + Hy * Hy + Hz * Hz) + 1e-6
    ndh = np.clip((Nx * Hx + Ny * Hy + Nz * Hz) / hl, 0, 1)
    spec = ndh ** 40 * fresnel * 3.0 * (0.4 + 0.6 * tissue)
    sun_col = np.array([1.0, 0.97, 0.92], np.float32) * 2.0
    colour = albedo * (ndl * 0.8 + wrap * 0.25)[..., None] * sun_col
    colour += albedo * 0.35 * bb.rgb((70, 110, 180))                       # starlight and the nebula's glow
    colour += spec[..., None] * sun_col
    colour += ((1 - ndv) ** 3 * wrap)[..., None] * bb.rgb((90, 150, 255)) * 0.6

    # Emission, strongest on the night side where nothing else lights it.
    night = 1 - 0.6 * wrap
    emit = (lit_trench[..., None] * TEAL * (0.55 + 0.45 * cid)[..., None] * 0.9
            + ring[..., None] * TEAL * 1.4 + pit[..., None] * CORE * 0.5
            + veins[..., None] * BIO * 0.35)
    colour += emit * night[..., None] * (0.35 + 0.65 * sharp)[..., None]

    # A thin haze towards the limb.
    to_sun = np.clip(dX * sun[0] + dY * sun[1] + dZ * sun[2], -1, 1)
    near_sun = np.exp(-np.arccos(to_sun) / 0.12)
    haze = (1 - ndv) ** 4
    colour = colour * (1 - haze[..., None] * 0.6) + bb.rgb((40, 80, 170)) * (haze * (0.3 + 1.5 * near_sun))[..., None]

    cover = cv2.GaussianBlur(hit.astype(np.float32), (0, 0), 0.7)
    out[:] = out * (1 - cover[..., None]) + np.where(hit[..., None], colour, 0) * cover[..., None]

    # Light rising behind the horizon: a thin bright limb, a glow, and the sun's bloom.
    # Height over the hull of the ray's closest approach; rays climbing away from it
    # are closest at the camera.
    closest = np.where(b < 0, np.sqrt(np.maximum(oc * oc - b * b, 0)), oc)
    alt = np.where(hit, 0, np.maximum(closest - SPHERE_R, 0)).astype(np.float32)
    above = ~hit
    limb_line = np.exp(-alt / 0.35) * near_sun ** 0.4 * above
    limb_glow = np.exp(-alt / 2.0) * (0.10 + 0.90 * near_sun) * above
    out += limb_line[..., None] * CORE * 2.2
    out += limb_glow[..., None] * bb.rgb((90, 150, 255)) * 0.7
    burst = np.exp(-np.arccos(to_sun) / 0.030) * above
    out += burst[..., None] * np.array([1.0, 0.98, 0.95], np.float32) * 2.4
    halo = np.exp(-np.arccos(to_sun) / 0.10) * above
    out += halo[..., None] * bb.rgb((50, 95, 200)) * 0.16


# --- Talon, bloom, grade -------------------------------------------------------

def talon_outline():
    """Talon's insignia on the TALON_QUAD plane, out of focus: soft lines and a wide glow."""
    layer = np.asarray(Image.open(bb.INSIGNIA_LAYER).convert("L"), np.float32) / 255.0
    layer = cv2.dilate(layer, np.ones((3, 3), np.uint8))
    lh, lw = layer.shape
    src = np.float32([[0, 0], [lw, 0], [lw, lh], [0, lh]])
    dst = np.float32(TALON_QUAD) * SS
    m = cv2.getPerspectiveTransform(src, dst)
    lines = cv2.warpPerspective(layer, m, (W, H), flags=cv2.INTER_AREA)
    lines = cv2.GaussianBlur(lines, (0, 0), TALON_BLUR * SS)
    lines /= max(float(lines.max()), 1e-6)
    halo = cv2.GaussianBlur(lines, (0, 0), 20.0 * SS)
    halo /= max(float(halo.max()), 1e-6)
    xs = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    ys = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    fade = smoothstep(0.50, 0.80, xs) * (1 - smoothstep(0.70, 0.84, ys))
    return lines * fade, halo * fade


def bloom(out: np.ndarray) -> None:
    lum = out @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    bright = out * smoothstep(1.0, 3.0, lum)[..., None]
    out += cv2.GaussianBlur(bright, (0, 0), 5 * SS) * 0.25
    out += cv2.GaussianBlur(bright, (0, 0), 26 * SS) * 0.12


def tonemap(x: np.ndarray) -> np.ndarray:
    """ACES-like filmic curve, then sRGB."""
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    x = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def grade(out: np.ndarray, rng) -> np.ndarray:
    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    v = np.hypot((xs - WIDTH * 0.5) / (WIDTH * 0.62), (ys - HEIGHT * 0.56) / (HEIGHT * 0.70))
    out *= (1 - 0.34 * smoothstep(0.55, 1.25, v))[..., None]
    grain = rng.normal(0, 0.010, (HEIGHT, WIDTH)).astype(np.float32)
    out += grain[..., None] * (0.6 + 0.4 * (1 - out.mean(axis=2, keepdims=True)))
    return np.clip(out, 0, 1)


def lens_streak(out: np.ndarray, y: float) -> None:
    """A horizontal anamorphic streak through the logo, after the wordmark's."""
    xs = np.linspace(-1, 1, WIDTH, dtype=np.float32)[None, :]
    ys = np.arange(HEIGHT, dtype=np.float32)[:, None]
    core = np.exp(-((ys - y) / 1.2) ** 2) * np.exp(-np.abs(xs - 0.25) / 0.32)
    wide = np.exp(-((ys - y) / 9.0) ** 2) * np.exp(-np.abs(xs - 0.25) / 0.5)
    out += core[..., None] * CORE * 0.26 + wide[..., None] * STREAK * 0.18


# --- type and logo ----------------------------------------------------------------

def load_font(size):
    for path in (FONT,) + FONT_FALLBACKS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_tagline(img: Image.Image) -> None:
    """The tagline between openQ4-style bracket marks, the game's name in teal."""
    scale = 4
    w, h = img.size
    layer = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    font = load_font(33 * scale)
    lead, name = TAGLINE
    tracking = 2.0 * scale
    name_tracking = 4.4 * scale

    def width(text, track):
        return sum(d.textlength(ch, font=font) + track for ch in text) - track

    gap = d.textlength(" ", font=font) * 0.15
    total = width(lead, tracking) + gap + width(name, name_tracking)
    x = (w * scale - total) / 2
    y = TAGLINE_Y * scale
    top = y - font.size * 0.74
    for text, colour, track in ((lead, (226, 238, 252, 255), tracking),
                                (name, (0x1B, 0xDD, 0xEF, 255), name_tracking)):
        for ch in text:
            d.text((x, y), ch, font=font, fill=colour, anchor="ls")
            x += d.textlength(ch, font=font) + track
        x += gap
    pad = 28 * scale
    left = (w * scale - total) / 2 - pad
    right = (w * scale + total) / 2 + pad
    mid = (top + y) / 2 + 2 * scale
    hh = (y - top) * 0.92
    line = int(2.0 * scale)
    teal = (0x1B, 0xDD, 0xEF, 220)
    for sx, sign in ((left, 1), (right, -1)):
        d.line([(sx + sign * 11 * scale, mid - hh), (sx, mid - hh), (sx, mid + hh), (sx + sign * 11 * scale, mid + hh)],
               fill=teal, width=line, joint="curve")
        d.line([(sx - sign * 10 * scale, mid), (sx - sign * 3 * scale, mid)], fill=teal, width=line)
    layer = layer.resize((w, h), Image.LANCZOS)
    shade = layer.getchannel("A").filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.6))
    dark = Image.new("RGBA", (w, h), (0, 3, 10, 0))
    dark.putalpha(shade)
    img.alpha_composite(dark)
    glow = layer.filter(ImageFilter.GaussianBlur(5))
    img.alpha_composite(Image.blend(Image.new("RGBA", (w, h), (0, 0, 0, 0)), glow, 0.4))
    img.alpha_composite(layer)


def place_logo(canvas: Image.Image, logo_rgba: np.ndarray) -> float:
    """Composite the logo, centred; returns the y of its lettering's middle."""
    logo = bb.to_image(logo_rgba)
    alpha = np.asarray(logo)[..., 3]
    ys, xs = np.nonzero(alpha > 8)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    logo = logo.crop(box)
    scale = LOGO_WIDTH / logo.width
    logo = logo.resize((round(logo.width * scale), round(logo.height * scale)), Image.LANCZOS)
    x = round((WIDTH - logo.width) / 2)
    y = round(LOGO_CENTRE_Y - logo.height / 2)
    pad = 90
    a = Image.new("L", (logo.width + 2 * pad, logo.height + 2 * pad), 0)
    a.paste(logo.getchannel("A"), (pad, pad))
    for blur, strength, drop in ((28, 0.55, 10), (6, 0.45, 4)):
        s = a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v, k=strength: int(v * k))
        pool = Image.new("RGBA", a.size, (0, 3, 10, 0))
        pool.putalpha(s)
        canvas.alpha_composite(pool, (x - pad, y - pad + drop))
    canvas.alpha_composite(logo, (x, y))
    middle = bb.GLYPH_ORIGIN[1] + bb.CAP / 2
    return y + (middle - box[1]) * scale


# --- assembly ----------------------------------------------------------------------

def render_background(rng) -> np.ndarray:
    nebula, transmit, band = render_nebula(rng)
    ys = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    out = np.zeros((H, W, 3), np.float32) + bb.rgb((2, 4, 12)) + bb.rgb((4, 10, 26)) * ys
    out += nebula
    out += render_stars(rng, band, transmit)
    lines, halo = talon_outline()
    out += (lines * 0.20)[..., None] * (TEAL * 0.6 + CORE * 0.4)
    out += (halo * 0.07)[..., None] * TEAL
    composite_earth(out)
    render_sphere(out)
    bloom(out)
    return out


def render(logo_rgba: np.ndarray, earth_maps=None) -> Image.Image:
    if earth_maps is not None or not EARTH_LAYER.exists():
        if earth_maps is None:
            raise SystemExit(f"{EARTH_LAYER} is missing; pass --earth-maps DAY NIGHT to build it")
        render_earth_layer(*earth_maps)
    rng = np.random.default_rng(2006)
    hdr = render_background(rng)
    ldr = tonemap(hdr * 0.85).astype(np.float32)
    ldr = cv2.resize(ldr, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    img = Image.fromarray(np.round(np.clip(ldr, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    mid = place_logo(img, logo_rgba)
    out = np.asarray(img.convert("RGB"), np.float32) / 255.0
    lens_streak(out, mid)
    out = grade(out, rng)
    img = Image.fromarray(np.round(out * 255).astype(np.uint8)).convert("RGBA")
    draw_tagline(img)
    return img.convert("RGB")
