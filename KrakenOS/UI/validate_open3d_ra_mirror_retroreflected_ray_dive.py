"""Display-free guard for bugs/0191: on the folded RA-mirror scene the MARGINAL
imaging rays must not retroreflect at the first ideal Thin Lens and dive out the
back of the 45-deg hypotenuse.

After bugs/0190 clamped the reflected optical-axis GUIDE ("Optical Axis 2"), the
user re-flagged the same visual once more (flag_20260701_102844_382: "reflection
still wrong at hypotenuse"). The residual is NOT a guide overlay this time -- it is
the traced RAYS: 0187 folds the running frame so the imaging cone behaves, but the
ideal Thin Lens deflection ``(L/N)*f`` still back-bends a folded off-axis ray whose
axial cosine ``N`` the fold drove small, so ~21% of the marginal rays retroreflect
at row 4 (X~100), double-pass back through the mirror, and terminate at Z~-50 --
a downward ray fan crossing the hypotenuse.

Fix (bugs/0191): ``_folded_retroreflected_tail_points(points)`` truncates a display
polyline at the first ~180-deg propagation reversal (unit-direction dot below
``_FOLDED_RETROREFLECTED_TAIL_COS_MAX = -0.75``, the middle of the measured empty
gap between the retroreflection cluster [-1.0,-0.9] and the steepest legitimate fold
turn [>= -0.6]); the mixin method ``_truncate_folded_retroreflected_ray_tails`` runs
it over ``bundle.ray_paths`` ONLY on a folded scene (the same
``_optical_axis_fold_world_transform_for_row`` gate 0188/0189 use), rewriting each
``path.points_world`` in place. Unfolded / plain scenes are byte-identical.

This guard binds the REAL free function (unit) and the REAL folded gate (to the live
editor), asserting:
  1. a synthetic forward->lens->reversed->dive polyline truncates at the reversal
     vertex (the forward prefix + the reversal vertex are kept, the dive tail dropped);
  2. a monotonic-forward polyline and a degenerate/short polyline are left untouched
     (None);
  3. INTEGRATION: on the REAL traced AZ85 bundle drawn rays dive through the
     hypotenuse (Z<40 at |X|<20,|Y|<20) BEFORE the fix and NONE after -- both when the
     real free function is applied to the raw paths AND when the wired finalizer method
     runs inside _build_scene_bundle; exactly the marginal rays truncate, the imaging
     cone stays, and ray 124 keeps its axis segment 2->3 (so 0190's Optical Axis 2
     survives);
  4. the folded gate is not None for AZ85 (truncation runs) and None for flat_mirror
     (truncation gated OFF -> unfolded scenes stay byte-identical).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import (
    KrakenLayoutEditor,
    _build_system_from_specs,
    _load_python_data,
)
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.services.layout_scene_bundle_display import (
    _FOLDED_RETROREFLECTED_TAIL_COS_MAX,
    _folded_retroreflected_tail_points,
)

_LAYOUTS = Path(__file__).resolve().parent.parent / "common_optical_layouts"
_AZ85 = "machine_vision_AZ85_RA_Mirror.py"
_PLAIN = "flat_mirror_45_deg.py"
_ROW_SPEC_KEYS = (
    "surface", "name", "rc", "k", "axicon", "diff_ord", "grating_d", "grating_angle",
    "thickness", "diameter", "in_diameter", "drawing", "extra_data", "uda", "advanced",
    "tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y", "desp_z", "axis_move", "glass",
)


def _build_editor(name: str):
    layout_path = _LAYOUTS / name
    info = _load_python_data(layout_path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.tk = object()  # break tkinter __getattr__ recursion on the __new__ instance
    editor.current_layout_file = layout_path
    for attr in (
        "imported_lens_step_path",
        "imported_optical_step_path",
        "imported_led_step_path",
        "imported_camera_step_path",
    ):
        if not hasattr(editor, attr):
            setattr(editor, attr, None)
    editor._normalize_special_rows()
    return editor


def _trace(editor):
    rows = editor.rows
    row_specs = [{k: getattr(r, k) for k in _ROW_SPEC_KEYS} for r in rows]
    if row_specs and getattr(editor, "metal_catalogs", None):
        row_specs[0]["_metal_catalogs"] = editor.metal_catalogs
    system = _build_system_from_specs(row_specs)
    wavelength = float(editor._current_wavelength())
    rays = Kos.raykeeper(system)
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in rows), default=1.0)
    editor._trace_preview_rays(
        system, rays, wavelength, max_radius,
        allow_full_pupil=True, sampling_mode=editor._preview_2d_sampling_mode(),
    )
    editor.last_system = system
    editor.last_rays = rays
    return system, rays, max_radius


def _scene_is_folded(editor) -> bool:
    return any(
        editor._optical_axis_fold_world_transform_for_row(i) is not None
        for i in range(len(editor.rows))
    )


def _dives(points) -> bool:
    """A drawn ray crosses BELOW the mirror at the axis (Z<40, |X|<20, |Y|<20), past
    its launch point -- the down-through-the-hypotenuse signature."""
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2:
        return False
    tail = pts[1:]
    return bool(np.any((tail[:, 2] < 40.0) & (np.abs(tail[:, 0]) < 20.0) & (np.abs(tail[:, 1]) < 20.0)))


def _drawn(editor, bundle):
    return list(editor._iter_3d_scene_ray_records(editor.last_rays, bundle))


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    # ---- (1) a forward->lens->reversed->dive polyline truncates at the reversal ----
    poly = np.asarray(
        (
            (0.0, 0.0, 0.0),      # object
            (0.0, 0.0, 71.9),     # mirror fold (90 deg turn, dot ~0, NOT a reversal)
            (40.0, 0.0, 71.9),    # +X toward the lens
            (100.0, 0.0, 71.9),   # first Thin Lens -- the retroreflection vertex
            (40.0, 0.0, 71.9),    # reversed -X (double-pass back)
            (0.0, 0.0, -50.0),    # dive out the back of the hypotenuse
        ),
        dtype=float,
    )
    cut = _folded_retroreflected_tail_points(poly)
    if cut is None:
        failures.append("truncate: the retroreflect+dive polyline was NOT truncated")
    else:
        cut = np.asarray(cut, dtype=float)
        if cut.shape[0] != 4:
            failures.append(
                f"truncate: kept {cut.shape[0]} points, expected 4 (object..fold..40..lens-vertex)"
            )
        if float(cut[:, 2].min()) < -1.0:
            failures.append("truncate: the dive tail (Z<0, below the hypotenuse) survived the truncation")
        if abs(float(cut[-1, 0]) - 100.0) > 1e-6:
            failures.append("truncate: the ray was not stopped AT the lens reversal vertex (X=100)")
        if _dives(cut):
            failures.append("truncate: the truncated ray still dives through the hypotenuse")

    # ---- (2) a forward-only polyline + a degenerate one are left untouched ----
    forward_only = np.asarray(
        ((0.0, 0.0, 0.0), (0.0, 0.0, 71.9), (40.0, 0.0, 71.9), (100.0, 0.0, 71.9), (288.0, 0.0, 71.9)),
        dtype=float,
    )
    if _folded_retroreflected_tail_points(forward_only) is not None:
        failures.append("regression: a monotonic-forward (imaging-cone) ray was truncated")
    if _folded_retroreflected_tail_points(np.zeros((1, 3))) is not None:
        failures.append("regression: a 1-point polyline was not handled safely (expected None)")
    if _folded_retroreflected_tail_points(np.zeros((2, 3))) is not None:
        failures.append("regression: a degenerate 2-point polyline was not handled safely (expected None)")
    if _FOLDED_RETROREFLECTED_TAIL_COS_MAX >= -0.6 or _FOLDED_RETROREFLECTED_TAIL_COS_MAX <= -0.9:
        failures.append(
            f"threshold: cos_max {_FOLDED_RETROREFLECTED_TAIL_COS_MAX} is not inside the measured "
            f"empty gap (-0.9, -0.6) between retroreflections and the steepest legitimate fold turn"
        )

    # ---- (3) INTEGRATION: real AZ85 rays dive BEFORE, none AFTER ----
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor = _build_editor(_AZ85)
            _trace(editor)
            # BEFORE: shadow the wired finalizer method with a no-op so the bundle keeps
            # the raw (un-truncated) retroreflecting polylines.
            editor._truncate_folded_retroreflected_ray_tails = lambda bundle: 0
            raw_bundle = editor._build_scene_bundle(editor.last_system, editor.last_rays, 1.0)
            raw_records = _drawn(editor, raw_bundle)
            # AFTER (a): the REAL free function applied to each raw drawn polyline.
            # AFTER (b): the REAL wired finalizer method inside a fresh build.
            del editor._truncate_folded_retroreflected_ray_tails  # restore the class method
            _trace(editor)
            fixed_bundle = editor._build_scene_bundle(editor.last_system, editor.last_rays, 1.0)
            fixed_records = _drawn(editor, fixed_bundle)

        dives_before = sum(1 for (_ri, _c, pts, _t) in raw_records if _dives(pts))
        helper_after = 0
        truncated = 0
        r124_seg_ok = None
        for (ri, _c, pts, _t) in raw_records:
            fixed = _folded_retroreflected_tail_points(pts)
            drawn = pts if fixed is None else fixed
            if fixed is not None:
                truncated += 1
            if _dives(drawn):
                helper_after += 1
            if int(ri) == 124:
                d = np.asarray(drawn, dtype=float)
                # segment 2->3 (X 40 -> 82.45) is the basis of 0190's "Optical Axis 2"
                r124_seg_ok = d.shape[0] >= 4 and float(d[:, 0].max()) < 150.0
        wired_after = sum(1 for (_ri, _c, pts, _t) in fixed_records if _dives(pts))

        if dives_before <= 0:
            failures.append(
                "AZ85 integration: no drawn ray dives through the hypotenuse BEFORE the fix "
                "(the bug precondition is gone?) -- guard would be vacuous"
            )
        if helper_after != 0:
            failures.append(
                f"AZ85 integration: {helper_after} ray(s) still dive after the REAL free function"
            )
        if wired_after != 0:
            failures.append(
                f"AZ85 integration: {wired_after} ray(s) still dive after the WIRED finalizer method"
            )
        if truncated <= 0:
            failures.append("AZ85 integration: the free function truncated no rays at all")
        if r124_seg_ok is False:
            failures.append(
                "AZ85 integration: ray 124 lost its axis segment 2->3 after truncation "
                "(0190's Optical Axis 2 would break)"
            )
        notes.append(
            f"AZ85 drawn rays {len(raw_records)} | dive BEFORE {dives_before} -> free-fn AFTER "
            f"{helper_after}, wired AFTER {wired_after} | truncated {truncated} | "
            f"ray124 seg2->3 kept {r124_seg_ok}"
        )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"AZ85 integration raised {exc!r}")

    # ---- (4) folded gate: not None for AZ85, None for flat_mirror ----
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            az_folded = _scene_is_folded(_build_editor(_AZ85))
            plain_folded = _scene_is_folded(_build_editor(_PLAIN))
        if not az_folded:
            failures.append("AZ85 gate: scene reports UNfolded -> the truncation would never run")
        if plain_folded:
            failures.append(
                f"regression: {_PLAIN} reports FOLDED -> truncation would run on an unfolded scene"
            )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"folded-gate check raised {exc!r}")

    if failures:
        print("FAIL bugs/0191 folded RA-mirror retroreflected-ray dive through the hypotenuse:")
        for line in failures:
            print(f"  - {line}")
        for note in notes:
            print(f"  - note: {note}")
        return 1
    print("PASS bugs/0191 folded RA-mirror retroreflected-ray dive (marginal rays stop at the lens):")
    print("  - a forward->lens->reversed->dive polyline truncates at the reversal vertex (dive dropped)")
    print("  - a forward-only ray + degenerate/short polylines are left untouched (None)")
    print("  - AZ85 real trace: rays dive through the hypotenuse BEFORE, 0 after (free fn AND wired method)")
    print(f"  - folded gate: not None for AZ85 (truncation runs), None for {_PLAIN} (gated OFF)")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
