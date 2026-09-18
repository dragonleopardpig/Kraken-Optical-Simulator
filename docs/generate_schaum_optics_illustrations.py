"""Generate reproducible, mathematically constructed Schaum optics SVG figures."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle, Wedge
from scipy.optimize import brentq
from scipy.special import fresnel, j1

from schaum_optics_worked.illustrations import PROBLEMS, TOPICS, figure_name


OUTPUT = (
    Path(__file__).resolve().parent
    / "source/_static/knowledge_base/worked_exercises/schaum_optics"
)
BLUE, TEAL, ORANGE, RED, PURPLE = "#2563a6", "#087f8c", "#c87916", "#b83749", "#7856a6"
plt.rcParams.update(
    {
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": matplotlib.cycler(color=[BLUE, ORANGE, TEAL, PURPLE, RED]),
        "svg.fonttype": "none",
        "svg.hashsalt": "schaum-optics-worked-v1",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "lines.linewidth": 2,
        "legend.fontsize": 9,
    }
)


def canvas(title: str, panels: int = 2):
    figure, axes = plt.subplots(
        1, panels, figsize=(11.2, 4.4), layout="constrained", squeeze=False
    )
    figure.suptitle(title, fontsize=15, fontweight="bold", color="#193047")
    return figure, axes[0]


def graph(axis, xlabel: str, ylabel: str, title: str = "") -> None:
    axis.set(xlabel=xlabel, ylabel=ylabel, title=title)
    axis.grid(alpha=0.18)


def diagram(axis, limits=(-1, 5, -2, 2), equal=False) -> None:
    axis.set(xlim=limits[:2], ylim=limits[2:])
    axis.axis("off")
    if equal:
        axis.set_aspect("equal")


def arrow(axis, start, end, color=BLUE, label=None) -> None:
    axis.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={"arrowstyle": "->", "color": color, "lw": 2},
    )
    if label:
        midpoint = (np.asarray(start) + end) / 2
        axis.annotate(
            label,
            midpoint,
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            color=color,
        )


def ray(axis, points, color=BLUE, dashed=False) -> None:
    points = np.asarray(points)
    axis.plot(points[:, 0], points[:, 1], "--" if dashed else "-", color=color, lw=1.6)
    if not dashed:
        start, end = points[-2:]
        arrow(axis, start + 0.38 * (end - start), start + 0.58 * (end - start), color)


def annotate(axis, position, label, offset=(5, 7), color="#24384b") -> None:
    axis.annotate(
        label,
        position,
        xytext=offset,
        textcoords="offset points",
        color=color,
        fontsize=10,
    )


def lens(axis, position, height=1.4, color=TEAL) -> None:
    axis.annotate(
        "",
        xy=(position, height),
        xytext=(position, -height),
        arrowprops={"arrowstyle": "<->", "color": color, "lw": 2},
    )


def impulses(axis, positions, weights, color=BLUE) -> None:
    for position, weight in zip(positions, weights):
        arrow(axis, (position, 0), (position, weight), color)
        annotate(axis, (position, weight), str(weight), offset=(-3, 5), color=color)
    axis.axhline(0, color="#82909e", lw=0.8)
    axis.set_xlim(min(positions) - 0.65, max(positions) + 0.65)
    axis.set_ylim(min(0, min(weights)) - 0.25, max(weights) + 0.65)


def triangle(coordinate):
    return np.maximum(1 - np.abs(coordinate), 0)


def array_factor(coordinate, count):
    phase = 2 * np.pi * np.asarray(coordinate)
    return (
        np.abs(np.exp(1j * np.outer(phase, np.arange(count))).sum(axis=1) / count) ** 2
    )


def fresnel_power(angle, incident=1.0, transmitted=1.5):
    cosine_i = np.cos(angle)
    cosine_t = np.sqrt(1 - (incident / transmitted * np.sin(angle)) ** 2 + 0j)
    reflect_s = (incident * cosine_i - transmitted * cosine_t) / (
        incident * cosine_i + transmitted * cosine_t
    )
    reflect_p = (transmitted * cosine_i - incident * cosine_t) / (
        transmitted * cosine_i + incident * cosine_t
    )
    return np.abs(reflect_s) ** 2, np.abs(reflect_p) ** 2


def generate_waves(save):
    coordinate = np.linspace(-5, 5, 600)
    figure, axes = canvas("Travelling profiles: shape and direction")
    for axis, direction, label in zip(
        axes, [1, -1], [r"$F(x-vt)$ moves right", r"$F(x+vt)$ moves left"]
    ):
        axis.plot(coordinate, np.exp(-(coordinate**2)), label="t = 0")
        axis.plot(
            coordinate, np.exp(-((coordinate - 2 * direction) ** 2)), label="later time"
        )
        arrow(axis, (0, 1.15), (2 * direction, 1.15), TEAL)
        graph(axis, "position x (relative units)", "displacement / amplitude", label)
        axis.set_ylim(-0.05, 1.35)
        axis.legend(loc="upper left")
    save("1-1", figure)

    figure, axes = canvas("Wavelength and period are different measurements")
    position = np.linspace(0, 3, 600)
    time = np.linspace(0, 8, 600)
    axes[0].plot(position, np.cos(2 * np.pi * position))
    axes[0].annotate(
        "", (2, 1.15), (1, 1.15), arrowprops={"arrowstyle": "<->", "color": TEAL}
    )
    annotate(axes[0], (1.45, 1.15), r"$\lambda$", (0, 5))
    axes[0].set_ylim(-1.3, 1.45)
    axes[1].plot(time, -3 * np.sin(np.pi * time / 4))
    axes[1].scatter([0, 2, 4, 6, 8], [0, -3, 0, 3, 0], color=ORANGE, zorder=3)
    graph(
        axes[0],
        r"position / $\lambda$",
        "normalized displacement",
        "Snapshot at a fixed time",
    )
    graph(
        axes[1], "time (s)", "displacement (source units)", "Problem 1.43: period = 8 s"
    )
    save("1-2", figure)

    figure, axes = canvas("Following a crest: constant phase fixes its trajectory")
    time = np.linspace(0, 4, 100)
    for offset in [-1, 0, 1]:
        axes[0].plot(time, time + offset, label=f"crest offset {offset}")
    axes[1].plot(time, time, label="v = 1")
    axes[1].plot(time, 2 * time, label="v = 2")
    for axis in axes:
        graph(axis, "time (relative units)", "crest position (relative units)")
        axis.legend()
    save("1-3", figure)

    figure, axes = canvas("Phasors convert harmonic addition into vector addition")
    for axis in axes:
        axis.axhline(0, color="#9ba9b6", lw=0.8)
        axis.axvline(0, color="#9ba9b6", lw=0.8)
        axis.set_aspect("equal")
        graph(axis, "real component", "imaginary component")
    arrow(axes[0], (0, 0), (2, 1), BLUE, "first phasor")
    arrow(axes[0], (2, 1), (-1, 2), ORANGE, "second phasor")
    arrow(axes[0], (0, 0), (-1, 2), TEAL)
    axes[0].set(xlim=(-2, 3), ylim=(-0.8, 3), title="Head-to-tail construction")
    arrow(axes[1], (0, 0), (-1, 2), TEAL, r"$A e^{i\phi}$")
    axes[1].plot([-1, -1, 0], [0, 2, 2], "--", color="#7c8996", lw=1)
    axes[1].set(
        xlim=(-2, 3), ylim=(-0.8, 3), title=r"$A=\sqrt{5},\quad \phi=116.6^\circ$"
    )
    save("1-4", figure)

    figure, axes = canvas("Plane and spherical phase fronts")
    for axis in axes:
        diagram(axis, (-3.4, 3.4, -2.8, 2.8), equal=True)
    for position in np.arange(-2.5, 3, 1):
        axes[0].plot([position, position], [-2, 2], color=BLUE)
    arrow(axes[0], (-2.5, 0), (2.5, 0), ORANGE, r"wave vector $\mathbf{k}$")
    for radius in [0.6, 1.2, 1.8, 2.4]:
        axes[1].add_patch(Circle((0, 0), radius, fill=False, edgecolor=BLUE))
    for angle in np.arange(0, 360, 60):
        direction = np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])
        arrow(axes[1], direction * 0.6, direction * 2.6, ORANGE)
    axes[0].set_title(r"$\mathbf{k}\cdot\mathbf{r}-\omega t=\mathrm{constant}$")
    axes[1].set_title(r"$kr-\omega t=\mathrm{constant}$; amplitude falls as $1/r$")
    save("1-5", figure)


def generate_fields(save):
    figure, axes = canvas("A vacuum electromagnetic wave is transverse")
    position = np.linspace(0, 2, 500)
    axes[0].plot(position, np.cos(2 * np.pi * position), label=r"$E/E_0$")
    axes[0].plot(position, np.cos(2 * np.pi * position), "--", label=r"$cB/E_0$")
    graph(
        axes[0],
        r"position / $\lambda$",
        "normalized field",
        "Fields oscillate in phase",
    )
    axes[0].legend()
    diagram(axes[1], (-1.8, 2.8, -1.8, 2.8), equal=True)
    arrow(axes[1], (0, 0), (2, 0), BLUE, "E along x")
    arrow(axes[1], (0, 0), (0, 2), TEAL)
    annotate(axes[1], (0, 2), "B along y")
    axes[1].add_patch(Circle((0, 0), 0.17, fill=False, color=ORANGE))
    axes[1].plot(0, 0, ".", color=ORANGE)
    annotate(axes[1], (0, -0.7), "E × B: +z, toward viewer", (-60, 0), ORANGE)
    save("2-1", figure)

    figure, axes = canvas("Refraction changes wavelength, not frequency")
    position = np.linspace(-2, 2, 900)
    phase = np.where(position < 0, 2 * np.pi * position, 3 * np.pi * position)
    axes[0].plot(position, np.cos(phase))
    axes[0].axvline(0, color=ORANGE, label="interface")
    graph(
        axes[0],
        "position (vacuum wavelengths)",
        "normalized field",
        "Schematic transmitted phase; amplitudes normalized",
    )
    axes[0].legend()
    axes[1].bar([0, 1, 2], [1, 1, 1], width=0.35, label="n = 1", color=BLUE)
    axes[1].bar(
        np.array([0, 1, 2]) + 0.35,
        [2 / 3, 2 / 3, 1],
        width=0.35,
        label="n = 1.5",
        color=TEAL,
    )
    axes[1].set_xticks([0.175, 1.175, 2.175], ["speed", "wavelength", "frequency"])
    graph(axes[1], "quantity", "ratio to vacuum value")
    axes[1].legend()
    save("2-2", figure)

    figure, axes = canvas("Irradiance averages the square of the field")
    phase = np.linspace(0, 4 * np.pi, 700)
    axes[0].plot(phase / (2 * np.pi), np.cos(phase), label=r"$E/E_0$")
    axes[1].plot(phase / (2 * np.pi), np.cos(phase) ** 2, label=r"$E^2/E_0^2$")
    axes[1].axhline(0.5, color=ORANGE, ls="--", label="time average = 1/2")
    for axis in axes:
        graph(axis, "time / period", "normalized value")
        axis.legend()
    save("2-3", figure)

    figure, axes = canvas("Photon momentum and radiation pressure")
    for axis, title in zip(axes, ["Absorber", "Perfect reflector"]):
        diagram(axis, (-0.5, 4, -1.6, 1.8))
        axis.add_patch(Rectangle((2.5, -1.25), 0.25, 2.5, color="#b9c6d2"))
        arrow(axis, (0, 0.5), (2.5, 0.5), BLUE, r"incoming $p=h/\lambda$")
        axis.set_title(title)
    annotate(axes[0], (0.3, -0.6), r"$\Delta p_{\rm surface}=p$", (0, 0))
    annotate(axes[0], (0.3, -1.1), r"$P_{\rm radiation}=I/c$", (0, 0))
    arrow(axes[1], (2.5, -0.25), (0, -0.25), ORANGE)
    annotate(axes[1], (0.3, -0.8), r"$\Delta p_{\rm surface}=2p$", (0, 0))
    annotate(axes[1], (0.3, -1.3), r"$P_{\rm radiation}=2I/c$", (0, 0))
    save("2-4", figure)

    figure, axes = canvas(
        "One spectrum: reciprocal wavelength and photon energy", panels=1
    )
    wavelength = np.logspace(-12, 1, 600)
    axes[0].loglog(wavelength, 1.239841984e-6 / wavelength)
    axes[0].axvspan(
        400e-9, 700e-9, color=TEAL, alpha=0.2, label="400–700 nm visible interval"
    )
    for label, location in [
        ("X-ray", 1e-10),
        ("UV", 1e-7),
        ("IR", 1e-5),
        ("microwave", 0.01),
        ("radio", 1),
    ]:
        annotate(axes[0], (location, 1.239841984e-6 / location), label, (5, 13))
    graph(axes[0], "vacuum wavelength (m)", "photon energy (eV)")
    axes[0].legend()
    save("2-5", figure)


def generate_interfaces(save):
    figure, axes = canvas(
        "Parallel plate: same emerging direction, shifted ray", panels=1
    )
    axis = axes[0]
    diagram(axis, (-2.5, 4.5, -3, 2.8), equal=True)
    axis.add_patch(Rectangle((0, -3), 1.4, 6, color="#dfedf5"))
    angle_i = np.deg2rad(45)
    angle_t = np.arcsin(np.sin(angle_i) / 1.5)
    exit_height = -1.4 * np.tan(angle_t)
    ray(axis, [(-2, 2), (0, 0), (1.4, exit_height), (3.4, exit_height - 2)])
    ray(axis, [(0, 0), (2.5, -2.5)], color=ORANGE, dashed=True)
    foot = ((1.4 - exit_height) / 2, (exit_height - 1.4) / 2)
    axis.annotate(
        "",
        (1.4, exit_height),
        foot,
        arrowprops={"arrowstyle": "<->", "color": TEAL, "lw": 1.5},
    )
    annotate(axis, (1.15, -0.95), "a", (5, -8), TEAL)
    axis.plot([-1, 2], [0, 0], ":", color="#82909e")
    annotate(axis, (0.3, 2), "glass n = 1.5")
    annotate(axis, (-1.8, 1.8), "air")
    annotate(axis, (2.1, -1), "emerging ray")
    annotate(axis, (0.4, -0.2), r"$\theta_t$", (0, 0))
    annotate(axis, (-0.75, 0.3), r"$\theta_i$")
    axis.annotate(
        "", (1.4, 1.4), (0, 1.4), arrowprops={"arrowstyle": "<->", "color": TEAL}
    )
    annotate(axis, (0.55, 1.4), "d")
    save("3-1", figure)

    figure, axes = canvas("Stationary optical path selects the refraction point")
    crossing = np.linspace(-0.3, 3.5, 400)
    optical_path = np.sqrt(crossing**2 + 4) + 1.5 * np.sqrt((3 - crossing) ** 2 + 2.25)
    optimum = brentq(
        lambda value: (
            value / np.sqrt(value**2 + 4)
            - 1.5 * (3 - value) / np.sqrt((3 - value) ** 2 + 2.25)
        ),
        0,
        3,
    )
    diagram(axes[0], (-0.5, 3.8, -2.1, 2.6), equal=True)
    axes[0].axhline(0, color=TEAL)
    for value in [0.4, optimum, 3.2]:
        ray(
            axes[0],
            [(0, 2), (value, 0), (3, -1.5)],
            color=BLUE if value == optimum else "#adb8c2",
        )
    annotate(axes[0], (0, 2), "source")
    annotate(axes[0], (3, -1.5), "receiver", (-50, -20))
    annotate(axes[0], (0, -0.8), "n = 1.5")
    annotate(axes[0], (0, 0.5), "n = 1")
    axes[1].plot(crossing, optical_path)
    axes[1].axvline(optimum, color=ORANGE, ls="--", label="Snell stationary point")
    graph(axes[1], "interface crossing x", "optical path (relative units)")
    axes[1].legend()
    save("3-2", figure)

    angle = np.linspace(0, np.pi / 2 - 0.0001, 800)
    for key, indices, title in [
        ("3-3", (1, 1.5), "External reflection: Brewster cancellation"),
        ("3-4", (1.5, 1), "Internal reflection: the critical-angle boundary"),
    ]:
        figure, axes = canvas(title, panels=1)
        reflect_s, reflect_p = fresnel_power(angle, *indices)
        axes[0].plot(np.rad2deg(angle), reflect_s, label="s power reflectance")
        axes[0].plot(np.rad2deg(angle), reflect_p, label="p power reflectance")
        critical = (
            np.rad2deg(np.arcsin(1 / 1.5))
            if key == "3-4"
            else np.rad2deg(np.arctan(1.5))
        )
        axes[0].axvline(
            critical,
            color=TEAL,
            ls="--",
            label=f"{'critical' if key == '3-4' else 'Brewster'} angle = {critical:.2f}°",
        )
        if key == "3-4":
            axes[0].axvspan(critical, 90, color=TEAL, alpha=0.08)
        graph(
            axes[0],
            "incidence angle from normal (degrees)",
            "reflected / incident power",
        )
        axes[0].set(xlim=(0, 90), ylim=(-0.025, 1.05))
        axes[0].legend(loc="upper left")
        save(key, figure)


def generate_imaging(save):
    figure, axes = canvas("A Cartesian oval equalizes optical path", panels=1)
    axis = axes[0]
    diagram(axis, (-3.7, 4.7, -1.4, 1.6), equal=True)
    heights = np.linspace(-1, 1, 101)
    surface = [
        brentq(
            lambda position: (
                np.hypot(position + 3, height)
                + 1.5 * np.hypot(4 - position, height)
                - 9
            ),
            0,
            1.7,
        )
        for height in heights
    ]
    axis.plot(surface, heights, color=TEAL, lw=3)
    for height in [-0.9, -0.45, 0, 0.45, 0.9]:
        position = brentq(
            lambda value: (
                np.hypot(value + 3, height) + 1.5 * np.hypot(4 - value, height) - 9
            ),
            0,
            1.7,
        )
        ray(axis, [(-3, 0), (position, height), (4, 0)], color=BLUE)
    annotate(axis, (-3, 0), "S", (-8, -20))
    annotate(axis, (4, 0), "P", (5, -20))
    annotate(axis, (-1.5, 1.1), "n = 1; source distance 3")
    annotate(axis, (1, 1.1), "n = 1.5; image distance 4")
    annotate(
        axis, (-1.5, -1.35), "Every drawn ray has optical path 9 (relative units)."
    )
    save("4-1", figure)

    figure, axes = canvas("Spherical refraction: Problem 4.68", panels=1)
    axis = axes[0]
    diagram(axis, (-48, 90, -15, 18))
    axis.axhline(0, color="#8a99a8", lw=0.8)
    heights = np.linspace(-10, 10, 100)
    axis.plot(20 - np.sqrt(400 - heights**2), heights, color=TEAL, lw=3)
    for height in [-7, 0, 7]:
        position = 20 - np.sqrt(400 - height**2)
        ray(axis, [(-40, 0), (position, height), (80, 0)])
    axis.scatter([-40, 0, 20, 80], [0, 0, 0, 0], color=ORANGE)
    for position, label in [
        (-40, "object"),
        (0, "vertex"),
        (20, "C: R = +20 cm"),
        (80, "image"),
    ]:
        annotate(axis, (position, 0), label, (-15, -20))
    annotate(axis, (-30, 12), "n = 1; object distance 40 cm")
    annotate(axis, (25, 12), "n = 2; image distance 80 cm")
    annotate(
        axis, (-30, -12), "Paraxial conjugates: spherical aberration is not included."
    )
    save("4-2", figure)

    figure, axes = canvas("Thin-lens real imaging: three principal rays", panels=1)
    axis = axes[0]
    diagram(axis, (-3.5, 2.5, -1.5, 1.7), equal=True)
    axis.axhline(0, color="#8a99a8", lw=0.8)
    lens(axis, 0)
    arrow(axis, (-3, 0), (-3, 1), TEAL)
    arrow(axis, (1.5, 0), (1.5, -0.5), RED)
    ray(axis, [(-3, 1), (0, 1), (1.5, -0.5)], BLUE)
    ray(axis, [(-3, 1), (0, 0), (1.5, -0.5)], ORANGE)
    ray(axis, [(-3, 1), (0, -0.5), (1.5, -0.5)], PURPLE)
    axis.scatter([-1, 1], [0, 0], color=TEAL)
    annotate(axis, (-1, 0), "F", (-5, -20))
    annotate(axis, (1, 0), "F′", (-5, 8))
    annotate(axis, (-3, 1), "object: 3f")
    annotate(axis, (1.5, -0.5), "image: 1.5f", (-55, -25))
    save("4-3", figure)

    figure, axes = canvas(
        "Two lenses: track signed conjugates, not just distances", panels=1
    )
    axis = axes[0]
    diagram(axis, (-20, 120, -22, 9))
    axis.axhline(0, color="#8a99a8", lw=0.8)
    lens(axis, 0, 6)
    lens(axis, 21, 6)
    for height, color in [(0, BLUE), (1, ORANGE), (2, TEAL)]:
        slope = (height - 1) / 12 - height / 9
        second_height = height + 21 * slope
        second_slope = slope + second_height / 18
        ray(
            axis,
            [
                (-12, 1),
                (0, height),
                (21, second_height),
                (111, second_height + 90 * second_slope),
            ],
            color,
        )
        ray(axis, [(21, second_height), (36, -3)], color, dashed=True)
    arrow(axis, (-12, 0), (-12, 1), TEAL)
    arrow(axis, (111, 0), (111, -18), RED)
    annotate(axis, (0, 6), "L1: f = +9 cm", (-30, 9))
    annotate(axis, (21, 6), "L2: f = −18 cm", (5, 9))
    annotate(axis, (36, -3), "would-be focus at 36 cm", (0, 10))
    annotate(axis, (55, -21), "Final image: 90 cm beyond L2; magnification −18")
    save("4-4", figure)

    figure, axes = canvas("Thick-lens cardinal planes: Problem 4.82", panels=1)
    axis = axes[0]
    diagram(axis, (-3.4, 5.3, -1.8, 2))
    axis.add_patch(Rectangle((0, -1.1), 2, 2.2, color="#e3edf4"))
    axis.axhline(0, color="#8a99a8", lw=0.8)
    for position, label, color in [
        (0, "V1", BLUE),
        (2, "V2", BLUE),
        (0.5, "H1", TEAL),
        (1, "H2", PURPLE),
        (-2.5, "F1", ORANGE),
        (4, "F2", ORANGE),
    ]:
        axis.axvline(
            position,
            ymin=0.2,
            ymax=0.8,
            color=color,
            ls="--" if label.startswith("H") else "-",
            lw=1.4,
        )
        annotate(
            axis,
            (position, -1.2 if label.startswith("V") else 1.2),
            label,
            (-8, 0),
            color,
        )
    for start, end, height in [(-2.5, 0.5, 1.65), (1, 4, -1.6)]:
        axis.annotate(
            "",
            (end, height),
            (start, height),
            arrowprops={"arrowstyle": "<->", "color": TEAL},
        )
        annotate(axis, ((start + end) / 2, height), "f = 3 cm", (-20, 6))
    annotate(axis, (2.6, 0.4), "BFL = 2 cm", (-10, 0))
    annotate(axis, (-2, -0.6), "FFL = 2.5 cm", (-10, 0))
    save("4-5", figure)

    figure, axes = canvas(
        "Ocular front focal planes: compare the actual lens positions"
    )
    for axis, positions, focal, title in [
        (axes[0], [0, 2], 1.5, "Huygens: f1 = 3q, f2 = q"),
        (axes[1], [0, 2 / 3], -0.25, "Ramsden: f1 = f2 = q"),
    ]:
        diagram(axis, (-0.7, 2.7, -1.6, 1.7))
        axis.axhline(0, color="#8a99a8", lw=0.8)
        for index, position in enumerate(positions, 1):
            lens(axis, position, 1)
            annotate(axis, (position, 1.1), f"L{index}", (-8, 4))
        axis.axvline(focal, ymin=0.15, ymax=0.8, color=ORANGE, ls="--")
        annotate(axis, (focal, -1.15), "front focal plane", (-50, -10), ORANGE)
        axis.set_title(title)
        annotate(axis, (-0.45, 1.4), "Coordinates in units of q")
    save("4-6", figure)

    figure, axes = canvas("Concave mirror: Problem 4.94", panels=1)
    axis = axes[0]
    diagram(axis, (-13, 1, -1.4, 1.5))
    axis.axhline(0, color="#8a99a8", lw=0.8)
    heights = np.linspace(-1.2, 1.2, 80)
    axis.plot(-(heights**2) / 16, heights, color=TEAL, lw=3)
    arrow(axis, (-12, 0), (-12, 1), TEAL)
    arrow(axis, (-6, 0), (-6, -0.5), RED)
    ray(axis, [(-12, 1), (0, 1), (-6, -0.5)], BLUE)
    ray(axis, [(-12, 1), (0, 0), (-6, -0.5)], ORANGE)
    axis.scatter([-8, -4], [0, 0], color=TEAL)
    annotate(axis, (-8, 0), "C", (-4, -20))
    annotate(axis, (-4, 0), "F", (-4, -20))
    annotate(axis, (-12, 1), "1 cm object")
    annotate(axis, (-6, -0.5), "0.5 cm inverted image", (-60, -25))
    annotate(axis, (-10, 1.25), "Paraxial rays; horizontal distances in cm")
    save("4-7", figure)


def polarization_axes(axis, title):
    axis.axhline(0, color="#9ba9b6", lw=0.7)
    axis.axvline(0, color="#9ba9b6", lw=0.7)
    axis.set_aspect("equal")
    axis.set(xlim=(-1.7, 1.7), ylim=(-1.7, 1.7))
    graph(axis, r"$E_x/E_0$", r"$E_y/E_0$", title)


def trajectory(axis, horizontal, vertical, color=BLUE):
    axis.plot(horizontal, vertical, color=color)
    arrow(axis, (horizontal[25], vertical[25]), (horizontal[45], vertical[45]), color)


def generate_polarization(save):
    phase = np.linspace(0, 2 * np.pi, 600)
    figure, axes = canvas("Linear polarization: components stay in phase")
    axes[0].plot(phase / (2 * np.pi), np.cos(phase) / np.sqrt(2), label="x component")
    axes[0].plot(
        phase / (2 * np.pi), np.cos(phase) / np.sqrt(2), "--", label="y component"
    )
    graph(axes[0], "time / period", "field / total peak amplitude")
    axes[0].legend()
    polarization_axes(axes[1], "The tip stays on one line")
    axes[1].plot(np.cos(phase) / np.sqrt(2), np.cos(phase) / np.sqrt(2))
    arrow(axes[1], (0, 0), (0.7, 0.7), TEAL)
    save("5-1", figure)

    figure, axes = canvas("Circular states: equal quadrature components")
    for axis, sign, title in [
        (axes[0], -1, "Source right-circular convention"),
        (axes[1], 1, "Source left-circular convention"),
    ]:
        polarization_axes(axis, title)
        trajectory(axis, np.cos(phase), sign * np.sin(phase))
        annotate(axis, (-1.5, -1.5), "Arrows show increasing time at fixed z.", (0, 0))
    save("5-2", figure)

    figure, axes = canvas("Elliptical polarization: orientation and axis ratio")
    polarization_axes(axes[0], "Equal components, relative phase −45°")
    trajectory(axes[0], np.cos(phase), np.cos(phase + np.pi / 4))
    axes[0].plot([-1.3, 1.3], [-1.3, 1.3], "--", color=ORANGE, lw=1)
    polarization_axes(axes[1], "Principal axes aligned; amplitude ratio 2:1")
    trajectory(axes[1], 1.4 * np.cos(phase), -0.7 * np.sin(phase))
    save("5-3", figure)

    figure, axes = canvas("Partial polarization: Problem 5.66", panels=1)
    angle = np.linspace(-90, 180, 700)
    output = 22 + 21 * np.cos(np.deg2rad(angle - 30)) ** 2
    axes[0].plot(angle, output, label="analyzer output")
    axes[0].axhline(
        22, color=ORANGE, ls="--", label="unpolarized contribution after analyzer"
    )
    axes[0].scatter([30, -60], [43, 22], color=TEAL, zorder=4)
    graph(axes[0], "analyzer angle right of vertical (degrees)", "irradiance (W/m²)")
    axes[0].legend(loc="upper right")
    axes[0].set_ylim(0, 50)
    save("5-4", figure)

    figure, axes = canvas("Malus projections: intermediate filters matter")
    angles = np.linspace(0, 90, 300)
    axes[0].plot(angles, np.cos(np.deg2rad(angles)) ** 2)
    graph(
        axes[0],
        "relative analyzer angle (degrees)",
        "transmitted / incident linear irradiance",
        r"$I/I_1=\cos^2\theta$",
    )
    axes[1].plot(
        [0, 1, 2, 3, 4],
        [1, 0.5, 0.375, 0.28125, 0.2109375],
        "o-",
        label="axes: 0°, 30°, 60°, 90°",
    )
    axes[1].plot([0, 1, 4], [1, 0.5, 0], "s--", label="end filters only: 0°, 90°")
    graph(
        axes[1],
        "position in filter sequence",
        "irradiance / natural input",
        "Problem 5.71",
    )
    axes[1].set_xticks([0, 1, 2, 3, 4])
    axes[1].legend()
    save("5-5", figure)

    figure, axes = canvas("Brewster reflection selects s polarization")
    diagram(axes[0], (-2.3, 2.3, -2.1, 2.1), equal=True)
    axes[0].axhline(0, color=TEAL, lw=2)
    axes[0].axvline(0, color="#9ba9b6", ls="--", lw=1)
    brewster = np.arctan(1.5)
    ray(
        axes[0],
        [
            (-2 * np.sin(brewster), 2 * np.cos(brewster)),
            (0, 0),
            (2 * np.sin(brewster), 2 * np.cos(brewster)),
        ],
    )
    ray(axes[0], [(0, 0), (2 * np.cos(brewster), -2 * np.sin(brewster))], ORANGE)
    annotate(axes[0], (-2, 1.7), "air")
    annotate(axes[0], (-2, -1.5), "glass n = 1.5")
    annotate(axes[0], (0.5, 0.5), "s reflection only")
    angle = np.linspace(0, 89.9, 600)
    reflect_s, reflect_p = fresnel_power(np.deg2rad(angle))
    axes[1].plot(angle, reflect_p, label="p reflectance")
    axes[1].axvline(np.rad2deg(brewster), color=TEAL, ls="--", label="56.31°")
    graph(axes[1], "incidence angle (degrees)", "power reflectance")
    axes[1].legend()
    save("5-6", figure)

    figure, axes = canvas("Retarders change relative phase without mixing eigenaxes")
    polarization_axes(axes[0], "45° linear → quarter-wave → circular")
    axes[0].plot(np.cos(phase), np.cos(phase), ls="--", color=ORANGE, label="before")
    trajectory(axes[0], np.cos(phase), np.sin(phase))
    axes[0].legend()
    polarization_axes(axes[1], "Circular → half-wave → opposite circular")
    trajectory(axes[1], np.cos(phase), -np.sin(phase), BLUE)
    trajectory(axes[1], 0.85 * np.cos(phase), 0.85 * np.sin(phase), ORANGE)
    annotate(
        axes[1], (-1.6, -1.55), "Radii offset only to show both rotations.", (0, 0)
    )
    save("5-7", figure)


def generate_interference(save):
    figure, axes = canvas("Two-source interference: spacing and phase steering")
    angle = np.linspace(-90, 90, 1200)
    for spacing in [0.5, 2]:
        axes[0].plot(
            angle,
            np.cos(np.pi * spacing * np.sin(np.deg2rad(angle))) ** 2,
            label=f"spacing / wavelength = {spacing}",
        )
    for shift in [0, 30]:
        axes[1].plot(
            angle,
            np.cos(2 * np.pi * np.sin(np.deg2rad(angle)) + np.deg2rad(shift) / 2) ** 2,
            label=f"source phase difference {shift}°",
        )
    for axis in axes:
        graph(axis, "angle from broadside (degrees)", r"$I/(4I_0)$")
        axis.legend(loc="lower center")
    axes[1].set_xlim(-12, 12)
    save("6-1", figure)

    figure, axes = canvas("Coherent source images and screen fringes")
    diagram(axes[0], (-0.6, 5.5, -2.2, 2.2))
    axes[0].scatter([0, 0], [-0.6, 0.6], color=TEAL, s=35)
    axes[0].plot([5, 5], [-2, 2], color="#9ba9b6", lw=3)
    for height in [-1.2, 0, 1.2]:
        ray(axes[0], [(0, -0.6), (5, height)], BLUE)
        ray(axes[0], [(0, 0.6), (5, height)], ORANGE)
    annotate(axes[0], (0, 0.6), "S1", (-20, 10))
    annotate(axes[0], (0, -0.6), "S2", (-20, -20))
    annotate(axes[0], (2, -1.9), "source separation a; screen distance L", (-65, 0))
    coordinate = np.linspace(-3, 3, 900)
    axes[1].plot(coordinate, np.cos(np.pi * coordinate) ** 2)
    graph(axes[1], r"screen coordinate $y/(\lambda L/a)$", r"$I/(4I_0)$")
    save("6-2", figure)

    figure, axes = canvas("Thin-film phase: propagation plus reflection reversal")
    diagram(axes[0], (-1.5, 3.5, -1.7, 2.3), equal=True)
    axes[0].add_patch(Rectangle((-1.5, -1), 5, 1, color="#dfedf5"))
    ray(axes[0], [(-1, 1), (0, 0), (1, 1)], BLUE)
    ray(axes[0], [(0, 0), (0.5, -1), (1, 0), (2, 1)], ORANGE)
    annotate(axes[0], (-1.3, -0.55), "film", (0, 0))
    annotate(axes[0], (0.6, 1.5), "first reflection: π shift", (-50, 0))
    annotate(axes[0], (0.8, -1.45), "round-trip OPL = 2nt cos θt", (-70, 0))
    thickness = np.linspace(0, 2, 600)
    axes[1].plot(thickness, np.sin(2 * np.pi * thickness) ** 2)
    graph(
        axes[1],
        r"optical thickness $nt\cos\theta_t/\lambda_0$",
        "normalized reflected interference factor",
    )
    axes[1].set_xticks([0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2])
    save("6-3", figure)

    figure, axes = canvas("Michelson displacement metrology")
    diagram(axes[0], (-2, 4, -1.5, 3.5), equal=True)
    ray(axes[0], [(-1.8, 0), (0, 0), (3, 0)], BLUE)
    ray(axes[0], [(0, 0), (0, 2.7)], ORANGE)
    axes[0].plot([-0.35, 0.35], [-0.35, 0.35], color=TEAL, lw=3)
    axes[0].plot([3, 3], [-0.5, 0.5], color=PURPLE, lw=4)
    axes[0].plot([-0.5, 0.5], [2.7, 2.7], color=PURPLE, lw=4)
    arrow(axes[0], (0, -0.1), (0, -1.2), TEAL)
    annotate(axes[0], (3, 0.7), "moving mirror", (-60, 0))
    annotate(axes[0], (0.2, 2.9), "fixed mirror")
    annotate(axes[0], (0.1, -1.1), "detector")
    displacement = np.linspace(0, 2, 600)
    axes[1].plot(displacement, (1 + np.cos(4 * np.pi * displacement)) / 2)
    graph(
        axes[1],
        r"mirror travel / $\lambda$",
        "normalized detector irradiance",
        "One fringe per half-wavelength travel",
    )
    save("6-4", figure)

    figure, axes = canvas("Temporal coherence: delay washes out interference")
    delay = np.linspace(-3, 3, 1400)
    visibility = np.exp(-(delay**2) / 2)
    axes[0].plot(delay, visibility)
    axes[1].plot(delay, 1 + visibility * np.cos(35 * delay), lw=1.1)
    axes[1].plot(delay, 1 + visibility, "--", color=ORANGE)
    axes[1].plot(delay, 1 - visibility, "--", color=ORANGE)
    graph(
        axes[0],
        "delay / chosen coherence scale",
        "visibility",
        "Illustrative Gaussian spectrum",
    )
    graph(axes[1], "delay / chosen coherence scale", "normalized interferogram")
    save("6-5", figure)

    figure, axes = canvas("Problem 6.52: two different geometries")
    for axis in axes:
        diagram(axis, (-2, 4.2, -0.5, 4), equal=True)
    axes[0].scatter([-1.5, 1.5], [0, 0], color=TEAL)
    axes[0].plot([0, 0], [0, 3.8], "--", color=ORANGE)
    ray(axes[0], [(-1.5, 0), (0, 2.25)], BLUE)
    ray(axes[0], [(1.5, 0), (0, 2.25)], BLUE)
    axes[0].set_title("Literal perpendicular bisector: equal paths")
    annotate(axes[0], (-1.4, 3.3), r"$\Delta r=0$: no destructive fringe", (0, 0))
    axes[1].scatter([0, 3], [0, 0], color=TEAL)
    ray(axes[1], [(0, 0), (0, 2.25)], BLUE)
    ray(axes[1], [(3, 0), (0, 2.25)], ORANGE)
    annotate(axes[1], (0, 1), "2.25 m", (-50, 0))
    annotate(axes[1], (1.4, 1), "3.75 m")
    axes[1].set_title("Line through one source: half-wave difference")
    annotate(axes[1], (-1.2, 3.3), "Path difference = 1.5 m", (0, 0))
    save("6.52", figure)


def generate_diffraction(save):
    coordinate = np.linspace(-1.3, 1.3, 2200)
    figure, axes = canvas("Coherent arrays: aperture extent sets peak width")
    for count in [2, 4, 8]:
        axes[0].plot(coordinate, array_factor(coordinate, count), label=f"N = {count}")
    axes[1].plot(coordinate, array_factor(coordinate, 8))
    axes[1].set_xlim(0, 1)
    for axis in axes:
        graph(axis, r"$a\sin\theta/\lambda$", r"$I/(N^2 I_1)$")
    axes[0].legend()
    axes[1].set_title("N = 8: seven internal zeros, six subsidiary peaks")
    save("7-1", figure)

    figure, axes = canvas("Two slits: interference inside a diffraction envelope")
    coordinate = np.linspace(-2.5, 2.5, 2500)
    envelope = np.sinc(coordinate) ** 2
    axes[0].plot(coordinate, envelope, label="single-slit envelope")
    axes[0].plot(
        coordinate,
        envelope * np.cos(4 * np.pi * coordinate) ** 2,
        label="two-slit pattern",
        lw=1.2,
    )
    axes[1].plot(
        coordinate,
        np.cos(4 * np.pi * coordinate) ** 2,
        alpha=0.5,
        label="interference factor",
    )
    axes[1].plot(
        coordinate,
        envelope * np.cos(4 * np.pi * coordinate) ** 2,
        label="envelope × interference",
    )
    axes[1].set_xlim(0.65, 1.2)
    axes[1].axvline(1, color=TEAL, ls="--", label="missing fourth order")
    for axis in axes:
        graph(axis, r"$b\sin\theta/\lambda$", "normalized irradiance")
        axis.legend()
    save("7-2", figure)

    figure, axes = canvas("Grating dispersion and finite-line resolution")
    wavelength = np.linspace(450, 650, 300)
    pitch = 25400000 / 12000
    for order in [1, 2]:
        axes[0].plot(
            wavelength,
            np.rad2deg(np.arcsin(order * wavelength / pitch)),
            label=f"order {order}",
        )
    graph(
        axes[0],
        "wavelength (nm)",
        "diffraction angle (degrees)",
        "12,000 grooves per inch",
    )
    axes[0].legend()
    offset = np.linspace(-2, 3, 1400)
    first = np.sinc(offset) ** 2
    second = np.sinc(offset - 1) ** 2
    axes[1].plot(offset, first, "--", label="line 1")
    axes[1].plot(offset, second, "--", label="line 2")
    axes[1].plot(offset, first + second, label="incoherent sum")
    graph(
        axes[1],
        "offset / first-null width",
        "relative irradiance",
        "Rayleigh-separated spectral lines",
    )
    axes[1].legend()
    save("7-3", figure)

    figure, axes = canvas("Rectangular and circular apertures: different sidelobes")
    coordinate = np.linspace(-4, 4, 900)
    axes[0].plot(coordinate, np.sinc(coordinate) ** 2, label="square: axial section")
    axes[0].plot(coordinate, np.sinc(coordinate) ** 4, label="square: diagonal section")
    radial = np.linspace(0, 5, 800)
    argument = np.pi * radial
    amplitude = np.ones_like(argument)
    np.divide(2 * j1(argument), argument, out=amplitude, where=argument != 0)
    axes[1].plot(radial, amplitude**2)
    axes[1].axvline(1.21967, color=ORANGE, ls="--", label="first zero: 1.22")
    graph(axes[0], r"$b\sin\theta/\lambda$", "normalized irradiance")
    graph(
        axes[1],
        r"$D\sin\theta/\lambda$",
        "normalized irradiance",
        "Circular pupil: Airy profile",
    )
    for axis in axes:
        axis.legend()
    save("7-4", figure)

    figure, axes = canvas("Circular Fresnel zones: add amplitudes before squaring")
    diagram(axes[0], (-2.4, 2.4, -2.4, 2.4), equal=True)
    for order in range(4, 0, -1):
        axes[0].add_patch(
            Circle(
                (0, 0),
                np.sqrt(order),
                facecolor=BLUE if order % 2 else "#dfeaf5",
                edgecolor="white",
                alpha=0.7,
            )
        )
        annotate(
            axes[0],
            (np.sqrt(order) - 0.3, 0.12),
            str(order),
            (0, 0),
            "white" if order % 2 else "#24384b",
        )
    axes[0].set_title(r"Zone boundaries: $r_m=\sqrt{m\lambda z}$")
    zones = np.linspace(0, 6, 900)
    axes[1].plot(zones, 4 * np.sin(np.pi * zones / 2) ** 2)
    graph(axes[1], r"uncovered zone count $N=r^2/(\lambda z)$", r"axial $I/I_0$")
    save("7-5", figure)

    figure, axes = canvas("Cornu spiral and straight-edge Fresnel diffraction")
    parameter = np.linspace(-5, 5, 3000)
    sine, cosine = fresnel(parameter)
    axes[0].plot(cosine, sine, lw=1.3)
    edge_sine, edge_cosine = fresnel(np.array([1.0, 1.5]))
    axes[0].plot(edge_cosine, edge_sine, "o-", color=ORANGE, label="Problem 7.99 chord")
    graph(axes[0], "C(v)", "S(v)")
    axes[0].set_aspect("equal")
    axes[0].legend()
    axes[1].plot(parameter, ((0.5 + cosine) ** 2 + (0.5 + sine) ** 2) / 2)
    axes[1].scatter([0], [0.25], color=ORANGE, zorder=4, label="edge: I/I0 = 1/4")
    graph(axes[1], "scaled distance into illuminated side v", r"$I/I_0$")
    axes[1].set_xlim(-3, 4)
    axes[1].legend()
    save("7-6", figure)

    figure, axes = canvas("Problem 7.61: full width at HALF IRRADIANCE", panels=1)
    coordinate = np.linspace(-1.3, 1.3, 900)
    axes[0].plot(coordinate, np.sinc(coordinate) ** 2)
    axes[0].axhline(0.5, color=ORANGE, ls="--", label="half irradiance")
    half = 1.39155737825151 / np.pi
    axes[0].scatter([-half, half], [0.5, 0.5], color=TEAL, zorder=3)
    axes[0].annotate(
        "",
        (half, 0.5),
        (-half, 0.5),
        arrowprops={"arrowstyle": "<->", "color": TEAL, "lw": 2},
    )
    annotate(axes[0], (0, 0.56), "FWHM = 0.885893 × λL/a", (-100, 0))
    graph(axes[0], r"$y/(\lambda L/a)$", r"$I/I(0)$")
    axes[0].legend()
    save("7.61", figure)

    for key in ["7.89", "7.91", "7.92"]:
        figure, axes = canvas(f"Problem {key}: aperture geometry and zone weights")
        axis = axes[0]
        diagram(axis, (-2.8, 2.8, -2.8, 2.8), equal=True)
        axis.add_patch(
            Rectangle(
                (-2.7, -2.7),
                5.4,
                5.4,
                facecolor="white" if key == "7.92" else "#9eafbf",
            )
        )
        color = "#647c91" if key == "7.92" else "white"
        axis.add_patch(Circle((0, 0), np.sqrt(2), facecolor=color))
        if key == "7.89":
            axis.add_patch(Wedge((0, 0), 2, 225, 315, facecolor=color))
            weights = [2, -0.5]
            labels = ["first zone", "quarter of second"]
            field = 1.5
        elif key == "7.91":
            axis.add_patch(Wedge((0, 0), np.sqrt(6), 180, 360, facecolor=color))
            weights = [1, 1]
            labels = ["upper semicircle", "lower semicircle"]
            field = 2
        else:
            for start in [-45, 135]:
                axis.add_patch(Wedge((0, 0), 2, start, start + 90, facecolor=color))
            weights = [1, -2, 1]
            labels = ["unobstructed", "block first zone", "block half second"]
            field = 0
        for radius in [np.sqrt(2), 2, np.sqrt(6)]:
            axis.add_patch(
                Circle(
                    (0, 0), radius, fill=False, edgecolor=ORANGE, linestyle="--", lw=1
                )
            )
        axis.set_title("White = transmitting; dashed circles = zone boundaries")
        axes[1].bar(
            np.arange(len(weights)), weights, color=[BLUE, ORANGE, TEAL][: len(weights)]
        )
        axes[1].set_xticks(np.arange(len(weights)), labels, rotation=12)
        graph(
            axes[1],
            "coherent contribution",
            r"field / $U_0$",
            f"Total field = {field:g}; irradiance ratio = {field**2:g}",
        )
        axes[1].axhline(0, color="#82909e", lw=1)
        save(key, figure)

    figure, axes = canvas("Problem 7.100: optimize the centred slit width", panels=1)
    parameter = np.linspace(0, 4, 1300)
    sine, cosine = fresnel(parameter)
    axes[0].plot(parameter, 2 * (sine**2 + cosine**2))
    axes[0].axhline(1, color=ORANGE, ls="--", label="unobstructed limit")
    axes[0].scatter(
        [1.2093767], [1.8014164], color=TEAL, label="largest maximum", zorder=3
    )
    graph(axes[0], "scaled half-width v", r"axial $I/I_0$")
    axes[0].legend()
    save("7.100", figure)

    figure, axes = canvas(
        "Problem 7.105: Fresnel shadow of a 1.766 mm opaque strip", panels=1
    )
    coordinate = np.linspace(-4, 4, 2400) * 1e-3
    scale = np.sqrt(2 / (693.4e-9))
    lower_sine, lower_cosine = fresnel((-0.001766 / 2 - coordinate) * scale)
    upper_sine, upper_cosine = fresnel((0.001766 / 2 - coordinate) * scale)
    intensity = (
        (1 - upper_cosine + lower_cosine) ** 2 + (1 - upper_sine + lower_sine) ** 2
    ) / 2
    axes[0].axvspan(-0.883, 0.883, color="#dfeaf5", label="geometrical shadow")
    axes[0].plot(coordinate * 1000, intensity, lw=1.3)
    axes[0].scatter([0], [0.0840462], color=ORANGE, label="axis: 0.084 I0", zorder=3)
    graph(axes[0], "screen position (mm)", r"$I/I_0$")
    axes[0].legend()
    save("7.105", figure)


def generate_fourier(save):
    figure, axes = canvas("Fourier reconstruction: source-specific waveforms")
    coordinate = np.linspace(-np.pi, np.pi, 1400)
    source = np.where(coordinate < 0, -np.pi, coordinate)
    ramp_series = np.full_like(coordinate, -np.pi / 4)
    triangle_series = np.full_like(coordinate, np.pi / 2)
    for harmonic in range(1, 32):
        ramp_series += (((-1) ** harmonic - 1) / (np.pi * harmonic**2)) * np.cos(
            harmonic * coordinate
        )
        ramp_series += ((1 - 2 * (-1) ** harmonic) / harmonic) * np.sin(
            harmonic * coordinate
        )
        triangle_series += (
            2
            * ((-1) ** harmonic - 1)
            / (np.pi * harmonic**2)
            * np.cos(harmonic * coordinate)
        )
    axes[0].plot(coordinate, source, color="#9eafbf", lw=3, label="piecewise target")
    axes[0].plot(coordinate, ramp_series, label="31-harmonic sum", lw=1.4)
    axes[1].plot(
        coordinate, np.abs(coordinate), color="#9eafbf", lw=3, label="triangular target"
    )
    axes[1].plot(coordinate, triangle_series, label="31-harmonic sum", lw=1.4)
    graph(axes[0], "x (radians)", "f(x)", "Problem 8.25: ramp and negative plateau")
    graph(axes[1], "y (radians)", "f(y)", "Problem 8.26: periodic absolute value")
    for axis in axes:
        axis.legend()
    save("8-1", figure)

    figure, axes = canvas("Transform pairs: aperture shape determines spectral shape")
    coordinate = np.linspace(-4, 4, 1200)
    axes[0].plot(
        coordinate,
        (np.abs(coordinate) < 1).astype(float) / 2,
        label="unit-area rectangle",
    )
    axes[0].plot(
        coordinate,
        np.exp(-(coordinate**2)) / np.sqrt(np.pi),
        label="unit-area Gaussian",
    )
    frequency = np.linspace(-10, 10, 1200)
    axes[1].plot(frequency, np.sinc(frequency / np.pi), label="rectangle transform")
    axes[1].plot(frequency, np.exp(-(frequency**2) / 4), label="Gaussian transform")
    graph(axes[0], "position x", "amplitude")
    graph(axes[1], "angular spatial frequency k", "Fourier amplitude")
    for axis in axes:
        axis.legend()
    save("8-2", figure)

    figure, axes = canvas("Discrete convolution counts ordered position sums")
    impulses(axes[0], [-1, 0, 1], [1, 1, 1])
    impulses(axes[1], [-2, -1, 0, 1, 2], [1, 2, 3, 2, 1], TEAL)
    graph(axes[0], "position", "impulse weight", "Input: three unit impulses")
    graph(
        axes[1],
        "position sum",
        "impulse weight",
        "Self-convolution: nine ordered pairs",
    )
    save("8-3", figure)

    figure, axes = canvas("Problem 8.42: self-convolution of four spectral lines")
    positions = [-3, -2, 2, 3]
    counts = Counter(first + second for first in positions for second in positions)
    sums = sorted(counts)
    impulses(axes[0], positions, [1] * 4)
    impulses(axes[1], sums, [counts[position] for position in sums], TEAL)
    graph(axes[0], "frequency coordinate", "impulse weight", "Input spectrum")
    graph(axes[1], "frequency coordinate", "impulse weight", "Sixteen ordered pairs")
    axes[1].set_xticks(sums)
    save("8.42", figure)

    figure, axes = canvas("Problem 8.43: a signed impulse pair shifts a rectangle")
    coordinate = np.linspace(-2, 2, 1200)
    axes[0].plot(
        coordinate,
        (np.abs(coordinate) < 0.5).astype(float),
        label="rectangle of width d = 1",
    )
    axes[0].legend()
    result = (np.abs(coordinate - 0.5) < 0.5).astype(float) - (
        np.abs(coordinate + 0.5) < 0.5
    ).astype(float)
    axes[1].plot(coordinate, result)
    axes[1].fill_between(coordinate, 0, result, alpha=0.15)
    graph(axes[0], "x / d", "amplitude / E0")
    graph(
        axes[1], "x / d", "amplitude / E0", "Convolution: negative left, positive right"
    )
    save("8.43", figure)

    figure, axes = canvas("Problem 8.44: finite slits convolve into triangles")
    coordinate = np.linspace(-4, 4, 1600)
    slit_width = 0.6
    separation = 2.4
    source = (
        (np.abs(coordinate - separation / 2) < slit_width / 2)
        | (np.abs(coordinate + separation / 2) < slit_width / 2)
    ).astype(float)
    result = slit_width * (
        triangle((coordinate - separation) / slit_width)
        + 2 * triangle(coordinate / slit_width)
        + triangle((coordinate + separation) / slit_width)
    )
    axes[0].plot(coordinate, source)
    axes[1].plot(coordinate, result, color=TEAL)
    graph(axes[0], "position x", "aperture transmission", "Two slits: b = 0.6, d = 2.4")
    graph(axes[1], "position x", "convolution amplitude", "Peak weights: 1 : 2 : 1")
    save("8.44", figure)

    figure, axes = canvas("Problem 8.45: unequal rectangles produce a trapezoid")
    coordinate = np.linspace(0, 8, 1600)
    axes[0].plot(
        coordinate,
        2 * ((coordinate > 1) & (coordinate < 2)),
        label="f: height 2 on [1,2]",
    )
    axes[0].plot(
        coordinate,
        ((coordinate > 3) & (coordinate < 5)).astype(float),
        label="h: height 1 on [3,5]",
    )
    overlap = np.maximum(
        0, np.minimum(2, coordinate - 3) - np.maximum(1, coordinate - 5)
    )
    axes[1].plot(coordinate, 2 * overlap, color=TEAL)
    axes[1].fill_between(coordinate, 0, 2 * overlap, color=TEAL, alpha=0.12)
    graph(axes[0], "position x", "amplitude", "Input functions")
    graph(
        axes[1],
        "position x",
        "convolution amplitude",
        "Overlap support [4,7]; plateau [5,6]",
    )
    axes[0].legend()
    save("8.45", figure)

    figure, axes = canvas("Problem 8.46: weighted shifts of a triangular kernel")
    positions = list(range(6))
    weights = [1, 2, 3, 1, 1, 2]
    impulses(axes[0], positions, weights)
    coordinate = np.linspace(-1.5, 6.5, 1400)
    total = np.zeros_like(coordinate)
    for position, weight in zip(positions, weights):
        component = weight * triangle(coordinate - position)
        total += component
        axes[1].plot(coordinate, component, "--", lw=0.8, alpha=0.5)
    axes[1].plot(coordinate, total, color=TEAL, lw=2.4, label="sum")
    graph(axes[0], "position x", "impulse weight")
    graph(axes[1], "position x", "convolution amplitude")
    axes[1].legend()
    save("8.46", figure)

    figure, axes = canvas(
        "Problem 8.47: six hole centres give nineteen pair-sum centres"
    )
    vertices = [(2, 0), (1, 1), (-1, 1), (-2, 0), (-1, -1), (1, -1)]
    counts = Counter(
        (first[0] + second[0], first[1] + second[1])
        for first in vertices
        for second in vertices
    )
    for axis in axes:
        diagram(axis, (-2.5, 2.5, -2.2, 2.2), equal=True)
    for horizontal, vertical in vertices:
        axes[0].add_patch(
            Circle(
                (horizontal / 2, vertical * np.sqrt(3) / 2),
                0.14,
                facecolor=BLUE,
                alpha=0.8,
            )
        )
    for (horizontal, vertical), weight in counts.items():
        position = (horizontal / 2, vertical * np.sqrt(3) / 2)
        axes[1].add_patch(
            Circle(position, 0.19, facecolor=TEAL, alpha=0.18 + 0.1 * weight)
        )
        axes[1].text(*position, str(weight), ha="center", va="center", fontsize=11)
    axes[0].set_title("Input: six equal circular holes")
    axes[1].set_title("Output centres and multiplicities (sum = 36)")
    save("8.47", figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preview-dir",
        type=Path,
        help="Also write PNG previews outside the source tree.",
    )
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
    written = set()

    def save(key, figure):
        if key in written:
            raise ValueError(f"Duplicate illustration: {key}")
        caption = TOPICS[key] if key in TOPICS else PROBLEMS[key]
        path = OUTPUT / figure_name(key)
        figure.savefig(
            path,
            format="svg",
            metadata={"Date": None, "Title": caption, "Description": caption},
        )
        if args.preview_dir:
            figure.savefig(args.preview_dir / path.with_suffix(".png").name, dpi=130)
        plt.close(figure)
        written.add(key)

    for generate in [
        generate_waves,
        generate_fields,
        generate_interfaces,
        generate_imaging,
        generate_polarization,
        generate_interference,
        generate_diffraction,
        generate_fourier,
    ]:
        generate(save)
    if written != set(TOPICS) | set(PROBLEMS):
        raise ValueError(
            "Generated illustration inventory does not match caption inventory"
        )
    print(f"Generated {len(written)} original SVG illustrations in {OUTPUT}")


if __name__ == "__main__":
    main()
