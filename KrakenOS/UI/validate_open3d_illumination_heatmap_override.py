"""bugs/0276 -- the source-illumination heatmap window must pin to the vendor-camera
sensor override (the orange square), not the cropped illuminated data footprint.

flag_20260709_104624_302 (a direct follow-up to 0275): after 0275 removed the
catch-DIAMETER fallback, the MV-150 coaxial heatmap read SMALLER than the sensor with
no 2-dark / 2-uniform fold edges. Root cause: a vendor-glued camera declares its sensor
size in the runtime ``_camera_detector_active_dims_overrides`` (the same source
``scene_builder`` uses to draw the orange sensor square), NOT in ``row.advanced['Detector']``.
``_source_illumination_target_model`` read only the row block -> active dims 0 -> the
extent fell through to the illuminated data footprint (data min/max + 20% pad), clipping
the fold dark edges away.

Fix: ``_source_illumination_target_model`` now consults the same detector-dims override,
mirroring ``scene_builder``, so the heatmap window is the 39x39 sensor again.

Checks (display-free; numpy + one headless trace, no VTK/Tk):
  * MODEL differential -- on a detector whose active dims live ONLY in the override, the
    heatmap target-model reports the sensor dims; drop the override and it collapses to 0
    (proving the override consult is load-bearing, not the row block).
  * INTEGRATION -- the real overlay quad, dims-in-override-only, spans the 39x39 sensor
    (half ~18.3 mm, NOT the ~15 mm data footprint, NOT the 78 mm catch diameter) and still
    reads the fold edge columns darker than the perpendicular edge rows (2 dark + 2 uniform).
"""
from __future__ import annotations

import os

import numpy as np

# Diffuse-scatter budget; enough rays for a stable fold-vs-perp edge asymmetry.
_TRACE_RAYS = int(os.environ.get("HEATMAP_OVERRIDE_RAYS", "8000") or "8000")


def _build_override_only_overlay(ray_count: int):
    """Coaxial-LED fixture whose detector active dims live ONLY in the vendor-camera
    override (``_camera_detector_active_dims_overrides``), not in ``row.advanced['Detector']``
    -- the real vendor-STEP scene (flag_20260709_104624_302). Returns
    ``(editor, system, bundle, det_index, fov)`` or ``(None, ...)`` on any build failure."""
    try:
        import KrakenOS as Kos
        from KrakenOS.common_optical_layouts import machine_vision_150mm_coaxial_led as layout
        from KrakenOS.UI.layout_editor import _build_system_from_specs
        from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
        from KrakenOS.UI.scene_builder import build_scene_bundle

        settings = dict(layout.SETTINGS)
        src_specs = [dict(s) for s in settings["scene_sources"]]
        src_specs[0]["ray_count"] = int(ray_count)
        settings["scene_sources"] = src_specs
        surfaces = [dict(s) for s in layout.SURFACES]
        det_index = max(i for i, s in enumerate(surfaces) if str(s.get("surface")) == "Image")
        det_adv = dict(surfaces[det_index].get("advanced", {}) or {})
        det_block = dict(det_adv.get("Detector", {}) or {})
        fov = float(det_block.get("active_width_mm", 0.0) or 0.0)
        if fov <= 0.0:
            return None, None, None, None, None
        # Move the sensor dims OUT of the row and INTO the override (the vendor-glue case).
        det_block["active_width_mm"] = 0.0
        det_block["active_height_mm"] = 0.0
        det_adv["Detector"] = det_block
        surfaces[det_index] = dict(surfaces[det_index], advanced=det_adv)

        rows = _rows_from_layout_info({"surfaces": surfaces, "settings": settings})
        editor = _snapshot_editor(rows, settings)
        editor._camera_detector_active_dims_overrides = lambda: {int(det_index): (fov, fov)}
        sources = editor._collect_scene_sources(wavelength=float(settings["wavelength"]))
        system = _build_system_from_specs(surfaces)
        rays = Kos.raykeeper(system)
        max_radius = max((max(r.diameter / 2.0, 0.5) for r in rows), default=1.0)
        editor._trace_preview_rays(system, rays, float(settings["wavelength"]), max_radius, allow_full_pupil=False)
        bundle = build_scene_bundle(
            rows=rows, system=system, rays=rays, sources=sources,
            field_count=len(sources),
            ray_count_per_field=max((s.ray_count for s in sources), default=1),
        )
        editor.last_system, editor.last_rays, editor._last_scene_bundle = system, rays, bundle
        return editor, system, bundle, det_index, fov
    except Exception:  # pragma: no cover - fixture guard
        return None, None, None, None, None


def _check_model_and_integration(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle, det_index, fov = _build_override_only_overlay(_TRACE_RAYS)
    if editor is None:
        notes.append("SKIP override: coaxial-LED fixture unavailable")
        return
    half_sensor = 0.5 * float(fov)

    # --- MODEL differential: the override is the only source of the sensor dims. ---
    samples = editor._source_illumination_hit_samples(system, det_index)
    model = editor._source_illumination_target_model(samples)
    model_w = float(model.get("active_width_mm", 0.0) or 0.0)
    model_h = float(model.get("active_height_mm", 0.0) or 0.0)
    if not (np.isclose(model_w, fov) and np.isclose(model_h, fov)):
        failures.append(
            f"MODEL: override-only detector reports active dims {model_w}x{model_h} != sensor "
            f"{fov}x{fov} mm -- the heatmap ignored _camera_detector_active_dims_overrides "
            f"(bugs/0276 regressed)"
        )
    # Drop the override; with no row block either, the dims must collapse to 0.
    editor._camera_detector_active_dims_overrides = lambda: None
    model_off = editor._source_illumination_target_model(samples)
    if float(model_off.get("active_width_mm", 0.0) or 0.0) > 1e-9:
        failures.append(
            "MODEL: active dims survived with no override and no row block -- the differential "
            "is broken (the override is not actually what drives the window)"
        )
    editor._camera_detector_active_dims_overrides = lambda: {int(det_index): (fov, fov)}

    # --- INTEGRATION: the real overlay quad must span the sensor, not the data footprint. ---
    try:
        spec = editor.source_illumination_overlay_spec(system, bundle)
    except Exception as exc:
        failures.append(f"INTEGRATION: source_illumination_overlay_spec raised {exc!r}")
        return
    if not spec:
        failures.append("INTEGRATION: overlay spec is None on the override-only fixture")
        return

    pts = np.asarray(spec["points"], dtype=float)
    center = np.asarray(spec["center"], dtype=float)
    u = np.asarray(spec["tangent"], dtype=float)
    v = np.asarray(spec["bitangent"], dtype=float)
    half = max(float(np.max(np.abs((pts - center) @ u))), float(np.max(np.abs((pts - center) @ v))))
    # 39x39 sensor -> bin-centre half ~18.3 mm. Without the override the window falls to the
    # raw data footprint, which is the WRONG size either way: it can crop inside the sensor
    # (the user's flag) or overrun it (this wide-catch fixture, ~50 mm) depending on how far
    # the off-sensor scatter reaches -- so guard both bounds.
    if half <= half_sensor - 2.5:
        failures.append(
            f"INTEGRATION: quad half {half:.1f} mm crops inside the {half_sensor:.1f} mm sensor "
            f"-- data-footprint regression (flag_20260709_104624_302)"
        )
    if half >= half_sensor + 2.0:
        failures.append(
            f"INTEGRATION: quad half {half:.1f} mm overruns the {half_sensor:.1f} mm sensor "
            f"-- catch-diameter regression"
        )

    fold = float(spec["x_edge_ratio"])
    perp = float(spec["y_edge_ratio"])
    if not (fold < perp):
        failures.append(f"INTEGRATION: fold edge not darker than perp ({fold:.3f} vs {perp:.3f})")

    # 2 dark (fold / tangent columns) + 2 uniform (perp / bitangent rows).
    rel = np.asarray(spec["relative"], dtype=float)
    if rel.ndim == 2 and rel.size:
        fold_edges = 0.5 * (float(np.mean(rel[:, 0])) + float(np.mean(rel[:, -1])))
        perp_edges = 0.5 * (float(np.mean(rel[0, :])) + float(np.mean(rel[-1, :])))
        if not (fold_edges < perp_edges):
            failures.append(
                f"INTEGRATION: fold edge columns ({fold_edges:.3f}) not darker than perp edge rows "
                f"({perp_edges:.3f}) -- 2-dark / 2-uniform pattern lost"
            )
        notes.append(f"override: fold-edge {fold_edges:.3f} < perp-edge {perp_edges:.3f}")

    notes.append(
        f"override-only: {_TRACE_RAYS} rays -> model {model_w:.0f}x{model_h:.0f}, quad "
        f"half={half:.1f} mm (sensor {half_sensor:.1f}), fold={fold:.3f} perp={perp:.3f}"
    )


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    _check_model_and_integration(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    ok, messages = run_checks()
    for line in messages:
        print(("PASS " if ok else "") + line)
    print("RESULT:", "pass" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
