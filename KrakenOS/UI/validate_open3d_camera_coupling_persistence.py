#!/usr/bin/env python3
"""bugs/0306 -- display-free guard for camera-coupling *persistence*.

bugs/0296 gave the camera sensor coupling a stash-on-couple / restore-on-decouple
lifecycle, but the stash (``_camera_coverage_precouple_stash``) lived only in the
running session.  Once 0305 ("save everything") made save/reopen the common
workflow, a layout saved with a camera coupled and then reopened had no stash, so
deleting the camera left the sensor image-surface aperture behind -- the user's
"why the bug resurface? Deleting a camera still leave the detector behind." flag.

The 0306 fix has two parts, both proved here without Tk / VTK:

  * Part 1 -- persist the stash.  ``_collect_layout_settings`` writes
    ``camera_precouple_stash`` and ``_apply_layout_settings`` restores it, so the
    natural pre-camera field / image aperture survives a save/reload round-trip and
    a *later* delete can still revert.  Checked structurally (the two settings
    touch-points) and semantically (a JSON round-tripped stash drives a correct
    decouple, exactly the save -> reopen -> delete path).

  * Part 2 -- legacy grace.  A layout saved *before* 0306 (no persisted stash) can
    no longer reconstruct its exact pre-camera field, but ``_decouple_camera_model``
    must not leave the image aperture locked to the deleted sensor: with no stash it
    flips a Manual image-diameter mode back to the self-computing Auto mode.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_camera_coupling_persistence
"""
from __future__ import annotations

import inspect
import json

# Importing the editor coordinator injects the workbench mixin's late-bound editor
# globals (CAMERA_NONE_LABEL, camera_image_coverage_mm, ...) so the real
# _apply_camera_coverage_autofill / _decouple_camera_model resolve on the stub.
import KrakenOS.UI.layout_editor  # noqa: F401
from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
from KrakenOS.UI.services.layout_settings import LayoutSettingsService
from KrakenOS.UI.camera_database import CAMERA_NONE_LABEL, camera_image_coverage_mm

_CAMERA = "Allied Vision hr25MCX"  # PYTHON 25K: 23.04x23.04 -> semi-diagonal 16.2915


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
    """Only the collaborators the couple / stash / decouple helpers touch.

    Datasheet defaults model a folder-import surrogate before any camera couples:
    a Real Image Height field at image-circle/2 and an image-surface aperture at
    the datasheet image circle.
    """

    def __init__(self):
        self.field_type_var = _Var("Real Image Height")
        self.field_value_var = _Var("35.355")             # datasheet default (image-circle/2)
        self.image_diameter_mode_var = _Var("Auto")
        self.camera_model_var = _Var(CAMERA_NONE_LABEL)
        self.rows = [_Row("Object", 0.0), _Row("Image", 70.71)]  # datasheet image circle
        self._field_type_defaults = {"Real Image Height": "35.355"}
        self._last_field_type = "Real Image Height"
        self._camera_coverage_precouple_stash = None
        self.imported_camera_step_path = None

    def _current_field_type(self):
        return self.field_type_var.get()

    def _current_image_diameter_mode(self):
        return self.image_diameter_mode_var.get()

    def _set_image_diameter_mode(self, mode):
        if mode in {"Auto", "Manual"}:
            self.image_diameter_mode_var.set(mode)

    def _apply_image_diameter_mode(self):
        # The real recompute needs the whole field-sampling stack; the mode FLIP is
        # what Part 2 asserts, so the stub keeps the aperture value put.
        return False

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


def _coupled_editor():
    """A stub that has already been coupled to the vendor camera (mode Manual,
    field / image aperture at the sensor) -- i.e. the state a saved camera layout
    reopens into."""
    cov = camera_image_coverage_mm(_CAMERA)
    ed = _FakeCameraEditor()
    ed.camera_model_var.set(_CAMERA)
    ed.image_diameter_mode_var.set("Manual")
    ed.rows[-1].diameter = float(cov[0])
    ed.field_value_var.set(f"{float(cov[1]):.6g}")
    ed.field_type_var.set("Real Image Height")
    return ed, cov


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # ------------------------------------------------------------------
    # Part 1 (structural): the two settings touch-points exist.
    # ------------------------------------------------------------------
    collect_src = inspect.getsource(LayoutSettingsService._collect_layout_settings)
    if '"camera_precouple_stash"' not in collect_src or "_camera_coverage_precouple_stash" not in collect_src:
        failures.append("P1a _collect_layout_settings does not persist camera_precouple_stash")

    apply_src = inspect.getsource(LayoutSettingsService._apply_layout_settings)
    if "camera_precouple_stash" not in apply_src or "self._camera_coverage_precouple_stash" not in apply_src:
        failures.append("P1b _apply_layout_settings does not restore camera_precouple_stash")

    # ------------------------------------------------------------------
    # Part 1 (semantic): a JSON round-tripped stash drives a correct decouple,
    # exactly the save -> reopen -> delete path.
    # ------------------------------------------------------------------
    natural = _FakeCameraEditor()
    nat_diam = natural.rows[-1].diameter
    nat_field = natural.field_value_var.get()
    nat_mode = natural.image_diameter_mode_var.get()

    natural._stash_camera_precouple_field_state()
    natural.camera_model_var.set(_CAMERA)
    natural._apply_camera_coverage_autofill(_CAMERA)
    stash = natural._camera_coverage_precouple_stash
    if not isinstance(stash, dict):
        failures.append("P1c no stash captured on the first couple")

    # Persist exactly what _collect_layout_settings writes, and prove it survives
    # a JSON round-trip (the layout .py stores JSON-safe scalars).
    try:
        persisted = json.loads(json.dumps({"camera_precouple_stash": dict(stash)}))
    except (TypeError, ValueError) as exc:
        failures.append(f"P1d stash is not JSON-serialisable: {exc}")
        persisted = {"camera_precouple_stash": None}

    reopened, cov = _coupled_editor()
    # Simulate _apply_layout_settings restoring the persisted stash on load.
    reopened._camera_coverage_precouple_stash = persisted["camera_precouple_stash"]

    restored = reopened._decouple_camera_model()
    if not restored:
        failures.append("P1e persisted-stash decouple reported nothing to restore")
    if reopened.camera_model_var.get() != CAMERA_NONE_LABEL:
        failures.append("P1f camera not reset to None after the reopen-delete")
    if abs(reopened.rows[-1].diameter - nat_diam) > 1e-6:
        failures.append(
            f"P1g image aperture not restored to the pre-camera circle "
            f"({reopened.rows[-1].diameter} != {nat_diam})"
        )
    if reopened.field_value_var.get() != nat_field:
        failures.append(
            f"P1h field not restored to the pre-camera value "
            f"({reopened.field_value_var.get()} != {nat_field})"
        )
    if reopened.image_diameter_mode_var.get() != nat_mode:
        failures.append(
            f"P1i image-diameter mode not restored ({reopened.image_diameter_mode_var.get()} != {nat_mode})"
        )
    # Sanity: the reopened editor really started at the sensor coverage (else the
    # restore above proves nothing).
    if abs(float(cov[0]) - nat_diam) < 1e-6:
        failures.append("P1j test setup: sensor coverage coincides with the pre-camera circle")

    # ------------------------------------------------------------------
    # Part 2: a legacy file (coupled, NO stash) must not stay Manual-locked on the
    # deleted sensor -- decouple flips Manual -> Auto and clears the model.
    # ------------------------------------------------------------------
    legacy, _ = _coupled_editor()
    legacy._camera_coverage_precouple_stash = None  # never persisted (pre-0306 save)
    legacy_restored = legacy._decouple_camera_model()
    if legacy_restored is not False:
        failures.append("P2a legacy no-stash decouple should report no stash (False)")
    if legacy.camera_model_var.get() != CAMERA_NONE_LABEL:
        failures.append("P2b legacy decouple did not clear the camera model")
    if legacy.image_diameter_mode_var.get() != "Auto":
        failures.append(
            f"P2c legacy decouple left the image aperture Manual-locked "
            f"({legacy.image_diameter_mode_var.get()} != Auto)"
        )

    return (not failures, failures)


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("FAIL: camera coupling persistence guard (bugs/0306)")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: camera coupling persistence guard (bugs/0306)")
    print("  P1: stash persisted + restored -> a reopen-then-delete reverts to the pre-camera circle")
    print("  P2: a legacy no-stash delete unlocks Manual -> Auto instead of keeping the sensor aperture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
