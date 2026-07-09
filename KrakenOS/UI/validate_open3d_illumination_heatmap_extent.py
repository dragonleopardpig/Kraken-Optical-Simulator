"""Display-free guard: the on-detector relative-illumination heatmap window is the SENSOR, not the
round catch DIAMETER (flag_20260709_093800_013 / bugs/0275).

The MV-150 coaxial *folded* scene's return-path detector plane has a 78 mm (2xFOV) clear-aperture
DIAMETER but a 39x39 mm active sensor. ``source_illumination_map_extent`` used to fall back to that
diameter whenever a detector declared no explicit active area, draping a 78x78 mm heatmap -- a square
that spills PAST the image circle and whose symmetric dark border buried the real fold/perp dark-edge
asymmetry (2 dark edges on the fold axis, 2 uniform on the perpendicular). bugs/0163 already ruled
that a detector's round clear-aperture diameter is NOT a sensor size (the orange sensor square is
drawn ONLY from explicit rectangular dims -- ``scene_target_has_explicit_sensor``); this guard holds
the heatmap extent to that same rule so the map lands on the sensor the Monitor shows.

Pins (display-free: pure numpy + one headless trace, no VTK):

  * PURE (``source_illumination_map_extent``): an explicit local sensor (both dims > 0) -> the
    +/-half-sensor window, independent of where the hits landed; a detector with NO explicit dims
    (only a round diameter) does NOT return +/-diameter/2 -- it falls through to the illuminated
    DATA footprint (data min/max + 20% pad); non-local hit coords ignore the sensor window;
    deterministic.
  * LAYOUT (static): the folded coaxial detector surface declares active_width/height = FOV_MM (the
    39x39 sensor -- Fix A), so the in-app anchor pins to +/-19.5 mm; its TRACE diameter stays the
    wider 2xFOV catch aperture (window != aperture).
  * INTEGRATION (clean coaxial-LED fixture): the real overlay quad spans the 39x39 sensor
    (~+/-18 mm bin-centres), NOT the 78 mm catch diameter (half 39), and still reads the fold edge
    darker than the perpendicular edge.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_illumination_heatmap_extent

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import os

import numpy as np

from KrakenOS.UI.source_illumination_analysis import source_illumination_map_extent

# Deterministic (source_seed) trace budget for the integration check. The quad SIZE is
# ray-count-independent for an explicit sensor (the extent is fixed at +/-half); 8000 rays give a
# stable fold-darker-than-perp signal too while keeping the phase quick.
_TRACE_RAYS = int(os.environ.get("HEATMAP_EXTENT_RAYS", "8000"))


def _check_pure_extent(failures: list[str]) -> None:
    local = {"coord": "local"}
    xs = np.array([-5.0, 3.0, 8.0])
    ys = np.array([-4.0, 2.0, 6.0])

    # Explicit 39x39 sensor -> the +/-19.5 mm window, regardless of the (smaller) data spread.
    sensor = {"is_detector": True, "active_width_mm": 39.0, "active_height_mm": 39.0, "diameter_mm": 78.0}
    ext = source_illumination_map_extent(local, xs, ys, sensor)
    if not np.allclose(ext, (-19.5, 19.5, -19.5, 19.5), atol=1e-9):
        failures.append(f"PURE: explicit 39x39 sensor -> {tuple(round(v, 3) for v in ext)} != +/-19.5")

    # Diameter-only detector (no explicit active dims): must NOT span the 78 mm catch aperture
    # (+/-39) -- the flag_20260709_093800_013 regression -- it falls to the illuminated data footprint.
    dia_only = {"is_detector": True, "active_width_mm": 0.0, "active_height_mm": 0.0, "diameter_mm": 78.0}
    xd = np.array([-10.0, 0.0, 11.0])
    yd = np.array([-9.0, 0.0, 8.0])
    ext_d = source_illumination_map_extent(local, xd, yd, dia_only)
    if max(abs(v) for v in ext_d) >= 39.0 - 1e-6:
        failures.append(
            f"PURE: diameter-only detector still spans the 78 mm catch aperture: "
            f"{tuple(round(v, 2) for v in ext_d)}"
        )
    span = max(11.0 - (-10.0), 8.0 - (-9.0))  # pad = 20% of the larger axis span
    want = (-10.0 - 0.2 * span, 11.0 + 0.2 * span, -9.0 - 0.2 * span, 8.0 + 0.2 * span)
    if not np.allclose(ext_d, want, atol=1e-6):
        failures.append(
            f"PURE: diameter-only extent did not fall to the data footprint: "
            f"{tuple(round(v, 2) for v in ext_d)} != {tuple(round(v, 2) for v in want)}"
        )

    # Non-local (world) hit coords are not sensor-local -> the sensor window must be ignored.
    ext_w = source_illumination_map_extent({"coord": "world"}, xs, ys, sensor)
    if np.allclose(ext_w, (-19.5, 19.5, -19.5, 19.5), atol=1e-6):
        failures.append("PURE: world-coord samples wrongly used the +/-19.5 sensor window")

    # No target model at all -> data footprint (never a fixed box).
    ext_none = source_illumination_map_extent(local, xd, yd, None)
    if not np.allclose(ext_none, want, atol=1e-6):
        failures.append(f"PURE: missing target_model did not fall to the data footprint: {tuple(round(v, 2) for v in ext_none)}")

    # Deterministic.
    if source_illumination_map_extent(local, xs, ys, sensor) != ext:
        failures.append("PURE: extent is not deterministic")


def _check_layout_static(failures: list[str]) -> None:
    try:
        from KrakenOS.common_optical_layouts import machine_vision_150mm_coaxial_led_folded as folded
    except Exception as exc:  # pragma: no cover - import guard
        failures.append(f"LAYOUT: folded coaxial layout failed to import ({exc!r})")
        return

    fov = float(getattr(folded, "FOV_MM", 0.0) or 0.0)
    if fov <= 0.0:
        failures.append("LAYOUT: folded layout lost FOV_MM")
        return

    detector_rows = [
        s for s in getattr(folded, "SURFACES", [])
        if isinstance((s.get("advanced") or {}).get("Detector"), dict)
    ]
    if not detector_rows:
        failures.append(
            "LAYOUT: folded coaxial detector declares no explicit active area (Fix A lost) -- "
            "the heatmap will fall back to the 2xFOV catch diameter"
        )
        return
    for surface in detector_rows:
        det = surface["advanced"]["Detector"]
        w = float(det.get("active_width_mm", 0.0) or 0.0)
        h = float(det.get("active_height_mm", 0.0) or 0.0)
        if not (np.isclose(w, fov) and np.isclose(h, fov)):
            failures.append(f"LAYOUT: detector active area {w}x{h} != FOV {fov}x{fov} mm")
        diam = float(surface.get("diameter", 0.0) or 0.0)
        if diam > 0.0 and diam <= fov + 1e-6:
            failures.append(
                f"LAYOUT: detector trace diameter {diam} mm collapsed to the sensor -- the catch "
                f"aperture should stay wider than the {fov} mm sensor window"
            )


def _check_integration(failures: list[str], notes: list[str]) -> None:
    try:
        from KrakenOS.UI.validate_open3d_source_illumination_overlay import _build_coaxial_overlay
    except Exception as exc:  # pragma: no cover - import guard
        notes.append(f"SKIP integration: harness unavailable ({exc!r})")
        return

    editor, system, bundle = _build_coaxial_overlay(_TRACE_RAYS)
    if editor is None:
        notes.append("SKIP integration: clean coaxial-LED fixture unavailable")
        return
    try:
        spec = editor.source_illumination_overlay_spec(system, bundle)
    except Exception as exc:
        failures.append(f"INTEGRATION: source_illumination_overlay_spec raised {exc!r}")
        return
    if not spec:
        failures.append("INTEGRATION: overlay spec is None on the clean coaxial-LED fixture")
        return

    pts = np.asarray(spec["points"], dtype=float)
    center = np.asarray(spec["center"], dtype=float)
    u = np.asarray(spec["tangent"], dtype=float)
    v = np.asarray(spec["bitangent"], dtype=float)
    local_x = (pts - center) @ u
    local_y = (pts - center) @ v
    half = max(float(np.max(np.abs(local_x))), float(np.max(np.abs(local_y))))
    # 39x39 sensor -> bin-centre half ~18.3 mm; the bug drew the 78 mm catch diameter (half 39).
    if half >= 25.0:
        failures.append(
            f"INTEGRATION: heatmap quad half-span {half:.1f} mm exceeds the 39x39 sensor -- "
            f"catch-diameter regression (flag_20260709_093800_013)"
        )
    if half < 12.0:
        failures.append(f"INTEGRATION: heatmap quad half-span {half:.1f} mm does not span the sensor")

    fold = float(spec["x_edge_ratio"])
    perp = float(spec["y_edge_ratio"])
    if not (fold < perp):
        failures.append(f"INTEGRATION: fold edge not darker than perp ({fold:.3f} vs {perp:.3f})")
    notes.append(
        f"integration: {_TRACE_RAYS} rays -> clean-fixture quad half={half:.1f} mm (39x39 sensor), "
        f"fold={fold:.3f} perp={perp:.3f}"
    )


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_pure_extent(failures)
    _check_layout_static(failures)
    _check_integration(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] illumination heatmap extent = sensor, not catch diameter")
        return 1
    print("[PASS] relative-illumination heatmap window pins to the sensor, not the round diameter")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
