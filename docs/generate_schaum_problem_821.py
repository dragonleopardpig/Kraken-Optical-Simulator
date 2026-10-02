"""Draw the three-hole convolution construction for Schaum Problem 8.21."""

from __future__ import annotations

import argparse
from collections import Counter
from io import StringIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

OUTPUT = (
    Path(__file__).resolve().parent
    / "source/_static/knowledge_base/worked_exercises/schaum_optics/problem_8_21"
)
F_CENTRES = ((0, 2), (-1, -1), (1, -1))
H_CENTRES = tuple((-point[0], -point[1]) for point in F_CENTRES)
COLOURS = ("#2563a6", "#087f8c", "#c87916")
plt.rcParams.update(
    {
        "font.size": 12,
        "svg.fonttype": "none",
        "svg.hashsalt": "schaum-problem-8-21",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def pair_sum_counts() -> Counter:
    return Counter(
        (first[0] + second[0], first[1] + second[1])
        for first in F_CENTRES
        for second in H_CENTRES
    )


def coordinates(points):
    return np.asarray(points, dtype=float) * (1, 1 / np.sqrt(3))


def shadow_ray_hits(source_points, aperture_points, source_distance, screen_distance):
    ratio = screen_distance / source_distance
    return np.asarray(
        [
            (1 + ratio) * aperture - ratio * source
            for source in source_points
            for aperture in aperture_points
        ]
    )


def panel(axis, title, extent):
    axis.set(title=title, xlim=(-extent, extent), ylim=(-extent, extent))
    axis.set_aspect("equal")
    axis.axhline(0, color="#d4dce5", linewidth=0.8, zorder=0)
    axis.axvline(0, color="#d4dce5", linewidth=0.8, zorder=0)
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.text(extent - 0.1, -0.14, "$x$", ha="right", color="#556575")
    axis.text(0.12, extent - 0.1, "$y$", va="top", color="#556575")


def outline(axis, points, colour):
    closed = np.vstack((points, points[0]))
    axis.plot(closed[:, 0], closed[:, 1], "--", color=colour, linewidth=1.5)


def draw_masks():
    figure, axes = plt.subplots(1, 2, figsize=(9.6, 4.4), layout="constrained")
    for axis, centres, labels, title, colour in zip(
        axes,
        (F_CENTRES, H_CENTRES),
        (("A", "B", "C"), ("A'", "B'", "C'")),
        ("First mask: f(x, y)", "Second mask: h(x, y)"),
        COLOURS,
    ):
        panel(axis, title, 1.65)
        points = coordinates(centres)
        outline(axis, points, colour)
        axis.scatter(
            points[:, 0],
            points[:, 1],
            s=240,
            facecolors="white",
            edgecolors=colour,
            linewidths=2,
            zorder=3,
        )
        axis.plot(0, 0, "+", color="#556575", markersize=12)
        axis.annotate("origin", (0, 0), xytext=(10, -18), textcoords="offset points")
        for position, label in zip(points, labels):
            axis.annotate(
                label,
                position,
                xytext=(13, 10),
                textcoords="offset points",
                color=colour,
                weight="bold",
            )
    return figure


def draw_construction():
    figure, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), layout="constrained")
    panel(axes[0], "Place one copy of h at each f hole", 2.65)
    panel(axes[1], "Add the contributions: f * h", 2.65)
    for centre, label, colour in zip(F_CENTRES, ("A", "B", "C"), COLOURS):
        anchor = coordinates([centre])[0]
        points = coordinates(H_CENTRES) + anchor
        outline(axes[0], points, colour)
        axes[0].scatter(
            points[:, 0],
            points[:, 1],
            s=240,
            facecolors="none",
            edgecolors=colour,
            linewidths=2,
            zorder=3,
        )
        axes[0].plot(*anchor, "+", color=colour, markersize=12, markeredgewidth=2)
        axes[0].annotate(
            label,
            anchor,
            xytext=(10, 0),
            textcoords="offset points",
            color=colour,
            weight="bold",
        )
    axes[0].annotate(
        "three copies meet",
        (0, 0),
        xytext=(0, 17),
        textcoords="offset points",
        ha="center",
        fontsize=10,
    )
    for position, weight in sorted(pair_sum_counts().items()):
        location = coordinates([position])[0]
        axes[1].scatter(
            *location,
            s=700 if weight == 3 else 370,
            facecolors="#2563a6" if weight == 3 else "#e9f1fa",
            edgecolors="#2563a6",
            linewidths=2,
            zorder=3,
        )
        axes[1].text(
            *location,
            str(weight),
            ha="center",
            va="center",
            color="white" if weight == 3 else "#193047",
            weight="bold",
            zorder=4,
        )
    return figure


def draw_bench():
    figure, axes = plt.subplots(1, 3, figsize=(12.6, 4.7), layout="constrained")
    figure.suptitle(
        "LED + diffuser → source mask → 100 mm → aperture mask → 100 mm → screen",
        fontsize=12,
    )
    source_points = -2 * coordinates(F_CENTRES)
    aperture_points = coordinates(H_CENTRES)
    titles = (
        "Source mask: rotated f\n16 mm hole-centre spacing",
        "Aperture mask: h\n8 mm hole-centre spacing",
        "Screen: enlarged f * h\nouter radius 16 mm",
    )
    for axis, title in zip(axes, titles):
        panel(axis, title, 4.4)
    for axis, points, colour in zip(axes, (source_points, aperture_points), COLOURS):
        outline(axis, points, colour)
        axis.scatter(
            points[:, 0],
            points[:, 1],
            s=160,
            facecolors="white",
            edgecolors=colour,
            linewidths=2,
            zorder=3,
        )
        axis.plot(0, 0, "+", color="#556575", markersize=10)
    hits = shadow_ray_hits(source_points, aperture_points, 100, 100)
    counts = Counter(tuple(point) for point in np.round(hits, 12))
    for location, weight in counts.items():
        axes[2].scatter(
            *location,
            s=550 if weight == 3 else 260,
            facecolors="#2563a6" if weight == 3 else "#e9f1fa",
            edgecolors="#2563a6",
            linewidths=2,
            zorder=3,
        )
        axes[2].text(
            *location,
            str(weight),
            ha="center",
            va="center",
            color="white" if weight == 3 else "#193047",
            weight="bold",
            zorder=4,
        )
    return figure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-dir", type=Path)
    arguments = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if arguments.preview_dir:
        arguments.preview_dir.mkdir(parents=True, exist_ok=True)
    for name, figure in (
        ("masks", draw_masks()),
        ("construction", draw_construction()),
        ("bench", draw_bench()),
    ):
        svg_content = StringIO()
        figure.savefig(svg_content, format="svg", metadata={"Date": None})
        clean_svg = "\n".join(
            line.rstrip() for line in svg_content.getvalue().splitlines()
        )
        (OUTPUT / f"{name}.svg").write_text(clean_svg + "\n", encoding="utf-8")
        if arguments.preview_dir:
            figure.savefig(arguments.preview_dir / f"{name}.png", dpi=160)
        plt.close(figure)
    print(f"Generated Problem 8.21 illustrations in {OUTPUT}")


if __name__ == "__main__":
    main()
