"""How the 3D scene LOOKS: the classic look, or the modern one (bugs/0966).

The classic look is the Tk app's since bugs/0020: bright cyan glass under two dark-teal outline
passes, opaque saturated rays, a white sheet behind them. The user, in the Qt shell: "the rays, the
glass, the optical elements can have a nicer look? Apart from the STEP element, the rest look like
old TK. Perhaps reference to Optiland, very nice display."

The modern look takes its recipe from Optiland's 3D viewer (`optiland/visualization`, MIT, (c) 2024
Kramer Harrison): a soft vertical gradient behind the scene, pale glass with a strong narrow
highlight, mirror-bright mirrors, thin rays in mid-tone colours. One thing is this program's own:
it draws hundreds of rays per field where Optiland draws a handful, so a ray's opacity falls with
the number drawn -- a bundle then reads as a beam of light rather than a painted fan.

DISPLAY ONLY. A look changes the colour, opacity, line width and shading of what the scene refresh
already draws. It adds and removes no actor and moves no point, so picking, the row bookkeeping
and "Alt picks the nearest DRAWN edge" (bugs/0323) are the same in both looks. It restyles the
TABLE's elements and the traced rays; imported STEP hardware has its own switch (bugs/0958).

One imported body is the look's business all the same (bugs/0974): the UN-PROMOTED part of an
"optical" import -- the fixture the prisms are promoted out of. In the classic palette it is a
saturated teal. The user: "You can make it modern look for the unpromoted STEP, but the color
should be well contrast to all the promoted prism within it."

Nothing here is toolkit or VTK code except `apply_backdrop` and `apply_material`, which take the
renderer / property they are handed.
"""
from __future__ import annotations

import colorsys
import math
from typing import Any, NamedTuple, Optional

# ---- the classic palette: what the scene refresh asks for ---------------------------------------
#: an analytic glass element (`Kraken3DInspector._surface_color`), a mirror, a file-backed solid
CLASSIC_GLASS_COLOR = (12 / 256.0, 238 / 256.0, 246 / 256.0)
CLASSIC_MIRROR_COLOR = (189 / 256.0, 189 / 256.0, 189 / 256.0)
CLASSIC_STEP_BODY_COLOR = (0.10, 0.62, 0.72)
#: the glass edge palette (bugs/0020): the deep silhouette pass and the brighter line on top
CLASSIC_EDGE_COLOR = (0.026, 0.512, 0.528)
CLASSIC_SILHOUETTE_COLOR = (0.014, 0.279, 0.288)
#: the dark ring round an element that is not glass (a mirror, a stop, the object and image
#: planes), and the heavier copy laid over it while rays are shown
CLASSIC_OUTLINE_COLOR = (0.15, 0.15, 0.15)
CLASSIC_OUTLINE_OVERLAY_COLOR = (0.02, 0.03, 0.05)
CLASSIC_BACKGROUND = (1.0, 1.0, 1.0)

# ---- the modern palette ---------------------------------------------------------------------------
#: glass: Optiland's lens colour is (0.9, 0.9, 1.0) on a darker backdrop; a shade bluer here so it
#: holds against this scene's lighter one
MODERN_GLASS_COLOR = (0.66, 0.83, 0.98)
MODERN_GLASS_OPACITY = (0.26, 0.40)          # a glass body is kept inside this range
MODERN_MIRROR_COLOR = (0.90, 0.92, 0.95)
#: one quiet outline instead of two heavy ones
MODERN_EDGE_COLOR = (0.34, 0.44, 0.56)
MODERN_EDGE_WIDTH = 1.2
MODERN_EDGE_OPACITY = 0.90
#: the ring round a mirror or a stop: darker than a glass edge (it marks an opaque thing), not black
MODERN_OUTLINE_COLOR = (0.20, 0.25, 0.32)
#: the backdrop, bottom then top
MODERN_BACKGROUND = ((0.96, 0.97, 0.99), (0.73, 0.80, 0.89))
#: (ambient, diffuse, specular, specular power)
GLASS_MATERIAL = (0.62, 0.28, 1.0, 50.0)
MIRROR_MATERIAL = (0.62, 0.30, 1.0, 100.0)
#: the UN-PROMOTED part of an "optical" STEP import -- the body the prisms are promoted out of
#: (bugs/0974): a smoked bronze. Chosen by measurement on om05a_folded -- how much drawing the
#: promoted prisms changes the pixels where they lie WITHIN this body, as a CIE76 colour
#: difference, over fourteen candidates at the same opacity: the pale glass colour itself 2.6 (the
#: prisms vanish), the classic teal 7.1, a neutral warm grey 7.8, the hardware's slate 10.9, this
#: family 10 to 12. Warm and mid-dark is what the pale blue prisms stand out against. Copper
#: scored highest (14.1) but swallows an orange ray bundle, as the amber LED once did (bugs/0052).
MODERN_UNPROMOTED_STEP_COLOR = (0.52, 0.42, 0.33)
MODERN_UNPROMOTED_STEP_OPACITY = (0.30, 0.46)
#: satin, not glassy: it is a fixture, and a strong highlight would compete with the prisms'
UNPROMOTED_STEP_MATERIAL = (0.55, 0.40, 0.45, 30.0)
#: the import label of that body
UNPROMOTED_STEP_LABEL = "optical"

#: rays: up to this many are drawn at their full opacity; beyond it opacity falls as 1/sqrt(n)
RAY_FULL_OPACITY_COUNT = 36
RAY_MIN_DENSITY_FACTOR = 0.20
#: a diagnostic ray (a miss, a clipped stub) is a message, not light: it never fades below this
RAY_DIAGNOSTIC_DENSITY_FLOOR = 0.70
#: the classic style draws an ordinary ray 1.0 px wide; a miss is wider, a clipped stub thinner
RAY_ORDINARY_WIDTH = 1.0
#: ray colours are pulled to the mid-tones: saturation capped, lightness drawn toward the middle
RAY_MAX_SATURATION = 0.62
RAY_LIGHTNESS_CENTRE = 0.45
RAY_LIGHTNESS_SPREAD = 0.40


class MeshLook(NamedTuple):
    """What an element's actor is drawn with; `material` is (ambient, diffuse, specular, power)."""
    color: tuple
    opacity: float
    line_width: float
    material: Optional[tuple]


def is_modern(inspector: Any) -> bool:
    """The inspector's "Modern look" switch (off when it has none: the classic look)."""
    variable = getattr(inspector, "modern_look_var", None)
    try:
        return bool(variable.get()) if variable is not None else False
    except Exception:
        return False


def _same(color, reference, tolerance: float = 2e-3) -> bool:
    try:
        return len(color) == 3 and all(abs(float(a) - float(b)) <= tolerance for a, b in zip(color, reference))
    except Exception:
        return False


def mesh_look(color, opacity: float, line_width: float, *, wireframe: bool = False) -> Optional[MeshLook]:
    """The MODERN drawing of a table element's actor asked for in the classic palette, or None
    when the modern look has nothing to say about it (any other colour is the scene's own
    business: a user's surface colour, a handle, a highlight)."""
    opacity = float(opacity)
    if _same(color, CLASSIC_GLASS_COLOR) or _same(color, CLASSIC_STEP_BODY_COLOR):
        if wireframe:
            # the triangle wires the classic look lays over an opaque element so it reads under
            # the rays; modern glass is translucent and needs none
            return MeshLook(MODERN_GLASS_COLOR, 0.0, float(line_width), None)
        low, high = MODERN_GLASS_OPACITY
        # an element drawn at opacity 0 is hidden ON PURPOSE (a cement layer, a redundant drum,
        # a suppressed aperture disc -- bugs/0046, 0033): it stays hidden
        return MeshLook(MODERN_GLASS_COLOR, min(max(opacity, low), high) if opacity > 1e-3 else 0.0,
                        float(line_width), GLASS_MATERIAL)
    if _same(color, CLASSIC_MIRROR_COLOR):
        if wireframe:                       # as for glass: a lit mirror needs no triangle wires
            return MeshLook(MODERN_MIRROR_COLOR, 0.0, float(line_width), None)
        return MeshLook(MODERN_MIRROR_COLOR, opacity, float(line_width), MIRROR_MATERIAL)
    if _same(color, CLASSIC_SILHOUETTE_COLOR) or _same(color, CLASSIC_EDGE_COLOR):
        return MeshLook(MODERN_EDGE_COLOR, opacity * MODERN_EDGE_OPACITY, MODERN_EDGE_WIDTH, None)
    if _same(color, CLASSIC_OUTLINE_COLOR) or _same(color, CLASSIC_OUTLINE_OVERLAY_COLOR):
        return MeshLook(MODERN_OUTLINE_COLOR, opacity, min(float(line_width), MODERN_EDGE_WIDTH), None)
    return None


def color_difference(color_a, color_b) -> float:
    """The CIE76 difference of two sRGB colours (components 0..1): about 2 is the least the eye
    notices, 10 is plain, 30 and more is a different colour altogether."""
    def lab(color):
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (float(v) for v in color)]
        x = (0.4124564 * linear[0] + 0.3575761 * linear[1] + 0.1804375 * linear[2]) / 0.95047
        y = 0.2126729 * linear[0] + 0.7151522 * linear[1] + 0.0721750 * linear[2]
        z = (0.0193339 * linear[0] + 0.1191920 * linear[1] + 0.9503041 * linear[2]) / 1.08883
        fx, fy, fz = (v ** (1.0 / 3.0) if v > 216.0 / 24389.0 else (24389.0 / 27.0 * v + 16.0) / 116.0 for v in (x, y, z))
        return 116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)

    return math.dist(lab(color_a), lab(color_b))


def step_body_look(label, color, opacity: float) -> Optional[MeshLook]:
    """The MODERN drawing of an imported STEP BODY, by its import label, or None when the modern
    look leaves it as asked -- lens, camera and LED hardware keep the look bugs/0958 gave them.

    The one it restyles is the un-promoted "optical" import (bugs/0974)."""
    if str(label or "").strip().lower() != UNPROMOTED_STEP_LABEL or not _same(color, CLASSIC_STEP_BODY_COLOR):
        return None
    low, high = MODERN_UNPROMOTED_STEP_OPACITY
    opacity = float(opacity)
    return MeshLook(MODERN_UNPROMOTED_STEP_COLOR, min(max(opacity, low), high) if opacity > 1e-3 else 0.0,
                    1.0, UNPROMOTED_STEP_MATERIAL)


def soften_ray_color(color) -> tuple:
    """A ray colour in the mid-tones: the same hue, less saturated, nearer middle lightness.
    Greys pass through (a clipped stub is grey on purpose)."""
    try:
        red, green, blue = (min(max(float(c), 0.0), 1.0) for c in color)
    except Exception:
        return tuple(color)
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    if saturation < 0.08:
        return (red, green, blue)
    lightness = RAY_LIGHTNESS_CENTRE + RAY_LIGHTNESS_SPREAD * (lightness - RAY_LIGHTNESS_CENTRE)
    return tuple(colorsys.hls_to_rgb(hue, lightness, min(saturation, RAY_MAX_SATURATION)))


def ray_density_factor(ray_count: int) -> float:
    """How much of its opacity an ordinary ray keeps when `ray_count` rays are drawn."""
    count = max(int(ray_count), 1)
    if count <= RAY_FULL_OPACITY_COUNT:
        return 1.0
    return max(math.sqrt(RAY_FULL_OPACITY_COUNT / count), RAY_MIN_DENSITY_FACTOR)


def ray_look(color, opacity: float, line_width: float, ray_count: int) -> tuple:
    """(colour, opacity, line width) of a traced ray in the modern look. `line_width` is the
    classic style's (`_ray_terminal_3d_style`): 1.0 px is ordinary light; a missed ray is wider and a
    clipped stub thinner, and those diagnostics keep most of their opacity whatever the count."""
    factor = ray_density_factor(ray_count)
    if abs(float(line_width) - RAY_ORDINARY_WIDTH) > 1e-6:
        factor = max(factor, RAY_DIAGNOSTIC_DENSITY_FLOOR)
    return soften_ray_color(color), float(opacity) * factor, float(line_width)


def apply_material(prop, material) -> None:
    """Light a surface with `material` = (ambient, diffuse, specular, specular power)."""
    ambient, diffuse, specular, power = material
    prop.SetInterpolationToPhong()
    prop.SetAmbient(float(ambient))
    prop.SetDiffuse(float(diffuse))
    prop.SetSpecular(float(specular))
    prop.SetSpecularPower(float(power))
    prop.SetSpecularColor(1.0, 1.0, 1.0)


def apply_backdrop(renderer, modern: bool) -> None:
    """The sheet behind the scene: white, or the modern look's soft vertical gradient."""
    if renderer is None:
        return
    if not modern:
        renderer.GradientBackgroundOff()
        renderer.SetBackground(*CLASSIC_BACKGROUND)
        return
    bottom, top = MODERN_BACKGROUND
    renderer.SetBackground(*bottom)
    renderer.SetBackground2(*top)
    renderer.GradientBackgroundOn()
