"""Display-free guard for the 3D distortion grid-warp overlay (idea #2, 2nd half).

A lens images a rectilinear object grid as a barrel/pincushion-warped grid on the
detector. The overlay draws the ideal (rectilinear) grid and its real (radially warped)
image from the per-field real-vs-paraxial chief-ray heights the 2D Distortion analysis
already computes; the divergence is the distortion.

This guard pins (headless, no VTK):

  * PURE GEOMETRY (``distortion_grid``): a synthetic pincushion warp keeps the ideal
    grid rectilinear (off-axis lines stay straight) while the real grid bows outward
    (off-axis lines curve, radii expand), the max distortion % is reported, a tiny warp
    is auto-exaggerated (factor > 1, ``display`` displacement grows), degenerate -> None.
  * INTEGRATION on the real Zemax double gauss: ``distortion_grid_overlay_spec`` returns
    a grid with a sane non-zero max distortion, the real grid genuinely differs from the
    ideal, and the lazy field scan is CACHED.
  * RENDER-ONLY / TOGGLE contract: ``refresh_scene`` reads ``show_distortion_grid_var``
    and calls ``_add_distortion_grid_overlays``; that renderer never rebuilds the system,
    does not shadow the pv/np/vtkBillboardTextActor3D module globals (bytecode check),
    and the toggle handler routes through the bugs/0166 display-toggle gate.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_distortion_grid

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.services.distortion_grid import build_distortion_grid
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService
from KrakenOS.UI.validate_open3d_best_focus_surface import _build_scene_bundle_for_double_gauss


def _line_bow(points: np.ndarray) -> float:
    """Max perpendicular deviation of a polyline's points from its end-to-end chord."""
    pts = np.asarray(points, dtype=float)
    a, b = pts[0], pts[-1]
    chord = b - a
    length = float(np.linalg.norm(chord))
    if length < 1e-9:
        return 0.0
    chord = chord / length
    rel = pts - a
    proj = rel - np.outer(rel @ chord, chord)
    return float(np.max(np.linalg.norm(proj, axis=1)))


def _check_pure_geometry(failures: list[str]) -> None:
    center = np.array([0.0, 0.0, 100.0])
    normal = np.array([0.0, 0.0, 1.0])
    tangent = np.array([1.0, 0.0, 0.0])
    ideal = np.linspace(0.0, 10.0, 6)
    # Pincushion: real height grows faster than ideal (real > ideal off axis).
    real = ideal * (1.0 + 0.02 * (ideal / 10.0))

    spec = build_distortion_grid(ideal, real, center=center, normal=normal, tangent=tangent, exaggeration=1.0)
    if spec is None:
        failures.append("PURE: build_distortion_grid returned None for valid input")
        return
    ideal_lines = spec["ideal_polylines"]
    real_lines = spec["real_polylines"]
    if len(ideal_lines) != len(real_lines) or len(ideal_lines) < 4:
        failures.append(f"PURE: grid line counts off (ideal {len(ideal_lines)}, real {len(real_lines)})")
        return

    # Off-axis line 0 (a full edge line): ideal straight, real bowed.
    if _line_bow(ideal_lines[0]) > 1e-6:
        failures.append(f"PURE: ideal off-axis line is not rectilinear (bow {_line_bow(ideal_lines[0]):.3g})")
    if _line_bow(real_lines[0]) <= 1e-3:
        failures.append("PURE: real off-axis line did not bow (no warp)")

    # Pincushion expands: the real grid reaches farther from the centre than the ideal.
    ideal_max_r = max(float(np.max(np.linalg.norm(np.asarray(line) - center, axis=1))) for line in ideal_lines)
    real_max_r = max(float(np.max(np.linalg.norm(np.asarray(line) - center, axis=1))) for line in real_lines)
    if real_max_r <= ideal_max_r:
        failures.append(f"PURE: pincushion did not expand the grid (ideal {ideal_max_r:.3g}, real {real_max_r:.3g})")
    if not (1.0 < float(spec["max_distortion_pct"]) < 5.0):
        failures.append(f"PURE: max_distortion_pct {spec['max_distortion_pct']:.3g} not ~2%")

    # Auto exaggeration magnifies the tiny warp (factor > 1, real bows MORE than true).
    auto = build_distortion_grid(ideal, real, center=center, normal=normal, tangent=tangent)
    factor = float(auto["exaggeration"])
    if factor <= 1.0:
        failures.append(f"PURE: tiny distortion was not exaggerated (factor {factor:.3g})")
    if _line_bow(auto["real_polylines"][0]) <= _line_bow(real_lines[0]) * 1.5:
        failures.append("PURE: exaggerated grid does not bow more than the true-scale grid")
    if abs(float(auto["max_distortion_pct"]) - float(spec["max_distortion_pct"])) > 1e-6:
        failures.append("PURE: exaggeration changed the reported TRUE max distortion %")

    # Lift onto a best-focus bowl (the "distorted bowl" when both overlays are on):
    # every vertex gets the interpolated axial offset along the normal.
    lift_radii = np.array([0.0, 5.0, 10.0])
    lift_dz = np.array([0.0, -1.0, -4.0])  # a dish (toward the lens)
    lifted = build_distortion_grid(
        ideal, real, center=center, normal=normal, tangent=tangent,
        exaggeration=1.0, lift_radii=lift_radii, lift_dz=lift_dz,
    )
    if not lifted or not lifted.get("lifted"):
        failures.append("PURE: lift params did not produce a lifted grid")
    else:
        rim_pts = np.asarray(lifted["real_polylines"][0], dtype=float)
        rim_axial = (rim_pts - center) @ normal
        if float(np.max(np.abs(rim_axial))) <= 1e-3:
            failures.append("PURE: lifted grid has no axial offset (not laid on the bowl)")
        flat_rim = np.asarray(real_lines[0], dtype=float)
        if float(np.max(np.abs((flat_rim - center) @ normal))) > 1e-6:
            failures.append("PURE: the un-lifted grid should stay in the image plane (no axial offset)")

    # Degenerate inputs -> None.
    if build_distortion_grid([0.0], [0.0], center=center, normal=normal, tangent=tangent) is not None:
        failures.append("PURE: <2 radii did not return None")
    if build_distortion_grid([0.0, 0.0], [0.0, 0.0], center=center, normal=normal, tangent=tangent) is not None:
        failures.append("PURE: zero image radius did not return None")


def _check_integration(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle = _build_scene_bundle_for_double_gauss()
    if editor is None:
        notes.append("SKIP integration: double-gauss layout/bundle unavailable")
        return
    spec = editor.distortion_grid_overlay_spec(system, bundle)
    if spec is None:
        failures.append("INTEGRATION: distortion_grid_overlay_spec returned None on the double gauss")
        return
    max_pct = float(spec.get("max_distortion_pct", 0.0))
    if not (0.1 < max_pct < 10.0):
        failures.append(f"INTEGRATION: double-gauss max distortion {max_pct:.3g}% out of sane range")
    real_lines = spec.get("real_polylines") or []
    ideal_lines = spec.get("ideal_polylines") or []
    if not real_lines or len(real_lines) != len(ideal_lines):
        failures.append("INTEGRATION: missing/mismatched grid polylines")
        return
    # The real grid must genuinely differ from the ideal (some line bows).
    if max(_line_bow(line) for line in real_lines) <= 1e-4:
        failures.append("INTEGRATION: real grid identical to the rectilinear ideal (no warp drawn)")
    spec2 = editor.distortion_grid_overlay_spec(system, bundle)
    if spec2 is not spec:
        failures.append("INTEGRATION: distortion grid spec is not cached (recomputes the field scan)")
    notes.append(f"integration: double-gauss max distortion {max_pct:.3g}%, ×{float(spec.get('exaggeration', 1)):.0f}")


def _check_source_contracts(failures: list[str]) -> None:
    refresh_src = inspect.getsource(Open3DSceneRefreshService.refresh_scene)
    if "show_distortion_grid_var" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not read show_distortion_grid_var")
    if "_add_distortion_grid_overlays" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not call _add_distortion_grid_overlays")

    add_src = inspect.getsource(Kraken3DInspector._add_distortion_grid_overlays)
    for forbidden in ("build_system(", "_build_preview_system_rays_bundle("):
        if forbidden in add_src:
            failures.append(f"CONTRACT: _add_distortion_grid_overlays references {forbidden!r} -- not render-only")
    add_code = Kraken3DInspector._add_distortion_grid_overlays.__code__
    shadowed = [g for g in ("pv", "np", "vtkBillboardTextActor3D") if g in add_code.co_varnames]
    if shadowed:
        failures.append(f"CONTRACT: _add_distortion_grid_overlays shadows module globals {shadowed} with locals")

    handler_src = inspect.getsource(Kraken3DInspector._on_scene_visibility_changed)
    if "can_reuse_current_scene_for_display_toggle" not in handler_src:
        failures.append("CONTRACT: the Distortion toggle would rebuild -- handler lost the bugs/0166 gate")


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
        print("[FAIL] 3D distortion grid-warp overlay")
        return 1
    print("[PASS] distortion grid warps a rectilinear grid into its real image (idea #2, 2nd half)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
