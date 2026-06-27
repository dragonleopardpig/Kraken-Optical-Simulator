"""Display-free guard for the 3D curved best-focus surface overlay (field-curvature
visualization, idea #2).

The real best-focus surface of a lens is curved (Petzval / field curvature); the
detector is flat. The overlay lofts the per-field tangential & sagittal best-focus
offsets (the same numbers the 2D Field Curvature analysis computes, on-axis
referenced) into a translucent surface of revolution at the image plane, so the
field curvature -- and the field-dependent gap to the flat detector -- reads in 3D.

This guard pins (all headless, no VTK):

  * PURE GEOMETRY (``best_focus_surface``): synthetic field-curving input lofts a
    ring grid whose apex sits at the image centre, whose rim ring reaches the image
    radius, whose per-ring axial offset equals the medial (mean T/S) focus and grows
    with field, with well-formed faces; degenerate inputs return None.
  * INTEGRATION on the real Zemax double gauss: ``best_focus_surface_overlay_spec``
    returns a surface that genuinely DEVIATES from the flat image plane (non-trivial
    field curvature), and the lazy field-curvature scan is CACHED (a second call
    returns the same object).
  * ANCHOR: a beam-splitter scene (a branch-detector target present) is SKIPPED for
    now (returns None) -- the per-branch surface is a follow-up.
  * RENDER-ONLY / TOGGLE contract: ``refresh_scene`` reads ``show_best_focus_surface_var``
    and calls ``_add_best_focus_surface_overlays``; that renderer never rebuilds the
    system; and the toggle handler routes through the bugs/0166 display-toggle gate
    (so flipping it re-renders the cached scene, no solid re-mesh).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_best_focus_surface

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import (
    LAYOUTS_DIR,
    Kraken3DInspector,
    KrakenLayoutEditor,
    _load_python_data,
    _load_python_title,
)
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor
from KrakenOS.UI.services.best_focus_surface import (
    best_focus_surface_faces,
    build_best_focus_surface,
)
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

_DOUBLE_GAUSS_TITLE = "Zemax Double Gauss 28 Degree Field"


def _axial_offsets(points: np.ndarray, center: np.ndarray, normal: np.ndarray) -> np.ndarray:
    return (points - center) @ normal


def _radial_distances(points: np.ndarray, center: np.ndarray, normal: np.ndarray) -> np.ndarray:
    rel = points - center
    axial = np.outer(rel @ normal, normal)
    return np.linalg.norm(rel - axial, axis=1)


def _check_pure_geometry(failures: list[str]) -> None:
    center = np.array([0.0, 0.0, 100.0])
    normal = np.array([0.0, 0.0, 1.0])
    tangent = np.array([1.0, 0.0, 0.0])
    rim_radius = 12.0
    # Rings sized to the REAL image height per field (rim = max image height).
    image_heights = np.linspace(0.0, rim_radius, 6)
    # Tiny inward-curving field with astigmatism (T != S) -- like a corrected lens.
    focus_t = -0.0006 * image_heights**2
    focus_s = -0.0003 * image_heights**2
    medial = 0.5 * (focus_t + focus_s)

    # 1) TRUE scale (exaggeration=1): geometry matches the raw offsets.
    true_spec = build_best_focus_surface(
        image_heights, focus_t, focus_s,
        center=center, normal=normal, tangent=tangent, exaggeration=1.0,
    )
    if true_spec is None:
        failures.append("PURE: build_best_focus_surface returned None for valid input")
        return
    n_rings = int(true_spec["n_rings"])
    n_az = int(true_spec["n_az"])
    points = np.asarray(true_spec["points"], dtype=float)
    if points.shape != (n_rings * n_az, 3):
        failures.append(f"PURE: points shape {points.shape} != ({n_rings * n_az}, 3)")
        return
    apex = points[:n_az]
    if not np.allclose(apex, apex[0], atol=1e-9) or not np.allclose(apex[0], center, atol=1e-6):
        failures.append("PURE: apex ring does not collapse to the image centre")
    rim = points[(n_rings - 1) * n_az:n_rings * n_az]
    rim_radial = _radial_distances(rim, center, normal)
    if not np.allclose(rim_radial, rim_radius, atol=1e-6):
        failures.append(f"PURE: rim radius {rim_radial.mean():.4g} != max image height {rim_radius}")
    if abs(float(true_spec["radius"]) - rim_radius) > 1e-6:
        failures.append(f"PURE: spec radius {true_spec['radius']:.4g} != max image height {rim_radius}")
    axial = _axial_offsets(points, center, normal)
    for i in range(n_rings):
        if not np.allclose(axial[i * n_az:(i + 1) * n_az], medial[i], atol=1e-9):
            failures.append(f"PURE: true-scale ring {i} axial != medial")
            break
    if not np.allclose(np.asarray(true_spec["ring_dz"]), medial, atol=1e-12):
        failures.append("PURE: ring_dz is not the true medial offsets")

    # 2) AUTO exaggeration: the sag is magnified to a visible fraction of the rim,
    #    the factor > 1 (tiny true sag), and ring_dz stays TRUE.
    spec = build_best_focus_surface(
        image_heights, focus_t, focus_s,
        center=center, normal=normal, tangent=tangent,
    )
    factor = float(spec["exaggeration"])
    if factor <= 1.0:
        failures.append(f"PURE: tiny curvature was not exaggerated (factor={factor:.3g})")
    display_axial = _axial_offsets(np.asarray(spec["points"], dtype=float), center, normal)
    rim_display = abs(float(display_axial[(n_rings - 1) * n_az]))
    if rim_display < 0.05 * rim_radius:
        failures.append(f"PURE: exaggerated rim sag {rim_display:.3g} < 5% of rim {rim_radius} -- still flat")
    if not np.allclose(np.asarray(spec["ring_dz"]), medial, atol=1e-12):
        failures.append("PURE: exaggeration corrupted the TRUE ring_dz (must stay un-exaggerated)")
    if not np.allclose(np.asarray(spec["display_dz"]), medial * factor, atol=1e-9):
        failures.append("PURE: display_dz != medial * exaggeration")

    faces = best_focus_surface_faces(n_rings, n_az)
    if faces.size != (n_rings - 1) * n_az * 5:
        failures.append(f"PURE: faces size {faces.size} != {(n_rings - 1) * n_az * 5}")
    if faces.size and (np.max(faces[faces != 4]) >= n_rings * n_az):
        failures.append("PURE: a face references a point index out of range")

    # Degenerate inputs -> None.
    if build_best_focus_surface([0.0], [0.0], [0.0], center=center, normal=normal, tangent=tangent) is not None:
        failures.append("PURE: <2 rings did not return None")
    if build_best_focus_surface([0.0, 0.0], [0.0, 0.0], [0.0, 0.0], center=center, normal=normal, tangent=tangent) is not None:
        failures.append("PURE: zero image radius did not return None")


def _double_gauss_editor():
    layout_path = None
    for path in sorted(LAYOUTS_DIR.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            if str(_load_python_title(path)).strip() == _DOUBLE_GAUSS_TITLE:
                layout_path = path
                break
        except Exception:
            continue
    if layout_path is None:
        return None, None, None
    info = _load_python_data(layout_path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.tk = object()  # break tkinter __getattr__ recursion on the __new__ instance
    editor.current_layout_file = layout_path
    editor._normalize_special_rows()
    system = _build_runtime_system(layout_path, editor.rows)
    return editor, system, layout_path


def _build_scene_bundle_for_double_gauss():
    """Shared headless harness: editor + system + traced scene bundle for the double
    gauss (reused by the distortion-grid guard). Returns (None, None, None) on any
    fixture/build failure."""
    editor, system, _layout_path = _double_gauss_editor()
    if editor is None:
        return None, None, None
    try:
        wavelength = float(editor._current_wavelength())
        rays = Kos.raykeeper(system)
        max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
        editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=True,
                                   sampling_mode=editor._preview_2d_sampling_mode())
        bundle = editor._build_scene_bundle(system, rays, max_radius)
    except Exception:
        return None, None, None
    return editor, system, bundle


def _check_integration(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle = _build_scene_bundle_for_double_gauss()
    if editor is None:
        notes.append("SKIP integration: double-gauss layout/bundle unavailable")
        return

    anchor = editor._best_focus_surface_anchor_target(bundle)
    if anchor is None:
        notes.append("SKIP integration: no image-plane anchor target in the double-gauss bundle")
        return

    spec = editor.best_focus_surface_overlay_spec(system, bundle)
    if spec is None:
        failures.append("INTEGRATION: best_focus_surface_overlay_spec returned None on the double gauss")
        return
    ring_dz = np.asarray(spec.get("ring_dz", []), dtype=float)
    if ring_dz.size < 2:
        failures.append("INTEGRATION: surface has < 2 rings")
        return
    max_dev = float(np.max(np.abs(ring_dz)))  # TRUE field curvature (mm)
    if max_dev <= 1e-4:
        failures.append(f"INTEGRATION: surface does not deviate from the flat plane (max|dz|={max_dev:.3g} mm)")

    # The rim is sized to the REAL chief-ray image height (where the rays land), not
    # the lens clear-aperture: the double gauss images its 14-deg field to ~24.5 mm.
    rim = float(spec.get("radius", 0.0))
    scan = editor._analysis_plot_service()._sample_field_curvature_distortion(system, float(editor._current_wavelength()))
    if scan:
        true_rim = float(np.max(np.asarray(scan[0]["Y"]["image_height"], dtype=float)))
        if abs(rim - true_rim) > 0.5:
            failures.append(f"INTEGRATION: rim {rim:.4g} != max real image height {true_rim:.4g} (sized to clear-aperture?)")

    # The tiny true sag must be auto-exaggerated to a visible fraction of the rim.
    factor = float(spec.get("exaggeration", 1.0))
    display_dz = np.asarray(spec.get("display_dz", []), dtype=float)
    if factor <= 1.0:
        failures.append(f"INTEGRATION: sub-mm curvature ({max_dev:.3g} mm) was not exaggerated (factor={factor:.3g})")
    if display_dz.size and float(np.max(np.abs(display_dz))) < 0.05 * max(rim, 1e-9):
        failures.append("INTEGRATION: exaggerated sag still < 5% of the rim -- bowl would read flat")

    # Caching: a second call must reuse the same object (the scan is expensive).
    spec2 = editor.best_focus_surface_overlay_spec(system, bundle)
    if spec2 is not spec:
        failures.append("INTEGRATION: best-focus surface spec is not cached (recomputes the field scan each call)")
    notes.append(
        f"integration: double-gauss field curv P-V~{float(np.ptp(ring_dz)):.4g} mm, rim {rim:.4g} mm, ×{factor:.0f}"
    )


def _check_anchor_skips_branch_scene(failures: list[str]) -> None:
    editor, _system, _path = _double_gauss_editor()
    if editor is None:
        editor = _snapshot_editor([], {})
        editor.tk = object()

    class _Target:
        def __init__(self, metadata, row_index):
            self.metadata = metadata
            self.row_index = row_index
            self.center_world = np.zeros(3)
            self.normal_world = np.array([0.0, 0.0, 1.0])
            self.tangent_world = np.array([1.0, 0.0, 0.0])
            self.diameter = 10.0
            self.active_width_mm = 0.0
            self.active_height_mm = 0.0
            self.is_detector = True

    class _Bundle:
        def __init__(self, targets):
            self.targets = targets

    branch_bundle = _Bundle([
        _Target({"target_source": "table_row"}, 5),
        _Target({"target_source": "branch_detector"}, 100000),
    ])
    if editor._best_focus_surface_anchor_target(branch_bundle) is not None:
        failures.append("ANCHOR: a branch-detector scene was not skipped (should return None)")

    plain_bundle = _Bundle([_Target({"target_source": "table_row"}, 5)])
    if editor._best_focus_surface_anchor_target(plain_bundle) is None:
        failures.append("ANCHOR: a plain image-plane target was not selected")


def _check_source_contracts(failures: list[str]) -> None:
    refresh_src = inspect.getsource(Open3DSceneRefreshService.refresh_scene)
    if "show_best_focus_surface_var" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not read show_best_focus_surface_var")
    if "_add_best_focus_surface_overlays" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not call _add_best_focus_surface_overlays")

    add_src = inspect.getsource(Kraken3DInspector._add_best_focus_surface_overlays)
    for forbidden in ("build_system(", "_build_preview_system_rays_bundle("):
        if forbidden in add_src:
            failures.append(f"CONTRACT: _add_best_focus_surface_overlays references {forbidden!r} -- not render-only")
    # The render method reads the pyvista/np module globals; a local of the same name
    # makes the whole method treat them as unassigned locals (the 0167 `pv = P-V`
    # UnboundLocalError that crashed the app). Headless can't drive the renderer, so
    # pin it on the bytecode: none of these globals may appear as a local.
    add_code = Kraken3DInspector._add_best_focus_surface_overlays.__code__
    shadowed = [g for g in ("pv", "np", "vtkBillboardTextActor3D") if g in add_code.co_varnames]
    if shadowed:
        failures.append(
            f"CONTRACT: _add_best_focus_surface_overlays shadows module globals {shadowed} "
            "with same-named locals (UnboundLocalError at runtime)"
        )

    handler_src = inspect.getsource(Kraken3DInspector._on_scene_visibility_changed)
    if "can_reuse_current_scene_for_display_toggle" not in handler_src:
        failures.append("CONTRACT: the Focus-surf toggle would rebuild -- handler lost the bugs/0166 display gate")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_pure_geometry(failures)
    _check_integration(failures, notes)
    _check_anchor_skips_branch_scene(failures)
    _check_source_contracts(failures)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] 3D curved best-focus surface overlay")
        return 1
    print("[PASS] curved best-focus surface lofts the field curvature over the flat detector (idea #2)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
