"""bugs/0483 -- a promoted solid's obstacle box must follow the ROW, not the last refresh.

Flag flag_20260729_185536: "unhide the Camera STEP: the anti-crash algorithm not functioning.
Camera crash to RA mirror."

``_promoted_solid_current_center`` read the centre from ``_last_scene_bundle``'s ``optical_solid``
placement, on the assumption bugs/0393b wrote down: "the mirror does not move during a lens swap,
so the last-refresh placement centre is its live position". True for a swap. False for every
action that moves a solid and then ASKS before the next refresh -- a FOV solve, a leg split, a
focus move.

Measured on ``attachment/machine_vision_AZ85_RA_Mirror_BS.py`` (bugs/0482's scene): after a
30 x 30 FOV solve with no refresh, the cached placement is 13.3 mm out in x and 31.6 mm out in z
on the fold mirror (36.9 mm in z on the BS):

    row 7 bundle (0, 229.930, 53.803)   row 7 live pose (216.603, 0, 85.365)
    row 3 bundle (-0.122, 0, 54.459)    row 3 live pose (-0.122,  0, 91.351)

``camera_body_collisions`` sizes its obstacle from that centre, so the anti-crash was testing the
mirror's PRE-SOLVE box: at 30 x 30 the mirror really sat at z[78.20, 103.20] while the check
believed z[41.30, 66.30], and it reported no overlap however deep the body sat.

Fix: prefer the ROW's own pose (``_split_row_world_center`` = station + desp, folded when the row
carries an override) -- the same truth the trace and the frozen split writers use. Measured, it
equals the bundle placement EXACTLY whenever the bundle is fresh (as loaded, after a refresh,
after a re-refresh), so this is identical when nothing moved and correct when something did.

Display-free: a stub editor whose bundle placement deliberately disagrees with its rows. No Tk,
no render, no trace.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0483_promoted_solid_live_center
"""
from __future__ import annotations

from types import SimpleNamespace


class _Row:
    def __init__(self, thickness, desp, promo_min, promo_max):
        self.thickness = float(thickness)
        self.desp_x, self.desp_y, self.desp_z = (float(v) for v in desp)
        self.advanced = {
            "StepOverlayPromotion": {
                "bounds_min_world": list(promo_min),
                "bounds_max_world": list(promo_max),
            }
        }


class _Editor:
    """Only the members the centre/bounds helpers touch."""

    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as _Mixin

    _promoted_solid_current_center = _Mixin._promoted_solid_current_center
    _promoted_solid_world_bounds = _Mixin._promoted_solid_world_bounds

    def __init__(self, rows, bundle_center=None, fold=None):
        self.rows = rows
        self._fold = fold
        self._last_scene_bundle = (
            SimpleNamespace(
                placements=[
                    SimpleNamespace(
                        source_kind="optical_solid", row_index=1, center_world=list(bundle_center)
                    )
                ]
            )
            if bundle_center is not None
            else None
        )

    # station = cumulative thickness, exactly as the real editor computes it
    def _row_z_positions(self):
        out, z = [0.0], 0.0
        for row in self.rows[:-1]:
            z += float(row.thickness)
            out.append(z)
        while len(out) < len(self.rows):
            out.append(z)
        return out

    def _split_row_world_center(self, index):
        import numpy as np

        stations = self._row_z_positions()
        row = self.rows[int(index)]
        return np.asarray(
            (float(row.desp_x), float(row.desp_y), float(stations[int(index)]) + float(row.desp_z)),
            dtype=float,
        )

    def _optical_axis_fold_world_transform_for_row(self, index):
        return self._fold


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        import numpy as np

        from KrakenOS.UI.services.layout_table_workbench import (  # noqa: F401
            LayoutTableWorkbenchMixin,
        )
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: workbench mixin unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    # The measured scene, reduced: an object gap then the promoted mirror. Promotion metadata
    # records a 25 mm cube centred where the row sat AT PROMOTION.
    def scene(object_gap):
        return [
            _Row(object_gap, (0.0, 0.0, 0.0), (-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)),
            _Row(0.0, (229.93, 0.0, -235.102), (217.43, -12.5, 41.30), (242.43, 12.5, 66.30)),
        ]

    # --- A. fresh bundle: the two sources agree, so nothing changes ------------------------
    rows = scene(288.905)
    live = _Editor(rows)._split_row_world_center(1)
    editor = _Editor(rows, bundle_center=live)
    centre = editor._promoted_solid_current_center(1)
    check(
        centre is not None and np.allclose(centre, live, atol=1.0e-9),
        f"A1: with a FRESH bundle the centre is unchanged ({np.round(centre, 3).tolist()})",
    )
    bounds = editor._promoted_solid_world_bounds(rows[1], row_index=1)
    check(
        bounds is not None and abs((bounds[1] - bounds[0]) - 25.0) < 1.0e-9,
        "A2: the promotion metadata still supplies the SIZE (25 mm), which a move cannot change",
    )

    # --- B. the regression: the row moved, the bundle did not ------------------------------
    # A 30 x 30 solve grew the object gap; the mirror's station moved with it.
    moved = scene(288.905 + 36.892)
    stale = _Editor(scene(288.905))._split_row_world_center(1)  # what the bundle still holds
    editor = _Editor(moved, bundle_center=stale)
    centre = editor._promoted_solid_current_center(1)
    expected = _Editor(moved)._split_row_world_center(1)
    check(
        centre is not None and np.allclose(centre, expected, atol=1.0e-9),
        f"B1: after the row moved, the centre follows the ROW ({np.round(centre, 3).tolist()}), "
        f"not the stale bundle ({np.round(stale, 3).tolist()})",
    )
    check(
        abs(float(centre[2]) - float(stale[2])) > 30.0,
        f"B2: the correction is the whole 36.9 mm the solve moved it "
        f"({float(centre[2]) - float(stale[2]):+.3f} mm in z)",
    )
    stale_bounds = _Editor(moved, bundle_center=stale)
    live_bounds = stale_bounds._promoted_solid_world_bounds(moved[1], row_index=1)
    check(
        live_bounds is not None and abs(live_bounds[4] - (float(expected[2]) - 12.5)) < 1.0e-9,
        "B3: the obstacle BOX moves with it, so a clearance test sees the real mirror",
    )

    # --- C. no row_index: the caller gets the documented stale fallback, not a crash -------
    fallback = _Editor(moved, bundle_center=stale)._promoted_solid_world_bounds(moved[1])
    check(
        fallback is not None and abs(fallback[4] - 41.30) < 1.0e-9,
        "C1: without a row index the promotion box is still returned (documented fallback)",
    )

    # --- D. a folded row is carried through its fold transform -----------------------------
    fold = np.eye(4)
    fold[:3, 3] = (5.0, -2.0, 7.0)
    folded = _Editor(moved, bundle_center=stale, fold=fold)._promoted_solid_current_center(1)
    check(
        folded is not None and np.allclose(folded, np.asarray(expected) + (5.0, -2.0, 7.0), atol=1.0e-9),
        "D1: a row with a fold override is reported in FOLDED world coordinates",
    )

    # --- E. the bundle is still the fallback when the row pose cannot be read --------------
    broken = _Editor(moved, bundle_center=stale)
    broken._split_row_world_center = lambda index: (_ for _ in ()).throw(RuntimeError("no pose"))
    centre = broken._promoted_solid_current_center(1)
    check(
        centre is not None and np.allclose(centre, stale, atol=1.0e-9),
        "E1: an unreadable row pose falls back to the bundle placement (bugs/0393b path kept)",
    )

    # --- F. the anti-crash actually consults this helper -----------------------------------
    try:
        import inspect as _inspect

        from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

        src = _inspect.getsource(ScenePlacementMixin.camera_body_collisions)
        check(
            "_promoted_solid_world_bounds" in src,
            "F1: the camera anti-crash sizes its obstacle from this helper (bugs/0476)",
        )
    except Exception as exc:
        notes.append(f"SKIP: anti-crash source unreadable ({type(exc).__name__}: {exc})")

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
