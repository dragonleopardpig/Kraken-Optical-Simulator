"""Guard: a coated promoted solid is detected through the real metadata schema
and stays in the trace / off the axis (bugs/0066).

Reported (recording flag_20260612_091552_059): the user parked a beam-splitter
cube off to the side and assigned it a `Beam Splitter` coating in the Face
Editor; after the refresh the cube **snapped back onto the optical axis** and
left weird thickness overlays behind.

Root cause: `offbeam_optical_solid.solid_has_active_coating` read
`OpticalSolidFaces` as a *bare list*, but the persisted metadata is a *dict*
`{"version", "source_stl", "faces": [...], "virtual_planes"}`. The
`isinstance(faces, (list, tuple))` guard was therefore always false for real
data, so a genuinely Beam-Splitter-coated solid reported as UNCOATED -> it became
eligible for bugs/0065 off-beam neutralization, which (when the cube was parked
off the beam) dropped it from the non-sequential trace and ZEROED its `desp`, so
its body was drawn on the axis. A Beam Splitter must always stay non-sequential
(North Star), so this is a correctness bug, not only a display glitch.

Fix: `solid_has_active_coating` reads through
`normalize_optical_solid_face_metadata`, which accepts either schema. bugs/0065's
own guard missed this because its fixtures used a bare list (which the buggy
`isinstance` read happens to accept); this guard exercises the real DICT schema.

Fully DISPLAY-FREE: pure classifier + the real `_build_system_from_specs`
prescription (build only, no render).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_coated_solid_schema_exempt

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import contextlib
import copy
import io
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRESCRIPTION = PROJECT_ROOT / "attachment" / "machine_vision_150mm_measured_test.py"


def _lens(diameter: float, rc: float) -> dict:
    return {
        "surface": "Surface", "rc": rc, "thickness": 5.0, "diameter": diameter,
        "glass": "N-BK7", "desp_x": 0.0, "desp_y": 0.0,
    }


def _faces_dict(functions: list[str]) -> dict:
    """The REAL persisted OpticalSolidFaces schema: a dict wrapping the list."""
    return {
        "version": 1,
        "source_stl": "attachment/prisms/cube.stl",
        "faces": [
            {"face_id": f"F{i:03d}", "role": fn, "function": fn,
             "normal": [0.0, 0.0, 1.0], "centroid": [0.0, 0.0, 0.0]}
            for i, fn in enumerate(functions, start=1)
        ],
        "virtual_planes": [],
    }


def _cube_dict(desp_x: float, functions: list[str]) -> dict:
    """A promoted STEP cube (~25 mm footprint) whose face metadata uses the real
    DICT schema, placed at lateral ``desp_x``."""
    return {
        "surface": "Surface", "rc": 0.0, "thickness": 50.0, "diameter": 25.0,
        "glass": "N-BK7", "desp_x": desp_x, "desp_y": 0.0, "desp_z": 0.0,
        "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0,
        "advanced": {
            "Solid_3d_stl": "attachment/prisms/cube.stl",
            "StepOverlayPromotion": {
                "step_label": "cube",
                "bounds_min_world": [-12.5, -12.5, 200.0],
                "bounds_max_world": [12.5, 12.5, 225.0],
            },
            "OpticalSolidFaces": _faces_dict(functions),
            "OpticalSolidSourceFormat": "STEP",
        },
    }


_OBJECT = {"surface": "Object", "rc": 0.0, "thickness": 100.0, "diameter": 1.0, "glass": "AIR"}
_IMAGE = {"surface": "Image", "rc": 0.0, "thickness": 0.0, "diameter": 35.0, "glass": "AIR"}

# Bare-list schema (what the bugs/0065 fixture used) -- must still read as coated.
_COATED_LIST = [{"face_id": "f0", "function": "Transmit/Port"}, {"face_id": "fc", "function": "Beam Splitter"}]


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
        solid_has_active_coating,
    )

    # --- A. coating detection across schemas (pure) --------------------------
    ok(solid_has_active_coating(_cube_dict(0.0, ["Transmit/Port", "Beam Splitter"])),
       "A1: a DICT-schema Beam-Splitter solid reads as coated (the real bug)")
    ok(solid_has_active_coating({"advanced": {"OpticalSolidFaces": _COATED_LIST}}),
       "A2: a bare-LIST Beam-Splitter solid still reads as coated (back-compat)")
    ok(not solid_has_active_coating(_cube_dict(0.0, ["Transmit/Port", "Transmit/Port"])),
       "A3: a DICT-schema all-uncoated solid reads as NOT coated")
    for fn in ("Mirror", "TIR", "Absorber/Mechanical"):
        ok(solid_has_active_coating(_cube_dict(0.0, ["Transmit/Port", fn])),
           f"A4[{fn}]: a DICT-schema {fn} solid reads as coated (active-function set)")

    # --- B. the payoff: a coated off-axis cube is NOT neutralized (killer) ----
    # beam_radius = 17.5 (lens semi-diameter); cube half-extent 12.5; at
    # desp_x = -55 the inner edge clears the beam (42.5 >= 35), so an UNCOATED
    # cube IS off-beam, but the COATED one must be exempt and keep its decenter.
    lenses = [_lens(17.5, 50.0), _lens(17.5, -50.0)]
    cube_idx = 3
    coated = [_OBJECT, *lenses, _cube_dict(-55.0, ["Transmit/Port", "Beam Splitter"]), _IMAGE]
    uncoated = [_OBJECT, *lenses, _cube_dict(-55.0, ["Transmit/Port", "Transmit/Port"]), _IMAGE]
    radius = beam_clear_radius(coated)
    ok(abs(radius - 17.5) < 1e-9, f"B0: beam radius = on-beam semi-diameter (17.5), got {radius}")
    ok(not is_offbeam_inert_solid_spec(coated[cube_idx], radius),
       "B1: a DICT-schema COATED off-axis cube is exempt from off-beam neutralization")
    ok(is_offbeam_inert_solid_spec(uncoated[cube_idx], radius),
       "B1b: a DICT-schema UNCOATED off-axis cube IS off-beam (contrast -- classifier still works)")

    try:
        sys_coated = _build(coated)
        sys_uncoated = _build(uncoated)
    except Exception as exc:  # pragma: no cover - build should not raise
        ok(False, f"B2: _build_system_from_specs raised {type(exc).__name__}: {exc}")
        sys_coated = sys_uncoated = None

    if sys_coated is not None and sys_uncoated is not None:
        c = sys_coated.SDT[cube_idx]
        ok(abs(float(c.DespX) + 55.0) < 1e-6,
           f"B2 (killer): the COATED cube keeps its decenter (DespX={c.DespX}) -- "
           "stays in the non-seq trace, body off-axis (no snap)")
        u = sys_uncoated.SDT[cube_idx]
        ok(abs(float(u.DespX)) < 1e-9,
           f"B2b: the UNCOATED cube is neutralized (DespX={u.DespX} -> on-axis), proving "
           "the coated/uncoated split is the only difference")

    # --- C. the real persisted prescription (skip-if-absent) ------------------
    if PRESCRIPTION.exists():
        try:
            from KrakenOS.UI.render_layout_snapshot import _load_layout_module

            module = _load_layout_module(PRESCRIPTION)
            surfaces = list(getattr(module, "SURFACES", []) or [])
            cube_row = next(
                (s for s in surfaces
                 if isinstance(s, dict) and solid_has_active_coating(s)),
                None,
            )
            ok(cube_row is not None,
               "C: the real machine-vision prescription's promoted cube reads as coated "
               "(was UNCOATED before the schema fix)")
        except Exception as exc:
            notes.append(f"SKIP: real prescription check unavailable ({type(exc).__name__})")
    else:
        notes.append("SKIP: machine-vision prescription fixture absent")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Coated-solid schema-detection validation passed.")
        return 0
    print("Coated-solid schema-detection validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
