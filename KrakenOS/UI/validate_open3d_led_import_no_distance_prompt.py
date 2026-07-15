#!/usr/bin/env python3
"""Display-free guard for bugs/0318: importing an LED STEP must NOT pop a modal
"working distance" prompt.

The user (flag follow-up): "we can remove the LED working distance prompt. Let
user align themselves, the thickness overlay can be click -> change value ->
physical change." Importing an LED used to block on ``_ask_led_edge_distance``
-- a modal asking for the object->LED-edge distance in mm before the body would
even appear. bugs/0318 drops that prompt: the LED lands at the existing auto
default (``_default_led_object_edge_distance``) and the user aligns it by eye
(drag along the axis, or click the live Object->LED dimension to type a value).
The EXPLICIT ``set_led_edge_distance`` menu action keeps its prompt -- that is a
user asking to type a number, not an import getting in the way.

What it checks
--------------
  A. Import wiring (source): ``import_led_step`` no longer calls
     ``_ask_led_edge_distance`` and has no "import cancelled" early-out, while
     ``set_led_edge_distance`` (the explicit action) still prompts.
  B. Fresh import lands at the auto default: driving ``import_led_step`` on a
     stub whose ``_ask_led_edge_distance`` RAISES returns the imported path
     (never None), sets ``led_object_edge_distance_mm`` to the default, and never
     touches the modal.
  C. Re-import preserves an already-set distance (no surprise reset to default).
  D. The default distance itself is finite and non-negative.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_import_no_distance_prompt

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from pathlib import Path


class _ModalCalled(AssertionError):
    """Raised if the removed working-distance modal is invoked during import."""


class _Refresh:
    def clear_step_overlay_physics_preview(self, _label):
        return None


class _StatusVar:
    def __init__(self):
        self.value = ""

    def set(self, message):
        self.value = str(message)


class _LedImportStub:
    """Minimal collaborators ``import_led_step`` touches, no Tk/display."""

    def __init__(self, *, existing_distance: float, default_distance: float, fake_path: Path):
        self.led_object_edge_distance_mm = float(existing_distance)
        self._default_distance = float(default_distance)
        self._fake_path = fake_path
        self.status_var = _StatusVar()
        self.modal_calls = 0
        # attributes the method assigns to -- just need to exist / be settable
        self.imported_led_step_path = None
        self.led_step_rotation_x_deg = 999.0
        self.led_step_rotation_y_deg = 999.0
        self.led_step_rotation_z_deg = 999.0
        self.led_step_object_edge_local_z = 123.0
        self.led_step_axis_offset_xy = (9.0, 9.0)
        self.led_step_placement_offset_xyz = (9.0, 9.0, 9.0)
        self._selected_step_label = None
        self._cad_axis_pick_any = True
        self._cad_led_object_edge_pick = True
        self._live_step_overlay_trace_plan_cache = {"stale": 1}

    # --- collaborators -----------------------------------------------------
    def _ask_step_file(self, _title, _initial_dir, parent=None):
        return self._fake_path

    def _default_led_object_edge_distance(self):
        return self._default_distance

    def _ask_led_edge_distance(self, _initial, parent=None):
        self.modal_calls += 1
        raise _ModalCalled("import_led_step must not open the working-distance modal")

    def _begin_history_capture(self):
        return None

    def _commit_history_capture(self):
        return None

    def _clear_step_overlay_axis_anchor(self, _label):
        return None

    def _open3d_trace_refresh_service(self):
        return _Refresh()

    def _invalidate_preview_scene_trace(self):
        return None

    def _refresh_open_3d_views(self, **_kwargs):
        return None


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services.step_overlay_import import StepOverlayImportService
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    failures: list[str] = []
    import_led_step = StepOverlayImportService.import_led_step

    # A) Source wiring: the import no longer prompts; the explicit action still does.
    import_src = inspect.getsource(import_led_step)
    if "_ask_led_edge_distance" in import_src:
        failures.append("FAIL(A): import_led_step must not call _ask_led_edge_distance (drop the modal)")
    if "import cancelled" in import_src.lower():
        failures.append("FAIL(A): import_led_step should have no modal-cancel early-out")
    try:
        set_src = inspect.getsource(ScenePlacementMixin.set_led_edge_distance)
        if "_ask_led_edge_distance" not in set_src:
            failures.append("FAIL(A): set_led_edge_distance (explicit action) must keep its prompt")
    except (AttributeError, OSError) as exc:
        failures.append(f"FAIL(A): could not read set_led_edge_distance source ({exc!r})")

    fake_path = Path("/tmp/validate_led_no_prompt.step")

    # B) Fresh import (distance 0) lands at the auto default, no modal.
    stub = _LedImportStub(existing_distance=0.0, default_distance=17.5, fake_path=fake_path)
    try:
        returned = import_led_step(stub, refresh_open_3d=False)
    except _ModalCalled:
        returned = None
        failures.append("FAIL(B): import opened the removed working-distance modal")
    except Exception as exc:  # pragma: no cover - defensive
        returned = None
        failures.append(f"FAIL(B): import_led_step raised {type(exc).__name__}: {exc}")
    if returned != fake_path:
        failures.append(f"FAIL(B): import must return the chosen path, got {returned!r}")
    if stub.modal_calls != 0:
        failures.append(f"FAIL(B): the working-distance modal was called {stub.modal_calls}x")
    if abs(float(stub.led_object_edge_distance_mm) - 17.5) > 1e-9:
        failures.append(
            f"FAIL(B): fresh import should land at the auto default 17.5, "
            f"got {stub.led_object_edge_distance_mm}")
    if stub.imported_led_step_path != fake_path:
        failures.append("FAIL(B): import must record imported_led_step_path")
    if stub._selected_step_label != "led":
        failures.append("FAIL(B): import must select the LED label")
    # the pose knobs must have been reset to neutral (no stale carry)
    if stub.led_step_placement_offset_xyz != (0.0, 0.0, 0.0):
        failures.append("FAIL(B): import must reset the LED placement offset")
    if stub.led_step_object_edge_local_z is not None:
        failures.append("FAIL(B): import must clear the LED object-edge local z")

    # C) Re-import with an existing nonzero distance preserves it (no reset).
    stub2 = _LedImportStub(existing_distance=42.0, default_distance=17.5, fake_path=fake_path)
    try:
        import_led_step(stub2, refresh_open_3d=False)
    except _ModalCalled:
        failures.append("FAIL(C): re-import opened the removed modal")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"FAIL(C): re-import raised {type(exc).__name__}: {exc}")
    if abs(float(stub2.led_object_edge_distance_mm) - 42.0) > 1e-9:
        failures.append(
            f"FAIL(C): re-import should keep the existing 42.0 distance, "
            f"got {stub2.led_object_edge_distance_mm}")

    # D) The default distance is a finite non-negative number on the real editor.
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        default_fn = KrakenLayoutEditor._default_led_object_edge_distance
        # drive it on a stub exposing a zero lens datum -> default 0.0 (LED-only scene)
        lens_stub = type("_LensDatumStub", (), {"_lens_front_datum_z": lambda self: 0.0})()
        value = default_fn(lens_stub)
        if not (isinstance(value, float) and value >= 0.0 and value == value):
            failures.append(f"FAIL(D): default LED distance must be finite >= 0, got {value!r}")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"FAIL(D): default-distance check raised {type(exc).__name__}: {exc}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] LED STEP import must not prompt for a working distance")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] LED STEP imports with no working-distance modal; lands at the auto "
          "default and stays user-alignable (drag / click Object->LED dimension)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
