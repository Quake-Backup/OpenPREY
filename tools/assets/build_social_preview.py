#!/usr/bin/env python3
"""Render openPR06's social preview, assets/docs/img/social-preview.png.

Called by build_banner.py, which renders the logo first. A 1280x640 view of
space in Prey's palette (docs/dev/prey-ui-visual-design.md): a blue and teal
nebula over a star field, Earth to the upper left, the Sphere's horizon across
the foot with light rising behind it, and the hawk Talon's insignia drawn
faintly across the back, receding from the right edge. The logo stands in front
and the tagline sits under it between bracket marks, as on openQ4's preview.

Everything is procedural apart from the logo and the insignia layer.
"""

from __future__ import annotations


import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import build_banner as bb

WIDTH, HEIGHT = 1280, 640
SS = 2
TAGLINE = ("The modern way to play ", "PREY")
FONT = "C:/Windows/Fonts/GOTHICI.TTF"   # Century Gothic Italic: a plain geometric sans
FONT_FALLBACKS = ("C:/Windows/Fonts/GOTHIC.TTF", "DejaVuSans-Oblique.ttf", "DejaVuSans.ttf")

LOGO_WIDTH = 880.0
LOGO_CENTRE_Y = 250.0
TAGLINE_Y = 452.0

EARTH_CENTRE = (70.0, 62.0)
EARTH_RADIUS = 172.0
SUN = (650.0, 590.0)            # the light rising behind the Sphere's horizon
SPHERE_CENTRE = (640.0, 2830.0)  # the Sphere is vast: only its horizon shows
SPHERE_RADIUS = 2300.0

TEAL = bb.rgb((0x1B, 0xDD, 0xEF))
CORE = bb.rgb((0xAF, 0xFC, 0xFF))


def stars(shape, rng, count, scale):
    """A star field: mostly faint points, a few bright ones with a soft halo."""
    h, w = shape
    field = np.zeros(shape, np.float32)
    ys = rng.integers(0, h, count)
    xs = rng.integers(0, w, count)
    mag = rng.pareto(2.2, count).astype(np.float32) * 0.10 + 0.05
    np.add.at(field, (ys, xs), np.clip(mag, 0.0, 1.6))
    points = cv2.GaussianBlur(field, (0, 0), 0.6 * scale)
    halo = cv2.GaussianBlur(field, (0, 0), 2.5 * scale) * 4.0
    out = points * (1.0 * scale * scale) + halo
    # A few bright stars get four-point spikes.
    bright = np.argsort(mag)[-7:]
    spikes = np.zeros(shape, np.float32)
    for i in bright:
        length = int((6 + 14 * min(mag[i], 1.4)) * scale)
        cv2.line(spikes, (int(xs[i]) - length, int(ys[i])), (int(xs[i]) + length, int(ys[i])), 1.0, 1)
        cv2.line(spikes, (int(xs[i]), int(ys[i]) - length // 2), (int(xs[i]), int(ys[i]) + length // 2), 1.0, 1)
    spikes = cv2.GaussianBlur(spikes, (0, 0), 0.8 * scale) * 0.35
    return out + spikes


def render_space(X, Y, rng):
    shape = X.shape
    # Deep blue, lighter towards the horizon light.
    d_sun = np.hypot(X - SUN[0], (Y - SUN[1]) * 1.6)
    base = bb.rgb((2, 5, 14)) + (bb.rgb((10, 26, 60)) - bb.rgb((2, 5, 14))) * np.exp(-d_sun / 520.0)[..., None]

    gas = bb.fbm(shape, rng, 380 * SS, octaves=5, stretch=(1.6, 1.0))
    fine = bb.fbm(shape, rng, 90 * SS, octaves=4, stretch=(2.0, 1.0))
    dust = bb.fbm(shape, rng, 160 * SS, octaves=4)
    across = np.clip(X / WIDTH, 0.0, 1.0)[..., None]
    tint = bb.rgb((0x5B, 0x2E, 0xA6)) * (1 - across) * 0.55 + bb.rgb((0x1F, 0x4F, 0xB8)) * 0.6 \
        + bb.rgb((0x14, 0x97, 0xB8)) * across * 0.9
    density = np.clip(0.55 + 0.6 * gas + 0.25 * fine, 0.0, 1.0) ** 2.2
    lanes = np.clip(0.5 + 1.4 * dust, 0.0, 1.0)
    out = base + tint * (density * lanes * 0.30)[..., None]
    out += bb.rgb((150, 210, 255)) * (np.clip(fine, 0.0, 1.0) ** 3 * density * 0.10)[..., None]
    out += stars(shape, rng, 2600, SS)[..., None] * bb.rgb((220, 232, 255))
    return out


def warped_fbm(shape, rng, cell, octaves, warp, stretch=(1.0, 1.0)):
    """fbm whose lookup is displaced by two more fbm fields: coastlines and cloud bands."""
    base = bb.fbm(shape, rng, cell, octaves, stretch)
    wx = bb.fbm(shape, rng, cell * 1.3, 3) * warp
    wy = bb.fbm(shape, rng, cell * 1.3, 3) * warp
    h, w = shape
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(base, gx + wx, gy + wy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def render_earth(X, Y, rng, out):
    """Earth, mostly in night, lit on its lower right limb by the same light as the horizon."""
    cx, cy = EARTH_CENTRE
    r = EARTH_RADIUS
    dx, dy = (X - cx) / r, (Y - cy) / r
    rr = dx * dx + dy * dy
    nz = np.sqrt(np.clip(1.0 - rr, 0.0, 1.0))
    light = np.array([0.78, 0.62, -0.08], np.float32)
    light /= np.linalg.norm(light)
    ndl = dx * light[0] + dy * light[1] + nz * light[2]
    lam = np.clip(ndl, 0.0, 1.0)
    term = bb.smoothstep(-0.08, 0.25, ndl)            # soft terminator

    # Surface coordinates, so features bend round the limb.
    u = (np.arctan2(dx, nz) * r * 1.15 + cx) * SS
    v = (np.arcsin(np.clip(dy, -1, 1)) * r * 1.15 + cy) * SS
    shape = X.shape
    land_n = warped_fbm(shape, rng, 85 * SS, 6, 30 * SS)
    cloud_n = warped_fbm(shape, rng, 26 * SS, 6, 18 * SS, stretch=(3.6, 1.0))
    land_n = cv2.remap(land_n, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR)
    cloud_n = cv2.remap(cloud_n, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR)
    land = bb.smoothstep(0.17, 0.20, land_n)
    ocean = bb.rgb((4, 18, 52)) + (bb.rgb((18, 62, 132)) - bb.rgb((4, 16, 44))) * (nz ** 0.6)[..., None]
    ground = bb.rgb((30, 58, 38)) + (bb.rgb((118, 104, 72)) - bb.rgb((30, 44, 34))) \
        * np.clip((land_n - 0.18) * 3.0, 0.0, 1.0)[..., None]
    surface = ocean * (1 - land[..., None]) + ground * land[..., None]
    clouds = (bb.smoothstep(0.26, 0.70, cloud_n) * 0.65)[..., None]
    surface = surface * (1 - clouds) + bb.rgb((0xE8, 0xEA, 0xF0)) * clouds
    lit = surface * (0.015 + 1.1 * (lam ** 0.8) * term)[..., None]
    # Sun glint on the oceans.
    half = light + np.array([0, 0, 1], np.float32)
    half /= np.linalg.norm(half)
    spec = np.clip(dx * half[0] + dy * half[1] + nz * half[2], 0.0, 1.0) ** 60 * (1 - land) * (1 - clouds[..., 0])
    lit += spec[..., None] * bb.rgb((190, 215, 255)) * 0.5
    # City lights on the night side's land.
    lights_n = bb.fbm(shape, rng, 3 * SS, 2)
    lights_n = cv2.remap(lights_n, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR)
    city = bb.smoothstep(0.55, 0.8, lights_n) * land * (1 - term) * (1 - clouds[..., 0]) * nz
    lit += city[..., None] * bb.rgb((255, 176, 92)) * 0.35
    # Atmosphere: a thin blue shell, brightest on the lit limb.
    rim = np.clip(1.0 - nz, 0.0, 1.0) ** 3.0
    lit += (rim * (0.05 + 1.2 * bb.smoothstep(-0.2, 0.6, ndl)))[..., None] * bb.rgb((90, 160, 255))
    edge = np.clip((1.0 - np.sqrt(rr)) * r * SS / 1.5, 0.0, 1.0)   # antialiased disc
    dist = np.sqrt(rr) * r
    side = bb.smoothstep(-0.3, 0.7, (dx * light[0] + dy * light[1]) / np.maximum(np.sqrt(rr), 1e-3))
    halo = np.exp(-np.abs(dist - r) / 7.0) * side
    out[:] = out * (1 - edge[..., None]) + lit * edge[..., None]
    out += (halo * (1 - edge))[..., None] * bb.rgb((80, 150, 255)) * 0.8


def render_sphere(X, Y, rng, out):
    """The Sphere's horizon: a dark organic shell, plated in places, lit along its rim."""
    cx, cy = SPHERE_CENTRE
    r = SPHERE_RADIUS
    dist = np.hypot(X - cx, Y - cy)
    depth = r - dist                     # pixels inside the horizon
    cover = np.clip(depth * SS + 0.5, 0.0, 1.0)
    shape = X.shape

    # Surface coordinates: along the horizon, and into the surface (foreshortened).
    along = np.arctan2(X - cx, cy - Y) * r
    into = np.sqrt(np.clip(depth, 0.0, None)) * 14.0
    su = (along - along.min()) * SS
    sv = into * SS
    ridged = 1.0 - np.abs(warped_fbm(shape, rng, 60 * SS, 5, 14 * SS, stretch=(2.0, 1.0)))
    ridged = cv2.remap(ridged, su.astype(np.float32), sv.astype(np.float32), cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REFLECT)
    plates_n = bb.fbm(shape, rng, 70 * SS, 3, stretch=(2.4, 1.0))
    plates_n = cv2.remap(plates_n, su.astype(np.float32), sv.astype(np.float32), cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REFLECT)
    bio_n = bb.fbm(shape, rng, 90 * SS, 4, stretch=(2.4, 1.0))
    bio_n = cv2.remap(bio_n, su.astype(np.float32), sv.astype(np.float32), cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_REFLECT)

    shell = bb.rgb((0x0F, 0x17, 0x1B)) + (bb.rgb((0x2A, 0x3D, 0x48)) - bb.rgb((0x0F, 0x17, 0x1B))) \
        * (ridged ** 6)[..., None]
    plate = bb.smoothstep(0.30, 0.34, plates_n)
    surf = shell * (1 - plate[..., None] * 0.45) + bb.rgb((0x2D, 0x45, 0x69)) * (plate * 0.45 * (0.4 + 0.6 * ridged))[..., None]
    bio = bb.smoothstep(0.30, 0.55, bio_n) * (1 - plate)
    surf = surf * (1 - bio[..., None] * 0.45) + bb.rgb((0x1F, 0x60, 0x43)) * (bio * 0.45)[..., None]
    # Veins: the ridges of the shell glow faintly teal, greener in the living patches.
    vein = bb.smoothstep(0.90, 0.985, ridged) * (depth > 2)
    vein_col = TEAL * (1 - bio[..., None]) + bb.rgb((0x3C, 0xE0, 0x9A)) * bio[..., None]
    surf += (cv2.GaussianBlur(vein, (0, 0), 0.8 * SS) * 0.42 + cv2.GaussianBlur(vein, (0, 0), 4.0 * SS) * 0.28)[..., None] * vein_col

    # Light from just behind the horizon grazes the surface near the rim.
    d_sun = np.hypot(X - SUN[0], (Y - SUN[1]) * 2.2)
    graze = np.exp(-np.maximum(depth, 0) / 30.0) * np.exp(-d_sun / 560.0)
    surf += graze[..., None] * (bb.rgb((0x4A, 0x6F, 0x84)) * 1.6 + bb.rgb((0xAF, 0xC5, 0xE3)) * 0.5 * (ridged ** 4)[..., None])
    surf *= (0.55 + 0.45 * np.exp(-np.maximum(depth, 0) / 140.0))[..., None]
    # A few teal lights where the plates meet the shell.
    seam = np.exp(-((plates_n - 0.32) / 0.008) ** 2) * bb.smoothstep(0.70, 0.92, ridged) * (depth > 4)
    surf += cv2.GaussianBlur(seam, (0, 0), 1.2 * SS)[..., None] * TEAL * 1.6

    out[:] = out * (1 - cover[..., None]) + surf * cover[..., None]
    # The rim line and the light rising behind it.
    rim = np.exp(-((depth - 0.8) / 1.4) ** 2) * np.exp(-d_sun / 760.0)
    out += rim[..., None] * CORE * 1.5
    above = np.clip(-depth, 0.0, None)
    haze = np.exp(-above / 34.0) * np.exp(-d_sun / 460.0) * (depth < 0)
    out += haze[..., None] * bb.rgb((110, 170, 255)) * 0.8
    burst = np.exp(-np.hypot(X - SUN[0], (Y - SUN[1] + 46) * 2.8) / 80.0)
    out += burst[..., None] * bb.rgb((235, 248, 255)) * 1.0
    flare = np.exp(-np.abs(Y - (SUN[1] - 46)) / 1.8) * np.exp(-np.abs(X - SUN[0]) / 380.0)
    out += flare[..., None] * bb.rgb((0x33, 0x80, 0xB1)) * 1.3


def render_insignia_outline(shape, out):
    """Talon's outline, faint, across the back: big at the right edge, receding to the left."""
    # Place the insignia flat, then tilt it: a homography that shrinks its left
    # side, so it reads as a plane turned away from the viewer.
    src = np.float32([[0, 0], [1, 0], [1, 1], [0, 1]])
    dst = np.float32([[600, 150], [1400, -110], [1400, 760], [600, 500]])
    place = cv2.getPerspectiveTransform(src, dst).astype(np.float64)
    # insignia_lines centres the layer at `centre` with `height`; undo that to map the unit square.
    core, halo = bb_insignia_unit(shape, place)
    glow = core * 0.16 + halo * 0.10
    out += glow[..., None] * (TEAL * 0.7 + CORE * 0.3)


def bb_insignia_unit(shape, unit_to_canvas):
    layer = np.asarray(Image.open(bb.INSIGNIA_LAYER).convert("L"), np.float32) / 255.0
    lh, lw = layer.shape
    to_unit = np.array([[1.0 / lw, 0, 0], [0, 1.0 / lh, 0], [0, 0, 1]])
    s = np.diag([SS, SS, 1.0])
    m = s @ unit_to_canvas @ to_unit
    # Thicken the thin source lines as they are magnified, so they stay lines.
    layer = cv2.dilate(layer, np.ones((3, 3), np.uint8))
    core = cv2.warpPerspective(layer, m, (shape[1], shape[0]), flags=cv2.INTER_LINEAR)
    halo = cv2.GaussianBlur(core, (0, 0), 7.0 * SS)
    halo /= max(float(halo.max()), 1e-6)
    return np.clip(core, 0, 1), halo


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
    font = load_font(34 * scale)
    lead, name = TAGLINE
    tracking = 2.2 * scale

    def width(text):
        return sum(d.textlength(ch, font=font) + tracking for ch in text) - tracking

    gap = d.textlength(" ", font=font) * 0.2
    total = width(lead) + gap + width(name) * 1.08
    x = (w * scale - total) / 2
    y = TAGLINE_Y * scale
    top = y - font.size * 0.80
    for text, colour, extra in ((lead, (232, 242, 255, 255), 0.0), (name, (0x1B, 0xDD, 0xEF, 255), 2.2 * scale)):
        for ch in text:
            d.text((x, y), ch, font=font, fill=colour, anchor="ls")
            x += d.textlength(ch, font=font) + tracking + extra
        x += gap
    # Bracket marks: an open corner with a short tick, as openQ4's preview draws them.
    pad = 30 * scale
    left = (w * scale - total) / 2 - pad
    right = (w * scale + total) / 2 + pad
    mid = (top + y) / 2
    hh = (y - top) * 0.95
    line = int(2.2 * scale)
    teal = (0x1B, 0xDD, 0xEF, 230)
    for sx, sign in ((left, 1), (right, -1)):
        d.line([(sx + sign * 12 * scale, mid - hh), (sx, mid - hh), (sx, mid + hh), (sx + sign * 12 * scale, mid + hh)],
               fill=teal, width=line, joint="curve")
        d.line([(sx - sign * 9 * scale, mid), (sx - sign * 3 * scale, mid)], fill=teal, width=line)
    layer = layer.resize((w, h), Image.LANCZOS)
    glow = layer.filter(__import__("PIL.ImageFilter", fromlist=["GaussianBlur"]).GaussianBlur(6))
    img.alpha_composite(Image.blend(Image.new("RGBA", (w, h), (0, 0, 0, 0)), glow, 0.6))
    img.alpha_composite(layer)


def place_logo(canvas: Image.Image, logo_rgba: np.ndarray) -> None:
    logo = bb.to_image(logo_rgba)
    alpha = np.asarray(logo)[..., 3]
    ys, xs = np.nonzero(alpha > 8)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    logo = logo.crop(box)
    scale = LOGO_WIDTH / logo.width
    logo = logo.resize((round(logo.width * scale), round(logo.height * scale)), Image.LANCZOS)
    x = round((WIDTH - logo.width) / 2)
    y = round(LOGO_CENTRE_Y - logo.height / 2)
    # A soft dark pool under the logo keeps it clear of the nebula.
    shadow = Image.new("L", logo.size, 0)
    shadow.paste(logo.getchannel("A"))
    from PIL import ImageFilter  # noqa: PLC0415
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    pool = Image.new("RGBA", logo.size, (0, 4, 10, 0))
    pool.putalpha(shadow.point(lambda v: int(v * 0.55)))
    canvas.alpha_composite(pool, (x, y + 6))
    canvas.alpha_composite(logo, (x, y))


def render(logo_rgba: np.ndarray) -> Image.Image:
    rng = np.random.default_rng(1006)
    h, w = HEIGHT * SS, WIDTH * SS
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    X = (xs + 0.5) / SS
    Y = (ys + 0.5) / SS
    del xs, ys

    out = render_space(X, Y, rng)
    render_insignia_outline(X.shape, out)
    render_earth(X, Y, rng, out)
    render_sphere(X, Y, rng, out)
    # Gentle filmic roll-off so the bright horizon does not clip hard.
    out = 1.0 - np.exp(-np.clip(out, 0.0, None) * 1.15)
    out = cv2.resize(out, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    img = Image.fromarray(np.round(np.clip(out, 0, 1) ** (1 / 1.0) * 255).astype(np.uint8)).convert("RGBA")
    place_logo(img, logo_rgba)
    draw_tagline(img)
    return img.convert("RGB")
