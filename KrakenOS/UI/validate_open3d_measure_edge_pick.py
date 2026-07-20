"""Display-free guard for bugs/0353..0370 -- CAD-style Measure E/E entity picks.

The 0370 overhaul: a click resolves the entity under the cursor from the PICKED
CELL on the picked actor's OWN mesh (edge > face > point, no recognised-component
gate, no drawn-actor indirection), the first entity ARMS with a persistent
highlight, and every pair reduces to two world points
(services/measure_edge_pick.reduce_measure_entities), so the segment/label/
offset-handle/persistence/STEP-export pipeline is untouched.

HARD LESSON baked into this guard (the 0353..0369 saga): the old integration fake
STUBBED the show-highlight helper, hiding that the real helper NULLED the freshly
armed ``_measure_pending_edge`` -- so edge+edge never completed in-app while the
guard stayed green. The fakes below bind the REAL show helper (only the renderer
plumbing is stubbed), so state-nulling in the draw path can never hide again.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_measure_edge_pick
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services.measure_edge_pick import (
    closest_point_on_polyline,
    closest_point_on_segments,
    closest_points_between_polylines,
    closest_points_between_segment_sets,
    collinear_edge_run,
    measure_edge_pick,
    measure_point_pick,
    outline_pairs_to_segments,
    polyline_to_segments,
    reduce_measure_entities,
    reduce_measure_picks,
)

# The CO90 camera-side window's two vertical edges: 51.00 mm apart, offset endpoint
# spans so only the clamped perpendicular pair -- not an endpoint pair -- reads it.
EDGE_A = np.array([[-19.94, -27.12, 40.5], [-19.94, 24.38, 40.5]], dtype=float)
EDGE_B = np.array([[31.06, -20.0, 40.5], [31.06, 30.0, 40.5]], dtype=float)


def _edge_entity(polyline):
    pts = np.asarray(polyline, dtype=float)
    return {"kind": "edge", "segments": polyline_to_segments(pts), "world": pts[0]}


def _point_entity(world):
    return {"kind": "point", "segments": None, "world": np.asarray(world, dtype=float)}


class _StatusVar:
    def __init__(self):
        self.last = ""

    def set(self, text):
        self.last = str(text)


class _Fake:
    """Display-free stand-in binding the REAL measure methods -- including the REAL
    show-highlight helper (only renderer plumbing stubbed)."""

    _record_measure_point = Kraken3DInspector._record_measure_point
    _on_measure_entity_pick = Kraken3DInspector._on_measure_entity_pick
    _anchor_measure_point = Kraken3DInspector._anchor_measure_point
    _resolve_measure_point = Kraken3DInspector._resolve_measure_point
    _clear_measure_pending_edge = Kraken3DInspector._clear_measure_pending_edge
    _show_measure_pending_entity = Kraken3DInspector._show_measure_pending_entity

    def __init__(self):
        self._measure_pick_mode = True
        self._measure_entity_mode = True
        self._measure_p0 = None
        self._measure_reanchor = None
        self._measure_pending_edge = None
        self._measure_pending_edge_actors = []
        self._measure_segments = []
        self._renderer = None  # real show helper bails after the actor clear
        self.status_var = _StatusVar()

    def _measure_row_z_positions(self):
        return None

    def _clear_measure_snap_marker(self):
        pass

    def _set_axis_pick_cursor(self, _on):
        pass

    def _clear_dimension_anchor_snap_highlight(self):
        pass

    def _clear_measure_preview(self):
        pass

    def _refresh_measure_overlays(self):
        pass

    def _begin_measure_offset_adjust(self, _seg):
        return False

    def _update_mode_badge(self):
        pass

    def _remove_renderer_view_prop(self, _actor):
        pass

    def _add_renderer_view_prop(self, _actor):
        pass


def _segment_length(fake) -> float:
    seg = fake._measure_segments[-1]
    p0 = fake._resolve_measure_point(seg["p0"], seg["r0"], seg["dz0"])
    p1 = fake._resolve_measure_point(seg["p1"], seg["r1"], seg["dz1"])
    return float(np.linalg.norm(p1 - p0))


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # --- 1) PURE closest-pair math (chains + segment sets) -------------------------
    _pa, _pb, width = closest_points_between_polylines(EDGE_A, EDGE_B)
    if abs(width - 51.0) > 1e-9:
        failures.append(f"parallel opening edges must measure 51.00 mm, got {width!r}")
    _pa, _pb, skew = closest_points_between_polylines(
        [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]], [[5.0, 3.0, 4.0], [5.0, 9.0, 4.0]]
    )
    if abs(skew - 5.0) > 1e-9:
        failures.append(f"skew edge pair must measure 5.00 mm, got {skew!r}")
    q, dist = closest_point_on_polyline([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]], [3.0, 4.0, 0.0])
    if abs(dist - 4.0) > 1e-9 or abs(float(q[0]) - 3.0) > 1e-9:
        failures.append(f"point->edge projection wrong: q={q!r} dist={dist!r}")
    pa, pb, d = reduce_measure_picks(measure_point_pick([1, 2, 3]), measure_point_pick([4, 6, 3]))
    if abs(d - 5.0) > 1e-9:
        failures.append("point+point reduction is not a passthrough")
    _pa, _pb, d = reduce_measure_picks(measure_edge_pick(EDGE_A), measure_edge_pick(EDGE_B))
    if abs(d - 51.0) > 1e-9:
        failures.append(f"edge+edge reduction must give 51.00 mm, got {d!r}")

    chain_pts = np.array(
        [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [20.0, 0.0, 0.0], [20.0, 10.0, 0.0]], dtype=float
    )
    chain_pairs = [(0, 1), (1, 2), (2, 3)]
    run = collinear_edge_run(chain_pts, chain_pairs, (0, 1))
    if run.shape[0] != 3 or not np.allclose(run[-1], [20, 0, 0]):
        failures.append("collinear run must span the straight chain and stop at the corner")

    # segment-set entities (bugs/0370): face-face gap, entity reductions
    rect_pts = np.array([[0, 0, 0], [10, 0, 0], [10, 8, 0], [0, 8, 0]], dtype=float)
    rect_pairs = [(0, 1), (1, 2), (2, 3), (3, 0)]
    face_a = outline_pairs_to_segments(rect_pts, rect_pairs)
    face_b = outline_pairs_to_segments(rect_pts + np.array([0.0, 0.0, 4.0]), rect_pairs)
    _pa, _pb, gap = closest_points_between_segment_sets(face_a, face_b)
    if abs(gap - 4.0) > 1e-9:
        failures.append(f"parallel face outlines must gap 4.00 mm, got {gap!r}")
    q, dist = closest_point_on_segments(face_a, [5.0, 20.0, 0.0])
    if abs(dist - 12.0) > 1e-9:
        failures.append("point->face-outline projection wrong")
    _pa, _pb, d = reduce_measure_entities(_edge_entity(EDGE_A), _edge_entity(EDGE_B))
    if abs(d - 51.0) > 1e-9:
        failures.append("entity edge+edge reduction must give 51.00 mm")
    _pa, _pb, d = reduce_measure_entities(_point_entity([0, 0, 40.5]), _edge_entity(EDGE_B))
    if abs(d - 31.06) > 1e-9:
        failures.append("entity point+edge reduction must project onto the edge")
    _pa, _pb, d = reduce_measure_entities(_point_entity([1, 2, 3]), _point_entity([4, 6, 3]))
    if abs(d - 5.0) > 1e-9:
        failures.append("entity point+point reduction is not a passthrough")

    # --- 2) INTEGRATION: real record pipeline with the REAL show helper -------------
    fake = _Fake()
    fake._on_measure_entity_pick(_edge_entity(EDGE_A))
    if not isinstance(fake._measure_pending_edge, dict) or fake._measure_segments:
        failures.append(
            "first entity pick must ARM the pending entity (the 0353..0369 saga: the "
            "old show helper NULLED it right after arming)"
        )
    if not fake._measure_pick_mode:
        failures.append("arming must keep measure mode on")
    fake._on_measure_entity_pick(_edge_entity(EDGE_B))
    if len(fake._measure_segments) != 1:
        failures.append("second entity pick must complete exactly one segment")
    elif abs(_segment_length(fake) - 51.0) > 1e-9:
        failures.append(f"edge+edge segment must span 51.00 mm, got {_segment_length(fake)!r}")
    if fake._measure_pending_edge is not None or fake._measure_pick_mode:
        failures.append("completing the pair must clear the pending entity and leave measure mode")
    if getattr(fake, "_measure_entity_mode", True):
        failures.append("completing the pair must also end entity mode (zombie flag, bugs/0370)")

    fake2 = _Fake()
    fake2._record_measure_point(np.array([0.0, 0.0, 40.5]), None)
    fake2._on_measure_entity_pick(_edge_entity(EDGE_B))
    if len(fake2._measure_segments) != 1 or abs(_segment_length(fake2) - 31.06) > 1e-9:
        failures.append("point-first + entity-second must project onto the entity (31.06 mm)")

    fake3 = _Fake()
    fake3._record_measure_point(np.array([1.0, 2.0, 3.0]), None)
    fake3._record_measure_point(np.array([4.0, 6.0, 3.0]), None)
    if len(fake3._measure_segments) != 1 or abs(_segment_length(fake3) - 5.0) > 1e-9:
        failures.append("plain two-point flow regressed")
    if fake3._measure_pending_edge is not None:
        failures.append("plain two-point flow must never touch the pending entity")

    # degenerate SECOND entity must never strand the armed one (bugs/0367)
    fake4 = _Fake()
    fake4._on_measure_entity_pick(_edge_entity(EDGE_A))
    fake4._on_measure_entity_pick(
        {"kind": "edge", "segments": np.full((1, 2, 3), np.nan), "world": np.array([1.0, 2.0, 3.0])}
    )
    if fake4._measure_pending_edge is not None:
        failures.append("a degenerate second entity must not strand the armed one (bugs/0367)")

    # point entity pair completes too (nothing is ever un-measurable)
    fake5 = _Fake()
    fake5._on_measure_entity_pick(_point_entity([0.0, 0.0, 0.0]))
    fake5._on_measure_entity_pick(_point_entity([3.0, 4.0, 0.0]))
    if len(fake5._measure_segments) != 1 or abs(_segment_length(fake5) - 5.0) > 1e-9:
        failures.append("point+point entities must complete a 5.00 mm segment")

    # --- 3) WIRING: source needles ---------------------------------------------------
    press_src = inspect.getsource(Kraken3DInspector._on_left_button_press)
    for needle in (
        "_measure_entity_mode",
        "_edge_pick_alt_active",
        "_measure_resolve_entity",
        "_on_measure_entity_pick",
        "nothing under the cursor",  # bugs/0370: every click has a visible outcome
        "_measure_resolve_snap",  # the legacy point path survives verbatim
        "closest_point_on_segments",  # armed-entity reduction in the legacy path
    ):
        if needle not in press_src:
            failures.append(f"_on_left_button_press lost its {needle} wiring")

    resolve_src = inspect.getsource(Kraken3DInspector._measure_resolve_entity)
    for needle in (
        "GetCellId",  # the picked cell drives the resolution
        "mesh_has_face_index",
        "face_index_for_display_cell",
        "face_outline_from_face_indices",
        "cached_display_feature_edges",  # no-face-index fallback
        "nearest_display_edge",
        "depth_reference",
        "collinear_edge_run",
        "append_debug",  # breadcrumb on pick failure, never a silent None
    ):
        if needle not in resolve_src:
            failures.append(f"_measure_resolve_entity lost its {needle} wiring")
    if "_measure_recognised_component" in resolve_src or "_step_component_edge_outline" in resolve_src:
        failures.append("the entity resolver must NOT use the old gate/drawn-actor chain (bugs/0370)")

    show_src = inspect.getsource(Kraken3DInspector._show_measure_pending_entity)
    if "self._clear_measure_pending_edge()" in show_src:
        failures.append(
            "the show helper must clear ACTORS ONLY -- calling _clear_measure_pending_edge "
            "nulls the freshly armed state (the 0353..0369 root cause)"
        )
    pick_src = inspect.getsource(Kraken3DInspector._on_measure_entity_pick)
    before_reduce = pick_src.split("reduce_measure_entities(pending", 1)[0]
    if "reduce_measure_entities(pending" not in pick_src or "_clear_measure_pending_edge()" not in before_reduce:
        failures.append("the pending entity must be cleared BEFORE the reduce (strand-proof)")
    arm_zone = pick_src.split("# First pick", 1)[-1]
    if arm_zone.find("_show_measure_pending_entity") > arm_zone.find("_measure_pending_edge ="):
        failures.append("arming must draw BEFORE assigning state (belt-and-braces ordering)")

    hover_src = inspect.getsource(Kraken3DInspector._update_measure_hover_highlight)
    for needle in ("_measure_entity_mode", "_measure_resolve_entity", "_measure_entity_hover_key"):
        if needle not in hover_src:
            failures.append(f"the entity hover lost its {needle} wiring")
    entity_hover = hover_src.split("_measure_entity_mode", 1)[-1].split("if pickable", 1)[0]
    if "hover_key ==" not in entity_hover:
        failures.append(
            "the entity hover must be CHANGE-GATED on the hover key -- unchanged entity "
            "means no render and NO status write (bugs/0370: the per-move status "
            "clobbered every click result)"
        )

    entity_src = inspect.getsource(Kraken3DInspector.start_measure_entity_pick)
    if "start_measure_pick" not in entity_src or "_measure_entity_mode" not in entity_src:
        failures.append("start_measure_entity_pick must arm entity mode over the plain flow")
    for owner, method in (
        ("start_measure_pick", Kraken3DInspector.start_measure_pick),
        ("clear_measurements", Kraken3DInspector.clear_measurements),
        ("_record_measure_point", Kraken3DInspector._record_measure_point),
    ):
        if "_clear_measure_pending_edge" not in inspect.getsource(method):
            failures.append(f"{owner} does not clear the pending entity")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Measure entity-pick validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Measure entity-pick validation passed: clicks resolve the entity off the "
        "picked cell (edge > face > point, no gates), the first entity ARMS and "
        "stays armed (the show helper clears actors only), pairs reduce via the "
        "clamped closest-pair math (51.00 mm opening, 4.00 mm face gap), every "
        "click has a visible outcome, and the hover is change-gated so it never "
        "clobbers click feedback."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
