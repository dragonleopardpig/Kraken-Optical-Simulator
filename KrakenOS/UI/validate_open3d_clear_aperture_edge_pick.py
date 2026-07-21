"""Display-free guard for bugs/0379 -- the interactive multi-EDGE clear-aperture pick.

Pins the mode STATE MACHINE (arm -> collect -> finish -> store, plus cancel), the mode
badge text, and the CA-rectangle DRAW geometry, all without VTK. The pure ray-stop
geometry contract lives in ``validate_open3d_clear_aperture_stops`` (phase 319); this
guards the UI wiring that feeds it.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_clear_aperture_edge_pick
"""

from __future__ import annotations

import numpy as np


class _FakeService:
    def selected_import_label(self, candidates):
        for c in candidates:
            if c:
                return str(c).strip().lower()
        return ""


class _FakeEditor:
    def __init__(self):
        self.store: dict[str, list] = {}
        self.debug: list = []

    def add_clear_aperture_rect_from_edges(self, label, edges):
        from KrakenOS.UI.services.clear_aperture_stops import rect_from_edges

        rect = rect_from_edges(edges)
        if rect is None:
            return None
        self.store.setdefault(str(label).strip().lower(), []).append(rect)
        return rect

    def clear_aperture_edge_rects(self, label):
        return [dict(r) for r in self.store.get(str(label).strip().lower(), [])]

    def remove_clear_aperture_edge_rects(self, label):
        label = str(label).strip().lower()
        n = len(self.store.get(label, []))
        self.store.pop(label, None)
        return n

    def append_debug(self, *a, **k):
        self.debug.append(a)

    def _open3d_step_state_service(self):
        return _FakeService()


class _FakeOverlay:
    def __init__(self, points):
        self.points = np.asarray(points, dtype=float)


class _StatusVar:
    def __init__(self):
        self.messages: list[str] = []

    def set(self, text):
        self.messages.append(str(text))

    def last(self):
        return self.messages[-1] if self.messages else ""


def _fake_inspector():
    from KrakenOS.UI import open3d_inspector as _oi
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.open3d_interaction_mode import InteractionModeState

    # bugs/0379: the module-global ``pv`` is bound lazily during real inspector init
    # (open3d_inspector.py: ``pv = layout_editor_module.pv``); a __new__ instance never
    # ran it, so the draw's ``pv.lines_from_points`` would hit None. Bind it as init would,
    # so this guard exercises the SAME draw path production uses during scene refresh.
    if getattr(_oi, "pv", None) is None:
        import pyvista as _pv

        _oi.pv = _pv

    insp = Kraken3DInspector.__new__(Kraken3DInspector)
    insp.tk = object()  # guard tkinter __getattr__ recursion on a __new__ instance
    insp._interaction_mode_state = InteractionModeState()
    insp.editor = _FakeEditor()
    insp.status_var = _StatusVar()
    insp._selected_step_feature_label = None
    insp._step_clear_aperture_pick_label = ""
    insp._step_clear_aperture_pick_edges = False
    insp._step_clear_aperture_edge_buffer = []
    # plain-attr pick state that start_...edge_pick / cancel clear (properties are no-ops
    # when not in their own mode, so they need no seeding)
    insp._step_carry_follow_state = None
    insp._step_carry_drag_state = None
    insp._row_carry_drag_state = None
    insp._axis_slide_drag_state = None
    insp._center_row_to_ray_face_id = ""
    insp._dimension_anchor_pick_mode = False
    # side-effect stubs
    insp._update_mode_badge = lambda *a, **k: None
    insp._set_axis_pick_cursor = lambda *a, **k: None
    insp._set_step_carry_cursor = lambda *a, **k: None
    insp._set_step_hover_outline = lambda *a, **k: None
    insp.refresh_from_editor = lambda *a, **k: None
    insp._cancel_step_carry_hold_timer = lambda *a, **k: None
    insp._cancel_row_carry_hold_timer = lambda *a, **k: None
    insp._draw_calls = []
    insp._add_mesh_actor = lambda mesh, **k: insp._draw_calls.append((mesh, k))
    return insp


def _corners_3_edges():
    cx, cy, cz, hu, hv = 10.0, -5.0, 100.0, 25.5, 25.75
    C = {
        "TL": (cx - hu, cy + hv, cz), "TR": (cx + hu, cy + hv, cz),
        "BR": (cx + hu, cy - hv, cz), "BL": (cx - hu, cy - hv, cz),
    }

    def edge(a, b):
        return np.linspace(np.array(C[a]), np.array(C[b]), 8)

    return [edge("TL", "TR"), edge("TR", "BR"), edge("BR", "BL")]


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # --- ARM --------------------------------------------------------------------
    insp = _fake_inspector()
    insp.start_step_clear_aperture_edge_pick("led")
    if not insp._step_clear_aperture_pick_mode:
        failures.append("arm: _step_clear_aperture_pick_mode should be True")
    if not insp._step_clear_aperture_pick_edges:
        failures.append("arm: _step_clear_aperture_pick_edges should be True")
    if insp._step_clear_aperture_pick_label != "led":
        failures.append(f"arm: label = {insp._step_clear_aperture_pick_label!r}, expected 'led'")
    if insp._step_clear_aperture_edge_buffer:
        failures.append("arm: edge buffer must start empty")

    # --- COLLECT (stub the shared resolver so hover==click by construction) ------
    edges = _corners_3_edges()

    def _fake_pick(points):
        return lambda *a, **k: {"feature": (points.mean(axis=0), _FakeOverlay(points), None)}

    for i, e in enumerate(edges):
        insp._step_feature_pick_for_display_xy = _fake_pick(e)
        insp._collect_step_clear_aperture_edge("led", (100 + i, 200), actor=None, actor_key=None, cell_id=-1)
    if len(insp._step_clear_aperture_edge_buffer) != 3:
        failures.append(f"collect: buffer has {len(insp._step_clear_aperture_edge_buffer)} edges, expected 3")

    # A pick with no resolvable feature must NOT append (and must not crash).
    insp._step_feature_pick_for_display_xy = lambda *a, **k: None
    insp._collect_step_clear_aperture_edge("led", (5, 5), actor=None, actor_key=None, cell_id=-1)
    if len(insp._step_clear_aperture_edge_buffer) != 3:
        failures.append("collect: an unresolved pick must not grow the buffer")

    # A collect on the WRONG label must be ignored.
    insp._step_feature_pick_for_display_xy = _fake_pick(edges[0])
    insp._collect_step_clear_aperture_edge("camera", (5, 5), actor=None, actor_key=None, cell_id=-1)
    if len(insp._step_clear_aperture_edge_buffer) != 3:
        failures.append("collect: a wrong-label click must be ignored")

    # --- BADGE ------------------------------------------------------------------
    badge = insp._active_mode_badge_text()
    if "EDGES" not in badge.upper() or "3 EDGE" not in badge.upper().replace("(S)", ""):
        failures.append(f"badge: edge-mode text unexpected: {badge!r}")

    # --- FINISH -----------------------------------------------------------------
    ok = insp.finish_step_clear_aperture_edge_pick()
    if not ok:
        failures.append("finish: should return True for a valid 3-edge buffer")
    if insp._step_clear_aperture_pick_mode or insp._step_clear_aperture_pick_edges:
        failures.append("finish: must exit the pick mode")
    if insp._step_clear_aperture_edge_buffer:
        failures.append("finish: must clear the edge buffer")
    stored = insp.editor.clear_aperture_edge_rects("led")
    if len(stored) != 1:
        failures.append(f"finish: editor stored {len(stored)} rects, expected 1")
    else:
        halves = sorted([stored[0]["half_u"], stored[0]["half_v"]])
        if abs(halves[0] - 25.5) > 0.05 or abs(halves[1] - 25.75) > 0.05:
            failures.append(f"finish: stored extent {halves} (expected ~25.5 x 25.75)")

    # --- FINISH with an empty buffer is a graceful no-op -------------------------
    insp2 = _fake_inspector()
    insp2.start_step_clear_aperture_edge_pick("led")
    if insp2.finish_step_clear_aperture_edge_pick():
        failures.append("finish(empty): must return False when nothing is picked")

    # --- DRAW -------------------------------------------------------------------
    insp._draw_calls = []
    insp._add_clear_aperture_edge_rect_actors("led")
    if len(insp._draw_calls) != 1:
        failures.append(f"draw: expected 1 rectangle actor, got {len(insp._draw_calls)}")
    else:
        mesh, _kw = insp._draw_calls[0]
        pts = np.asarray(mesh.points, dtype=float)
        if pts.shape[0] < 4:
            failures.append("draw: rectangle polyline has too few points")
        else:
            # closed loop bbox must match the opening extent (~51 x 51.5)
            span = pts.max(axis=0) - pts.min(axis=0)
            planar = sorted(span)[1:]  # drop the ~0 out-of-plane axis
            if abs(planar[0] - 51.0) > 0.2 or abs(planar[1] - 51.5) > 0.2:
                failures.append(f"draw: rectangle span {planar} (expected ~51 x 51.5)")

    # --- CANCEL clears a half-collected buffer ----------------------------------
    insp3 = _fake_inspector()
    insp3.start_step_clear_aperture_edge_pick("led")
    insp3._step_feature_pick_for_display_xy = _fake_pick(edges[0])
    insp3._collect_step_clear_aperture_edge("led", (1, 1), actor=None, actor_key=None, cell_id=-1)
    # Drive only the reset core: stub the operation-labels probe truthy and swallow any
    # later unseeded-attr access -- the CA reset lines run before the rest of cancel.
    insp3._active_3d_operation_labels = lambda: ["clear-aperture edge pick"]
    try:
        insp3.cancel_active_3d_operation()
    except AttributeError:
        pass
    if insp3._step_clear_aperture_pick_mode or insp3._step_clear_aperture_pick_edges:
        failures.append("cancel: must leave the pick mode")
    if insp3._step_clear_aperture_edge_buffer:
        failures.append("cancel: must drop the half-collected edge buffer")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Clear-aperture edge-pick validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Clear-aperture edge-pick validation passed: arm -> collect (hover==click via the "
        "shared resolver) -> finish stores a rectangle; empty finish is a no-op; the draw "
        "outlines the opening; cancel drops a half-collected buffer."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
