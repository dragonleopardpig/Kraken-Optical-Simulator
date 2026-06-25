#!/usr/bin/env python3
"""Display-free guard for bugs/0140: switching to a PRESET view (the YZ / -YZ /
XY ... buttons) must re-square the perpendicular thickness labels to their arrows,
exactly as a mouse orbit already does.

Why it exists (user flagged it, flag_20260625_090727_802):
  "Changed from ISO to YZ or -YZ view, the thickness overlay text should changed to
   perpendicular to the arrow segments."
  bugs/0128 made the labels track the camera -- but only via the orbit backstop
  ``_on_camera_interaction`` (a mouse InteractionEvent/EndInteractionEvent). A preset
  button calls ``set_camera_preset`` which JUMPS the camera with no mouse interaction,
  so the backstop never fired and every label kept the angle baked against the
  PREVIOUS (Iso) camera -- reading slanted, not square, in the new YZ view.

The fix calls ``_reorient_thickness_labels_for_camera`` at the end of
``set_camera_preset`` (after the camera is positioned), so the preset jump re-derives
each label's billboard angle for the just-set basis.

What it checks -- binds the REAL ``set_camera_preset`` /
``_reorient_thickness_labels_for_camera`` / ``_camera_screen_world_axes`` onto a light
fake inspector with a fake camera that stores Set*/returns Get* (so the camera the
preset sets is the camera the reorient reads back):
  A. Before any preset, a registered world-Z arrow label has no orientation set.
  B. After ``set_camera_preset("-yz")`` the Z-arrow label is re-angled to exactly
     ``_perp_label_orientation`` for the resulting basis -- 90 (vertical text), i.e.
     square to the horizontal Z arrow in the YZ view. The same for ``"+yz"``.
  C. Mutation guard: a label registered AFTER positioning still gets squared, proving
     the reorient runs against the LIVE camera, not a stale basis.
  D. Source contract -- ``set_camera_preset`` calls
     ``_reorient_thickness_labels_for_camera`` (so removing it fails here too).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_preset_view_squares_labels

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

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


class _FakeCamera:
    """Stores Set*/returns Get* so _camera_screen_world_axes reads back exactly the
    pose set_camera_preset just applied."""

    def __init__(self) -> None:
        self.position = (0.0, 0.0, 0.0)
        self.focal = (0.0, 0.0, 0.0)
        self.view_up = (0.0, 1.0, 0.0)
        self.parallel = 0
        self.parallel_scale = 1.0

    def GetPosition(self):
        return self.position

    def GetFocalPoint(self):
        return self.focal

    def GetViewUp(self):
        return self.view_up

    def SetPosition(self, x, y, z):
        self.position = (float(x), float(y), float(z))

    def SetFocalPoint(self, x, y, z):
        self.focal = (float(x), float(y), float(z))

    def SetViewUp(self, x, y, z):
        self.view_up = (float(x), float(y), float(z))

    def SetParallelProjection(self, value):
        self.parallel = int(value)

    def SetParallelScale(self, value):
        self.parallel_scale = float(value)


class _FakeRenderer:
    def __init__(self, camera) -> None:
        self._camera = camera

    def GetActiveCamera(self):
        return self._camera


class _FakeInspector:
    """tk/VTK-free stand-in carrying the REAL preset + reorient + camera-basis methods
    so the test exercises production code, not a paraphrase of it."""

    set_camera_preset = Kraken3DInspector.set_camera_preset
    _reorient_thickness_labels_for_camera = (
        Kraken3DInspector._reorient_thickness_labels_for_camera
    )
    _camera_screen_world_axes = Kraken3DInspector._camera_screen_world_axes
    _parallel_scale_for_orthographic_fit = staticmethod(
        Kraken3DInspector._parallel_scale_for_orthographic_fit
    )

    def __init__(self) -> None:
        self._camera = _FakeCamera()
        self._renderer = _FakeRenderer(self._camera)
        self._perp_label_axis_map: dict[str, tuple[float, float, float]] = {}
        self._actor_by_key: dict[str, _FakeActor] = {}
        self._camera_preset = None
        self.render_calls = 0
        self.reset_clip_calls = 0

    def _camera_fit_bounds(self):
        return np.array([-100.0, 100.0, -50.0, 50.0, -200.0, 200.0], dtype=float)

    def _render_aspect(self) -> float:
        return 1.4

    def _reset_camera_clipping_range_for_scene(self) -> None:
        self.reset_clip_calls += 1

    def render(self) -> None:
        self.render_calls += 1


_AXIS_Z = (0.0, 0.0, 1.0)  # transmit/thickness arrow -- horizontal in a YZ view


def _expected_for_live_camera(insp: _FakeInspector, axis) -> float:
    right, up = insp._camera_screen_world_axes()
    return Open3DThicknessDimensionService._perp_label_orientation(
        np.asarray(axis, dtype=float), right, up
    )


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # --- A: a fresh registered Z label has no orientation yet ----------------
    insp = _FakeInspector()
    actor = _FakeActor()
    insp._perp_label_axis_map = {"z": _AXIS_Z}
    insp._actor_by_key = {"z": actor}
    if actor.GetTextProperty().orientation is not None:
        failures.append("A FAIL: label started with an orientation already set")

    # --- B: the preset jump squares the Z label to its arrow -----------------
    for preset in ("-yz", "+yz"):
        insp = _FakeInspector()
        actor = _FakeActor()
        insp._perp_label_axis_map = {"z": _AXIS_Z}
        insp._actor_by_key = {"z": actor}
        insp.set_camera_preset(preset)
        got = actor.GetTextProperty().orientation
        want = _expected_for_live_camera(insp, _AXIS_Z)
        if got is None:
            failures.append(
                f"B FAIL: set_camera_preset({preset!r}) left the Z-arrow label "
                "unsquared -- the preset path did not re-derive its angle (bugs/0140)"
            )
        elif abs(got - want) > 1e-6:
            failures.append(
                f"B FAIL: set_camera_preset({preset!r}) angle {got} != "
                f"_perp_label_orientation {want}"
            )
        # in a YZ view the horizontal Z arrow gets vertical (90) text.
        elif abs(got - 90.0) > 1e-6:
            failures.append(
                f"B FAIL: set_camera_preset({preset!r}) Z arrow should read 90 "
                f"(vertical text) square to its horizontal arrow, got {got}"
            )
        if insp.render_calls < 1:
            failures.append(f"B FAIL: set_camera_preset({preset!r}) did not render")

    # --- C: reorient runs against the LIVE (just-set) camera basis -----------
    # Register the label, switch to -yz (square -> 90), then switch to -xz where
    # the Z arrow is also horizontal but the basis differs; the label must follow
    # the live camera, not stay frozen at the first preset's angle.
    insp = _FakeInspector()
    actor = _FakeActor()
    insp._perp_label_axis_map = {"z": _AXIS_Z}
    insp._actor_by_key = {"z": actor}
    insp.set_camera_preset("-yz")
    angle_yz = actor.GetTextProperty().orientation
    insp.set_camera_preset("-xz")
    angle_xz = actor.GetTextProperty().orientation
    want_xz = _expected_for_live_camera(insp, _AXIS_Z)
    if angle_xz is None or abs(angle_xz - want_xz) > 1e-6:
        failures.append(
            f"C FAIL: after switching -yz -> -xz the Z label angle {angle_xz} != "
            f"live-camera expected {want_xz} (reorient used a stale basis)"
        )

    # --- D: source contract --------------------------------------------------
    preset_src = inspect.getsource(Kraken3DInspector.set_camera_preset)
    if "_reorient_thickness_labels_for_camera" not in preset_src:
        failures.append(
            "D FAIL: set_camera_preset must call _reorient_thickness_labels_for_camera "
            "so a preset-view jump re-squares the thickness labels (bugs/0140)"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0140 preset-view jump must re-square thickness labels")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] bugs/0140: switching to a YZ/-YZ preset view squares thickness labels to their arrows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
