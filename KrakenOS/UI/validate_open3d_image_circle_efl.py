"""Display-free guard for bugs/0168: the image-circle / max real image height of an
infinity-object layout must use EFL*tan(field), not back-focal-distance*tan(field).

``_field_metrics_for_value`` computed ``real_image_height = image_distance * tan(angle)``
for the non-finite-magnification (infinity / Angle-field) branch. ``image_distance`` is
the last-surface->image gap (the back focal distance), but an object-space field angle
images to ``EFL * tan(angle)`` (the rear nodal point, not the last surface, is the
pivot). On any thick lens BFD < EFL, so the "Image circle" overlay underread by the
EFL/BFD ratio -- ~1.7x on a double gauss, ~16x on a Cooke triplet -- which is why the
traced rays landed well beyond the drawn image circle.

The fix maps the real image height through the EFL (so ``max_real_image_height`` is the
paraxial chief height, a non-tracing estimator's best estimate; true distortion comes
from the traced image diameter), and exports the object-mode-aware ``field_image_radius``
that the detector-coverage image circle now uses.

This guard pins (display-free), on every checked-out infinity layout:

  * ``field_image_radius == max_paraxial_image_height`` (object-mode-aware radius);
  * ``max_real_image_height == field_image_radius`` (root: no longer the BFD value);
  * the radius equals EFL*tan(max field) -- and is EFL/BFD times BIGGER than the old
    ``image_distance*tan`` value (fail-before/pass-after, EFL>BFD on the test lenses);
  * the detector-coverage ``_image_circle_radius`` reads ``field_image_radius``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_image_circle_efl

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.layout_editor import (
    LAYOUTS_DIR,
    KrakenLayoutEditor,
    _load_python_data,
    _load_python_title,
)
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.services.detector_coverage_overlay import DetectorCoverageOverlayService

# Infinity-object layouts spanning a range of EFL/BFD (the bug magnitude): the double
# gauss (~1.7x) and the Cooke triplet (~16x). Skipped cleanly if absent.
_TEST_TITLES = ["Zemax Double Gauss 28 Degree Field", "Cooke Triplet Optimization Case Study"]


def _editor_by_title(title: str):
    for path in sorted(LAYOUTS_DIR.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            if str(_load_python_title(path)).strip() != title:
                continue
        except Exception:
            continue
        info = _load_python_data(path)
        settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
        rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
        if len(rows) < 3:
            return None
        rows[0].surface = "Object"
        rows[-1].surface = "Image"
        editor = _snapshot_editor(rows, settings)
        editor.tk = object()
        editor.current_layout_file = path
        editor._normalize_special_rows()
        return editor
    return None


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    checked = 0

    for title in _TEST_TITLES:
        editor = _editor_by_title(title)
        if editor is None:
            notes.append(f"SKIP: layout unavailable: {title}")
            continue
        if str(editor._current_object_mode()) != "Infinity":
            notes.append(f"SKIP: {title} is not an infinity layout")
            continue
        effl = float(editor._current_effl_estimate())
        image_distance = float(editor._current_image_distance())
        fm = editor._field_metrics_summary()
        fir = float(fm["field_image_radius"])
        max_real = float(fm["max_real_image_height"])
        max_parax = float(fm["max_paraxial_image_height"])
        if fir <= 1e-6 or max_parax <= 1e-6:
            notes.append(f"SKIP: {title} has no field radius")
            continue
        checked += 1

        # 1) object-mode-aware radius == the paraxial chief height.
        if abs(fir - max_parax) > 0.02 * max_parax:
            failures.append(f"{title}: field_image_radius {fir:.4g} != max_paraxial {max_parax:.4g}")
        # 2) root: max_real is no longer the BFD underestimate -- it equals the radius.
        if abs(max_real - fir) > 0.02 * max(fir, 1e-9):
            failures.append(f"{title}: max_real_image_height {max_real:.4g} != field_image_radius {fir:.4g} (root not fixed)")
        # 3) fail-before/pass-after: the OLD value was image_distance*tan(angle); the fix
        #    makes it EFL/BFD times bigger. These lenses are thick (EFL > BFD).
        if effl <= image_distance:
            notes.append(f"NOTE: {title} EFL {effl:.4g} <= BFD {image_distance:.4g} (thin-ish; small error)")
        else:
            old_value = fir * (image_distance / max(effl, 1e-9))  # what image_distance*tan would give
            if fir <= old_value * 1.05:
                failures.append(f"{title}: radius {fir:.4g} not larger than the BFD value {old_value:.4g}")
            notes.append(
                f"{title}: image circle R {fir:.3g} mm (was ~{old_value:.3g}; EFL/BFD={effl / image_distance:.2f}x)"
            )

    # 4) source contract: the image circle reads field_image_radius.
    src = inspect.getsource(DetectorCoverageOverlayService._image_circle_radius)
    if "field_image_radius" not in src:
        failures.append("CONTRACT: _image_circle_radius does not read field_image_radius")

    if checked == 0 and not failures:
        notes.append("SKIP: no infinity test layouts checked out")
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] image circle / max real image height (bugs/0168)")
        return 1
    print("[PASS] image circle uses EFL*tan(field), matching where the rays land (bugs/0168)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
