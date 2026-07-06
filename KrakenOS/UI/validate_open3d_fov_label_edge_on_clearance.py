"""Display-free guard for bugs/0164: the object FOV label must stand clear of the
object plane + ray bundle in the edge-on -YZ view the user works in.

The old code offset the FOV label purely in-plane at clock angle 90deg, which for
the +Z object axis is the -X direction. Looking along X (the -YZ view) that offset
projects to nothing, so the label landed right on the object-plane disc and the rays.

The fix lifts the label along the object-plane normal AWAY from the optics (behind
the object) and adds a +Y vertical component, so it separates both edge-on (in z)
and off the dotted axis (in y). This guard pins:

  * the FOV label is carried BEHIND the object (dot(anchor-obj, img-obj) < 0);
  * edge-on (drop X) it projects clear of the object FOV box (separation in y,z
    exceeds the FOV box half-diagonal) -- the fail-before/pass-after property, since
    the old -X placement projected to ~0 edge-on;
  * the label text is unchanged ("FOV WxH"), an infinite object draws no FOV label,
    and the image-plane labels are still present and lifted.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_fov_label_edge_on_clearance

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.services.detector_coverage_overlay import (
    _basis,
    detector_coverage_label_specs,
    detector_coverage_metrics,
)

# MV150 1X-ish: object at z=0, image at z=595.81; sensor 12.8x12.8, |m|=1 ->
# object FOV 12.8x12.8 (the BC-GN25M12X4 sensor at unit magnification).
_OBJ = np.array([0.0, 0.0, 0.0])
_IMG = np.array([0.0, 0.0, 595.81])
_SENSOR = 12.8
_IMAGE_RADIUS = 9.05


def _fov_label(metrics, finite: bool = True):
    labels = detector_coverage_label_specs(_OBJ, _IMG, metrics, object_mode_finite=finite)
    fov = [l for l in labels if str(l["text"]).startswith("FOV")]
    return labels, (fov[0] if fov else None)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    m = detector_coverage_metrics(_SENSOR, _SENSOR, _IMAGE_RADIUS, 1.0, sensor_is_real=True)
    labels, fov = _fov_label(m)
    if fov is None:
        return False, ["FAIL: finite-object overlay emitted no FOV label at all"]

    anchor = np.asarray(fov["anchor"], dtype=float).reshape(3)
    off = anchor - _OBJ
    axis = _IMG - _OBJ                       # object -> image (+Z, toward optics)
    fov_diag = float(np.hypot(_SENSOR / 2.0, _SENSOR / 2.0))   # FOV box half-diagonal

    # 1) text carries the live dimensions, unchanged by the move.
    if fov["text"] != f"FOV {_SENSOR:.1f}×{_SENSOR:.1f}":
        failures.append(f"FAIL: FOV label text changed (got {fov['text']!r})")

    # 2) the label is carried BEHIND the object (away from the optics/image).
    if float(np.dot(off, axis)) >= 0.0:
        failures.append(
            f"FAIL: FOV label not lifted behind the object (dot(off, axis)={np.dot(off, axis):.3f} >= 0)"
        )

    # 3) edge-on -YZ clearance (drop the X component): the label must project clear
    #    of the object FOV box -- separation in (y, z) exceeds the box half-diagonal.
    #    This is the fail-before/pass-after check: the old -X-only offset projected
    #    to ~0 here.
    edge_on_sep = float(np.hypot(off[1], off[2]))
    if edge_on_sep <= fov_diag:
        failures.append(
            f"FAIL: FOV label edge-on (-YZ) separation {edge_on_sep:.3f} mm does not clear the "
            f"FOV box half-diagonal {fov_diag:.3f} mm (it would overlap the plane + rays)"
        )

    # 3b) bugs/0245: the NORMAL (off-plane) lift must stay CLOSE to the object plane --
    #     a small fraction of the FOV box, NOT the full half-diagonal. The old code lifted
    #     the label ~fov_reach (> half-diagonal) behind the object, which at a large FOV
    #     (55x55) read as "too far from the object plane" (user). The in-plane offset (checked
    #     in #3) still clears the rect; this bounds only the perpendicular float.
    axis_hat = axis / float(np.linalg.norm(axis))
    normal_dist = abs(float(np.dot(off, axis_hat)))
    if normal_dist > fov_diag:
        failures.append(
            f"FAIL: FOV label floats {normal_dist:.3f} mm off the object plane along the normal, "
            f"exceeding the FOV box half-diagonal {fov_diag:.3f} mm (bugs/0245: label too far)"
        )

    # 4) it must NOT sit on the X axis line either (a real vertical component).
    if abs(float(off[1])) < 5.0:
        failures.append(
            f"FAIL: FOV label has no vertical (Y) clearance from the optical axis (|dy|={abs(off[1]):.3f} < 5)"
        )

    # 5) the image-plane labels are unaffected: still present, still lifted off the
    #    image plane along the detector normal (regression guard for the shared func).
    img_labels = [l for l in labels if not str(l["text"]).startswith("FOV")]
    if not any(str(l["text"]).startswith("Sensor") for l in img_labels):
        failures.append(f"FAIL: image-plane Sensor label missing (got {[l['text'] for l in img_labels]})")
    for l in img_labels:
        a = np.asarray(l["anchor"], dtype=float).reshape(3)
        if abs(float(a[2]) - float(_IMG[2])) < 1e-6:
            failures.append(f"FAIL: image label {l['text']!r} not lifted off the image plane (still at z=image)")

    # 5b) the Sensor label sits on the sensor's VERTICAL (right) edge -- +v (= -X) -- not above
    #     the TOP (+u = +Y) where it collided with the spot-map text box. The user flagged the
    #     top placement twice (0deg was the wrong axis: +u is up, not the side); pin the side.
    iu, iv = _basis(_IMG - _OBJ)  # +Z image axis -> iu = +Y (top), iv = -X (right, in-view)
    sensor = next((l for l in img_labels if str(l["text"]).startswith("Sensor")), None)
    if sensor is not None:
        soff = np.asarray(sensor["anchor"], dtype=float).reshape(3) - _IMG
        along_top = float(np.dot(soff, iu))    # +Y (up / top edge)
        along_side = float(np.dot(soff, iv))   # -X (right / vertical edge)
        if abs(along_top) > 1.0 or along_side <= abs(along_top) + 1.0:
            failures.append(
                f"FAIL: Sensor label is not on the sensor's vertical side -- top(+Y)={along_top:.2f} mm, "
                f"side(-X)={along_side:.2f} mm (want side >> top: beside the right edge, not above it)"
            )
        # ...and it must HUG the right edge (half-width), not float out at the corner (half-diagonal):
        # the diagonal radius sat it ~5 mm off the edge (user: "should be JUST beside the orange square").
        if along_side >= m.sensor_half_diagonal:
            failures.append(
                f"FAIL: Sensor label floats off the edge -- side(-X)={along_side:.2f} mm >= half-diagonal "
                f"{m.sensor_half_diagonal:.2f} mm (should hug the ~{m.sensor_half_width:.1f} mm right edge)"
            )

    # 6) an infinite-conjugate object draws no FOV label (object plane has no rect).
    _, inf_fov = _fov_label(m, finite=False)
    if inf_fov is not None:
        failures.append("FAIL: infinite-object overlay drew an FOV label (should be none)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0164 FOV label edge-on clearance")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] object FOV label lifts clear of the object plane + rays in the -YZ view (bugs/0164)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
