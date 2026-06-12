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

    lenses = [_lens(17.5, 50.0), _lens(17.5, -50.0)]

    # --- A. classifier (pure, portable) --------------------------------------
    offbeam_specs = [_OBJECT, *lenses, _cube(105.0, 174.0, copy.deepcopy(_UNCOATED)), _IMAGE]
    radius = beam_clear_radius(offbeam_specs)
    ok(abs(radius - 17.5) < 1e-9,
       f"A6: beam radius = max on-beam optical semi-diameter (17.5), got {radius}")
    ok(offbeam_inert_solid_indices(offbeam_specs) == [3],
       "A1: an off-beam uncoated promoted cube is classified off-beam")
    ok(offbeam_inert_solid_indices([_OBJECT, *lenses, _cube(105.0, 174.0, copy.deepcopy(_COATED)), _IMAGE]) == [],
       "A2: a COATED (beam-splitter) off-axis cube is exempt (stays in the trace)")
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
