"""Guard for bugs/0643 — the BS reflect axis is bounded to the REAL coating face.

flag_20260824_144559 ("the glued illuminator source + BS Cube + LED moved together, the
optical axis is not moving"). User's call (illuminator-only semantics): moving the
illuminator must NOT drag the object/lens/camera; instead the reflect axis must be honest.
The fold point used to be the crossing of the incoming axis with the coating's INFINITE
plane, so sliding the BS off the imaging beam left a stale-looking second axis hanging at
the old crossing where the cube no longer is. Now the fold point must land ON the coating:
the drawer skips a coating whose fold point is farther than the face's in-plane half-extent.

Checks (display-free):
  A  EXTENT — `_beam_splitter_coating_face_extent_mm`: clear_aperture wins; else sqrt(area)/2
     (38.945 mm for the real 55x78 BS cube's 6067 mm^2 coating, vs its true 39.0/38.9 halves);
     an unsized face reports 0.0 (callers then apply no bound rather than guess).
  B  ON THE GLASS — a fold point inside the extent still emits axis:global:split.
  C  OFF THE GLASS — the same coating slid laterally off the incoming beam emits NOTHING.
  D  UNSIZED — extent 0.0 keeps the pre-0643 behaviour (a record is still emitted).
  E  API — `beam_splitter_coating_world_frames` still returns plain (centroid, normal)
     2-tuples over the extent-carrying records (its long-standing callers are unchanged).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0643_reflect_axis_bounded_to_face
"""

from __future__ import annotations

import numpy as np


def _drawer_records(monkey_records):
    """Call the real _bs_reflect_axis_guide_records with a stub self + synthetic coatings."""
    from KrakenOS.UI import nonseq_output_ports as ports
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    class _Stub:
        editor = type("E", (), {"rows": []})()

        @staticmethod
        def _incoming_axis_leg_for_point(point, axis_records):
            # The imaging axis: +Z through x=0 (the scene's root leg).
            return np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])

    saved = ports.beam_splitter_coating_world_records
    try:
        ports.beam_splitter_coating_world_records = lambda rows: list(monkey_records)
        bounds = np.array([-100.0, 100.0, -100.0, 100.0, -500.0, 1200.0])
        return Kraken3DInspector._bs_reflect_axis_guide_records(_Stub(), bounds, [])
    finally:
        ports.beam_splitter_coating_world_records = saved


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.nonseq_output_ports import (
        _beam_splitter_coating_face_extent_mm,
        beam_splitter_coating_world_frames,
    )

    # ---------------------------------------------------------------- A: extent
    from_area = _beam_splitter_coating_face_extent_mm({"area_mm2": 6066.976182580578})
    from_ca = _beam_splitter_coating_face_extent_mm({"clear_aperture_mm": 50.0, "area_mm2": 6066.98})
    unsized = _beam_splitter_coating_face_extent_mm({})
    if abs(from_area - 38.9454) > 1e-3:
        ok = False
        notes.append(f"FAIL: A (bugs/0643): sqrt(area)/2 extent {from_area} != 38.9454 for the real coating")
    elif abs(from_ca - 25.0) > 1e-9:
        ok = False
        notes.append(f"FAIL: A (bugs/0643): an explicit clear_aperture must win ({from_ca} != 25.0)")
    elif unsized != 0.0:
        ok = False
        notes.append(f"FAIL: A (bugs/0643): an unsized face must report 0.0, got {unsized}")
    else:
        notes.append(f"PASS: A: extent = {from_area:.2f} mm from area, clear-aperture wins, unsized -> 0")

    # A 45 deg coating on the imaging beam (the flagged scene's geometry, mm).
    normal = np.array([-0.7071067811865475, 0.0, 0.7071067811865477])
    # the coating's in-plane axes: u along the x-z diagonal, v along y (a lateral slide walks
    # the crossing along u -- the rectangle test must catch it)
    u_axis = np.array([0.7071067811865475, 0.0, 0.7071067811865477])
    v_axis = np.array([0.0, 1.0, 0.0])
    on_beam = {"centroid": np.array([1.3, 0.0, 174.646185]), "normal": normal, "extent_mm": 38.95,
               "u_axis": u_axis, "v_axis": v_axis}
    # Slid +40 mm laterally off the beam: the infinite plane still crosses x=0 (at z=133.35),
    # but that crossing is 58.4 mm from the coating centroid -- off the glass.
    off_beam = {"centroid": np.array([41.3, 0.0, 174.646185]), "normal": normal, "extent_mm": 38.95,
                "u_axis": u_axis, "v_axis": v_axis}
    unsized_rec = {"centroid": np.array([41.3, 0.0, 174.646185]), "normal": normal, "extent_mm": 0.0,
                   "u_axis": u_axis, "v_axis": v_axis}

    # ---------------------------------------------------------------- B/C/D: the drawer
    try:
        drawn_on = _drawer_records([on_beam])
        drawn_off = _drawer_records([off_beam])
        drawn_unsized = _drawer_records([unsized_rec])
    except Exception as exc:  # noqa: BLE001
        return False, notes + [f"FAIL: B/C/D (bugs/0643): the drawer raised {exc!r}"]

    if len(drawn_on) != 1 or "split" not in str(drawn_on[0].get("axis_id", "")):
        ok = False
        notes.append(f"FAIL: B (bugs/0643): a coating ON the beam did not emit the reflect axis ({drawn_on})")
    elif drawn_off:
        anchor = np.asarray(drawn_off[0].get("points"))[0]
        ok = False
        notes.append(
            f"FAIL: C (bugs/0643): a coating slid OFF the beam still emitted a reflect axis at "
            f"{np.round(anchor, 2).tolist()} -- the stale hanging axis the user reported"
        )
    elif len(drawn_unsized) != 1:
        ok = False
        notes.append("FAIL: D (bugs/0643): an unsized coating must keep the pre-0643 behaviour (still drawn)")
    else:
        anchor = np.asarray(drawn_on[0].get("points"))[0]
        notes.append(
            f"PASS: B/C/D: on-glass emits (anchor {np.round(anchor, 2).tolist()}), off-glass emits "
            "nothing, unsized unchanged"
        )

    # ---------------------------------------------------------------- E: 2-tuple API kept
    frames = beam_splitter_coating_world_frames([])
    if frames != []:
        ok = False
        notes.append("FAIL: E (bugs/0643): the frames wrapper changed its empty-rows contract")
    else:
        import inspect

        src = inspect.getsource(beam_splitter_coating_world_frames)
        if "beam_splitter_coating_world_records" not in src:
            ok = False
            notes.append("FAIL: E (bugs/0643): frames must wrap the extent-carrying records")
        else:
            notes.append("PASS: E: the (centroid, normal) API still wraps the extent-carrying records")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Reflect-axis-bounded-to-face validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
