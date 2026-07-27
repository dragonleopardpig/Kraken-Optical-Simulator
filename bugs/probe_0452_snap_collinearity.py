"""bugs/0452 -- the snap refuses a non-collinear selection instead of scattering it.

flag_20260726_191537 "rubberband snap": after the 0449 undo-tear the front datum sat
at z=53 while the rest of the lens block sat at z=115.5. The first->last fit ran
corner-to-corner through the bend (48.7 deg), the single rigid R rotated the whole
selection by that skew, and the preserved internal bend read as "scattered" -- rows
3-5 landed on a -49 deg string with their exact 9.9 mm spacing while the two fit
endpoints landed exactly on the axis (replayed from recording_20260726_191552).
Rigid-from-garbage is still garbage: snap_rows_to_axis now measures each reference
member's perpendicular deviation from the fit line and refuses loudly, moving
nothing, when it exceeds max(2.0 mm, 2% of span).

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0452_snap_collinearity.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok " if ok else "XX "), label, (" " + detail if detail else ""))
    if not ok:
        FAILURES.append(label)


def _world_centers(app):
    z = app._row_z_positions()
    return {
        i: np.array(
            [float(r.desp_x), float(r.desp_y), float(z[i]) + float(r.desp_z)]
        )
        for i, r in enumerate(app.rows)
    }


def _frozen_scene(app):
    """The 0433/0446 recipe: delete mirror-1 (freeze bakes the chain collinear at z=53)."""
    app.layout_files["az85"] = SCENE
    app.load_layout_by_name("az85")
    mirror1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
    app.delete_optical_step_rows([mirror1])


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    # ---- 1: torn-state replay (the recording's pre-snap geometry) -> REFUSED ----
    app = KrakenLayoutEditor()
    try:
        _frozen_scene(app)
        front = app._lens_datum_row_index("front")
        rear = app._lens_datum_row_index("rear")
        image_row = next(
            i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"
        )
        mirror2 = next(
            i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", ""))
        )
        # Replicate the tear: everything BETWEEN the datE... front datum stays on the
        # old leg (z=53), the rest of the block + mirror shifted +62.5 (the undo-torn
        # z=115.5 state from the recording).
        torn = [i for i in range(front + 1, mirror2 + 1)]
        for i in torn:
            app.rows[i].desp_z = float(app.rows[i].desp_z) + 62.5
        before = _world_centers(app)
        dev_row = torn[0]
        # Document the forensic magnitude: the fit line (front datum -> rear datum)
        # misses the interior members by ~28 mm on this geometry.
        a = before[front]
        b = before[rear]
        d = b - a
        d = d / np.linalg.norm(d)
        rel = before[dev_row] - a
        perp = float(np.linalg.norm(rel - float(np.dot(rel, d)) * d))
        check("forensic: torn interior member sits far off the fit line", perp > 20.0, f"perp={perp:.1f}mm")

        selection = [front] + torn + [image_row]
        tilts_before = [
            (float(r.tilt_x), float(r.tilt_y), float(r.tilt_z)) for r in app.rows
        ]
        res = app.snap_rows_to_axis(
            selection,
            {
                "axis_id": "axis:global:split",
                "axis_label": "BS reflect",
                "points": np.array([(0.0, 0.0, 54.2), (268.0, 0.0, 54.2)]),
                "picked_world": np.array([160.0, 0.0, 54.2]),
            },
        )
        after = _world_centers(app)
        tilts_after = [
            (float(r.tilt_x), float(r.tilt_y), float(r.tilt_z)) for r in app.rows
        ]
        check(
            "torn selection REFUSED (error=non_collinear_selection, no rows moved)",
            res.get("error") == "non_collinear_selection" and res.get("moved_rows") == [],
            str({k: res[k] for k in ("error", "offenders") if k in res}),
        )
        moved = [i for i in before if not np.allclose(before[i], after[i], atol=1e-12)]
        check("torn selection: every world center byte-identical", moved == [], str(moved))
        check("torn selection: every tilt byte-identical", tilts_before == tilts_after)
        check(
            "refusal names the off-axis rows in the status",
            "do not lie on one axis" in app.status_var.get(),
            app.status_var.get()[:80],
        )
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    # ---- 2: sane frozen chain still snaps rigidly ----
    app = KrakenLayoutEditor()
    try:
        _frozen_scene(app)
        front = app._lens_datum_row_index("front")
        image_row = next(
            i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"
        )
        mirror2 = next(
            i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", ""))
        )
        selection = list(range(front, image_row + 1))
        before = _world_centers(app)
        res = app.snap_rows_to_axis(
            selection,
            {
                "axis_id": "axis:global:split",
                "axis_label": "BS reflect",
                "points": np.array([(0.0, 0.0, 54.2), (268.0, 0.0, 54.2)]),
                "picked_world": np.array([90.0, 0.0, 54.2]),
            },
        )
        after = _world_centers(app)
        check("sane chain: snap accepted", sorted(res.get("moved_rows") or []) == selection, str(res.get("moved_rows")))
        entry = [i for i in selection if i < mirror2]
        on_axis = [abs(float(after[i][2]) - 54.2) < 1e-6 and abs(float(after[i][1])) < 1e-9 for i in entry]
        check("sane chain: entry members land on the picked axis", all(on_axis), str([after[i].round(2).tolist() for i in entry]))
        # rigidity: pairwise distances preserved
        import itertools

        errs = [
            abs(
                float(np.linalg.norm(before[i] - before[j]))
                - float(np.linalg.norm(after[i] - after[j]))
            )
            for i, j in itertools.combinations(selection, 2)
        ]
        # the re-pack may close non-selected gaps; on this contiguous selection there are none
        check("sane chain: rigid (pairwise distances preserved)", max(errs) < 1e-6, f"max={max(errs):.2e}")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    # ---- 3: single-row translate-only unaffected + 4: tolerance boundary ----
    app = KrakenLayoutEditor()
    try:
        _frozen_scene(app)
        front = app._lens_datum_row_index("front")
        image_row = next(
            i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"
        )
        mirror2 = next(
            i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", ""))
        )
        res = app.snap_rows_to_axis(
            [image_row],
            {
                "axis_id": "axis:global:frozen-fold:7",
                "axis_label": "Optical Axis (fold)",
                "points": np.array([(235.9, 0.0, 53.0), (235.9, 0.0, -200.0)]),
                "picked_world": np.array([235.9, 0.0, -30.0]),
            },
        )
        check("single row: translate-only path untouched", bool(res.get("translate_only")), str(res))

        # 4a: a 1.5 mm intentional decenter passes (under max(2.0, 2% span)).
        selection = [i for i in range(front, mirror2)]
        app.rows[selection[1]].desp_y = float(app.rows[selection[1]].desp_y) + 1.5
        res = app.snap_rows_to_axis(
            selection,
            {
                "axis_id": "axis:global:split",
                "points": np.array([(0.0, 0.0, 54.2), (268.0, 0.0, 54.2)]),
            },
        )
        check("1.5 mm decenter: allowed (under tolerance)", res.get("error") != "non_collinear_selection", str(res.get("error")))
        # 4b: a 3.0 mm bend on the same short span is refused.
        app.rows[selection[2]].desp_y = float(app.rows[selection[2]].desp_y) + 3.0
        res = app.snap_rows_to_axis(
            selection,
            {
                "axis_id": "axis:global:split",
                "points": np.array([(0.0, 0.0, 54.2), (268.0, 0.0, 54.2)]),
            },
        )
        check("3.0 mm bend: refused", res.get("error") == "non_collinear_selection", str(res.get("error")))
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- non-collinear selections refused; sane snaps rigid; translate-only intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
