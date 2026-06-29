"""Display-free guard: the FOLDED MV-150 coaxial area-LED layout traces the real beam path.

Companion to ``validate_open3d_coaxial_led_dark_edges`` (the UNFOLDED quantitative
relative-illumination reference). This guard covers ``machine_vision_150mm_coaxial_led_folded``
-- the VISUAL layout that renders the actual folded coaxial path the user sees on the floor:

    area LED (side port) -> reflect off the 45 deg BS diagonal -> down to the FOV object ->
    diffuse scatter back up -> transmit through the BS -> imaging lens + camera.

It is display-free and asserts:
  1. STRUCTURAL contract -- a side-port (-X) Random rectangle LED outside the +X BS face, a
     Beam Splitter surface tilted to fold -X -> -Z (the MV-150 cube's diagonal), a Diffuse
     Object on the reflected arm, and "Beam-splitter paths" ray display.
  2. FOLD GEOMETRY (near-collimated probe) -- the reflected beam illuminates the FOV object
     across an AREA (not a single point, i.e. the fold direction is correct) whose extents map
     the LED 55 mm fold dimension onto object X and the 78 mm perp dimension onto object Y. A
     radius_x/radius_y swap (the easy mistake after the -X->-Z fold) would put the wide 78 mm
     on X instead, so the guard asserts fold(X) < perp(Y).
  3. END-TO-END -- with the as-shipped 30 deg LED cone the full branched diffuse double-pass
     still reaches the image plane (rays complete LED -> BS -> object -> back -> BS -> image).

The quantitative 0.66 fold dark-edge ratio lives in the UNFOLDED guard; here the BS aperture
is not yet the limiting stop (a follow-up), so this guard checks the PATH, not the dip.
"""
from __future__ import annotations

import os

import numpy as np

# Low ray budgets: the diffuse double-pass fans each launched ray into many paths, so a small
# seeded count is enough to populate the footprint while keeping the phase quick.
_GEO_RAYS = int(os.environ.get("COAXIAL_FOLDED_GEO_RAYS", "40"))
_E2E_RAYS = int(os.environ.get("COAXIAL_FOLDED_E2E_RAYS", "24"))
_GEO_CONE_DEG = 2.0  # near-collimated, to isolate the LED-size->object mapping from cone spread


def _load_layout():
    from KrakenOS.common_optical_layouts import machine_vision_150mm_coaxial_led_folded as layout

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
    direction = [float(v) for v in (src.get("direction") or [0.0, 0.0, 0.0])]
    if not (direction[0] < -0.9 and abs(direction[1]) < 0.1 and abs(direction[2]) < 0.1):
        notes.append(f"LED not a -X side port: direction={direction}")
        ok = False
    origin = [float(v) for v in (src.get("origin") or [0.0, 0.0, 0.0])]
    if not (origin[0] > 0.0):
        notes.append(f"LED origin not outside the +X face: origin={origin}")
        ok = False
    # radius_x -> world Y (perp, 78), radius_y -> world Z -> object X (fold, 55): perp must be wider.
    radius_x = float(src.get("radius_x", 0.0))  # perp half (Y)
    radius_y = float(src.get("radius_y", 0.0))  # fold half (via Z)
    if not (0.0 < radius_y < radius_x):
        notes.append(
            f"source half-widths not perp>fold: radius_x(perp)={radius_x}, radius_y(fold)={radius_y}"
        )
        ok = False

    bs = layout.SURFACES[1]
    if str(bs.get("surface")) != "Beam Splitter":
        notes.append(f"row 1 is {bs.get('surface')!r}, expected 'Beam Splitter'")
        ok = False
    # Normal must fold -X -> -Z: that needs tilt about Y of -45 (normal [-0.707,0,+0.707]).
    if abs(float(bs.get("tilt_y", 0.0)) + 45.0) > 1.0:
        notes.append(f"BS tilt_y={bs.get('tilt_y')} (need -45 to fold -X -> -Z)")
        ok = False
    if "BeamSplitter" not in (bs.get("advanced") or {}):
        notes.append("BS surface lacks BeamSplitter advanced settings")
        ok = False

    diffuse = None
    for s in layout.SURFACES:
        if str(s.get("surface")) == "Diffuse Object":
            diffuse = s
            break
    if diffuse is None:
        notes.append("no Diffuse Object surface on the reflected arm")
        ok = False
    elif "DiffuseScatter" not in (diffuse.get("advanced") or {}):
        notes.append("Diffuse Object lacks DiffuseScatter advanced settings")
        ok = False

    if str(settings.get("ray_display_mode")) != "Beam-splitter paths":
        notes.append(f"ray_display_mode={settings.get('ray_display_mode')!r}, expected 'Beam-splitter paths'")
        ok = False
    if str(settings.get("trace_mode")) != "Non-Sequential Preview":
        notes.append(f"trace_mode={settings.get('trace_mode')!r}, expected 'Non-Sequential Preview'")
        ok = False
    return ok


def _trace_surface_samples(layout, surface_indices, ray_count, cone_override=None):
    """Run the REAL in-app scene-source non-seq trace and return ``{idx: (x, y)}`` hit samples
    (mm) on each requested surface -- the same plumbing the inspector renders and the
    relative-illumination map bins (build_scene_bundle -> _source_illumination_hit_samples)."""
    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
    from KrakenOS.UI.scene_builder import build_scene_bundle

    settings = dict(layout.SETTINGS)
    src_specs = [dict(s) for s in settings["scene_sources"]]
    src_specs[0]["ray_count"] = int(ray_count)
    if cone_override is not None:
        src_specs[0]["cone_deg"] = float(cone_override)
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
        ray_count_per_field=max((getattr(s, "ray_count", 1) for s in sources), default=1),
    )
    editor.last_system = system
    editor.last_rays = rays
    editor._last_scene_bundle = bundle
    recs = editor._ray_analysis_records_for_trace(system=system, rays=rays)
    out = {}
    for idx in surface_indices:
        samples = editor._source_illumination_hit_samples(system, idx, ray_records=recs)
        out[idx] = (
            np.asarray(samples.get("x", []), dtype=float),
            np.asarray(samples.get("y", []), dtype=float),
        )
    return out


def _object_index(layout) -> int:
    for i, s in enumerate(layout.SURFACES):
        if str(s.get("surface")) == "Diffuse Object":
            return i
    return -1


def _check_fold_geometry(layout, notes: list[str]) -> bool:
    """Near-collimated probe: the reflected beam must illuminate the FOV object across an area
    whose X (fold) extent ~ 55 mm and Y (perp) extent ~ 78 mm, with fold < perp (no swap)."""
    obj_idx = _object_index(layout)
    img_idx = len(layout.SURFACES) - 1
    if obj_idx < 0:
        notes.append("could not locate the Diffuse Object surface")
        return False
    try:
        samples = _trace_surface_samples(
            layout, [obj_idx, img_idx], _GEO_RAYS, cone_override=_GEO_CONE_DEG
        )
    except Exception as exc:  # pragma: no cover - trace/build failure
        notes.append(f"near-collimated trace raised: {exc!r}")
        return False
    ox, oy = samples[obj_idx]
    if ox.size < 20:
        notes.append(f"FOV object under-illuminated ({ox.size} hits) -> fold direction wrong?")
        return False
    fold_ext = float(ox.max() - ox.min())  # object X = fold
    perp_ext = float(oy.max() - oy.min())  # object Y = perp
    want_fold = 2.0 * float(layout.LED_HALF_X)  # 55
    want_perp = 2.0 * float(layout.LED_HALF_Y)  # 78
    notes.append(
        f"object footprint (collimated): fold(X)={fold_ext:.1f} (~{want_fold:.0f}) "
        f"perp(Y)={perp_ext:.1f} (~{want_perp:.0f})"
    )
    ok = True
    if not (0.80 * want_fold <= fold_ext <= 1.25 * want_fold):
        notes.append(f"fold(X) extent {fold_ext:.1f} off target {want_fold:.0f}")
        ok = False
    if not (0.80 * want_perp <= perp_ext <= 1.25 * want_perp):
        notes.append(f"perp(Y) extent {perp_ext:.1f} off target {want_perp:.0f}")
        ok = False
    if not (fold_ext < perp_ext):
        notes.append(
            f"footprint not fold<perp ({fold_ext:.1f} vs {perp_ext:.1f}) -> radius_x/radius_y swapped"
        )
        ok = False
    return ok


def _check_end_to_end(layout, notes: list[str]) -> bool:
    """As-shipped 30 deg cone: the full branched diffuse double-pass must still reach the image."""
    img_idx = len(layout.SURFACES) - 1
    try:
        samples = _trace_surface_samples(layout, [img_idx], _E2E_RAYS, cone_override=None)
    except Exception as exc:  # pragma: no cover - trace/build failure
        notes.append(f"as-shipped trace raised: {exc!r}")
        return False
    ix, iy = samples[img_idx]
    notes.append(f"as-shipped (30 deg cone) image-plane hits: {ix.size}")
    if ix.size < 20:
        notes.append(
            f"folded path does not reach the image ({ix.size} hits) -> branched double-pass broken"
        )
        return False
    return True


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    try:
        layout = _load_layout()
    except Exception as exc:  # pragma: no cover - import failure
        return False, [f"layout import raised: {exc!r}"]

    passed = True
    passed &= _check_structural(layout, notes)
    passed &= _check_fold_geometry(layout, notes)
    passed &= _check_end_to_end(layout, notes)
    return bool(passed), notes


def main() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(("OK   " if passed else "NOTE ") + note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
