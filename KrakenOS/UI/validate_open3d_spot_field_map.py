"""Display-free guard for the 3D spot RMS field map (idea #1/#3 foundation).

Trace the geometric spot at a grid of field points; at each field's landing position on
the detector draw a circle sized by the (magnified) RMS spot radius, coloured green
(tight) -> red (soft). The map shows spot-quality variation across the sensor in 3D.

This guard pins (headless, no VTK):

  * PURE GEOMETRY (``spot_field_map``): circles land at the per-field chief positions,
    each radius = rms * magnification, the worst spot's circle is bigger than the best's,
    a tiny RMS is magnified (factor > 1), colour tracks RMS, degenerate / perfect input
    returns None.
  * INTEGRATION on the real Zemax double gauss: ``spot_field_map_overlay_spec`` returns a
    sane map (a few-um RMS that GROWS toward the field edge), magnified, and CACHED.
  * RENDER-ONLY / TOGGLE contract: ``refresh_scene`` reads ``show_spot_field_map_var`` and
    calls ``_add_spot_field_map_overlays``; that renderer never rebuilds the system, does
    not shadow the pv/np/vtkBillboardTextActor3D globals, and the right-click menu has it.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_spot_field_map

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService
from KrakenOS.UI.services.spot_field_map import build_spot_field_map
from KrakenOS.UI.validate_open3d_best_focus_surface import _build_scene_bundle_for_double_gauss


def _check_pure_geometry(failures: list[str]) -> None:
    center = np.array([0.0, 0.0, 100.0])
    normal = np.array([0.0, 0.0, 1.0])
    tangent = np.array([1.0, 0.0, 0.0])  # -> u=+x, v=+y
    chief_u = np.array([0.0, 5.0, -5.0, 0.0, 0.0])
    chief_v = np.array([0.0, 0.0, 0.0, 5.0, -5.0])
    rms = np.array([0.001, 0.004, 0.004, 0.010, 0.010])  # mm; edge softer

    spec = build_spot_field_map(chief_u, chief_v, rms, center=center, normal=normal, tangent=tangent, image_radius=10.0)
    if spec is None:
        failures.append("PURE: build_spot_field_map returned None for valid input")
        return
    circles = spec["circles"]
    if len(circles) != 5:
        failures.append(f"PURE: expected 5 circles, got {len(circles)}")
        return
    factor = float(spec["magnification"])
    if factor <= 1.0:
        failures.append(f"PURE: tiny RMS was not magnified (factor {factor:.3g})")

    radii = []
    for i in range(5):
        circle = np.asarray(circles[i], dtype=float)[:-1]  # drop the closing duplicate
        centroid = circle.mean(axis=0)
        want_center = center + chief_u[i] * np.array([1.0, 0.0, 0.0]) + chief_v[i] * np.array([0.0, 1.0, 0.0])
        if not np.allclose(centroid, want_center, atol=1e-6):
            failures.append(f"PURE: circle {i} not at its chief position (got {centroid}, want {want_center})")
            break
        ring_radii = np.linalg.norm(circle - centroid, axis=1)
        if not np.allclose(ring_radii, rms[i] * factor, rtol=1e-5, atol=1e-9):
            failures.append(f"PURE: circle {i} radius {ring_radii.mean():.4g} != rms*mag {rms[i] * factor:.4g}")
            break
        radii.append(float(ring_radii.mean()))
    if len(radii) == 5 and not (radii[3] > radii[0] + 1e-9):
        failures.append("PURE: the soft edge field's circle is not bigger than the on-axis circle")

    colors = spec["colors"]
    if len(colors) == 5:
        # on-axis (min rms) greener than edge (max rms): more green channel, less red.
        if not (colors[0][1] > colors[3][1] and colors[0][0] < colors[3][0]):
            failures.append("PURE: colour does not track RMS (good->green, bad->red)")

    # Scatter: the real spot shape laid at the chief, magnified by the same factor as the
    # circle (so each blob fits inside its RMS circle).
    theta = np.linspace(0.0, 2.0 * np.pi, 16, endpoint=False)
    scatter = [np.column_stack((rms[i] * np.cos(theta), rms[i] * np.sin(theta))) for i in range(5)]
    spec_scatter = build_spot_field_map(
        chief_u, chief_v, rms, center=center, normal=normal, tangent=tangent, image_radius=10.0, scatter=scatter,
    )
    groups = spec_scatter.get("scatter_groups", []) if spec_scatter else []
    if len(groups) != 5:
        failures.append(f"PURE: expected 5 scatter groups, got {len(groups)}")
    else:
        factor_s = float(spec_scatter["magnification"])
        for i in range(5):
            pts = np.asarray(groups[i]["points"], dtype=float)
            centroid = pts.mean(axis=0)
            want_center = center + chief_u[i] * np.array([1.0, 0.0, 0.0]) + chief_v[i] * np.array([0.0, 1.0, 0.0])
            if not np.allclose(centroid, want_center, atol=1e-6):
                failures.append(f"PURE: scatter group {i} not centred at its chief")
                break
            blob_radius = float(np.linalg.norm(pts - centroid, axis=1).mean())
            if not np.isclose(blob_radius, rms[i] * factor_s, rtol=1e-5, atol=1e-9):
                failures.append(f"PURE: scatter group {i} radius {blob_radius:.4g} != rms*mag {rms[i] * factor_s:.4g}")
                break

    if build_spot_field_map([0.0], [0.0], [0.0], center=center, normal=normal, tangent=tangent) is not None:
        failures.append("PURE: <2 spots did not return None")
    if build_spot_field_map(chief_u, chief_v, np.zeros(5), center=center, normal=normal, tangent=tangent) is not None:
        failures.append("PURE: a perfect (zero-RMS) lens did not return None")


def _check_integration(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle = _build_scene_bundle_for_double_gauss()
    if editor is None:
        notes.append("SKIP integration: double-gauss layout/bundle unavailable")
        return
    spec = editor.spot_field_map_overlay_spec(system, bundle)
    if spec is None:
        failures.append("INTEGRATION: spot_field_map_overlay_spec returned None on the double gauss")
        return
    n_spots = int(spec.get("n_spots", 0))
    if n_spots < 5:
        failures.append(f"INTEGRATION: too few spots traced ({n_spots})")
    rms_lo = float(spec.get("rms_min_mm", 0.0))
    rms_hi = float(spec.get("rms_max_mm", 0.0))
    if not (0.0 < rms_lo <= rms_hi):
        failures.append(f"INTEGRATION: nonsensical RMS range ({rms_lo:.4g}..{rms_hi:.4g} mm)")
    if rms_hi <= rms_lo:
        failures.append("INTEGRATION: spot RMS does not vary across the field")
    if float(spec.get("magnification", 1.0)) <= 1.0:
        failures.append("INTEGRATION: the few-um spots were not magnified")
    if len(spec.get("circles") or []) != n_spots:
        failures.append("INTEGRATION: circle count != spot count")
    # The actual ray-intercept scatter (the real spot shape) must be present per field.
    groups = spec.get("scatter_groups") or []
    if len(groups) != n_spots:
        failures.append(f"INTEGRATION: scatter groups {len(groups)} != {n_spots} fields (no spot shape drawn)")
    elif groups and int(np.asarray(groups[0]["points"]).shape[0]) < 10:
        failures.append("INTEGRATION: a spot has too few scatter points to show its shape")
    if editor.spot_field_map_overlay_spec(system, bundle) is not spec:
        failures.append("INTEGRATION: spot map is not cached (re-traces every call)")
    notes.append(f"integration: double-gauss RMS {rms_lo*1000:.2g}-{rms_hi*1000:.2g} µm over {n_spots} fields, ×{float(spec.get('magnification',1)):.0f}")


def _check_source_contracts(failures: list[str]) -> None:
    refresh_src = inspect.getsource(Open3DSceneRefreshService.refresh_scene)
    if "show_spot_field_map_var" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not read show_spot_field_map_var")
    if "_add_spot_field_map_overlays" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not call _add_spot_field_map_overlays")

    method = Kraken3DInspector._add_spot_field_map_overlays
    add_src = inspect.getsource(method)
    for forbidden in ("build_system(", "_build_preview_system_rays_bundle("):
        if forbidden in add_src:
            failures.append(f"CONTRACT: _add_spot_field_map_overlays references {forbidden!r} -- not render-only")
    if "scatter_groups" not in add_src or ".glyph(" not in add_src:
        failures.append("CONTRACT: _add_spot_field_map_overlays does not render the spot scatter (only circles)")
    shadowed = [g for g in ("pv", "np", "vtkBillboardTextActor3D") if g in method.__code__.co_varnames]
    if shadowed:
        failures.append(f"CONTRACT: _add_spot_field_map_overlays shadows module globals {shadowed} with locals")

    analysis_src = inspect.getsource(Kraken3DInspector._add_image_plane_analysis_menu)
    if "show_spot_field_map_var" not in analysis_src:
        failures.append("CONTRACT: the right-click analyses menu does not offer the spot map")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_pure_geometry(failures)
    _check_integration(failures, notes)
    _check_source_contracts(failures)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] 3D spot RMS field map")
        return 1
    print("[PASS] spot RMS map shows spot quality across the field in 3D (idea #1/#3)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
