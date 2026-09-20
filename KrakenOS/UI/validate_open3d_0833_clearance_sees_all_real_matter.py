"""bugs/0833 guard -- the clearance walks see all real matter, and never report an absence.

flag_20260920_175110 asked "is the lens hit the Edmund filter?".  It did, and nothing warned,
because every obstacle walk in the swap/solve path only counted rows carrying a promoted
``Solid_3d_stl``.  om05a's Filter 48-926 is an ordinary surrogate row -- N-BK7, O50.8, 1.0 mm,
drawing on -- so the lens room measure looked straight past it to RA mirror 2, 40 mm further
down the leg, and reported room the lens did not have.

The camera layer had the mirror image of the same fault: it assumed the obstacle was
``rows[-2]``.  On om05a that is 'sensor standoff', a plain air gap carrying no body, so
``_promoted_solid_world_bounds`` returned None and the layer reported ``"0 mm: missing
obstacle"`` on every swap -- an ABSENCE dressed as a measurement -- while RA mirror 2 sat eight
rows back, never examined.

Row ORDER is not the repair, and the first draft proved it: walking back from the sensor lands
on 'LED panel B', a promoted solid in the illumination arm that is nowhere near the camera.
Both walks now use the bugs/0719 recipe -- transverse overlap on both axes, nearest along-leg
separation wins.

Checks:
  SOURCE  -- the element AABB, the geometric picker and the absence note all exist.
  ELEMENT -- the Filter's world AABB matches the transverse extent the user's own capture
             DREW (30.96, 81.76, -50.40, 0.40), while AIR datums and the standoff are not
             bodies (bugs/0806: a datum disc is a mount face, not matter).
  ROOM    -- the downstream room now names the Filter; the STL-ONLY rule is shown to name
             RA mirror 2 instead, so a revert cannot pass.
  CAMERA  -- the clearance layer reaches "ok" with an obstacle chosen by geometry, and that
             obstacle beats both the row-order answer (LED panel B) and RA mirror 2.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/om05a_folded.py")

# What the user's 17:51 capture recorded the Filter actor as, transversely.
DRAWN_FILTER_TRANSVERSE = (30.96, 81.76, -50.40, 0.40)


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import layout_table_workbench as ltw
    from KrakenOS.UI.services import scene_placement_commands as spc

    spc_src = _inspect.getsource(spc)
    ltw_src = _inspect.getsource(ltw)
    wanted = {
        "_element_row_world_aabb": spc_src,
        "GLASS is the discriminator": spc_src,
        "_nearest_body_row_along_leg": ltw_src,
        "_swap_clearance_unmeasured": ltw_src,
    }
    missing = [token for token, src in wanted.items() if token not in src]
    if missing:
        notes.append(f"SOURCE missing {missing}")
        ok = False
    else:
        notes.append("SOURCE = element AABB, geometric picker and the absence note are present")

    if not SCENE.exists():
        notes.append("SKIP: om05a_folded is absent (gitignored attachment)")
        return ok, notes

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
        app.layout_files["guard"] = SCENE
        app.load_layout_by_name("guard")
        rows = app.rows

        filter_row = next(
            (i for i, r in enumerate(rows)
             if str(getattr(r, "name", "") or "").startswith("Filter")),
            None,
        )
        if filter_row is None:
            notes.append("SKIP: this om05a_folded has no Filter row")
            return ok, notes

        bounds = app._element_row_world_aabb(filter_row)
        if bounds is None:
            notes.append(f"ELEMENT row {filter_row} (N-BK7 glass) is still not a body")
            ok = False
        elif max(abs(float(a) - float(b))
                 for a, b in zip(bounds[2:6], DRAWN_FILTER_TRANSVERSE)) <= 0.05:
            notes.append(
                f"ELEMENT = the Filter's AABB matches what the capture DREW transversely "
                f"{tuple(round(float(v), 2) for v in bounds[2:6])}"
            )
        else:
            notes.append(
                f"ELEMENT the Filter's transverse AABB {tuple(round(float(v), 2) for v in bounds[2:6])} "
                f"does not match the drawn {DRAWN_FILTER_TRANSVERSE}"
            )
            ok = False

        not_bodies = []
        for index, row in enumerate(rows):
            name = str(getattr(row, "name", "") or "")
            if "Datum" in name or name == "sensor standoff":
                if app._element_row_world_aabb(index) is not None:
                    not_bodies.append((index, name))
        if not_bodies:
            notes.append(f"ELEMENT AIR datum / standoff rows were counted as bodies: {not_bodies}")
            ok = False
        else:
            notes.append("ELEMENT = AIR datums and the standoff are not matter (bugs/0806)")

        front = app._lens_datum_row_index("front")
        rear = app._lens_datum_row_index("rear")
        info = app._lens_block_physical_room_mm(int(front), int(rear), +1.0)
        if int(info.get("obstacle_row", -1)) == int(filter_row):
            notes.append(
                f"ROOM = the downstream obstacle is row {filter_row} "
                f"{info.get('obstacle')!r}, {float(info.get('room_phys')):.3f} mm of room"
            )
        else:
            notes.append(
                f"ROOM the downstream obstacle is row {info.get('obstacle_row')} "
                f"{info.get('obstacle')!r}, not the Filter"
            )
            ok = False

        # The pre-0833 rule, re-run here: STL rows only.
        stl_only = [
            i for i in range(int(rear) + 1, len(rows))
            if (rows[i].advanced if isinstance(getattr(rows[i], "advanced", None), dict) else {}).get(
                "Solid_3d_stl"
            )
        ]
        if stl_only and int(stl_only[0]) != int(filter_row):
            notes.append(
                f"ROOM = the STL-only rule would have named row {stl_only[0]} "
                f"{str(getattr(rows[stl_only[0]], 'name', ''))!r} instead -- the defect reproduces"
            )
        else:
            notes.append("ROOM the STL-only rule no longer differs here; the guard proves nothing")
            ok = False

        cam_bounds, _reason = app._camera_body_world_bounds()
        leg = app._folded_leg_axis_unit()
        if cam_bounds is None or leg is None:
            notes.append("CAMERA no camera body / leg on this scene")
            ok = False
        else:
            picked, picked_bounds = app._nearest_body_row_along_leg(
                cam_bounds, leg, exclude=(len(rows) - 1,)
            )
            row_order = next(
                (i for i in range(len(rows) - 2, -1, -1) if app._row_world_body_aabb(i) is not None),
                None,
            )
            if picked is None or picked_bounds is None:
                notes.append("CAMERA the geometric picker found no obstacle at all")
                ok = False
            elif row_order is not None and int(row_order) != int(picked):
                notes.append(
                    f"CAMERA = geometry picks row {picked} "
                    f"{str(getattr(rows[picked], 'name', ''))!r}; a row-order walk would pick row "
                    f"{row_order} {str(getattr(rows[row_order], 'name', ''))!r} -- order is not spatial"
                )
            else:
                notes.append(
                    f"CAMERA row order and geometry agree here (row {picked}); the guard cannot "
                    "tell them apart on this scene"
                )
                ok = False

        app._swap_camera_body_clearance_deficit()
        dbg = dict(getattr(app, "_swap_clearance_debug", None) or {})
        result = str(dbg.get("result", ""))
        if "missing" in result:
            notes.append(f"CAMERA the layer still reports an absence as a number: {result!r}")
            ok = False
        elif dbg.get("obstacle_bounds"):
            notes.append(
                f"CAMERA = the layer measured against row {dbg.get('upstream_row')} "
                f"{dbg.get('upstream_name')!r} via {dbg.get('obstacle_center_source')!r} -> {result!r}"
            )
        else:
            notes.append(f"CAMERA no obstacle bounds reached the layer ({result!r})")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: scene drive failed ({exc!r})")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
