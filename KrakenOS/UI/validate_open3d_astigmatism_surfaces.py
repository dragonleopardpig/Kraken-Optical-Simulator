"""Display-free guard for the 3D tangential/sagittal astigmatism surfaces (idea #2a).

Astigmatism is the separation between the tangential and sagittal best-focus surfaces.
The overlay draws both (tangential = amber, sagittal = blue) from the per-field T/S
foci the 2D Field Curvature analysis already computes, magnified by the SAME factor as
the medial best-focus bowl so their gap is the astigmatism at the true relative scale.

This guard pins (headless, no VTK):

  * INTEGRATION on the real Zemax double gauss: ``astigmatism_surfaces_overlay_spec``
    returns two surfaces that genuinely DIFFER (max T-S ~0.09 mm), both sized to the
    image circle, sharing one exaggeration, ``max_astigmatism_mm`` matches the T-S gap,
    and the lazy field scan is CACHED.
  * RENDER-ONLY / TOGGLE contract: ``refresh_scene`` reads ``show_astigmatism_var`` and
    calls ``_add_astigmatism_surfaces_overlays``; that renderer never rebuilds the system,
    does not shadow the pv/np/vtkBillboardTextActor3D globals, and the right-click analyses
    menu offers the toggle.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_astigmatism_surfaces

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService
from KrakenOS.UI.validate_open3d_best_focus_surface import _build_scene_bundle_for_double_gauss


def _check_integration(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle = _build_scene_bundle_for_double_gauss()
    if editor is None:
        notes.append("SKIP integration: double-gauss layout/bundle unavailable")
        return
    spec = editor.astigmatism_surfaces_overlay_spec(system, bundle)
    if spec is None:
        failures.append("INTEGRATION: astigmatism_surfaces_overlay_spec returned None on the double gauss")
        return
    tangential = spec.get("tangential")
    sagittal = spec.get("sagittal")
    if not tangential or not sagittal:
        failures.append("INTEGRATION: missing tangential/sagittal surface")
        return

    t_dz = np.asarray(tangential.get("ring_dz", []), dtype=float)
    s_dz = np.asarray(sagittal.get("ring_dz", []), dtype=float)
    if t_dz.size < 2 or t_dz.size != s_dz.size:
        failures.append("INTEGRATION: T/S surfaces have mismatched/too-few rings")
        return
    max_gap = float(np.max(np.abs(t_dz - s_dz)))
    if max_gap <= 1e-4:
        failures.append(f"INTEGRATION: tangential and sagittal coincide -- no astigmatism (max|T-S|={max_gap:.3g})")
    reported = float(spec.get("max_astigmatism_mm", 0.0))
    if abs(reported - max_gap) > 1e-6:
        failures.append(f"INTEGRATION: max_astigmatism_mm {reported:.4g} != surface gap {max_gap:.4g}")
    if abs(float(tangential.get("exaggeration", 0.0)) - float(sagittal.get("exaggeration", -1.0))) > 1e-6:
        failures.append("INTEGRATION: tangential and sagittal use different exaggeration factors")

    image_circle = float(editor._field_metrics_summary().get("field_image_radius", 0.0))
    if image_circle > 1e-6 and abs(float(tangential.get("radius", 0.0)) - image_circle) > 0.02 * image_circle:
        failures.append("INTEGRATION: astigmatism surface rim does not coincide with the image circle")

    if editor.astigmatism_surfaces_overlay_spec(system, bundle) is not spec:
        failures.append("INTEGRATION: astigmatism spec is not cached (recomputes the field scan)")
    notes.append(f"integration: double-gauss astigmatism max T-S {reported:.4g} mm ×{float(spec.get('exaggeration', 1)):.0f}")


def _check_source_contracts(failures: list[str]) -> None:
    refresh_src = inspect.getsource(Open3DSceneRefreshService.refresh_scene)
    if "show_astigmatism_var" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not read show_astigmatism_var")
    if "_add_astigmatism_surfaces_overlays" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not call _add_astigmatism_surfaces_overlays")

    for method_name in ("_add_astigmatism_surfaces_overlays", "_draw_focus_surface_fill_and_rings"):
        method = getattr(Kraken3DInspector, method_name)
        add_src = inspect.getsource(method)
        for forbidden in ("build_system(", "_build_preview_system_rays_bundle("):
            if forbidden in add_src:
                failures.append(f"CONTRACT: {method_name} references {forbidden!r} -- not render-only")
        shadowed = [g for g in ("pv", "np", "vtkBillboardTextActor3D") if g in method.__code__.co_varnames]
        if shadowed:
            failures.append(f"CONTRACT: {method_name} shadows module globals {shadowed} with locals")

    analysis_src = inspect.getsource(Kraken3DInspector._add_image_plane_analysis_menu)
    if "show_astigmatism_var" not in analysis_src:
        failures.append("CONTRACT: the right-click analyses menu does not offer astigmatism")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_integration(failures, notes)
    _check_source_contracts(failures)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] 3D tangential/sagittal astigmatism surfaces")
        return 1
    print("[PASS] tangential + sagittal best-focus surfaces show astigmatism in 3D (idea #2a)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
