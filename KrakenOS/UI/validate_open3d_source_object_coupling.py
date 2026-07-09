"""Display-free guard: bugs/0274 (Stage 3, Option B) Source -> Object -> Detector coupling.

Stage 3 of the "Source + Object separation" feature: a marked face is an illumination SOURCE and
the object is a SCATTERER.  Option B factorizes the coupling -- trace the source onto the object
ONCE and bin its irradiance (reusing the 0259-0262 relative-illumination machinery), then weight
each object -> lens imaging ray by the local source irradiance at its object origin.  The source
non-uniformity (e.g. the MV-150 coaxial dark edges, bugs/0179) then rides the ACTUAL detector image,
not just the standalone "Relative illumination" overlay.

The coupling is ADDITIVE and read-only over the imaging trace: it only re-weights imaging rays for
display; it NEVER redefines the image plane / detector / optical axis (bugs/0266).

This guard is display-free.  It asserts:
  1. SYNTHETIC sampler math (no trace) -- ``sample_irradiance`` nearest-bins a hand-built map,
     returns the peak at centre, a dark value at the fold edge, the bright value at the (uniform)
     perp edge, and 0.0 off-grid / non-finite / for a ``None`` map; ``couple_imaging_records``
     multiplies a base weight by the sampled irradiance and skips records with no object origin.
  2. REAL trace on a portable coaxial-scatter fixture (built-in "Random rectangle source" + a
     Diffuse Object at the FOV plane + a detector) -- the object index auto-detects, coupling
     applies, the source -> object map is asymmetric (fold darker than perp), the coupled detector
     image shows the fold-axis dark edges while the perp axis stays uniform, coupling is NOT a
     no-op, and it DEEPENS the fold dip versus the un-coupled base.
  3. bugs/0266 GUARDRAIL -- coupling reuses the exact base detector samples (identical terminal
     x/y and identical un-coupled control weights); it only re-scales the display weight and never
     promotes the object/source to the image plane (object index != detector index).

The fixture is deterministic and rayfile-free: the scene source is seeded (``source_seed``) and the
Lambertian scatter directions are a golden-angle Fibonacci spiral (no RNG), so any GitHub clone
reproduces it with nothing to download.
"""
from __future__ import annotations

import copy
import os

import numpy as np

# Source rays launched by the portable fixture.  The scene source is seeded and the Lambertian
# scatter is a deterministic Fibonacci spiral, so this is reproducible; 800 rays spawn ~950 imaging
# rays (sample_count=7 children per object hit) -- enough for stable central-strip marginals while
# keeping the phase to ~10 s.
_TRACE_RAYS = int(os.environ.get("COUPLING_TRACE_RAYS", "800"))

_FOV_HALF = 19.5  # 39x39 mm FOV -> +/-19.5 mm detector window (fixture detector active area)


# --------------------------------------------------------------------------------------------------
# 1. Synthetic sampler-math check (no trace)
# --------------------------------------------------------------------------------------------------
def _synthetic_map():
    """A hand-built peak-normalized map: bright at centre, DARK at the fold (X) edges, UNIFORM on
    the perp (Y) axis -- the same structure the coaxial source imprints, but exact and trace-free."""
    x_edges = np.linspace(-20.0, 20.0, 9)  # 8 fold bins
    y_edges = np.linspace(-20.0, 20.0, 9)  # 8 perp bins
    x_centres = 0.5 * (x_edges[:-1] + x_edges[1:])
    # Fold profile: 1.0 at centre, rolling to 0.25 at the edges; independent of the perp axis.
    fold_profile = 0.25 + 0.75 * np.clip(1.0 - (np.abs(x_centres) / 17.5) ** 2, 0.0, 1.0)
    density = np.tile(fold_profile, (y_edges.size - 1, 1))  # [iy, ix], uniform down each column
    density = density / float(density.max())
    return {
        "density": density,
        "x_edges": x_edges,
        "y_edges": y_edges,
        "extent": [x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
        "coord": "local",
        "hit_count": 1000,
    }


class _FakeEditor:
    """Minimal stand-in so ``couple_imaging_records`` can resolve an object origin without a trace:
    a hit already carries its object-local (x, y)."""

    def _hit_local_xy(self, system, index, hit):
        return float(hit["x"]), float(hit["y"]), "local"


def _check_synthetic(notes: list[str]) -> bool:
    from KrakenOS.UI.services.source_object_coupling import (
        couple_imaging_records,
        imaging_ray_object_origin,
        sample_irradiance,
    )

    ok = True
    irr_map = _synthetic_map()
    density = irr_map["density"]

    centre = sample_irradiance(irr_map, 0.0, 0.0)
    fold_edge = sample_irradiance(irr_map, 17.5, 0.0)
    perp_edge = sample_irradiance(irr_map, 0.0, 17.5)
    notes.append(f"synthetic sample centre={centre:.3f} fold_edge={fold_edge:.3f} perp_edge={perp_edge:.3f}")
    if not (centre >= 0.99):
        notes.append(f"synthetic centre not peak: {centre:.3f} (<0.99)")
        ok = False
    if not (fold_edge <= 0.5):
        notes.append(f"synthetic fold edge not dark: {fold_edge:.3f} (>0.5)")
        ok = False
    if not (perp_edge >= 0.99):
        notes.append(f"synthetic perp edge not uniform: {perp_edge:.3f} (<0.99)")
        ok = False

    # Off-grid, non-finite and None-map all read 0.0 (no source light there).
    if sample_irradiance(irr_map, 100.0, 0.0) != 0.0:
        notes.append("synthetic off-grid (fold) sample not 0.0")
        ok = False
    if sample_irradiance(irr_map, 0.0, 100.0) != 0.0:
        notes.append("synthetic off-grid (perp) sample not 0.0")
        ok = False
    if sample_irradiance(irr_map, float("nan"), 0.0) != 0.0:
        notes.append("synthetic non-finite sample not 0.0")
        ok = False
    if sample_irradiance(None, 0.0, 0.0) != 0.0:
        notes.append("synthetic None-map sample not 0.0")
        ok = False

    # Nearest-bin correctness: a point inside a known bin returns that bin's density.
    probe_x, probe_y = -12.5, 2.5  # ix bin containing -12.5, iy bin containing 2.5
    ix = int(np.clip(np.digitize(probe_x, irr_map["x_edges"]) - 1, 0, density.shape[1] - 1))
    iy = int(np.clip(np.digitize(probe_y, irr_map["y_edges"]) - 1, 0, density.shape[0] - 1))
    got = sample_irradiance(irr_map, probe_x, probe_y)
    if not np.isclose(got, float(density[iy, ix])):
        notes.append(f"synthetic nearest-bin wrong: got {got:.3f}, expected {float(density[iy, ix]):.3f}")
        ok = False

    # couple_imaging_records: base weight * sampled irradiance, records with no object origin skipped.
    fake = _FakeEditor()
    records = [
        {"hits": [{"surface": "2", "x": 0.0, "y": 0.0}], "branch_power": 1.0},   # centre -> bright
        {"hits": [{"surface": "2", "x": 17.5, "y": 0.0}], "branch_power": 1.0},  # fold edge -> dark
        {"hits": [{"surface": "9", "x": 0.0, "y": 0.0}], "branch_power": 1.0},   # no object hit -> skip
    ]
    origin = imaging_ray_object_origin(fake, None, 2, records[0])
    if not (origin[2] and np.isclose(origin[0], 0.0) and np.isclose(origin[1], 0.0)):
        notes.append(f"imaging_ray_object_origin wrong for centre record: {origin!r}")
        ok = False
    if imaging_ray_object_origin(fake, None, 2, records[2])[2]:
        notes.append("imaging_ray_object_origin found an origin on a record with no object hit")
        ok = False
    coupled = couple_imaging_records(fake, None, 2, records, irr_map)
    if len(coupled) != 2:
        notes.append(f"couple_imaging_records kept {len(coupled)} entries, expected 2 (1 skipped)")
        ok = False
    else:
        c_centre = coupled[0]["irradiance"]
        c_edge = coupled[1]["irradiance"]
        if not (c_centre >= 0.99 and c_edge <= 0.5 and c_centre > c_edge):
            notes.append(f"couple_imaging_records irradiance not centre>edge: {c_centre:.3f} vs {c_edge:.3f}")
            ok = False
    return ok


# --------------------------------------------------------------------------------------------------
# 2. Real-trace check on the portable coaxial-scatter fixture
# --------------------------------------------------------------------------------------------------
def _build_coupling_fixture(ray_count: int):
    """Portable rayfile-free coupling scene: the coaxial area-LED layout with the FOV plane turned
    into a Diffuse Object (MIRROR base + built-in Lambertian scatter, guided at an appended detector)
    so the seeded source imprints its dark edges on the object AND ~950 scatter rays image on the
    detector.  Returns ``(editor, system, records, object_index=2, detector_index=3)``."""
    import KrakenOS as Kos
    from KrakenOS.common_optical_layouts import machine_vision_150mm_coaxial_led as cx
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
    from KrakenOS.UI.scene_builder import build_scene_bundle

    settings = copy.deepcopy(cx.SETTINGS)
    settings["scene_sources"][0]["ray_count"] = int(ray_count)
    s0, s1, s2 = copy.deepcopy(cx.SURFACES)
    s2_obj = copy.deepcopy(s2)
    s2_obj.update({"surface": "Diffuse Object", "name": "Diffuse object at FOV plane",
                   "glass": "MIRROR", "thickness": 40.0})
    s2_obj["advanced"] = dict(s2_obj.get("advanced", {}))
    s2_obj["advanced"]["DiffuseScatter"] = {
        "model": "Lambertian", "backend": "Built-in", "reflectance": 0.8,
        "sample_count": 7, "max_scatter_angle_deg": 75.0, "min_branch_power": 1e-6,
        "max_branch_depth": 1, "target_surface": 3, "target_radius_scale": 0.9,
        "polarization": "Preserve projected Jones",
    }
    s_det = {"surface": "Image", "name": "Camera detector", "rc": 0.0, "thickness": 0.0,
             "diameter": 2.0 * cx.FOV_MM, "glass": "AIR",
             "advanced": {"Detector": {"active_width_mm": cx.FOV_MM, "active_height_mm": cx.FOV_MM}}}
    surfaces = [s0, s1, s2_obj, s_det]

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
    records = editor._ray_analysis_records_for_trace(system=system, rays=rays)
    return editor, system, records, 2, 3


def _edge_over_centre(along, perp, weights, half=_FOV_HALF, strip=6.0, nb=13):
    """Weighted edge/centre ratio of the ``along``-axis profile within a central ``perp`` strip
    (isolates one axis from the orthogonal 2-D cone bowl -- the robust per-axis signal)."""
    edges = np.linspace(-half, half, nb + 1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    mask = np.abs(perp) <= strip
    prof, _ = np.histogram(along[mask], bins=edges, weights=weights[mask])
    centre = prof[np.abs(centres) <= 4.5].mean()
    edge = prof[np.abs(centres) >= 13.5].mean()
    return (edge / centre) if centre > 0 else 0.0


def _source_object_map_asymmetry(editor, system, object_index, records):
    """fold(X) and perp(Y) edge/centre of the binned source -> object density map."""
    from KrakenOS.UI.services.source_object_coupling import object_irradiance_map

    irr_map = object_irradiance_map(editor, system, object_index, ray_records=records)
    if not irr_map:
        return None
    density = np.asarray(irr_map["density"], dtype=float)
    x_edges = np.asarray(irr_map["x_edges"], dtype=float)
    y_edges = np.asarray(irr_map["y_edges"], dtype=float)
    x_centres = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_centres = 0.5 * (y_edges[:-1] + y_edges[1:])
    fold_prof = density[np.abs(y_centres) <= 5.0, :].sum(0)
    perp_prof = density[:, np.abs(x_centres) <= 5.0].sum(1)

    def ratio(prof, centres):
        cen = prof[np.abs(centres) <= 4.5].mean()
        edg = prof[np.abs(centres) >= 13.5].mean()
        return (edg / cen) if cen > 0 else 0.0

    return ratio(fold_prof, x_centres), ratio(perp_prof, y_centres)


def _check_real_trace(notes: list[str]) -> bool:
    try:
        editor, system, records, obj_idx, det_idx = _build_coupling_fixture(_TRACE_RAYS)
    except Exception as exc:  # pragma: no cover - trace/build failure
        notes.append(f"coupling fixture build raised: {exc!r}")
        return False

    ok = True
    detected = editor._source_object_coupling_object_index()
    notes.append(f"auto-detected object index={detected} (expected {obj_idx})")
    if detected != obj_idx:
        notes.append(f"object index auto-detect wrong: {detected} != {obj_idx}")
        ok = False

    # Source -> object map asymmetry (the dark edges before imaging).
    asym = _source_object_map_asymmetry(editor, system, obj_idx, records)
    if asym is None:
        notes.append("source -> object irradiance map is empty (object receives no source light)")
        return False
    map_fold, map_perp = asym
    notes.append(f"source->object map fold(X) edge/centre={map_fold:.3f} perp(Y)={map_perp:.3f}")
    if not (map_fold <= 0.75):
        notes.append(f"source->object map fold edge not dark: {map_fold:.3f} (>0.75)")
        ok = False
    if not (map_perp - map_fold >= 0.08):
        notes.append(f"source->object map not asymmetric fold<perp: {map_fold:.3f} vs {map_perp:.3f} (<0.08 gap)")
        ok = False

    res = editor._illumination_weighted_detector_spot_samples(system, "All paths", ray_records=records)
    if not res.get("coupling_applied"):
        notes.append(f"coupling did not apply: coupling_applied={res.get('coupling_applied')}")
        return False
    if res.get("object_surface_index") != obj_idx:
        notes.append(f"coupled object index {res.get('object_surface_index')} != {obj_idx}")
        ok = False
    coupled_rays = int(res.get("coupled_ray_count", 0))
    notes.append(
        f"coupling_applied on {coupled_rays} imaging rays "
        f"(irr hits {res.get('irradiance_hit_count')}, {_TRACE_RAYS} source rays)"
    )
    if coupled_rays < 200:
        notes.append(f"too few coupled imaging rays ({coupled_rays}) for a stable check")
        ok = False

    x = np.asarray(res["x"], dtype=float)
    y = np.asarray(res["y"], dtype=float)
    weights = np.asarray(res["weights"], dtype=float)
    base_weights = np.asarray(res["base_weights"], dtype=float)
    irradiance = np.asarray(res["irradiance"], dtype=float)

    # Multiply correctness: coupled weight == base weight * sampled irradiance, elementwise.
    if not np.allclose(weights, base_weights * irradiance, rtol=1e-6, atol=1e-9):
        notes.append("coupled weights != base_weights * irradiance (coupling math broken)")
        ok = False
    # Irradiance spans dark..bright in [0, 1].
    if irradiance.size and not (0.0 <= irradiance.min() and irradiance.max() <= 1.0 + 1e-9):
        notes.append(f"irradiance outside [0,1]: min={irradiance.min():.3f} max={irradiance.max():.3f}")
        ok = False
    if irradiance.size and not (irradiance.min() <= 0.5 and irradiance.max() >= 0.8):
        notes.append(f"irradiance lacks dark+bright span: min={irradiance.min():.3f} max={irradiance.max():.3f}")
        ok = False
    # Coupling is NOT a no-op.
    if not (float(np.sum(np.abs(weights - base_weights))) > 0.0):
        notes.append("coupling changed nothing (weights == base_weights): no-op")
        ok = False

    coupled_fold = _edge_over_centre(x, y, weights)
    coupled_perp = _edge_over_centre(y, x, weights)
    base_fold = _edge_over_centre(x, y, base_weights)
    base_perp = _edge_over_centre(y, x, base_weights)
    notes.append(
        f"COUPLED detector image fold(X) edge/centre={coupled_fold:.3f} perp(Y)={coupled_perp:.3f}; "
        f"BASE fold={base_fold:.3f} perp={base_perp:.3f}"
    )
    # The coupled detector image carries the fold-axis dark edges while the perp axis stays uniform.
    if not (coupled_fold <= 0.45):
        notes.append(f"coupled detector fold edge not dark: {coupled_fold:.3f} (>0.45)")
        ok = False
    if not (coupled_perp >= 0.80):
        notes.append(f"coupled detector perp edge not uniform: {coupled_perp:.3f} (<0.80)")
        ok = False
    # Coupling DEEPENS the fold dip versus the un-coupled base (transfers the source rolloff).
    if not (base_fold - coupled_fold >= 0.15):
        notes.append(
            f"coupling did not deepen the fold dip: base {base_fold:.3f} -> coupled {coupled_fold:.3f} (<0.15)"
        )
        ok = False

    # bugs/0266 guardrail: coupling reuses the exact base detector samples -- identical terminal
    # geometry and identical un-coupled control weights -- so it never redefines the image plane.
    base = editor._branch_detector_spot_samples(system, "All paths", ray_records=records)
    base_x = np.asarray(base["x"], dtype=float)
    base_y = np.asarray(base["y"], dtype=float)
    base_w = np.asarray(base["weights"], dtype=float)
    same_geometry = (
        base_x.shape == x.shape
        and np.allclose(base_x, x, rtol=1e-6, atol=1e-9)
        and np.allclose(base_y, y, rtol=1e-6, atol=1e-9)
    )
    if not same_geometry:
        notes.append("coupling changed the detector terminal geometry (image plane redefined -> 0266 violation)")
        ok = False
    if not (base_w.shape == base_weights.shape and np.allclose(base_w, base_weights, rtol=1e-6, atol=1e-9)):
        notes.append("coupled base_weights control diverged from the untouched base detector weights")
        ok = False
    if obj_idx == det_idx:
        notes.append(f"object index == detector index ({obj_idx}); object promoted to image plane -> 0266 violation")
        ok = False
    if not editor._surface_index_is_detector(det_idx):
        notes.append(f"detector index {det_idx} not recognised as a detector")
        ok = False
    return ok


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    passed = True
    try:
        passed &= _check_synthetic(notes)
    except Exception as exc:  # pragma: no cover - defensive
        notes.append(f"synthetic check raised: {exc!r}")
        passed = False
    try:
        passed &= _check_real_trace(notes)
    except Exception as exc:  # pragma: no cover - defensive
        notes.append(f"real-trace check raised: {exc!r}")
        passed = False
    return bool(passed), notes


def main() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(("OK   " if passed else "NOTE ") + note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
