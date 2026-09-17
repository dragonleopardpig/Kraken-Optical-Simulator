"""Generate SVG illustrations for docs/source/knowledge_base/pupil_sampling.rst.

Run from the repository root:

    python tools/generate_pupil_sampling_svgs.py

Each figure lands in docs/source/_static/knowledge_base/pupil_sampling/.
The samplers mirror the ones used in KrakenOS itself so the figures stay in
sync with the code:

* Hexapolar, Square, Random, Fan X/Y/Cross — see PupilCalc.Pattern in
  KrakenOS/PupilTool.py.
* Vogel / golden-angle spiral — see sample_source_disk_points in
  KrakenOS/UI/source_trace_helpers.py (and sample_reference_disk_points_3d,
  source_modeling.py, trace_preview_sampling.py).
* Cosine-weighted hemisphere — KrakenSys.py lambertian/lobe samplers.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "docs/source/_static/knowledge_base/pupil_sampling"

GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))  # ≈ 2.39996 rad ≈ 137.5078°
PHI = (1.0 + math.sqrt(5.0)) / 2.0

DOT_COLOUR = "#c0392b"
RING_COLOUR = "#2c5f9e"
ACCENT_COLOUR = "#1f7a3b"
GREY = "#888"


def _new_axes(title: str | None = None, size: float = 4.0):
    fig, ax = plt.subplots(figsize=(size, size))
    ax.set_aspect("equal")
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.axhline(0.0, color=GREY, linewidth=0.6, linestyle=(0, (4, 4)))
    ax.axvline(0.0, color=GREY, linewidth=0.6, linestyle=(0, (4, 4)))
    ax.add_patch(Circle((0.0, 0.0), 1.0, fill=False, edgecolor=RING_COLOUR, linewidth=1.2))
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    if title:
        ax.set_title(title, fontsize=11)
    return fig, ax


def _scatter(ax, x, y, *, size: float = 14.0, colour: str = DOT_COLOUR):
    ax.scatter(x, y, s=size, c=colour, zorder=3, edgecolors="none")


def _save(fig, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / name
    fig.tight_layout(pad=0.4)
    fig.savefig(out_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# 01 — overview / "what is a pupil sample?"
# ---------------------------------------------------------------------------
def fig_overview() -> None:
    fig, ax = _new_axes("The pupil disk and a ray sample", size=4.2)
    # one chief ray + a sketch of a few sample points
    samples = [(0.0, 0.0), (0.55, 0.30), (-0.45, 0.55), (-0.25, -0.6), (0.65, -0.5)]
    xs, ys = zip(*samples)
    _scatter(ax, xs, ys, size=28)
    for (x, y) in samples:
        ax.annotate("", xy=(x, y), xytext=(0, 0), arrowprops=dict(arrowstyle="-",
                                                                  color=GREY, linewidth=0.6))
    ax.text(0.0, -1.05, "unit pupil", ha="center", va="top", color=RING_COLOUR, fontsize=9)
    ax.text(0.02, 0.06, "chief ray", color=DOT_COLOUR, fontsize=8)
    ax.text(0.58, 0.34, "sample i", color=DOT_COLOUR, fontsize=8)
    _save(fig, "01_pupil_overview.svg")


# ---------------------------------------------------------------------------
# 02 — equal-area mapping
# ---------------------------------------------------------------------------
def fig_equal_area() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 4.0))
    for ax in axes:
        ax.set_aspect("equal")
        ax.set_xlim(-1.15, 1.15)
        ax.set_ylim(-1.15, 1.15)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.add_patch(Circle((0.0, 0.0), 1.0, fill=False, edgecolor=RING_COLOUR, linewidth=1.0))

    n = 200
    rng = np.random.default_rng(7)
    # Wrong: r linear in i/N (over-densifies the centre)
    idx = np.arange(n)
    phi = rng.uniform(0.0, 2.0 * np.pi, n)
    r_lin = idx / float(n)
    axes[0].scatter(r_lin * np.cos(phi), r_lin * np.sin(phi), s=8, c=DOT_COLOUR)
    axes[0].set_title(r"$r = i/N$  (centre-biased)", fontsize=10)

    # Right: r = sqrt(i/N) — equal-area
    r_sqrt = np.sqrt(idx / float(n))
    axes[1].scatter(r_sqrt * np.cos(phi), r_sqrt * np.sin(phi), s=8, c=ACCENT_COLOUR)
    axes[1].set_title(r"$r = \sqrt{i/N}$  (equal-area)", fontsize=10)
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT_DIR / "02_equal_area.svg", format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {(OUT_DIR / '02_equal_area.svg').relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# 03 — section fans
# ---------------------------------------------------------------------------
def fig_section_fans() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.6))
    samp = 6
    rng = np.arange(-samp, samp + 1) / float(samp)
    fan_x = [(r, 0.0) for r in rng if abs(r) <= 1.0]
    fan_y = [(0.0, r) for r in rng if abs(r) <= 1.0]
    cross = fan_x + fan_y

    titles = ("Fan X", "Fan Y", "Cross fan")
    data = (fan_x, fan_y, cross)
    for ax, title, pts in zip(axes, titles, data):
        ax.set_aspect("equal")
        ax.set_xlim(-1.15, 1.15)
        ax.set_ylim(-1.15, 1.15)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.add_patch(Circle((0.0, 0.0), 1.0, fill=False, edgecolor=RING_COLOUR, linewidth=1.0))
        ax.axhline(0.0, color=GREY, linewidth=0.5, linestyle=(0, (4, 4)))
        ax.axvline(0.0, color=GREY, linewidth=0.5, linestyle=(0, (4, 4)))
        xs, ys = zip(*pts)
        ax.scatter(xs, ys, s=14, c=DOT_COLOUR)
        ax.set_title(title, fontsize=10)
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT_DIR / "03_section_fans.svg", format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {(OUT_DIR / '03_section_fans.svg').relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# 04 — hexapolar
# ---------------------------------------------------------------------------
def hexapolar_points(samp: int) -> list[tuple[float, float]]:
    pts = [(0.0, 0.0)]
    for j in range(1, samp + 1):
        r = j / float(samp)
        count = 6 * j
        for k in range(count):
            theta = 2.0 * math.pi * k / float(count)
            pts.append((r * math.cos(theta), r * math.sin(theta)))
    return pts


def fig_hexapolar() -> None:
    fig, ax = _new_axes("Hexapolar  (Samp = 5)")
    samp = 5
    pts = hexapolar_points(samp)
    for j in range(1, samp + 1):
        ax.add_patch(Circle((0.0, 0.0), j / float(samp), fill=False, edgecolor=GREY,
                            linewidth=0.4, linestyle=(0, (2, 3))))
    xs, ys = zip(*pts)
    _scatter(ax, xs, ys, size=10)
    ax.text(0.0, -1.08, f"$N = 1 + 3\\cdot {samp}\\cdot {samp + 1} = {1 + 3 * samp * (samp + 1)}$",
            ha="center", va="top", fontsize=9)
    _save(fig, "04_hexapolar.svg")


# ---------------------------------------------------------------------------
# 05 — square grid clipped to disk
# ---------------------------------------------------------------------------
def fig_square_grid() -> None:
    fig, ax = _new_axes("Square grid clipped to disk  (Samp = 6)")
    samp = 6
    coords = np.linspace(-1.0, 1.0, 2 * samp + 1)
    xs, ys = np.meshgrid(coords, coords)
    xs = xs.flatten()
    ys = ys.flatten()
    mask = xs ** 2 + ys ** 2 <= 1.0 + 1e-9
    _scatter(ax, xs[mask], ys[mask], size=10)
    # show the bounding square
    ax.plot([-1, 1, 1, -1, -1], [-1, -1, 1, 1, -1], color=GREY, linewidth=0.5, linestyle=(0, (3, 3)))
    _save(fig, "05_square_grid.svg")


# ---------------------------------------------------------------------------
# 06 — random disk
# ---------------------------------------------------------------------------
def fig_random_disk() -> None:
    fig, ax = _new_axes("Uniform random disk  (N = 200)")
    rng = np.random.default_rng(42)
    n = 200
    pts: list[tuple[float, float]] = []
    while len(pts) < n:
        x = rng.uniform(-1.0, 1.0)
        y = rng.uniform(-1.0, 1.0)
        if x * x + y * y <= 1.0:
            pts.append((x, y))
    xs, ys = zip(*pts)
    _scatter(ax, xs, ys, size=8)
    _save(fig, "06_random_disk.svg")


# ---------------------------------------------------------------------------
# 07 — Vogel / golden-angle spiral with the angle annotation
# ---------------------------------------------------------------------------
def vogel_points(n: int, radius: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    idx = np.arange(n)
    r = radius * np.sqrt(idx / float(max(n - 1, 1)))
    theta = idx * GOLDEN_ANGLE
    return r * np.cos(theta), r * np.sin(theta)


def fig_vogel_overview() -> None:
    fig, ax = _new_axes("Vogel / golden-angle spiral  (N = 300)", size=4.5)
    xs, ys = vogel_points(300)
    _scatter(ax, xs, ys, size=10)
    # highlight the first ~14 points and the 137.5° turn
    n_hi = 14
    xs_hi, ys_hi = vogel_points(n_hi)
    ax.plot(xs_hi, ys_hi, color=ACCENT_COLOUR, linewidth=1.0)
    ax.scatter(xs_hi, ys_hi, s=18, c=ACCENT_COLOUR, zorder=4)
    ax.text(0.0, -1.08,
            r"$\theta_i = i \cdot 137.508^\circ$,  $r_i = \sqrt{i/N}$",
            ha="center", va="top", fontsize=9)
    _save(fig, "07_vogel_spiral.svg")


# ---------------------------------------------------------------------------
# 08 — golden-angle geometry (why ~137.5°?)
# ---------------------------------------------------------------------------
def fig_golden_angle() -> None:
    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    ax.set_aspect("equal")
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-1.25, 1.25)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.add_patch(Circle((0.0, 0.0), 1.0, fill=False, edgecolor=RING_COLOUR, linewidth=1.2))
    # arc from 0 to 137.508° (the golden angle)
    theta = np.linspace(0.0, GOLDEN_ANGLE, 200)
    ax.plot(np.cos(theta), np.sin(theta), color=ACCENT_COLOUR, linewidth=2.2)
    # the rest of the circumference in grey
    theta_rest = np.linspace(GOLDEN_ANGLE, 2 * math.pi, 200)
    ax.plot(np.cos(theta_rest), np.sin(theta_rest), color=GREY, linewidth=1.2,
            linestyle=(0, (4, 3)))
    # radii at 0 and at golden angle
    ax.plot([0, 1], [0, 0], color=ACCENT_COLOUR, linewidth=1.0)
    ax.plot([0, math.cos(GOLDEN_ANGLE)], [0, math.sin(GOLDEN_ANGLE)], color=ACCENT_COLOUR,
            linewidth=1.0)
    ax.scatter([1, math.cos(GOLDEN_ANGLE)], [0, math.sin(GOLDEN_ANGLE)],
               s=22, c=ACCENT_COLOUR, zorder=4)
    # labels
    ax.text(0.55, 0.42, r"$\alpha \approx 137.508^\circ$", color=ACCENT_COLOUR, fontsize=10)
    ax.text(0.05, -0.6, r"$\alpha = 2\pi (1 - 1/\varphi)$" "\n"
                       r"$\varphi = \frac{1 + \sqrt{5}}{2}$",
            color="black", fontsize=9)
    ax.set_title("The golden angle", fontsize=11)
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT_DIR / "08_golden_angle.svg", format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {(OUT_DIR / '08_golden_angle.svg').relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# 09 — why φ? rational vs irrational angle
# ---------------------------------------------------------------------------
def fig_rational_vs_golden() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.6))
    n = 200

    def spiral(angle: float):
        idx = np.arange(n)
        r = np.sqrt(idx / float(n))
        th = idx * angle
        return r * np.cos(th), r * np.sin(th)

    titles_angles = [
        (r"$\alpha = 360^\circ / 7$  (rational)", 2 * math.pi / 7.0, "#b07a00"),
        (r"$\alpha = 360^\circ / \pi$  (mild irrational)", 2 * math.pi / math.pi, "#6b6bb0"),
        (r"$\alpha = 2\pi/\varphi^{2}$  (golden)", GOLDEN_ANGLE, ACCENT_COLOUR),
    ]
    for ax, (title, angle, colour) in zip(axes, titles_angles):
        ax.set_aspect("equal")
        ax.set_xlim(-1.15, 1.15)
        ax.set_ylim(-1.15, 1.15)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.add_patch(Circle((0.0, 0.0), 1.0, fill=False, edgecolor=RING_COLOUR, linewidth=1.0))
        x, y = spiral(angle)
        ax.scatter(x, y, s=10, c=colour)
        ax.set_title(title, fontsize=10)
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT_DIR / "09_rational_vs_golden.svg", format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {(OUT_DIR / '09_rational_vs_golden.svg').relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# 10 — nearest-neighbour distance histogram: random vs hexapolar vs Vogel
# ---------------------------------------------------------------------------
def _nearest_neighbour(points: np.ndarray) -> np.ndarray:
    """Return the nearest-neighbour distance for every point (brute force, N≤500)."""
    n = points.shape[0]
    dists = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
    np.fill_diagonal(dists, np.inf)
    return dists.min(axis=1)


def fig_nearest_neighbour() -> None:
    n_target = 300
    # Vogel
    xv, yv = vogel_points(n_target)
    vogel = np.column_stack((xv, yv))
    # Random
    rng = np.random.default_rng(2026)
    rand_pts: list[tuple[float, float]] = []
    while len(rand_pts) < n_target:
        x = rng.uniform(-1.0, 1.0)
        y = rng.uniform(-1.0, 1.0)
        if x * x + y * y <= 1.0:
            rand_pts.append((x, y))
    random_pts = np.asarray(rand_pts)
    # Hexapolar with Samp chosen so total is close to n_target
    samp = 9  # 1 + 3*9*10 = 271
    hexa = np.asarray(hexapolar_points(samp))

    nn_vogel = _nearest_neighbour(vogel)
    nn_random = _nearest_neighbour(random_pts)
    nn_hexa = _nearest_neighbour(hexa)

    fig, ax = plt.subplots(figsize=(6.0, 3.5))
    bins = np.linspace(0.0, 0.18, 40)
    ax.hist(nn_random, bins=bins, alpha=0.55, label=f"Random ($N={len(nn_random)}$)", color="#888")
    ax.hist(nn_hexa, bins=bins, alpha=0.55, label=f"Hexapolar ($N={len(nn_hexa)}$)",
            color=RING_COLOUR)
    ax.hist(nn_vogel, bins=bins, alpha=0.65, label=f"Vogel ($N={len(nn_vogel)}$)", color=ACCENT_COLOUR)
    ax.set_xlabel("nearest-neighbour distance  (pupil radii)")
    ax.set_ylabel("count")
    ax.set_title("Spacing uniformity across samplers")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout(pad=0.5)
    fig.savefig(OUT_DIR / "10_nearest_neighbour.svg", format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {(OUT_DIR / '10_nearest_neighbour.svg').relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# 11 — Vogel lifted onto a hemisphere (Lambertian / cosine weight)
# ---------------------------------------------------------------------------
def fig_hemisphere() -> None:
    fig = plt.figure(figsize=(5.2, 4.2))
    ax = fig.add_subplot(111, projection="3d")
    n = 400
    idx = np.arange(n)
    # cosine-weighted hemisphere via golden-angle spiral
    sin2 = idx / float(n)
    cos_theta = np.sqrt(np.clip(1.0 - sin2, 0.0, 1.0))
    sin_theta = np.sqrt(sin2)
    phi = idx * GOLDEN_ANGLE
    xs = sin_theta * np.cos(phi)
    ys = sin_theta * np.sin(phi)
    zs = cos_theta
    ax.scatter(xs, ys, zs, s=8, c=ACCENT_COLOUR, depthshade=False)

    # faint reference hemisphere wireframe
    u = np.linspace(0.0, 2.0 * np.pi, 60)
    v = np.linspace(0.0, np.pi / 2.0, 30)
    uu, vv = np.meshgrid(u, v)
    xs2 = np.cos(uu) * np.sin(vv)
    ys2 = np.sin(uu) * np.sin(vv)
    zs2 = np.cos(vv)
    ax.plot_wireframe(xs2, ys2, zs2, color=GREY, linewidth=0.3, alpha=0.4)

    ax.set_box_aspect((1, 1, 0.8))
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_zlabel("")
    ax.view_init(elev=22, azim=-60)
    ax.set_title("Cosine-weighted hemisphere  (Vogel, $N = 400$)", fontsize=10)
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT_DIR / "11_hemisphere.svg", format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {(OUT_DIR / '11_hemisphere.svg').relative_to(REPO_ROOT)}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig_overview()
    fig_equal_area()
    fig_section_fans()
    fig_hexapolar()
    fig_square_grid()
    fig_random_disk()
    fig_vogel_overview()
    fig_golden_angle()
    fig_rational_vs_golden()
    fig_nearest_neighbour()
    fig_hemisphere()


if __name__ == "__main__":
    main()
