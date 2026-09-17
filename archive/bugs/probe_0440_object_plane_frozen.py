"""bugs/0440 -- the object plane vanished after the 0433 freeze/snap.

Chain under test (all display-free after the app builds):
  frozen/snapped rows carry BAKED desp/tilt (ScenePlacement breadcrumbs)
  -> _paraxial_reference_rows_for_layout must UNFOLD them (not raise)
  -> _shared_first_order_reference is not None
  -> _current_finite_paraxial_magnification is finite
  -> detector_coverage_metrics(object) FOV halves > 0
  -> detector_coverage_overlay_specs contains "object_fov_rect"  (the drawn
     "Object Plane" the user lost -- flag_20260726_111415_152).

Also guards: a genuinely HAND-TILTED prescription row (no breadcrumb) still
trips the centered guard -- the 0440 unfold is breadcrumb-scoped.
"""
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.detector_coverage_overlay import (
    detector_coverage_metrics,
    detector_coverage_overlay_specs,
)

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
failures: list[str] = []


def check(ok: bool, note: str) -> None:
    print(("ok  " if ok else "FAIL"), note)
    if not ok:
        failures.append(note)


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        pristine_mag = app._current_finite_paraxial_magnification()
        check(
            pristine_mag is not None and np.isfinite(pristine_mag),
            f"pristine magnification finite ({pristine_mag})",
        )

        # user round-2 order: delete FIRST (0433 freeze), then add the BS plate
        m1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([m1])
        frozen_ref = app._shared_first_order_reference()
        frozen_mag = app._current_finite_paraxial_magnification()
        check(frozen_ref is not None, "post-freeze shared first-order reference is not None")
        check(
            frozen_mag is not None and np.isfinite(frozen_mag),
            f"post-freeze magnification finite ({frozen_mag}); pristine was {pristine_mag}",
        )

        app.add_beam_splitter_to_led(kind="plate")
        chain = [
            i
            for i, r in enumerate(app.rows)
            if getattr(r, "surface", None) in ("Standard", "Thin Lens", "Aperture", "Image")
            and i > 0
            and "next gap" not in str(getattr(r, "name", ""))
            and "Promoted" not in str(getattr(r, "name", ""))
        ]
        rec = {
            "axis_id": "axis:global:split",
            "axis_label": "BS reflect",
            "points": np.array([(0.0, 0.0, 41.8), (193.3, 0.0, 41.8)]),
        }
        app.snap_rows_to_axis(chain, rec)
        snapped_ref = app._shared_first_order_reference()
        snapped_mag = app._current_finite_paraxial_magnification()
        check(snapped_ref is not None, "post-snap shared first-order reference is not None")
        check(
            snapped_mag is not None and np.isfinite(snapped_mag),
            f"post-snap magnification finite ({snapped_mag})",
        )

        if snapped_mag is not None and np.isfinite(snapped_mag):
            metrics = detector_coverage_metrics(23.0, 23.0, 16.29, snapped_mag)
            check(
                metrics.object_fov_half_width > 1e-9,
                f"object FOV half-width > 0 ({metrics.object_fov_half_width:.3f})",
            )
            specs = detector_coverage_overlay_specs(
                (0.0, 0.0, 0.0), (100.0, 0.0, 41.8), metrics, object_mode_finite=True
            )
            kinds = [s.get("kind") for s in specs]
            check("object_fov_rect" in kinds, f"overlay specs contain object_fov_rect ({kinds})")

        # NEGATIVE control: a hand-tilted prescription row (no breadcrumb) must
        # still trip the centered guard -- reload pristine, tilt a thin lens.
        app.load_layout_by_name("az85")
        thin = next(i for i, r in enumerate(app.rows) if getattr(r, "surface", None) == "Thin Lens")
        app.rows[thin].tilt_x = 5.0
        hand_ref = app._shared_first_order_reference()
        check(hand_ref is None, "hand-tilted prescription row still yields no reference (guard kept)")
    finally:
        app.destroy()

    if failures:
        print(f"RESULT: FAIL ({len(failures)})")
        return 1
    print("RESULT: PASS -- object plane chain restored on frozen/snapped scenes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
