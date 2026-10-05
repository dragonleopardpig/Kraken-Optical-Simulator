from argparse import ArgumentParser
from io import StringIO
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle

matplotlib.use("Agg")


DOCUMENTATION_DIR = Path(__file__).resolve().parent
ASSET_DIR = DOCUMENTATION_DIR / "source/_static/knowledge_base/active_fiber_alignment"
BLUE = "#245da1"
ORANGE = "#b95419"
GREEN = "#116b62"
GRAY = "#475569"


def style_axes(axis):
    axis.grid(alpha=0.2)
    axis.spines[["top", "right"]].set_visible(False)


def mode_overlap():
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 8.8), layout="constrained")
    waist_um = 2.5
    displacement_um = 1.0
    coordinates_um = np.linspace(-6, 6, 501)
    target = np.exp(-((coordinates_um / waist_um) ** 2))
    incident = np.exp(-(((coordinates_um - displacement_um) / waist_um) ** 2))
    field_axis = axes[0, 0]
    field_axis.plot(coordinates_um, target, color=BLUE, label="Target guided mode")
    field_axis.plot(
        coordinates_um, incident, color=ORANGE, label="Incident field, offset +1 µm"
    )
    field_axis.axvline(0, color=BLUE, linestyle=":")
    field_axis.axvline(displacement_um, color=ORANGE, linestyle=":")
    field_axis.set(
        title="(a) Field amplitudes across the facet",
        xlabel="Transverse coordinate X (µm)",
        ylabel="Field amplitude / peak amplitude",
    )
    field_axis.legend(fontsize=11)
    style_axes(field_axis)

    displacement_axis = axes[0, 1]
    offsets_um = np.linspace(-5, 5, 501)
    retained = np.exp(-((offsets_um / waist_um) ** 2))
    displacement_axis.plot(offsets_um, 100 * retained, color=BLUE)
    example_efficiency = np.exp(-((displacement_um / waist_um) ** 2))
    displacement_axis.scatter(
        [-1, 1], [100 * example_efficiency] * 2, color=ORANGE, zorder=4
    )
    displacement_axis.annotate(
        "−1 µm and +1 µm\nboth retain 85.2%",
        xy=(1, 100 * example_efficiency),
        xytext=(1.5, 48),
        arrowprops={"arrowstyle": "->", "color": ORANGE},
    )
    displacement_axis.set(
        title="(b) Coupling versus lateral offset",
        xlabel="Beam-to-core offset Δx (µm)",
        ylabel="Retained coupling η / η₀ (%)",
        ylim=(0, 105),
    )
    style_axes(displacement_axis)

    geometry_axis = axes[1, 0]
    geometry_axis.set_axis_off()
    geometry_axis.set(
        xlim=(0, 1), ylim=(0, 1), title="(c) Offset and tilt at the facet (schematic)"
    )
    geometry_axis.add_patch(
        Rectangle(
            (0.76, 0.32), 0.19, 0.32, facecolor="#eaf1fb", edgecolor=BLUE, linewidth=2
        )
    )
    geometry_axis.add_patch(Rectangle((0.76, 0.475), 0.19, 0.025, facecolor=BLUE))
    geometry_axis.plot([0.08, 0.95], [0.4875, 0.4875], color=BLUE, linestyle="--")
    geometry_axis.annotate(
        "",
        xy=(0.75, 0.665),
        xytext=(0.12, 0.81),
        arrowprops={"arrowstyle": "->", "color": ORANGE, "lw": 3},
    )
    geometry_axis.plot([0.12, 0.38], [0.81, 0.81], color=GRAY, linestyle=":")
    geometry_axis.annotate(
        "",
        xy=(0.70, 0.665),
        xytext=(0.70, 0.4875),
        arrowprops={"arrowstyle": "<->", "color": GRAY},
    )
    geometry_axis.text(0.60, 0.565, "Δx", color=GRAY)
    geometry_axis.text(0.33, 0.76, "αₓ", color=ORANGE)
    geometry_axis.text(0.16, 0.89, "Incoming beam", color=ORANGE)
    geometry_axis.text(0.09, 0.43, "Fiber-axis reference", color=BLUE)
    geometry_axis.text(0.75, 0.24, "Input facet")
    geometry_axis.annotate(
        "",
        xy=(0.40, 0.12),
        xytext=(0.10, 0.12),
        arrowprops={"arrowstyle": "->", "color": GRAY},
    )
    geometry_axis.annotate(
        "",
        xy=(0.10, 0.34),
        xytext=(0.10, 0.12),
        arrowprops={"arrowstyle": "->", "color": GRAY},
    )
    geometry_axis.text(0.42, 0.12, "+z", va="center")
    geometry_axis.text(0.10, 0.36, "+x", ha="center")
    geometry_axis.text(
        0.52, 0.04, "Geometry and angle exaggerated", ha="center", fontsize=10
    )

    angular_axis = axes[1, 1]
    wavelength_um = 1.55
    wave_number_per_um = 2 * np.pi / wavelength_um
    angles_mrad = np.linspace(-100, 100, 501)
    angular_efficiency = np.exp(
        -((wave_number_per_um * waist_um * angles_mrad / 1000) ** 2) / 4
    )
    example_angle_mrad = 20.0
    example_angular_efficiency = np.exp(
        -((wave_number_per_um * waist_um * example_angle_mrad / 1000) ** 2) / 4
    )
    angular_axis.plot(angles_mrad, 100 * angular_efficiency, color=GREEN)
    angular_axis.scatter(
        [example_angle_mrad], [100 * example_angular_efficiency], color=ORANGE, zorder=4
    )
    angular_axis.annotate(
        "20 mrad → 98.98%",
        xy=(20, 100 * example_angular_efficiency),
        xytext=(-85, 88),
        arrowprops={"arrowstyle": "->", "color": ORANGE},
    )
    angular_axis.set(
        title="(d) Coupling versus optical tilt in air",
        xlabel="Beam-to-fiber direction error αₓ (mrad)",
        ylabel="Retained coupling η / η₀ (%)",
        ylim=(70, 102),
    )
    style_axes(angular_axis)
    figure.suptitle(
        "Matched Gaussian modes: w = 2.5 µm; angular example λ₀ = 1.55 µm, n = 1",
        fontsize=15,
    )
    assert np.isclose(example_efficiency, 0.8521437889662113)
    assert np.isclose(example_angular_efficiency, 0.9897824179516475)
    return figure


def dither_gradient():
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 8.5), layout="constrained")
    waist_um = 2.5
    amplitude_um = 0.05
    center_x_um, center_y_um = 1.0, -0.5
    frequency_hz = 100.0
    time_seconds = np.linspace(0, 2 / frequency_hz, 2001)
    phase = 2 * np.pi * frequency_hz * time_seconds
    motion_x_um = amplitude_um * np.cos(phase)
    motion_y_um = amplitude_um * np.sin(phase)
    center_power = np.exp(-(center_x_um**2 + center_y_um**2) / waist_um**2)
    gradient = -2 * center_power / waist_um**2 * np.array([center_x_um, center_y_um])
    correction_um = 0.5 * gradient

    position_axis = axes[0, 0]
    grid_x_um = np.linspace(-0.4, 1.4, 151)
    grid_y_um = np.linspace(-0.9, 0.6, 151)
    mesh_x_um, mesh_y_um = np.meshgrid(grid_x_um, grid_y_um)
    objective = np.exp(-(mesh_x_um**2 + mesh_y_um**2) / waist_um**2)
    position_axis.contour(
        mesh_x_um,
        mesh_y_um,
        objective,
        levels=[0.7, 0.8, 0.9, 0.98],
        colors=GRAY,
        alpha=0.5,
    )
    position_axis.plot(
        center_x_um + motion_x_um, center_y_um + motion_y_um, color=ORANGE, linewidth=2
    )
    position_axis.scatter(
        [0], [0], marker="*", s=140, color=BLUE, label="Power maximum"
    )
    position_axis.scatter(
        [center_x_um], [center_y_um], color=ORANGE, label="Dither center (+1, −0.5) µm"
    )
    position_axis.annotate(
        "",
        xy=(center_x_um + correction_um[0], center_y_um + correction_um[1]),
        xytext=(center_x_um, center_y_um),
        arrowprops={"arrowstyle": "->", "color": GREEN, "lw": 3},
    )
    position_axis.text(0.60, -0.74, "Correction: −x, +y", color=GREEN)
    position_axis.set(
        title="(a) Small circle about a misaligned center",
        xlabel="Calibrated lateral x (µm)",
        ylabel="Calibrated lateral y (µm)",
        aspect="equal",
    )
    position_axis.legend(loc="upper right", fontsize=10)
    style_axes(position_axis)

    motion_axis = axes[0, 1]
    motion_axis.plot(
        1000 * time_seconds,
        1000 * motion_x_um,
        color=BLUE,
        label=r"$x-x_0=a_{\mathrm{d}}\cos(\omega t)$",
    )
    motion_axis.plot(
        1000 * time_seconds,
        1000 * motion_y_um,
        color=GREEN,
        label=r"$y-y_0=a_{\mathrm{d}}\sin(\omega t)$",
    )
    motion_axis.set(
        title="(b) Known motion provides the phase reference",
        xlabel="Time t (ms)",
        ylabel="Motion about center (nm)",
    )
    motion_axis.legend(fontsize=11)
    style_axes(motion_axis)

    measured_power = np.exp(
        -((center_x_um + motion_x_um) ** 2 + (center_y_um + motion_y_um) ** 2)
        / waist_um**2
    )
    first_order = center_power + gradient[0] * motion_x_um + gradient[1] * motion_y_um
    power_axis = axes[1, 0]
    power_axis.plot(
        1000 * time_seconds, measured_power, color=ORANGE, label="Gaussian model"
    )
    power_axis.plot(
        1000 * time_seconds,
        first_order,
        color=GRAY,
        linestyle="--",
        label="First-order gradient approximation",
    )
    power_axis.set(
        title="(c) Output modulation encodes the local slopes",
        xlabel="Time t (ms)",
        ylabel="Normalized objective F",
    )
    power_axis.legend(loc="upper right", fontsize=10)
    style_axes(power_axis)

    sampling_phase = np.arange(32768) * 2 * np.pi / 32768
    samples = np.exp(
        -(
            (center_x_um + amplitude_um * np.cos(sampling_phase)) ** 2
            + (center_y_um + amplitude_um * np.sin(sampling_phase)) ** 2
        )
        / waist_um**2
    )
    estimates = (
        2
        / amplitude_um
        * np.array(
            [
                np.mean(samples * np.cos(sampling_phase)),
                np.mean(samples * np.sin(sampling_phase)),
            ]
        )
    )
    gradient_axis = axes[1, 1]
    gradient_axis.bar(["x slope", "y slope"], estimates, color=[BLUE, GREEN], width=0.5)
    gradient_axis.axhline(0, color=GRAY)
    gradient_axis.text(
        0,
        -0.20,
        f"{estimates[0]:+.3f} / µm\nmove toward −x",
        ha="center",
        color="white",
        fontsize=12,
    )
    gradient_axis.text(
        1,
        0.045,
        f"{estimates[1]:+.3f} / µm\nmove toward +y",
        ha="center",
        color="white",
        fontsize=12,
    )
    gradient_axis.set(
        title="(d) Demodulation separates signed slopes",
        ylabel="Estimated gradient (1/µm)",
        ylim=(-0.32, 0.18),
    )
    style_axes(gradient_axis)
    figure.suptitle(
        r"Illustrative dither: $a_{\mathrm{d}}$ = 50 nm, f = 100 Hz, w = 2.5 µm",
        fontsize=15,
    )
    assert np.allclose(estimates, gradient, rtol=0.001)
    return figure


def centered_harmonics():
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 8.0), layout="constrained")
    waist_um = 2.5
    amplitude_um = 0.05
    frequency_hz = 100.0
    time_seconds = np.linspace(0, 2 / frequency_hz, 2001)
    phase = 2 * np.pi * frequency_hz * time_seconds
    motion_x_um = amplitude_um * np.cos(phase)
    motion_y_um = amplitude_um * np.sin(phase)
    linear_axis = axes[0, 0]
    linear_axis.plot(
        1000 * motion_x_um, np.zeros_like(motion_x_um), color=BLUE, linewidth=3
    )
    circle_axis = axes[0, 1]
    circle_axis.plot(1000 * motion_x_um, 1000 * motion_y_um, color=GREEN, linewidth=3)
    for axis, title in zip(
        (linear_axis, circle_axis),
        ("(a) Linear dither through the peak", "(b) Circular dither around the peak"),
    ):
        axis.scatter(
            [0],
            [0],
            marker="*",
            s=140,
            color=ORANGE,
            label="Maximum at (0, 0)",
            zorder=4,
        )
        axis.set(
            title=title,
            xlabel="x displacement (nm)",
            ylabel="y displacement (nm)",
            xlim=(-70, 70),
            ylim=(-70, 70),
            aspect="equal",
        )
        axis.legend(fontsize=10, loc="upper right")
        style_axes(axis)

    linear_power = np.exp(-(motion_x_um**2) / waist_um**2)
    circular_power = np.exp(-(motion_x_um**2 + motion_y_um**2) / waist_um**2)
    axes[1, 0].plot(1000 * time_seconds, 100 * linear_power, color=BLUE)
    axes[1, 0].axhline(99.98, color=GRAY, linestyle=":", label="Mean ≈ 99.980%")
    axes[1, 0].set(title="(c) Linear motion gives power ripple at 2f")
    axes[1, 0].text(10, 99.968, "Power ripple at 2f = 200 Hz", ha="center", color=BLUE)
    axes[1, 0].legend(fontsize=11, loc="upper right")
    axes[1, 1].plot(1000 * time_seconds, 100 * circular_power, color=GREEN)
    axes[1, 1].set(title="(d) Circular motion gives constant power")
    axes[1, 1].text(
        10,
        99.983,
        "99.960% constant power\nNo f or 2f ripple in this ideal radial model",
        ha="center",
        color=GREEN,
    )
    for axis in axes[1]:
        axis.set(
            xlabel="Time t (ms)",
            ylabel=r"Retained power $F/F_{\max}$ (%)",
            ylim=(99.95, 100.01),
        )
        axis.ticklabel_format(axis="y", useOffset=False)
        style_axes(axis)
    figure.suptitle(
        r"At a radially symmetric Gaussian maximum: w = 2.5 µm, $a_{\mathrm{d}}$ = 50 nm, f = 100 Hz",
        fontsize=15,
    )
    assert np.ptp(circular_power) < 1e-14
    assert np.isclose(circular_power.mean(), np.exp(-(amplitude_um**2) / waist_um**2))
    return figure


def spatial_measurements():
    figure, axes = plt.subplots(1, 3, figsize=(14, 5.3), layout="constrained")
    coordinates_px = np.linspace(-16, 16, 257)
    mesh_x_px, mesh_y_px = np.meshgrid(coordinates_px, coordinates_px)
    for axis, offset_px, title, detail in (
        (
            axes[0],
            8,
            "(a) Near-field centroid",
            "M = 40; pixel pitch p = 5 µm\n+8 pixels → +1 µm at facet",
        ),
        (
            axes[1],
            10,
            "(b) Fourier-plane centroid",
            r"$f_{\mathrm{F}}$ = 50 mm; p = 5 µm" + "\n+10 pixels → +1 mrad tilt",
        ),
    ):
        image = np.exp(-((mesh_x_px - offset_px) ** 2 + mesh_y_px**2) / 8)
        axis.imshow(
            image,
            origin="lower",
            extent=(-16, 16, -16, 16),
            cmap="cividis",
            vmin=0,
            vmax=1,
        )
        axis.axvline(0, color="white", linestyle=":", linewidth=1)
        axis.axhline(0, color="white", linestyle=":", linewidth=1)
        axis.scatter([0], [0], color="white", marker="+", s=100)
        axis.annotate(
            "",
            xy=(offset_px, -6),
            xytext=(0, -6),
            arrowprops={"arrowstyle": "<->", "color": "white", "lw": 2},
        )
        axis.text(
            offset_px / 2,
            -9,
            f"+{offset_px} pixels",
            color="white",
            ha="center",
            fontsize=11,
        )
        axis.set(
            title=title,
            xlabel="Registered camera x (pixels)",
            ylabel="Registered camera y (pixels)",
        )
        axis.text(
            0.5, -0.26, detail, transform=axis.transAxes, ha="center", fontsize=12
        )

    residual_axis = axes[2]
    residual_axis.set(
        title="(c) Residual-region powers",
        xlim=(-1.05, 1.05),
        ylim=(-1.05, 1.05),
        aspect="equal",
        xlabel="Registered camera x",
        ylabel="Registered camera y",
    )
    for origin_x, origin_y, power_mw, color in (
        (-1, 0, 0.20, "#dceaf6"),
        (0, 0, 0.35, "#f4d6b8"),
        (-1, -1, 0.20, "#dceaf6"),
        (0, -1, 0.25, "#efdcc8"),
    ):
        residual_axis.add_patch(
            Rectangle(
                (origin_x, origin_y),
                1,
                1,
                facecolor=color,
                edgecolor="white",
                linewidth=2,
            )
        )
        residual_axis.text(
            origin_x + 0.5,
            origin_y + 0.5,
            f"{power_mw:.2f} mW",
            ha="center",
            va="center",
            fontsize=12,
        )
    residual_axis.add_patch(
        Circle((0, 0), 0.22, facecolor="white", edgecolor=GRAY, linewidth=1.5)
    )
    residual_axis.text(0, 0, "core\nmask", ha="center", va="center", fontsize=9)
    residual_axis.set_xticks([-0.65, 0.65], ["Left", "Right"])
    residual_axis.set_yticks([-0.65, 0.65], ["Bottom", "Top"])
    residual_axis.text(
        0.5,
        -0.26,
        "$P_R$ = 0.60, $P_L$ = 0.40 mW → $S_x$ = +0.20\n$P_T$ = 0.55, $P_B$ = 0.45 mW → $S_y$ = +0.10",
        transform=residual_axis.transAxes,
        ha="center",
        fontsize=11,
    )
    figure.suptitle(
        "Three independent measurement examples; camera signs are calibrated with y increasing upward",
        fontsize=14,
    )
    return figure


def calibration_response():
    figure, axes = plt.subplots(1, 2, figsize=(13.5, 5.7), layout="constrained")
    response = np.array([[4.0, 1.0], [1.0, 3.0]])
    stage_error_um = np.array([2.0, -1.0])
    feature_error_px = response @ stage_error_um
    damping = 0.5
    move_um = -damping * np.linalg.solve(response, feature_error_px)
    stage_after_um = stage_error_um + move_um
    features_after_px = feature_error_px + response @ move_um
    for axis, before, after, title, xlabel, ylabel, limits in (
        (
            axes[0],
            stage_error_um,
            stage_after_um,
            "(a) Calibrated stage coordinates",
            "x relative to optimum (µm)",
            "y relative to optimum (µm)",
            ((-0.5, 2.7), (-1.5, 1.0)),
        ),
        (
            axes[1],
            feature_error_px,
            features_after_px,
            "(b) Camera-feature coordinates",
            "Feature residual e₁ (pixels)",
            "Feature residual e₂ (pixels)",
            ((-1, 8.5), (-2.3, 4.5)),
        ),
    ):
        axis.scatter([0], [0], marker="*", s=150, color=BLUE, label="Target")
        axis.scatter(
            [before[0]], [before[1]], color=ORANGE, s=65, label="Before correction"
        )
        axis.scatter(
            [after[0]], [after[1]], color=GREEN, s=65, label="After half correction"
        )
        axis.annotate(
            "",
            xy=after,
            xytext=before,
            arrowprops={"arrowstyle": "->", "color": GREEN, "lw": 2.5},
        )
        axis.annotate(
            f"({before[0]:g}, {before[1]:g})",
            xy=before,
            xytext=(7, -22),
            textcoords="offset points",
            color=ORANGE,
        )
        axis.annotate(
            f"({after[0]:g}, {after[1]:g})",
            xy=after,
            xytext=(7, 7),
            textcoords="offset points",
            color=GREEN,
        )
        axis.set(
            title=title, xlabel=xlabel, ylabel=ylabel, xlim=limits[0], ylim=limits[1]
        )
        axis.legend(fontsize=10, loc="upper right")
        style_axes(axis)
    axes[1].annotate(
        "",
        xy=(4, 1),
        xytext=(0, 0),
        arrowprops={"arrowstyle": "->", "color": GRAY, "linestyle": "--"},
    )
    axes[1].text(4.1, 1.1, "+1 µm in x\n→ (+4, +1) pixels", fontsize=10)
    axes[1].annotate(
        "",
        xy=(1, 3),
        xytext=(0, 0),
        arrowprops={"arrowstyle": "->", "color": GRAY, "linestyle": "--"},
    )
    axes[1].text(1.15, 3.0, "+1 µm in y\n→ (+1, +3) pixels", fontsize=10)
    figure.suptitle(
        "J = [[4, 1], [1, 3]] pixels/µm; measured e = (7, −1) pixels; γ = 0.5",
        fontsize=15,
    )
    assert np.allclose(move_um, [-1, 0.5])
    assert np.allclose(features_after_px, [3.5, -0.5])
    return figure


def main():
    parser = ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ASSET_DIR)
    parser.add_argument("--preview-dir", type=Path)
    arguments = parser.parse_args()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    if arguments.preview_dir:
        arguments.preview_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 12,
            "svg.fonttype": "none",
            "svg.hashsalt": "active-fiber-alignment",
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    for filename, builder in (
        ("mode_overlap", mode_overlap),
        ("dither_gradient", dither_gradient),
        ("centered_harmonics", centered_harmonics),
        ("spatial_measurements", spatial_measurements),
        ("calibration_response", calibration_response),
    ):
        figure = builder()
        svg_buffer = StringIO()
        figure.savefig(
            svg_buffer,
            format="svg",
            bbox_inches="tight",
            pad_inches=0.15,
            metadata={
                "Date": None,
                "Title": filename.replace("_", " "),
                "Description": "Original analytical illustration for the KrakenOS active fiber alignment guide.",
            },
        )
        svg_text = "\n".join(
            line.rstrip() for line in svg_buffer.getvalue().splitlines()
        )
        (arguments.output_dir / f"{filename}.svg").write_text(svg_text + "\n")
        if arguments.preview_dir:
            figure.savefig(
                arguments.preview_dir / f"{filename}.png",
                bbox_inches="tight",
                pad_inches=0.15,
                dpi=120,
            )
        plt.close(figure)
        print(arguments.output_dir / f"{filename}.svg")


if __name__ == "__main__":
    main()
