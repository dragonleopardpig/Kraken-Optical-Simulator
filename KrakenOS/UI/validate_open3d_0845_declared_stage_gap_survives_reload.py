"""Display-free guard: a gap the SCENE declares signed survives a reload (bugs/0845).

Found while proving bugs/0844 on the user's own saved scene: the fix worked on a reconstructed
path and NOT on ``attachment/om05a_folded_refusal.py``. The file holds
``row 23 'sensor standoff' thickness = -78.334`` -- the camera stage (bugs/0759) had travelled
87.154 mm toward the lens and the standoff takes the same delta -- and the load-time healer
(bugs/0559) zeroed it, returning the amount through every follower's ``desp_z``.

That keeps the WORLD and breaks the FIRST ORDER, which sums thicknesses and never reads
``desp_z``: the image track read 235.26 mm after a reload against 156.92 mm live and in the
world. Every later solve booked the image side 78.33 mm wrong; the next one parked the Filter
3.9 mm inside the lens barrel. The scene itself declares that row's travel as
-171.65 .. +30.42 mm, so the value is a POSITION, not a corruption.

  C  CONTROL -- healed the old way, the world is kept and the first-order track jumps 78.334
  K  with the scene's declaration the row, and every follower's desp_z, are byte-identical
  B  below the declared floor it is corruption again and is healed
  O  another negative gap in the same scene is still healed (0559 keeps its job)
  D  no stage / disabled / non-negative floor / garbage -> nothing is declared
  R  the user's saved scene (rebuilt from om05a_folded.py): the standoff survives and
     first order equals the world track
  W  both loaders hand the declaration to the healer (the bugs/0563 two-loader trap)
"""
from __future__ import annotations

import inspect
from pathlib import Path

STANDOFF_MM = -78.3343391747
STAGE = {"enabled": True, "row": 5, "min_mm": -171.65, "max_mm": 30.42, "arm_row": 3}


def _rows(standoff=STANDOFF_MM, lens_gap=79.6812):
    from KrakenOS.UI.surface_table_model import SurfaceRow

    def _row(name, thickness, desp_z=0.0):
        row = SurfaceRow(name=name, thickness=float(thickness), diameter=25.0, glass="AIR")
        row.desp_z = float(desp_z)
        return row

    return [
        _row("Object", 112.49),
        _row("Rear Optical Vertex Datum", lens_gap),
        _row("Filter 48-926", 1.0),
        _row("RA mirror 2", 36.31, desp_z=-393.63),
        _row("LED panel B", 0.0, desp_z=-459.89),
        _row("sensor standoff", standoff),
        _row("Image / Sensor", 0.0),
    ]


def _track(rows) -> float:
    """What the first order believes the image track is: a thickness sum, desp_z unread."""
    return sum(float(r.thickness) for r in rows[1:6])


def _world_z(rows) -> list:
    out, z = [], 0.0
    for row in rows:
        out.append(round(z + float(row.desp_z), 9))
        z += float(row.thickness)
    return out


def _print(rows) -> tuple:
    return tuple((repr(r.thickness), repr(r.desp_z)) for r in rows)


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.services.layout_import_export import LayoutImportExportMixin as M

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    heal, declared = M._heal_negative_gaps_on_load, M._declared_signed_gap_rows
    info = {"settings": {"camera_focus_stage": dict(STAGE)}}

    # ---- C: CONTROL -- the old heal keeps the world and moves the first order -------------------
    rows = _rows()
    track_before, world_before = _track(rows), _world_z(rows)
    healed = heal(rows)
    ok(len(healed) == 1 and rows[5].thickness == 0.0 and _world_z(rows) == world_before
       and abs((_track(rows) - track_before) - 78.3343391747) < 1e-9,
       f"C: CONTROL -- healed without the declaration the WORLD is kept and the first-order "
       f"image track jumps {_track(rows) - track_before:+.4f} mm ({track_before:.2f} -> "
       f"{_track(rows):.2f}): the defect, reproduced")

    # ---- K: the declaration keeps it, exactly ---------------------------------------------------
    rows = _rows()
    before = _print(rows)
    healed = heal(rows, declared(info))
    ok(healed == [] and _print(rows) == before and declared(info) == {5: -171.65},
       f"K: with the scene's declaration {declared(info)} the standoff stays "
       f"{rows[5].thickness!r} and no follower's desp_z is touched")

    # ---- B: below the floor is corruption -------------------------------------------------------
    rows = _rows(standoff=-200.0)
    healed = heal(rows, declared(info))
    ok(len(healed) == 1 and rows[5].thickness == 0.0,
       "B: -200 mm is below the declared -171.65 floor -- not a position the stage has, so it "
       "is healed as corruption")

    # ---- O: another negative gap is still 0559's job --------------------------------------------
    rows = _rows(lens_gap=-13.5949)
    healed = heal(rows, declared(info))
    ok([h["row_index"] for h in healed] == [1] and rows[1].thickness == 0.0
       and rows[5].thickness == STANDOFF_MM,
       "O: an undeclared negative gap in the same scene is still healed, and the declared "
       "standoff beside it is still kept")

    # ---- D: nothing is declared unless the scene says so ----------------------------------------
    nothing = [
        None, {}, {"settings": None}, {"settings": {}},
        {"settings": {"camera_focus_stage": None}},
        {"settings": {"camera_focus_stage": dict(STAGE, enabled=False)}},
        {"settings": {"camera_focus_stage": dict(STAGE, min_mm=0.0)}},
        {"settings": {"camera_focus_stage": dict(STAGE, min_mm=36.31)}},
        {"settings": {"camera_focus_stage": {"enabled": True, "row": "x", "min_mm": -5}}},
        {"settings": {"camera_focus_stage": {"enabled": True, "min_mm": -5}}},
    ]
    ok(all(declared(case) == {} for case in nothing),
       "D: no stage, a disabled one, a non-negative floor or a malformed spec declares nothing "
       "-- every such scene heals exactly as before")

    # ---- R: the user's saved scene, rebuilt from the ORIGINAL file ------------------------------
    # The user saved attachment/om05a_folded_refusal.py and will delete it; it differs from the
    # shipped om05a_folded.py in exactly these five row values (and a split-field band width the
    # healer never reads), so the guard rebuilds it instead of depending on it.
    saved = {7: 35.2344243107, 12: 79.6812365146, 14: 118.264339175, 23: STANDOFF_MM}
    seat_x = -181.982660825
    path = Path("attachment/om05a_folded.py")
    if not path.exists():
        notes.append("= R: SKIP -- attachment/om05a_folded.py is not checked out here")
    else:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data

        data = _load_python_data(path)
        real = [KrakenLayoutEditor._row_from_layout_item(item) for item in data["surfaces"]]
        for index, value in saved.items():
            real[index].thickness = value
        real[15].desp_x = seat_x
        healed = heal(real, declared(data))
        track = sum(float(real[i].thickness) for i in range(12, 24))
        # the world, measured on the loaded scene: lens rear -> RA mirror 2 102.430 mm along x,
        # RA mirror 2 -> sensor 54.491 mm along y
        ok(healed == [] and float(real[23].thickness) == STANDOFF_MM
           and abs(track - (102.430 + 54.491)) < 0.01,
           f"R: on the user's saved scene (om05a_folded + its five saved values) the standoff "
           f"survives ({real[23].thickness!r}) and the first-order image track is {track:.3f} mm "
           f"-- the world's 156.921, not the 235.26 a healed reload believed")

    # ---- W: both loaders pass it on (executable lines only, not this fix's own comments) --------
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as W

    def _passes(function) -> bool:
        code = [ln.split("#", 1)[0] for ln in inspect.getsource(function).splitlines()]
        return any("_declared_signed_gap_rows(info)" in ln for ln in code)

    ok(_passes(M.open_layout) and _passes(W.load_layout_by_name),
       "W: open_layout AND load_layout_by_name hand the scene's declaration to the healer")

    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
