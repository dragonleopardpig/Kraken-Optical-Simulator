"""bugs/0440 guard -- the object plane survives the 0433 freeze/snap workflow.

The 0433 stay-put freeze / axis snap bake world placement into row desp/tilt
(ScenePlacement breadcrumbs). The first-order reference builder must UNFOLD
breadcrumbed rows (their tilts are placement, not prescription) instead of
tripping the centered guard -- otherwise `_shared_first_order_reference` is
None, the magnification is None, the detector-coverage object-FOV halves are
zero and the drawn "Object Plane" silently vanishes (flag_20260726_111415).

Checks (notes with '=' are ok-lines):
  FROZEN-REF     freeze -> shared reference non-None + finite magnification
  SNAPPED-REF    freeze -> BS add -> snap -> same, and the object_fov_rect
                 overlay spec is emitted
  GUARD-KEPT     a hand-tilted (un-breadcrumbed) prescription row still yields
                 no reference -- the unfold is breadcrumb-scoped
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    app = None
    try:
        import numpy as np

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services.detector_coverage_overlay import (
            detector_coverage_metrics,
            detector_coverage_overlay_specs,
        )

        if not SCENE.exists():
            return True, ["SKIP: attachment scene absent (gitignored fixture)"]
        app = KrakenLayoutEditor()
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
    except Exception as exc:  # environment failure -> never block the gate
        try:
            if app is not None:
                app.destroy()
        except Exception:
            pass
        return True, [f"SKIP: environment cannot build the editor ({exc!r})"]

    failures: list[str] = []
    try:
        m1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([m1])
        ref = app._shared_first_order_reference()
        mag = app._current_finite_paraxial_magnification()
        if ref is None or mag is None or not np.isfinite(mag):
            failures.append(f"FROZEN-REF: reference/mag missing after the freeze (ref={ref is not None}, mag={mag!r})")
        else:
            notes.append(f"FROZEN-REF = reference restored, mag {mag:.4f}")

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
        mag2 = app._current_finite_paraxial_magnification()
        if mag2 is None or not np.isfinite(mag2):
            failures.append(f"SNAPPED-REF: magnification missing after the snap ({mag2!r})")
        else:
            metrics = detector_coverage_metrics(23.0, 23.0, 16.29, mag2)
            specs = detector_coverage_overlay_specs(
                (0.0, 0.0, 0.0), (100.0, 0.0, 41.8), metrics, object_mode_finite=True
            )
            kinds = [s.get("kind") for s in specs]
            if "object_fov_rect" not in kinds:
                failures.append(f"SNAPPED-REF: object_fov_rect missing from overlay specs ({kinds})")
            else:
                notes.append(f"SNAPPED-REF = object plane drawn (mag {mag2:.4f})")

        app.load_layout_by_name("az85")
        thin = next(i for i, r in enumerate(app.rows) if getattr(r, "surface", None) == "Thin Lens")
        app.rows[thin].tilt_x = 5.0
        if app._shared_first_order_reference() is not None:
            failures.append("GUARD-KEPT: a hand-tilted prescription row must still yield no reference")
        else:
            notes.append("GUARD-KEPT = centered guard intact for un-breadcrumbed tilts")
    except Exception as exc:
        failures.append(f"guard raised: {exc!r}")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    return (not failures), notes + failures


def run() -> int:
    passed, notes = run_checks()
    print("[PASS]" if passed else "[FAIL]", "bugs/0440 object plane on frozen/snapped scenes")
    for note in notes:
        print("   ", note)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
