"""Prototype: show that the BEAM-SPLITTER clear aperture (not the LED, not the imaging
lens) is the limiting stop that carves the 2 fold-axis dark edges in the MV-150 coaxial
area-LED setup. See bugs/0179.

Everything is built from the real machine_vision_150mm_coaxial_led.py constants, so the
picture tracks the layout the relative-illumination map traces.

Two views:
  (top)    side-view acceptance cones -- fold (x-z) and perp (y-z). The cone has its
           APEX at a FOV-edge point and is BOUNDED BY THE BS APERTURE, extended back to
           the LED plane. The fold cone's upper marginal ray is clipped by the BS edge so
           it underfills the LED (-> dark edge); the perp cone overfills the LED (-> uniform).
  (bottom) footprint-at-the-LED-plane for 3 field points: the BS aperture projected onto
           the LED plane through each FOV point. overlap(footprint, LED) / LED = relative
           irradiance. fold-edge slides half off the LED (0.66); centre & perp are full (1.00).
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from KrakenOS.common_optical_layouts import machine_vision_150mm_coaxial_led as L

# --- geometry from the real layout -------------------------------------------------
Z_LED = 0.0
Z_STOP = L.LED_TO_STOP                 # 75
Z_FOV = L.LED_TO_STOP + L.STOP_TO_FOV  # 130
FOV_HALF = L.FOV_MM / 2.0              # 19.5

AX = {  # per-axis half-widths: fold = X (narrow stop), perp = Y (wide stop)
    "fold": dict(led=L.LED_HALF_X, stop=L.STOP_HALF_X, label="Fold axis  (X, 55 mm LED / 30 mm BS stop)"),
    "perp": dict(led=L.LED_HALF_Y, stop=L.STOP_HALF_Y, label="Perp axis  (Y, 78 mm LED / 78 mm BS stop)"),
}


def led_coord(stop_edge, apex):
    """Where a ray from FOV apex through a BS-aperture edge lands on the LED plane."""
    f = (Z_LED - Z_FOV) / (Z_STOP - Z_FOV)
    return f * stop_edge + (1.0 - f) * apex


def cone_at_led(apex, stop_half):
    """LED-plane span [lo, hi] of the acceptance cone bounded by the BS aperture."""
    a = led_coord(-stop_half, apex)
    b = led_coord(+stop_half, apex)
    return (min(a, b), max(a, b))


def overlap(seg, half):
    lo = max(seg[0], -half)
    hi = min(seg[1], half)
    return (lo, hi) if hi > lo else None


# --- figure ------------------------------------------------------------------------
fig = plt.figure(figsize=(13.5, 9.0))
fig.suptitle(
    "The BEAM-SPLITTER clear aperture is the limiting stop -> 2 fold-axis dark edges (MV-150 coaxial LED)",
    fontsize=13, fontweight="bold",
)
gs = fig.add_gridspec(2, 6, height_ratios=[1.05, 1.0], hspace=0.32, wspace=0.9)

COL_CONE = "#1f77b4"
COL_SEEN = "#2ca02c"
COL_DARK = "#d62728"
COL_LED = "#bdbdbd"


def draw_side_view(ax, which, apex):
    p = AX[which]
    led_h, stop_h = p["led"], p["stop"]
    lo, hi = cone_at_led(apex, stop_h)
    seen = overlap((lo, hi), led_h)
    cover = (seen[1] - seen[0]) / (2.0 * led_h) if seen else 0.0

    tmax = 72.0
    # opaque BS stop blades (gap = clear aperture)
    ax.plot([Z_STOP, Z_STOP], [stop_h, tmax], color="black", lw=4, solid_capstyle="butt")
    ax.plot([Z_STOP, Z_STOP], [-tmax, -stop_h], color="black", lw=4, solid_capstyle="butt")
    ax.annotate("BS exit\naperture", (Z_STOP, stop_h), textcoords="offset points",
                xytext=(6, 10), fontsize=8, color="black")

    # acceptance cone (apex at FOV point, through the aperture edges, to the LED plane)
    cone = Polygon([(Z_FOV, apex), (Z_LED, hi), (Z_LED, lo)], closed=True,
                   facecolor=COL_CONE, alpha=0.16, edgecolor="none")
    ax.add_patch(cone)
    for edge_t in (hi, lo):
        ax.plot([Z_FOV, Z_LED], [apex, edge_t], color=COL_CONE, lw=1.4)

    # LED: seen part green, occluded part red-hatched
    ax.plot([Z_LED, Z_LED], [-led_h, led_h], color=COL_LED, lw=7, solid_capstyle="butt", zorder=1)
    if seen:
        ax.plot([Z_LED, Z_LED], [seen[0], seen[1]], color=COL_SEEN, lw=7,
                solid_capstyle="butt", zorder=2)
    for a, b in ((-led_h, seen[0] if seen else -led_h), (seen[1] if seen else led_h, led_h)):
        if b - a > 1e-6:
            ax.add_patch(Rectangle((Z_LED - 1.4, a), 2.8, b - a, facecolor="none",
                                   edgecolor=COL_DARK, hatch="////", lw=0.0, zorder=3))

    # FOV plane + apex point
    ax.plot([Z_FOV, Z_FOV], [-FOV_HALF, FOV_HALF], color="#555555", lw=7,
            solid_capstyle="butt")
    ax.plot([Z_FOV], [apex], "o", color=COL_CONE, ms=6)

    ax.text(Z_LED, -tmax + 5, "LED", ha="center", fontsize=8)
    ax.text(Z_FOV, -tmax + 5, "FOV", ha="center", fontsize=8)
    ax.set_title(f"{p['label']}\nFOV edge sees {cover*100:4.0f}% of the LED",
                 fontsize=9.5)
    ax.set_xlim(-12, Z_FOV + 12)
    ax.set_ylim(-tmax, tmax)
    ax.set_xlabel("z (mm)", fontsize=8)
    ax.set_ylabel(f"{'x' if which == 'fold' else 'y'} (mm)", fontsize=8)
    ax.tick_params(labelsize=7)


def draw_footprint(ax, title, px, py):
    fx = cone_at_led(px, L.STOP_HALF_X)
    fy = cone_at_led(py, L.STOP_HALF_Y)
    ox = overlap(fx, L.LED_HALF_X)
    oy = overlap(fy, L.LED_HALF_Y)
    cover = 0.0
    if ox and oy:
        cover = ((ox[1] - ox[0]) * (oy[1] - oy[0])) / (4.0 * L.LED_HALF_X * L.LED_HALF_Y)

    # LED rectangle
    ax.add_patch(Rectangle((-L.LED_HALF_X, -L.LED_HALF_Y), 2 * L.LED_HALF_X, 2 * L.LED_HALF_Y,
                           facecolor=COL_LED, alpha=0.45, edgecolor="#777777", lw=1.2))
    # BS-aperture footprint projected onto the LED plane
    ax.add_patch(Rectangle((fx[0], fy[0]), fx[1] - fx[0], fy[1] - fy[0],
                           facecolor="none", edgecolor=COL_CONE, lw=1.8, ls="--"))
    # overlap = LED actually seen
    if ox and oy:
        ax.add_patch(Rectangle((ox[0], oy[0]), ox[1] - ox[0], oy[1] - oy[0],
                               facecolor=COL_SEEN, alpha=0.35, edgecolor=COL_SEEN, lw=1.2))
    # the LED strip the BS aperture occludes (LED minus overlap, x-direction)
    if ox and oy and (ox[1] - ox[0]) < 2 * L.LED_HALF_X - 1e-6:
        for a, b in ((-L.LED_HALF_X, ox[0]), (ox[1], L.LED_HALF_X)):
            if b - a > 1e-6:
                ax.add_patch(Rectangle((a, -L.LED_HALF_Y), b - a, 2 * L.LED_HALF_Y,
                                       facecolor="none", edgecolor=COL_DARK, hatch="////", lw=0.0))

    ax.set_title(f"{title}\nirradiance ≈ {cover:.2f}", fontsize=9)
    ax.set_xlim(-70, 70)
    ax.set_ylim(-70, 70)
    ax.set_aspect("equal")
    ax.axhline(0, color="#dddddd", lw=0.6, zorder=0)
    ax.axvline(0, color="#dddddd", lw=0.6, zorder=0)
    ax.set_xlabel("x (mm, fold)", fontsize=8)
    ax.set_ylabel("y (mm, perp)", fontsize=8)
    ax.tick_params(labelsize=7)


# top row: side-view cones (each spans 3 of the 6 columns)
draw_side_view(fig.add_subplot(gs[0, 0:3]), "fold", +FOV_HALF)
draw_side_view(fig.add_subplot(gs[0, 3:6]), "perp", +FOV_HALF)

# bottom row: footprint-at-LED for the 3 representative field points
draw_footprint(fig.add_subplot(gs[1, 0:2]), "Centre  (0, 0)", 0.0, 0.0)
draw_footprint(fig.add_subplot(gs[1, 2:4]), "Fold edge  (x=+19.5)", +FOV_HALF, 0.0)
draw_footprint(fig.add_subplot(gs[1, 4:6]), "Perp edge  (y=+19.5)", 0.0, +FOV_HALF)

# shared legend
handles = [
    plt.Line2D([0], [0], color=COL_CONE, lw=2, label="acceptance cone / BS-aperture footprint"),
    plt.Line2D([0], [0], color=COL_SEEN, lw=6, label="LED seen (contributes irradiance)"),
    plt.Line2D([0], [0], color=COL_DARK, lw=6, label="LED occluded by the BS aperture"),
    plt.Line2D([0], [0], color=COL_LED, lw=6, label="LED extent (55 x 78 mm)"),
]
fig.legend(handles=[h for h in handles], loc="lower center", ncol=4, fontsize=8.5,
           frameon=False, bbox_to_anchor=(0.5, 0.005))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proto_bs_limiter_footprint.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print("wrote", out)

# numeric check against the bug-doc coverage model (fold 0.66, perp 1.00)
for name, px, py in (("centre", 0.0, 0.0), ("fold-edge", FOV_HALF, 0.0), ("perp-edge", 0.0, FOV_HALF)):
    fx = cone_at_led(px, L.STOP_HALF_X)
    fy = cone_at_led(py, L.STOP_HALF_Y)
    ox = overlap(fx, L.LED_HALF_X)
    oy = overlap(fy, L.LED_HALF_Y)
    cov = ((ox[1] - ox[0]) * (oy[1] - oy[0])) / (4.0 * L.LED_HALF_X * L.LED_HALF_Y)
    print(f"  {name:10s} footprint x={fx[0]:7.2f}..{fx[1]:6.2f}  coverage={cov:.3f}")
