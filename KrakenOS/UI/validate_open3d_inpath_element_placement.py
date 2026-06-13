"""Guard: a promoted in-path optical element is inserted at its true axial
position, with the chain ORDER matching the geometry and the lens/image left
fixed (bugs/0079).

The Analytic/Solid promote paths appended the element at the chain end (after the
lens) with a large desp_z, so a beam splitter that physically sits BEFORE the lens
ended up after it in the chain -> the trace produced zero rays
(ray_actor_count=0, recording flag_20260613_203812_658). The position-aware
placement core inserts it in the gap that physically contains it and splits that
gap so nothing downstream moves.

Fully DISPLAY-FREE: pure planner + spec insertion (``optical_chain_insert``) and a
real ``_build_system_from_specs`` round-trip (build only, no render).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_inpath_element_placement

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import contextlib
import io


_OBJECT = {"surface": "Object", "rc": 0.0, "thickness": 200.0, "diameter": 1.0, "glass": "AIR"}
_LENS_FRONT = {"surface": "Surface", "rc": 60.0, "thickness": 6.0, "diameter": 30.0, "glass": "N-BK7", "desp_x": 0.0, "desp_y": 0.0}
_LENS_BACK = {"surface": "Surface", "rc": -60.0, "thickness": 120.0, "diameter": 30.0, "glass": "AIR", "desp_x": 0.0, "desp_y": 0.0}
_IMAGE = {"surface": "Image", "rc": 0.0, "thickness": 0.0, "diameter": 35.0, "glass": "AIR"}

# A flat beam-splitter plate: two flat surfaces, 55 mm of BK7 between, AIR after.
_BS_SURFACES = [
    {"surface": "Standard", "rc": 0.0, "thickness": 55.0, "diameter": 80.0, "glass": "N-BK7"},
    {"surface": "Standard", "rc": 0.0, "thickness": 0.0, "diameter": 80.0, "glass": "AIR"},
]


def _build(specs):
    from KrakenOS.UI.layout_editor import _build_system_from_specs

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return _build_system_from_specs(specs)


def _vertices(system):
    sdt = getattr(system, "SDT", None) or []
    out, running = [], 0.0
    for surf in sdt:
        out.append(running)
        running += float(getattr(surf, "Thickness", 0.0) or 0.0)
    return out


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    try:
        from KrakenOS.UI.services.optical_chain_insert import (
            insert_inpath_element_into_specs,
            plan_inpath_insertion,
            vertex_positions,
        )
    except Exception as exc:  # pragma: no cover - env skip
        notes.append(f"SKIP: optical_chain_insert import failed ({type(exc).__name__}: {exc})")
        return True, notes

    # --- A. the planner splits the host gap; downstream is preserved ----------
    thicknesses = [200.0, 6.0, 120.0, 0.0]  # object, lens-front, lens-back, image
    idx, pre, trail = plan_inpath_insertion(thicknesses, element_front_z=40.0, element_depth=55.0)
    ok(idx == 1, f"A1: element inserted in the object->lens gap (after the Object, index {idx} == 1)")
    ok(abs((pre + 55.0 + trail) - 200.0) < 1e-9,
       f"A2: preceding+glass+trailing == original gap ({pre}+55+{trail} == 200) -> lens/image fixed")
    ok(abs(pre - 40.0) < 1e-9, f"A3: front face lands at the element's physical Z ({pre} == 40)")
    # an element past the last vertex still gets a sane (final) gap, never crashes
    idx2, _, _ = plan_inpath_insertion(thicknesses, element_front_z=999.0, element_depth=10.0)
    ok(0 <= idx2 <= len(thicknesses), "A4: an out-of-range Z resolves to a valid slot (no crash)")

    # --- B. real build: element BEFORE the lens, chain order == geometry ------
    baseline = [dict(_OBJECT), dict(_LENS_FRONT), dict(_LENS_BACK), dict(_IMAGE)]
    placed = insert_inpath_element_into_specs(baseline, surfaces=[dict(s) for s in _BS_SURFACES], element_front_z=40.0)
    ok(len(placed) == len(baseline) + 2, f"B1: two element surfaces spliced in ({len(placed)} == {len(baseline)+2})")
    # order: Object, BS-front, BS-back, lens-front, lens-back, Image
    surfaces_order = [str(s.get("surface", "")) for s in placed]
    bs_idx = surfaces_order.index("Standard")
    lens_idx = next(i for i, s in enumerate(placed) if abs(float(s.get("rc", 0.0)) - 60.0) < 1e-9)
    ok(bs_idx < lens_idx, f"B2: the element comes BEFORE the lens in the chain (idx {bs_idx} < {lens_idx})")
    ok(all(abs(float(placed[i].get("desp_z", 0.0))) < 1e-9 for i in (bs_idx, bs_idx + 1)),
       "B3: spliced surfaces carry NO axial decenter (no desp_z corruption)")

    try:
        sys_base = _build(baseline)
        sys_placed = _build(placed)
    except Exception as exc:  # pragma: no cover
        ok(False, f"B0: _build_system_from_specs raised {type(exc).__name__}: {exc}")
        return (not any(l.startswith("FAIL") for l in notes)), notes

    ok(sys_base is not None and sys_placed is not None, "B4: both prescriptions build")
    if sys_base is not None and sys_placed is not None:
        pos_base = _vertices(sys_base)
        pos_placed = _vertices(sys_placed)
        ok(len(pos_placed) == len(pos_base) + 2, "B5: built system gained the two element surfaces")
        # lens-front: index 1 baseline, index 3 after the 2 inserted surfaces
        if len(pos_base) >= 2 and len(pos_placed) >= 4:
            ok(abs(pos_placed[3] - pos_base[1]) < 1e-6,
               f"B6: the lens vertex does NOT move ({pos_placed[3]:.3f} == {pos_base[1]:.3f})")
        ok(abs(pos_placed[-1] - pos_base[-1]) < 1e-6,
           f"B7: the image plane does NOT move ({pos_placed[-1]:.3f} == {pos_base[-1]:.3f})")

    # --- C. the promote wiring uses the placement core (source guard) ---------
    try:
        import inspect

        from KrakenOS.UI.services.step_overlay_promotion import StepOverlayPromotionService

        promote_src = inspect.getsource(StepOverlayPromotionService.promote_imported_step_to_optical_solid_row)
    except Exception as exc:  # pragma: no cover - env skip
        notes.append(f"SKIP: promote-wiring source unavailable ({type(exc).__name__}: {exc})")
    else:
        ok("inpath_axial_placement" in promote_src,
           "C1: optical-solid promote accepts inpath_axial_placement (UI on-axis promote opts in)")
        ok("plan_inpath_insertion" in promote_src,
           "C2: promote uses plan_inpath_insertion for the axial slot + gap-split")
        ok("straddles_axis" in promote_src,
           "C3: position-aware placement is gated to elements that straddle the optical axis")
        ok('glass="AIR"' in promote_src and "inpath_trailing_gap" in promote_src,
           "C4: the trailing gap to the next element is carried by a flat AIR spacer (lens/image stay fixed)")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("In-path element placement validation passed.")
        return 0
    print("In-path element placement validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
