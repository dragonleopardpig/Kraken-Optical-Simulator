#!/usr/bin/env python3
"""Reproduce flag_20260715_092801_523: after a camera is deleted the FOV / Max
sensor / Image circle overlay remains.

0311 fixed the LEGACY (no-stash) decouple branch but gated the field un-pin on
``_camera_pinned_field`` -- a flag set ONLY by ``_apply_camera_coverage_autofill``.
This probe drives the REAL MV-150 editor headless through three paths and prints
the field type / value / image-circle radius after delete, to find the path where
the flag is never set so the reset is skipped and the overlay lingers:

  A  interactive folder-import couple -> delete           (stash + flag -> works)
  B1 save -> reload (camera valid in DB) -> delete         (stash restored -> works)
  B2 save -> reload (camera INVALID in DB) -> delete       (no stash, no flag -> BUG)

Run: .devenv/state/venv/bin/python bugs/diag_0312_camera_delete_withstash.py
"""
from __future__ import annotations

import contextlib

from KrakenOS.common_optical_layouts.machine_vision_150mm_datasheet_1x import SETTINGS, SURFACES
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
from KrakenOS.UI import camera_database as camdb
from KrakenOS.UI.camera_database import CAMERA_DATABASE, camera_image_coverage_mm, CAMERA_NONE_LABEL

CAMERA = "BC-OM25M"


def _radius(app):
    try:
        return float(app._field_metrics_summary().get("field_image_radius"))
    except Exception:
        return None


def _snap(app, tag):
    fv = app.field_value_var.get() if hasattr(app, "field_value_var") else "?"
    stash = getattr(app, "_camera_coverage_precouple_stash", None)
    pinned = getattr(app, "_camera_pinned_field", "<unset>")
    try:
        mode = app._current_image_diameter_mode()
    except Exception:
        mode = "?"
    try:
        imgdia = float(app.rows[-1].diameter) if app.rows and app.rows[-1].surface == "Image" else None
    except Exception:
        imgdia = None
    try:
        sig = app._field_matches_camera_autofill_signature()
    except Exception as exc:
        sig = f"err:{exc}"
    print(f"    [{tag}] field={app._current_field_type()!r} val={fv!r} "
          f"radius={_radius(app)} stash={'set' if stash else None} pinned={pinned} "
          f"imgmode={mode!r} imgdia={imgdia} sig={sig}")


def _fresh_editor():
    app = KrakenLayoutEditor(headless=True)
    app.rows = [
        SurfaceRow(**{k: v for k, v in s.items() if k in SurfaceRow.__dataclass_fields__})
        for s in SURFACES
    ]
    with contextlib.suppress(Exception):
        app._auto_assign_missing_elements(app.rows)
    app._apply_layout_settings(SETTINGS)
    app._apply_initial_field_defaults()
    app._normalize_special_rows()
    app._sync_table()
    return app


def _couple_interactive(app):
    """Mirror _couple_camera_model_from_step 3232-3234."""
    app._stash_camera_precouple_field_state()
    if hasattr(app, "camera_model_var"):
        app.camera_model_var.set(CAMERA)
    app._apply_camera_coverage_autofill(CAMERA)


def _load_path_autofill(app):
    """Mirror load_layout_by_name lines 535-538."""
    if hasattr(app, "_current_camera_model"):
        loaded = app._current_camera_model()
        if loaded != CAMERA_NONE_LABEL:
            app._apply_camera_coverage_autofill(loaded)


def _verdict(app, tag):
    r = _radius(app)
    ok = not (r and r > 1e-6)
    print(f"  == {tag}: {'OK (overlay clears)' if ok else f'BUG -- image circle radius {r:.4f} (draws Ø{2*r:.1f})'}")
    return ok


def scenario_A():
    print("SCENARIO A: interactive folder-import couple -> delete")
    app = _fresh_editor()
    _snap(app, "pre")
    _couple_interactive(app)
    _snap(app, "coupled")
    app._decouple_camera_model()
    _snap(app, "deleted")
    _verdict(app, "A")
    with contextlib.suppress(Exception):
        app.destroy()


def scenario_B(invalid_at_load: bool):
    tag = "B2 reload with camera INVALID in DB" if invalid_at_load else "B1 reload with camera valid in DB"
    print(f"\nSCENARIO {tag}")
    # --- session 1: couple + save
    app1 = _fresh_editor()
    _couple_interactive(app1)
    settings = app1._collect_layout_settings()
    rows_snapshot = [SurfaceRow(**{f: getattr(r, f) for f in SurfaceRow.__dataclass_fields__}) for r in app1.rows]
    print(f"    saved settings: camera_model={settings.get('camera_model')!r} "
          f"field_type={settings.get('field_type')!r} field_value={settings.get('field_value')!r} "
          f"stash={'set' if settings.get('camera_precouple_stash') else None}")
    with contextlib.suppress(Exception):
        app1.destroy()

    # --- session 2: fresh editor, load saved rows+settings
    removed_record = None
    if invalid_at_load:
        removed_record = CAMERA_DATABASE.pop(CAMERA, None)  # simulate camera not merged at load
    try:
        app2 = KrakenLayoutEditor(headless=True)
        app2.rows = rows_snapshot
        with contextlib.suppress(Exception):
            app2._auto_assign_missing_elements(app2.rows)
        app2._apply_layout_settings(settings)
        print(f"    (after _apply_layout_settings: pinned={getattr(app2, '_camera_pinned_field', '<unset>')} "
              f"camera_model_var={app2.camera_model_var.get()!r} field={app2._current_field_type()!r})")
        app2._normalize_special_rows()
        app2._sync_table()
        _load_path_autofill(app2)
        _snap(app2, "loaded")
        app2._decouple_camera_model()
        _snap(app2, "deleted")
        _verdict(app2, tag)
        with contextlib.suppress(Exception):
            app2.destroy()
    finally:
        if removed_record is not None:
            CAMERA_DATABASE[CAMERA] = removed_record


def main():
    print(f"CAMERA {CAMERA} in DB: {CAMERA in CAMERA_DATABASE}  coverage={camera_image_coverage_mm(CAMERA)}\n")
    scenario_A()
    scenario_B(invalid_at_load=False)
    scenario_B(invalid_at_load=True)


if __name__ == "__main__":
    main()
