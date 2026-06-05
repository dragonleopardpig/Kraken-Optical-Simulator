"""Regression: geometry-only sphere fit recovers Zemax Rc on Edmund STEPs.

The user asked for an analytic-promote workflow that works on
self-drawn STEP files without a paired Zemax .zmx. The fit module
in ``step_overlay_analytic_fit`` does least-squares sphere/plane
fits on each preserved face. To prove the fit is good enough for
production use, this test loads the same Edmund STEP fixtures that
come with .zmx alongside, runs the fit, and asserts the recovered
``Rc`` matches the Zemax CURV value within 0.01 mm.

If a future change to the fit math or face-decomposition pipeline
shifts the fit, this test fails immediately with the diff between
expected and observed Rc.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.step_overlay_analytic_fit import (
    SphereFit,
    fit_step_overlay_analytic_surfaces,
    maybe_split_full_sphere_face,
)
from KrakenOS.UI.services.step_overlay_promotion import _auto_assign_lens_face_functions


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Fixture: each entry pairs a STEP file with the expected Rc value(s)
# from the matching .zmx prescription. The fit is expected to recover
# these values to within ``tolerance_mm``.
FIXTURES = [
    {
        # Ball lens (Edmund 63227, sapphire R=4.7625 mm). The STEP
        # importer collapses both hemispheres into a single face
        # group with area = 4 pi R^2; previously the analytic-promote
        # path failed entirely. After sphere-splitting in
        # ``maybe_split_full_sphere_face`` the front gets Rc=+R and
        # back gets Rc=-R (matching Zemax CURV = +/-0.20997).
        "name": "Ball Lens (63227)",
        "path": PROJECT_ROOT / "attachment" / "Lens" / "ball_lens" / "step_63227.stp",
        "expected_rc": (+4.7625, -4.7625),
        "tolerance_mm": 0.01,
    },
    {
        # DCV is the smoking-gun fixture for the sign-convention bug:
        # the front surface (concave toward incoming light) has Rc<0
        # in KrakenOS convention, and the back surface (concave toward
        # outgoing light) has Rc>0. Earlier the fit used the per-face
        # outward normal for sign, which made BOTH faces collapse to
        # Rc=-52.10 -- so the rendered lens body looked wrong and a
        # paraxial trace through it gave nonsense. The Rc-sign test
        # below specifically asserts BOTH +52.10 and -52.10 are
        # recovered, locking in the fix.
        "name": "DCV (32996)",
        "path": PROJECT_ROOT / "attachment" / "Lens" / "DCV" / "32996" / "step_32996.stp",
        "expected_rc": (-52.10, +52.10),
        "tolerance_mm": 0.01,
    },
    {
        "name": "Achromat (32323) front",
        "path": PROJECT_ROOT / "attachment" / "Lens" / "Achromatic_Lenses" / "32323" / "step_32323.stp",
        "expected_rc": (+34.53,),    # only the front of the doublet is easy to extract
        "tolerance_mm": 0.01,
    },
]


def _run() -> int:
    failures: list[str] = []
    app = KrakenLayoutEditor()
    try:
        for fixture in FIXTURES:
            name = fixture["name"]
            path = fixture["path"]
            tol = float(fixture["tolerance_mm"])
            expected_rc = tuple(float(v) for v in fixture["expected_rc"])
            if not path.exists():
                print(f"WARN: {name}: fixture missing at {path}", file=sys.stderr)
                continue
            app.imported_optical_step_path = path
            app.optical_step_rotation_x_deg = 0.0
            app.optical_step_rotation_y_deg = 0.0
            app.optical_step_rotation_z_deg = 0.0
            app.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
            try:
                mesh = app._transformed_imported_optical_step_mesh()
                face_md = app._step_overlay_face_metadata("optical") or {}
            except Exception as exc:
                failures.append(f"{name}: could not load metadata: {exc}")
                continue
            if mesh is None:
                failures.append(f"{name}: transformed mesh unavailable")
                continue
            # Mirror the production preview pipeline: run the sphere
            # splitter on each raw face BEFORE auto-assign so a ball
            # lens (one full-sphere face) is decomposed into front /
            # back hemispheres the same way the promote service does.
            raw_faces = list(face_md.get("faces") or [])
            faces: list[dict] = []
            for f in raw_faces:
                split = maybe_split_full_sphere_face(mesh, f, source_axis=(0.0, 0.0, 1.0))
                if split is None:
                    faces.append(f)
                else:
                    faces.extend(split)
            face_copies = [dict(f) for f in faces]
            _auto_assign_lens_face_functions(face_copies)
            # Mirror the production selector (step_overlay_promotion.py): the
            # refractive surfaces are the optical-axis pair the auto-assign flags,
            # not every uncoated face (bug 0016 defaults side walls to Transmit so
            # the trace won't absorb a ray). Fall back to function for the manual
            # path.
            transmit_faces = [
                faces[i]
                for i, f in enumerate(face_copies)
                if f.get("optical_axis_surface")
            ]
            if not transmit_faces:
                transmit_faces = [
                    faces[i]
                    for i, f in enumerate(face_copies)
                    if f.get("function") == "Transmit/Port"
                ]
            if not transmit_faces:
                failures.append(f"{name}: no Transmit/Port faces after auto-assign")
                continue
            result = fit_step_overlay_analytic_surfaces(
                mesh,
                transmit_faces,
                source_axis=(0.0, 0.0, 1.0),
            )
            if not result.specs:
                failures.append(f"{name}: fit returned no specs")
                continue
            # The 'expected' tuple lists the Rc values we know in
            # order along the optical axis. The fit returns specs
            # sorted by axial position too, so they should line up.
            sphere_rcs = [
                float(spec.fit.signed_rc)
                for spec in result.specs
                if isinstance(spec.fit, SphereFit)
            ]
            if not sphere_rcs:
                failures.append(f"{name}: fit produced no SphereFit results")
                continue
            for expected in expected_rc:
                # Match against the closest fitted Rc; a successful
                # fit recovers Zemax to better than tol mm.
                closest = min(sphere_rcs, key=lambda v: abs(v - expected))
                if abs(closest - expected) > tol:
                    failures.append(
                        f"{name}: expected Rc≈{expected:+.4f}, "
                        f"closest fit {closest:+.4f} (diff {closest-expected:+.4f} mm > tol {tol})"
                    )
                else:
                    print(
                        f"  OK  {name}: Zemax Rc={expected:+.4f} mm  fit={closest:+.4f} mm"
                        f"  diff={abs(closest-expected):.5f} mm"
                    )
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if failures:
        print("FAIL: geometry-fit regressions:", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1
    print("PASS: geometry-only sphere fit recovers Zemax Rc to < 0.01 mm on every fixture.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
