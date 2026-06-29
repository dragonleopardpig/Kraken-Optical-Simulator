"""Display-free guard: the MV-150 coaxial area-LED layout reproduces the 2 dark edges.

Feature (user Q4/Q5): a 55x78 mm area LED illuminates a 39x39 mm FOV coaxially through a
beam-splitter cube; the 25 MP image shows 2 DARK EDGES on one axis and stays uniform on the
other, because the fold-axis BS clear-aperture stop (~30 mm) UNDER-fills the 39 mm FOV while
the perp-axis 78 mm stop covers it. The unfolded on-axis layout
``machine_vision_150mm_coaxial_led`` feeds the in-app "Relative illumination" analysis, whose
2-D hit-power map must therefore dip at the fold (X) FOV edges and stay flat on the perp (Y)
edges.

This guard is display-free. It asserts:
  1. STRUCTURAL contract -- asymmetric rectangle source (radius_x != radius_y), rectangular
     BS-exit UDA whose fold half-width under-fills the FOV while the perp half covers it, and
     ``relative_illumination`` enabled.
  2. The rectangular UDA clips as a rectangle (a point just past the fold half is rejected, a
     point just inside the perp half is accepted) -- the mechanism that carves the dark edges.
  3. The "Random rectangle source" samples a true W x H rectangle (fold/perp extents differ;
     corners populated -> not a disk/ellipse).
  4. PHYSICS -- the closed-form coverage (umbra-pinch) model on the layout's own geometry
     yields a fold-axis FOV edge clearly DARK (~0.66 of centre) while the perp axis stays
     UNIFORM (~1.00).  This is exact and deterministic: from a FOV point X the visible source
     measure through the stop is the length of the ray-slope window that simultaneously clears
     the source half-width, the stop half-width and the emission cone.  (The in-app Monte-Carlo
     relative-illumination map traces this same geometry; a 2-D histogram adds a radial cone
     "bowl" that compresses the dip in a naive marginal, so the deterministic per-axis coverage
     is the robust regression signal.  The end-to-end trace is verified manually -- see
     bugs/0179_coaxial_led_dark_edges.md.)
"""
from __future__ import annotations

import os

import numpy as np

# Ray budget for the decisive end-to-end trace check (bugs/0179). The scene-source
# sampler is seeded (``source_seed``), so this trace is deterministic; 8000 rays give
# a stable fold/perp strip ratio with a wide margin while keeping the phase quick.
_TRACE_RAYS = int(os.environ.get("COAXIAL_TRACE_RAYS", "8000"))


def _load_layout():
    from KrakenOS.common_optical_layouts import machine_vision_150mm_coaxial_led as layout

    return layout


def _check_structural(layout, notes: list[str]) -> bool:
    ok = True
    settings = layout.SETTINGS
    sources = settings.get("scene_sources") or []
    if not sources:
        notes.append("layout has no scene_sources")
        return False
    src = sources[0]
    if str(src.get("model")) != "Random rectangle source":
        notes.append(f"source model is {src.get('model')!r}, expected 'Random rectangle source'")
        ok = False
    radius_x = float(src.get("radius_x", 0.0))
    radius_y = float(src.get("radius_y", 0.0))
    if not (0.0 < radius_x < radius_y):
        notes.append(f"source not asymmetric W<H: radius_x={radius_x}, radius_y={radius_y}")
        ok = False

    half_fov = float(layout.FOV_MM) / 2.0
    stop = layout.SURFACES[1]
    uda = stop.get("uda") or {}
    if str(uda.get("kind", "")).lower() not in {"rectangle", "rectangle_uda", "uda_rectangle"}:
        notes.append(f"BS-exit surface lacks a rectangle UDA: {uda!r}")
        return ok and False
    stop_half_x = float(uda.get("half_x", 0.0))
    stop_half_y = float(uda.get("half_y", 0.0))
    if not (stop_half_x < half_fov):
        notes.append(f"fold stop does not under-fill the FOV: half_x={stop_half_x} >= {half_fov}")
        ok = False
    if not (stop_half_y >= half_fov):
        notes.append(f"perp stop does not cover the FOV: half_y={stop_half_y} < {half_fov}")
        ok = False
    if not (stop_half_x < stop_half_y):
        notes.append(f"stop not asymmetric fold<perp: half_x={stop_half_x}, half_y={stop_half_y}")
        ok = False
    if "relative_illumination" not in (settings.get("analysis_modes") or []):
        notes.append("analysis_modes lacks 'relative_illumination'")
        ok = False
    return ok


def _point_in_polygon(px: float, py: float, xs, ys) -> bool:
    inside = False
    count = len(xs)
    j = count - 1
    for i in range(count):
        xi, yi, xj, yj = xs[i], ys[i], xs[j], ys[j]
        if (yi > py) != (yj > py):
            x_cross = (xj - xi) * (py - yi) / ((yj - yi) or 1e-30) + xi
            if px < x_cross:
                inside = not inside
        j = i
    return inside


def _check_uda_clips(layout, notes: list[str]) -> bool:
    from KrakenOS.UI.custom_surfaces import decode_custom_surface_value

    uda = dict(layout.SURFACES[1]["uda"])
    half_x = float(uda.get("half_x"))
    half_y = float(uda.get("half_y"))
    decoded = decode_custom_surface_value(uda)
    try:
        xs = list(np.asarray(decoded[0], dtype=float))
        ys = list(np.asarray(decoded[1], dtype=float))
    except Exception as exc:
        notes.append(f"rectangle UDA did not decode to a polygon: {exc!r}")
        return False
    ok = True
    # Just OUTSIDE the fold half (the clipping edge that carves the dark edges) -> rejected.
    if _point_in_polygon(half_x + 0.5, 0.0, xs, ys):
        notes.append(f"UDA accepts a point past the fold half_x={half_x} (no fold clipping)")
        ok = False
    # Just inside the perp half, past the fold half -> accepted only because perp is wider.
    if not _point_in_polygon(0.0, half_y - 0.5, xs, ys):
        notes.append(f"UDA rejects a point inside the perp half_y={half_y} (perp not open)")
        ok = False
    # A point outside the perp half -> rejected.
    if _point_in_polygon(0.0, half_y + 0.5, xs, ys):
        notes.append(f"UDA accepts a point past the perp half_y={half_y}")
        ok = False
    return ok


def _check_source_fill(layout, notes: list[str]) -> bool:
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
    from KrakenOS.UI.source_trace_helpers import build_scene_source_bundle

    settings = dict(layout.SETTINGS)
    rows = _rows_from_layout_info({"surfaces": layout.SURFACES, "settings": settings})
    editor = _snapshot_editor(rows, settings)
    sources = editor._collect_scene_sources(wavelength=float(settings["wavelength"]))
    if not sources:
        notes.append("no scene sources collected from the layout")
        return False
    bundle = build_scene_source_bundle(sources[0])
    if bundle is None:
        notes.append("rectangle source bundle is None")
        return False
    px = np.asarray(bundle[0], dtype=float)
    py = np.asarray(bundle[1], dtype=float)
    if px.size < 100:
        notes.append(f"rectangle source produced too few points: {px.size}")
        return False
    ok = True
    ext_x, ext_y = float(np.max(np.abs(px))), float(np.max(np.abs(py)))
    want_x, want_y = float(layout.LED_HALF_X), float(layout.LED_HALF_Y)
    if not (0.85 * want_x <= ext_x <= 1.02 * want_x):
        notes.append(f"fold extent {ext_x:.1f} off target {want_x}")
        ok = False
    if not (0.85 * want_y <= ext_y <= 1.02 * want_y):
        notes.append(f"perp extent {ext_y:.1f} off target {want_y}")
        ok = False
    if ext_y <= ext_x:
        notes.append(f"source not asymmetric: fold extent {ext_x:.1f} >= perp extent {ext_y:.1f}")
        ok = False
    # Corners populated -> a filled rectangle, not a disk/ellipse/diamond.
    corner = np.count_nonzero((np.abs(px) > 0.8 * want_x) & (np.abs(py) > 0.8 * want_y))
    if corner < 0.02 * px.size:
        notes.append(f"rectangle corners under-populated ({corner}/{px.size}) -> not a rectangle")
        ok = False
    return ok


def _axis_edge_over_centre(half_source, half_stop, z_src_to_fov, d_stop_to_fov, cone_deg, fov_half):
    """Closed-form coverage ratio edge/centre for one axis (umbra-pinch window model).

    A ray leaving the source at offset ``xs`` with slope ``t`` reaches FOV point ``X`` when
    ``xs = X - z_src_to_fov*t`` and crosses the stop at ``X - d_stop_to_fov*t``.  The FOV
    irradiance at X (uniform-solid-angle emission) is the length of the slope window that
    simultaneously satisfies |source|, |stop| and the |cone| bound -- the visible-source
    measure.  edge/centre < 1 means the stop (or cone) under-fills that FOV point.
    """
    tan_cone = float(np.tan(np.deg2rad(float(cone_deg))))

    def window(point: float) -> float:
        lo = max(
            (point - half_stop) / d_stop_to_fov,
            (point - half_source) / z_src_to_fov,
            -tan_cone,
        )
        hi = min(
            (point + half_stop) / d_stop_to_fov,
            (point + half_source) / z_src_to_fov,
            tan_cone,
        )
        return max(hi - lo, 0.0)

    centre = window(0.0)
    edge = window(float(fov_half))
    return (edge / centre) if centre > 1e-12 else 0.0, centre


def _check_physics(layout, notes: list[str]) -> bool:
    """Deterministic coverage physics on the layout's own geometry (no Monte-Carlo trace)."""
    fov_half = float(layout.FOV_MM) / 2.0
    z_src_to_fov = float(layout.LED_TO_STOP) + float(layout.STOP_TO_FOV)
    d_stop_to_fov = float(layout.STOP_TO_FOV)
    cone_deg = float(layout.LED_CONE_DEG)

    fold_ratio, fold_centre = _axis_edge_over_centre(
        float(layout.LED_HALF_X), float(layout.STOP_HALF_X),
        z_src_to_fov, d_stop_to_fov, cone_deg, fov_half,
    )
    perp_ratio, perp_centre = _axis_edge_over_centre(
        float(layout.LED_HALF_Y), float(layout.STOP_HALF_Y),
        z_src_to_fov, d_stop_to_fov, cone_deg, fov_half,
    )
    notes.append(
        f"coverage fold edge/centre={fold_ratio:.3f} perp edge/centre={perp_ratio:.3f} "
        f"(centre widths fold={fold_centre:.3f} perp={perp_centre:.3f})"
    )
    ok = True
    if not (fold_centre > 1e-9 and perp_centre > 1e-9):
        notes.append("degenerate centre coverage window (geometry collapsed)")
        return False
    if not (fold_ratio <= 0.75):
        notes.append(f"fold FOV edge not dark enough: edge/centre={fold_ratio:.3f} (>0.75)")
        ok = False
    if not (perp_ratio >= 0.90):
        notes.append(f"perp FOV edge not uniform: edge/centre={perp_ratio:.3f} (<0.90)")
        ok = False
    if not (perp_ratio - fold_ratio >= 0.20):
        notes.append(
            f"fold not clearly darker than perp: {fold_ratio:.3f} vs {perp_ratio:.3f} (<0.20 gap)"
        )
        ok = False
    return ok


def _trace_fov_hit_samples(layout, stop_half_x, ray_count):
    """Run the REAL in-app scene-source trace at the given fold stop half-width and return
    the FOV-plane hit samples ``(x, y)`` in mm that the relative-illumination map is built
    from (build_scene_bundle -> _source_illumination_hit_samples).  This exercises the exact
    non-sequential plumbing the user's analysis uses."""
    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
    from KrakenOS.UI.scene_builder import build_scene_bundle

    settings = dict(layout.SETTINGS)
    src_specs = [dict(s) for s in settings["scene_sources"]]
    src_specs[0]["ray_count"] = int(ray_count)
    settings["scene_sources"] = src_specs
    surfaces = [dict(s) for s in layout.SURFACES]
    surfaces[1] = dict(surfaces[1])
    uda = dict(surfaces[1]["uda"])
    uda["half_x"] = float(stop_half_x)
    surfaces[1]["uda"] = uda

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
    editor.last_system = system
    editor.last_rays = rays
    editor._last_scene_bundle = bundle
    image_index = len(rows) - 1
    recs = editor._ray_analysis_records_for_trace(system=system, rays=rays)
    samples = editor._source_illumination_hit_samples(system, image_index, ray_records=recs)
    return (
        np.asarray(samples.get("x", []), dtype=float),
        np.asarray(samples.get("y", []), dtype=float),
    )


def _strip_edge_over_centre(along, perp, fov_half, strip=5.0, nb=13):
    """Edge/centre ratio of the ``along``-axis profile within a central ``perp`` strip.  The
    strip isolates one axis from the orthogonal 2-D cone bowl (the robust per-axis signal)."""
    edges = np.linspace(-fov_half, fov_half, nb + 1)
    cen = 0.5 * (edges[:-1] + edges[1:])
    prof, _ = np.histogram(along[np.abs(perp) <= strip], bins=edges)
    centre = prof[np.abs(cen) <= 4.5].mean()
    edge = prof[np.abs(cen) >= 13.5].mean()
    return (edge / centre) if centre > 0 else 0.0


def _check_in_app_trace(layout, notes: list[str]) -> bool:
    """DECISIVE end-to-end check (bugs/0179): the in-app relative-illumination sampler must
    show the fold-axis FOV edge DARK while the perp axis stays uniform.

    The deterministic coverage model (``_check_physics``) passed even while the real
    non-sequential trace shot rays straight THROUGH the rectangular UDA stop and then
    mislabeled vignetted terminals as image hits -- so the analytic check alone never caught
    that the user's map stayed flat.  This traces the actual pipeline and measures the dip.
    """
    try:
        x, y = _trace_fov_hit_samples(layout, float(layout.STOP_HALF_X), _TRACE_RAYS)
    except Exception as exc:  # pragma: no cover - trace/build failure
        notes.append(f"in-app trace raised: {exc!r}")
        return False
    if x.size < 200:
        notes.append(f"in-app trace produced too few FOV hits ({x.size}) to measure dark edges")
        return False
    fov_half = float(layout.FOV_MM) / 2.0
    fold = _strip_edge_over_centre(x, y, fov_half)  # fold = X profile, central Y strip
    perp = _strip_edge_over_centre(y, x, fov_half)  # perp = Y profile, central X strip
    notes.append(
        f"in-app trace ({x.size} FOV hits, {_TRACE_RAYS} launched) "
        f"fold(X) edge/centre={fold:.3f} perp(Y) edge/centre={perp:.3f}"
    )
    ok = True
    if not (fold <= 0.85):
        notes.append(f"in-app fold FOV edge not dark: edge/centre={fold:.3f} (>0.85) -> UDA stop not vignetting")
        ok = False
    if not (perp >= 0.85):
        notes.append(f"in-app perp FOV edge not uniform: edge/centre={perp:.3f} (<0.85)")
        ok = False
    if not (perp - fold >= 0.12):
        notes.append(f"in-app fold not clearly darker than perp: {fold:.3f} vs {perp:.3f} (<0.12 gap)")
        ok = False
    return ok


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    try:
        layout = _load_layout()
    except Exception as exc:  # pragma: no cover - import/build failure
        return False, [f"layout import raised: {exc!r}"]

    passed = True
    passed &= _check_structural(layout, notes)
    passed &= _check_uda_clips(layout, notes)
    passed &= _check_source_fill(layout, notes)
    passed &= _check_physics(layout, notes)
    passed &= _check_in_app_trace(layout, notes)
    return bool(passed), notes


def main() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(("OK   " if passed else "NOTE ") + note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
