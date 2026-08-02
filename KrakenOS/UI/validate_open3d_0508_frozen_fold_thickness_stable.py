"""bugs/0508 A -- a frozen fold solid's thickness must survive the reached-walk.

Root cause: ``folded_beam_reached_mirror_fold_indices`` launched from the NOMINAL
origin and decided reachability geometrically for EVERY fold solid. Sliding the
BS (alone, or via the 0505 LED station drag) moved the walk's fold point off the
baked RA mirror, the mirror lost its "reached" verdict, and
``neutralize_offbeam_inert_solids`` zeroed its 44.12 mm row thickness -- but the
0433-frozen chain's stations were AUTHORED with that thickness, so the built
image landed exactly one mirror->image gap low ("rays go pass the sensor",
flag_20260802_131958 / _140514).

Fix under test (both in offbeam_optical_solid.py):
  1. reached-by-authorship -- a fold solid on a breadcrumbed row
     (``ScenePlacement.stay_put_freeze`` / ``last_axis_to_axis_move``) seeds the
     reached set; the walk stays the arbiter for free-placed solids only;
  2. the walk launches from the OBJECT row's lateral station
     (``axis_root_origin`` semantics), so a station drag keeps its verdicts.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0508_frozen_fold_thickness_stable
"""
from __future__ import annotations

import inspect
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
SLIDE = -23.4


def _thickness_map(specs) -> dict[int, float]:
    return {
        i: round(float(s.get("thickness", 0.0) or 0.0), 6)
        for i, s in enumerate(specs)
        if isinstance(s, dict)
    }


def _strip_breadcrumbs(specs) -> list:
    import copy

    stripped = copy.deepcopy(specs)
    for spec in stripped:
        if not isinstance(spec, dict):
            continue
        advanced = spec.get("advanced")
        if isinstance(advanced, dict):
            advanced.pop("ScenePlacement", None)
    return stripped


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    from KrakenOS.UI.services import offbeam_optical_solid as ob

    # -- source contract: the walk is seeded by authorship and launched on the object --
    walk_src = inspect.getsource(ob.folded_beam_reached_mirror_fold_indices)
    check(
        "_spec_is_baked_world_pose" in walk_src and "_walk_launch_origin" in walk_src,
        "S1: reached-walk seeds baked fold rows and launches from the object station",
    )

    # -- B: portable synthetic contrast (no attachment dependency) ---------------------
    mirror_faces = {
        "version": 1,
        "source_stl": "x.stl",
        "faces": [
            {"face_id": "f0", "function": "Transmit/Port"},
            {"face_id": "fm", "function": "Mirror", "normal": (0.0, 0.7071, -0.7071),
             "centroid": (0.0, 0.0, 0.0), "area_mm2": 625.0},
        ],
        "virtual_planes": [],
    }

    def parked_fold(breadcrumbed: bool) -> list[dict]:
        advanced = {
            "Solid_3d_stl": "attachment/prisms/cube.stl",
            "OpticalSolidFaces": mirror_faces,
            "OpticalSolidSourceFormat": "STEP",
        }
        if breadcrumbed:
            advanced["ScenePlacement"] = {
                "last_axis_to_axis_move": {"old_axis": "axis:selection", "new_axis": "axis:global:split"}
            }
        return [
            {"surface": "Object", "rc": 0.0, "thickness": 100.0, "diameter": 1.0, "glass": "AIR"},
            {"surface": "Surface", "rc": 50.0, "thickness": 5.0, "diameter": 35.0, "glass": "N-BK7"},
            {"surface": "Surface", "rc": 0.0, "thickness": 60.0, "diameter": 35.0, "glass": "AIR"},
            {"surface": "Surface", "rc": 0.0, "thickness": 40.0, "diameter": 25.0, "glass": "N-BK7",
             "desp_x": 200.0, "desp_y": 0.0, "desp_z": 0.0, "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0,
             "advanced": advanced},
            {"surface": "Image", "rc": 0.0, "thickness": 0.0, "diameter": 35.0, "glass": "AIR"},
        ]

    free = parked_fold(breadcrumbed=False)
    free_out = ob.neutralize_offbeam_inert_solids(free)
    check(
        abs(float(free_out[3].get("thickness", 0.0) or 0.0)) < 1e-9,
        "B1: a FREE parked fold solid is still made axially inert (0074 preserved)",
    )
    frozen = parked_fold(breadcrumbed=True)
    frozen_out = ob.neutralize_offbeam_inert_solids(frozen)
    check(
        abs(float(frozen_out[3].get("thickness", 0.0) or 0.0) - 40.0) < 1e-9,
        "B2: the SAME solid on a breadcrumbed row keeps its authored thickness",
    )
    check(
        3 in ob.folded_beam_reached_mirror_fold_indices(frozen),
        "B3: the breadcrumbed fold solid is reached BY AUTHORSHIP",
    )
    import numpy as np

    origin = ob._walk_launch_origin(
        [{"surface": "Object", "desp_x": 5.0, "desp_y": -3.0}]
    )
    check(
        np.allclose(origin, (5.0, -3.0, 0.0)) and np.allclose(ob._walk_launch_origin([]), (0.0, 0.0, 0.0)),
        "B4: the walk launch rides the object's lateral station (nominal when absent)",
    )

    # -- A: the real flagged scene (skip-if-absent, gitignored attachment) -------------
    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    editor = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        editor = KrakenLayoutEditor()
        editor.layout_files["frozen_fold_probe"] = SCENE
        editor.load_layout_by_name("frozen_fold_probe")

        def specs_now():
            return editor._serializable_specs_for_rows(editor.rows)

        base_specs = specs_now()
        base_th = _thickness_map(base_specs)
        mirror_rows = sorted(
            i
            for i, s in enumerate(base_specs)
            if isinstance(s, dict) and ob._spec_face_folds_beam(s) and ob._spec_is_baked_world_pose(s)
        )
        check(bool(mirror_rows), f"A0: the scene has breadcrumbed fold solids ({mirror_rows})")
        check(
            _thickness_map(ob.neutralize_offbeam_inert_solids(base_specs)) == base_th,
            "A1: baseline -- the neutralizer changes nothing",
        )

        bs_row = 3
        base_bs = float(editor.rows[bs_row].desp_x)
        base_obj = float(editor.rows[0].desp_x)

        # A2 -- the one-line repro: the BS alone slides past the walk threshold.
        editor.rows[bs_row].desp_x = base_bs + SLIDE
        repro_specs = specs_now()
        check(
            _thickness_map(ob.neutralize_offbeam_inert_solids(repro_specs)) == base_th,
            f"A2: BS desp_x{SLIDE:+g} alone -- every authored thickness survives",
        )
        stripped_reached = ob.folded_beam_reached_mirror_fold_indices(_strip_breadcrumbs(repro_specs))
        notes.append(
            f"NOTE A2b: on the BS-alone slide the breadcrumb-stripped geometric walk reaches "
            f"{sorted(stripped_reached)} -- authorship, not geometry, is what preserves the frozen chain"
        )

        # A3 -- the 0505 station gesture: object + BS slide together; the origin-anchored
        # walk must re-reach the mirror GEOMETRICALLY (breadcrumbs stripped on purpose).
        editor.rows[0].desp_x = base_obj + SLIDE
        station_specs = specs_now()
        check(
            _thickness_map(ob.neutralize_offbeam_inert_solids(station_specs)) == base_th,
            f"A3: station drag (object+BS {SLIDE:+g}) -- every authored thickness survives",
        )
        station_reached = ob.folded_beam_reached_mirror_fold_indices(_strip_breadcrumbs(station_specs))
        check(
            set(mirror_rows) <= station_reached,
            f"A4: with breadcrumbs stripped the station-anchored walk still reaches {mirror_rows} "
            f"geometrically (got {sorted(station_reached)})",
        )
        editor.rows[bs_row].desp_x = base_bs
        editor.rows[0].desp_x = base_obj
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass

    return ok, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
