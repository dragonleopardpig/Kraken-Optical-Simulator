"""bugs/0292 -- "Effective Illumination area bounds the imaging FOV" through the PRODUCTION overlay.

The user's ask: launch the imaging FOV from the folded LED's EFFECTIVE illumination area (fold axis
55*cos45 = 38.9 mm, perp 74 mm) instead of the 39x39 imaging-lens FOV, so the 2 fold-axis dark edges
appear on the sensor.

The folded flood cannot be traced through to foreshorten (a split branch ray never consults the later
limiting aperture -- the 0287/0289 engine wall), so the effective area is built GEOMETRICALLY from a
coaxial-illuminator DESCRIPTOR attached to the LED spec (as add_illumination_led_source does), then imaged
onto the sensor by the existing bugs/0288 ``project_footprint_onto_sensor`` using the REAL scene's own |m|
and sensor size.  This probe drives that whole production path end-to-end on the real vendor scene and
checks for 2 fold-dark edges + uniform perp.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u -m bugs.diag_effective_illum
"""
from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

import bugs.diag_0289_side_led_probe as probe  # reuse the vendor-scene loader / build / trace scaffolding

# The 55x74 side LED with a coaxial-illuminator descriptor attached -- exactly what
# add_illumination_led_source records: RAW aperture (fold 55, perp 74) + fold angle (45), NOT a
# pre-computed 38.9. The overlay foreshortens the fold axis itself (55*cos45 = 38.9). A small ray budget
# is enough: the coaxial overlay is geometric and does not depend on the flood density.
COAXIAL_LED = dict(probe.SIDE_LED)
COAXIAL_LED.update(
    {
        "ray_count": 400,
        "coaxial_illuminator": True,
        "coaxial_aperture_fold_mm": 55.0,
        "coaxial_aperture_perp_mm": 74.0,
        "coaxial_fold_angle_deg": 45.0,
        "coaxial_fold_axis": "x",
    }
)


def _overlay_edges(editor, system, bundle):
    """fold/perp edge-vs-centre ratios of the PRODUCTION detector overlay, or None when it is blank."""
    spec = editor.source_illumination_overlay_spec(system, bundle)
    if not spec:
        return None
    rel = np.asarray(spec["relative"], dtype=float)
    nx, ny = spec["dims"]
    grid = rel.reshape(ny, nx)
    cx, cy = nx // 2, ny // 2
    centre = grid[cy, cx] or 1.0
    fold = (float(grid[cy, 0]) / centre, float(grid[cy, -1]) / centre)  # x = fold axis
    perp = (float(grid[0, cx]) / centre, float(grid[-1, cx]) / centre)  # y = perp axis
    return {
        "spec": spec,
        "fold": fold,
        "perp": perp,
        "fold_mean": float(np.mean(fold)),
        "perp_mean": float(np.mean(perp)),
    }


def evaluate():
    editor = probe._load_editor(with_stop=False)
    editor.layout_scene_source_specs = [dict(COAXIAL_LED)]
    system, bundle = probe._trace(editor)
    mag = abs(float(editor._current_finite_paraxial_magnification()))
    target = editor._source_illumination_anchor_target(bundle)
    hw, hh = editor._detector_target_half_extent(target)
    descriptor = editor._live_coaxial_illuminator_descriptor()
    edges = _overlay_edges(editor, system, bundle)
    return {
        "mag": mag,
        "hw": float(hw),
        "hh": float(hh),
        "fov_half_fold": float(hw) / mag if mag else float("nan"),
        "fov_half_perp": float(hh) / mag if mag else float("nan"),
        "descriptor": descriptor,
        "edges": edges,
    }


def run_checks():
    """(ok, problems) for the penta-validator phase -- the production overlay must draw 2 fold-dark edges
    with a uniform perp axis on the REAL vendor scene, driven purely by the coaxial descriptor."""
    problems: list[str] = []
    try:
        r = evaluate()
    except Exception as exc:  # noqa: BLE001
        return (False, [f"evaluate() raised: {exc!r}"])

    descriptor = r["descriptor"]
    if descriptor is None:
        problems.append("live coaxial descriptor not resolved from the LED spec")
    else:
        fold_eff = descriptor["aperture_fold_mm"] * float(np.cos(np.radians(descriptor["fold_angle_deg"])))
        if not (0.4 * descriptor["aperture_fold_mm"] < fold_eff < descriptor["aperture_fold_mm"]):
            problems.append(f"folded aperture not foreshortened: eff={fold_eff:.2f} of {descriptor['aperture_fold_mm']:.2f}")

    edges = r["edges"]
    if edges is None:
        problems.append("production overlay is None (blank sensor) -- expected the effective-illumination footprint")
        return (False, problems)
    if not (edges["fold_mean"] < 0.85):
        problems.append(f"fold edges not dark: mean={edges['fold_mean']:.3f} (expected < 0.85)")
    if not (edges["perp_mean"] >= 0.85):
        problems.append(f"perp edges not uniform: mean={edges['perp_mean']:.3f} (expected >= 0.85)")
    return (len(problems) == 0, problems)


def main() -> int:
    if not probe.PATH.exists():
        print("fixture missing:", probe.PATH)
        return 1
    r = evaluate()
    print(
        f"REAL vendor scene: |m|={r['mag']:.4f}  sensor half={r['hw']:.2f}x{r['hh']:.2f} mm  "
        f"imaged-FOV half={r['fov_half_fold']:.2f}x{r['fov_half_perp']:.2f} mm"
    )
    print(f"live coaxial descriptor: {r['descriptor']}")
    edges = r["edges"]
    if edges is None:
        print("PRODUCTION OVERLAY: None (blank sensor)")
    else:
        spec = edges["spec"]
        print(
            f"PRODUCTION OVERLAY: dims={spec['dims']}  "
            f"fold edges {edges['fold'][0]:.3f}/{edges['fold'][1]:.3f}  "
            f"perp edges {edges['perp'][0]:.3f}/{edges['perp'][1]:.3f}  min_rel={spec['min_relative']:.3f}"
        )
        if edges["fold_mean"] < 0.85 <= edges["perp_mean"]:
            verdict = "2-SIDED fold-dark (the user's expected pattern)"
        elif edges["fold_mean"] < 0.85 and edges["perp_mean"] < 0.85:
            verdict = "dark on ALL edges"
        else:
            verdict = "UNIFORM (no dark edges)"
        print(f"  => fold={edges['fold_mean']:.3f}  perp={edges['perp_mean']:.3f}  {verdict}")

    ok, problems = run_checks()
    print("CHECKS:", "PASS" if ok else "FAIL")
    for problem in problems:
        print("  -", problem)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
