from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.zemax_wavefront import load_zemax_wavefront_map, sample_wavefront_grid


@dataclass
class ZemaxWavefrontImportCheck:
    check: str
    ok: bool
    detail: str


def _synthetic_zemax_wavefront_text(path: Path, wavelength_um: float = 0.55, size: int = 9) -> np.ndarray:
    axis = np.linspace(-1.0, 1.0, size)
    xx, yy = np.meshgrid(axis, axis)
    values = 0.12 * (xx * xx + yy * yy - 0.5) + 0.035 * xx - 0.02 * yy
    lines = [
        "Zemax Wavefront Map",
        f"Wavelength: {wavelength_um:.6f} µm",
        f"Pupil grid size: {size} by {size}",
        "Data are in waves",
        "",
    ]
    # The importer follows Zemax/STOP-utils convention and flips exported data
    # vertically after parsing, so write the exported orientation here.
    exported = np.flipud(values)
    for row in exported:
        lines.append(" ".join(f"{float(value): .8E}" for value in row))
    path.write_text("\n".join(lines), encoding="utf-16le")
    return values


def _synthetic_zemax_wavefront_text_wavelength_nm(path: Path, values: np.ndarray, wavelength_um: float = 0.55) -> None:
    size = int(values.shape[0])
    lines = [
        "Zemax Wavefront Map",
        f"Wavelength: {wavelength_um * 1000.0:.6f} nm",
        f"Pupil grid size: {size} by {size}",
        "Data are in waves",
        "",
    ]
    for row in np.flipud(values):
        lines.append(" ".join(f"{float(value): .8E}" for value in row))
    path.write_text("\n".join(lines), encoding="utf-16le")


def validate_zemax_wavefront_import() -> list[ZemaxWavefrontImportCheck]:
    checks: list[ZemaxWavefrontImportCheck] = []
    with tempfile.TemporaryDirectory(prefix="kraken-zemax-wfm-") as temp_dir:
        path = Path(temp_dir) / "synthetic_wavefront_map.txt"
        expected = _synthetic_zemax_wavefront_text(path)
        reference = load_zemax_wavefront_map(path)
        checks.append(
            ZemaxWavefrontImportCheck(
                "parse",
                reference.shape == expected.shape
                and abs(reference.wavelength_um - 0.55) < 1e-12
                and np.allclose(reference.values_waves, expected, atol=1e-10),
                f"shape={reference.shape}, lambda={reference.wavelength_um:.6g}, pv={reference.pv_waves:.6g}",
            )
        )

        path_nm = Path(temp_dir) / "synthetic_wavefront_map_wavelength_nm.txt"
        _synthetic_zemax_wavefront_text_wavelength_nm(path_nm, expected)
        reference_nm_header = load_zemax_wavefront_map(path_nm)
        checks.append(
            ZemaxWavefrontImportCheck(
                "wavelength-nm-header",
                reference_nm_header.raw_units == "waves"
                and abs(reference_nm_header.wavelength_um - 0.55) < 1e-12
                and np.allclose(reference_nm_header.values_waves, expected, atol=1e-10),
                f"lambda={reference_nm_header.wavelength_um:.6g} um, raw_units={reference_nm_header.raw_units}",
            )
        )

        sample_axis = np.linspace(-1.0, 1.0, 7)
        xx, yy = np.meshgrid(sample_axis, sample_axis)
        samples = sample_wavefront_grid(reference.values_waves, xx.ravel(), yy.ravel())
        checks.append(
            ZemaxWavefrontImportCheck(
                "sample",
                np.count_nonzero(np.isfinite(samples)) == samples.size,
                f"samples={samples.size}, finite={np.count_nonzero(np.isfinite(samples))}",
            )
        )

        editor = KrakenLayoutEditor.__new__(KrakenLayoutEditor)
        editor._zemax_wavefront_reference = reference
        comparison = editor._compare_zemax_wavefront_reference(xx.ravel(), yy.ravel(), samples, 0.55)
        checks.append(
            ZemaxWavefrontImportCheck(
                "compare",
                bool(comparison and comparison.get("ok"))
                and float(comparison.get("residual_rms_waves", np.inf)) < 1e-9,
                "ok={ok}, orientation={orientation}, rms={rms:.6g} waves".format(
                    ok=bool(comparison and comparison.get("ok")),
                    orientation=(comparison or {}).get("orientation", ""),
                    rms=float((comparison or {}).get("residual_rms_waves", np.inf)),
                ),
            )
        )
    return checks


def _print_table(checks: list[ZemaxWavefrontImportCheck]) -> None:
    print("KrakenOS Zemax Wavefront Map import validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Zemax Wavefront Map text import and comparison.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_zemax_wavefront_import()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
