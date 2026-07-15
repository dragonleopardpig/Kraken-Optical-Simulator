"""Guard: deleting a camera un-pins the camera-set field so the image-circle /
object-FOV overlay clears (bugs/0311, extended for the orphaned-camera case in
bugs/0312).

Reported (recording flag_20260715_084524_992): "After camera deleted, FOV, Max
Sensor, Image circle remains." Deleting the BC-OM25M camera STEP dropped the
detector's explicit sensor (the label read "Max sensor", not "Sensor"), so the
decouple DID run -- but the green object-FOV cone, "Max sensor 23.0x23.0" and
"Image circle Ø32.6" overlays stayed on-screen.

Root cause: coupling a camera pins the field to ``Real Image Height`` = the
sensor half-diagonal (``_apply_camera_coverage_autofill``), and that field drives
``_image_circle_radius`` / the object-FOV box. On decouple WITHOUT a pre-couple
stash to restore (a layout that *loaded* with a camera coupled -- the stash is
interactive-only), the 0306 legacy branch flipped the image APERTURE Manual->Auto
but never touched that pinned field, so the image circle / FOV lingered.

Fix: the couple sets a ``_camera_pinned_field`` flag; the legacy decouple branch,
when that flag is set, resets the field back to the object-mode default (Angle for
an infinity object, Object Height for a finite one) via
``_reset_camera_pinned_field_to_default`` -- no camera means no coverage overlay.
The flag (not a bare ``field_type == "Real Image Height"`` test) is what makes this
safe: a surrogate that legitimately uses a Real Image Height field with NO camera
is never wiped, and a user who manually re-typed the field while a camera was
coupled keeps their choice.

This guard is DISPLAY-FREE (runs the REAL ``_decouple_camera_model`` on a stub):
  * A -- a camera-pinned legacy decouple un-pins the field to the object-mode
    default (Finite -> Object Height 0; Infinity -> Angle 0) and clears the flag.
  * B -- a surrogate with a legitimate Real Image Height field and NO camera pin is
    left untouched on decouple (no over-reach).
  * C -- a camera-pinned field the user manually re-typed away from Real Image
    Height is not reset (respects the override).
  * D -- the WITH-stash decouple still restores the exact pre-camera field and
    clears the pin flag.
  * F (bugs/0312) -- an ORPHANED camera (saved model absent from THIS machine's
    registry) loads with the flag unset, so the value signature (image aperture ==
    2 x Real Image Height = the sensor diagonal) un-pins the field instead.
  * G (bugs/0312) -- that signature stays narrow: a Manual Real Image Height field
    whose aperture is NOT twice the field value is left untouched.
  * E (structural) -- the couple sets ``_camera_pinned_field``; the decouple gates
    the reset on it AND the 0312 value signature; deleting a camera STEP decouples
    (clear_imported_step_overlay_state).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_camera_delete_field_unpin

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import KrakenOS.UI.layout_editor  # noqa: F401  -- injects the workbench editor globals
from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
from KrakenOS.UI.camera_database import CAMERA_NONE_LABEL, camera_image_coverage_mm


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Row:
    def __init__(self, surface, diameter):
        self.surface = surface
        self.diameter = diameter


class _Ed(LayoutTableWorkbenchMixin):
    def __init__(self, *, field_type, field_value, mode, pinned, object_mode="Finite",
                 stash=None, camera="BC-OM25M", image_diameter=32.5835):
        self.field_type_var = _Var(field_type)
        self.field_value_var = _Var(field_value)
        self.image_diameter_mode_var = _Var(mode)
        self.camera_model_var = _Var(camera)
        self.object_mode_var = _Var(object_mode)
        self.rows = [_Row("Object", 0.0), _Row("Image", image_diameter)]
        self._field_type_defaults = {field_type: field_value}
        self._last_field_type = field_type
        self._camera_coverage_precouple_stash = stash
        self._camera_pinned_field = pinned
        self.imported_camera_step_path = None

    def _current_field_type(self):
        return self.field_type_var.get()

    def _current_image_diameter_mode(self):
        return self.image_diameter_mode_var.get()

    def _current_object_mode(self):
        return self.object_mode_var.get()

    def _field_type_display_label(self, field_type):
        return field_type

    def _current_camera_record(self):
        return None

    def _set_image_diameter_mode(self, mode):
        self.image_diameter_mode_var.set(mode)

    def _apply_image_diameter_mode(self):
        pass

    def _sync_field_mode_ui(self):
        pass

    def _sync_object_diameter_from_manual_image(self):
        pass

    def _sync_table(self):
        pass

    def _sync_object_controls(self):
        pass


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    # A -- camera-pinned legacy (no-stash) decouple un-pins the field.
    fin = _Ed(field_type="Real Image Height", field_value="16.2917", mode="Manual", pinned=True,
              object_mode="Finite")
    fin._decouple_camera_model()
    ok(
        fin.field_type_var.get() == "Object Height" and float(fin.field_value_var.get()) == 0.0,
        f"A1 finite pin -> Object Height 0 (got {fin.field_type_var.get()} {fin.field_value_var.get()})",
    )
    ok(fin.camera_model_var.get() == CAMERA_NONE_LABEL, "A2 camera model reset to None")
    ok(fin._camera_pinned_field is False, "A3 pin flag cleared after decouple")
    ok(fin.image_diameter_mode_var.get() == "Auto", "A4 image aperture Manual -> Auto (0306 kept)")

    inf = _Ed(field_type="Real Image Height", field_value="16.2917", mode="Manual", pinned=True,
              object_mode="Infinity")
    inf._decouple_camera_model()
    ok(
        inf.field_type_var.get() == "Angle" and float(inf.field_value_var.get()) == 0.0,
        f"A5 infinity pin -> Angle 0 (got {inf.field_type_var.get()} {inf.field_value_var.get()})",
    )

    # B -- surrogate that legitimately uses Real Image Height with NO camera pin.
    surr = _Ed(field_type="Real Image Height", field_value="35.355", mode="Auto", pinned=False)
    surr._decouple_camera_model()
    ok(
        surr.field_type_var.get() == "Real Image Height" and surr.field_value_var.get() == "35.355",
        f"B unpinned surrogate field untouched (got {surr.field_type_var.get()} {surr.field_value_var.get()})",
    )

    # C -- camera-pinned but user re-typed the field away from Real Image Height.
    over = _Ed(field_type="Angle", field_value="5.0", mode="Manual", pinned=True)
    over._decouple_camera_model()
    ok(
        over.field_type_var.get() == "Angle" and over.field_value_var.get() == "5.0",
        f"C user override not reset (got {over.field_type_var.get()} {over.field_value_var.get()})",
    )

    # F (bugs/0312) -- ORPHANED camera: a layout saved with a camera not in THIS
    # machine's registry loads with camera_model forced to None, so the flag-setting
    # autofill never runs (pinned=False) -- yet the Real Image Height field is still
    # restored (Manual, image aperture = 2 x half-diagonal = the sensor diagonal).
    # Deleting the still-shown camera STEP must still un-pin via the value signature.
    orphan_fin = _Ed(field_type="Real Image Height", field_value="16.2917", mode="Manual",
                     pinned=False, object_mode="Finite", image_diameter=32.5835)
    orphan_fin._decouple_camera_model()
    ok(
        orphan_fin.field_type_var.get() == "Object Height" and float(orphan_fin.field_value_var.get()) == 0.0,
        f"F1 orphaned finite (no flag) -> Object Height 0 (got {orphan_fin.field_type_var.get()} {orphan_fin.field_value_var.get()})",
    )
    orphan_inf = _Ed(field_type="Real Image Height", field_value="16.2917", mode="Manual",
                     pinned=False, object_mode="Infinity", image_diameter=32.5835)
    orphan_inf._decouple_camera_model()
    ok(
        orphan_inf.field_type_var.get() == "Angle" and float(orphan_inf.field_value_var.get()) == 0.0,
        f"F2 orphaned infinity (no flag) -> Angle 0 (got {orphan_inf.field_type_var.get()} {orphan_inf.field_value_var.get()})",
    )

    # G (bugs/0312) -- signature stays NARROW: a Manual Real Image Height field whose
    # image aperture is NOT twice the field value is not the camera fingerprint, so an
    # unflagged decouple leaves it alone (only image_diameter == 2 x field_value resets).
    narrow = _Ed(field_type="Real Image Height", field_value="20.0", mode="Manual",
                 pinned=False, image_diameter=32.5835)
    narrow._decouple_camera_model()
    ok(
        narrow.field_type_var.get() == "Real Image Height" and narrow.field_value_var.get() == "20.0",
        f"G non-2x Manual RIH untouched (got {narrow.field_type_var.get()} {narrow.field_value_var.get()})",
    )

    # D -- real couple sets the flag; WITH-stash decouple restores + clears it.
    cov = camera_image_coverage_mm("Allied Vision hr25MCX")
    if cov is not None:
        d = _Ed(field_type="Object Height", field_value="3.2", mode="Auto", pinned=False)
        d._stash_camera_precouple_field_state()
        d.camera_model_var.set("Allied Vision hr25MCX")
        d._apply_camera_coverage_autofill("Allied Vision hr25MCX")
        ok(d._camera_pinned_field is True, "D1 real couple sets the pin flag")
        d._decouple_camera_model()
        ok(
            d.field_type_var.get() == "Object Height" and d.field_value_var.get() == "3.2",
            f"D2 stash restored the exact pre-camera field (got {d.field_type_var.get()} {d.field_value_var.get()})",
        )
        ok(d._camera_pinned_field is False, "D3 pin flag cleared after stash restore")
    else:
        notes.append("SKIP D real coverage unavailable")

    # E -- structural wiring.
    autofill_src = inspect.getsource(LayoutTableWorkbenchMixin._apply_camera_coverage_autofill)
    ok("_camera_pinned_field = True" in autofill_src, "E1 couple sets _camera_pinned_field")
    decouple_src = inspect.getsource(LayoutTableWorkbenchMixin._decouple_camera_model)
    ok(
        "_camera_pinned_field" in decouple_src and "_reset_camera_pinned_field_to_default" in decouple_src,
        "E2 decouple gates the reset on _camera_pinned_field",
    )
    from KrakenOS.UI.services.step_overlay_import import StepOverlayImportService
    clear_src = inspect.getsource(StepOverlayImportService.clear_imported_step_overlay_state)
    ok("_decouple_camera_model" in clear_src, "E3 deleting a camera STEP decouples")
    ok(
        "_field_matches_camera_autofill_signature" in decouple_src,  # bugs/0312
        "E4 decouple also un-pins on the camera-autofill value signature (0312)",
    )

    passed = all(not n.startswith("FAIL") for n in notes)
    if verbose or not passed:
        for n in notes:
            print("  " + n)
    return passed, [n for n in notes if n.startswith("FAIL")]


def run_orphaned_camera_check(verbose: bool = False) -> "tuple[bool, list[str]]":
    """bugs/0312 end-to-end: drive the REAL editor pipeline (not the _Ed stub) for
    the orphaned-camera case -- couple a camera, save its settings, then load them on
    a fresh editor with that camera POPPED from CAMERA_DATABASE (a cross-machine
    registry miss). ``_apply_layout_settings`` must drop the model to None yet keep
    the Real Image Height field, and deleting the still-shown camera STEP
    (``_decouple_camera_model``) must collapse the image-circle radius to ~0.

    Hermetic: the camera record is restored in a finally. Soft-skips (passes with a
    note) when the headless editor or datasheet scene can't be built in this env.
    """
    import contextlib

    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    camera = "BC-OM25M"
    try:
        from KrakenOS.common_optical_layouts.machine_vision_150mm_datasheet_1x import SETTINGS, SURFACES
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
        from KrakenOS.UI import camera_database as camdb
        from KrakenOS.UI.camera_database import CAMERA_DATABASE, CAMERA_NONE_LABEL
    except Exception as exc:  # pragma: no cover - constrained env
        notes.append(f"SKIP orphaned-camera end-to-end (import unavailable: {exc!r})")
        if verbose:
            for n in notes:
                print("  " + n)
        return True, [n for n in notes if n.startswith("FAIL")]

    if camdb.camera_record(camera) is None:
        notes.append(f"SKIP orphaned-camera end-to-end ({camera} not in registry)")
        if verbose:
            for n in notes:
                print("  " + n)
        return True, [n for n in notes if n.startswith("FAIL")]

    def _radius(app):
        try:
            return float(app._field_metrics_summary().get("field_image_radius"))
        except Exception:
            return None

    def _fresh():
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

    removed = None
    try:
        # session 1: interactive couple + save
        app1 = _fresh()
        app1._stash_camera_precouple_field_state()
        if hasattr(app1, "camera_model_var"):
            app1.camera_model_var.set(camera)
        app1._apply_camera_coverage_autofill(camera)
        settings = app1._collect_layout_settings()
        rows_snapshot = [
            SurfaceRow(**{f: getattr(r, f) for f in SurfaceRow.__dataclass_fields__}) for r in app1.rows
        ]
        with contextlib.suppress(Exception):
            app1.destroy()

        # session 2: reload with the camera absent from THIS machine's registry
        removed = CAMERA_DATABASE.pop(camera, None)
        app2 = KrakenLayoutEditor(headless=True)
        app2.rows = rows_snapshot
        with contextlib.suppress(Exception):
            app2._auto_assign_missing_elements(app2.rows)
        app2._apply_layout_settings(settings)
        app2._normalize_special_rows()
        app2._sync_table()
        if hasattr(app2, "_current_camera_model"):
            loaded = app2._current_camera_model()
            if loaded != CAMERA_NONE_LABEL:
                app2._apply_camera_coverage_autofill(loaded)
        ok(app2._current_camera_model() == CAMERA_NONE_LABEL, "H1 orphaned model dropped to None on load")
        ok(app2._current_field_type() == "Real Image Height", "H2 orphaned field stays Real Image Height")
        r_loaded = _radius(app2)
        ok(bool(r_loaded and r_loaded > 1e-6), f"H3 image circle present before delete (radius {r_loaded})")
        app2._decouple_camera_model()
        r_deleted = _radius(app2)
        ok(not (r_deleted and r_deleted > 1e-6), f"H4 image circle clears after delete (radius {r_deleted})")
        with contextlib.suppress(Exception):
            app2.destroy()
    except Exception as exc:  # pragma: no cover - defensive
        notes.append(f"FAIL orphaned-camera end-to-end raised: {exc!r}")
    finally:
        if removed is not None:
            CAMERA_DATABASE[camera] = removed

    passed = all(not n.startswith("FAIL") for n in notes)
    if verbose or not passed:
        for n in notes:
            print("  " + n)
    return passed, [n for n in notes if n.startswith("FAIL")]


def main() -> int:
    passed, failures = run_checks(verbose=True)
    passed_e2e, failures_e2e = run_orphaned_camera_check(verbose=True)
    passed = passed and passed_e2e
    failures = failures + failures_e2e
    if not passed:
        print("FAIL: camera-delete field un-pin guard (bugs/0311 + 0312)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("PASS: camera-delete field un-pin guard (bugs/0311 + 0312)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
