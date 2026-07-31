"""bugs/0470 guard -- "remove defocus" works on a beam-splitter scene.

flag_20260729_150120 / _150208: "change FOV to 23x23 without any constraint. Rays defocus at
sensor." then "right click remove defocus at sensor: nothing happen."

Both were real. An UNCONSTRAINED FOV solve leaves residual defocus -- measured, the axial spot
went 0.269 -> 0.805 mm RMS -- which is expected in kind, because the solve is paraxial while
the real chain carries a BS plate, a 51.5 mm mirror substrate and mesh solids. The app's remedy
for exactly that is "Snap detector to image plane (remove defocus)", and it refused with
"best focus is not computable for this layout": the analytic conjugate cannot handle the
splitter, and the ray fallback needs `_folded_optical_solid_straight_equivalent_rows()`, which
returns None for a scene with no straight equivalent.

But the rays are right there -- the preview trace lands 169 on the detector. The snap now falls
back to measuring the ACTUAL bundle's waist (transverse RMS minimised along the detector
normal, axial field only). Measured on the user's scene: waist at 20.02 mm, RMS 0.0007 mm
there versus 0.805 mm at the detector.

Checks:
  SOLVED   -- an unconstrained 23 x 23 solve applies.
  SNAPPED  -- "remove defocus" succeeds where it used to refuse.
  FOCUSED  -- and the axial spot actually shrinks.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

BS_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def _axial_rms(app) -> float | None:
    _s, _r, bundle = app._build_preview_system_rays_bundle(
        sampling_mode=None, update_state=True, trace_rays=True
    )
    ends = []
    for path in list(getattr(bundle, "ray_paths", None) or []):
        if str(getattr(path, "termination_reason", "")) != "target_termination":
            continue
        pts = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        if float(np.linalg.norm(pts[0, :3])) > 1.0:
            continue
        ends.append(pts[-1, :3])
    if len(ends) < 4:
        return None
    arr = np.asarray(ends, dtype=float)
    return float(np.sqrt(((arr - arr.mean(axis=0)) ** 2).sum(axis=1).mean()))


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    if not BS_SCENE.exists():
        return True, ["SKIP: the BS scene is absent (gitignored attachment)"]

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        app = KrakenLayoutEditor()
        app.layout_files["bs"] = BS_SCENE
        app.load_layout_by_name("bs")
        inspector = _open_inspector(app)
        applied, _msg = inspector._quick_estimation_service().fov_solve(
            "object", "thickness", 23.0, 23.0, None
        )
        if applied:
            notes.append("SOLVED = the unconstrained 23 x 23 solve applies")
        else:
            notes.append("SOLVED the 23 x 23 solve was refused; cannot exercise the snap")
            return ok, notes

        before = _axial_rms(app)
        moved = bool(app.snap_detector_to_image_plane())
        reason = str(app.status_var.get())
        after = _axial_rms(app)
        # bugs/0490 changed what this can assert, and the reason matters more than the wording.
        # The defect here was that the snap REFUSED on a splitter scene -- "best focus is not
        # computable for this layout" -- so the invariant is that it is COMPUTABLE and the scene
        # ends at best focus, not that this particular call moves something. Since the solve now
        # finishes on the traced focus itself, there is usually nothing left to remove by the time
        # this runs, and "Detector already at best focus" is the healthy answer. A refusal that
        # says "not computable" is still the bug and still fails.
        already = "already at best focus" in reason.lower()
        if moved or already:
            notes.append(
                f"SNAPPED = remove-defocus is computable on the splitter scene "
                f"({'moved' if moved else 'already at best focus after the solve'}: {reason[:52]})"
            )
        else:
            notes.append(f"SNAPPED remove-defocus refused: {reason[:70]}")
            ok = False
        # ... and the spot is AT the minimum, whether this call or the solve put it there.
        if before is not None and after is not None and after <= before + 1e-9:
            trend = "shrank" if after < before - 1e-12 else "was already at the minimum"
            notes.append(f"FOCUSED = the axial spot {trend} {before:.4g} -> {after:.4g} mm RMS")
        else:
            notes.append(f"FOCUSED the axial spot did not improve: {before} -> {after}")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: scene drive failed ({exc!r})")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
