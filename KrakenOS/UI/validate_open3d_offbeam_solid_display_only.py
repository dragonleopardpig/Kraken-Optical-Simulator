"""Guard: a promoted optical solid parked off the beam is display-only (bugs/0065).

Reported (recording flag_20260612_073237_607): the user dragged a promoted
beam-splitter cube clear of the ray path; the on-axis trace then went wrong --
focus short of the detector, the image circle offset, and the rays appeared to
"chase" the cube ("behave like sequential rather than non-sequential ... wrong
from fundamental North Star architecture").

Root cause: the solid's lateral decenter lives in the row's `desp_x`/`desp_y`,
which `_build_system_from_specs` copies verbatim onto `surface.DespX`/`DespY` as
a *propagating* coordinate break, dragging the off-axis cube into the centered
prescription and corrupting the paraxial / best-focus / image-circle solve.

Fix: `offbeam_optical_solid.neutralize_offbeam_inert_solids`, called at the top
of `_build_system_from_specs`, replaces each off-beam INERT promoted solid with a
flat zero-power AIR surface at the on-axis station -- same thickness / diameter /
surface kind (surface count and axial chain preserved), zero decenter, no STL
solid. The solid keeps drawing in 3-D (the inspector keys on the row overlay, not
on these build specs). A coated splitter or an on-beam solid stays in the trace.

This guard is fully DISPLAY-FREE: it exercises the pure classifier and the real
`_build_system_from_specs` prescription (build=0, no render). The killer check
(C3) proves the off-beam cube's prescription is OPTICALLY IDENTICAL to a plain
air spacer -- i.e. zero optical effect, the focus is unchanged.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_offbeam_solid_display_only

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import copy
import io


def _lens(diameter: float, rc: float) -> dict:
    return {
        "surface": "Surface", "rc": rc, "thickness": 5.0, "diameter": diameter,
        "glass": "N-BK7", "desp_x": 0.0, "desp_y": 0.0,
    }


def _air(thickness: float, diameter: float = 17.5) -> dict:
    return {
        "surface": "Surface", "rc": 0.0, "thickness": thickness, "diameter": diameter,
        "glass": "AIR", "desp_x": 0.0, "desp_y": 0.0,
    }


def _mirror(desp_x: float, desp_y: float) -> dict:
    # An intentional decentered fold MIRROR -- NOT a promoted solid, must be left
    # untouched (its decenter is the user's design intent, not an off-beam body).
    return {
        "surface": "Mirror", "rc": 0.0, "thickness": -20.0, "diameter": 17.5,
        "glass": "MIRROR", "desp_x": desp_x, "desp_y": desp_y,
        "tilt_x": 45.0, "tilt_y": 0.0, "tilt_z": 0.0,
    }


def _cube(desp_x: float, desp_y: float, faces: list[dict]) -> dict:
    # A promoted STEP beam-splitter cube (~55 mm footprint), placed at (desp).
    return {
        "surface": "Surface", "rc": 0.0, "thickness": 50.0, "diameter": 25.0,
        "glass": "N-BK7", "desp_x": desp_x, "desp_y": desp_y, "desp_z": 0.0,
        "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0,
        "advanced": {
            "Solid_3d_stl": "attachment/prisms/cube.stl",
            "StepOverlayPromotion": {
                "step_label": "optical",
                "bounds_min_world": [77.5, 146.8, 341.1],
                "bounds_max_world": [133.1, 202.3, 419.7],
            },
            "OpticalSolidFaces": faces,
            "OpticalSolidSourceFormat": "STEP",
        },
    }


_UNCOATED = [{"face_id": "f0", "function": "Unassigned"}, {"face_id": "f1", "function": "Transmit/Port"}]
_COATED = [{"face_id": "f0", "function": "Transmit/Port"}, {"face_id": "fc", "function": "Beam Splitter"}]
# The REAL persisted schema wraps the face list in a dict (bugs/0066). A
# bare-list-only coating check silently treated this as uncoated and neutralised
# a genuine splitter off the trace -- exercise it explicitly here.
_COATED_DICT = {"version": 1, "source_stl": "x.stl", "faces": _COATED, "virtual_planes": []}
_OBJECT = {"surface": "Object", "rc": 0.0, "thickness": 100.0, "diameter": 1.0, "glass": "AIR"}
_IMAGE = {"surface": "Image", "rc": 0.0, "thickness": 0.0, "diameter": 35.0, "glass": "AIR"}


def _build(specs: list[dict]):
    from KrakenOS.UI.layout_editor import _build_system_from_specs

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return _build_system_from_specs(specs)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    from KrakenOS.UI.services.offbeam_optical_solid import (
        beam_clear_radius,
        is_offbeam_inert_solid_spec,
        neutralize_offbeam_inert_solids,
        neutralized_offbeam_solid_spec,
        offbeam_inert_solid_indices,
    )

    # `diameter` is a FULL clear-aperture diameter project-wide (KrakenOS draws
    # apertures at Diameter/2), so a 35 mm-diameter lens has a 17.5 mm beam radius.
    lenses = [_lens(35.0, 50.0), _lens(35.0, -50.0)]

    # --- A. classifier (pure, portable) --------------------------------------
    offbeam_specs = [_OBJECT, *lenses, _cube(105.0, 174.0, copy.deepcopy(_UNCOATED)), _IMAGE]
    radius = beam_clear_radius(offbeam_specs)
    ok(abs(radius - 17.5) < 1e-9,
       f"A6: beam radius = HALF the max on-beam full diameter (35 -> 17.5), got {radius} "
       "(bugs/0073: a full diameter used as a radius doubled the off-beam threshold)")
    ok(offbeam_inert_solid_indices(offbeam_specs) == [3],
       "A1: an off-beam uncoated promoted cube is classified off-beam")
    ok(offbeam_inert_solid_indices([_OBJECT, *lenses, _cube(105.0, 174.0, copy.deepcopy(_COATED)), _IMAGE]) == [],
       "A2: a COATED (beam-splitter) off-axis cube is exempt (stays in the trace)")
    ok(offbeam_inert_solid_indices([_OBJECT, *lenses, _cube(105.0, 174.0, copy.deepcopy(_COATED_DICT)), _IMAGE]) == [],
       "A2b: a COATED cube using the REAL dict face schema is also exempt (bugs/0066 -- "
       "a bare-list-only coating check missed this and snapped the splitter onto the axis)")
    ok(offbeam_inert_solid_indices([_OBJECT, *lenses, _cube(0.0, 0.0, copy.deepcopy(_UNCOATED)), _IMAGE]) == [],
       "A3: an on-axis cube is on the beam (not neutralised)")
    ok(offbeam_inert_solid_indices([_OBJECT, *lenses, _cube(10.0, 0.0, copy.deepcopy(_UNCOATED)), _IMAGE]) == [],
       "A4: a slightly decentered cube overlapping the beam is not neutralised")
    ok(offbeam_inert_solid_indices([_OBJECT, *lenses, _mirror(120.0, 0.0), _IMAGE]) == [],
       "A5: an intentional decentered MIRROR (not a promoted solid) is untouched")

    # --- B. neutralised spec contents (pure) ---------------------------------
    cube_spec = _cube(105.0, 174.0, copy.deepcopy(_UNCOATED))
    cube_spec_snapshot = copy.deepcopy(cube_spec)
    neutral = neutralized_offbeam_solid_spec(cube_spec)
    ok(all(abs(neutral[k]) < 1e-12 for k in ("desp_x", "desp_y", "desp_z", "tilt_x", "tilt_y", "tilt_z")),
       "B1: neutralised spec zeroes all decenter + tilt")
    ok(str(neutral["glass"]).upper().strip() == "AIR" and abs(neutral["rc"]) < 1e-12,
       "B2: neutralised spec is flat (rc 0) AIR")
    adv = neutral.get("advanced", {})
    ok(str(adv.get("Solid_3d_stl", "")).strip() == "None"
       and "StepOverlayPromotion" not in adv and "OpticalSolidFaces" not in adv,
       "B3: solid-ness dropped (Solid_3d_stl None, promotion + face metadata gone)")
    ok(abs(neutral["thickness"] - 50.0) < 1e-9 and abs(neutral["diameter"] - 25.0) < 1e-9
       and neutral["surface"] == "Surface",
       "B4: thickness, diameter and surface kind preserved (axial chain + index intact)")
    ok(cube_spec == cube_spec_snapshot,
       "B5: the source spec is not mutated (neutralisation copies)")

    # --- C. real prescription via _build_system_from_specs (display-free) -----
    spacer_specs = [_OBJECT, *lenses, _air(50.0), _IMAGE]
    try:
        sys_cube = _build(offbeam_specs)
        sys_spacer = _build(spacer_specs)
    except Exception as exc:  # pragma: no cover - build should not raise
        ok(False, f"C1: _build_system_from_specs raised {type(exc).__name__}: {exc}")
        sys_cube = sys_spacer = None

    if sys_cube is not None and sys_spacer is not None:
        ok(len(sys_cube.SDT) == len(offbeam_specs) == len(sys_spacer.SDT),
           f"C1: surface count preserved ({len(sys_cube.SDT)} == {len(offbeam_specs)})")
        n = sys_cube.SDT[3]
        ok(abs(float(n.DespX)) < 1e-12 and abs(float(n.DespY)) < 1e-12,
           f"C2: off-beam built surface has NO coordinate break (DespX={n.DespX}, DespY={n.DespY})")
        ok(str(n.Glass).upper().strip() == "AIR"
           and str(getattr(n, "Solid_3d_stl", "None")).strip() == "None",
           "C2b: off-beam built surface is a flat AIR no-op (no STL solid traced)")

        def _optically_equal(a, b) -> bool:
            return (
                abs(float(a.Rc) - float(b.Rc)) < 1e-9
                and abs(float(a.Thickness) - float(b.Thickness)) < 1e-9
                and abs(float(a.DespX) - float(b.DespX)) < 1e-9
                and abs(float(a.DespY) - float(b.DespY)) < 1e-9
                and str(a.Glass).upper().strip() == str(b.Glass).upper().strip()
            )

        ok(all(_optically_equal(sys_cube.SDT[i], sys_spacer.SDT[i]) for i in range(len(sys_cube.SDT))),
           "C3: off-beam-cube prescription == plain-AIR-spacer prescription "
           "(zero optical effect -- focus unchanged, the reported symptom is gone)")

        # C4: a coated off-axis splitter is NOT neutralised -- its decenter
        # survives into the prescription (it folds the beam; it is on the trace).
        # (Solid_3d_stl resolution is an orthogonal bugs/0021 concern keyed on the
        # on-disk mesh, so the decenter is the direct evidence the fix left it be.)
        coated_specs = [_OBJECT, *lenses, _cube(105.0, 174.0, copy.deepcopy(_COATED)), _IMAGE]
        sys_coated = _build(coated_specs)
        c = sys_coated.SDT[3]
        ok(abs(float(c.DespX) - 105.0) < 1e-6 and abs(float(c.DespY) - 174.0) < 1e-6,
           f"C4: a COATED off-axis splitter keeps its decenter (DespX={c.DespX}, DespY={c.DespY}) -- still in trace")

        # C5: an intentional decentered mirror keeps its decenter.
        mirror_specs = [_OBJECT, *lenses, _mirror(120.0, 0.0), _IMAGE]
        sys_mirror = _build(mirror_specs)
        m = sys_mirror.SDT[3]
        ok(abs(float(m.DespX) - 120.0) < 1e-6,
           f"C5: an intentional decentered mirror keeps its decenter (DespX={m.DespX})")

        # C6: integration -- neutralizer applied inside the builder leaves a
        # normal (no-solid) layout's prescription byte-for-byte unchanged.
        plain_specs = [_OBJECT, *lenses, _IMAGE]
        ok(neutralize_offbeam_inert_solids(plain_specs) is plain_specs,
           "C6: a layout with no off-beam solid is returned unchanged (zero overhead)")

    # --- D. full-diameter convention: beam_clear_radius is a true RADIUS ------
    # Production layouts store the FULL clear-aperture diameter in `diameter`
    # (KrakenOS draws apertures at Diameter/2; an Image row's diameter is the
    # literal image-circle "Ø"). The off-beam test compares a RADIAL inner-edge
    # against the beam radius, so beam_clear_radius MUST return a semi-diameter.
    # Recording flag_20260612_155154_645: a moderately decentered beam-splitter
    # cube (centre (22.62, 75.40), 50.5 mm footprint -> inner edge ~53.5 mm) was
    # parked clear of a wide machine-vision lens (full diameter 46 -> radius 23),
    # yet direct-promote (no Face Editor) bent the rays -- beam_clear_radius
    # returned the full diameter 46, inflating the off-beam threshold to 92, so the
    # 53.5 mm clearance was rejected and the cube's desp leaked (bugs/0073).
    mv_lenses = [_lens(46.0, 200.0), _lens(38.0, 150.0), _lens(21.55, 0.0),
                 _lens(38.0, 450.0), _lens(46.0, -200.0)]
    mv_image = {"surface": "Image", "rc": 0.0, "thickness": 0.0, "diameter": 37.36, "glass": "AIR"}
    mv_cube = {
        "surface": "Surface", "rc": 0.0, "thickness": 50.48, "diameter": 50.48,
        "glass": "N-BK7", "desp_x": 22.62, "desp_y": 75.40, "desp_z": 0.0,
        "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0,
        "advanced": {
            "Solid_3d_stl": "attachment/prisms/cube.stl",
            "StepOverlayPromotion": {"step_label": "optical",
                                     "bounds_min_world": [-2.62, 50.16, 217.34],
                                     "bounds_max_world": [47.86, 100.64, 267.82]},
            "OpticalSolidFaces": copy.deepcopy(_UNCOATED),
            "OpticalSolidSourceFormat": "STEP",
        },
    }
    mv_specs = [_OBJECT, *mv_lenses, mv_cube, mv_image]
    mv_cube_idx = len(mv_specs) - 2
    mv_radius = beam_clear_radius(mv_specs)
    ok(abs(mv_radius - 23.0) < 1e-9,
       f"D1: beam radius is HALF the widest full diameter (46 -> 23), got {mv_radius} "
       "(was 46 before bugs/0073 -- a full diameter read as a radius)")
    ok(offbeam_inert_solid_indices(mv_specs) == [mv_cube_idx],
       "D2: the moderately-decentered off-beam cube IS classified off-beam "
       "(inner edge 53.5 >= threshold 46; rejected before the fix vs the inflated 92)")
    sys_mv = _build(mv_specs)
    d = sys_mv.SDT[mv_cube_idx]
    ok(abs(float(d.DespX)) < 1e-9 and abs(float(d.DespY)) < 1e-9,
       f"D3: the off-beam cube is neutralised end-to-end (DespX={d.DespX}, DespY={d.DespY} ~ 0) "
       "-- no coordinate-break leak, the rays no longer bend")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Off-beam display-only solid validation passed.")
        return 0
    print("Off-beam display-only solid validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
