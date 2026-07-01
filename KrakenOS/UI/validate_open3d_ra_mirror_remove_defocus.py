"""Display-free guard for bugs/0194: "Remove defocus" (Snap detector to image plane) must
work on the folded AZ85 RA-mirror scene.

The user re-flagged the folded AZ85 after bugs/0192 fixed the reflection: one of the
residual issues was "Defocus at the image" -- the right-click "Snap detector to image
plane (remove defocus)" did nothing, reporting "best focus is not computable".

Root cause: the detector's back-focal gap is set from the optics' best focus, but every
first-order extractor assumes straight +Z propagation. Row 1 is a promoted BK7 mesh MIRROR
(surface=Standard, Solid_3d_stl set, placement desp_z=12.5) that folds the axis 90deg:
  * ``_paraxial_image_plane_z`` -> ``_exact_paraxial_solution_for_rows`` trips its
    "centered refractive systems only" guard on the solid's desp_z -> None;
  * the ``_real_ray_best_focus_shift_for_rows`` fallback keeps the mesh, so PupilCalc
    branches/throws on the 90deg internal reflection -> None.
So snap has no target and bails.

Fix: folding is a RIGID transform, so the unfolded straight sequential system has the
IDENTICAL best-focus back distance. ``_folded_optical_solid_straight_equivalent_rows``
replaces each promoted mesh optical solid with its flat sequential plate (mesh/placement
stripped, curvature/decenter/tilt zeroed, thickness+glass kept), preserving the
cumulative-z frame; ``_paraxial_image_plane_z`` and ``_real_ray_best_focus_shift_for_rows``
evaluate it with ``self.rows`` swapped so the two agree.

This guard asserts, on the live AZ85 editor:
  1. BEFORE (the equivalent-rows helper shadowed to None): both the paraxial image plane
     and the real-ray best-focus are None and snap returns False / "not computable" -- the
     precondition, so the guard is not vacuous;
  2. AFTER (the real helper): the paraxial image plane and the real-ray shift AGREE (~0.1mm)
     and snap moves the back-focal gap by ~+7.76mm onto best focus, then is idempotent;
  3. scope: the sequential flat_mirror scene and a straight-through beam-splitter cube build
     NO flat equivalent (None) -- the fix is inert off the folding-mesh-mirror path
     (bugs/0173's keep-mesh cube snap is untouched).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_remove_defocus

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _build_editor, _AZ85, _PLAIN

_BS_CUBE = "machine_vision_150mm_coaxial_led.py"
_EXPECTED_SHIFT = 7.7557  # paraxial defocus delta on the AZ85 (mm)


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            editor = _build_editor(_AZ85)
            editor._build_preview_system_rays_bundle(update_state=True)
            detector_z = sum(float(r.thickness) for r in editor.rows[:-1])
            base_gap = float(editor.rows[-2].thickness)

            # (1) BEFORE: shadow the equivalent-rows helper so the folded solve has no
            # straight surrogate -> both extractors fail and snap cannot move.
            editor._folded_optical_solid_straight_equivalent_rows = lambda: None
            before_pz = editor._paraxial_image_plane_z()
            before_bf = editor._real_ray_best_focus_shift_for_rows()
            before_moved = editor.snap_detector_to_image_plane()
            before_status = editor.status_var.get()
            before_gap = float(editor.rows[-2].thickness)

            # (2) AFTER: the real helper.
            del editor._folded_optical_solid_straight_equivalent_rows
            equivalent = editor._folded_optical_solid_straight_equivalent_rows()
            after_pz = editor._paraxial_image_plane_z()
            after_bf = editor._real_ray_best_focus_shift_for_rows()
            after_moved = editor.snap_detector_to_image_plane()
            after_status = editor.status_var.get()
            after_gap = float(editor.rows[-2].thickness)
            second_moved = editor.snap_detector_to_image_plane()

        # (1) precondition: BEFORE nothing is computable and snap does not move.
        if before_pz is not None or before_bf is not None:
            failures.append(
                f"AZ85 precondition: BEFORE the folded solve was computable "
                f"(paraxial={before_pz}, real-ray={before_bf}) -- guard vacuous"
            )
        if before_moved is not False or abs(before_gap - base_gap) > 1e-9:
            failures.append(
                f"AZ85 precondition: BEFORE snap moved the detector "
                f"(moved={before_moved}, gap {base_gap:.4f}->{before_gap:.4f}) -- guard vacuous"
            )
        notes.append(f"BEFORE: paraxial={before_pz} real-ray={before_bf} snap={before_moved!r} ({before_status!r})")

        # (2) AFTER: equivalent built, extractors agree, snap moves ~+7.76mm, idempotent.
        if equivalent is None:
            failures.append("AZ85: the real helper built NO flat equivalent for the folding mesh mirror")
        if after_pz is None or after_bf is None:
            failures.append(f"AZ85: AFTER the folded solve is still None (paraxial={after_pz}, real-ray={after_bf})")
        else:
            paraxial_shift = float(after_pz) - float(detector_z)
            if abs(paraxial_shift - float(after_bf)) > 0.2:
                failures.append(
                    f"AZ85: paraxial defocus {paraxial_shift:+.4f}mm and real-ray best focus "
                    f"{float(after_bf):+.4f}mm disagree (>0.2mm) -- the equivalent is inconsistent"
                )
            notes.append(f"AFTER: paraxial defocus {paraxial_shift:+.4f}mm ~ real-ray {float(after_bf):+.4f}mm")
        if after_moved is not True:
            failures.append(f"AZ85: AFTER snap did not move (moved={after_moved}; {after_status!r})")
        applied = after_gap - base_gap
        if abs(applied - _EXPECTED_SHIFT) > 0.2:
            failures.append(
                f"AZ85: snap applied {applied:+.4f}mm, expected ~{_EXPECTED_SHIFT:+.4f}mm "
                f"(gap {base_gap:.4f}->{after_gap:.4f})"
            )
        if second_moved is not False:
            failures.append(f"AZ85: second snap moved again (moved={second_moved}) -- not idempotent at best focus")
        notes.append(
            f"AFTER: snap moved gap {base_gap:.4f}->{after_gap:.4f} ({applied:+.4f}mm); "
            f"second snap moved={second_moved!r} ({after_status!r})"
        )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"AZ85 integration raised {exc!r}")

    # (3) scope: no flat equivalent off the folding-mesh-mirror path.
    for layout, label in ((_PLAIN, "sequential flat mirror"), (_BS_CUBE, "straight-through BS cube")):
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                other = _build_editor(layout)
                other._build_preview_system_rays_bundle(update_state=True)
                equiv = other._folded_optical_solid_straight_equivalent_rows()
            if equiv is not None:
                failures.append(
                    f"regression: {layout} ({label}) built a flat equivalent ({len(equiv)} rows) "
                    f"-- the fix must be inert off the folding-mesh-mirror path"
                )
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{label} scope check raised {exc!r}")

    if failures:
        print("FAIL bugs/0194 folded RA-mirror Remove-Defocus (snap detector to image plane):")
        for line in failures:
            print(f"  - {line}")
        for note in notes:
            print(f"  - note: {note}")
        return 1
    print("PASS bugs/0194 folded RA-mirror Remove-Defocus (snap detector to image plane):")
    print("  - BEFORE the folded best focus is not computable and snap bails; AFTER it snaps to best focus")
    print("  - paraxial image-plane and real-ray best-focus agree; snap is idempotent once at focus")
    print(f"  - scope: {_PLAIN} and {_BS_CUBE} build no flat equivalent (inert off the folding path)")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
