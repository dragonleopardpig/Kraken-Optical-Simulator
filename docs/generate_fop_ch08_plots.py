"""Generate the numerical SVG plots used by the Chapter 8 worked solutions."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "docs"
    / "source"
    / "_static"
    / "knowledge_base"
    / "worked_exercises"
    / "fundamentals_of_photonics"
    / "ch08"
)

BLUE = "#286f9e"
RED = "#d9485f"
PURPLE = "#7655b5"
GREEN = "#2b7a78"
GRID = "#ccd6df"


def save_svg(fig: plt.Figure, filename: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / filename
    fig.savefig(
        target,
        format="svg",
        bbox_inches="tight",
        metadata={"Date": None, "Creator": "KrakenOS documentation"},
    )
    plt.close(fig)
    # Matplotlib leaves spaces after multiline path coordinates.  Normalize
    # them so regenerated assets also pass Git's whitespace check.
    text = target.read_text(encoding="utf-8")
    target.write_text(
        "\n".join(line.rstrip() for line in text.splitlines()) + "\n",
        encoding="utf-8",
    )


def bisect_root(function, low: float, high: float) -> float:
    f_low = function(low)
    for _ in range(100):
        middle = 0.5 * (low + high)
        f_middle = function(middle)
        if f_low * f_middle <= 0:
            high = middle
        else:
            low = middle
            f_low = f_middle
    return 0.5 * (low + high)


def te0_field_plot() -> None:
    d = 0.5
    u = 0.4108277307826066
    gamma = 0.7158519586602867
    ky = 2 * u / d
    normalization = 0.7792225692670375
    y = np.linspace(-3.0, 3.0, 1600)
    field = np.where(
        np.abs(y) <= d / 2,
        normalization * np.cos(ky * y),
        normalization
        * math.cos(u)
        * np.exp(-gamma * (np.abs(y) - d / 2)),
    )

    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    ax.axvspan(-d / 2, d / 2, color="#d9ecff", label="core, n₁ = 1.48")
    ax.plot(y, field, color=RED, linewidth=2.8, label="normalized TE₀ field")
    ax.axvline(-d / 2, color=BLUE, linewidth=1.4)
    ax.axvline(d / 2, color=BLUE, linewidth=1.4)
    ax.annotate(
        "evanescent tail",
        xy=(1.25, float(np.interp(1.25, y, field))),
        xytext=(1.55, 0.66),
        arrowprops={"arrowstyle": "->", "color": PURPLE},
        color=PURPLE,
    )
    ax.set(xlabel="transverse position y (µm)", ylabel="u₀(y) (µm⁻¹ᐟ²)")
    ax.set_title("Problem 8.2-5 — normalized TE₀ slab mode")
    ax.set_xlim(-3, 3)
    ax.set_ylim(0, 0.86)
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.75)
    ax.legend(loc="upper right")
    save_svg(fig, "problem_08_02_05_te0_field.svg")


def tm_mode_plot() -> None:
    critical_sine = 0.3
    index_factor = 1 / (1 - critical_sine**2)

    def rhs_scalar(sine: float) -> float:
        return index_factor * math.sqrt(critical_sine**2 / sine**2 - 1)

    roots = []
    for mode in range(3):
        def branch_difference(sine: float, branch: int = mode) -> float:
            return (
                math.tan(5 * math.pi * sine - branch * math.pi / 2)
                - rhs_scalar(sine)
            )

        roots.append(
            bisect_root(
                branch_difference,
                mode / 10 + 1e-8,
                (mode + 1) / 10 - 1e-8,
            )
        )
    roots.append(critical_sine)

    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    s_rhs = np.linspace(0.012, critical_sine, 800)
    rhs = index_factor * np.sqrt(critical_sine**2 / s_rhs**2 - 1)
    ax.plot(s_rhs, np.minimum(rhs, 8), color=RED, linewidth=2.6, label="TM phase RHS")

    for mode in range(3):
        s = np.linspace(mode / 10 + 0.001, (mode + 1) / 10 - 0.001, 450)
        lhs = np.tan(5 * np.pi * s - mode * np.pi / 2)
        valid = (lhs >= 0) & (lhs <= 8)
        ax.plot(s[valid], lhs[valid], color=BLUE, linewidth=2.0)
        root = roots[mode]
        ax.scatter([root], [rhs_scalar(root)], color=PURPLE, s=50, zorder=4)
        ax.annotate(f"m={mode}", (root, rhs_scalar(root)), xytext=(5, 7),
                    textcoords="offset points", color=PURPLE)

    ax.scatter([critical_sine], [0], color=PURPLE, s=55, zorder=4)
    ax.annotate("m=3 (cutoff)", (critical_sine, 0), xytext=(-92, 14),
                textcoords="offset points", color=PURPLE)
    ax.plot([], [], color=BLUE, linewidth=2.0, label="LHS branches")
    ax.set(xlabel="s = sin θ", ylabel="dimensionless equation value")
    ax.set_title("Problem 8.2-9 — graphical TM-mode roots")
    ax.set_xlim(0, 0.31)
    ax.set_ylim(0, 8)
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.75)
    ax.legend(loc="upper right")
    save_svg(fig, "problem_08_02_09_tm_modes.svg")


def mode_count_plot() -> None:
    c0 = 299_792_458.0
    d = 1e-4
    area = d**2
    numerical_aperture = 0.1
    frequency_thz = np.linspace(0, 400, 600)
    frequency_hz = frequency_thz * 1e12
    rectangular = (
        math.pi * area * (numerical_aperture * frequency_hz / c0) ** 2
    )
    slab = 2 * d * numerical_aperture * frequency_hz / c0

    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.plot(frequency_thz, rectangular, color=BLUE, linewidth=2.8,
            label="square guide (2-D), M ∝ ν²")
    ax.plot(frequency_thz, slab, color=GREEN, linewidth=2.4,
            label="same-width slab (1-D), M ∝ ν")
    check_frequencies = np.array([50, 100, 200, 300, 400])
    check_counts = math.pi * area * (
        numerical_aperture * check_frequencies * 1e12 / c0
    ) ** 2
    ax.scatter(check_frequencies, check_counts, color=RED, s=32, zorder=4,
               label="tabulated checks")
    ax.set(xlabel="optical frequency ν (THz)", ylabel="TE mode count M")
    ax.set_title("Problem 8.3-1 — approximate mode-count scaling")
    ax.set_xlim(0, 400)
    ax.set_ylim(0, 600)
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.75)
    ax.legend(loc="upper left")
    save_svg(fig, "problem_08_03_01_mode_count.svg")


def main() -> None:
    matplotlib.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "svg.fonttype": "none",
            "svg.hashsalt": "fop-ch08",
        }
    )
    te0_field_plot()
    tm_mode_plot()
    mode_count_plot()


if __name__ == "__main__":
    main()
