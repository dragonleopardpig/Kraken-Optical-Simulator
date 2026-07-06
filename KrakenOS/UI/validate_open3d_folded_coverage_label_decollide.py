"""Display-free guard for bugs/0241 -- the "Sensor and Image texts overlap" coverage labels.

flag_20260706_130527_037 on the two-fold AZ85: after a 55x55 FOV solve the detector-coverage
labels "Sensor 26.3x26.3" (orange) and "Image circle O32.6" (cyan) printed on top of each other
("Sensor 2Ima6g.3e x2c6ir.3cle O32.6" in the screenshot). Root: the coverage labels are placed at
distinct CLOCK ANGLES in the image PLANE (spanned by ``iu, iv``); that spreads them face-on, but the
user works EDGE-ON (the folded -YZ arm), where one in-plane axis projects to nothing so the clock
spread collapses onto a line and the fixed-screen-size billboards stack on the same spot. Several
angles (Sensor 90deg, Needs 275deg) have a near-zero in-plane ``iu`` component, so they collapse right
onto the detector centre.

Fix: STACK the co-planar image labels along the detector NORMAL (the one axis still visible when the
image plane is edge-on) by a per-label step, ON TOP of the existing clock placement. Face-on the
normal offset is depth-only, so the tuned clock layout is unchanged. Sensor stays at stack 0 so its
tuned right-edge anchor (pinned by validate_open3d_fov_label_edge_on_clearance / bugs/0164) is byte-
identical.

  (A) STACKED ALONG NORMAL: every pair of image-plane labels is separated ALONG the detector normal by
      >= the stack step -- distinct rows. Fail-before: the un-stacked placement shares one normal
      offset (0 mm apart along the normal).
  (B) EDGE-ON SEPARATED: under the user's -YZ projection (drop world X, normal along Z) the min
      pairwise 2-D screen separation clears the label standoff; the un-stacked placement collapses a
      pair to < 2 mm (the Sensor/Needs pile-up).
  (C) SENSOR PINNED: the Sensor anchor is byte-identical to its un-stacked (stack-0) placement -- the
      tuned right-edge placement is preserved.
  (D) FACE-ON PRESERVED: projected onto the image plane (drop the normal component) the labels keep
      their distinct clock positions -- the face-on layout is unchanged.
  (E) TEXT + ORDER: the label texts and their order are unchanged.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_coverage_label_decollide
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.services.detector_coverage_overlay import (
    _LABEL_GAP,
    _LABEL_MARGIN,
    _LABEL_NORMAL_LIFT_FRACTION,
    _LABEL_STACK_MIN_MM,
    _LABEL_STACK_STEP_FRACTION,
    _basis,
    detector_coverage_label_specs,
    detector_coverage_metrics,
)

# The real folded repro pose (from the two-fold probe): the detector sits on the +X arm at a fixed
# Z, its normal along -Z, and the object is off-axis -- so the detector normal is NOT the
# object->image axis (a genuine fold). Looking along X (the -YZ view) collapses world X.
_OBJ = np.array([11.52, 11.52, 0.0])
_IMG = np.array([101.1, 0.0, 93.92])
_NORMAL = np.array([0.0, 0.0, -1.0])


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _image_labels(metrics):
    labels = detector_coverage_label_specs(
        _OBJ, _IMG, metrics, object_mode_finite=True, object_axis=(_IMG - _OBJ), image_axis=_NORMAL
    )
    img = [l for l in labels if not str(l["text"]).startswith("FOV")]
    return labels, img


def _flat_anchor(metrics, radius, angle_deg):
    """The pre-fix (un-stacked) placement: shared normal lift + the clock offset, no per-label step."""
    iu, iv = _basis(_NORMAL)
    n = _NORMAL / float(np.linalg.norm(_NORMAL))
    lift = metrics.sensor_half_diagonal * _LABEL_NORMAL_LIFT_FRACTION + _LABEL_GAP
    center = _IMG + n * lift
    a = np.radians(float(angle_deg))
    return center + radius * (np.cos(a) * iu + np.sin(a) * iv)


def _flat_image_anchors(metrics):
    """Reconstruct the un-stacked anchors for the same labels, in the same order, for fail-before."""
    out = []
    if metrics.sensor_half_width > 1e-9 and metrics.sensor_half_height > 1e-9:
        out.append(("Sensor", _flat_anchor(metrics, metrics.sensor_half_width * (1.0 + _LABEL_MARGIN) + _LABEL_GAP, 90.0)))
    if metrics.image_circle_radius > 1e-9:
        out.append(("Image circle", _flat_anchor(metrics, metrics.image_circle_radius * (1.0 + _LABEL_MARGIN) + _LABEL_GAP, 150.0)))
    if metrics.sensor_is_real and not metrics.covers and metrics.sensor_half_diagonal > 1e-9:
        out.append(("Needs", _flat_anchor(metrics, metrics.sensor_half_diagonal * (1.0 + _LABEL_MARGIN) + _LABEL_GAP, 275.0)))
    return out


def _screen_yz(a):
    """The user's -YZ edge-on projection: camera looks along X, so world X collapses."""
    a = np.asarray(a, dtype=float).reshape(3)
    return np.array([a[1], a[2]])


def _min_pair(vals, key):
    best = float("inf")
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            best = min(best, float(key(vals[i], vals[j])))
    return best


def validate_folded_coverage_label_decollide() -> list[Check]:
    checks: list[Check] = []
    n_hat = _NORMAL / float(np.linalg.norm(_NORMAL))

    # SHORT (image circle < sensor half-diagonal) exercises the worst 3-label case (Sensor + Image +
    # Needs); the screenshot's 26.3 mm sensor with a O32.6 image circle is exactly this.
    short = detector_coverage_metrics(26.3, 26.3, 16.3, -0.5, sensor_is_real=True)
    cover = detector_coverage_metrics(11.3, 11.3, 12.0, -0.5, sensor_is_real=True)  # 2-label covering case
    step = max(short.sensor_half_diagonal * _LABEL_STACK_STEP_FRACTION, _LABEL_STACK_MIN_MM)

    _labels, img = _image_labels(short)
    anchors = [np.asarray(l["anchor"], dtype=float).reshape(3) for l in img]

    # ---- (A) stacked along the detector normal: distinct rows ------------------------------- #
    along_normal = [float(np.dot(a - _IMG, n_hat)) for a in anchors]
    min_normal_sep = _min_pair(along_normal, lambda p, q: abs(p - q))
    flat = _flat_image_anchors(short)
    flat_normal = [float(np.dot(a - _IMG, n_hat)) for _t, a in flat]
    flat_min_normal = _min_pair(flat_normal, lambda p, q: abs(p - q))
    checks.append(Check(
        "STACKED ALONG NORMAL: image labels occupy distinct rows along the detector normal",
        len(img) >= 3 and min_normal_sep >= step - 1e-6 and flat_min_normal < 1e-6,
        f"stacked min normal sep={min_normal_sep:.2f} mm (step={step:.2f}); un-stacked={flat_min_normal:.2f} mm",
    ))

    # ---- (B) edge-on (-YZ, drop world X) separation: fix vs fail-before ---------------------- #
    edge_sep = _min_pair(anchors, lambda p, q: float(np.linalg.norm(_screen_yz(p) - _screen_yz(q))))
    flat_edge_sep = _min_pair([a for _t, a in flat], lambda p, q: float(np.linalg.norm(_screen_yz(p) - _screen_yz(q))))
    checks.append(Check(
        "EDGE-ON SEPARATED: -YZ screen min-sep clears the standoff (un-stacked pile-up did not)",
        edge_sep > 5.0 and flat_edge_sep < 2.0,
        f"stacked edge-on min-sep={edge_sep:.2f} mm; un-stacked min-sep={flat_edge_sep:.2f} mm",
    ))

    # ---- (C) Sensor anchor pinned to its tuned (stack-0) placement --------------------------- #
    sensor = next((l for l in img if str(l["text"]).startswith("Sensor")), None)
    flat_sensor = next((a for t, a in flat if t == "Sensor"), None)
    sensor_pinned = (
        sensor is not None and flat_sensor is not None
        and float(np.linalg.norm(np.asarray(sensor["anchor"], dtype=float).reshape(3) - flat_sensor)) < 1e-9
    )
    checks.append(Check(
        "SENSOR PINNED: the Sensor label keeps its tuned right-edge anchor (bugs/0164)",
        sensor_pinned,
        f"sensor={None if sensor is None else np.round(sensor['anchor'], 2)} flat={None if flat_sensor is None else np.round(flat_sensor, 2)}",
    ))

    # ---- (D) face-on (drop the normal component) keeps the distinct clock spread ------------- #
    def in_plane(a):
        d = np.asarray(a, dtype=float).reshape(3) - _IMG
        return d - np.dot(d, n_hat) * n_hat
    face_sep = _min_pair(anchors, lambda p, q: float(np.linalg.norm(in_plane(p) - in_plane(q))))
    checks.append(Check(
        "FACE-ON PRESERVED: dropping the normal, the labels keep distinct clock positions",
        face_sep > 3.0,
        f"face-on min in-plane sep={face_sep:.2f} mm",
    ))

    # ---- (E) text + order unchanged ---------------------------------------------------------- #
    all_labels, _img2 = _image_labels(short)
    texts = [str(l["text"]) for l in all_labels]
    expected = [
        "Sensor 26.3×26.3",
        "Image circle Ø32.6 (short)",
        "Needs Ø37.2",
        "FOV 52.6×52.6",
    ]
    _cl, cimg = _image_labels(cover)
    cover_ok = len(cimg) == 2 and not any(str(l["text"]).startswith("Needs") for l in cimg)
    checks.append(Check(
        "TEXT + ORDER: label texts + order unchanged; covering case drops 'Needs'",
        texts == expected and cover_ok,
        f"texts={texts}; cover_labels={[l['text'] for l in cimg]}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_coverage_label_decollide()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_coverage_label_decollide()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded coverage-label de-collision validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
