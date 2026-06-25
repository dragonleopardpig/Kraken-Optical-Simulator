#!/usr/bin/env python3
"""Display-free guard for bugs/0149: re-anchored dimension endpoints are now
INDEPENDENT per-endpoint anchors that TRACK the feature they were pinned to.

bugs/0053 lets a thickness/distance dimension arrow be Ctrl-click re-anchored: the
end nearer the cursor follows the mouse onto a picked surface/edge and a plain
click commits a MEASUREMENT-ONLY override (the optical model is untouched).

bugs/0147 stored a SINGLE spec per row -- the moved end (``ref_z``) plus the other
end frozen at ``fixed_z`` -- so both ends were absolute z. Two problems surfaced:

  * "I changed the FOV, the last re-anchored arrow stay where it was, wrong
    position now." -- a frozen-z anchor cannot follow a surface that moved when the
    FOV/layout changed (the blue model dims recompute and follow; the re-anchored
    one went stale).
  * "only the right arrow can be reanchored, how about the left? Can make both
    arrow independent anchor?" -- a single spec means re-anchoring one end
    overwrites the other.

bugs/0149 reworks the override to keep ONE independent anchor PER ENDPOINT
(``override["start"]`` / ``override["end"]``). A ``kind=="surface"`` anchor
re-derives its live axial z from ``editor._surface_reference_world_point`` every
redraw (so it FOLLOWS the model on an FOV change); an empty-space / unresolved pick
stores a ``kind=="absolute"`` anchor frozen at the picked z (the pre-0149
behaviour, kept as the fallback). An endpoint with no anchor keeps its live
``p0``/``p1`` z. The legacy single-spec form still draws frozen (back-compat).

No X server needed. ``run_checks()`` covers:

  1. A per-endpoint ``surface`` anchor FOLLOWS the live surface (the FOV-change bug):
     move the surface and the drawn endpoint moves with it.
  2. BOTH ends can carry independent ``surface`` anchors and both track.
  3. An ``absolute`` anchor stays frozen when the model moves (empty-space fallback).
  4. A ``surface`` anchor whose live resolve FAILS (or editor is None) falls back to
     ``abs_z``; an endpoint with no anchor stays on the live p0/p1.
  5. ``apply_dimension_anchor_override(..., feature_ref={"row": r})`` builds a
     ``surface`` anchor, leaves ``rows[i].thickness`` untouched, and re-anchoring one
     end does NOT discard the other end's anchor (independent slots).
  6. A pre-0149 legacy ``fixed_z`` is MIGRATED into an absolute anchor for the other
     end when this end is re-anchored (so the other end is not lost on transition).
  7. The per-endpoint anchors round-trip through settings save/load.
  8. The legacy single-spec form still draws frozen (back-compat, no regression).
  9. Source markers: ``reanchored_endpoints`` consults ``start``/``end`` +
     ``_resolve_endpoint_anchor_z``; the resolver consults
     ``_surface_reference_world_point``; ``apply_dimension_anchor_override`` accepts
     ``feature_ref``; the pick path captures/forwards ``snap_feature``.

Penta phase 138 (baseline -> 138).
"""
from __future__ import annotations

import inspect
import types

import numpy as np


class _FakeEditor:
    """Stand-in editor whose live surface station z is mutable, so a check can
    simulate the FOV/layout move that shifts an optical surface."""

    def __init__(self, live_z: dict[int, float], *, fail: bool = False) -> None:
        self._live_z = live_z
        self._fail = fail

    def _surface_reference_world_point(self, row_index: int, *, face_id: str = "") -> np.ndarray:
        if self._fail:
            raise RuntimeError("simulated resolve failure")
        return np.array([0.0, 0.0, float(self._live_z[int(row_index)])], dtype=float)


def _service(editor):
    from KrakenOS.UI.services.open3d_thickness_dimensions import (
        Open3DThicknessDimensionService,
    )

    return Open3DThicknessDimensionService(
        types.SimpleNamespace(editor=editor), pv_module=None, billboard_text_actor_cls=None
    )


def _build_editor():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow

    app = KrakenLayoutEditor(headless=True)
    app.rows = [
        SurfaceRow(label="0", surface="Object", element="", name="Object",
                   thickness=275.0, diameter=25.0, glass="AIR"),
        SurfaceRow(label="1", surface="Standard", element="L1", name="L1 front",
                   thickness=8.0, diameter=25.0, glass="N-BK7"),
        SurfaceRow(label="2", surface="Standard", element="", name="L1 back",
                   thickness=24.405, diameter=25.0, glass="AIR"),
        SurfaceRow(label="3", surface="Image", element="", name="Image",
                   thickness=0.0, diameter=25.0, glass="AIR"),
    ]
    try:
        app._sync_table()
    except Exception:
        pass
    return app


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    def record(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and bool(passed)
        notes.append(f"{name} | {'PASS' if passed else 'FAIL'}" + (f" | {detail}" if detail else ""))

    p0 = np.array([0.0, 0.0, 8.0])
    p1 = np.array([0.0, 0.0, 24.405])

    # --- 1) a surface anchor FOLLOWS the live surface (the FOV-change bug) -------
    live = {0: 0.0, 1: 8.0, 2: 24.405}
    svc = _service(_FakeEditor(live))
    ov_end_surface = {"end": {"kind": "surface", "row": 2, "abs_z": 24.405, "label": "z=24.4"}}
    q0, q1, measured = svc.reanchored_endpoints(p0, p1, ov_end_surface)
    at_pick = abs(q1[2] - 24.405) < 1e-9
    live[2] = 40.0  # FOV/layout change moves surface 2 downstream
    q0b, q1b, measured_b = svc.reanchored_endpoints(p0, p1, ov_end_surface)
    record(
        "surface anchor tracks the model after an FOV move (not stale)",
        at_pick and abs(q1b[2] - 40.0) < 1e-9 and abs(measured_b - 32.0) < 1e-9,
        f"pick q1z={q1[2]:.6g} -> moved q1z={q1b[2]:.6g} (frozen 24.405 would be the BUG)",
    )

    # --- 2) BOTH ends carry independent surface anchors, both track -------------
    live2 = {0: 0.0, 1: 8.0, 2: 24.405}
    svc2 = _service(_FakeEditor(live2))
    ov_both = {
        "start": {"kind": "surface", "row": 1, "abs_z": 8.0, "label": "z=8"},
        "end": {"kind": "surface", "row": 2, "abs_z": 24.405, "label": "z=24.4"},
    }
    live2[1] = 12.0
    live2[2] = 50.0
    qb0, qb1, mb = svc2.reanchored_endpoints(p0, p1, ov_both)
    record(
        "both ends are independent surface anchors and both follow the model",
        abs(qb0[2] - 12.0) < 1e-9 and abs(qb1[2] - 50.0) < 1e-9 and abs(mb - 38.0) < 1e-9,
        f"q0z={qb0[2]:.6g} q1z={qb1[2]:.6g} measured={mb:.6g}",
    )

    # --- 3) an absolute anchor stays frozen when the model moves ---------------
    live3 = {0: 0.0, 1: 8.0, 2: 24.405}
    svc3 = _service(_FakeEditor(live3))
    ov_abs = {"end": {"kind": "absolute", "abs_z": 99.0, "label": "z=99"}}
    live3[2] = 500.0  # surface moved, but the empty-space anchor must not care
    qa0, qa1, _ = svc3.reanchored_endpoints(p0, p1, ov_abs)
    record(
        "absolute (empty-space) anchor stays frozen + unanchored start stays live",
        abs(qa1[2] - 99.0) < 1e-9 and abs(qa0[2] - 8.0) < 1e-9,
        f"q0z={qa0[2]:.6g} (live p0=8) q1z={qa1[2]:.6g} (frozen 99)",
    )

    # --- 4) failed resolve / editor=None / no-anchor fallbacks -----------------
    svc_fail = _service(_FakeEditor({2: 24.405}, fail=True))
    qf0, qf1, _ = svc_fail.reanchored_endpoints(p0, p1, ov_end_surface)
    svc_none = _service(None)
    qn0, qn1, _ = svc_none.reanchored_endpoints(p0, p1, ov_end_surface)
    record(
        "surface resolve failure / editor=None -> abs_z fallback (no crash)",
        abs(qf1[2] - 24.405) < 1e-9 and abs(qn1[2] - 24.405) < 1e-9,
        f"fail q1z={qf1[2]:.6g} none q1z={qn1[2]:.6g} (abs_z=24.405)",
    )

    # --- 5) apply_dimension_anchor_override builds surface anchors + independent
    try:
        app = _build_editor()
        before = float(app.rows[2].thickness)
        app.apply_dimension_anchor_override(2, "end", np.array([0.0, 0.0, 24.405]), feature_ref={"row": 2})
        app.apply_dimension_anchor_override(2, "start", np.array([0.0, 0.0, 8.0]), feature_ref={"row": 1})
        ov = app._dimension_anchor_override_for_row(2)
        end_anchor = ov.get("end") if isinstance(ov, dict) else None
        start_anchor = ov.get("start") if isinstance(ov, dict) else None
        independent = (
            isinstance(end_anchor, dict) and end_anchor.get("kind") == "surface" and int(end_anchor.get("row")) == 2
            and isinstance(start_anchor, dict) and start_anchor.get("kind") == "surface" and int(start_anchor.get("row")) == 1
        )
        record(
            "re-anchoring start keeps the end anchor (independent per-endpoint slots)",
            independent and abs(float(app.rows[2].thickness) - before) < 1e-9,
            f"start={start_anchor} end={end_anchor} thickness {before}->{app.rows[2].thickness}",
        )
    except Exception as exc:  # pragma: no cover - environment guard
        record("re-anchoring start keeps the end anchor", False, f"raised {exc!r}")

    # --- 6) a pre-0149 legacy fixed_z is migrated into an absolute anchor -------
    try:
        app2 = _build_editor()
        app2._dimension_anchor_overrides = {2: {"endpoint": "end", "ref_z": 50.0, "fixed_z": 10.0}}
        app2.apply_dimension_anchor_override(2, "start", np.array([0.0, 0.0, 3.0]), feature_ref={"row": 1})
        ov2 = app2._dimension_anchor_override_for_row(2)
        migrated = ov2.get("end") if isinstance(ov2, dict) else None
        start2 = ov2.get("start") if isinstance(ov2, dict) else None
        record(
            "legacy fixed_z migrates to an absolute end anchor (other end not lost)",
            isinstance(migrated, dict) and migrated.get("kind") == "absolute"
            and abs(float(migrated.get("abs_z")) - 10.0) < 1e-9
            and isinstance(start2, dict) and start2.get("kind") == "surface",
            f"migrated end={migrated} start={start2}",
        )
    except Exception as exc:  # pragma: no cover
        record("legacy fixed_z migrates to an absolute end anchor", False, f"raised {exc!r}")

    # --- 7) per-endpoint anchors round-trip through settings save/load ----------
    try:
        app3 = _build_editor()
        app3.apply_dimension_anchor_override(2, "end", np.array([0.0, 0.0, 24.405]), feature_ref={"row": 2})
        app3.apply_dimension_anchor_override(2, "start", np.array([0.0, 0.0, 8.0]), feature_ref={"row": 1})
        settings = app3._collect_layout_settings()
        app3._dimension_anchor_overrides = {}
        app3._apply_layout_settings(settings)
        ov3 = app3._dimension_anchor_override_for_row(2)
        e3 = ov3.get("end") if isinstance(ov3, dict) else None
        s3 = ov3.get("start") if isinstance(ov3, dict) else None
        record(
            "per-endpoint surface anchors round-trip through settings",
            isinstance(e3, dict) and e3.get("kind") == "surface" and int(e3.get("row")) == 2
            and isinstance(s3, dict) and s3.get("kind") == "surface" and int(s3.get("row")) == 1,
            f"start={s3} end={e3}",
        )
    except Exception as exc:  # pragma: no cover
        record("per-endpoint surface anchors round-trip through settings", False, f"raised {exc!r}")

    # --- 8) legacy single-spec form still draws frozen (back-compat) ------------
    svc_legacy = _service(_FakeEditor({2: 24.405}))
    ql0, ql1, qlm = svc_legacy.reanchored_endpoints(p0, p1, {"endpoint": "end", "ref_z": 42.0, "fixed_z": 5.0})
    record(
        "legacy single-spec form is unchanged (frozen ref_z/fixed_z)",
        abs(ql1[2] - 42.0) < 1e-9 and abs(ql0[2] - 5.0) < 1e-9 and abs(qlm - 37.0) < 1e-9,
        f"q0z={ql0[2]:.6g} q1z={ql1[2]:.6g} measured={qlm:.6g}",
    )

    # --- 9) source markers ------------------------------------------------------
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    re_src = inspect.getsource(Open3DThicknessDimensionService.reanchored_endpoints)
    record(
        "reanchored_endpoints consults per-endpoint start/end + _resolve_endpoint_anchor_z",
        '"start"' in re_src and '"end"' in re_src and "_resolve_endpoint_anchor_z" in re_src,
    )
    resolver_src = inspect.getsource(Open3DThicknessDimensionService._resolve_endpoint_anchor_z)
    record(
        "_resolve_endpoint_anchor_z re-derives via _surface_reference_world_point",
        "_surface_reference_world_point" in resolver_src,
    )
    apply_src = inspect.getsource(ScenePlacementMixin.apply_dimension_anchor_override)
    record(
        "apply_dimension_anchor_override accepts feature_ref + builds per-endpoint anchors",
        "feature_ref" in apply_src and "_dimension_endpoint_anchor_from_feature" in apply_src,
    )
    motion_src = inspect.getsource(Kraken3DInspector._apply_dimension_anchor_pick_motion)
    commit_src = inspect.getsource(Kraken3DInspector._commit_dimension_anchor_pick)
    record(
        "pick path captures snap_feature and forwards it as feature_ref",
        "snap_feature" in motion_src and "feature_ref" in commit_src,
    )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(note)
    print(
        "[PASS] re-anchored dimension endpoints track their feature (independent per-endpoint anchors)"
        if ok
        else "[FAIL] re-anchored dimension feature-tracking regressed"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
