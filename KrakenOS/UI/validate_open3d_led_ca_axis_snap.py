#!/usr/bin/env python3
"""Display-free guard for the LED clear-aperture Alt-toggle + axis snap (bugs/0332, 0333).

User report (imported ILS0202 LED, two issues):
  1. "How should the ALT + Hover function now? Toggle between Surface and Edge
     highlight?" -- plain hover over a clear-aperture OPENING highlights its EDGE
     (rim); Alt should toggle to the SURFACE that owns the opening, mirroring the
     body-face path (plain = whole face, Alt = nearest edge). Before the fix Alt was
     a no-op over an opening (the opening pick returned early, ungated).
  2. "After highlighting the CA edge, right click snap to optical Axis option: the
     CA should be centered to the optical axis AND Normal to it, just now I tried,
     it is not. Also, since we might have multiple Axis now, after right click
     selection, prompt user to click on the intended optical axis." -- the old
     "Center Clear Aperture -> Optical Axis" was TRANSLATE-ONLY to a hard-coded
     global x=0/y=0 axis and never rotated the normal, so a tilted / off-axis
     opening stayed tilted and off-axis.

Fix:
  0332. ``step_feature_pick_for_display_xy`` gates the opening hover on
        ``_edge_pick_alt_active``: plain returns the opening EDGE feature; Alt
        returns ``_opening_owning_surface_feature`` (the whole owning face outline).
        Falls back to the edge feature when the owning surface can't be resolved,
        so Alt is inert rather than blank.
  0333. Both opening feature builders mark ``"opening": True`` so the right-click
        menu can detect an opening and offer "Snap Clear Aperture -> Optical Axis
        (center + normal)". That arms ``start_step_normal_axis_pick`` in the new
        ``feature_center`` anchor mode with the opening's own centroid + normal;
        clicking an axis routes ``_apply_step_normal_axis_pick`` ->
        ``_apply_step_feature_center_axis_pick`` -> the shared
        ``snap_step_feature_normal_to_optical_axis`` engine, which rotates the
        normal opposite the axis AND translates the centre onto it. The prompt tells
        the user to click the INTENDED optical axis (there can be several).

What it checks
--------------
  1. Alt toggle (behavioural): ``_opening_owning_surface_feature`` resolves the
     owning face's whole outline for a valid ``face_id`` and returns None for an
     empty one; the ``step_feature_pick_for_display_xy`` branch returns the EDGE
     opening feature plain and the SURFACE feature under Alt.
  2. Arm (behavioural): ``start_step_normal_axis_pick(anchor_mode="feature_center")``
     stores the opening centre/normal/label, arms the pick mode, and prompts for the
     INTENDED optical axis; non-finite geometry does NOT arm.
  3. Dispatch + engine (behavioural + source): ``_apply_step_normal_axis_pick``
     delegates ``feature_center`` mode to ``_apply_step_feature_center_axis_pick``,
     which calls ``snap_step_feature_normal_to_optical_axis`` (center + normal, NOT
     the translate-only centre) with the stored geometry and the clicked axis frame;
     the menu wires the opening snap and both builders mark the opening.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_ca_axis_snap

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types

import numpy as np

try:
    import pyvista as pv
except Exception:  # pragma: no cover
    pv = None


def _synthetic_face0_mesh():
    """One z=0 square (face index 0, 2 triangles) -- the owning surface."""
    quad = np.array([[0, 0, 0], [4, 0, 0], [4, 4, 0], [0, 4, 0]], dtype=float)
    tris = np.array([[quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]]], dtype=float)
    count = int(tris.shape[0])
    points = tris.reshape((-1, 3))
    faces = np.empty((count, 4), dtype=np.int64)
    faces[:, 0] = 3
    faces[:, 1] = np.arange(0, 3 * count, 3, dtype=np.int64)
    faces[:, 2] = faces[:, 1] + 1
    faces[:, 3] = faces[:, 1] + 2
    mesh = pv.PolyData(points, faces.reshape(-1))
    face_index = np.array([0, 0], dtype=np.int32)
    mesh.cell_data["kraken_step_selection_face_index"] = face_index
    mesh.cell_data["kraken_step_face_index"] = face_index
    mesh.field_data["kraken_step_analytic"] = np.asarray([1], dtype=np.int8)
    return mesh


def _fake_pick_inspector(mesh):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    insp = types.SimpleNamespace()
    insp._edge_pick_alt_active = False
    insp._step_label_is_round_lens_like = lambda _label: False
    insp._hover_overlay_for_feature = Kraken3DInspector._hover_overlay_for_feature
    insp.editor = types.SimpleNamespace(
        _transformed_imported_step_mesh_for_label=lambda _label: mesh,
        _step_overlay_fine_face_centroid_normal=lambda _label, _fid: (
            np.asarray([2.0, 2.0, 0.0]),
            np.asarray([0.0, 0.0, 1.0]),
            16.0,
        ),
    )
    return insp


class _Status:
    def __init__(self):
        self.text = ""

    def set(self, value):
        self.text = str(value)

    def get(self):
        return self.text


def _fake_axis_inspector():
    """A SimpleNamespace carrying every attribute the arm + apply paths touch."""
    status = _Status()
    editor = types.SimpleNamespace(
        _open3d_step_state_service=lambda: types.SimpleNamespace(
            selected_import_label=lambda pair: next((str(p) for p in pair if p), ""),
        ),
        status_var=_Status(),
        append_debug=lambda *_a, **_k: None,
        _selected_step_label=None,
    )
    fake = types.SimpleNamespace(
        status_var=status,
        editor=editor,
        _selected_step_feature_label="",
        _picker=object(),
        _step_normal_axis_pick_mode=False,
        _step_normal_axis_anchor_mode="body_center",
        _step_normal_axis_feature_center=None,
        _step_normal_axis_feature_normal=None,
        _step_normal_axis_feature_label="",
        _step_surface_center_axis_pick_mode=False,
        _step_carry_follow_state=None,
        _step_carry_drag_state=None,
        _step_carry_active_label=None,
        _step_carry_snap_ray_mode=False,
        _step_carry_snap_target_mode=False,
        _source_target_pick_mode=False,
        _center_row_to_ray_mode=False,
        _center_row_to_ray_face_id="",
        _placement_target_pick_mode=False,
        _placement_orient_pick_mode=False,
        _placement_orient_ray_mode=False,
        _step_rotation_active_label=None,
        _open3d_step_admin_panel_instance=None,
        # no-op UI hooks
        _set_step_carry_cursor=lambda *_a, **_k: None,
        _set_axis_pick_cursor=lambda *_a, **_k: None,
        _update_mode_badge=lambda *_a, **_k: None,
        _hide_regular_rays_for_center_axis_pick=lambda *_a, **_k: None,
        _world_xyz_text=lambda _c: "(x,y,z)",
        _clear_selected_step_feature_state=lambda *_a, **_k: None,
        # bugs/0334: the CA-snap apply tail now drops the pinned opening rim.
        _clear_selected_step_opening=lambda *_a, **_k: False,
        _set_optical_axis_highlight=lambda *_a, **_k: None,
        _restore_rays_after_step_axis_pick=lambda _l: False,
        refresh_from_editor=lambda *_a, **_k: None,
        _remove_step_rotation_handle_actors=lambda: False,
        render=lambda *_a, **_k: None,
    )
    return fake


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services import open3d_round_lens_pick as pick_mod
    from KrakenOS.UI.services import open3d_face_assignment as fa_mod

    failures: list[str] = []
    if pv is None:
        return False, ["FAIL: PyVista unavailable -- cannot exercise the CA axis-snap fix"]

    mesh = _synthetic_face0_mesh()

    # 1) Alt toggle -- owning-surface resolver + the pick branch.
    insp = _fake_pick_inspector(mesh)
    surf = pick_mod._opening_owning_surface_feature(insp, "led", {"face_id": "F000"})
    if not isinstance(surf, dict):
        failures.append("FAIL(1): _opening_owning_surface_feature must resolve a valid owning face")
    else:
        if str(surf.get("face_id", "")) != "F000":
            failures.append(f"FAIL(1): owning surface face_id must be 'F000', got {surf.get('face_id')!r}")
        outline = surf.get("feature", (None, None, None))[1]
        if outline is None or int(getattr(outline, "n_points", 0)) <= 0:
            failures.append("FAIL(1): owning surface must carry a non-empty whole-face outline")
    if pick_mod._opening_owning_surface_feature(insp, "led", {"face_id": ""}) is not None:
        failures.append("FAIL(1): an opening with no owning face must return None (Alt inert, not blank)")

    # Toggle behaviour through the real branch, with a synthetic opening hover.
    opening_feature = {
        "feature": (
            np.asarray([2.0, 2.0, 0.0]),
            Kraken3DInspector._hover_overlay_for_feature((2.0, 2.0, 0.0), mesh),
            np.asarray([0.0, 0.0, 1.0]),
        ),
        "surface_center": np.asarray([2.0, 2.0, 0.0]),
        "face_id": "F000",
        "through_pick": None,
        "opening": True,
    }
    original = pick_mod._step_opening_hover_pick
    pick_mod._step_opening_hover_pick = lambda _i, _l, _xy: opening_feature
    try:
        insp._edge_pick_alt_active = False
        plain = pick_mod.step_feature_pick_for_display_xy(insp, "led", (2.0, 2.0), cell_id=0)
        insp._edge_pick_alt_active = True
        alt = pick_mod.step_feature_pick_for_display_xy(insp, "led", (2.0, 2.0), cell_id=0)
    finally:
        pick_mod._step_opening_hover_pick = original
    if plain is not opening_feature:
        failures.append("FAIL(1): plain hover over an opening must return the EDGE opening feature unchanged")
    if not isinstance(alt, dict) or alt.get("opening"):
        failures.append("FAIL(1): Alt hover over an opening must return a SURFACE feature (no 'opening' marker)")
    elif str(alt.get("face_id", "")) != "F000":
        failures.append(f"FAIL(1): Alt surface feature must own face 'F000', got {alt.get('face_id')!r}")

    # 2) Arm feature_center mode -- stores geometry, prompts for the intended axis.
    fake = _fake_axis_inspector()
    Kraken3DInspector.start_step_normal_axis_pick(
        fake, "led", anchor_mode="feature_center",
        feature_center=(1.0, 2.0, 3.0), feature_normal=(0.0, 0.0, 1.0),
    )
    if not fake._step_normal_axis_pick_mode:
        failures.append("FAIL(2): feature_center arm must set _step_normal_axis_pick_mode")
    if str(fake._step_normal_axis_anchor_mode) != "feature_center":
        failures.append(f"FAIL(2): anchor mode must be 'feature_center', got {fake._step_normal_axis_anchor_mode!r}")
    if fake._step_normal_axis_feature_center is None or not np.allclose(
        np.asarray(fake._step_normal_axis_feature_center, dtype=float), [1.0, 2.0, 3.0]
    ):
        failures.append("FAIL(2): the opening centre must be stored for the pending axis pick")
    if str(fake._step_normal_axis_feature_label) != "led":
        failures.append("FAIL(2): the opening's STEP label must be stored")
    prompt = fake.status_var.text.lower()
    if "intended" not in prompt or "optical axis" not in prompt:
        failures.append(f"FAIL(2): arm must prompt to click the INTENDED optical axis, got {fake.status_var.text!r}")

    fake_bad = _fake_axis_inspector()
    Kraken3DInspector.start_step_normal_axis_pick(
        fake_bad, "led", anchor_mode="feature_center",
        feature_center=(np.nan, 0.0, 0.0), feature_normal=(0.0, 0.0, 1.0),
    )
    if fake_bad._step_normal_axis_pick_mode:
        failures.append("FAIL(2): non-finite opening geometry must NOT arm the pick mode")

    # 3a) Dispatch: feature_center mode routes to _apply_step_feature_center_axis_pick.
    routed = {"n": 0}
    disp = types.SimpleNamespace(
        _step_normal_axis_anchor_mode="feature_center",
        _apply_step_feature_center_axis_pick=lambda _ai: routed.__setitem__("n", routed["n"] + 1),
    )
    Kraken3DInspector._apply_step_normal_axis_pick(disp, {"axis_id": "axis:0"})
    if routed["n"] != 1:
        failures.append("FAIL(3a): feature_center mode must delegate to _apply_step_feature_center_axis_pick")

    # 3b) Engine: the apply calls snap (center + normal) with the stored geometry.
    calls = {}
    fake_apply = _fake_axis_inspector()
    fake_apply._step_normal_axis_feature_label = "led"
    fake_apply._step_normal_axis_feature_center = np.asarray([1.0, 2.0, 3.0])
    fake_apply._step_normal_axis_feature_normal = np.asarray([0.0, 0.0, 1.0])
    fake_apply._optical_axis_frame_from_pick = lambda _ai, _pk: {
        "target_point": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0), "axis_label": "Optical Axis",
    }

    def _snap(label, center, normal, *, axis_frame=None):
        calls["label"] = label
        calls["center"] = np.asarray(center, dtype=float)
        calls["normal"] = np.asarray(normal, dtype=float)
        calls["axis_frame"] = axis_frame
        return {"axis_label": "Optical Axis", "angle_error_deg": 0.0}

    fake_apply.editor.snap_step_feature_normal_to_optical_axis = _snap
    Kraken3DInspector._apply_step_feature_center_axis_pick(fake_apply, {"axis_id": "axis:0"})
    if calls.get("label") != "led":
        failures.append("FAIL(3b): apply must snap the stored opening's label")
    if "center" not in calls or not np.allclose(calls["center"], [1.0, 2.0, 3.0]):
        failures.append("FAIL(3b): apply must pass the opening CENTRE to the snap engine")
    if "normal" not in calls or not np.allclose(calls["normal"], [0.0, 0.0, 1.0]):
        failures.append("FAIL(3b): apply must pass the opening NORMAL to the snap engine")
    if calls.get("axis_frame") is None:
        failures.append("FAIL(3b): apply must pass the clicked axis frame to the snap engine")
    if fake_apply._step_normal_axis_pick_mode:
        failures.append("FAIL(3b): a successful snap must clear the pick mode")

    # 3c) Source contract -- center+normal engine (not translate-only), markers, wiring.
    apply_src = inspect.getsource(Kraken3DInspector._apply_step_feature_center_axis_pick)
    if "snap_step_feature_normal_to_optical_axis" not in apply_src:
        failures.append("FAIL(3c): CA snap must use snap_step_feature_normal_to_optical_axis (center + normal)")
    if "center_step_feature_on_optical_axis" in apply_src or "center_clear_aperture_on_optical_axis" in apply_src:
        failures.append("FAIL(3c): CA snap must NOT fall back to the translate-only centre")
    edge_src = inspect.getsource(Kraken3DInspector._clear_aperture_opening_edge_feature)
    loop_src = inspect.getsource(Kraken3DInspector._opening_loop_hover_feature)
    if '"opening": True' not in edge_src or '"opening": True' not in loop_src:
        failures.append("FAIL(3c): both opening feature builders must mark 'opening': True")
    menu_src = inspect.getsource(fa_mod.Open3DFaceAssignmentService._show_surface_function_context_menu)
    if "_snap_clear_aperture_to_optical_axis_from_context" not in menu_src:
        failures.append("FAIL(3c): the right-click menu must offer the CA center+normal axis snap")
    if 'feature_pick.get("opening")' not in menu_src:
        failures.append("FAIL(3c): the menu must detect an opening feature to offer the CA snap")
    handler_src = inspect.getsource(fa_mod.Open3DFaceAssignmentService._snap_clear_aperture_to_optical_axis_from_context)
    if 'anchor_mode="feature_center"' not in handler_src:
        failures.append("FAIL(3c): the CA snap handler must arm the feature_center anchor mode")

    # 4) bugs/0337 -- one-click CA->optical-axis snap when the scene has a single axis.
    # The two-step "click the dotted axis" is unusable for an opening offset from an
    # axis that runs THROUGH the body (hidden near the opening, visible only in the
    # screen corners), so a single unambiguous axis snaps on the menu click alone.
    Svc = fa_mod.Open3DFaceAssignmentService
    one_axis = [{
        "axis_id": "axis:global", "axis_label": "Optical Axis",
        "points": np.asarray([[0.0, 0.0, -100.0], [0.0, 0.0, 100.0]], dtype=float),
    }]

    def _closest(pts, c):
        c = np.asarray(c, dtype=float).reshape(-1)[:3]
        return np.asarray([0.0, 0.0, float(c[2])]), np.asarray([0.0, 0.0, 1.0])

    svc = types.SimpleNamespace(
        _optical_axis_pick_records=one_axis,
        editor=types.SimpleNamespace(_closest_polyline_point_and_direction=_closest),
    )
    info = Svc._single_optical_axis_pick_info(svc, (5.0, 1.0, 2.0))
    if not isinstance(info, dict):
        failures.append("FAIL(4): a single optical axis must yield a one-click pick payload")
    else:
        if str(info.get("axis_id", "")) != "axis:global":
            failures.append(f"FAIL(4): single-axis payload must carry the axis id, got {info.get('axis_id')!r}")
        pw = np.asarray(info.get("picked_world", []), dtype=float).reshape(-1)
        if pw.size < 3 or not np.allclose(pw[:3], [5.0, 1.0, 2.0]):
            failures.append("FAIL(4): picked_world must be the opening centre (perpendicular-foot target)")

    two_axes = [
        {"axis_id": "axis:global", "points": np.asarray([[0, 0, -100], [0, 0, 100]], dtype=float)},
        {"axis_id": "axis:branch", "points": np.asarray([[0, 10, -100], [0, 10, 100]], dtype=float)},
    ]
    svc_multi = types.SimpleNamespace(
        _optical_axis_pick_records=two_axes,
        editor=types.SimpleNamespace(_closest_polyline_point_and_direction=_closest),
    )
    if Svc._single_optical_axis_pick_info(svc_multi, (0.0, 0.0, 0.0)) is not None:
        failures.append("FAIL(4): several optical axes must NOT auto-pick (keep the two-step)")

    svc_empty = types.SimpleNamespace(
        _optical_axis_pick_records=[],
        editor=types.SimpleNamespace(_closest_polyline_point_and_direction=_closest),
    )
    if Svc._single_optical_axis_pick_info(svc_empty, (0.0, 0.0, 0.0)) is not None:
        failures.append("FAIL(4): no optical axis records must return None")

    # 4b) behavioural: single axis -> arm THEN apply in one right-click (no 2nd click).
    seq = {"arm": 0, "apply": 0}
    handler_svc = _fake_axis_inspector()
    handler_svc._optical_axis_pick_records = one_axis
    handler_svc.editor._closest_polyline_point_and_direction = _closest
    handler_svc._single_optical_axis_pick_info = types.MethodType(Svc._single_optical_axis_pick_info, handler_svc)

    def _arm(label, *, anchor_mode="body_center", feature_center=None, feature_normal=None):
        seq["arm"] += 1
        handler_svc._step_normal_axis_pick_mode = True

    handler_svc.start_step_normal_axis_pick = _arm
    handler_svc._apply_step_normal_axis_pick = lambda _ai: seq.__setitem__("apply", seq["apply"] + 1)
    Svc._snap_clear_aperture_to_optical_axis_from_context(handler_svc, "led", (5.0, 1.0, 2.0), (0.0, 0.0, 1.0))
    if seq["arm"] != 1:
        failures.append("FAIL(4b): the CA snap must arm the feature_center pick")
    if seq["apply"] != 1:
        failures.append("FAIL(4b): a single optical axis must apply the snap immediately (one click)")

    # 4c) behavioural: several axes -> arm only, no immediate apply (two-step retained).
    seq2 = {"arm": 0, "apply": 0}
    handler_multi = _fake_axis_inspector()
    handler_multi._optical_axis_pick_records = two_axes
    handler_multi.editor._closest_polyline_point_and_direction = _closest
    handler_multi._single_optical_axis_pick_info = types.MethodType(Svc._single_optical_axis_pick_info, handler_multi)

    def _arm2(label, *, anchor_mode="body_center", feature_center=None, feature_normal=None):
        seq2["arm"] += 1
        handler_multi._step_normal_axis_pick_mode = True

    handler_multi.start_step_normal_axis_pick = _arm2
    handler_multi._apply_step_normal_axis_pick = lambda _ai: seq2.__setitem__("apply", seq2["apply"] + 1)
    Svc._snap_clear_aperture_to_optical_axis_from_context(handler_multi, "led", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    if seq2["arm"] != 1 or seq2["apply"] != 0:
        failures.append("FAIL(4c): several optical axes must keep the explicit click-the-axis step")

    # 4d) source contract: the handler one-clicks through the helper + apply.
    snap_src = inspect.getsource(Svc._snap_clear_aperture_to_optical_axis_from_context)
    if "_single_optical_axis_pick_info" not in snap_src or "_apply_step_normal_axis_pick" not in snap_src:
        failures.append("FAIL(4d): the CA snap handler must one-click via _single_optical_axis_pick_info + _apply_step_normal_axis_pick")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] LED clear-aperture Alt-toggle + optical-axis center+normal snap")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Alt toggles opening EDGE<->SURFACE; CA right-click snap centres AND "
          "normals the opening on the intended optical axis (not translate-only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
