#!/usr/bin/env python3
"""Live headless promote guard for bugs/0079 (re-enabled 2026-06-18): promoting an
imported STEP overlay that straddles the optical axis must use the in-path axial
placement -- split the host gap at the solid's true Z, keep the lens AND image
EXACTLY where they were -- and must NOT raise (the bugs/0081 kill-switch was for a
kwarg TypeError later fixed in bugs/0082).

Boots the real inspector (its own Xvfb), imports the tracked prism into the
object gap, promotes with ``inpath_axial_placement=True`` and asserts:
  * the promote succeeds (no raise) and inserts the solid + a trailing AIR spacer,
  * the cube + spacer fit the original gap (the lens stays fixed),
  * the Image moves to the plate-shifted focus t(1-1/n) further (image-at-focus,
    bugs/0093: so the transmit ray reaches its detector instead of stopping at the
    bare focus), while the lens does not move.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_inpath_promote_live

Exit: 0 = pass (incl. environment skip), 1 = regression.
"""
from __future__ import annotations

import numpy as np


def _vertices(rows):
    out, running = [], 0.0
    for r in rows:
        out.append(running)
        running += float(getattr(r, "thickness", 0.0) or 0.0)
    return out


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond, label):
        notes.append(("PASS " if cond else "FAIL ") + label)

    try:
        from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP
    except Exception as exc:  # pragma: no cover - env skip
        notes.append(f"SKIP: prism fixture import failed ({type(exc).__name__})")
        return True, notes
    if not PRISM_42779_STEP.exists():
        notes.append("SKIP: tracked prism STEP fixture missing")
        return True, notes

    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display
    from KrakenOS.UI.services import step_overlay_promotion as sop

    own_display = app is None
    xvfb = None
    if own_display:
        xvfb, disp_err = _ensure_display()
        if disp_err:
            notes.append(f"SKIP: no display for live promote ({disp_err})")
            return True, notes
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector, _import_step

        if app is None:
            app = KrakenLayoutEditor()
            inspector = _open_inspector(app)
        app.rows = [
            SurfaceRow(label="0", surface="Object", name="Object", thickness=200.0, diameter=25.0, glass="AIR"),
            SurfaceRow(label="1", surface="Surface", name="Lens front", rc=60.0, thickness=6.0, diameter=30.0, glass="N-BK7"),
            SurfaceRow(label="2", surface="Surface", name="Lens back", rc=-60.0, thickness=120.0, diameter=30.0, glass="AIR"),
            SurfaceRow(label="3", surface="Image", name="Image", thickness=0.0, diameter=35.0, glass="AIR"),
        ]
        app._sync_table()
        try:
            app.clear_step_imports()
        except Exception:
            pass
        inspector.show_rays_var.set(False)
        _import_step(app, PRISM_42779_STEP)
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks()

        ok(bool(sop._INPATH_AXIAL_PLACEMENT_ENABLED),
           "0079 in-path axial placement is ENABLED (kill switch off)")
        before_image_z = _vertices(app.rows)[-1]
        original_gap = float(app.rows[0].thickness)  # object->lens gap before insertion

        try:
            out = app.promote_imported_step_to_optical_solid_row(
                "optical", open_face_editor=False, clear_overlay=True,
                refresh_open_3d=False, inpath_axial_placement=True,
            )
            raised = None
        except Exception as exc:  # the very thing the kill switch guarded
            raised = exc
            out = None

        ok(raised is None, f"in-path promote does not raise ({type(raised).__name__ if raised else 'ok'})")
        if raised is not None or not isinstance(out, dict) or out.get("row_index") is None:
            return (not any(l.startswith("FAIL") for l in notes)), notes

        slot = int(out["row_index"])
        # the split gap: preceding (slot-1) + solid (slot) + trailing spacer (slot+1)
        pre_t = float(app.rows[slot - 1].thickness)
        solid_t = float(app.rows[slot].thickness)
        trail_t = float(app.rows[slot + 1].thickness)
        ok(abs((pre_t + solid_t + trail_t) - original_gap) < 1e-6,
           f"cube fits the original gap (lens stays put): {pre_t}+{solid_t}+{trail_t} == {original_gap}")
        after_image_z = _vertices(app.rows)[-1]
        # bugs/0093 image-at-focus: a refracting in-path solid pushes the focus
        # FURTHER by the plane-parallel-plate shift t(1-1/n); the Image moves THERE
        # (so the transmit ray reaches its detector), while the lens stays fixed (the
        # cube + spacer still fit the original gap above).
        focus_shift = after_image_z - before_image_z
        ok(0.0 < focus_shift < solid_t,
           f"image moved to the plate-shifted focus (0 < {focus_shift:.3f} < glass depth {solid_t})")
        ok(str(getattr(app.rows[slot + 1], "glass", "")).upper() == "AIR",
           "trailing spacer is a flat AIR gap")
    finally:
        if own_display and xvfb is not None:
            try:
                xvfb.terminate()
            except Exception:
                pass

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    print("In-path live promote validation", "passed." if passed else "FAILED:")
    if not passed:
        for line in notes:
            if line.startswith("FAIL"):
                print(f"- {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
