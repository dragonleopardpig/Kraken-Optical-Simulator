"""Guard for bugs/0764 -- the focus snap may not leave the scene worse than it found it,
and the traced measure that proves it must actually see the rays.

The flag: "kill Kitty, restarted, set FOV to 30x30, click Apply+Solve FOV for this face.
Image is not landed on sensor." Measured on ``attachment/om05a_folded_80mm.py`` with the
device 30 mm deep, the solve landed focus at -0.0506 mm and then moved the sensor +5.8819 mm
back off it, ending at -5.9325 mm -- which is -0.0506 - 5.8819 to four decimals.

Two independent defects stacked:

  1. ``_traced_bundle_best_focus_shift`` filtered ray paths on ``termination_reason ==
     "target_termination"`` alone. That is the OLDER spelling; the scene builder stamps
     "image". On om05a 644 rays land as "image" and 0 as "target_termination", so the measure
     matched nothing and returned None on every call. None is not inert: it is the signal
     ``snap_detector_to_image_plane`` reads as "no bundle is measurable", and the finisher's
     before/after verification (bugs/0645) degrades to NaN and claims focus unconditionally.

  2. With no real-ray measure, the snap's unfrozen branch fired a single unverified shot at
     ``_paraxial_image_plane_z() - sum(row.thickness)`` -- two STATION-frame sums that equal
     the world defocus only when every row sits at its cumulative thickness. om05a seats rows
     16-23 by desp and runs its image gap row backwards, so the number was measured in a frame
     that is not that scene. bugs/0577 had already written the rule for the frozen branch --
     "a refocus that cannot improve the scene must leave it exactly as it found it" -- but the
     unfrozen branch enforced nothing.

Checks (display-free, pure):
  A  the traced measure accepts BOTH termination spellings, and a synthetic bundle stamped
     with the current spelling is measured rather than refused;
  B  the unfrozen snap measures before, measures after, and restores the snapshot when the
     move made the traced defocus worse -- and says so instead of reporting success;
  C  a move that improves focus, or one the measure cannot judge, is left alone (the guard
     never blocks a good snap, and never invents a verdict from no measurement);
  D  the verification is REAL-RAY: it may not fall back to a station-frame walk to check a
     station-frame correction;
  E  the flag bundle records the inspection part (W/D/H), and the part dialog reads W, D, H.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0764_focus_snap_may_not_make_focus_worse
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np


class _Path:
    def __init__(self, termination_reason, points):
        self.termination_reason = termination_reason
        self.points_world = np.asarray(points, dtype=float)


class _Target:
    is_detector = True
    metadata = {"focus_source": "reached_image"}

    def __init__(self, centre, normal):
        self.center_world = np.asarray(centre, dtype=float)
        self.normal_world = np.asarray(normal, dtype=float)


def _converging_bundle(spelling: str, waist_at: float = 7.5, tail: float = 0.5):
    """A cone of rays that waists ``waist_at`` mm past the detector, stamped with ``spelling``.

    Four rays converging on the axis -- enough to clear the measure's >=4 test -- launched
    from one point so they read as a single field. Returns ``(bundle, expected_shift)``: the
    measure scans forward from each ray's LAST point, which sits ``tail`` mm down the final
    segment, so the waist it should report is ``waist_at`` less that segment's own z advance.
    """
    launch = np.array([0.0, 0.0, -100.0])
    paths = []
    expected = None
    for dx, dy in ((1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)):
        start = np.array([dx, dy, 0.0])
        end = np.array([0.0, 0.0, float(waist_at)])
        direction = end - start
        direction = direction / np.linalg.norm(direction)
        paths.append(_Path(spelling, [launch, start, start + direction * tail]))
        expected = float(waist_at) - float(tail) * float(direction[2])
    bundle = SimpleNamespace(
        ray_paths=paths,
        targets=[_Target((0.0, 0.0, 0.0), (0.0, 0.0, 1.0))],
    )
    return bundle, expected


class _MeasureHost:
    """The minimum surface ``_traced_bundle_best_focus_shift`` reads."""

    def __init__(self, bundle):
        self._bundle = bundle
        self.rows = [SimpleNamespace(desp_x=0.0, desp_y=0.0, desp_z=-100.0)]

    def _build_preview_system_rays_bundle(self, **_kwargs):
        return (None, None, self._bundle)

    def _row_z_positions(self):
        return [0.0]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import scene_placement_commands as spc
    from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin

    # ---- A: the traced measure sees the rays that actually land ----------------------------
    measure_src = inspect.getsource(ParaxialToolsMixin._traced_bundle_best_focus_shift)
    ok(
        '"image", "target_termination"' in measure_src
        or '"target_termination", "image"' in measure_src,
        "A1: the traced best-focus measure accepts BOTH termination spellings, so a bundle "
        "stamped with the current one ('image') is not silently unmeasurable",
    )
    ok(
        'termination_reason", "")) != "target_termination"' not in measure_src,
        "A2: the old exact-match on the legacy spelling alone is gone",
    )

    class _Measurer(ParaxialToolsMixin, _MeasureHost):
        pass

    results = {}
    expected_shift = None
    for spelling in ("image", "target_termination"):
        bundle, expected_shift = _converging_bundle(spelling)
        host = _Measurer(bundle)
        try:
            results[spelling] = host._traced_bundle_best_focus_shift()
        except Exception as exc:  # pragma: no cover - a raise is a failure, reported below
            results[spelling] = f"raised {type(exc).__name__}: {exc}"
    ok(
        isinstance(results.get("image"), float),
        f"A3: a bundle stamped 'image' MEASURES instead of returning None "
        f"(got {results.get('image')!r})",
    )
    ok(
        isinstance(results.get("target_termination"), float),
        f"A4: the legacy spelling still measures -- accepting both did not drop the old one "
        f"(got {results.get('target_termination')!r})",
    )
    if isinstance(results.get("image"), float) and isinstance(
        results.get("target_termination"), float
    ):
        ok(
            abs(float(results["image"]) - float(results["target_termination"])) < 1e-6,
            "A5: and both spellings measure the SAME waist (the filter is the only difference)",
        )
        ok(
            abs(abs(float(results["image"])) - float(expected_shift)) < 0.01,
            f"A6: the measured shift finds the cone's waist "
            f"(expected {float(expected_shift):.4f} mm, got "
            f"{abs(float(results['image'])):.4f} mm)",
        )

    # ---- B/C/D: the snap's unfrozen branch verifies and reverts ------------------------------
    mixin = spc.ScenePlacementMixin
    snap_src = inspect.getsource(mixin.snap_detector_to_image_plane)

    unfrozen = snap_src.split("if not _frozen_world:", 1)[-1].split("        else:", 1)[0]
    ok(
        "_traced_snap_defocus_magnitude()" in unfrozen,
        "B1: the unfrozen branch MEASURES the traced defocus around its write",
    )
    ok(
        unfrozen.count("_traced_snap_defocus_magnitude()") >= 2,
        "B2: before AND after -- one reading cannot tell you whether the move helped",
    )
    ok(
        "_restore_row_snapshot(" in unfrozen and "_row_snapshot()" in unfrozen,
        "B3: and it restores the row snapshot rather than leaving the bad write standing "
        "(bugs/0577's rule, now enforced off the frozen branch too)",
    )
    ok(
        "_snap_detector_refusal" in unfrozen and "return False" in unfrozen,
        "B4: a reverted snap reports a refusal and returns False, so the caller cannot go on "
        "claiming focus it did not achieve",
    )
    ok(
        "_SNAP_REGRESSION_TOL_MM" in unfrozen,
        "B5: the regression test carries a named tolerance, not a bare float",
    )
    ok(
        0.0 < float(spc._SNAP_REGRESSION_TOL_MM) < 0.153,
        f"C1: the tolerance ({spc._SNAP_REGRESSION_TOL_MM} mm) sits inside one pixel of depth "
        f"of focus (0.153 mm) -- it reverts real regressions, not sampling noise",
    )
    ok(
        "if _defocus_before is not None:" in unfrozen,
        "C2: with no measure available the guard stands down (behaviour unchanged) instead of "
        "inventing a verdict",
    )
    ok(
        "> _defocus_before + _SNAP_REGRESSION_TOL_MM" in unfrozen,
        "C3: only a move that measured WORSE is reverted -- an improving or neutral snap is "
        "left exactly as the existing code applied it",
    )

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    # bugs/0763, the crash in the same flag's error.png -- documented in bugs/0764 as defect 1.
    pair_src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok(
        "if isinstance(object_slid, dict):" in pair_src
        and "object_slid.get(" not in pair_src.split("if isinstance(object_slid, dict):")[0]
        .rsplit("moved_mm", 1)[-1],
        "B0: the residual report reads object_slid only after an isinstance check -- the lens "
        "does not always move by a SLIDE, and 'NoneType' object has no attribute 'get' killed "
        "the solve mid-write (bugs/0763)",
    )

    finisher_src = inspect.getsource(QuickEstimationService._finish_solve_on_traced_focus)
    ok(
        "already at the traced focus" in finisher_src
        and finisher_src.index("_snap_detector_refusal") < finisher_src.index(
            "(snapped to the traced focus)"
        ),
        "B6: a DECLINED snap is not reported as 'snapped to the traced focus' -- crediting the "
        "snap for focus the solve had already landed is how the fabricated correction went "
        "unnoticed",
    )

    guard_src = inspect.getsource(mixin._traced_snap_defocus_magnitude) if mixin else ""
    ok(
        "_traced_bundle_best_focus_shift" in guard_src
        and "_measure_focused_image_plane" in guard_src,
        "D1: the verification reads the traced bundle (with the bugs/0752 per-image measure as "
        "its fallback for a split-field scene)",
    )
    ok(
        "_real_ray_best_focus_shift_for_rows" not in guard_src
        and "_paraxial_image_plane_z" not in guard_src,
        "D2: and it never verifies a station-frame correction with another station-frame walk "
        "-- the straight equivalent is a different prescription (bugs/0593)",
    )

    # ---- E: the flag records the part, and the dialog reads W, D, H --------------------------
    from KrakenOS.UI import open3d_inspector
    from KrakenOS.UI.services import inspection_part

    inspector_src = inspect.getsource(open3d_inspector)
    ok(
        '"inspection_part": self._flag_inspection_part_spec(),' in inspector_src,
        "E1: the 3D flag bundle records the inspection part alongside the scene state",
    )

    class _SpecHost:
        editor = SimpleNamespace(
            inspection_part_spec={
                "enabled": True, "width_mm": "30", "height_mm": "1", "depth_mm": "30",
                "axis_reach_mm": "0", "axis_offset_mm": "0", "active_face": "front",
                "step_path": "",
            }
        )
        _flag_inspection_part_spec = open3d_inspector.Kraken3DInspector.__dict__[
            "_flag_inspection_part_spec"
        ]

    recorded = _SpecHost()._flag_inspection_part_spec()
    ok(
        {"width_mm", "height_mm", "depth_mm"} <= set(recorded),
        f"E2: W, H and D all reach the bundle (got {sorted(recorded)})",
    )
    ok(
        float(recorded.get("width_mm", 0)) == 30.0
        and float(recorded.get("height_mm", 0)) == 1.0
        and float(recorded.get("depth_mm", 0)) == 30.0,
        f"E3: as the numbers a repro can feed straight back "
        f"(got W={recorded.get('width_mm')} H={recorded.get('height_mm')} "
        f"D={recorded.get('depth_mm')})",
    )
    _SpecHost.editor = SimpleNamespace()
    ok(
        isinstance(_SpecHost()._flag_inspection_part_spec(), dict),
        "E4: a scene with no part still flags cleanly -- the recorder never raises",
    )

    dialog_src = inspect.getsource(inspection_part.open_inspection_part_dialog)
    order = [
        label
        for label in ("Width W (mm)", "Depth D (mm)", "Height H (mm)")
    ]
    positions = [dialog_src.find(label) for label in order]
    ok(
        all(pos > 0 for pos in positions) and positions == sorted(positions),
        f"E5: the part dialog reads W, D, then H (user request) -- got offsets {positions}",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0764 focus-snap-may-not-make-focus-worse validation PASSED")
        return 0
    print("0764 focus-snap-may-not-make-focus-worse validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
