"""bugs/0217 -- VALIDATED-BUT-UNSHIPPED prototype, preserved as scratch.

This is the reconcile-to-ray-convergence post-pass that fixed the two-mirror AZ85 focus
HEADLESSLY (detector + ray endpoints snap to z=-33.84 at 0.7 um; single-mirror = clean no-op)
but was REVERTED because it only moves SOME of the detector's several representations and so
regressed ``validate_open3d_second_mirror_orientation_driven_fold`` (see bugs/0217 doc, "The
entanglement"). Kept here so an in-app eyeball session can re-apply it in seconds.

TO EYEBALL (accepts the one guard regression, which is cosmetic-to-the-eyeball):
  1. Paste ``_FOLDED_FOCUS_*`` constants below the other module constants in
     ``KrakenOS/UI/services/three_d_scene_tools.py`` (near ``_RAY_DRAW_BUDGET_CONE``).
  2. Paste ``_reconcile_folded_image_to_ray_convergence`` as a method right after
     ``_apply_folded_display_bend`` in the same file.
  3. In ``_build_preview_system_rays_bundle``, right after the ``_apply_folded_display_bend``
     call, add (inside ``if folded_trace_rows is not None:``):
         if straight_equivalent_fold_transform is not None:
             self._reconcile_folded_image_to_ray_convergence(scene_bundle)
  4. Open the two-mirror AZ85 scene in-app; the cone should terminate SHARPLY on the detector.
  5. ``git checkout KrakenOS/UI/services/three_d_scene_tools.py`` to revert after eyeballing.

Headless self-check (no app): ``.devenv/state/venv/bin/python bugs/probe_0217_reconcile_prototype.py``
re-applies the post-pass to the live editor via a wrapper and asserts the two-mirror focuses +
single-mirror is a no-op -- WITHOUT editing the source (so it always runs clean).
"""
from __future__ import annotations

import contextlib
import io

import numpy as np

# ---- the gate constants (module-level in three_d_scene_tools.py) ----
_FOLDED_FOCUS_MIN_RAYS = 8
_FOLDED_FOCUS_AXIAL_LAUNCH_MM = 1.0
_FOLDED_FOCUS_PLANE_TOL_MM = 5.0
_FOLDED_FOCUS_MIN_OVERSHOOT_MM = 2.0
_FOLDED_FOCUS_MAX_WAIST_MM = 0.1
_FOLDED_FOCUS_WAIST_RATIO = 0.2


def reconcile_folded_image_to_ray_convergence(scene_bundle) -> int:
    """Free-function copy of the prototype method (``self`` unused). See module docstring."""
    if scene_bundle is None:
        return 0
    detectors = [t for t in (getattr(scene_bundle, "targets", None) or []) if getattr(t, "is_detector", False)]
    ray_paths = getattr(scene_bundle, "ray_paths", None) or []
    if not detectors or len(ray_paths) < _FOLDED_FOCUS_MIN_RAYS:
        return 0
    anchor = detectors[0]
    try:
        ref = np.asarray(anchor.center_world, dtype=float).reshape(3)
        axis = np.asarray(anchor.normal_world, dtype=float).reshape(3)
    except Exception:
        return 0
    axis_norm = float(np.linalg.norm(axis))
    if axis_norm < 1e-9 or not (np.all(np.isfinite(ref)) and np.all(np.isfinite(axis))):
        return 0
    axis = axis / axis_norm

    polys: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    for path in ray_paths:
        pw = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 2 or pw.shape[1] < 3:
            continue
        if float(np.linalg.norm(pw[0, :3])) > _FOLDED_FOCUS_AXIAL_LAUNCH_MM:
            continue
        end = pw[-1, :3]
        if abs(float((end - ref) @ axis)) > _FOLDED_FOCUS_PLANE_TOL_MM:
            continue
        polys.append(pw)
        ends.append(end)
    if len(polys) < _FOLDED_FOCUS_MIN_RAYS:
        return 0
    ends_arr = np.asarray(ends, dtype=float)
    if float(np.mean((ends_arr - ref) @ axis)) < 0.0:
        axis = -axis

    legs: list[np.ndarray] = []
    for pw in polys:
        proj = pw[:, :3] @ axis
        start = len(proj) - 1
        while start > 0 and proj[start - 1] <= proj[start] + 1e-9:
            start -= 1
        leg_pw = pw[start:, :3]
        if leg_pw.shape[0] >= 2:
            legs.append(leg_pw)
    if len(legs) < _FOLDED_FOCUS_MIN_RAYS:
        return 0

    u = np.cross(axis, np.eye(3)[int(np.argmin(np.abs(axis)))])
    u = u / max(float(np.linalg.norm(u)), 1e-12)
    v = np.cross(axis, u)

    def _spread(s: float):
        c = ref + s * axis
        hits: list[np.ndarray] = []
        for leg_pw in legs:
            sd = (leg_pw - c) @ axis
            for i in range(len(sd) - 1):
                if sd[i] * sd[i + 1] <= 0 and abs(sd[i + 1] - sd[i]) > 1e-9:
                    t = -sd[i] / (sd[i + 1] - sd[i])
                    hits.append(leg_pw[i] + t * (leg_pw[i + 1] - leg_pw[i]))
                    break
        if len(hits) < _FOLDED_FOCUS_MIN_RAYS:
            return 1e18, None
        a = np.asarray(hits, dtype=float)
        ctr = a.mean(0)
        return float(np.sqrt((((a - ctr) @ u) ** 2 + ((a - ctr) @ v) ** 2).mean())), ctr

    endpoint_rms, _ = _spread(0.0)
    if not np.isfinite(endpoint_rms):
        return 0
    leg_span = float(np.max([float(np.ptp(lp @ axis)) for lp in legs]))
    best = (1e18, 0.0, None)
    for s in np.linspace(-max(leg_span, 1.0), _FOLDED_FOCUS_PLANE_TOL_MM, 700):
        rms, ctr = _spread(float(s))
        if rms < best[0]:
            best = (rms, float(s), ctr)
    waist_rms, waist_s, waist_ctr = best
    overshoot = -waist_s
    if (
        waist_ctr is None
        or overshoot < _FOLDED_FOCUS_MIN_OVERSHOOT_MM
        or waist_rms > _FOLDED_FOCUS_MAX_WAIST_MM
        or waist_rms > _FOLDED_FOCUS_WAIST_RATIO * max(endpoint_rms, 1e-9)
    ):
        return 0

    plane_pt = np.asarray(waist_ctr, dtype=float)
    for path in ray_paths:
        pw = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 2 or pw.shape[1] < 3:
            continue
        if abs(float((pw[-1, :3] - ref) @ axis)) > _FOLDED_FOCUS_PLANE_TOL_MM:
            continue
        a, b = pw[-2, :3], pw[-1, :3]
        d = b - a
        dn = float(d @ axis)
        if abs(dn) < 1e-9:
            continue
        t = float((plane_pt - a) @ axis) / dn
        if t <= 0.0:
            continue
        new_pw = pw.copy()
        new_pw[-1, :3] = a + t * d
        path.points_world = new_pw
    moved = 0
    shift = waist_s * axis
    for target in detectors:
        try:
            target.center_world = np.asarray(target.center_world, dtype=float).reshape(3) + shift
            moved += 1
        except Exception:
            continue
    return moved


def _selfcheck() -> int:
    from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import (
        _build_single_mirror,
        _build_two_mirror,
    )

    def _run(builder, name, expect_move):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor, _ = builder()
            system, rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
        moved = reconcile_folded_image_to_ray_convergence(bundle)
        det = next((np.asarray(t.center_world, float).reshape(3) for t in bundle.targets if getattr(t, "is_detector", False)), None)
        print(f"{name}: moved={moved} (expect {'>0' if expect_move else '0'})  detector={None if det is None else [round(float(x),2) for x in det]}")

    _run(_build_single_mirror, "SINGLE-MIRROR", expect_move=False)
    _run(_build_two_mirror, "TWO-MIRROR (0217)", expect_move=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(_selfcheck())
