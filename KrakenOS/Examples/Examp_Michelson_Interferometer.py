"""Ray-only Michelson interferometer path diagnostic.

This example validates source-driven, non-sequential beam-splitter tracing for
a simple Michelson geometry:

* independent physical source at (0, 0, 0), direction +Z;
* 45 degree deterministic 50/50 splitter at z=50 mm;
* one return mirror on the transmitted path;
* one return mirror on the reflected path;
* second splitter encounter produces four recombination paths;
* a first-order detector interferogram is computed from the two cross-port
  paths.

The interferogram is a coherent detector-plane sum using the branch powers,
splitter phases, and optical path difference recorded by ``raykeeper``.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos


BEAM_SPLITTER = {
    "split_mode": "Deterministic paths",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-4,
    "max_branch_depth": 2,
}

INTERFEROGRAM = {
    "analysis_title": "Michelson Interferogram",
    "detector_port": "cross",
    "detector_size_mm": 12.0,
    "pixels": 256,
    "fringe_tilt_x_mrad": 1.5,
    "fringe_tilt_y_mrad": 0.0,
    "opd_offset_um": 0.0,
    "visibility": 1.0,
}


def coating_from_splitter(settings):
    reflectance = min(max(float(settings["reflectance"]), 0.0), 1.0)
    absorption = min(max(float(settings["absorption"]), 0.0), 1.0 - reflectance)
    wavelengths = [0.55, 0.6328]
    angles = [0.0, 45.0, 70.0]
    r_table = [[reflectance for _wavelength in wavelengths] for _angle in angles]
    a_table = [[absorption for _wavelength in wavelengths] for _angle in angles]
    return [r_table, a_table, wavelengths, angles]


def build_system():
    obj = Kos.surf()
    obj.Name = "Input/reference"
    obj.Thickness = 50.0
    obj.Diameter = 35.0
    obj.Glass = "AIR"
    obj.AxisMove = 0.0

    splitter = Kos.surf()
    splitter.Name = "Michelson splitter"
    splitter.Thickness = 80.0
    splitter.Diameter = 35.0
    splitter.TiltX = 45.0
    splitter.Glass = "AIR"
    splitter.AxisMove = 0.0
    splitter.BeamSplitter = dict(BEAM_SPLITTER)
    splitter.Coating = coating_from_splitter(splitter.BeamSplitter)

    transmit_mirror = Kos.surf()
    transmit_mirror.Name = "Transmit return mirror"
    transmit_mirror.Thickness = 0.0
    transmit_mirror.Diameter = 35.0
    transmit_mirror.Glass = "MIRROR"
    transmit_mirror.AxisMove = 0.0

    reflect_mirror = Kos.surf()
    reflect_mirror.Name = "Reflect return mirror"
    reflect_mirror.Thickness = 0.0
    reflect_mirror.Diameter = 35.0
    reflect_mirror.TiltX = -90.0
    reflect_mirror.DespY = 80.0
    reflect_mirror.DespZ = -80.0
    reflect_mirror.Glass = "MIRROR"
    reflect_mirror.AxisMove = 0.0

    image = Kos.surf()
    image.Name = "Detector path / output port"
    image.Thickness = 0.0
    image.Diameter = 24.0
    image.Glass = "AIR"
    image.AxisMove = 0.0

    system = Kos.system([obj, splitter, transmit_mirror, reflect_mirror, image], Kos.Setup())
    system.energy_probability = 0
    system.NsLimit = 80
    return system


def collimated_meridional_source(radius=4.0, ray_count=5, wavelength=0.6328):
    count = max(1, int(ray_count))
    if count == 1:
        y_values = np.asarray([0.0], dtype=float)
    else:
        y_values = np.linspace(-float(radius), float(radius), count)
    x_values = np.zeros(count, dtype=float)
    z_values = np.zeros(count, dtype=float)
    l_values = np.zeros(count, dtype=float)
    m_values = np.zeros(count, dtype=float)
    n_values = np.ones(count, dtype=float)
    metadata = [
        {
            "source_model": "Collimated disk source",
            "source_xyz": [float(x_values[index]), float(y_values[index]), 0.0],
            "source_lmn": [0.0, 0.0, 1.0],
            "source_power": 1.0,
            "source_weight": 1.0 / float(count),
            "source_wavelength": float(wavelength),
        }
        for index in range(count)
    ]
    return x_values, y_values, z_values, l_values, m_values, n_values, metadata


def trace_demo(ray_count=1, wavelength=0.6328):
    system = build_system()
    rays = Kos.raykeeper(system)
    x, y, z, l, m, n, metadata = collimated_meridional_source(
        ray_count=ray_count,
        wavelength=wavelength,
    )
    Kos.NsTraceLoop(x, y, z, l, m, n, wavelength, rays, source_metadata=metadata)
    return rays


def _branch_value(rays, name, index, default=None):
    values = getattr(rays, name, None)
    if values is None or index >= len(values):
        return default
    arr = np.asarray(values[index]).ravel()
    if arr.size == 0:
        return default
    return arr[-1]


def _branch_code(branch_path):
    selectors = []
    for component in str(branch_path or "").split("->"):
        leaf = component.rsplit("/", 1)[-1].strip().lower()
        if leaf in {"transmit", "reflect"}:
            selectors.append("T" if leaf == "transmit" else "R")
    return "".join(selectors[-2:])


def compute_detector_interferogram(rays, wavelength=0.6328, settings=None):
    settings = dict(INTERFEROGRAM if settings is None else settings)
    codes = ("TR", "RT") if str(settings.get("detector_port", "cross")).lower() != "return" else ("TT", "RR")
    grouped = {code: [] for code in codes}
    for ray_index in range(len(getattr(rays, "BRANCH_PATH", []))):
        path = str(_branch_value(rays, "BRANCH_PATH", ray_index, "") or "")
        code = _branch_code(path)
        if code not in grouped:
            continue
        grouped[code].append(
            {
                "power": float(_branch_value(rays, "BRANCH_POWER", ray_index, 0.0) or 0.0),
                "top_mm": float(_branch_value(rays, "TOP", ray_index, 0.0) or 0.0),
                "phase_deg": float(_branch_value(rays, "BRANCH_PHASE", ray_index, 0.0) or 0.0),
            }
        )
    if not grouped[codes[0]] or not grouped[codes[1]]:
        raise RuntimeError(f"Need both {codes[0]} and {codes[1]} paths")

    def summarize(samples):
        power = np.asarray([item["power"] for item in samples], dtype=float)
        total = float(np.sum(power))
        return {
            "power": total,
            "top_mm": float(np.average([item["top_mm"] for item in samples], weights=power)),
            "phase_deg": float(np.average([item["phase_deg"] for item in samples], weights=power)),
        }

    a = summarize(grouped[codes[0]])
    b = summarize(grouped[codes[1]])
    wavelength_um = float(wavelength)
    wavelength_mm = wavelength_um * 1e-3
    size = float(settings.get("detector_size_mm", 12.0))
    pixels = int(settings.get("pixels", 256))
    axis = np.linspace(-0.5 * size, 0.5 * size, pixels)
    x, y = np.meshgrid(axis, axis)
    tilt_x = float(settings.get("fringe_tilt_x_mrad", 1.5)) * 1e-3
    tilt_y = float(settings.get("fringe_tilt_y_mrad", 0.0)) * 1e-3
    opd_um = (b["top_mm"] - a["top_mm"]) * 1000.0 + float(settings.get("opd_offset_um", 0.0))
    phase0 = 2.0 * np.pi * opd_um / wavelength_um + np.deg2rad(b["phase_deg"] - a["phase_deg"])
    spatial = (2.0 * np.pi / wavelength_mm) * (tilt_x * x + tilt_y * y)
    intensity = a["power"] + b["power"] + 2.0 * np.sqrt(a["power"] * b["power"]) * np.cos(phase0 + spatial)
    intensity /= max(float(np.max(intensity)), 1e-12)
    return axis, axis, intensity


if __name__ == "__main__":
    traced_rays = trace_demo()
    for ray_index, surfaces in enumerate(traced_rays.SURFACE):
        surface_path = [int(value) for value in np.asarray(surfaces, dtype=int)]
        branch_path = str(np.asarray(traced_rays.BRANCH_PATH[ray_index]).ravel()[0])
        branch_power = float(np.asarray(traced_rays.BRANCH_POWER[ray_index]).ravel()[0])
        branch_phase = float(np.asarray(traced_rays.BRANCH_PHASE[ray_index]).ravel()[0])
        top = float(np.asarray(traced_rays.TOP[ray_index]).ravel()[0])
        print(
            f"ray {ray_index:02d}: path={branch_path!r} "
            f"surfaces={surface_path} power={branch_power:.6g} "
            f"phase={branch_phase:.6g} deg TOP={top:.6g} mm"
        )
    x_axis, y_axis, interferogram = compute_detector_interferogram(traced_rays)
    print(
        "interferogram: "
        f"{interferogram.shape[1]}x{interferogram.shape[0]} pixels, "
        f"Imin={float(np.nanmin(interferogram)):.6g}, Imax={float(np.nanmax(interferogram)):.6g}, "
        f"detector_x=[{x_axis[0]:.6g}, {x_axis[-1]:.6g}] mm"
    )
