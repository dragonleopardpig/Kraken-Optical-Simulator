#!/usr/bin/env python3
"""Display-free guard for the LED STEP hover face/edge modes + jitter (bugs/0323).

User report (imported ILS0202 LED):
  1. "the hover highlight only a few. Sometime highlight edge, sometime I orbit
     the scene, the surface highlight, not edge, very inconsistent." The old code
     ran the whole-face->nearest-edge refinement on EVERY plain hover, so a
     sub-pixel cursor shift or an orbit flipped face<->edge unpredictably.
  2. "some highlight is phantom, meaning it highlight edges that does not match
     with drawn outline of the part." A single analytic face group can wrap the
     whole body (measured up to 134 mm on this LED), so a real-but-OCCLUDED
     far-side boundary segment could project near the cursor and win the pure-2D
     edge contest -- an edge the user cannot see.
  3. "during left or right click, a little bit of mouse movement will make the
     highlight disappear." A 4 px drag threshold turned a wobbly left-click into
     a camera orbit (dropping the pick); an unbound <B3-Motion> let a right-drag
     re-hover and clear the highlight the context menu was about to use.

Fix:
  A. Modifier-driven hover -- plain hover = WHOLE FACE (stable, no flicker); hold
     Alt = nearest DRAWN edge. The edge refinement in
     ``step_feature_pick_for_display_xy`` is gated on ``_edge_pick_alt_active``;
     the click inherits whatever is highlighted (WYSIWYG).
  B. Depth guard -- ``nearest_display_edge`` takes a ``depth_reference`` (the
     world-space front pick point). Screen-near candidates are ranked by 3D
     distance to that point first, so the FRONT edge wins over an occluded
     far-side one. ``None`` keeps the pure-2D behaviour byte-for-byte.
  C. Jitter tolerance -- drag threshold 4 -> 8 px (a small wobble stays a pick);
     the right button freezes the scene hover (tracked + <B3-Motion> swallowed)
     so a click cannot jitter the highlight away.

What it checks
--------------
  A. Gate (behavioural): on a synthetic analytic mesh (raw-fallback path), a
     near-edge hover returns the WHOLE FACE when ``_edge_pick_alt_active`` is
     False and a single EDGE (suffixed face_id) when True.
  B. Depth guard (pure): with a far segment 2D-closer than a front one,
     ``nearest_display_edge`` picks the FAR one with no ``depth_reference`` and
     the FRONT one with the front pick point -- and ``None`` is unchanged.
  C. Edge refinement threads depth: ``_edge_refined_feature(pick_point=front)``
     resolves to the front edge on a two-segment outline.
  D. Modifier bits: ``_event_alt_pressed`` <-> 0x0008, ``_event_control_pressed``
     <-> 0x0004, and the two are distinct.
  E. Source contract: both ``_edge_refined_feature`` calls in
     ``step_feature_pick_for_display_xy`` are gated by ``_edge_pick_alt_active``
     and pass ``pick_point``; ``_edge_refined_feature`` forwards ``depth_reference``.
  F. Mouse/interaction wiring (source): drag threshold is 8; ``hover_motion``
     records Alt and clears the right-button freeze; ``left_press`` records Alt;
     ``right_press`` sets the freeze; ``<B3-Motion>``/``<ButtonRelease-3>`` are
     bound; ``_on_mouse_move`` early-returns while the right button is held.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_edge_pick_modes

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
    """One z=0 square (face index 0, 2 triangles) -- the raw-fallback body."""
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


def _fake_inspector(mesh, *, alt: bool):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    insp = types.SimpleNamespace()
    insp._edge_pick_alt_active = bool(alt)
    insp._step_label_is_round_lens_like = lambda _label: False
    insp._picker = types.SimpleNamespace(GetPickPosition=lambda: (2.0, 0.0, 0.0))
    insp._world_to_display_2d = lambda p: np.asarray([p[0], p[1]], dtype=float)
    insp._hover_overlay_for_feature = Kraken3DInspector._hover_overlay_for_feature
    insp.editor = types.SimpleNamespace(
        _step_overlay_face_metadata=lambda _label: {"faces": []},
        _transformed_imported_step_mesh_for_label=lambda _label: mesh,
    )
    return insp


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.open3d_face_index_edges import (
        line_segment_pairs,
        nearest_display_edge,
    )
    from KrakenOS.UI.services import open3d_round_lens_pick as pick_mod
    from KrakenOS.UI.services import open3d_mouse_bindings as mb_mod
    from KrakenOS.UI.services import open3d_interaction as interaction_mod

    failures: list[str] = []
    if pv is None:
        return False, ["FAIL: PyVista unavailable -- cannot exercise the hover fix"]

    mesh = _synthetic_face0_mesh()

    # A) Gate (behavioural): near-edge hover -> whole face when Alt off, edge when on.
    cursor = (2.0, 0.3)  # just below the bottom edge midpoint (2,0)
    res_face = pick_mod.step_feature_pick_for_display_xy(
        _fake_inspector(mesh, alt=False), "led", cursor, cell_id=0
    )
    res_edge = pick_mod.step_feature_pick_for_display_xy(
        _fake_inspector(mesh, alt=True), "led", cursor, cell_id=0
    )
    if res_face is None or res_edge is None:
        failures.append("FAIL(A): raw-fallback hover returned nothing on the synthetic face")
    else:
        face_id_plain = str(res_face.get("face_id", ""))
        face_id_alt = str(res_edge.get("face_id", ""))
        if face_id_plain != "F000":
            failures.append(f"FAIL(A): plain hover must stay WHOLE FACE 'F000', got {face_id_plain!r}")
        if not (face_id_alt.startswith("F000") and "e" in face_id_alt[4:]):
            failures.append(f"FAIL(A): Alt hover must refine to an EDGE ('F000eN'), got {face_id_alt!r}")

    # B) Depth guard (pure): a FAR segment 2D-closer than a FRONT one.
    project = lambda p: (float(p[0]), float(p[1]))
    points = np.array([
        [1.5, 0.0, 100.0], [2.5, 0.0, 100.0],   # FAR: 2D dist ~1.5, behind
        [4.5, 0.0, 0.0],   [5.5, 0.0, 0.0],     # FRONT: 2D dist ~4.5, at pick depth
    ], dtype=float)
    pairs = [(0, 1), (2, 3)]
    hit_2d = nearest_display_edge(points, pairs, (0.0, 0.0), project, tolerance_px=14.0)
    hit_depth = nearest_display_edge(points, pairs, (0.0, 0.0), project, tolerance_px=14.0,
                                     depth_reference=(4.0, 0.0, 0.0))
    hit_default = nearest_display_edge(points, pairs, (0.0, 0.0), project, tolerance_px=14.0)
    if hit_2d is None or int(hit_2d[0]) != 0:
        failures.append(f"FAIL(B): pure-2D nearest must be the FAR segment (ordinal 0), got {hit_2d}")
    if hit_depth is None or int(hit_depth[0]) != 1:
        failures.append(f"FAIL(B): depth-aware nearest must be the FRONT segment (ordinal 1), got {hit_depth}")
    if hit_default is None or int(hit_default[0]) != 0:
        failures.append("FAIL(B): depth_reference=None must be byte-for-byte the old pure-2D result")

    # C) _edge_refined_feature threads the depth reference to the front edge.
    outline = pv.PolyData(
        points,
        lines=np.array([2, 0, 1, 2, 2, 3], dtype=np.int64),
    )
    fake = types.SimpleNamespace(
        _world_to_display_2d=lambda p: np.asarray(project(p), dtype=float),
        _hover_overlay_for_feature=Kraken3DInspector._hover_overlay_for_feature,
    )
    base_feature = (
        np.zeros(3, dtype=float),
        Kraken3DInspector._hover_overlay_for_feature((0.0, 0.0, 0.0), outline),
        np.asarray((0.0, 0.0, 1.0), dtype=float),
    )
    _feat_far, id_far = pick_mod._edge_refined_feature(
        fake, base_feature, "F000", outline, (0.0, 0.0), tolerance_px=14.0
    )
    _feat_front, id_front = pick_mod._edge_refined_feature(
        fake, base_feature, "F000", outline, (0.0, 0.0), tolerance_px=14.0,
        pick_point=(4.0, 0.0, 0.0),
    )
    if not id_far.endswith("e0"):
        failures.append(f"FAIL(C): without pick_point the 2D-nearest (far) edge e0 should win, got {id_far!r}")
    if not id_front.endswith("e1"):
        failures.append(f"FAIL(C): with a front pick_point the visible edge e1 should win, got {id_front!r}")

    # D) Modifier bits are the right, distinct masks.
    class _Evt:
        def __init__(self, state):
            self.state = state
    if not Kraken3DInspector._event_alt_pressed(_Evt(0x0008)):
        failures.append("FAIL(D): _event_alt_pressed must be True for state & 0x0008 (Mod1)")
    if not Kraken3DInspector._event_alt_pressed(_Evt(0x20000)):
        failures.append("FAIL(D): _event_alt_pressed must be True for state & 0x20000 (Mod5 Alt)")
    if Kraken3DInspector._event_alt_pressed(_Evt(0x0004)):
        failures.append("FAIL(D): _event_alt_pressed must be False for a Control-only state")
    if not Kraken3DInspector._event_control_pressed(_Evt(0x0004)):
        failures.append("FAIL(D): _event_control_pressed must be True for state & 0x0004")
    if Kraken3DInspector._event_control_pressed(_Evt(0x0008)):
        failures.append("FAIL(D): _event_control_pressed must be False for an Alt-only state")

    # E) Source contract in step_feature_pick_for_display_xy + _edge_refined_feature.
    pick_src = inspect.getsource(pick_mod.step_feature_pick_for_display_xy)
    if pick_src.count("_edge_pick_alt_active") < 2:
        failures.append("FAIL(E): both edge-refine calls must be gated on _edge_pick_alt_active")
    if pick_src.count("pick_point=pick_point") < 2:
        failures.append("FAIL(E): both edge-refine calls must forward pick_point for the depth guard")
    refine_src = inspect.getsource(pick_mod._edge_refined_feature)
    if "depth_reference=pick_point" not in refine_src:
        failures.append("FAIL(E): _edge_refined_feature must pass depth_reference into nearest_display_edge")

    # F) Mouse-bindings + interaction wiring (source).
    mb_src = inspect.getsource(mb_mod.Open3DMouseBindingsService._install_pick_only_left_click_bindings)
    if "drag_threshold_px = 8" not in mb_src:
        failures.append("FAIL(F): left-click drag threshold must be 8 px (jitter tolerance)")
    if "self._edge_pick_alt_active = self._event_alt_pressed(event)" not in mb_src:
        failures.append("FAIL(F): left_press must record the Alt modifier at press time")
    # bugs/0324 reshaped hover_motion to remember the previous Alt state (so it can
    # re-fire the pick on a transition); it still records the live modifier, now
    # via alt_now.
    if "alt_now = self._event_alt_pressed(event)" not in mb_src:
        failures.append("FAIL(F): hover_motion must record the live Alt modifier")
    if "self._right_button_active = True" not in mb_src or "self._right_button_active = False" not in mb_src:
        failures.append("FAIL(F): right button must set and clear the hover-freeze flag")
    if '"<B3-Motion>"' not in mb_src or '"<ButtonRelease-3>"' not in mb_src:
        failures.append("FAIL(F): <B3-Motion> and <ButtonRelease-3> must be bound (freeze right-drag)")
    move_src = inspect.getsource(interaction_mod.Open3DInteractionService._on_mouse_move)
    if 'getattr(self, "_right_button_active", False)' not in move_src:
        failures.append("FAIL(F): _on_mouse_move must freeze hover while the right button is held")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] LED STEP hover face/edge modes + jitter tolerance")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] plain hover = whole face, Alt = nearest DRAWN (front) edge; "
          "right-button + wider threshold keep a click from jittering the highlight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
