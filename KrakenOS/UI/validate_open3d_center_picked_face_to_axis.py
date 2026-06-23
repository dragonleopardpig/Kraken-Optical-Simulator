"""Guard for bugs/0119 + bugs/0120 -- the right-click face menu must offer a
TRANSLATE-ONLY "Center Picked Face -> Optical Axis" that lands the picked window's
CENTROID on the GLOBAL optical axis, not the normal-aligning snap that rotates the
body and not a slide onto a nearby traced ray.

Regression context
------------------
0119: "Snap Picked Face -> Optical Axis" is a normal-align command: it rotates the
STEP so the picked face's normal is anti-parallel to the optical axis, then
translates. A user who right-clicked a window face and reached for "the axis one"
wanting to *center* it got an unwanted tilt instead.

0120: the first translate-only centre still landed OFF the axis. Two causes: (a) it
targeted `_step_optical_axis_frame_near_point`, which reads the cached ray bundle
(alive even with rays hidden) and returns the nearest *traced ray* -- for an
off-axis body, an outer marginal ray a few mm off (0, 0); (b) it centred the raw
cursor hit, not the face centroid. Fix: target the GLOBAL axis via
`_global_optical_axis_frame_near_point` (always (0, 0, z)) and pass the face
centroid from the pick.

This guard is display-free: it drives the REAL
`center_step_feature_on_optical_axis` against a fake editor that records the
placement offset it sets and whether any rotation was applied, so no VTK / embedded
window is needed. The fake's nearest-traced-ray frame is deliberately OFF-axis so a
regression back to the ray-seeking helper makes the behavioural check fail.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_center_picked_face_to_axis

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


class _FakeStatusVar:
    def __init__(self) -> None:
        self._text = ""

    def set(self, text) -> None:
        self._text = str(text)

    def get(self) -> str:
        return self._text


# bugs/0120: the production nearest-traced-ray frame returned a point a few mm off
# (0, 0) for an off-axis body (e.g. the LED). Model that here so a regression back to
# the ray-seeking helper makes the behavioural check fail.
_OFF_AXIS_RAY_TARGET_XY = (-1.1534, -9.8039)


class _FakeEditor:
    """Minimal ScenePlacementMixin surface for center_step_feature_on_optical_axis.

    Two axis frames are modelled. `_global_optical_axis_frame_near_point` is the
    GLOBAL guide -- the projection (0, 0, z), what a correct centre must use.
    `_step_optical_axis_frame_near_point` is the nearest *traced ray*; it is set
    deliberately OFF-axis (the bugs/0120 failing case) so that if the centre ever
    reaches for the ray-seeking helper again, the behavioural check catches it.
    `_set_step_rotation_deg_tuple` records any call, so the behavioural check also
    proves the centre is translate-only."""

    def __init__(self, current_offset=(0.0, 0.0, 0.0)) -> None:
        self.status_var = _FakeStatusVar()
        self._offset = np.asarray(current_offset, dtype=float).reshape(3)
        self.set_offset_calls: list[np.ndarray] = []
        self.rotation_calls: list[tuple] = []
        self.anchor_records: list[dict] = []
        self.refreshed_labels: list[str] = []
        self.global_frame_calls: list[np.ndarray] = []
        self.nearest_ray_frame_calls: list[np.ndarray] = []
        self._cad_axis_pick_label = "sentinel"
        self._cad_axis_pick_any = True
        self._cad_led_object_edge_pick = True
        self._selected_step_label = None

    def _step_path_for_label(self, label):
        return f"/tmp/{label}.step"

    def _global_optical_axis_frame_near_point(self, reference_point):
        ref = np.asarray(reference_point, dtype=float).reshape(-1)[:3]
        self.global_frame_calls.append(ref)
        return {
            "target_point": np.asarray((0.0, 0.0, float(ref[2])), dtype=float),
            "direction": np.asarray((0.0, 0.0, 1.0), dtype=float),
            "axis_label": "global optical axis",
            "ray_index": -1,
            "branch_path": "",
        }

    def _step_optical_axis_frame_near_point(self, reference_point):
        ref = np.asarray(reference_point, dtype=float).reshape(-1)[:3]
        self.nearest_ray_frame_calls.append(ref)
        return {
            "target_point": np.asarray(
                (_OFF_AXIS_RAY_TARGET_XY[0], _OFF_AXIS_RAY_TARGET_XY[1], float(ref[2])),
                dtype=float,
            ),
            "direction": np.asarray((0.0, 0.0, 1.0), dtype=float),
            "axis_label": "nearest traced optical path ray 7",
            "ray_index": 7,
            "branch_path": "",
        }

    def _step_placement_offset_xyz(self, label):
        return np.asarray(self._offset, dtype=float).reshape(3)

    def _set_step_placement_offset_xyz(self, label, offset) -> None:
        arr = np.asarray(offset, dtype=float).reshape(3)
        self._offset = arr
        self.set_offset_calls.append(arr)

    # If a centre ever called this, the body would rotate -- a regression.
    def _set_step_rotation_deg_tuple(self, *args) -> None:
        self.rotation_calls.append(args)

    def _begin_history_capture(self) -> None:
        return None

    def _commit_history_capture(self) -> None:
        return None

    def _record_step_overlay_axis_anchor(self, label, **kwargs):
        record = {"label": label}
        record.update(kwargs)
        self.anchor_records.append(record)
        return record

    def _refresh_open_3d_views(self, *, step_label=None) -> None:
        self.refreshed_labels.append(step_label)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    # A. Behavioural: an off-axis face centre is translated onto the axis line with
    #    no rotation. centre=(21.4, 0, 274.4), current offset 0 -> next offset must
    #    zero x/y and keep z (delta = target - centre = (-21.4, 0, 0)).
    face_center = (21.4, 0.0, 274.4)
    fake = _FakeEditor(current_offset=(0.0, 0.0, 0.0))
    try:
        result = ScenePlacementMixin.center_step_feature_on_optical_axis(fake, "led", face_center)
    except Exception as exc:
        notes.append(f"FAIL: center_step_feature_on_optical_axis raised: {exc!r}")
        return False, notes

    if result is None:
        notes.append("FAIL: center_step_feature_on_optical_axis returned None for a valid LED face")
        passed = False
    if not fake.set_offset_calls:
        notes.append("FAIL: center never set a placement offset")
        passed = False
    else:
        next_offset = fake.set_offset_calls[-1]
        centered = np.asarray(face_center, dtype=float) + next_offset
        if not (abs(centered[0]) < 1e-6 and abs(centered[1]) < 1e-6):
            notes.append(
                f"FAIL: centred face is not on the axis line: face+offset={tuple(round(float(v), 4) for v in centered)} "
                f"(expected x=0, y=0)"
            )
            passed = False
        if abs(centered[2] - face_center[2]) > 1e-6:
            notes.append(
                f"FAIL: centring changed the along-axis z ({centered[2]:.4g} != {face_center[2]:.4g}); "
                f"it must only move perpendicular to the axis"
            )
            passed = False
    if fake.rotation_calls:
        notes.append(
            f"FAIL: centring rotated the body ({len(fake.rotation_calls)} _set_step_rotation_deg_tuple call(s)); "
            f"Center Picked Face must be translate-only"
        )
        passed = False
    # bugs/0120: the centre must use the GLOBAL axis, never the nearest traced ray.
    if not fake.global_frame_calls:
        notes.append(
            "FAIL: centring did not resolve the GLOBAL optical-axis frame "
            "(_global_optical_axis_frame_near_point was never called)"
        )
        passed = False
    if fake.nearest_ray_frame_calls:
        notes.append(
            f"FAIL: centring reached for the nearest-traced-ray frame "
            f"(_step_optical_axis_frame_near_point, {len(fake.nearest_ray_frame_calls)} call(s)); "
            f"Center Picked Face must target the global axis so an off-axis body lands on (0, 0)"
        )
        passed = False
    if fake.anchor_records:
        src = str(fake.anchor_records[-1].get("source", ""))
        if src != "feature_center_axis_center":
            notes.append(f"FAIL: axis anchor source is {src!r}, expected 'feature_center_axis_center'")
            passed = False

    # B. Source contract: the editor centre is translate-only (no rotation set).
    try:
        center_src = inspect.getsource(ScenePlacementMixin.center_step_feature_on_optical_axis)
    except Exception as exc:
        notes.append(f"FAIL: cannot read center_step_feature_on_optical_axis source: {exc!r}")
        return False, notes
    if "_set_step_rotation_deg_tuple" in center_src:
        notes.append(
            "FAIL: center_step_feature_on_optical_axis references _set_step_rotation_deg_tuple "
            "-- a centre must not rotate the body"
        )
        passed = False
    if "_set_step_placement_offset_xyz" not in center_src:
        notes.append("FAIL: center_step_feature_on_optical_axis does not set a placement offset")
        passed = False
    # bugs/0120 source contract: target the global axis helper, not the ray-seeking one.
    if "_global_optical_axis_frame_near_point" not in center_src:
        notes.append(
            "FAIL: center_step_feature_on_optical_axis does not resolve "
            "_global_optical_axis_frame_near_point -- it must target the global axis"
        )
        passed = False
    if "self._step_optical_axis_frame_near_point" in center_src:
        notes.append(
            "FAIL: center_step_feature_on_optical_axis still calls the nearest-traced-ray "
            "self._step_optical_axis_frame_near_point -- it must target the GLOBAL axis (bugs/0120)"
        )
        passed = False

    # C. Source contract: the right-click menu wires the centre handler, the dead
    #    normal-snap context handler is gone, and the menu label is the centre one.
    if hasattr(Open3DFaceAssignmentService, "_snap_step_face_to_optical_axis_from_context"):
        notes.append(
            "FAIL: the removed _snap_step_face_to_optical_axis_from_context handler is still present "
            "(the right-click rotate-snap should be gone)"
        )
        passed = False
    if not hasattr(Open3DFaceAssignmentService, "_center_step_face_to_optical_axis_from_context"):
        notes.append("FAIL: Open3DFaceAssignmentService is missing _center_step_face_to_optical_axis_from_context")
        passed = False
    else:
        handler_src = inspect.getsource(
            Open3DFaceAssignmentService._center_step_face_to_optical_axis_from_context
        )
        if "center_step_feature_on_optical_axis" not in handler_src:
            notes.append(
                "FAIL: _center_step_face_to_optical_axis_from_context does not call "
                "center_step_feature_on_optical_axis"
            )
            passed = False
        if "snap_step_feature_normal_to_optical_axis" in handler_src:
            notes.append(
                "FAIL: the centre handler still calls the rotating snap "
                "snap_step_feature_normal_to_optical_axis"
            )
            passed = False
    try:
        class_src = inspect.getsource(Open3DFaceAssignmentService)
    except Exception as exc:
        class_src = ""
        notes.append(f"FAIL: cannot read Open3DFaceAssignmentService source: {exc!r}")
        passed = False
    if class_src:
        if "Center Picked Face -> Optical Axis" not in class_src:
            notes.append("FAIL: the right-click menu no longer offers 'Center Picked Face -> Optical Axis'")
            passed = False
        if "Snap Picked Face -> Optical Axis" in class_src:
            notes.append(
                "FAIL: the right-click menu still offers 'Snap Picked Face -> Optical Axis' "
                "(the rotate item should be removed)"
            )
            passed = False
        # bugs/0120 source contract: the centre menu must hand the editor the face
        # CENTROID, resolved from the pick, not the raw cursor hit.
        if "_surface_center_from_face_ray_pick" not in class_src:
            notes.append(
                "FAIL: the right-click face menu does not resolve the face centroid via "
                "_surface_center_from_face_ray_pick -- Center Picked Face must centre the "
                "window centre, not the raw click point (bugs/0120)"
            )
            passed = False
        if "picked_center=face_center" not in class_src:
            notes.append(
                "FAIL: the 'Center Picked Face -> Optical Axis' menu does not bind the face "
                "centroid (picked_center=face_center) -- it must pass the centroid, not the "
                "raw click point, to _center_step_face_to_optical_axis_from_context (bugs/0120)"
            )
            passed = False

    if verbose:
        notes.append(
            "checked: center_step_feature_on_optical_axis zeroes x/y and keeps z with no rotation; "
            "source is translate-only; the right-click menu wires the centre handler and dropped the rotate snap"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0119: right-click 'Center Picked Face -> Optical Axis' is translate-only")
        return 0
    print("[FAIL] bugs/0119 center-picked-face guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
