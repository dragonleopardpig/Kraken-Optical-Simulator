#!/usr/bin/env python3
"""Generate the Figure 4.0-2 sampled-picture Fourier demonstration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "docs"
    / "source"
    / "_static"
    / "knowledge_base"
    / "worked_exercises"
    / "fundamentals_of_photonics"
    / "fourier_picture_decomposition"
)
WIDTH = 256
HEIGHT = 128
THRESHOLDS = (0.90, 0.95, 0.99, 0.999)


@dataclass(frozen=True)
class HarmonicGroup:
    members: tuple[tuple[int, int], ...]
    energy: float


def make_test_picture() -> np.ndarray:
    """Create a deterministic grayscale scene with smooth areas and edges."""

    y = np.arange(HEIGHT)[:, None]
    sky = 205.0 - 0.72 * y
    picture = np.repeat(sky, WIDTH, axis=1)

    water = y[:, 0] >= 78
    water_y = y[water, 0] - 78
    x = np.arange(WIDTH)[None, :]
    picture[water] = (
        112.0
        - 0.48 * water_y[:, None]
        + 7.0 * np.sin(2 * np.pi * x / 31.0 + water_y[:, None] / 5.0)
        + 3.5 * np.sin(2 * np.pi * x / 11.0 - water_y[:, None] / 3.0)
    )

    image = Image.fromarray(np.uint8(np.clip(picture, 0, 255)), mode="L")
    draw = ImageDraw.Draw(image)

    draw.ellipse((188, 12, 222, 46), fill=244)
    draw.ellipse((27, 18, 60, 29), fill=222)
    draw.ellipse((47, 15, 79, 30), fill=222)
    draw.ellipse((67, 20, 95, 31), fill=222)

    draw.polygon(((0, 78), (38, 34), (75, 78)), fill=82)
    draw.polygon(((38, 78), (94, 25), (151, 78)), fill=104)
    draw.polygon(((113, 78), (166, 42), (215, 78)), fill=126)
    draw.polygon(((173, 78), (224, 48), (255, 74), (255, 78)), fill=139)
    draw.polygon(((79, 39), (94, 25), (111, 41), (99, 37), (91, 43)), fill=184)

    draw.rectangle((113, 61, 139, 86), fill=52)
    draw.polygon(((108, 62), (126, 48), (145, 62)), fill=34)
    draw.rectangle((121, 68, 128, 86), fill=19)
    draw.rectangle((131, 67, 136, 73), fill=226)

    for trunk_x, base_y, tree_height in ((19, 79, 27), (51, 77, 23), (239, 78, 31)):
        draw.rectangle((trunk_x - 1, base_y - tree_height // 3, trunk_x + 1, base_y), fill=42)
        draw.polygon(
            (
                (trunk_x, base_y - tree_height),
                (trunk_x - 10, base_y - 6),
                (trunk_x + 10, base_y - 6),
            ),
            fill=58,
        )

    draw.line((173, 85, 173, 112), fill=31, width=2)
    draw.polygon(((174, 87), (174, 106), (193, 106)), fill=219)
    draw.polygon(((171, 91), (171, 106), (158, 106)), fill=178)
    draw.polygon(((154, 107), (196, 107), (188, 114), (162, 114)), fill=38)

    picture = np.asarray(image, dtype=np.float64)
    rng = np.random.default_rng(20260902)
    picture += rng.normal(0.0, 0.8, picture.shape)
    return np.clip(picture, 0.0, 255.0)


def conjugate_groups(spectrum: np.ndarray) -> list[HarmonicGroup]:
    """Pair DFT bins that jointly form one real spatial harmonic."""

    ny, nx = spectrum.shape
    visited: set[tuple[int, int]] = set()
    groups: list[HarmonicGroup] = []
    for py in range(ny):
        for px in range(nx):
            index = (py, px)
            if index in visited:
                continue
            partner = ((-py) % ny, (-px) % nx)
            members = (index,) if partner == index else (index, partner)
            visited.update(members)
            energy = float(sum(abs(spectrum[iy, ix]) ** 2 for iy, ix in members))
            groups.append(HarmonicGroup(members=members, energy=energy))
    return sorted(groups, key=lambda group: group.energy, reverse=True)


def group_count_for_energy(groups: list[HarmonicGroup], fraction: float) -> int:
    cumulative = np.cumsum([group.energy for group in groups])
    return int(np.searchsorted(cumulative, fraction * cumulative[-1]) + 1)


def reconstruct(
    spectrum: np.ndarray, groups: list[HarmonicGroup], count: int
) -> np.ndarray:
    retained = np.zeros_like(spectrum)
    for group in groups[:count]:
        for py, px in group.members:
            retained[py, px] = spectrum[py, px]
    return np.fft.ifft2(retained).real


def signed_bin(index: int, size: int) -> int:
    return index if index <= size // 2 else index - size


def save_overview(
    picture: np.ndarray,
    spectrum: np.ndarray,
    groups: list[HarmonicGroup],
    threshold_rows: list[dict[str, float | int]],
) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(15.2, 7.8), constrained_layout=True)
    fig.patch.set_facecolor("#f3efe6")
    for axis in axes.flat:
        axis.set_facecolor("#fbfaf6")

    axes[0, 0].imshow(picture, cmap="gray", vmin=0, vmax=255)
    axes[0, 0].set_title("Arbitrary 256 x 128 picture", fontweight="bold")
    axes[0, 0].set_xlabel("pixel x")
    axes[0, 0].set_ylabel("pixel y")

    log_magnitude = np.log10(1.0 + np.abs(np.fft.fftshift(spectrum)))
    spectrum_image = axes[0, 1].imshow(
        log_magnitude,
        cmap="magma",
        origin="lower",
        extent=(-0.5, 0.5, -0.5, 0.5),
        aspect=1,
    )
    axes[0, 1].set_title(r"Spectrum: $\log_{10}(1+|F|)$", fontweight="bold")
    axes[0, 1].set_xlabel(r"$\nu_x$ (cycles/pixel)")
    axes[0, 1].set_ylabel(r"$\nu_y$ (cycles/pixel)")
    fig.colorbar(spectrum_image, ax=axes[0, 1], fraction=0.048, pad=0.03)

    group_energy = np.array([group.energy for group in groups])
    cumulative = np.cumsum(group_energy) / group_energy.sum()
    axes[0, 2].semilogx(
        np.arange(1, len(groups) + 1),
        100 * cumulative,
        color="#b64b32",
        linewidth=2.3,
    )
    for fraction in THRESHOLDS:
        axes[0, 2].axhline(100 * fraction, color="#8899a6", linewidth=0.8, linestyle="--")
    axes[0, 2].set_ylim(75, 100.2)
    axes[0, 2].set_title("Energy captured by strongest groups", fontweight="bold")
    axes[0, 2].set_xlabel("retained real-harmonic groups")
    axes[0, 2].set_ylabel("total spectral energy (%)")
    axes[0, 2].grid(alpha=0.25)

    mean_only = reconstruct(spectrum, groups, 1)
    axes[0, 3].imshow(mean_only, cmap="gray", vmin=0, vmax=255)
    axes[0, 3].set_title("Strongest group only\nDC = average brightness", fontweight="bold")

    for axis, row in zip(axes[1], threshold_rows, strict=True):
        reconstruction = reconstruct(spectrum, groups, int(row["groups"]))
        axis.imshow(np.clip(reconstruction, 0, 255), cmap="gray", vmin=0, vmax=255)
        axis.set_title(
            f'{100 * float(row["target"]):g}% energy\n'
            f'{int(row["groups"]):,} groups / {int(row["coefficients"]):,} coefficients',
            fontweight="bold",
        )

    for axis in axes.flat:
        if axis not in (axes[0, 0], axes[0, 1], axes[0, 2]):
            axis.set_xticks([])
            axis.set_yticks([])
    fig.suptitle(
        "A sampled picture reconstructed from its strongest spatial harmonics",
        fontsize=18,
        fontweight="bold",
        color="#19324d",
    )
    fig.savefig(OUTPUT / "figure_4_0_2_fourier_decomposition.png", dpi=170)
    plt.close(fig)


def save_strongest_harmonics(
    spectrum: np.ndarray, groups: list[HarmonicGroup]
) -> None:
    non_dc = [group for group in groups if (0, 0) not in group.members][:8]
    fig, axes = plt.subplots(2, 4, figsize=(15.2, 6.4), constrained_layout=True)
    fig.patch.set_facecolor("#f3efe6")
    total_energy = sum(group.energy for group in groups)

    for rank, (axis, group) in enumerate(zip(axes.flat, non_dc, strict=True), start=1):
        component = reconstruct(spectrum, [group], 1)
        scale = max(float(np.max(np.abs(component))), 1e-12)
        py, px = group.members[0]
        qx = signed_bin(px, WIDTH)
        qy = signed_bin(py, HEIGHT)
        axis.imshow(component, cmap="coolwarm", vmin=-scale, vmax=scale)
        axis.set_title(
            f"AC rank {rank}: (qx, qy)=({qx}, {qy})\n"
            f"{100 * group.energy / total_energy:.3f}% of total energy",
            fontsize=10.5,
            fontweight="bold",
        )
        axis.set_xticks([])
        axis.set_yticks([])

    fig.suptitle(
        "Eight strongest non-DC real harmonics (each normalized for visibility)",
        fontsize=17,
        fontweight="bold",
        color="#19324d",
    )
    fig.savefig(OUTPUT / "figure_4_0_2_strongest_harmonics.png", dpi=170)
    plt.close(fig)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    picture = make_test_picture()
    spectrum = np.fft.fft2(picture)
    groups = conjugate_groups(spectrum)

    threshold_rows: list[dict[str, float | int]] = []
    for threshold in THRESHOLDS:
        count = group_count_for_energy(groups, threshold)
        selected = groups[:count]
        threshold_rows.append(
            {
                "target": threshold,
                "groups": count,
                "coefficients": sum(len(group.members) for group in selected),
                "energy": sum(group.energy for group in selected)
                / sum(group.energy for group in groups),
            }
        )

    dc_group = next(group for group in groups if (0, 0) in group.members)
    ac_groups = [group for group in groups if group is not dc_group]
    ac_rows = []
    for threshold in THRESHOLDS:
        count = group_count_for_energy(ac_groups, threshold)
        selected = ac_groups[:count]
        ac_rows.append(
            {
                "target": threshold,
                "groups": count,
                "coefficients": sum(len(group.members) for group in selected),
            }
        )

    numerical_nonzero = int(
        np.count_nonzero(np.abs(spectrum) > np.max(np.abs(spectrum)) * 1e-12)
    )
    metadata = {
        "width": WIDTH,
        "height": HEIGHT,
        "complex_coefficients": WIDTH * HEIGHT,
        "real_harmonic_groups": len(groups),
        "self_conjugate_bins": sum(len(group.members) == 1 for group in groups),
        "numerically_nonzero_coefficients": numerical_nonzero,
        "thresholds_total_energy": threshold_rows,
        "thresholds_contrast_energy_excluding_dc": ac_rows,
    }

    save_overview(picture, spectrum, groups, threshold_rows)
    save_strongest_harmonics(spectrum, groups)
    (OUTPUT / "figure_4_0_2_counts.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
