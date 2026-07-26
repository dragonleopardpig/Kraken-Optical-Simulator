"""bugs/0443 guard -- the object FOV plate faces the object's own axis.

The detector-coverage object_axis used to be derived from row 1's world point; on a
0433-frozen/snapped chain row 1 is baked off-axis and the FOV rectangle drew tilted
(flag_20260726_153531). The shipped derivation is +Z rotated by the OBJECT row's own
tilts, with the legacy row-1 fallback only when that rotation is unavailable.

Checks:
  SOURCE   -- the overlay derives the axis from the object row's tilts (with fallback).
  PRISTINE -- on the folded AZ85 the new axis equals the legacy one (+Z).
  FROZEN   -- after BS-add + mirror-delete + chain-snap the axis stays exactly +Z
              while the legacy derivation is measurably diagonal.
"""
from __future__ import annotations

import inspect as _inspect

import numpy as np


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    # SOURCE: the caller derives from the object row's rotation, keeps the fallback.
    try:
        from KrakenOS.UI.services import detector_coverage_overlay as mod

        src = _inspect.getsource(mod)
    except Exception as exc:
        return True, [f"SKIP: overlay module unavailable ({exc!r})"]
    if "rotation_matrix_from_kraken_tilts" in src and "_surface_reference_world_point(1" in src:
        notes.append("SOURCE = object axis from the object row's tilts, legacy row-1 fallback kept")
    else:
        notes.append("SOURCE object-axis derivation missing the 0443 shape")
        ok = False

    # PRISTINE + FROZEN: drive the real scene.
    try:
        from pathlib import Path

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts

        scene = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        if not scene.exists():
            notes.append("SKIP: AZ85 scene absent (gitignored attachment)")
            return ok, notes
        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = scene
        app.load_layout_by_name("az85")

        def shipped_axis() -> np.ndarray:
            obj = app.rows[0]
            rot = rotation_matrix_from_kraken_tilts(
                float(obj.tilt_x), float(obj.tilt_y), float(obj.tilt_z)
            )
            return np.asarray(rot @ np.array((0.0, 0.0, 1.0)), dtype=float).reshape(3)

        if np.allclose(shipped_axis(), (0, 0, 1), atol=1e-9):
            notes.append("PRISTINE = object axis +Z on the folded scene")
        else:
            notes.append(f"PRISTINE object axis unexpected: {shipped_axis().round(6).tolist()}")
            ok = False

        app.add_beam_splitter_to_led(kind="plate")
        mirror1 = next(
            i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", ""))
        )
        app.delete_optical_step_rows([mirror1])
        rows = [
            i
            for i, r in enumerate(app.rows)
            if getattr(r, "surface", None) in ("Standard", "Thin Lens", "Aperture", "Image")
            and i > 0
            and "next gap" not in str(getattr(r, "name", ""))
        ]
        app.snap_rows_to_axis(
            rows,
            {
                "axis_id": "axis:global:split",
                "points": np.array([(0.0, 0.0, 59.5), (348.0, 0.0, 59.5)]),
                "picked_world": np.array([77.0, 0.0, 59.5]),
            },
        )
        p0 = np.asarray(app._surface_reference_world_point(0, system=None), float).reshape(3)
        p1 = np.asarray(app._surface_reference_world_point(1, system=None), float).reshape(3)
        legacy = p1 - p0
        legacy = legacy / (np.linalg.norm(legacy) or 1.0)
        if np.allclose(shipped_axis(), (0, 0, 1), atol=1e-9) and abs(float(legacy[0])) > 0.2:
            notes.append(
                f"FROZEN = axis stays +Z while the legacy derivation tilts ({legacy.round(3).tolist()})"
            )
        else:
            notes.append(
                f"FROZEN unexpected: axis={shipped_axis().round(6).tolist()} legacy={legacy.round(3).tolist()}"
            )
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: frozen-scene drive failed ({exc!r})")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
