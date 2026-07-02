"""Display-free guard for bugs/0207: on the folded AZ85 RA-mirror the drawn lens/detector
chain must COINCIDE with where the reflected display rays actually land -- the rays must
reach the image plane / detector, not stop ~desp_z short of it.

The user flagged the working folded AZ85 scene (flag_20260702_183320_903):

    "the ray not reaching the image plane or detector."

Root cause: the bugs/0205 fix folds the display RAYS by REFLECTING the straight-equivalent
bundle about the mirror-face CENTRE (the '/' hypotenuse at Z=71.897) -- physically correct,
so the on-axis focus lands at the reflected image. But the drawn downstream chain (lenses,
camera, image plane, overlays) is folded onto the exit frame from
``_reflected_frame_from_interaction_face``, which added the FULL sequential mirror thickness
BEYOND the reflection hit. The hit sits ``desp_z`` (12.5 mm) past the row's front station, so
that pre-hit run was double-counted: the whole folded chain was drawn ``desp_z`` further along
+X than where the rays land. The reflected rays therefore terminated ~12.5 mm SHORT of the
drawn image plane -- a visible gap between the ray tips and the detector.

Fix (bugs/0207): ``_reflected_frame_from_interaction_face`` adds only the REMAINING thickness
after the hit (``thickness - pre_hit_run``), so the exit frame -- and the whole folded chain
that hangs off it -- lands exactly on the reflected rays.

Asserts (display-free, on the live AZ85 editor), AS-LOADED and AFTER snap-to-image-plane:
  1. the drawn detector (last-row reference) X coincides with the on-axis reflected ray
     endpoint X (gap < 0.05 mm) -- the rays reach the detector;
  2. EVERY folded downstream row's drawn X coincides with the on-axis ray's crossing there
     (max |gap| < 0.05 mm) -- the whole lens chain is aligned with the rays, not just the
     detector (so a partial fix that only moved the image plane is caught);
  3. the on-axis outgoing arm stays on the folded optical axis (Z = mirror-face centre,
     71.897 mm; gap < 0.05 mm) -- the bugs/0205 on-axis registration is preserved (no
     transverse offset reintroduced).

A revert of the fix (adding the full mirror thickness beyond the hit again) redraws the
whole folded chain +desp_z along +X, which (1) and (2) both catch.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_rays_reach_detector

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

_AXIS_Z = 71.897137  # folded optical axis Z = the '/' hypotenuse (mirror-face centre)
_TOL = 0.05


def _onaxis(bundle) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    for path in (getattr(bundle, "ray_paths", None) or []):
        pw = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 2 or pw.shape[1] < 3:
            continue
        if float(np.linalg.norm(pw[0][:3])) <= 1.0 and float(pw[:, 0].max()) > 250.0:
            out.append(pw)
    return out


def _outgoing_ray_vertices_x(onaxis: list[np.ndarray]) -> np.ndarray:
    """Sorted X of the on-axis ray's OUTGOING (past-mirror, X>5) vertices -- one per folded
    surface crossing, so they should line up 1:1 with the drawn outgoing-row X's."""
    if not onaxis:
        return np.empty(0)
    xs = onaxis[0][:, 0]
    return np.sort(xs[xs > 5.0])


def _detector_and_chain(editor):
    system, _rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    onaxis = _onaxis(bundle)
    n = len(editor.rows)
    drawn_x = float(
        np.asarray(editor._surface_reference_world_point(n - 1, system=system), dtype=float).reshape(3)[0]
    )
    # sorted drawn X of every outgoing follower row (past the mirror)
    drawn_chain = np.sort(
        np.asarray(
            [
                float(np.asarray(editor._surface_reference_world_point(i, system=system), dtype=float).reshape(3)[0])
                for i in range(2, n)
            ],
            dtype=float,
        )
    )
    ends = np.asarray([p[-1][:3] for p in onaxis], dtype=float) if onaxis else np.empty((0, 3))
    return drawn_x, drawn_chain, onaxis, ends


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor = _build_editor(_AZ85)

            for tag in ("as-loaded", "after-snap"):
                if tag == "after-snap":
                    editor.snap_detector_to_image_plane()
                drawn_x, drawn_chain, onaxis, ends = _detector_and_chain(editor)
                ray_chain = _outgoing_ray_vertices_x(onaxis)
                if len(onaxis) < 6 or ends.size == 0:
                    failures.append(f"[{tag}] too few on-axis folded rays ({len(onaxis)})")
                    continue
                end_x = float(ends[:, 0].mean())
                end_z = float(ends[:, 2].mean())

                # (1) rays reach the drawn detector
                gap = drawn_x - end_x
                if abs(gap) > _TOL:
                    failures.append(
                        f"[{tag}] rays do NOT reach the detector: on-axis end X {end_x:.3f} vs drawn "
                        f"detector X {drawn_x:.3f} (gap {gap:+.3f} mm; ~+desp_z is the 0207 defect)"
                    )
                # (2) the WHOLE chain is aligned, not just the detector: sorted drawn outgoing-row
                #     X's match the on-axis ray's outgoing vertex X's 1:1
                worst = float("inf")
                if drawn_chain.size and ray_chain.size == drawn_chain.size:
                    worst = float(np.max(np.abs(drawn_chain - ray_chain)))
                if not (worst <= _TOL):
                    failures.append(
                        f"[{tag}] folded lens chain off the rays: drawn rows {np.round(drawn_chain,2).tolist()} "
                        f"vs ray crossings {np.round(ray_chain,2).tolist()} (worst |gap| {worst:.3f} mm)"
                    )
                # (3) on-axis registration preserved (no transverse offset)
                if abs(end_z - _AXIS_Z) > _TOL:
                    failures.append(
                        f"[{tag}] on-axis arm OFF the folded axis: Z {end_z:.3f} vs {_AXIS_Z:.3f} "
                        f"(dZ {end_z-_AXIS_Z:+.3f}; a 0205 transverse-offset regression)"
                    )
                if abs(gap) <= _TOL and worst <= _TOL and abs(end_z - _AXIS_Z) <= _TOL:
                    notes.append(
                        f"[{tag}] rays reach the detector: end X {end_x:.3f} == drawn X {drawn_x:.3f} "
                        f"(gap {gap:+.3f}); chain aligned (worst {worst:.3f} mm); on-axis Z {end_z:.3f}"
                    )
    except Exception as exc:  # noqa: BLE001
        return False, [f"setup raised {exc!r}"]

    if failures:
        return False, failures + [f"note: {n}" for n in notes]
    return True, notes


def main() -> int:
    ok, notes = run_checks()
    if ok:
        print("PASS bugs/0207 folded RA-mirror rays reach the detector:")
    else:
        print("FAIL bugs/0207 folded RA-mirror rays reach the detector:")
    for note in notes:
        print(f"  - {note}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
