"""Repro for bug 0099 — an OFF-axis STEP overlay drag must not adjust the optical distance / rays.

Flagged flag_20260621_142611..142758 (4 recordings): a beam-splitter STEP imported into the LENS
overlay slot and dropped off the rays still moved a thickness dimension + the ray path when dragged.
Root cause = the item-1/4 "move together" glue (camera->detector / lens->object-gap) redirecting the
axial drag for ANY lens/camera overlay, even a foreign body placed off the axis.

Fix = gate the axial<->distance redirect on `overlay_on_axis` (the overlay's lateral offset ~0). This
display-free repro asserts: an ON-axis lens axial drag still redirects (glue intact); an OFF-axis lens
axial drag leaves the optical gap UNCHANGED and only moves the body.

Run: .devenv/state/venv/bin/python bugs/repro_0099.py
"""
from pathlib import Path
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
from KrakenOS.common_optical_layouts.machine_vision_150mm_measured import SURFACES, SETTINGS


def _load():
    app = KrakenLayoutEditor(headless=True)
    app.current_layout_file = Path("machine_vision_150mm_measured.py")
    app.rows = [SurfaceRow(**{k: v for k, v in s.items() if k in SurfaceRow.__dataclass_fields__}) for s in SURFACES]
    app._auto_assign_missing_elements(app.rows)
    app._apply_layout_settings(SETTINGS)
    return app


def main() -> int:
    # On-axis lens axial drag -> redirects to the object gap (item-4 glue still works).
    app = _load()
    front0 = float(app._lens_front_datum_z())
    app.translate_step_overlay("lens", [0.0, 0.0, 10.0], record_history=False, refresh=False)
    front_on = float(app._lens_front_datum_z())
    app.destroy()

    # Off-axis lens (lateral offset first), then axial drag -> gap UNCHANGED, body moves only.
    app = _load()
    app.translate_step_overlay("lens", [0.0, 30.0, 0.0], record_history=False, refresh=False)
    front_b0 = float(app._lens_front_datum_z())
    app.translate_step_overlay("lens", [0.0, 0.0, 10.0], record_history=False, refresh=False)
    front_off = float(app._lens_front_datum_z())
    off = [round(v, 3) for v in app._step_placement_offset_xyz("lens")]
    app.destroy()

    ok_on = abs(front_on - (front0 + 10.0)) <= 1e-6
    ok_off = abs(front_off - front_b0) <= 1e-6 and abs(off[1] - 30.0) <= 1e-6 and abs(off[2] - 10.0) <= 1e-6
    print(f"ON-AXIS  redirect: front {front0:.1f} -> {front_on:.1f} (want +10)  PASS={ok_on}")
    print(f"OFF-AXIS body-only: front {front_b0:.1f} -> {front_off:.1f} (want unchanged), offset={off}  PASS={ok_off}")
    if ok_on and ok_off:
        print("repro_0099: PASS")
        return 0
    print("repro_0099: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
