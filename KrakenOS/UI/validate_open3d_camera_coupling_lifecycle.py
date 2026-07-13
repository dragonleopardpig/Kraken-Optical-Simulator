#!/usr/bin/env python3
"""bugs/0296 -- display-free guard for the camera STEP coupling lifecycle.

Two flags on the folder-import surrogate flow exposed an asymmetric
camera-coupling lifecycle:

  * flag 20260713_160023 "after BC-GM camera deleted, the sensor size remain
    on the screen" -- deleting the camera STEP overlay left the coupled
    image-surface aperture / field (the sensor coverage) on the layout because
    ``clear_imported_step_overlay_state`` never decoupled the camera model.

  * "Immediately after ... click Done 2D ... it is not updated" -- an imported
    camera coupled the vendor sensor into the field / image circle, but the
    import path never marked the 2D layout dirty, so ``finish_stl_placement``
    ("Done 2D") skipped its ``refresh_plot`` and the 2D layout kept the stale
    datasheet FOV.

This guard runs the REAL couple (``_apply_camera_coverage_autofill``) and the
new decouple (``_decouple_camera_model``) on a minimal stub (no Tk / no VTK) to
prove the stash-on-couple / restore-on-decouple roundtrip, and structurally
asserts the two dirty/decouple wirings that need a live app to *see* but not to
*prove*.
"""
from __future__ import annotations

import inspect

# Importing the editor coordinator runs ``_sync_layout_globals`` (layout_editor.py),
# which injects the workbench mixin's late-bound editor globals (CAMERA_NONE_LABEL,
# camera_image_coverage_mm, ...) so the real _apply_camera_coverage_autofill resolves.
import KrakenOS.UI.layout_editor  # noqa: F401
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


class _FakeCameraEditor(LayoutTableWorkbenchMixin):
    """Only the collaborators the couple/stash/decouple helpers actually touch.

    The datasheet defaults model a folder-import surrogate before any camera is
    coupled: a Real Image Height field at image-circle/2 and an image-surface
    aperture at the datasheet image circle.
    """

    def __init__(self):
        self.field_type_var = _Var("Real Image Height")
        self.field_value_var = _Var("35.355")            # datasheet default (image-circle/2)
        self.image_diameter_mode_var = _Var("Auto")
        self.camera_model_var = _Var(CAMERA_NONE_LABEL)
        self.rows = [_Row("Object", 0.0), _Row("Image", 70.71)]  # datasheet image circle
        self._field_type_defaults = {"Real Image Height": "35.355"}
        self._last_field_type = "Real Image Height"
        self._camera_coverage_precouple_stash = None
        self.imported_camera_step_path = None

    # Faithful-enough field getters (identity display mapping keeps the
    # field-type round-trip hermetic; the alias table is not what 0296 tests).
    def _current_field_type(self):
        return self.field_type_var.get()

    def _current_image_diameter_mode(self):
        return self.image_diameter_mode_var.get()

    def _field_type_display_label(self, field_type):
        return field_type

    def _current_camera_record(self):
        return None

    def _sync_field_mode_ui(self):
        pass

    def _sync_object_diameter_from_manual_image(self):
        pass

    def _sync_table(self):
        pass

    def _sync_object_controls(self):
        pass


def run_checks() -> tuple[bool, list[str]]:
    """Return ``(passed, failures)`` -- ``failures`` is empty on success."""
    failures: list[str] = []

    # ------------------------------------------------------------------
    # Bug B: stash on the FIRST couple, restore on decouple (real couple).
    # ------------------------------------------------------------------
    ed = _FakeCameraEditor()
    pre_diam = ed.rows[-1].diameter
    pre_field = ed.field_value_var.get()
    pre_mode = ed.image_diameter_mode_var.get()

    ed._stash_camera_precouple_field_state()
    if ed._camera_coverage_precouple_stash is None:
        failures.append("B1 stash not captured on first couple")

    # "Japan Bopixel BC-GN25M12X4" (the flag's "BC-GM 25M"): 12.8x12.8 sensor
    # -> diagonal 18.1019 mm, half-diagonal 9.050967 (matches flag 160023 row6).
    bc_camera = "Japan Bopixel BC-GN25M12X4"
    bc_cov = camera_image_coverage_mm(bc_camera)
    ed.camera_model_var.set(bc_camera)
    applied = ed._apply_camera_coverage_autofill(bc_camera)
    if applied is None:
        failures.append("B2 real autofill did not apply the sensor coverage")
    elif abs(ed.rows[-1].diameter - bc_cov[0]) > 1e-6:
        failures.append(
            f"B2 couple did not set sensor aperture ({ed.rows[-1].diameter} != {bc_cov[0]})"
        )
    if abs(float(ed.field_value_var.get()) - bc_cov[1]) > 1e-4:
        failures.append(
            f"B3 couple did not set the sensor half-diagonal field ({ed.field_value_var.get()} != {bc_cov[1]})"
        )

    # Re-couple to a DIFFERENT camera must NOT overwrite the original stash
    # (guarded by an existing stash) -- decouple must land on the pre-CAMERA
    # datasheet state, not an intermediate sensor.
    ed._stash_camera_precouple_field_state()
    ed.camera_model_var.set("Allied Vision hr25MCX")
    ed._apply_camera_coverage_autofill("Allied Vision hr25MCX")
    if abs(float(ed._camera_coverage_precouple_stash["image_diameter"]) - pre_diam) > 1e-9:
        failures.append("B4 stash overwritten by a second couple")

    restored = ed._decouple_camera_model()
    if not restored:
        failures.append("B5 decouple reported no stash to restore")
    if ed.camera_model_var.get() != CAMERA_NONE_LABEL:
        failures.append("B6 camera model not reset to None on decouple")
    if abs(ed.rows[-1].diameter - pre_diam) > 1e-6:
        failures.append(f"B7 image aperture not restored ({ed.rows[-1].diameter} != {pre_diam})")
    if ed.field_value_var.get() != pre_field:
        failures.append(f"B8 field value not restored ({ed.field_value_var.get()} != {pre_field})")
    if ed.image_diameter_mode_var.get() != pre_mode:
        failures.append(
            f"B9 image-diameter mode not restored ({ed.image_diameter_mode_var.get()} != {pre_mode})"
        )
    if ed._camera_coverage_precouple_stash is not None:
        failures.append("B10 stash not cleared after restore")

    # Idempotent second decouple (nothing left to restore).
    if ed._decouple_camera_model() is not False:
        failures.append("B11 second decouple should report no stash")

    # ------------------------------------------------------------------
    # Bug A + delete wiring: structural (needs Tk to RUN, not to PROVE).
    # ------------------------------------------------------------------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.step_overlay_import import StepOverlayImportService

    import_src = inspect.getsource(Kraken3DInspector.import_step_overlay)
    if "_stl_placement_dirty = True" not in import_src or "bugs/0296" not in import_src:
        failures.append("A1 import_step_overlay does not mark the 2D dirty (bugs/0296)")

    delete_src = inspect.getsource(Kraken3DInspector.delete_selected_step)
    if "_stl_placement_dirty = True" not in delete_src or "bugs/0296" not in delete_src:
        failures.append("A2 delete_selected_step does not mark the 2D dirty (bugs/0296)")

    clear_src = inspect.getsource(StepOverlayImportService.clear_imported_step_overlay_state)
    if "_decouple_camera_model" not in clear_src:
        failures.append("A3 clear_imported_step_overlay_state does not decouple the camera")

    return (not failures, failures)


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("FAIL: camera coupling lifecycle guard (bugs/0296)")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: camera coupling lifecycle guard (bugs/0296)")
    print("  B: real couple -> decouple restores aperture / field / image-diameter mode")
    print("  B: a second couple preserves the original pre-camera stash")
    print("  A: import + delete mark the 2D dirty; delete decouples the sensor coverage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
