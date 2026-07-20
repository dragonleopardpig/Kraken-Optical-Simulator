"""Display-free guard for bugs/0353 -- Measure tool edge-to-edge picks.

Alt+click in MEASURE mode picks the nearest DRAWN edge as an entity (the hover
contract's modifier, penta 287/288); every pick pair reduces to two world points
(services/measure_edge_pick) before recording, so the segment/label/offset-handle/
persistence/STEP-export pipeline is untouched and the plain point-click path stays
byte-identical.

Checks:
1. PURE -- clamped closest-pair math: two parallel drawn edges 51.00 mm apart
   measure exactly 51.00 (an opening's clear width); a skew pair; point->edge
   projection; the point+point passthrough; and the collinear-run extension that
   walks a subdivided straight edge but stops at a corner.
2. INTEGRATION -- the real ``_on_measure_edge_pick`` + ``_record_measure_point``
   driven on a display-free fake: edge+edge arms then completes a 51.00 mm
   segment; point-first + edge-second projects onto the edge; two plain point
   picks still produce the plain segment with the pending state untouched.
3. WIRING -- source needles: the click fork gates on ``_edge_pick_alt_active``
   and routes to ``_measure_resolve_edge``/``_on_measure_edge_pick`` while the
   legacy ``_measure_resolve_snap`` path survives verbatim; the edge resolver
   honours the recognised-component gate and rides the drawn-edge machinery;
   arm/clear lifecycle hooks exist in start/clear/record/hover.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_measure_edge_pick
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services.measure_edge_pick import (
    closest_point_on_polyline,
    closest_points_between_polylines,
    collinear_edge_run,
    measure_edge_pick,
    measure_point_pick,
    reduce_measure_picks,
)

# The CO90 camera-side window's two vertical edges (x = -19.94 and +31.06 at the
# frame plane): 51.00 mm apart, with deliberately offset endpoint spans so only
# the clamped perpendicular pair -- not an endpoint pair -- reads the width.
EDGE_A = np.array([[-19.94, -27.12, 40.5], [-19.94, 24.38, 40.5]], dtype=float)
EDGE_B = np.array([[31.06, -20.0, 40.5], [31.06, 30.0, 40.5]], dtype=float)


class _StatusVar:
    def __init__(self):
        self.last = ""

    def set(self, text):
        self.last = str(text)


class _Fake:
    """Minimal display-free stand-in binding the REAL measure methods under test."""

    _record_measure_point = Kraken3DInspector._record_measure_point
    _on_measure_edge_pick = Kraken3DInspector._on_measure_edge_pick
    _anchor_measure_point = Kraken3DInspector._anchor_measure_point
    _resolve_measure_point = Kraken3DInspector._resolve_measure_point
    _clear_measure_pending_edge = Kraken3DInspector._clear_measure_pending_edge

    def __init__(self):
        self._measure_pick_mode = True
        self._measure_p0 = None
        self._measure_reanchor = None
        self._measure_pending_edge = None
        self._measure_pending_edge_actors = []
        self._measure_segments = []
        self.status_var = _StatusVar()
        self.shown_pending = None

    # display-free stubs around the real pipeline
    def _measure_row_z_positions(self):
        return None

    def _show_measure_pending_edge(self, polyline):
        self.shown_pending = np.asarray(polyline, dtype=float)

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


def _segment_length(fake) -> float:
    seg = fake._measure_segments[-1]
    p0 = fake._resolve_measure_point(seg["p0"], seg["r0"], seg["dz0"])
    p1 = fake._resolve_measure_point(seg["p1"], seg["r1"], seg["dz1"])
    return float(np.linalg.norm(p1 - p0))


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # --- 1) PURE closest-pair math ------------------------------------------------
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
    if abs(d - 5.0) > 1e-9 or abs(float(pa[0]) - 1.0) > 1e-9 or abs(float(pb[1]) - 6.0) > 1e-9:
        failures.append("point+point reduction is not a passthrough")
    _pa, _pb, d = reduce_measure_picks(measure_edge_pick(EDGE_A), measure_edge_pick(EDGE_B))
    if abs(d - 51.0) > 1e-9:
        failures.append(f"edge+edge reduction must give 51.00 mm, got {d!r}")

    chain_pts = np.array(
        [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [20.0, 0.0, 0.0], [20.0, 10.0, 0.0]], dtype=float
    )
    chain_pairs = [(0, 1), (1, 2), (2, 3)]
    run = collinear_edge_run(chain_pts, chain_pairs, (0, 1))
    if run.shape[0] != 3 or not np.allclose(run[0], [0, 0, 0]) or not np.allclose(run[-1], [20, 0, 0]):
        failures.append(f"collinear run must span the straight chain and stop at the corner, got {run!r}")
    run_mid = collinear_edge_run(chain_pts, chain_pairs, (1, 2))
    if run_mid.shape[0] != 3 or not np.allclose(run_mid[0], [0, 0, 0]):
        failures.append("collinear run seeded mid-chain must extend backwards to the chain start")

    # --- 2) INTEGRATION: real record pipeline on a display-free fake ----------------
    fake = _Fake()
    fake._on_measure_edge_pick({"polyline": EDGE_A, "hit_key": "led-body", "label": "led"})
    if fake._measure_pending_edge is None or fake._measure_segments:
        failures.append("first Alt edge pick must ARM the pending edge, not record")
    if fake.shown_pending is None or not fake._measure_pick_mode:
        failures.append("arming the first edge must highlight it and keep measure mode on")
    fake._on_measure_edge_pick({"polyline": EDGE_B, "hit_key": "led-body", "label": "led"})
    if len(fake._measure_segments) != 1:
        failures.append("second Alt edge pick must complete exactly one segment")
    elif abs(_segment_length(fake) - 51.0) > 1e-9:
        failures.append(f"edge+edge segment must span 51.00 mm, got {_segment_length(fake)!r}")
    if fake._measure_pending_edge is not None or fake._measure_pick_mode:
        failures.append("completing the pair must clear the pending edge and leave measure mode")

    fake2 = _Fake()
    fake2._record_measure_point(np.array([0.0, 0.0, 40.5]), None)
    fake2._on_measure_edge_pick({"polyline": EDGE_B, "hit_key": "led-body", "label": "led"})
    if len(fake2._measure_segments) != 1 or abs(_segment_length(fake2) - 31.06) > 1e-9:
        failures.append("point-first + edge-second must project onto the edge (31.06 mm)")

    fake3 = _Fake()
    fake3._record_measure_point(np.array([1.0, 2.0, 3.0]), None)
    fake3._record_measure_point(np.array([4.0, 6.0, 3.0]), None)
    if len(fake3._measure_segments) != 1 or abs(_segment_length(fake3) - 5.0) > 1e-9:
        failures.append("plain two-point flow regressed")
    if fake3._measure_pending_edge is not None:
        failures.append("plain two-point flow must never touch the pending edge")

    # bugs/0367: a degenerate SECOND edge must NEVER strand the armed edge -- the
    # pending edge is cleared before the reduce, so the user can always continue.
    fake4 = _Fake()
    fake4._on_measure_edge_pick({"polyline": EDGE_A, "hit_key": "led", "label": "led"})
    if fake4._measure_pending_edge is None:
        failures.append("first edge must arm before the strand-proof test")
    fake4._on_measure_edge_pick(
        {"polyline": np.array([[np.nan, 0.0, 0.0], [np.nan, 1.0, 0.0]]), "hit_key": "led", "label": "led"}
    )
    if fake4._measure_pending_edge is not None:
        failures.append("a degenerate second edge must not leave the armed edge stranded (bugs/0367)")

    # --- 3) WIRING: source needles ---------------------------------------------------
    press_src = inspect.getsource(Kraken3DInspector._on_left_button_press)
    for needle in (
        "_edge_pick_alt_active",
        "_measure_resolve_edge",
        "_on_measure_edge_pick",
        "_measure_pending_edge",
        "_measure_resolve_snap",  # the legacy point path must survive verbatim
        "closest_point_on_polyline",  # armed-edge reduction against a point click
        "_measure_entity_mode",  # bugs/0358: the dedicated E/E button forces edge picks
        "_measure_resolve_snap",  # bugs/0367: point fallback when no edge is under the cursor
    ):
        if needle not in press_src:
            failures.append(f"_on_left_button_press lost its {needle} wiring")
    # bugs/0367: the second click must always be able to complete (edge->point), never strand.
    if press_src.count("_record_measure_point") < 1 or "closest_point_on_polyline" not in press_src:
        failures.append("the E/E click handler lost its edge->point completion fallback (bugs/0367)")
    pick_src = inspect.getsource(Kraken3DInspector._on_measure_edge_pick)
    before_reduce = pick_src.split("closest_points_between_polylines(pending")[0]
    if "closest_points_between_polylines(pending" not in pick_src or "_clear_measure_pending_edge()" not in before_reduce:
        failures.append("the pending edge must be cleared BEFORE the reduce (strand-proof, bugs/0367)")
    entity_src = inspect.getsource(Kraken3DInspector.start_measure_entity_pick)
    if "start_measure_pick" not in entity_src or "_measure_entity_mode" not in entity_src:
        failures.append("start_measure_entity_pick must arm entity mode over the plain flow")

    resolve_src = inspect.getsource(Kraken3DInspector._measure_resolve_edge)
    for needle in (
        "_measure_recognised_component",
        "_step_component_edge_outline",
        "nearest_display_edge",
        "collinear_edge_run",
        "depth_reference",
        "_actor_row_map",  # bugs/0359: promoted (row-actor) bodies resolve too
        "_promoted_body_label_and_axis",
    ):
        if needle not in resolve_src:
            failures.append(f"_measure_resolve_edge lost its {needle} wiring")

    hover_entity_src = inspect.getsource(Kraken3DInspector._update_measure_hover_highlight)
    for needle in ("_measure_entity_mode", "_measure_resolve_edge", "_clear_measure_snap_marker"):
        if needle not in hover_entity_src:
            failures.append(f"the entity-mode hover lost its {needle} wiring (bugs/0359)")

    for owner, method in (
        ("start_measure_pick", Kraken3DInspector.start_measure_pick),
        ("clear_measurements", Kraken3DInspector.clear_measurements),
        ("_record_measure_point", Kraken3DInspector._record_measure_point),
    ):
        if "_clear_measure_pending_edge" not in inspect.getsource(method):
            failures.append(f"{owner} does not clear the pending edge")

    hover_src = inspect.getsource(Kraken3DInspector._update_measure_hover_highlight)
    if "_measure_pending_edge" not in hover_src:
        failures.append("the measure hover does not surface the armed-edge state")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Measure edge-to-edge pick validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Measure edge-to-edge pick validation passed: Alt+click picks a drawn edge "
        "entity, pairs reduce via clamped closest-pair math (a 51.00 mm opening "
        "measures 51.00), point+edge projects, the plain 2-point flow is untouched, "
        "and the arm/clear lifecycle is wired through start/clear/record/hover."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
