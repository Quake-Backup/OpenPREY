#!/usr/bin/env python3
# Copyright (C) 2026 DarkMatter Productions. GPL-3.0-or-later.
"""The campaign tips' controller plates, drawn as Prey draws its keys.

    python tools/ui/pad_tip_plates.py            write the plates and their materials
    python tools/ui/pad_tip_plates.py --check    exit 1 if any plate or the material file is stale
    python tools/ui/pad_tip_plates.py --preview out.png
                                                 a contact sheet of every plate, for review

Prey's tutorial tips (guis/hud/hud_tips.guifragment, `TipKey`) show the
key that does something as a large plate: `textures/interface/tips/key` (a
keycap), `keywide`, or a mouse with the button lit (`mouse1`..`mousedn`),
with the key's name written over the keycap by the GUI. A controller's
buttons get plates in the same hand: the keycap's thick pale steel edge
(`#BACFEB`), dark extruded sides that lighten toward the right, a
translucent steel top face with a darker rim, the whole plate at the
keycap's 87.5% opacity, and the mouse's orange for a lit part. The plates
share the keycap's 256x128 frame and its placement, so the GUI's key text
lands on a plate's top face exactly where it lands on a key's.

`idCommonLocal::MaterialKeyForBinding` (src/framework/Common.cpp) picks the
plate for a controller button from the glyph kind the retained prompts use
(`RetainedUI_KeyGlyph`): a face button's letter, bumper, trigger, stick,
paddle and other labelled buttons are plates the GUI writes the label on;
the PlayStation symbols, the face buttons by position, the d-pad's arms,
menu, view, home and touchpad carry their mark.

Every plate is drawn at SS times its size and box-filtered down; nothing
is random, so --check compares exactly.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXTURES = ROOT / "content" / "basepr" / "pak1" / "textures" / "interface" / "tips"
MATERIALS = ROOT / "content" / "basepr" / "pak0" / "materials" / "openpr06_padtips.mtr"

SIZE = (256, 128)          # the keycap's texture
SS = 4                     # supersampling
OPACITY = 223 / 255        # the keycap's alpha

EDGE = (186, 207, 235)     # the keycap's pale steel edge
SIDE_DARK = (65, 72, 83)   # its extruded sides
SIDE_LIGHT = (122, 135, 155)
RIM = (78, 87, 101)        # the darker rim inside the top face's edge
TOP = (107, 118, 135)      # the top face
TOP_GLOW = (150, 164, 184)
LIT = (255, 125, 0)        # the mouse's lit button
LIT_DEEP = (214, 64, 0)
INK = (255, 255, 255)      # the marks, white over a dark drop shadow as retail's arrows
INK_SHADOW = (0, 0, 0)

EDGE_W = 4.5               # texels: the outline
RIM_W = 3.0
CENTRE = (191.0, 45.0)     # where the GUI writes a key's name: the top face's centre
SHEAR = -0.1               # the marks lean as retail's overlay stages do (shear -0.1, 0)


# ------------------------------------------------------------------ shapes
# A shape is a function of an inset (texels) returning a closed polygon.

def ellipse(cx: float, cy: float, rx: float, ry: float, n: int = 96):
    def make(inset: float = 0.0):
        a, b = max(0.5, rx - inset), max(0.5, ry - inset)
        return [(cx + a * math.cos(2 * math.pi * i / n), cy + b * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return make


def rounded(x0: float, y0: float, x1: float, y1: float, r: float, r_bottom: float | None = None, n: int = 12):
    """A rounded rectangle; `r_bottom` gives the bottom corners their own radius."""
    rb = r if r_bottom is None else r_bottom

    def make(inset: float = 0.0):
        ax0, ay0, ax1, ay1 = x0 + inset, y0 + inset, x1 - inset, y1 - inset
        rt, rbb = max(0.0, r - inset), max(0.0, rb - inset)
        pts = []
        for (cx, cy, rad, start) in ((ax1 - rt, ay0 + rt, rt, -90), (ax1 - rbb, ay1 - rbb, rbb, 0),
                                     (ax0 + rbb, ay1 - rbb, rbb, 90), (ax0 + rt, ay0 + rt, rt, 180)):
            for i in range(n + 1):
                t = math.radians(start + 90 * i / n)
                pts.append((cx + rad * math.cos(t), cy + rad * math.sin(t)))
        return pts
    return make


def cross(cx: float, cy: float, half: float, arm: float, r: float = 5.0):
    """A d-pad's plus sign: arms `half` long from the centre, `arm` wide."""
    def make(inset: float = 0.0):
        h, a = half - inset, arm / 2 - inset
        rr = max(0.0, r - inset)
        corners = [(a, -h), (a, -a), (h, -a), (h, a), (a, a), (a, h), (-a, h), (-a, a), (-h, a), (-h, -a), (-a, -a), (-a, -h)]
        # Round only the eight outer corners.
        outer = {0, 2, 3, 5, 6, 8, 9, 11}
        pts = []
        for i, (x, y) in enumerate(corners):
            if i in outer and rr > 0:
                # Unit steps toward the neighbouring corners; the arc's centre
                # sits rr along both, and the arc runs between the two tangents.
                px, py = corners[i - 1]
                nx, ny = corners[(i + 1) % len(corners)]
                d1 = (math.copysign(1, px - x) if px != x else 0, math.copysign(1, py - y) if py != y else 0)
                d2 = (math.copysign(1, nx - x) if nx != x else 0, math.copysign(1, ny - y) if ny != y else 0)
                c = (x + (d1[0] + d2[0]) * rr, y + (d1[1] + d2[1]) * rr)
                a0 = math.atan2(y + d1[1] * rr - c[1], x + d1[0] * rr - c[0])
                a1 = math.atan2(y + d2[1] * rr - c[1], x + d2[0] * rr - c[0])
                da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
                for k in range(9):
                    t = a0 + da * k / 8
                    pts.append((cx + c[0] + rr * math.cos(t), cy + c[1] + rr * math.sin(t)))
            else:
                pts.append((cx + x, cy + y))
        return pts
    return make


def transformed(shape, dx: float, dy: float, scale: float = 1.0, about=CENTRE):
    def make(inset: float = 0.0):
        return [(about[0] + (x - about[0]) * scale + dx, about[1] + (y - about[1]) * scale + dy) for x, y in shape(inset)]
    return make


# ------------------------------------------------------------------ canvas

class Canvas:
    def __init__(self):
        import numpy as np
        self.np = np
        self.w, self.h = SIZE[0] * SS, SIZE[1] * SS
        self.rgb = np.zeros((self.h, self.w, 3))
        self.a = np.zeros((self.h, self.w))
        ys, xs = np.mgrid[0:self.h, 0:self.w]
        self.x = (xs + 0.5) / SS
        self.y = (ys + 0.5) / SS

    def mask(self, polys, width: float = 0.0, fill: bool = True):
        """A coverage mask of polygons (texel coordinates), optionally with an outline `width` wide."""
        from PIL import Image, ImageDraw
        layer = Image.new("L", (self.w, self.h), 0)
        draw = ImageDraw.Draw(layer)
        for poly in polys:
            pts = [(x * SS, y * SS) for x, y in poly]
            if fill:
                draw.polygon(pts, fill=255)
            if width > 0:
                draw.line(pts + [pts[0]], fill=255, width=max(1, round(width * SS)), joint="curve")
                r = width * SS / 2
                for x, y in pts:
                    draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
        return self.np.asarray(layer, dtype=float) / 255.0

    def lines(self, segments, width: float):
        from PIL import Image, ImageDraw
        layer = Image.new("L", (self.w, self.h), 0)
        draw = ImageDraw.Draw(layer)
        r = width * SS / 2
        for (x0, y0), (x1, y1) in segments:
            draw.line([(x0 * SS, y0 * SS), (x1 * SS, y1 * SS)], fill=255, width=max(1, round(width * SS)))
            for x, y in ((x0, y0), (x1, y1)):
                draw.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), fill=255)
        return self.np.asarray(layer, dtype=float) / 255.0

    def paint(self, mask, colour):
        """Paints `colour` (an RGB tuple, or an HxWx3 array) over the canvas through `mask`."""
        np = self.np
        c = np.asarray(colour, dtype=float) / 255.0
        m = mask[..., None]
        self.rgb = c * m + self.rgb * (1 - m)
        self.a = mask + self.a * (1 - mask)

    def gradient_x(self, x0: float, x1: float, c0, c1):
        t = self.np.clip((self.x - x0) / max(1e-6, x1 - x0), 0, 1)[..., None]
        return self.np.asarray(c0, float) * (1 - t) + self.np.asarray(c1, float) * t

    def radial(self, cx: float, cy: float, rx: float, ry: float, inner, outer):
        d = self.np.sqrt(((self.x - cx) / rx) ** 2 + ((self.y - cy) / ry) ** 2)
        t = self.np.clip(d, 0, 1)[..., None] ** 1.6
        return self.np.asarray(inner, float) * (1 - t) + self.np.asarray(outer, float) * t

    def image(self):
        from PIL import Image
        np = self.np
        a = self.a.reshape(SIZE[1], SS, SIZE[0], SS).mean(axis=(1, 3))
        pre = (self.rgb * self.a[..., None]).reshape(SIZE[1], SS, SIZE[0], SS, 3).mean(axis=(1, 3))
        straight = np.where(a[..., None] > 1e-6, pre / np.maximum(a, 1e-6)[..., None], 0)
        # Transparent texels take their neighbours' colour, so filtering never darkens an edge.
        known = a > 1e-6
        for _ in range(6):
            total = np.zeros_like(straight)
            count = np.zeros(a.shape)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                shifted = np.roll(known, (dy, dx), axis=(0, 1))
                total += np.roll(straight, (dy, dx), axis=(0, 1)) * shifted[..., None]
                count += shifted
            grow = ~known & (count > 0)
            straight[grow] = total[grow] / count[grow][:, None]
            known = known | grow
        rgba = np.dstack([np.clip(straight, 0, 1), a * OPACITY])
        return Image.fromarray(np.round(rgba * 255).astype("uint8"))


# ------------------------------------------------------------------ parts

def cap(cv: Canvas, top, base, creases=(), lit_top: bool = False, steps: int = 28):
    """An extruded cap: the sweep from `base` up to `top` in the sides'
    dark steel under a pale edge, crease lines from the top's corners
    `creases` (indices into both polygons) down to the base's, then the top
    face: its edge, a darker rim and the face, lit orange when `lit_top`."""
    sweep = [[(bx + (tx - bx) * k / steps, by + (ty - by) * k / steps) for (tx, ty), (bx, by) in zip(top(0), base(0))]
             for k in range(steps + 1)]
    cv.paint(cv.mask(sweep, width=EDGE_W * 2), EDGE)
    xs = [x for poly in sweep for x, _ in poly]
    cv.paint(cv.mask(sweep), cv.gradient_x(min(xs) + (max(xs) - min(xs)) * 0.55, max(xs), SIDE_DARK, SIDE_LIGHT))
    if creases:
        t, b = top(0), base(0)
        cv.paint(cv.lines([(t[i], b[i]) for i in creases], EDGE_W * 0.8), EDGE)
    face(cv, top, lit=lit_top)


def face(cv: Canvas, top, lit: bool = False):
    poly = top(0)
    cx = sum(x for x, _ in poly) / len(poly)
    cy = sum(y for _, y in poly) / len(poly)
    rx = (max(x for x, _ in poly) - min(x for x, _ in poly)) / 2
    ry = (max(y for _, y in poly) - min(y for _, y in poly)) / 2
    cv.paint(cv.mask([top(-EDGE_W / 2)]), EDGE)
    cv.paint(cv.mask([top(EDGE_W / 2)]), LIT_DEEP if lit else RIM)
    inner = top(EDGE_W / 2 + RIM_W)
    glow = cv.radial(cx + rx * 0.1, cy - ry * 0.15, rx, ry, LIT if lit else TOP_GLOW, LIT_DEEP if lit else TOP)
    cv.paint(cv.mask([inner]), glow)


def lean(points, about=CENTRE):
    """Leans a mark as retail's overlay stages do."""
    return [(x + (y - about[1]) * SHEAR, y) for x, y in points]


def ink(cv: Canvas, polys=(), segments=(), width: float = 4.0, fill: bool = True, colour=INK):
    """White marks over a dark drop shadow, leaning with the plate."""
    polys = [lean(p) for p in polys]
    segments = [tuple(lean(list(s))) for s in segments]
    for offset, tint in (((2.0, 2.0), INK_SHADOW), ((0.0, 0.0), colour)):
        moved_p = [[(x + offset[0], y + offset[1]) for x, y in p] for p in polys]
        moved_s = [((a[0] + offset[0], a[1] + offset[1]), (b[0] + offset[0], b[1] + offset[1])) for a, b in segments]
        m = cv.np.zeros((cv.h, cv.w))
        if moved_p:
            m = cv.np.maximum(m, cv.mask(moved_p, width=0 if fill else width, fill=fill))
        if moved_s:
            m = cv.np.maximum(m, cv.lines(moved_s, width))
        cv.paint(m * (0.75 if tint == INK_SHADOW else 1.0), tint)


def circle_pts(cx, cy, r, n=64):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# ------------------------------------------------------------------ plates

BUTTON_TOP = ellipse(CENTRE[0], CENTRE[1], 40, 31)
BUTTON_BASE = transformed(BUTTON_TOP, -18, 32, 1.12)


def plate_button(mark=None):
    def draw(cv):
        cap(cv, BUTTON_TOP, BUTTON_BASE)
        if mark:
            mark(cv)
    return draw


def mark_cross(cv):
    cx, cy, r = CENTRE[0], CENTRE[1], 13
    ink(cv, segments=[((cx - r, cy - r), (cx + r, cy + r)), ((cx - r, cy + r), (cx + r, cy - r))], width=5)


def mark_circle(cv):
    ink(cv, polys=[circle_pts(CENTRE[0], CENTRE[1], 14)], fill=False, width=4.5)


def mark_square(cv):
    cx, cy, r = CENTRE[0], CENTRE[1], 13
    ink(cv, polys=[[(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]], fill=False, width=4.5)


def mark_triangle(cv):
    cx, cy, r = CENTRE[0], CENTRE[1] + 2, 16
    ink(cv, polys=[[(cx, cy - r), (cx + r * 0.95, cy + r * 0.62), (cx - r * 0.95, cy + r * 0.62)]], fill=False, width=4.5)


FACE_POSITIONS = {"north": (0.0, -27.0), "west": (-36.0, 0.0), "east": (36.0, 0.0), "south": (0.0, 27.0)}


def plate_position(lit: str):
    """The four face buttons as a diamond of small caps, `lit` the button that does it."""
    def draw(cv):
        cx, cy = CENTRE[0] - 4, CENTRE[1] + 4
        for name in ("north", "west", "east", "south"):       # back to front
            dx, dy = FACE_POSITIONS[name]
            top = ellipse(cx + dx, cy + dy, 16, 12.5, n=64)
            base = transformed(top, -7, 13, 1.06, about=(cx + dx, cy + dy))
            cap(cv, top, base, lit_top=name == lit)
    return draw


def plate_bumper(cv):
    top = rounded(138, 27, 246, 63, 16)
    cap(cv, top, transformed(top, -16, 30, 1.04), creases=(26, 39))


def plate_trigger(cv):
    top = rounded(153, 6, 229, 80, 30, r_bottom=9)
    cap(cv, top, transformed(top, -18, 32, 1.08), creases=(26, 39))


def plate_paddle(cv):
    top = rounded(168, 4, 214, 86, 14)
    cap(cv, top, transformed(top, -14, 26, 1.04), creases=(26, 39))


def plate_stick(cv):
    # The well the stick stands in, then its short stem and the cap.
    well = ellipse(CENTRE[0] - 12, CENTRE[1] + 30, 58, 32)
    cv.paint(cv.mask([well(-EDGE_W / 2)]), EDGE)
    cv.paint(cv.mask([well(EDGE_W / 2)]), cv.gradient_x(140, 250, SIDE_DARK, SIDE_LIGHT))
    top = ellipse(CENTRE[0], CENTRE[1], 38, 29)
    cap(cv, top, transformed(top, -10, 22, 0.8))
    # The grip ring round the dished top.
    ring = ellipse(CENTRE[0], CENTRE[1], 30, 22)
    cv.paint(cv.mask([ring(0)], width=2.5, fill=False), RIM)


def plate_dpad(lit: str):
    def draw(cv):
        top = cross(CENTRE[0], CENTRE[1], 44, 30)
        cap(cv, top, transformed(top, -14, 28, 1.02))
        cx, cy = CENTRE
        half, arm = 44 - EDGE_W / 2 - RIM_W, 15 - EDGE_W / 2 - RIM_W
        near = 17.0
        arms = {"up": [(cx - arm, cy - half), (cx + arm, cy - half), (cx + arm, cy - near), (cx - arm, cy - near)],
                "down": [(cx - arm, cy + near), (cx + arm, cy + near), (cx + arm, cy + half), (cx - arm, cy + half)],
                "left": [(cx - half, cy - arm), (cx - near, cy - arm), (cx - near, cy + arm), (cx - half, cy + arm)],
                "right": [(cx + near, cy - arm), (cx + half, cy - arm), (cx + half, cy + arm), (cx + near, cy + arm)]}
        poly = arms[lit]
        xs, ys = [x for x, _ in poly], [y for _, y in poly]
        lx, ly = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        cv.paint(cv.mask([poly]), cv.radial(lx, ly, (max(xs) - min(xs)) / 1.4 + 1, (max(ys) - min(ys)) / 1.4 + 1, LIT, LIT_DEEP))
        # A small arrow on every arm, pointing out.
        for name, (ax, ay, ux, uy) in {"up": (cx, cy - 31, 0, -1), "down": (cx, cy + 31, 0, 1),
                                       "left": (cx - 31, cy, -1, 0), "right": (cx + 31, cy, 1, 0)}.items():
            s = 7.0
            tri = [(ax + ux * s, ay + uy * s), (ax - ux * s * 0.6 - uy * s, ay - uy * s * 0.6 + ux * s),
                   (ax - ux * s * 0.6 + uy * s, ay - uy * s * 0.6 - ux * s)]
            cv.paint(cv.mask([tri]), INK if name == lit else RIM)
    return draw


PILL_TOP = rounded(147, 21, 235, 69, 20)


def plate_pill(mark):
    def draw(cv):
        cap(cv, PILL_TOP, transformed(PILL_TOP, -16, 30, 1.06), creases=(26, 39))
        mark(cv)
    return draw


def mark_menu(cv):
    cx, cy = CENTRE
    ink(cv, segments=[((cx - 16, cy + dy), (cx + 16, cy + dy)) for dy in (-10, 0, 10)], width=4.5)


def mark_view(cv):
    cx, cy = CENTRE
    back = [(cx - 15, cy - 13), (cx + 7, cy - 13), (cx + 7, cy + 5), (cx - 15, cy + 5)]
    ink(cv, polys=[back], fill=False, width=3.5)
    front = [(cx - 7, cy - 5), (cx + 15, cy - 5), (cx + 15, cy + 13), (cx - 7, cy + 13)]
    ink(cv, polys=[front])


def mark_home(cv):
    cx, cy = CENTRE
    ink(cv, polys=[circle_pts(cx, cy, 15)], fill=False, width=4.5)
    ink(cv, polys=[circle_pts(cx, cy, 6)])


def plate_touchpad(cv):
    top = rounded(132, 16, 250, 74, 10)
    cap(cv, top, transformed(top, -14, 28, 1.03), creases=(26, 39))
    cx, cy = CENTRE[0], CENTRE[1]
    ink(cv, polys=[circle_pts(cx, cy, 11)], fill=False, width=4)
    ink(cv, polys=[circle_pts(cx, cy, 4)])


PLATES = {
    "pad_button": plate_button(),
    "pad_cross": plate_button(mark_cross),
    "pad_circle": plate_button(mark_circle),
    "pad_square": plate_button(mark_square),
    "pad_triangle": plate_button(mark_triangle),
    "pad_south": plate_position("south"),
    "pad_east": plate_position("east"),
    "pad_west": plate_position("west"),
    "pad_north": plate_position("north"),
    "pad_bumper": plate_bumper,
    "pad_trigger": plate_trigger,
    "pad_dpadup": plate_dpad("up"),
    "pad_dpaddown": plate_dpad("down"),
    "pad_dpadleft": plate_dpad("left"),
    "pad_dpadright": plate_dpad("right"),
    "pad_stick": plate_stick,
    "pad_menu": plate_pill(mark_menu),
    "pad_view": plate_pill(mark_view),
    "pad_home": plate_button(mark_home),
    "pad_touchpad": plate_touchpad,
    "pad_paddle": plate_paddle,
}


def textures() -> dict[str, object]:
    result = {}
    for name, draw in PLATES.items():
        cv = Canvas()
        draw(cv)
        result[f"{name}.tga"] = cv.image()
    return result


def material_text() -> str:
    lines = [
        "// The campaign tips' controller plates (guis/hud/hud_tips.guifragment's TipKey),",
        "// written by tools/ui/pad_tip_plates.py; idCommonLocal::MaterialKeyForBinding picks one.",
        "// Shaped as Prey's own textures/interface/tips/key.",
        "",
    ]
    for name in PLATES:
        lines += [
            f"textures/interface/tips/{name} {{",
            "\tnoshadows",
            "\tsort gui",
            "\t{",
            "\t\tblend blend",
            f"\t\tmap textures/interface/tips/{name}.tga",
            "\t\tlinear",
            "\t\tcolored",
            "\t}",
            "}",
            "",
        ]
    return "\n".join(lines)


def preview(path: Path, plates: dict) -> None:
    """A contact sheet on the HUD's dark ground, retail's keycap first when it can be found."""
    from PIL import Image, ImageDraw
    cols = 4
    items = list(plates.items())
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * SIZE[0], rows * (SIZE[1] + 14)), (18, 24, 22, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (name, image) in enumerate(items):
        x, y = (i % cols) * SIZE[0], (i // cols) * (SIZE[1] + 14)
        sheet.alpha_composite(image, (x, y))
        draw.text((x + 4, y + SIZE[1]), name, fill=(200, 210, 220, 255))
    sheet.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if any plate or the material file is stale")
    parser.add_argument("--preview", type=Path, help="write a contact sheet of the plates to this PNG and nothing else")
    args = parser.parse_args()
    from PIL import Image, ImageChops
    plates = textures()
    if args.preview:
        preview(args.preview, plates)
        return 0
    stale = 0
    for name, image in plates.items():
        path = TEXTURES / name
        if args.check:
            if not path.exists():
                print(f"missing: {path.relative_to(ROOT).as_posix()}")
                stale += 1
                continue
            with Image.open(path) as current:
                current = current.convert("RGBA")
                if current.size != image.size or ImageChops.difference(current, image).getbbox():
                    print(f"stale: {path.relative_to(ROOT).as_posix()}")
                    stale += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
        print(f"wrote {path.relative_to(ROOT).as_posix()}")
    text = material_text()
    if args.check:
        if not MATERIALS.exists() or MATERIALS.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
            print(f"stale: {MATERIALS.relative_to(ROOT).as_posix()}")
            stale += 1
    else:
        MATERIALS.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {MATERIALS.relative_to(ROOT).as_posix()}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
