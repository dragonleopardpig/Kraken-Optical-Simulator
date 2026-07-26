#!/usr/bin/env python3
"""bugs/0439 (anchor half) -- the explicit snap lands the chain at the CLICKED point.

flag_20260726_110657: "the elements snapped correctly but the shifted to the left
(crashing to the LED STEP), perhaps let the first element front edge follow the mouse
click coorditate on the optical axis." The explicit multi-select snap landed the
selection origin AT the branch point (axis record points[0]); when the axis pick
resolves through _optical_axis_info_near_display_xy the record carries picked_world --
now the landing target is that click PROJECTED onto the axis line, so the user chooses
the position along the axis with the click itself. No picked_world -> branch point
(old behavior, byte-identical fallback).

Flow mirrors the user's: freeze (delete mirror-1) -> rubber-band-equivalent selection
(chain + mirror-2 + Image) -> snap. Run: DISPLAY=:N .devenv/state/venv/bin/python
bugs/probe_0439_anchor_snap_at_click.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from KrakenOS.UI.layout_editor import KrakenLayoutEditor  # noqa: E402
from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold  # noqa: E402

SCENE = Path(__file__).resolve().parents[1] / "attachment" / "machine_vision_AZ85_RA_Mirror.py"

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok  " if ok else "FAIL") + f" {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


def world_centers(app, rows):
    z = app._row_z_positions()
    out = {}
    for i in rows:
        r = app.rows[i]
        out[i] = np.asarray(
            (float(r.desp_x), float(r.desp_y), float(z[i]) + float(r.desp_z)), dtype=float
        )
    return out


def frozen_selection(app):
    """Delete mirror-1 (0433 freeze) and return the rubber-band set front-datum..Image."""
    mirror_rows = [i for i, r in enumerate(app.rows) if _row_is_promoted_mirror_fold(r)]
    app.delete_optical_step_rows([mirror_rows[0]])
    front = app._lens_datum_row_index("front")
    image = next(
        (i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"),
        None,
    )
    return list(range(front, image + 1)), front, image


def run_snap(record):
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        rows, front, image = frozen_selection(app)
        pre = world_centers(app, rows)
        result = app.snap_rows_to_axis(rows, dict(record))
        post = world_centers(app, rows)
        return rows, front, image, pre, post, result
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def main() -> int:
    axis_points = np.asarray([(0.0, 0.0, 60.0), (100.0, 0.0, 60.0)], dtype=float)  # +X at z=60
    branch = axis_points[0]
    new_dir = np.asarray((1.0, 0.0, 0.0))

    # --- WITH picked_world: off-line click proves the projection ------------------
    picked = (60.0, 3.0, 61.0)  # projects to (60, 0, 60) on the axis line
    anchor = branch + float(np.dot(np.asarray(picked) - branch, new_dir)) * new_dir
    rows, front, image, pre, post, result = run_snap(
        {"axis_id": "axis:global:split", "axis_label": "BS reflect", "points": axis_points, "picked_world": picked}
    )
    check("snap moved the whole selection", sorted(result.get("moved_rows", [])) == sorted(rows),
          f"moved={result.get('moved_rows')}")
    check("entry member (front datum) lands AT the projected click", np.allclose(post[front], anchor, atol=1e-6),
          f"landed={np.round(post[front], 3)} anchor={np.round(anchor, 3)}")
    check("entry member is NOT at the branch point", not np.allclose(post[front], branch, atol=1e-3),
          f"branch={np.round(branch, 3)}")
    # rigidity: pairwise distances preserved (fold inside the selection included)
    pairs = [(a, b) for ai, a in enumerate(rows) for b in rows[ai + 1:]]
    dist_err = max(
        abs(float(np.linalg.norm(post[a] - post[b])) - float(np.linalg.norm(pre[a] - pre[b])))
        for a, b in pairs
    )
    check("rigid: every pairwise distance preserved", dist_err < 1e-6, f"max_err={dist_err:.2e}")
    # entry leg lies along the new axis at the anchor height
    along = [i for i in rows if i <= front + 4]
    on_axis = max(abs(float(post[i][2] - 60.0)) + abs(float(post[i][1])) for i in along)
    check("entry members sit ON the new axis line", on_axis < 1e-6, f"max_off={on_axis:.2e}")

    # --- WITHOUT picked_world: byte-identical old behavior (branch-point landing) --
    rows2, front2, image2, pre2, post2, result2 = run_snap(
        {"axis_id": "axis:global:split", "axis_label": "BS reflect", "points": axis_points}
    )
    check("fallback: entry member lands at the branch point", np.allclose(post2[front2], branch, atol=1e-6),
          f"landed={np.round(post2[front2], 3)}")
    # the two runs differ ONLY by the along-axis shift = |anchor - branch|
    shift = float(np.linalg.norm(anchor - branch))
    deltas = [float(np.linalg.norm(post[i] - post2[i])) for i in rows]
    check("picked_world run == fallback run + uniform along-axis shift",
          max(abs(d - shift) for d in deltas) < 1e-6,
          f"shift={shift:.3f} max_dev={max(abs(d - shift) for d in deltas):.2e}")

    if failures:
        print(f"RESULT: FAIL ({len(failures)} failure(s))")
        return 1
    print("RESULT: PASS -- explicit snap lands at the projected click; fallback unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
