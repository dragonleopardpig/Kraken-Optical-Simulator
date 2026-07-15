"""Guard: an imported camera STEP is oriented with its lens MOUNT toward the beam
(bugs/0308).

Reported (recording flag_20260715_075742_676): "Imported camera is reversed in
direction." The BC-OM25M12X2 vendor body imported back-to-front -- its C/M58 lens
mount (the bore that should face the imaging lens) pointed downstream, so the
sensor plane sat on the wrong face.

Root cause: the camera overlay was seated with a FIXED ``front_face="max"`` in two
places -- the display transform (``_transformed_imported_camera_step_mesh``) and
the export/snap params (``_step_alignment_affine`` via the camera params builder).
"max" happens to be the mount end for the Allied Vision hr25MCX (native max-z bore)
but is the WRONG end for BC-OM25M, whose mount is at native min-z. A fixed side can
only ever be right for half the vendor bodies.

Fix (general, no per-vendor hardcoding): ``_camera_step_mount_front_face`` reads the
geometry -- a lens mount is a circular bore, so that end's CENTRE is hollow (few
points near the optical axis). It compares the "central fraction" (points with
r < 0.25*rmax inside a 12%-span end slab) of each native-z end and seats the
emptier (bored) end toward the beam. Both the display and the export resolve the
same way: the export params emit ``front_face="auto"`` and ``_step_alignment_affine``
resolves it through the same detector, so the STEP export matches the display
(bugs/0300 invariant: export uses the SAME transform as the display).

This guard is DISPLAY-FREE and portable:
  * A -- synthetic bore meshes (pure point clouds): a body with a hollow mount ring
    at native min-z reads "min"; reflected in z it reads "max"; a body solid at both
    ends (no readable bore) and an ambiguous body both fall back to the default. This
    exercises the REAL production ``_camera_step_mount_front_face`` and proves it is
    symmetric, not hardcoded to a side.
  * B (fail-before/pass-after) -- the display build consults the detector and no
    longer hardcodes ``front_face="max"``.
  * C (fail-before/pass-after) -- the camera export params emit ``front_face="auto"``
    and ``_step_alignment_affine`` resolves "auto" through the same detector.
  * D -- the detector is reachable across the mixin boundary on the composed editor
    (the export mixin calls a method defined on the display mixin).
  * E -- real vendor caches (skip-if-absent): BC-OM25M -> "min", hr25MCX -> "max".

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_camera_mount_orientation

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import glob
import inspect
import os

import numpy as np

try:  # pyvista is a hard dependency of the app; the point-cloud checks need it.
    import pyvista as pv
except Exception:  # pragma: no cover - environment without pyvista
    pv = None


_BC_OM25M_CACHE_GLOB = "attachment/cad_cache/BC-OM25M*.analytic.v2.vtp"
_HR25_CACHE_GLOB = "attachment/cad_cache/*HR25*CXP*.analytic.v2.vtp"


class _Shim:
    """Minimal stand-in so the real (unbound) detector can run display-free."""

    def append_debug(self, *_a, **_k):
        return None


def _synthetic_camera_points(mount_at_min: bool, *, solid_both: bool = False,
                             seed: int = 0) -> "pv.PolyData":
    """A camera-like point cloud: a solid body + a solid electronics cap at one end
    and a hollow (bored) lens-mount ring at the other. The detector only reads
    ``mesh.points``, so a pure point cloud exercises it exactly.

    ``mount_at_min`` puts the bore at native min-z; the reflected build puts it at
    max-z. ``solid_both`` caps BOTH ends (no readable bore) to prove the detector
    stays conservative and falls back to the default.
    """
    rng = np.random.default_rng(seed)
    n = 4000
    # Solid body: a full disc (r<=30, incl. the axis) across z in [8, 40].
    zb = rng.uniform(8.0, 40.0, n)
    rb = 30.0 * np.sqrt(rng.uniform(0.0, 1.0, n))
    tb = rng.uniform(0.0, 2.0 * np.pi, n)
    body = np.column_stack([rb * np.cos(tb), rb * np.sin(tb), zb])
    # Solid electronics cap at the far (non-mount) end z = 40: a dense filled disc
    # including the axis -> a HIGH central fraction there.
    m = 2000
    rc = 30.0 * np.sqrt(rng.uniform(0.0, 1.0, m))
    tc = rng.uniform(0.0, 2.0 * np.pi, m)
    cap = np.column_stack([rc * np.cos(tc), rc * np.sin(tc), np.full(m, 40.0)])
    parts = [body, cap]
    # Mount bore ring at z in [0, 8]: an annulus 16 <= r <= 20, empty centre.
    k = 2000
    zr = rng.uniform(0.0, 8.0, k)
    if solid_both:
        # Fill the near end too (solid) -> no readable bore at either end.
        rr = 30.0 * np.sqrt(rng.uniform(0.0, 1.0, k))
    else:
        rr = rng.uniform(16.0, 20.0, k)
    tr = rng.uniform(0.0, 2.0 * np.pi, k)
    ring = np.column_stack([rr * np.cos(tr), rr * np.sin(tr), zr])
    parts.append(ring)
    pts = np.vstack(parts)
    if not mount_at_min:
        pts[:, 2] = float(pts[:, 2].max()) - pts[:, 2]
    return pv.PolyData(pts)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin
    from KrakenOS.UI.services.optical_solid_workflow import LayoutOpticalSolidWorkflowMixin

    detect = LayoutPolylineDisplayMixin._camera_step_mount_front_face
    shim = _Shim()

    # --- A. synthetic bore geometry -- the detector reads the mount end ----------
    if pv is None:
        skip("A: pyvista unavailable -- cannot build synthetic point clouds")
    else:
        face_min = detect(shim, _synthetic_camera_points(mount_at_min=True), default="max")
        ok(face_min == "min",
           f"A1: a hollow mount bore at native MIN-z is seated toward the beam "
           f"(front_face={face_min!r}, expected 'min')")

        face_max = detect(shim, _synthetic_camera_points(mount_at_min=False), default="min")
        ok(face_max == "max",
           f"A2 (symmetry -- not hardcoded to a side): the SAME body reflected in z, "
           f"bore now at MAX-z, seats the max face toward the beam "
           f"(front_face={face_max!r}, expected 'max')")

        face_solid = detect(shim, _synthetic_camera_points(mount_at_min=True, solid_both=True),
                            default="max")
        ok(face_solid == "max",
           f"A3 (conservative): a body solid at BOTH ends has no readable bore, so the "
           f"detector keeps the caller's default (front_face={face_solid!r}, expected 'max')")
        face_solid2 = detect(shim, _synthetic_camera_points(mount_at_min=True, solid_both=True),
                             default="min")
        ok(face_solid2 == "min",
           f"A4 (conservative): the same unreadable body honours a 'min' default too "
           f"(front_face={face_solid2!r}, expected 'min') -- it never invents an orientation")

        # A degenerate/too-small cloud must not raise and must keep the default.
        tiny = pv.PolyData(np.zeros((4, 3), dtype=float))
        face_tiny = detect(shim, tiny, default="max")
        ok(face_tiny == "max",
           f"A5 (robust): a degenerate cloud keeps the default without raising "
           f"(front_face={face_tiny!r})")

    # --- B. the DISPLAY build consults the detector -----------------------------
    build_src = inspect.getsource(
        LayoutPolylineDisplayMixin._transformed_imported_camera_step_mesh
    )
    ok("_camera_step_mount_front_face(" in build_src,
       "B1 (fail-before/pass-after): the camera display build resolves the mount end "
       "via _camera_step_mount_front_face (was a fixed side)")
    ok("front_face=front_face" in build_src,
       "B2: the display alignment uses the RESOLVED front_face variable")
    ok('front_face="max"' not in build_src and "front_face='max'" not in build_src,
       "B3: the display build no longer hardcodes front_face=\"max\" (the reversed line is gone)")

    # --- C. the EXPORT resolves the SAME way (bugs/0300 -- export == display) ----
    class_src = inspect.getsource(LayoutOpticalSolidWorkflowMixin)
    ok('"front_face": "auto"' in class_src,
       "C1 (fail-before/pass-after): the camera export params emit front_face=\"auto\" "
       "(was \"max\")")
    affine_src = inspect.getsource(LayoutOpticalSolidWorkflowMixin._step_alignment_affine)
    ok('front_face == "auto"' in affine_src,
       "C2: _step_alignment_affine recognises the \"auto\" sentinel")
    ok("_camera_step_mount_front_face(" in affine_src,
       "C3: _step_alignment_affine resolves \"auto\" through the SAME detector the display "
       "uses -- so the STEP export orientation matches the display")

    # --- D. cross-mixin resolution on the composed editor -----------------------
    # _step_alignment_affine (export mixin) calls self._camera_step_mount_front_face,
    # which lives on the DISPLAY mixin -- so the composed editor must expose it.
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    except Exception as exc:  # pragma: no cover - headless import guard
        skip(f"D: could not import KrakenLayoutEditor ({type(exc).__name__}: {exc})")
    else:
        resolved = getattr(KrakenLayoutEditor, "_camera_step_mount_front_face", None)
        ok(resolved is LayoutPolylineDisplayMixin.__dict__["_camera_step_mount_front_face"],
           "D1: the composed editor exposes _camera_step_mount_front_face (the export mixin's "
           "self-call into the display mixin resolves)")

    # --- E. real vendor caches (skip-if-absent, non-portable) -------------------
    if pv is None:
        skip("E: pyvista unavailable -- cannot read the vendor STEP caches")
    else:
        bc = sorted(glob.glob(_BC_OM25M_CACHE_GLOB))
        if bc:
            try:
                face = detect(shim, pv.read(bc[-1]), default="max")
                ok(face == "min",
                   f"E1: the real BC-OM25M camera (mount bore at native min-z) seats 'min' "
                   f"toward the beam (front_face={face!r}) -- the flag_20260715_075742 body")
            except Exception as exc:  # pragma: no cover
                skip(f"E1: could not read the BC-OM25M cache ({type(exc).__name__}: {exc})")
        else:
            skip("E1: no BC-OM25M analytic cache on disk (gitignored attachment; regenerated on load)")

        hr = sorted(glob.glob(_HR25_CACHE_GLOB))
        if hr:
            try:
                face = detect(shim, pv.read(hr[-1]), default="max")
                ok(face == "max",
                   f"E2 (no regression): the Allied Vision hr25MCX (mount bore at native max-z) "
                   f"still seats 'max' (front_face={face!r}) -- the vendor the fixed side got right")
            except Exception as exc:  # pragma: no cover
                skip(f"E2: could not read the hr25MCX cache ({type(exc).__name__}: {exc})")
        else:
            skip("E2: no hr25MCX analytic cache on disk (gitignored attachment; regenerated on load)")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Camera mount-orientation validation passed.")
        return 0
    print("Camera mount-orientation validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
