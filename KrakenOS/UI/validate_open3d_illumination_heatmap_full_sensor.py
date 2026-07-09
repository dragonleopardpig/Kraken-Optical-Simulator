"""bugs/0277 -- the coaxial-LED relative-illumination heatmap must (1) fill the sensor to the
RIM and (2) show 2 dark fold edges + 2 UNIFORM perp edges, not "4 dark edges".

flag_20260709_114618_526 (a direct follow-up to 0276): after 0276 pinned the heatmap WINDOW to the
vendor-camera sensor override, two defects remained. The draped quad stopped half-a-bin short of
the orange sensor square (a ~1.2 mm dark rim gap: the quad vertices sat at bin CENTRES, so the
outermost point was half a bin inside the window). And the UNIFORM (over-filled) perp axis speckled
DARK at the sparse coaxial ray density -- only ~800 rays land in the 39x39 FOV, so the old 16-bin
floor forced ~3 hits/bin (30%+ Poisson noise) and the perp edge read dark, so all 4 edges looked
dark instead of the wanted 2.

Fixes: pin the quad's OUTER vertices to the window edges (full-rim coverage,
``source_illumination_overlay``); drop the adaptive bin floor 16 -> 10 (``three_d_scene_tools``) and
raise the de-speckle sigma 1.0 -> 1.5 so the well-populated bins read the true smooth gradient.

Checks (display-free; numpy + one headless trace, no VTK/Tk), reusing the 0276 fixture:
  * FULL-SENSOR -- the overlay quad reaches the sensor rim (half ~= 19.5 mm, NOT the bin-centre
    ~18.3 mm), so there is no dark gap between the heatmap and the orange square.
  * 2-DARK/2-UNIFORM -- the fold edge stays dark (<= 0.85) while the perp edge reads uniform
    (>= 0.85) with clear separation, at the sparse coaxial density where the old params speckled.
"""
from __future__ import annotations

import os

import numpy as np

from KrakenOS.UI.validate_open3d_illumination_heatmap_override import _build_override_only_overlay

# Same diffuse-scatter budget as the 0276 guard: the sparse regime where the old 16-bin floor
# speckled the perp axis dark. Post-fix this lands perp ~1.08 -- comfortably clear of the 0.85 bar.
_TRACE_RAYS = int(os.environ.get("HEATMAP_FULL_SENSOR_RAYS", os.environ.get("HEATMAP_OVERRIDE_RAYS", "8000")) or "8000")

# The fold edge must be this dark or darker; the perp edge this uniform or brighter (phase 175 bar).
_DARK_BAR = 0.85
_UNIFORM_BAR = 0.85
# Clear 2-dark/2-uniform separation so a scene that reads BOTH edges dark (the flag) fails.
_SEPARATION = 0.08
# The quad half must sit within this of the sensor half: catches the ~1.2 mm bin-centre gap.
_RIM_TOL_MM = 0.6


def _check_full_sensor(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle, det_index, fov = _build_override_only_overlay(_TRACE_RAYS)
    if editor is None:
        notes.append("SKIP full-sensor: coaxial-LED fixture unavailable")
        return
    half_sensor = 0.5 * float(fov)

    try:
        spec = editor.source_illumination_overlay_spec(system, bundle)
    except Exception as exc:
        failures.append(f"FULL-SENSOR: source_illumination_overlay_spec raised {exc!r}")
        return
    if not spec:
        failures.append("FULL-SENSOR: overlay spec is None on the override-only fixture")
        return

    # --- FULL-SENSOR: the quad must reach the sensor rim, not stop half-a-bin short. ---
    pts = np.asarray(spec["points"], dtype=float)
    center = np.asarray(spec["center"], dtype=float)
    u = np.asarray(spec["tangent"], dtype=float)
    v = np.asarray(spec["bitangent"], dtype=float)
    half = max(float(np.max(np.abs((pts - center) @ u))), float(np.max(np.abs((pts - center) @ v))))
    if half < half_sensor - _RIM_TOL_MM:
        failures.append(
            f"FULL-SENSOR: quad half {half:.2f} mm stops short of the {half_sensor:.2f} mm sensor rim "
            f"-- the bin-centre gap regressed (vertices not pinned to the window edges)"
        )
    if half > half_sensor + _RIM_TOL_MM:
        failures.append(
            f"FULL-SENSOR: quad half {half:.2f} mm overruns the {half_sensor:.2f} mm sensor rim"
        )

    # --- 2-DARK/2-UNIFORM: fold dark, perp uniform, at the sparse density that used to speckle. ---
    fold = float(spec["x_edge_ratio"])
    perp = float(spec["y_edge_ratio"])
    if fold > _DARK_BAR:
        failures.append(f"2-DARK/2-UNIFORM: fold edge {fold:.3f} is not dark (> {_DARK_BAR})")
    if perp < _UNIFORM_BAR:
        failures.append(
            f"2-DARK/2-UNIFORM: perp edge {perp:.3f} speckled DARK (< {_UNIFORM_BAR}) -- the "
            f"'4 dark edges' regression (bin floor / smoothing sigma reverted?)"
        )
    if not (fold < perp - _SEPARATION):
        failures.append(
            f"2-DARK/2-UNIFORM: fold {fold:.3f} not clearly darker than perp {perp:.3f} "
            f"(need fold < perp - {_SEPARATION})"
        )

    notes.append(
        f"full-sensor: {_TRACE_RAYS} rays -> quad half {half:.2f} mm (sensor {half_sensor:.2f}), "
        f"fold {fold:.3f} <= {_DARK_BAR} dark, perp {perp:.3f} >= {_UNIFORM_BAR} uniform"
    )


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    _check_full_sensor(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    ok, messages = run_checks()
    for line in messages:
        print(("PASS " if ok else "") + line)
    print("RESULT:", "pass" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
