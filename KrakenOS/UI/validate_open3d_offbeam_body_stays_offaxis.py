"""Guard: a neutralised off-beam solid's BODY stays off-axis in 3-D (bugs/0067).

Reported (recordings flag_20260612_102753_518 / _103030_081): the moment a
parked, still-UNCOATED promoted solid is converted to an optical row / the Face
Editor opens, its 3-D body snaps onto the optical axis -- before the user can
even assign a Beam-Splitter coating.

Root cause: bugs/0065 correctly drops an off-beam INERT solid from the optical
trace (`neutralize_offbeam_inert_solids`), so the built prescription is on-axis
-- but the 3-D body is placed by that *neutralised* build transform
(`TRANS_2A[index]`), which now sits on the axis. The body geometry still comes
from the live row's STL, yet its world placement comes from the on-axis chain,
so the body snaps to the axis. (0065's docstring claimed the body "keeps drawing
off-axis"; it never actually did.)

Fix (display-only, optical solve untouched):
`offbeam_optical_solid.offbeam_neutralized_body_transform` restores the body's
lateral station by adding `R @ desp` to the neutralised transform's translation,
where `R` is its rotation block and `desp` the live row's decenter. For an
untilted solid this is EXACT: the non-neutralised and neutralised
`TRANS_2A[index]` share their rotation block and differ in translation by
precisely `R @ desp`. `three_d_scene_tools._iter_3d_optical_surface_meshes`
applies it right before placing the file-backed body. A coated splitter keeps
its decenter in the build (`SDT.DespX != 0`), so the helper no-ops and leaves it
exactly where the trace put it.

This guard is fully DISPLAY-FREE. It pins:
  * the pure helper contract (A),
  * a real `_build_system_from_specs` round-trip proving the body WOULD snap and
    that the re-decenter reproduces the non-neutralised station (B, the killer),
  * a coated splitter is never re-decentered (C),
  * the helper is actually wired into the scene builder (D).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_offbeam_body_stays_offaxis

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import copy
import io

import numpy as np


def _lens(diameter: float, rc: float) -> dict:
    return {
        "surface": "Surface", "rc": rc, "thickness": 5.0, "diameter": diameter,
        "glass": "N-BK7", "desp_x": 0.0, "desp_y": 0.0,
    }


def _faces_dict(functions: list[str]) -> dict:
    # The real persisted face schema: a dict wrapping the face list (bugs/0066).
    return {
        "version": 1, "source_stl": "attachment/prisms/cube.stl",
        "faces": [
            {"face_id": f"F{i:03d}", "role": fn, "function": fn,
             "normal": [0.0, 0.0, 1.0], "centroid": [0.0, 0.0, 0.0]}
            for i, fn in enumerate(functions, start=1)
        ],
        "virtual_planes": [],
    }


def _cube(desp_x: float, functions: list[str], *, desp_y: float = 0.0) -> dict:
    # A promoted STEP cube (~25 mm footprint) parked at (desp_x, desp_y).
    return {
        "surface": "Surface", "rc": 0.0, "thickness": 50.0, "diameter": 25.0,
        "glass": "N-BK7", "desp_x": desp_x, "desp_y": desp_y, "desp_z": 0.0,
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
_CUBE_IDX = 3


def _build(specs: list[dict]):
    from KrakenOS.UI.layout_editor import _build_system_from_specs

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return _build_system_from_specs(specs)


def _build_without_neutralization(specs: list[dict]):
    # Reference build with neutralisation stubbed to identity -- the off-axis
    # "truth" the display body must reproduce.
    import KrakenOS.UI.layout_editor as le

    orig = le.neutralize_offbeam_inert_solids
    le.neutralize_offbeam_inert_solids = lambda s: s
    try:
        return _build(specs)
    finally:
        le.neutralize_offbeam_inert_solids = orig


def _trans(system, idx: int):
    t = getattr(system, "TRANS_2A", None)
    if t is None or not (0 <= idx < len(t)):
        return None
    return np.asarray(t[idx], dtype=float)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    from KrakenOS.UI.services.offbeam_optical_solid import (
        beam_clear_radius,
        is_offbeam_inert_solid_spec,
        offbeam_neutralized_body_transform,
    )

    lenses = [_lens(17.5, 50.0), _lens(17.5, -50.0)]
    uncoated_specs = [_OBJECT, *lenses, _cube(-55.0, ["Transmit/Port", "Transmit/Port"]), _IMAGE]
    live_cube = copy.deepcopy(uncoated_specs[_CUBE_IDX])

    # --- A. pure helper contract (no build) ----------------------------------
    eye4 = np.eye(4)
    ok(offbeam_neutralized_body_transform(None, live_cube, 0.0, 0.0) is None,
       "A1: None base transform -> None (caller keeps ordinary placement)")
    ok(offbeam_neutralized_body_transform(eye4, {"surface": "Surface", "glass": "AIR"}, 0.0, 0.0) is None,
       "A2: a non-promoted spec is never re-decentered")
    ok(offbeam_neutralized_body_transform(eye4, _cube(0.0, ["Transmit/Port"]), 0.0, 0.0) is None,
       "A3: an on-axis promoted solid (no decenter) -> None")
    ok(offbeam_neutralized_body_transform(eye4, live_cube, -55.0, 0.0) is None,
       "A4: build KEPT the decenter (DespX != 0) -> None (no double-decenter; coated-splitter safe)")
    restored_eye = offbeam_neutralized_body_transform(eye4, live_cube, 0.0, 0.0)
    ok(restored_eye is not None and np.allclose(restored_eye[:3, 3], [-55.0, 0.0, 0.0], atol=1e-9),
       "A5: identity base + decenter -55 + built-desp 0 -> translation == desp (R == I)")
    ok(restored_eye is not None and np.allclose(restored_eye[:3, :3], np.eye(3), atol=1e-12),
       "A6: rotation block left unchanged (only the lateral station is restored)")
    ok(is_offbeam_inert_solid_spec(uncoated_specs[_CUBE_IDX], beam_clear_radius(uncoated_specs)),
       "A7: the test cube is classified off-beam inert (the build WILL neutralise it)")

    # --- B. real build round-trip: re-decenter reproduces the off-axis truth --
    try:
        sys_neut = _build(copy.deepcopy(uncoated_specs))             # production: neutralised
        sys_full = _build_without_neutralization(copy.deepcopy(uncoated_specs))  # truth
    except Exception as exc:  # pragma: no cover - build should not raise
        ok(False, f"B0: build raised {type(exc).__name__}: {exc}")
        sys_neut = sys_full = None

    if sys_neut is not None and sys_full is not None:
        tn = _trans(sys_neut, _CUBE_IDX)
        tf = _trans(sys_full, _CUBE_IDX)
        built_neut = sys_neut.SDT[_CUBE_IDX]
        built_full = sys_full.SDT[_CUBE_IDX]

        ok(abs(float(built_neut.DespX)) < 1e-9 and abs(float(built_neut.DespY)) < 1e-9,
           f"B1: production build neutralises the solid (SDT DespX={built_neut.DespX} ~ 0) -- optical solve untouched")
        ok(abs(float(built_full.DespX) + 55.0) < 1e-6,
           f"B2: the un-neutralised reference keeps the decenter (SDT DespX={built_full.DespX})")
        snapped_by = None if (tn is None or tf is None) else np.round(tf[:3, 3] - tn[:3, 3], 3)
        ok(tn is not None and tf is not None and not np.allclose(tn[:3, 3], tf[:3, 3], atol=1e-6),
           f"B3: WITHOUT the fix the body snaps -- neutralised TRANS_2A is on-axis, off by {snapped_by} from the true station")

        restored = (
            None if tn is None
            else offbeam_neutralized_body_transform(tn, live_cube, float(built_neut.DespX), float(built_neut.DespY))
        )
        ok(restored is not None and tf is not None and np.allclose(restored[:3, 3], tf[:3, 3], atol=1e-6),
           "B4 (KILLER): re-decentered body transform == the non-neutralised TRANS_2A station "
           f"(restored={None if restored is None else np.round(restored[:3, 3], 3)}, "
           f"truth={None if tf is None else np.round(tf[:3, 3], 3)})")
        ok(restored is not None and tn is not None and np.allclose(restored[:3, :3], tn[:3, :3], atol=1e-9),
           "B5: rotation block matches the build transform (lateral station only)")

        noop = (
            None if tf is None
            else offbeam_neutralized_body_transform(tf, live_cube, float(built_full.DespX), float(built_full.DespY))
        )
        ok(noop is None,
           "B6: on a build that kept the decenter the helper returns None (never double-decenters)")

    # --- C. a coated splitter is never re-decentered (stays where the trace puts it)
    coated_specs = [_OBJECT, *lenses, _cube(-55.0, ["Transmit/Port", "Beam Splitter"]), _IMAGE]
    try:
        sys_coated = _build(copy.deepcopy(coated_specs))
    except Exception as exc:  # pragma: no cover
        ok(False, f"C0: coated build raised {type(exc).__name__}: {exc}")
        sys_coated = None
    if sys_coated is not None:
        tc = _trans(sys_coated, _CUBE_IDX)
        built_coated = sys_coated.SDT[_CUBE_IDX]
        ok(abs(float(built_coated.DespX) + 55.0) < 1e-6,
           f"C1: a coated splitter keeps its decenter in the build (SDT DespX={built_coated.DespX}) -- still in trace")
        ok(tc is None or offbeam_neutralized_body_transform(
               tc, coated_specs[_CUBE_IDX], float(built_coated.DespX), float(built_coated.DespY)) is None,
           "C2: the coated splitter body is NOT re-decentered (the build already placed it off-axis)")

    # --- D. the fix is actually wired into the scene builder ------------------
    try:
        import KrakenOS.UI.services.three_d_scene_tools as tdt
        ok(getattr(tdt, "offbeam_neutralized_body_transform", None) is offbeam_neutralized_body_transform
           and callable(getattr(tdt, "surface_row_to_spec", None)),
           "D1: three_d_scene_tools imports the re-decenter helper + row->spec converter (wiring present)")
    except Exception as exc:  # pragma: no cover
        ok(False, f"D1: could not import three_d_scene_tools to confirm wiring ({type(exc).__name__}: {exc})")

    # --- E. the SHARED transform helper re-decenters too (bugs/0075) -----------
    # _iter_3d_optical_surface_meshes (D) is not the only consumer of the build
    # transform. The selected-body redraw, assigned-face overlays, markers,
    # virtual planes and the placement gizmo all read it through
    # Kraken3DInspector._runtime_transform_for_row, which returned the RAW on-axis
    # TRANS_2A -- so the instant the Face Editor selected a parked off-beam solid
    # the whole cube snapped onto the axis while the row Desp stayed off-axis
    # (recording flag_20260612_213626_155: row Desp (72.9, 88.4) but the body
    # actor centred on (0, 0)).
    try:
        import inspect as _inspect
        from types import SimpleNamespace as _NS
        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
        from KrakenOS.UI.surface_table_model import SurfaceRow as _SR

        rt_src = _inspect.getsource(Kraken3DInspector._runtime_transform_for_row)
        ok("offbeam_neutralized_body_transform(" in rt_src,
           "E1: _runtime_transform_for_row applies the off-beam re-decenter (wiring present)")

        def _to_row(spec: dict):
            fields = set(_SR.__dataclass_fields__)
            return _SR(**{k: v for k, v in spec.items() if k in fields})

        def _shared_transform(system, specs):
            insp = object.__new__(Kraken3DInspector)
            insp.editor = _NS(rows=[_to_row(s) for s in specs])
            insp._saved_step_native_display_transform_for_row = lambda idx: None
            return insp._runtime_transform_for_row(system, _CUBE_IDX)

        if sys_neut is not None:
            e_rt = _shared_transform(sys_neut, uncoated_specs)
            ok(e_rt is not None and abs(float(e_rt[0, 3]) + 55.0) < 1e-6,
               "E2 (KILLER): _runtime_transform_for_row re-decenters the neutralised solid "
               f"(x={None if e_rt is None else round(float(e_rt[0, 3]), 2)} ~ -55, NOT 0) -- "
               "the selected body / face overlays / markers / gizmo no longer snap to the optical axis")
        if sys_coated is not None:
            c_rt = _shared_transform(sys_coated, coated_specs)
            ok(c_rt is not None and abs(float(c_rt[0, 3]) + 55.0) < 1e-6,
               "E3: a coated splitter's shared transform keeps its decenter "
               f"(x={None if c_rt is None else round(float(c_rt[0, 3]), 2)} ~ -55) -- no double-decenter")
    except Exception as exc:  # pragma: no cover
        ok(False, f"E: _runtime_transform_for_row re-decenter check raised {type(exc).__name__}: {exc}")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Off-beam body-stays-off-axis validation passed.")
        return 0
    print("Off-beam body-stays-off-axis validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
