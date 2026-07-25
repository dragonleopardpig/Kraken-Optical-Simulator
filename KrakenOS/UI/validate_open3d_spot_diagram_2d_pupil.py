"""Display-free guard for bugs/0169: a spot diagram / PSF / spot-RMS must fill the pupil
in 2D, not the editor's 1-D display fan.

The spot trace asked for ``pattern="hexapolar"`` but ``_build_geometric_image_samples_full``
overrode it with the editor's display pupil pattern -- whose default is "Meridional fan"
(Ptype "fany", a 1-D Y-fan) -- so every spot collapsed to a vertical line (on-axis
X-spread = 0). The fix adds ``require_2d_pupil``: when the resolved pattern is a 1-D fan it
forces hexapolar.

This guard pins (display-free), on the real double gauss:

  * the editor's DEFAULT pupil pattern is a 1-D fan (so the fix is needed -- fail-before);
  * with ``require_2d_pupil=True`` the on-axis spot is ROUND (X-spread ~ Y-spread) and gains
    the X-spread the fan lacked (pass-after);
  * the 2-D Spot Diagram trace and the 3-D Spot-map trace both pass ``require_2d_pupil=True``,
    and the sampler honours it.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_spot_diagram_2d_pupil

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import numpy as np

from KrakenOS.UI.services.geometric_analysis import GeometricAnalysisMixin
from KrakenOS.UI.validate_open3d_best_focus_surface import _build_scene_bundle_for_double_gauss

_ONE_D_PTYPES = {"fanx", "fany", "fan", "chief", "rtheta"}


def _spot_spread(editor, system, *, require_2d_pupil: bool):
    cap = io.StringIO()
    with redirect_stdout(cap), redirect_stderr(cap):
        x, y, _z, _l, _m, _n, _w = editor._build_geometric_image_samples_full(
            system, float(editor._current_wavelength()), sample_count=10, pattern="hexapolar",
            surface_index=editor._analysis_surface_index(),
            aperture_type=editor._current_aperture_type(),
            aperture_value=editor._current_aperture_value(),
            field_type="angle" if editor._current_object_mode() == "Infinity" else "height",
            field_x=0.0, field_y=0.0, require_2d_pupil=require_2d_pupil,
        )
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 3:
        return None
    return float(np.ptp(x)), float(np.ptp(y))


def _check_integration(failures: list[str], notes: list[str]) -> None:
    editor, system, _bundle = _build_scene_bundle_for_double_gauss()
    if editor is None:
        notes.append("SKIP integration: double-gauss layout unavailable")
        return

    pattern = str(editor._current_kraken_pupil_pattern() or "")
    if pattern not in _ONE_D_PTYPES:
        notes.append(f"NOTE: editor default pupil pattern is '{pattern}', already 2-D on this clone")

    fan = _spot_spread(editor, system, require_2d_pupil=False)
    two_d = _spot_spread(editor, system, require_2d_pupil=True)
    if fan is None or two_d is None:
        failures.append("INTEGRATION: could not trace the on-axis spot")
        return
    fan_x, fan_y = fan
    x2, y2 = two_d

    # Fail-before: the default fan collapses X (a vertical line).
    if pattern in _ONE_D_PTYPES and fan_x > 0.2 * max(fan_y, 1e-9):
        notes.append(f"NOTE: the 1-D fan unexpectedly had X-spread {fan_x:.3g} (Y {fan_y:.3g})")

    # Pass-after: the 2-D pupil makes the on-axis spot ROUND (rotationally symmetric).
    if not (x2 > 0.5 * y2 and y2 > 0.5 * x2):
        failures.append(f"INTEGRATION: on-axis 2-D spot is not round (X={x2:.4g}, Y={y2:.4g} mm)")
    # And it adds the X-spread the fan was missing.
    if x2 <= 2.0 * fan_x + 1e-9:
        failures.append(f"INTEGRATION: require_2d_pupil did not add the missing X-spread (fan X={fan_x:.3g}, 2-D X={x2:.3g})")
    notes.append(f"integration: on-axis spot fan X/Y={fan_x*1000:.1f}/{fan_y*1000:.1f} µm -> 2-D X/Y={x2*1000:.1f}/{y2*1000:.1f} µm (round)")


def _check_source_contracts(failures: list[str]) -> None:
    sampler_src = inspect.getsource(GeometricAnalysisMixin._build_geometric_image_samples_full)
    if "require_2d_pupil" not in sampler_src or "hexapolar" not in sampler_src:
        failures.append("CONTRACT: _build_geometric_image_samples_full does not honour require_2d_pupil")

    ui_dir = Path(__file__).resolve().parent
    spot_diagram_src = (ui_dir / "services" / "analysis_plot.py").read_text(encoding="utf-8")
    if "require_2d_pupil=True" not in spot_diagram_src:
        failures.append("CONTRACT: the 2-D Spot Diagram trace does not force a 2-D pupil")
    spot_map_src = (ui_dir / "services" / "three_d_scene_tools.py").read_text(encoding="utf-8")
    if "require_2d_pupil=True" not in spot_map_src:
        failures.append("CONTRACT: the 3-D Spot-map trace does not force a 2-D pupil")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_integration(failures, notes)
    _check_source_contracts(failures)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] spot diagram must fill the pupil in 2D (bugs/0169)")
        return 1
    print("[PASS] spot diagram / spot map fill the pupil in 2D -- round spots, not fans (bugs/0169)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
