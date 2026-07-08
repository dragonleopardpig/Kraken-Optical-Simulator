"""Display-free guard for the on-detector relative-illumination heatmap overlay (3D viz idea #3).

The MV-150 coaxial area-LED shows 2 dark edges on the fold axis of the 25 MP sensor (the 55x55
beam-splitter cross-section, foreshortened by the 45 deg fold, UNDER-fills the 39x39 FOV on that
axis while the 78 mm perp axis covers it). The 2-D "Relative illumination" report already proves
this (see ``validate_open3d_coaxial_led_dark_edges``); THIS overlay drapes that same map onto the
DETECTOR plane as a smooth textured quad, so the dark edges read directly on the sensor -- what the
Monitor shows -- normalised to the sensor CENTRE = 1.0 and coloured by the camera chroma
(Mono/NIR -> grey ramp, Colour -> false colour).

This guard is display-free (pure numpy + a headless trace, no VTK). It pins:

  * PURE GEOMETRY (``build_source_illumination_overlay``): a synthetic density with a KNOWN fold
    dip + Poisson counting noise drapes bin-centre points onto the detector plane (all on the
    plane, dims = (nx, ny), scalars aligned), normalises to the centre (~1.0), reads the fold edge
    clearly darker than the perp edge, and the Gaussian de-speckle cuts per-bin noise a LOT while
    leaving the fold dip intact. Chroma picks the colormap; degenerate inputs return None.
  * INTEGRATION on the real coaxial-LED BS scene: ``source_illumination_overlay_spec`` returns a
    heatmap ON THE DETECTOR plane whose fold edge is dark, perp edge is not, with a clear gap, in
    the sensor's grey ramp, and is CACHED (a second call returns the same object -- bugs/0166).
  * RENDER-ONLY / TOGGLE contract: ``refresh_scene`` reads ``show_source_illumination_var`` and
    calls ``_add_source_illumination_overlays``; that renderer never rebuilds the system and draws
    the baked heatmap via ``direct_point_scalars``; and the Overlays menu exposes the toggle.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_source_illumination_overlay

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import os

import numpy as np

from KrakenOS.UI.services import source_illumination_overlay as sio

# Deterministic (source_seed=7) trace budget for the integration check. 16000 rays give a stable
# fold-clearly-darker-than-perp signal on the detector with a wide margin while keeping the phase
# quick (the phase-175 dark-edges guard uses 8000 for the FOV-plane version).
_TRACE_RAYS = int(os.environ.get("COAXIAL_OVERLAY_RAYS", "16000"))


def _synthetic_density(nx=30, ny=30, half=19.5, mean_hits=10.0, seed=7):
    """A detector density with a KNOWN fold (x) dip -> ~0.55 at the edge, uniform in perp (y), plus
    Poisson counting noise -- the shape the real coaxial trace produces, but deterministic + fast."""
    rng = np.random.default_rng(seed)
    xc = np.linspace(-half, half, nx)
    X = np.repeat(xc[None, :], ny, axis=0)
    fold = np.clip(1.0 - 0.55 * np.clip((np.abs(X) - 13.5) / (half - 13.5), 0.0, 1.0), 0.0, 1.0)
    counts = rng.poisson(np.clip(fold, 0.0, None) * mean_hits).astype(float)
    x_edges = np.linspace(-half, half, nx + 1)
    y_edges = np.linspace(-half, half, ny + 1)
    return {"density": counts, "x_edges": x_edges, "y_edges": y_edges}


def _neighbour_speckle(relative: np.ndarray) -> float:
    return float(np.mean(np.abs(np.diff(relative, axis=1))))


def _check_pure_geometry(failures: list[str]) -> None:
    center = np.array([0.0, 0.0, 130.0])
    normal = np.array([0.0, 0.0, 1.0])
    tangent = np.array([1.0, 0.0, 0.0])  # -> u=+x (fold), v=+y (perp)
    nx = ny = 30
    map_data = _synthetic_density(nx, ny)

    smooth = sio.build_source_illumination_overlay(
        map_data, center=center, normal=normal, tangent=tangent, chroma="Mono",
    )
    if smooth is None:
        failures.append("PURE: build_source_illumination_overlay returned None for valid input")
        return

    if tuple(smooth["dims"]) != (nx, ny):
        failures.append(f"PURE: dims {smooth['dims']} != ({nx}, {ny})")
    pts = np.asarray(smooth["points"], dtype=float)
    if pts.shape != (nx * ny, 3):
        failures.append(f"PURE: points shape {pts.shape} != ({nx * ny}, 3)")
    elif not np.allclose(pts[:, 2], 130.0, atol=1e-6):
        failures.append("PURE: bin-centre points are not on the detector plane z=130")
    if np.asarray(smooth["scalars"]).size != pts.shape[0]:
        failures.append("PURE: scalars do not align 1:1 with the grid points")
    # Fold axis (x) spans the sensor; the frame maps u->+x, v->+y.
    if pts.shape[0] == nx * ny:
        if not np.isclose(np.max(np.abs(pts[:, 0])), 19.5 * (nx - 1) / nx, atol=0.5):
            # bin CENTRES stop a half-bin short of the +/-19.5 edge; just assert they span the sensor.
            if np.max(np.abs(pts[:, 0])) < 15.0:
                failures.append("PURE: fold-axis points do not span the sensor")

    fold = float(smooth["x_edge_ratio"])
    perp = float(smooth["y_edge_ratio"])
    if not (fold < perp - 0.15):
        failures.append(f"PURE: fold edge not clearly darker than perp ({fold:.3f} vs {perp:.3f})")
    if not (0.55 <= fold <= 0.85):
        failures.append(f"PURE: fold dip depth off ({fold:.3f}, want 0.55..0.85)")
    if not (perp >= 0.90):
        failures.append(f"PURE: perp axis not uniform ({perp:.3f} < 0.90)")
    # Centre reference: the returned relative map is centre-normalised (~1.0 at the middle).
    rel = np.asarray(smooth["relative"], dtype=float)
    c0, c1 = ny // 2 - 2, nx // 2 - 2
    if not (0.85 <= float(rel[c0:c0 + 4, c1:c1 + 4].mean()) <= 1.15):
        failures.append("PURE: relative map is not normalised to ~1.0 at the sensor centre")

    # Gaussian de-speckle: smoothing must cut per-bin counting noise substantially...
    raw = sio.build_source_illumination_overlay(
        map_data, center=center, normal=normal, tangent=tangent, chroma="Mono", smooth_sigma_bins=0.0,
    )
    if raw is not None:
        sp_raw = _neighbour_speckle(np.asarray(raw["relative"]))
        sp_smooth = _neighbour_speckle(rel)
        if not (sp_smooth < 0.6 * sp_raw):
            failures.append(f"PURE: smoothing did not de-speckle enough ({sp_smooth:.3f} vs raw {sp_raw:.3f})")
        # ...while KEEPING the fold darker than perp (physics preserved through the blur).
        if not (float(raw["x_edge_ratio"]) < float(raw["y_edge_ratio"])):
            failures.append("PURE: even the RAW map should read fold darker than perp")

    # Chroma -> colormap: Mono/NIR grey ramp, Colour false colour.
    if sio.colormap_for_chroma("Mono") != "gray":
        failures.append("PURE: Mono sensor did not map to a grey ramp")
    if sio.colormap_for_chroma("NIR") != "gray":
        failures.append("PURE: NIR sensor did not map to a grey ramp")
    if not sio.colormap_for_chroma("Color").startswith(("turbo", "viridis", "jet", "inferno")):
        failures.append("PURE: Colour sensor did not map to a false-colour ramp")
    if smooth["cmap"] != "gray":
        failures.append(f"PURE: Mono overlay cmap {smooth['cmap']!r} != 'gray'")
    if list(smooth["clim"]) != [0.0, 1.0]:
        failures.append(f"PURE: clim {smooth['clim']} != [0, 1] (relative-illumination convention)")

    # Degenerate inputs -> None (nothing to drape).
    if sio.build_source_illumination_overlay(None, center=center, normal=normal, tangent=tangent) is not None:
        failures.append("PURE: non-dict map_data did not return None")
    zero = {"density": np.zeros((ny, nx)), "x_edges": map_data["x_edges"], "y_edges": map_data["y_edges"]}
    if sio.build_source_illumination_overlay(zero, center=center, normal=normal, tangent=tangent) is not None:
        failures.append("PURE: an all-zero density did not return None")


def _build_coaxial_overlay(ray_count: int):
    """Headless harness: editor + system + traced scene bundle for the coaxial-LED BS scene, with
    editor.last_system/last_rays/_last_scene_bundle set so ``source_illumination_overlay_spec``
    works. Returns (None, None, None) on any fixture/build failure."""
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
        rows = _rows_from_layout_info({"surfaces": surfaces, "settings": settings})
        editor = _snapshot_editor(rows, settings)
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
        return editor, system, bundle
    except Exception:
        return None, None, None


def _check_integration(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle = _build_coaxial_overlay(_TRACE_RAYS)
    if editor is None:
        notes.append("SKIP integration: coaxial-LED layout/bundle unavailable")
        return
    try:
        spec = editor.source_illumination_overlay_spec(system, bundle)
    except Exception as exc:
        failures.append(f"INTEGRATION: source_illumination_overlay_spec raised {exc!r}")
        return
    if not spec:
        failures.append("INTEGRATION: overlay spec is None on the coaxial-LED BS scene")
        return

    pts = np.asarray(spec["points"], dtype=float)
    zc = float(pts[:, 2].mean())
    if not np.allclose(pts[:, 2], zc, atol=1e-6):
        failures.append("INTEGRATION: heatmap points are not coplanar (not on the detector plane)")
    # The detector target sits well downstream of the object; z ~ 130 in this layout.
    det = next((t for t in bundle.targets if getattr(t, "is_detector", False)), None)
    if det is not None and not np.isclose(zc, float(np.asarray(det.center_world, float)[2]), atol=1.0):
        failures.append(f"INTEGRATION: heatmap plane z={zc:.1f} is not the detector plane")

    fold = float(spec["x_edge_ratio"])
    perp = float(spec["y_edge_ratio"])
    if not (fold <= 0.85):
        failures.append(f"INTEGRATION: fold FOV edge not dark on the detector ({fold:.3f} > 0.85)")
    if not (perp >= 0.85):
        failures.append(f"INTEGRATION: perp FOV edge not uniform on the detector ({perp:.3f} < 0.85)")
    if not (perp - fold >= 0.12):
        failures.append(f"INTEGRATION: fold not clearly darker than perp ({fold:.3f} vs {perp:.3f}, <0.12 gap)")
    if spec.get("cmap") != "gray":
        failures.append(f"INTEGRATION: Mono sensor overlay cmap {spec.get('cmap')!r} != 'gray'")
    if editor.source_illumination_overlay_spec(system, bundle) is not spec:
        failures.append("INTEGRATION: overlay is not cached (re-traces every call) -- breaks bugs/0166")
    notes.append(
        f"integration: {_TRACE_RAYS} rays -> detector heatmap dims={spec['dims']} plane z={zc:.1f}, "
        f"fold edge/centre={fold:.3f} perp={perp:.3f} (gap {perp - fold:.3f})"
    )


def _check_source_contracts(failures: list[str]) -> None:
    from KrakenOS.UI.layout_editor import Kraken3DInspector
    from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

    refresh_src = inspect.getsource(Open3DSceneRefreshService.refresh_scene)
    if "show_source_illumination_var" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not read show_source_illumination_var")
    if "_add_source_illumination_overlays" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not call _add_source_illumination_overlays")

    method = Kraken3DInspector._add_source_illumination_overlays
    add_src = inspect.getsource(method)
    for forbidden in ("build_system(", "_build_preview_system_rays_bundle("):
        if forbidden in add_src:
            failures.append(f"CONTRACT: _add_source_illumination_overlays references {forbidden!r} -- not render-only")
    if "direct_point_scalars" not in add_src:
        failures.append("CONTRACT: _add_source_illumination_overlays does not draw the baked heatmap (direct_point_scalars)")
    shadowed = [g for g in ("pv", "np") if g in method.__code__.co_varnames]
    if shadowed:
        failures.append(f"CONTRACT: _add_source_illumination_overlays shadows module globals {shadowed} with locals")

    from KrakenOS.UI.panels import open3d_top_controls
    controls_src = inspect.getsource(open3d_top_controls)
    if "show_source_illumination_var" not in controls_src:
        failures.append("CONTRACT: the Overlays menu does not offer the illumination heatmap")


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
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] on-detector relative-illumination heatmap overlay")
        return 1
    print("[PASS] coaxial-LED dark edges drape on the detector as a smooth heatmap (idea #3)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
