"""Load and sample a Zemax Wavefront Map text export.

Run from the repository root:

    python KrakenOS/Examples/Examp_Zemax_Wavefront_Map_Import.py path/to/wfm.txt

If no file path is supplied, the example writes a small synthetic Zemax-style
UTF-16 text export into a temporary directory and imports that file.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

from KrakenOS.UI.zemax_wavefront import load_zemax_wavefront_map, sample_wavefront_grid


def _write_synthetic_zemax_wavefront_map(path: Path) -> None:
    axis = np.linspace(-1.0, 1.0, 9)
    xx, yy = np.meshgrid(axis, axis)
    values_waves = 0.12 * (xx * xx + yy * yy - 0.5) + 0.03 * xx - 0.02 * yy
    lines = [
        "Zemax Wavefront Map",
        "Wavelength: 0.550000 um",
        "Pupil grid size: 9 by 9",
        "Data are in waves",
        "",
    ]
    for row in np.flipud(values_waves):
        lines.append(" ".join(f"{float(value): .8E}" for value in row))
    path.write_text("\n".join(lines), encoding="utf-16le")


def _sample_reference_grid(path: Path) -> None:
    reference = load_zemax_wavefront_map(path)
    print(f"File: {reference.path}")
    print(f"Grid: {reference.shape[1]} x {reference.shape[0]}")
    print(f"Wavelength: {reference.wavelength_um:.6g} um")
    print(f"Units: {reference.raw_units}")
    print(f"P-V: {reference.pv_waves:.6g} waves")
    print(f"RMS: {reference.rms_waves:.6g} waves")

    x_norm = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])
    y_norm = np.zeros_like(x_norm)
    samples_waves = sample_wavefront_grid(reference.values_waves, x_norm, y_norm)
    samples_nm = samples_waves * reference.wavelength_um * 1000.0

    print("\nNormalized pupil samples along Y=0:")
    print("x_norm | W [waves] | W [nm]")
    print("--- | --- | ---")
    for x_value, waves, nm_value in zip(x_norm, samples_waves, samples_nm):
        print(f"{x_value:+.2f} | {waves:+.6g} | {nm_value:+.6g}")


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        _sample_reference_grid(Path(argv[1]).expanduser())
        return 0

    with tempfile.TemporaryDirectory(prefix="kraken-zemax-wfm-example-") as temp_dir:
        path = Path(temp_dir) / "synthetic_zemax_wavefront_map.txt"
        _write_synthetic_zemax_wavefront_map(path)
        _sample_reference_grid(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
