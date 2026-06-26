"""Display-free guard for bugs/0163: a bare lens (no camera) recommends the
largest sensor that fits INSIDE the image circle, instead of fabricating a square
"Sensor" from its round image aperture and demanding a larger image circle.

With no vendor camera the Image detector's ``active_width_mm`` / ``active_height_mm``
are 0, so the old code filled both from the round clear-aperture diameter and drew
a 93.17x93.17 SQUARE, then reported the image circle "(short)" and asked for a
Ø131.8 ring (the square's diagonal) -- nonsense for a round aperture.

The fix:
  * ``scene_target_has_explicit_sensor`` is False for a no-camera target, so
    ``scene_target_active_footprint_polylines`` returns [] (the square is gone).
  * the coverage overlay recommends the inscribed square (side = R*sqrt(2), corners
    on the circle) with ``sensor_is_real=False`` -- it always covers, so no
    "(short)" / "Needs Ø" framing.
  * a REAL sensor (active dims set) is unchanged: footprint drawn, coverage-vs-
    corners framing kept (an over-large sensor still goes "short" + required ring).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_inscribed_sensor_recommendation

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.scene_geometry import (
    scene_target_active_footprint_polylines,
    scene_target_has_explicit_sensor,
)
from KrakenOS.UI.services.detector_coverage_overlay import (
    detector_coverage_label_specs,
    detector_coverage_metrics,
    detector_coverage_overlay_specs,
    recommended_inscribed_sensor_side,
)

# The Tessar (vignetting factors) numbers the user flagged.
_APERTURE_DIAMETER = 93.17     # round Image clear-aperture diameter
_IMAGE_RADIUS = 42.391         # max real image height -> image circle radius (Ø84.78)


class _Target:
    """Minimal detector target stand-in (no display)."""

    is_detector = True
    center_world = np.array([0.0, 0.0, 207.307])
    normal_world = np.array([0.0, 0.0, 1.0])
    tangent_world = np.array([0.0, 1.0, 0.0])

    def __init__(self, diameter: float, active_w: float = 0.0, active_h: float = 0.0) -> None:
        self.diameter = float(diameter)
        self.active_width_mm = float(active_w)
        self.active_height_mm = float(active_h)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # --- 1) no-camera target: no explicit sensor, footprint square suppressed ---
    bare = _Target(_APERTURE_DIAMETER)
    if scene_target_has_explicit_sensor(bare):
        failures.append("FAIL: no-camera target reported an explicit sensor (should be False)")
    foot = scene_target_active_footprint_polylines(bare)
    if foot:
        failures.append(f"FAIL: no-camera footprint drew {len(foot)} polylines (the misleading square; expected 0)")

    # --- 2) inscribed recommendation: side = R*sqrt(2), corners ON the circle ---
    rec_side = recommended_inscribed_sensor_side(_IMAGE_RADIUS)
    if not np.isclose(rec_side, _IMAGE_RADIUS * np.sqrt(2.0), atol=1e-6):
        failures.append(f"FAIL: inscribed side {rec_side:.4f} != R*sqrt(2) {_IMAGE_RADIUS * np.sqrt(2.0):.4f}")
    m = detector_coverage_metrics(rec_side, rec_side, _IMAGE_RADIUS, None, sensor_is_real=False)
    if not m.covers:
        failures.append("FAIL: inscribed sensor does not 'cover' (its corners should sit on the circle)")
    if m.sensor_is_real:
        failures.append("FAIL: recommended sensor metrics flagged sensor_is_real=True")
    # the inscribed square must NOT exceed the circle (half-diagonal == radius).
    if m.sensor_half_diagonal > _IMAGE_RADIUS + 1e-6:
        failures.append(
            f"FAIL: inscribed half-diagonal {m.sensor_half_diagonal:.4f} exceeds image radius "
            f"{_IMAGE_RADIUS:.4f} (sensor not within the image circle)"
        )

    # --- 3) no-camera specs/labels: recommended rect, no required ring / "short" ---
    obj = np.array([0.0, 0.0, -1.0])
    specs = detector_coverage_overlay_specs(
        obj, _Target(_APERTURE_DIAMETER).center_world, m,
        object_mode_finite=False, image_axis=_Target(_APERTURE_DIAMETER).normal_world,
    )
    kinds = {s["kind"] for s in specs}
    if "recommended_sensor_rect" not in kinds:
        failures.append(f"FAIL: no-camera specs missing recommended_sensor_rect (got {sorted(kinds)})")
    if "required_image_circle" in kinds:
        failures.append("FAIL: no-camera specs drew a required_image_circle ring (the Ø131.8 nonsense)")
    labels = [l["text"] for l in detector_coverage_label_specs(
        obj, _Target(_APERTURE_DIAMETER).center_world, m,
        object_mode_finite=False, image_axis=_Target(_APERTURE_DIAMETER).normal_world,
    )]
    if not any(t.startswith("Max sensor") for t in labels):
        failures.append(f"FAIL: no-camera label is not 'Max sensor ...' (got {labels})")
    if any("(short)" in t for t in labels):
        failures.append(f"FAIL: no-camera image-circle label says '(short)' (got {labels})")
    if any(t.startswith("Needs") for t in labels):
        failures.append(f"FAIL: no-camera drew a 'Needs Ø' label (got {labels})")

    # --- 4) REAL sensor unchanged: footprint drawn, coverage framing kept --------
    real = _Target(_APERTURE_DIAMETER, active_w=36.0, active_h=24.0)
    if not scene_target_has_explicit_sensor(real):
        failures.append("FAIL: real-sensor target not recognised as explicit")
    foot_r = scene_target_active_footprint_polylines(real)
    if len(foot_r) != 3:
        failures.append(f"FAIL: real-sensor footprint drew {len(foot_r)} polylines (expected 3: rect + 2 cross)")

    # an over-large real sensor still goes "short" with a required ring (regression
    # guard: the no-camera branch must not have softened the real-sensor path).
    big = detector_coverage_metrics(140.0, 140.0, _IMAGE_RADIUS, None, sensor_is_real=True)
    if big.covers:
        failures.append("FAIL: a 140x140 sensor should NOT be covered by the Ø84.8 image circle")
    big_specs = {s["kind"] for s in detector_coverage_overlay_specs(obj, real.center_world, big, object_mode_finite=False)}
    if "required_image_circle" not in big_specs:
        failures.append("FAIL: over-large real sensor lost its required_image_circle ring")
    if "recommended_sensor_rect" in big_specs:
        failures.append("FAIL: real-sensor scene drew a recommended_sensor_rect (only bare lenses should)")
    big_labels = [l["text"] for l in detector_coverage_label_specs(obj, real.center_world, big, object_mode_finite=False)]
    if not any(t.startswith("Sensor") for t in big_labels):
        failures.append(f"FAIL: real-sensor label is not 'Sensor ...' (got {big_labels})")
    if not any("(short)" in t for t in big_labels):
        failures.append(f"FAIL: over-large real sensor lost its '(short)' suffix (got {big_labels})")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0163 bare-lens inscribed-sensor recommendation")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] bare lens recommends the inscribed sensor (no fabricated square / Ø ring); real sensors unchanged (bugs/0163)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
