#!/usr/bin/env python3
"""Display-free guard for bugs/0128: perpendicular thickness-dimension labels must
stay SQUARE to their arrows as the 3D scene rotates.

Why it exists (user flagged it, flag_20260623_213541_579):
  "can't those thickness overlay stay strictly perpendicular to the arrow segments?
   They move when I rotate the 3D scene."
  The billboard text angle is computed from the world arrow axis projected onto the
  screen (right, up) basis and baked ONCE via ``text_prop.SetOrientation`` at label
  creation.  When the camera orbits, the screen basis changes but the baked angle
  did not -- so a label that started perpendicular drifted off its arrow.

The fix records each label's world-space arrow axis
(``Open3DThicknessDimensionService._register_perp_label_axis`` ->
``inspector._perp_label_axis_map``) and re-derives the billboard angle for the LIVE
camera on every orbit (``Kraken3DInspector._reorient_thickness_labels_for_camera``,
wired into ``_on_camera_interaction``).

What it checks (binds the REAL inspector method onto a light fake inspector, and
reuses the REAL ``_perp_label_orientation``):
  A. For an initial camera basis, each registered label is re-angled to exactly
     ``_perp_label_orientation(axis, right, up)`` (Z arrow -> 90 vertical text,
     Y arrow -> 0 horizontal text in the user's -YZ view).
  B. After the camera ROTATES (a different basis), the labels are re-angled again
     and the new angles DIFFER from the first basis -- i.e. they TRACK the camera,
     which is the whole bug.  Each still equals ``_perp_label_orientation`` for the
     new basis.
  C. A label whose actor has gone (missing from ``_actor_by_key``) is skipped
     without error, and with no camera basis nothing is changed.
  D. Source contract -- ``_on_camera_interaction`` calls
     ``_reorient_thickness_labels_for_camera``; ``add_label_actor`` registers the
     axis via ``_register_perp_label_axis``; and the three perpendicular call sites
     forward ``perp_axis`` (the main span loop, the promoted-solid span, and the
     LED object-edge overlay).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_perp_label_camera_track

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from types import MethodType

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService


class _FakeTextProperty:
    def __init__(self) -> None:
        self.orientation: float | None = None

    def SetOrientation(self, value: float) -> None:
        self.orientation = float(value)


class _FakeActor:
    def __init__(self) -> None:
        self._text_prop = _FakeTextProperty()

    def GetTextProperty(self) -> _FakeTextProperty:
        return self._text_prop


class _FakeInspector:
    """tk/VTK-free stand-in carrying the REAL reorient method so the test exercises
    production code, not a paraphrase of it."""

    def __init__(self, screen_axes) -> None:
        self._renderer = object()  # truthy non-None sentinel
        self._perp_label_axis_map: dict[str, tuple[float, float, float]] = {}
        self._actor_by_key: dict[str, _FakeActor] = {}
        self._screen_axes = screen_axes

    def _camera_screen_world_axes(self):
        return self._screen_axes

    # the method under test, bound from the real inspector class.
    _reorient_thickness_labels_for_camera = (
        Kraken3DInspector._reorient_thickness_labels_for_camera
    )


# orthonormal screen bases (right, up) ----------------------------------------
# Basis 1: the user's -YZ view -- world +Z reads screen-right, world +Y reads up.
_BASIS_1 = (
    np.array([0.0, 0.0, 1.0]),
    np.array([0.0, 1.0, 0.0]),
)
# Basis 2: orbit 45 deg in the Y-Z plane.
_R2 = np.array([0.0, 0.70710678, 0.70710678])
_U2 = np.array([0.0, -0.70710678, 0.70710678])
_BASIS_2 = (_R2, _U2)

_AXIS_Z = (0.0, 0.0, 1.0)   # transmit/thickness arrow
_AXIS_Y = (0.0, 1.0, 0.0)   # folded reflect arm arrow


def _expected(axis, basis) -> float:
    return Open3DThicknessDimensionService._perp_label_orientation(
        np.asarray(axis, dtype=float), basis[0], basis[1]
    )


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    insp = _FakeInspector(_BASIS_1)
    insp._perp_label_axis_map = {"z": _AXIS_Z, "y": _AXIS_Y}
    insp._actor_by_key = {"z": _FakeActor(), "y": _FakeActor()}

    # --- A: first camera basis -> each label square to its arrow -------------
    changed = insp._reorient_thickness_labels_for_camera()
    if not changed:
        failures.append("A FAIL: reorient reported no change with two registered labels")
    o_z1 = insp._actor_by_key["z"].GetTextProperty().orientation
    o_y1 = insp._actor_by_key["y"].GetTextProperty().orientation
    if o_z1 is None or abs(o_z1 - _expected(_AXIS_Z, _BASIS_1)) > 1e-6:
        failures.append(f"A FAIL: Z-arrow label orientation {o_z1} != expected {_expected(_AXIS_Z, _BASIS_1)}")
    if o_y1 is None or abs(o_y1 - _expected(_AXIS_Y, _BASIS_1)) > 1e-6:
        failures.append(f"A FAIL: Y-arrow label orientation {o_y1} != expected {_expected(_AXIS_Y, _BASIS_1)}")
    # sanity: in the -YZ view a horizontal Z arrow gets vertical (90) text, a
    # vertical Y arrow gets horizontal (0) text.
    if o_z1 is not None and abs(o_z1 - 90.0) > 1e-6:
        failures.append(f"A FAIL: Z arrow should read 90 (vertical text) in -YZ view, got {o_z1}")
    if o_y1 is not None and abs(o_y1 - 0.0) > 1e-6:
        failures.append(f"A FAIL: Y arrow should read 0 (horizontal text) in -YZ view, got {o_y1}")

    # --- B: rotate the camera -> labels TRACK (new angles, still perpendicular)
    insp._screen_axes = _BASIS_2
    changed2 = insp._reorient_thickness_labels_for_camera()
    if not changed2:
        failures.append("B FAIL: reorient reported no change after the camera rotated")
    o_z2 = insp._actor_by_key["z"].GetTextProperty().orientation
    o_y2 = insp._actor_by_key["y"].GetTextProperty().orientation
    if o_z2 is None or abs(o_z2 - _expected(_AXIS_Z, _BASIS_2)) > 1e-6:
        failures.append(f"B FAIL: rotated Z-arrow orientation {o_z2} != expected {_expected(_AXIS_Z, _BASIS_2)}")
    if o_y2 is None or abs(o_y2 - _expected(_AXIS_Y, _BASIS_2)) > 1e-6:
        failures.append(f"B FAIL: rotated Y-arrow orientation {o_y2} != expected {_expected(_AXIS_Y, _BASIS_2)}")
    # the regression itself: the angle must MOVE with the camera.
    if o_z1 is not None and o_z2 is not None and abs(o_z2 - o_z1) < 1e-6:
        failures.append(f"B FAIL: Z label did not track the camera (stayed at {o_z1} after orbit)")
    if o_y1 is not None and o_y2 is not None and abs(o_y2 - o_y1) < 1e-6:
        failures.append(f"B FAIL: Y label did not track the camera (stayed at {o_y1} after orbit)")

    # --- C: missing actor skipped; no camera basis -> no change -------------
    insp_missing = _FakeInspector(_BASIS_1)
    insp_missing._perp_label_axis_map = {"gone": _AXIS_Z}
    insp_missing._actor_by_key = {}  # actor was cleared on a rebuild
    try:
        c_changed = insp_missing._reorient_thickness_labels_for_camera()
    except Exception as exc:  # noqa: BLE001
        c_changed = True
        failures.append(f"C FAIL: missing-actor reorient raised {exc!r}")
    if c_changed:
        failures.append("C FAIL: reorient claimed a change with no live actor")
    insp_nocam = _FakeInspector(None)
    insp_nocam._perp_label_axis_map = {"z": _AXIS_Z}
    insp_nocam._actor_by_key = {"z": _FakeActor()}
    if insp_nocam._reorient_thickness_labels_for_camera():
        failures.append("C FAIL: reorient changed a label with no camera basis available")

    # --- D: source contracts ------------------------------------------------
    cam_src = inspect.getsource(Kraken3DInspector._on_camera_interaction)
    if "_reorient_thickness_labels_for_camera" not in cam_src:
        failures.append("D FAIL: _on_camera_interaction must call _reorient_thickness_labels_for_camera")
    add_src = inspect.getsource(Open3DThicknessDimensionService.add_label_actor)
    if "_register_perp_label_axis" not in add_src:
        failures.append("D FAIL: add_label_actor must register the world arrow axis via _register_perp_label_axis")
    svc_src = inspect.getsource(Open3DThicknessDimensionService)
    for token in ("perp_axis=axis", "perp_axis=axis_s", "perp_axis=axis_unit"):
        if token not in svc_src:
            failures.append(f"D FAIL: a perpendicular call site must forward {token}")
    reorient_src = inspect.getsource(Kraken3DInspector._reorient_thickness_labels_for_camera)
    if "_perp_label_orientation" not in reorient_src:
        failures.append("D FAIL: reorient must re-derive the angle via _perp_label_orientation (not a baked constant)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0128 perpendicular thickness labels must track the camera")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] thickness labels stay perpendicular to their arrows on orbit (bugs/0128)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
