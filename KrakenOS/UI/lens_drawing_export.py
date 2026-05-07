"""ISO 10110-style lens fabrication drawing export.

Generates multi-page PDF drawings suitable for lens fabrication,
following the format of vendor datasheets (e.g. Edmund Optics).

Page 1: Assembly cross-section with overall dimensions, EFL/BFL.
Page 2+: Individual element drawings with radii, thickness, glass,
         surface quality placeholders, and coating notes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
import numpy as np

from KrakenOS.UI.lens_drawing_properties import drawing_properties

if TYPE_CHECKING:
    from matplotlib.axes import Axes


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LensElement:
    """One glass element extracted from the surface table."""
    name: str
    left_rc: float          # radius of curvature, left surface
    right_rc: float         # radius of curvature, right surface
    center_thickness: float # mm
    diameter: float         # mm
    glass: str              # e.g. "N-BK7"
    index: int = 0          # element number (1-based)
    z_vertex_left: float = 0.0  # global z position of left vertex
    left_row_index: int = -1
    right_row_index: int = -1
    left_properties: dict = field(default_factory=dict)
    right_properties: dict = field(default_factory=dict)


@dataclass
class LensGroup:
    """A group of cemented elements (or a single element)."""
    elements: list[LensElement] = field(default_factory=list)

    @property
    def total_thickness(self) -> float:
        return sum(e.center_thickness for e in self.elements)

    @property
    def diameter(self) -> float:
        return max(e.diameter for e in self.elements) if self.elements else 0.0

    @property
    def is_cemented(self) -> bool:
        return len(self.elements) > 1

    @property
    def left_rc(self) -> float:
        return self.elements[0].left_rc if self.elements else 0.0

    @property
    def right_rc(self) -> float:
        return self.elements[-1].right_rc if self.elements else 0.0


# ---------------------------------------------------------------------------
# Element extraction from surface rows
# ---------------------------------------------------------------------------

_SKIP_SURFACES = {"Object", "Image", "Aperture"}


def _is_glass(glass: str) -> bool:
    return glass.upper() not in {"AIR", "", "MIRROR"}


def _drawing_properties(row) -> dict:
    return drawing_properties(row)


def identify_elements(rows: list) -> tuple[list[LensGroup], dict]:
    """Extract lens elements and groups from SurfaceRow list.

    Returns (groups, info).
    """
    elements: list[LensElement] = []
    elem_idx = 0
    z_pos = 0.0

    for i, row in enumerate(rows):
        surface_type = getattr(row, "surface", "Standard")
        name = getattr(row, "name", f"Surface {i}")
        rc = getattr(row, "rc", 0.0)
        thickness = getattr(row, "thickness", 0.0)
        diameter = getattr(row, "diameter", 25.0)
        glass = getattr(row, "glass", "AIR")

        if surface_type in _SKIP_SURFACES or name in _SKIP_SURFACES:
            z_pos += thickness
            continue

        if surface_type == "Thin Lens":
            z_pos += thickness
            continue

        if _is_glass(glass):
            elem_idx += 1
            right_rc = 0.0
            right_props = {}
            right_row_index = -1
            if i + 1 < len(rows):
                right_rc = getattr(rows[i + 1], "rc", 0.0)
                right_props = _drawing_properties(rows[i + 1])
                right_row_index = i + 1

            elements.append(LensElement(
                name=name,
                left_rc=rc,
                right_rc=right_rc,
                center_thickness=thickness,
                diameter=diameter,
                glass=glass,
                index=elem_idx,
                z_vertex_left=z_pos,
                left_row_index=i,
                right_row_index=right_row_index,
                left_properties=_drawing_properties(row),
                right_properties=right_props,
            ))

        z_pos += thickness

    # Group cemented elements (no air gap between them)
    groups: list[LensGroup] = []
    if not elements:
        return groups, {}

    current_group = LensGroup(elements=[elements[0]])
    for j in range(1, len(elements)):
        prev = elements[j - 1]
        curr = elements[j]
        gap = curr.z_vertex_left - (prev.z_vertex_left + prev.center_thickness)
        if abs(gap) < 0.01:
            current_group.elements.append(curr)
        else:
            groups.append(current_group)
            current_group = LensGroup(elements=[curr])
    groups.append(current_group)

    return groups, {}


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _sag(R: float, h: float) -> float:
    """Sag of a spherical surface at semi-diameter h."""
    if R == 0.0 or abs(R) <= abs(h):
        return 0.0
    return R - math.copysign(math.sqrt(R * R - h * h), R)


def _surface_profile(R: float, h: float, n_pts: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """Return (x_along_axis, y_radial) arrays for a surface arc."""
    y = np.linspace(-h, h, n_pts)
    if R == 0.0 or abs(R) <= h:
        x = np.zeros_like(y)
    else:
        x = R - np.sign(R) * np.sqrt(R ** 2 - y ** 2)
    return x, y


def _curvature_label(R: float) -> str:
    if R == 0.0:
        return "FLAT"
    return "CX" if R > 0 else "CV"


def _edge_thickness(elem: LensElement) -> float:
    """Compute edge thickness of an element."""
    h = elem.diameter / 2.0
    sag_l = _sag(elem.left_rc, h)
    sag_r = _sag(elem.right_rc, h)
    return elem.center_thickness - sag_l + sag_r


def _prop_text(props: dict, key: str, default: str) -> str:
    value = props.get(key, "")
    text = str(value).strip()
    return text if text else default


def _append_tolerance(value_text: str, props: dict, key: str) -> str:
    tolerance = str(props.get(key, "") or "").strip()
    if not tolerance:
        return value_text
    return f"{value_text}{tolerance}"


def _radius_text(R: float, props: dict) -> str:
    if R == 0.0:
        return "FLAT"
    radius = _append_tolerance(f"{abs(R):.2f}", props, "radius_tolerance")
    return f"R  {radius}  {_curvature_label(R)}"


def _dimension_text(value: float, props: dict, key: str, *, decimals: int = 1, prefix: str = "") -> str:
    text = f"{prefix}{value:.{decimals}f}"
    return _append_tolerance(text, props, key)


def _clear_aperture_text(props: dict, default_diameter: float) -> str:
    value = props.get("clear_aperture_mm", "")
    try:
        parsed = float(value)
    except Exception:
        parsed = 0.0
    clear_aperture = parsed if parsed > 0 else max(float(default_diameter) - 1.0, 0.0)
    return f"\u00d8e  {clear_aperture:.3g}"


# ---------------------------------------------------------------------------
# Drawing constants
# ---------------------------------------------------------------------------

_PROFILE_LW = 0.8
_DIM_LW = 0.4
_EXT_LW = 0.3    # extension lines
_HATCH_LW = 0.3
_CENTER_LW = 0.3
_FONT_SIZE = 8
_DIM_FONT = 7

# A4 portrait in inches
_PAGE_W = 8.27
_PAGE_H = 11.69

# Page layout zones (fraction of page height)
_MARGIN_L = 0.08
_MARGIN_R = 0.08
_DRAWING_TOP = 0.92
_DRAWING_BOT = 0.42   # drawing area
_NOTES_TOP = 0.41
_NOTES_BOT = 0.33      # notes area
_TABLE_TOP = 0.32
_TABLE_BOT = 0.14       # specs table
_TITLE_TOP = 0.12
_TITLE_BOT = 0.02       # title block


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _draw_dim_h(ax: Axes, x1: float, x2: float, y: float,
                label: str, ext_y1: float | None = None,
                ext_y2: float | None = None) -> None:
    """Horizontal dimension with extension lines and label above."""
    # Extension lines (thin, from feature to dimension line)
    ext_gap = abs(x2 - x1) * 0.02 + 0.15  # small gap from feature
    ext_over = abs(x2 - x1) * 0.02 + 0.3  # overshoot past dim line
    if ext_y1 is not None:
        y_start = ext_y1 + (ext_gap if ext_y1 < y else -ext_gap)
        y_end = y + (ext_over if ext_y1 < y else -ext_over)
        ax.plot([x1, x1], [y_start, y_end], "k-", linewidth=_EXT_LW, zorder=2)
    if ext_y2 is not None:
        y_start = ext_y2 + (ext_gap if ext_y2 < y else -ext_gap)
        y_end = y + (ext_over if ext_y2 < y else -ext_over)
        ax.plot([x2, x2], [y_start, y_end], "k-", linewidth=_EXT_LW, zorder=2)

    # Dimension line with arrows
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="<->", lw=_DIM_LW, color="black",
                                shrinkA=0, shrinkB=0))
    mid = (x1 + x2) / 2
    ax.text(mid, y, f"  {label}  ", ha="center", va="bottom",
            fontsize=_DIM_FONT, fontfamily="sans-serif",
            bbox=dict(facecolor="white", edgecolor="none", pad=0.5))


def _draw_dim_v(ax: Axes, y1: float, y2: float, x: float,
                label: str, ext_x1: float | None = None,
                ext_x2: float | None = None) -> None:
    """Vertical dimension with extension lines and rotated label."""
    ext_gap = abs(y2 - y1) * 0.01 + 0.15
    ext_over = abs(y2 - y1) * 0.01 + 0.3
    if ext_x1 is not None:
        x_start = ext_x1 + (ext_gap if ext_x1 < x else -ext_gap)
        x_end = x + (ext_over if ext_x1 < x else -ext_over)
        ax.plot([x_start, x_end], [y1, y1], "k-", linewidth=_EXT_LW, zorder=2)
    if ext_x2 is not None:
        x_start = ext_x2 + (ext_gap if ext_x2 < x else -ext_gap)
        x_end = x + (ext_over if ext_x2 < x else -ext_over)
        ax.plot([x_start, x_end], [y2, y2], "k-", linewidth=_EXT_LW, zorder=2)

    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="<->", lw=_DIM_LW, color="black",
                                shrinkA=0, shrinkB=0))
    mid = (y1 + y2) / 2
    ax.text(x, mid, f"  {label}  ", ha="left", va="center",
            fontsize=_DIM_FONT, fontfamily="sans-serif", rotation=90,
            bbox=dict(facecolor="white", edgecolor="none", pad=0.5))


def _draw_element_profile(ax: Axes, elem: LensElement,
                           x_offset: float = 0.0,
                           hatch: bool = True,
                           label: str | None = None,
                           label_y_frac: float = 1.15) -> None:
    """Draw the cross-section of a single lens element."""
    h = elem.diameter / 2.0
    R1 = elem.left_rc
    R2 = elem.right_rc
    CT = elem.center_thickness

    x_left, y_left = _surface_profile(R1, h)
    x_left = x_left + x_offset

    x_right, y_right = _surface_profile(R2, h)
    x_right = x_right + x_offset + CT

    left_top_x = x_left[-1]
    right_top_x = x_right[-1]
    left_bot_x = x_left[0]
    right_bot_x = x_right[0]

    # Closed polygon for hatching
    poly_x = np.concatenate([x_left, [left_top_x, right_top_x],
                             x_right[::-1], [right_bot_x, left_bot_x]])
    poly_y = np.concatenate([y_left, [h, h],
                             y_right[::-1], [-h, -h]])

    if hatch:
        polygon = mpatches.Polygon(
            np.column_stack([poly_x, poly_y]),
            closed=True, fill=False, edgecolor="none",
            hatch="////", linewidth=_HATCH_LW, zorder=2,
        )
        ax.add_patch(polygon)

    # Outline
    ax.plot(x_left, y_left, "k-", linewidth=_PROFILE_LW, zorder=3)
    ax.plot(x_right, y_right, "k-", linewidth=_PROFILE_LW, zorder=3)
    ax.plot([left_top_x, right_top_x], [h, h], "k-",
            linewidth=_PROFILE_LW, zorder=3)
    ax.plot([left_bot_x, right_bot_x], [-h, -h], "k-",
            linewidth=_PROFILE_LW, zorder=3)

    if label:
        ax.text(x_offset + CT / 2, h * label_y_frac, label,
                ha="center", va="bottom", fontsize=_FONT_SIZE,
                fontfamily="sans-serif")


# ---------------------------------------------------------------------------
# Page framework
# ---------------------------------------------------------------------------

def _make_page() -> tuple[Figure, "Axes"]:
    """Create A4 portrait figure with drawing axes in the upper area."""
    fig = Figure(figsize=(_PAGE_W, _PAGE_H))
    ax = fig.add_axes([_MARGIN_L, _DRAWING_BOT,
                       1 - _MARGIN_L - _MARGIN_R,
                       _DRAWING_TOP - _DRAWING_BOT])
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def _draw_title_block(fig: Figure, title: str, dwg_no: str,
                       sheet: int, total_sheets: int) -> None:
    """Draw the title block at the bottom of the page."""
    w = 1 - _MARGIN_L - _MARGIN_R
    tb = fig.add_axes([_MARGIN_L, _TITLE_BOT, w, _TITLE_TOP - _TITLE_BOT])
    tb.set_xlim(0, 1)
    tb.set_ylim(0, 1)
    tb.set_aspect("auto")
    for spine in tb.spines.values():
        spine.set_linewidth(1.0)
        spine.set_color("black")
    tb.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    # Vertical dividers
    tb.axvline(0.40, color="black", linewidth=0.5)
    tb.axvline(0.72, color="black", linewidth=0.5)
    # Horizontal divider in right two columns
    tb.plot([0.40, 1.0], [0.5, 0.5], "k-", linewidth=0.5,
            transform=tb.transAxes, clip_on=False)

    # Left: notes
    tb.text(0.01, 0.85, "ALL DIMS IN: mm", fontsize=6,
            fontfamily="sans-serif", va="top")
    tb.text(0.01, 0.55, "PROTECTIVE CHAMFERS AS NEEDED",
            fontsize=5.5, fontfamily="sans-serif", va="top")
    tb.text(0.01, 0.28, "FOR INFORMATION ONLY: DO NOT MANUFACTURE\n"
            "PARTS TO THIS DRAWING",
            fontsize=4.5, fontfamily="sans-serif", va="top", color="gray")
    tb.text(0.01, 0.05, "INDICATIONS IN ACCORDANCE WITH ISO 10110",
            fontsize=4.5, fontfamily="sans-serif", va="bottom", color="gray")

    # Middle: title
    tb.text(0.56, 0.80, "TITLE", fontsize=5, fontfamily="sans-serif",
            ha="center", va="center", color="gray")
    tb.text(0.56, 0.25, title, fontsize=8, fontfamily="sans-serif",
            ha="center", va="center", fontweight="bold")

    # Right: drawing number + sheet
    tb.text(0.74, 0.80, "DWG NO", fontsize=5, fontfamily="sans-serif",
            va="center", color="gray")
    tb.text(0.74, 0.25, dwg_no, fontsize=6.5, fontfamily="sans-serif",
            va="center")
    tb.text(0.90, 0.80, "SHEET SIZE", fontsize=4.5,
            fontfamily="sans-serif", va="center", ha="center", color="gray")
    tb.text(0.90, 0.58, "A4", fontsize=7, fontfamily="sans-serif",
            va="center", ha="center")
    tb.text(0.97, 0.80, "SHEET", fontsize=4.5,
            fontfamily="sans-serif", va="center", ha="center", color="gray")
    tb.text(0.97, 0.58, f"{sheet} OF {total_sheets}", fontsize=6.5,
            fontfamily="sans-serif", va="center", ha="center")


def _draw_notes(fig: Figure, lines: list[str]) -> None:
    """Draw notes between the drawing and the specs table."""
    w = 1 - _MARGIN_L - _MARGIN_R
    nax = fig.add_axes([_MARGIN_L, _NOTES_BOT, w * 0.55,
                        _NOTES_TOP - _NOTES_BOT])
    nax.axis("off")
    text = "\n".join(lines)
    nax.text(0, 1, text, fontsize=6.5, fontfamily="sans-serif",
             va="top", ha="left", transform=nax.transAxes, linespacing=1.5)


def _draw_element_specs_table(fig: Figure, elem: LensElement) -> None:
    """Draw LEFT SURFACE | MATERIAL | RIGHT SURFACE table."""
    w = 1 - _MARGIN_L - _MARGIN_R
    ax = fig.add_axes([_MARGIN_L, _TABLE_BOT, w, _TABLE_TOP - _TABLE_BOT])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("auto")
    ax.axis("off")

    col2 = 0.35
    col3 = 0.65

    # Header
    hy = 0.95
    ax.plot([0, 1], [hy, hy], "k-", linewidth=0.5, transform=ax.transAxes)
    hb = 0.85
    ax.plot([0, 1], [hb, hb], "k-", linewidth=0.5, transform=ax.transAxes)

    ax.text(col2 / 2, (hy + hb) / 2, "LEFT SURFACE", ha="center", va="center",
            fontsize=7, fontfamily="sans-serif", fontweight="bold")
    ax.text((col2 + col3) / 2, (hy + hb) / 2, "MATERIAL", ha="center", va="center",
            fontsize=7, fontfamily="sans-serif", fontweight="bold")
    ax.text((col3 + 1) / 2, (hy + hb) / 2, "RIGHT SURFACE", ha="center", va="center",
            fontsize=7, fontfamily="sans-serif", fontweight="bold")

    # Vertical dividers
    ax.plot([col2, col2], [0.05, hy], "k-", linewidth=0.5, transform=ax.transAxes)
    ax.plot([col3, col3], [0.05, hy], "k-", linewidth=0.5, transform=ax.transAxes)

    # Content rows
    lr = elem.left_rc
    rr = elem.right_rc
    left_props = elem.left_properties or {}
    right_props = elem.right_properties or {}
    lr_text = _radius_text(lr, left_props)
    rr_text = _radius_text(rr, right_props)
    material_note = _prop_text(left_props, "material_note", _prop_text(right_props, "material_note", ""))
    material_text = f"GLASS  {elem.glass}" + (f"  {material_note}" if material_note else "")

    rows_data = [
        (lr_text, material_text, rr_text),
        (_clear_aperture_text(left_props, elem.diameter), "", _clear_aperture_text(right_props, elem.diameter)),
        (
            _prop_text(left_props, "form_error", "3/  ___  \u03bb=632.8 nm"),
            "",
            _prop_text(right_props, "form_error", "3/  ___  \u03bb=632.8 nm"),
        ),
        (
            _prop_text(left_props, "irregularity", "4/  \u2014"),
            "",
            _prop_text(right_props, "irregularity", "4/  \u2014"),
        ),
        (
            _prop_text(left_props, "scratch_dig", "5/  ___  (MIL-PRF-13830B)"),
            "",
            _prop_text(right_props, "scratch_dig", "5/  ___  (MIL-PRF-13830B)"),
        ),
        (
            _prop_text(left_props, "surface_note", "6/  \u2014"),
            "",
            _prop_text(right_props, "surface_note", "6/  \u2014"),
        ),
    ]

    y = hb - 0.08
    step = 0.12
    for i, (left, mid, right) in enumerate(rows_data):
        color = "black" if i < 2 else "gray"
        fsz = 6.5 if i < 2 else 6.0
        ax.text(0.01, y, left, fontsize=fsz, fontfamily="sans-serif",
                va="center", color=color)
        if mid:
            ax.text(col2 + 0.01, y, mid, fontsize=fsz, fontfamily="sans-serif",
                    va="center", color=color)
        ax.text(col3 + 0.01, y, right, fontsize=fsz, fontfamily="sans-serif",
                va="center", color=color)
        y -= step

    # Bottom border
    ax.plot([0, 1], [y + step * 0.3, y + step * 0.3], "k-",
            linewidth=0.5, transform=ax.transAxes)


def _draw_assembly_specs_table(fig: Figure, elements: list[LensElement]) -> None:
    """Draw surface specs table for assembly page."""
    w = 1 - _MARGIN_L - _MARGIN_R
    ax = fig.add_axes([_MARGIN_L, _TABLE_BOT, w, _TABLE_TOP - _TABLE_BOT])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("auto")
    ax.axis("off")

    n_surfaces = len(elements) + 1
    col_w = 1.0 / n_surfaces

    # Header
    hy = 0.95
    hb = 0.85
    ax.plot([0, 1], [hy, hy], "k-", linewidth=0.5, transform=ax.transAxes)
    ax.plot([0, 1], [hb, hb], "k-", linewidth=0.5, transform=ax.transAxes)

    labels = [chr(65 + i) for i in range(n_surfaces)]
    for i, lbl in enumerate(labels):
        cx = i * col_w + col_w / 2
        ax.text(cx, (hy + hb) / 2, f"SURFACE {lbl}", ha="center", va="center",
                fontsize=7, fontfamily="sans-serif", fontweight="bold")
        if i > 0:
            ax.plot([i * col_w, i * col_w], [0.15, hy], "k-",
                    linewidth=0.5, transform=ax.transAxes)

    # Radii and clear apertures
    all_R = [elements[0].left_rc]
    all_d = [elements[0].diameter]
    all_props = [elements[0].left_properties or {}]
    for elem in elements:
        all_R.append(elem.right_rc)
        all_d.append(elem.diameter)
        all_props.append(elem.right_properties or {})

    y1 = hb - 0.10
    for i, (R, d, props) in enumerate(zip(all_R, all_d, all_props)):
        cx = i * col_w + 0.01
        r_text = _radius_text(R, props)
        ax.text(cx, y1, r_text, fontsize=6, fontfamily="sans-serif", va="center")
        ax.text(cx, y1 - 0.12, _clear_aperture_text(props, d), fontsize=6,
                fontfamily="sans-serif", va="center")

    # Cement note
    if len(elements) > 1:
        for i in range(len(elements) - 1):
            cx = (i + 1) * col_w + col_w / 2
            cement_props = elements[i].right_properties or elements[i + 1].left_properties or {}
            cement_text = _prop_text(cement_props, "cement_note", "___")
            ax.text(cx, y1 - 0.28, f"CEMENT: {cement_text}", fontsize=6,
                    fontfamily="sans-serif", va="center", ha="center",
                    color="gray")

    ax.plot([0, 1], [y1 - 0.38, y1 - 0.38], "k-",
            linewidth=0.5, transform=ax.transAxes)


# ---------------------------------------------------------------------------
# Page: individual element
# ---------------------------------------------------------------------------

def _build_element_page(elem: LensElement, sheet: int, total_sheets: int,
                         system_title: str, dwg_no: str) -> Figure:
    """Build a single-element fabrication drawing page."""
    fig, ax = _make_page()
    h = elem.diameter / 2.0
    CT = elem.center_thickness
    left_props = elem.left_properties or {}
    right_props = elem.right_properties or {}
    element_props = left_props or right_props

    # Draw the element centered in the drawing area
    _draw_element_profile(ax, elem, x_offset=0, hatch=True, label=elem.name)

    # Centerline (dash-dot, extends beyond the lens)
    sag_l = _sag(elem.left_rc, h)
    sag_r = _sag(elem.right_rc, h)
    cl_left = min(0, sag_l) - max(CT, h * 0.3)
    cl_right = CT + max(0, sag_r) + max(CT, h * 0.3)
    ax.plot([cl_left, cl_right], [0, 0], color="black", linewidth=_CENTER_LW,
            linestyle=(0, (10, 3, 2, 3)), zorder=1)

    # Dimension: center thickness (below lens, with extension lines)
    dim_y = -h - h * 0.45
    _draw_dim_h(ax, 0, CT, dim_y, _dimension_text(CT, element_props, "thickness_tolerance", decimals=1),
                ext_y1=-h, ext_y2=-h)

    # Dimension: diameter (right of lens, with extension lines)
    right_edge_x = CT + max(0, sag_r)
    dim_x = right_edge_x + max(CT * 0.5, h * 0.15) + 2.0
    top_edge_x = CT + (_sag(elem.right_rc, h) if elem.right_rc else 0)
    bot_edge_x = top_edge_x  # symmetric
    _draw_dim_v(ax, -h, h, dim_x, _dimension_text(elem.diameter, element_props, "diameter_tolerance", decimals=1, prefix="\u2300"),
                ext_x1=top_edge_x, ext_x2=bot_edge_x)

    # Coating callout: λ symbol OUTSIDE the lens, near top-right edge
    # with a leader line pointing to the surface
    coat_x = right_edge_x + max(CT * 0.15, 1.0)
    coat_y = h * 0.65
    ax.text(coat_x, coat_y, "\u03bb", fontsize=11,
            fontfamily="sans-serif", ha="left", va="center",
            fontstyle="italic", zorder=5)
    # "1" note marker near the coating symbol
    ax.text(coat_x + max(CT * 0.12, 0.8), coat_y + h * 0.15, "1",
            fontsize=6.5, fontfamily="sans-serif", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.12", facecolor="white",
                      edgecolor="black", linewidth=0.3),
            zorder=5)

    # Auto-scale view
    pad_x = max(h * 0.4, CT * 0.4, 3.0)
    pad_y = max(h * 0.7, 3.0)
    ax.set_xlim(cl_left - 1, dim_x + 3)
    ax.set_ylim(-h - pad_y, h + pad_y * 0.6)

    coating_notes = []
    left_coating = _prop_text(left_props, "coating_note", "")
    right_coating = _prop_text(right_props, "coating_note", "")
    if left_coating:
        coating_notes.append(f"LEFT:  {left_coating}")
    if right_coating:
        coating_notes.append(f"RIGHT: {right_coating}")
    if not coating_notes:
        coating_notes = ["(specify coating here)", "R(AVG) < ___% FROM ___\u2013___ nm"]
    extra_notes = []
    centration = _prop_text(element_props, "centration_note", "")
    if centration:
        extra_notes.append(f"CENTERING: {centration}")
    edge_note = _prop_text(element_props, "edge_note", "")
    if edge_note:
        extra_notes.append(f"EDGE / CHAMFER: {edge_note}")
    note_lines = ["1    COATING / SURFACE NOTES:", "", *[f"        {note}" for note in coating_notes]]
    if extra_notes:
        note_lines.extend(["", *extra_notes])
    _draw_notes(fig, note_lines)

    # Specs table
    _draw_element_specs_table(fig, elem)

    # Title block
    _draw_title_block(fig, system_title, dwg_no, sheet, total_sheets)

    return fig


# ---------------------------------------------------------------------------
# Page: assembly
# ---------------------------------------------------------------------------

def _build_assembly_page(group: LensGroup, sheet: int, total_sheets: int,
                          system_title: str, dwg_no: str,
                          efl: float | None = None,
                          bfl: float | None = None) -> Figure:
    """Build an assembly drawing page for a lens group."""
    fig, ax = _make_page()
    elements = group.elements
    h = group.diameter / 2.0
    total_ct = group.total_thickness

    # Draw each element
    x_off = 0.0
    for i, elem in enumerate(elements):
        _draw_element_profile(ax, elem, x_offset=x_off, hatch=True,
                              label=f"LENS L{i + 1}\n(SHEET {sheet + 1 + i})",
                              label_y_frac=1.08)
        x_off += elem.center_thickness

    # Centerline
    cl_pad = max(total_ct * 0.25, h * 0.3)
    ax.plot([-cl_pad, total_ct + cl_pad], [0, 0],
            color="black", linewidth=_CENTER_LW,
            linestyle=(0, (10, 3, 2, 3)), zorder=1)

    # Overall thickness dimension (top, with extension lines from top edge)
    dim_y = h + h * 0.35
    _draw_dim_h(ax, 0, total_ct, dim_y, f"{total_ct:.3f}",
                ext_y1=h, ext_y2=h)

    # Diameter dimension (right side)
    max_sag_r = 0
    x_tmp = 0.0
    for elem in elements:
        s = _sag(elem.right_rc, h)
        x_tmp += elem.center_thickness
        max_sag_r = max(max_sag_r, s, 0)
    right_edge = total_ct + max_sag_r
    dim_x = right_edge + max(total_ct * 0.3, h * 0.15) + 2.0

    _draw_dim_v(ax, -h, h, dim_x, f"\u2300{group.diameter:.1f}",
                ext_x1=right_edge, ext_x2=right_edge)

    # Surface labels at bottom
    x_off2 = 0.0
    label_y = -h - h * 0.30
    for i, elem in enumerate(elements):
        sl = _sag(elem.left_rc, h)
        ax.text(x_off2 + sl, label_y, chr(65 + i),
                ha="center", va="top", fontsize=_FONT_SIZE + 1,
                fontfamily="sans-serif", fontweight="bold")
        if i == len(elements) - 1:
            sr = _sag(elem.right_rc, h)
            ax.text(x_off2 + elem.center_thickness + sr, label_y,
                    chr(65 + i + 1),
                    ha="center", va="top", fontsize=_FONT_SIZE + 1,
                    fontfamily="sans-serif", fontweight="bold")
        x_off2 += elem.center_thickness

    # Auto-scale
    pad = max(h * 0.5, total_ct * 0.3, 3.0)
    ax.set_xlim(-cl_pad - 1, dim_x + 3)
    ax.set_ylim(-h - pad, dim_y + pad * 0.8)

    # Notes: EFL / BFL
    notes = []
    if efl is not None:
        notes.append(f"FOCAL LENGTH (EFL):  {efl:.2f}")
    if bfl is not None:
        notes.append(f"BACK FOCAL LENGTH (BFL):  {bfl:.2f}")
    if notes:
        _draw_notes(fig, notes)

    # Assembly specs table
    _draw_assembly_specs_table(fig, elements)

    # Title block
    _draw_title_block(fig, system_title, dwg_no, sheet, total_sheets)

    return fig


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_lens_drawing(rows: list, filepath: str | Path, title: str = "",
                         dwg_no: str = "", efl: float | None = None,
                         bfl: float | None = None) -> Path:
    """Export a multi-page lens fabrication drawing as PDF.

    Parameters
    ----------
    rows : list of SurfaceRow
        The optical system surface table.
    filepath : path
        Output PDF path.
    title : str
        Drawing title (system name).
    dwg_no : str
        Drawing number for the title block.
    efl, bfl : float, optional
        Effective / back focal length for the assembly page.

    Returns
    -------
    Path to the saved PDF.
    """
    filepath = Path(filepath)
    groups, info = identify_elements(rows)

    if not groups:
        raise ValueError("No lens elements found in the surface table.")

    pages: list[Figure] = []
    sheet = 1
    total_sheets = 0
    for g in groups:
        if g.is_cemented:
            total_sheets += 1
        total_sheets += len(g.elements)

    for g in groups:
        if g.is_cemented:
            fig = _build_assembly_page(g, sheet, total_sheets,
                                        title or "Lens Assembly", dwg_no,
                                        efl=efl, bfl=bfl)
            pages.append(fig)
            sheet += 1

        for elem in g.elements:
            fig = _build_element_page(elem, sheet, total_sheets,
                                       title or elem.name, dwg_no)
            pages.append(fig)
            sheet += 1

    with PdfPages(str(filepath)) as pdf:
        for fig in pages:
            pdf.savefig(fig, dpi=150)

    return filepath
