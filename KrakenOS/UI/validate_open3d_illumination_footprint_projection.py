"""bugs/0288 -- the illumination FOOTPRINT is projected onto the sensor at its TRUE imaged size.

Closes flag_20260710_170554_093 ("still a small patch launching from object plane") and
flag_20260710_170627_720 ("heat map"): on the real MV-150 vendor scene an added LED drew a full-sensor
radial bowl.  Two defects, both fixed here:

  1. WHAT COUNTS AS OBJECT ILLUMINATION.  KrakenOS records a scene source's LAUNCH as an
     object-surface (index 0) event *wherever the emitter sits*, so the old coupled map binned a
     coaxial LED parked at the beam splitter (z ~ 230 mm, x ~ 90 mm) as "illumination on the object".
     ``object_plane_illumination_samples`` accepts a direct object-surface event only when its WORLD
     position really lies on the object plane, and otherwise GEOMETRICALLY RELAYS the ray's terminal
     traced segment onto that plane -- the bugs/0287 trace-order-wall bypass (KrakenOS traces in
     surface-index order, so a flood reflecting off a beam splitter back toward surface 0 is never
     re-tested against it).  Absorbed rays illuminate nothing; backward segments are skipped;
     near-parallel blow-ups fall out at the aperture clip.

  2. HOW IT IS DRAWN.  ``project_object_map_onto_sensor`` (bugs/0286) rescales the footprint's own
     edges to the sensor half-extent, so the footprint ALWAYS fills the sensor and any under-fill is
     invisible -- a 10 mm LED patch on a 32.6 mm object became a full-sensor bowl.
     ``project_footprint_onto_sensor`` instead samples the object footprint at ``o = s/|m|`` for each
     sensor cell, using the scene's OWN paraxial magnification, so the lit region lands at its real
     size with a DARK surround.  Under-fill => dark edges; over-fill => uniform.  The geometry decides;
     nothing is tuned to a layout (proved here by scale-covariance in |m|).

All checks are display-free (no VTK, no pyvista window).  The real-vendor-scene check SKIPs when the
gitignored attachment is absent.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_illumination_footprint_projection

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import os

import numpy as np

_ATTACHMENT = "attachment/machine_vision_150mm_test.py"


class _PlanarEditor:
    """The object surface is an untilted plane, so surface-local (x, y) == world (x, y)."""

    def _hit_local_xy(self, system, index, hit):
        return float(hit["x"]), float(hit["y"]), "local"


def _record(**kw):
    base = {
        "hits": [],
        "termination": "no_next_intersection",
        "source_id": "source:led-1",
        "source_name": "LED",
        "source_weight": 1.0,
    }
    base.update(kw)
    return base


def _polyline(origin, direction, length=10.0):
    origin = np.asarray(origin, dtype=float)
    direction = np.asarray(direction, dtype=float)
    return [list(origin), list(origin + length * direction)]


def _grid_map(half, bright_half, bins):
    """A square top-hat footprint of half-width ``bright_half`` inside an extent of ``half``."""
    edges = np.linspace(-half, half, bins + 1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    gx, gy = np.meshgrid(centres, centres)
    density = ((np.abs(gx) <= bright_half) & (np.abs(gy) <= bright_half)).astype(float)
    return {
        "density": density,
        "x_edges": edges,
        "y_edges": edges,
        "extent": [-half, half, -half, half],
        "coord": "local",
        "hit_count": int(density.sum()),
    }


def _bright_half(map_data):
    """Half-width (mm) of the >=0.5 region along the centre row."""
    density = np.asarray(map_data["density"], dtype=float)
    x_edges = np.asarray(map_data["x_edges"], dtype=float)
    centres = 0.5 * (x_edges[:-1] + x_edges[1:])
    row = density[density.shape[0] // 2, :]
    lit = centres[row >= 0.5]
    return float(np.max(np.abs(lit))) if lit.size else 0.0


def _lit_fraction(map_data):
    density = np.asarray(map_data["density"], dtype=float)
    return float(np.count_nonzero(density >= 0.5)) / float(density.size)


# --------------------------------------------------------------------------------------------------
# 1. _terminal_ray -- the three tiers
# --------------------------------------------------------------------------------------------------
def _check_terminal_ray(failures: list[str]) -> None:
    from KrakenOS.UI.services.source_object_coupling import _terminal_ray

    poly = _record(traced_polyline_world=[[0.0, 0.0, 10.0], [0.0, 0.0, 4.0]])
    got = _terminal_ray(poly)
    if got is None or not np.allclose(got[0], [0, 0, 10]) or not np.allclose(got[1], [0, 0, -1]):
        failures.append("TERMINAL: traced_polyline_world tier did not yield (last interaction, unit dir)")

    hits = _record(hits=[{"x": 0.0, "y": 0.0, "z": 0.0}, {"x": 3.0, "y": 0.0, "z": 4.0}])
    got = _terminal_ray(hits)
    if got is None or not np.allclose(got[0], [0, 0, 0]) or not np.allclose(got[1], [0.6, 0.0, 0.8]):
        failures.append("TERMINAL: two-hit fallback did not yield the last segment")

    launch = _record(source_x=1.0, source_y=2.0, source_z=3.0, source_l=0.0, source_m=0.0, source_n=-2.0)
    got = _terminal_ray(launch)
    if got is None or not np.allclose(got[0], [1, 2, 3]) or not np.allclose(got[1], [0, 0, -1]):
        failures.append("TERMINAL: launch fallback did not normalise the launch direction")

    if _terminal_ray(_record()) is not None:
        failures.append("TERMINAL: a record with no path and no launch should yield None")


# --------------------------------------------------------------------------------------------------
# 2. object_plane_illumination_samples -- on-plane DIRECT vs geometric RELAY
# --------------------------------------------------------------------------------------------------
def _check_object_plane_samples(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.services.source_object_coupling import object_plane_illumination_samples

    editor = _PlanarEditor()

    def sample(records, radius=16.0, plane_z=0.0):
        return object_plane_illumination_samples(
            editor, None, 0, ray_records=records, object_plane_z=plane_z, object_radius=radius
        )

    # DIRECT: an emitter sitting ON the object plane lights it where it launches.
    direct = sample([_record(hits=[{"surface": 0, "x": 1.0, "y": 2.0, "z": 0.0}])])
    if not (direct["direct_count"] == 1 and direct["relayed_count"] == 0 and direct["x"].size == 1):
        failures.append("SAMPLES: an on-plane object-surface event was not counted as DIRECT illumination")
    elif not (np.isclose(direct["x"][0], 1.0) and np.isclose(direct["y"][0], 2.0)):
        failures.append("SAMPLES: DIRECT sample landed at the wrong object-local (x, y)")

    # OFF-PLANE LAUNCH (the flag's root cause): a coaxial LED at the beam splitter records a
    # surface-0 launch event at z ~ 230 mm.  It must NOT be binned as object illumination, and its
    # launch runs parallel to the plane so nothing is relayed either.
    off_plane = sample([
        _record(
            hits=[{"surface": 0, "x": 90.0, "y": 0.0, "z": 260.9}],
            traced_polyline_world=[[90.0, 0.0, 260.9], [27.5, 0.0, 260.9]],
        )
    ])
    if off_plane["x"].size != 0:
        failures.append(
            "SAMPLES: an OFF-PLANE launch event was binned as object illumination "
            f"(direct={off_plane['direct_count']} relayed={off_plane['relayed_count']}) -- flag 170554_093"
        )

    # RELAY: a flood heading toward the object plane is geometrically completed (trace-order wall).
    relayed = sample([_record(traced_polyline_world=_polyline((0.0, 0.0, 100.0), (0.0, 0.0, -1.0)))])
    if not (relayed["relayed_count"] == 1 and relayed["direct_count"] == 0 and relayed["x"].size == 1):
        failures.append("SAMPLES: a terminal segment crossing the object plane was not RELAYED")
    elif not (np.isclose(relayed["x"][0], 0.0) and np.isclose(relayed["y"][0], 0.0)):
        failures.append("SAMPLES: RELAY landed at the wrong object-plane point")

    tilt = np.asarray([0.1, 0.0, -1.0])
    tilt = tilt / np.linalg.norm(tilt)
    off_axis = sample([_record(traced_polyline_world=_polyline((0.0, 0.0, 100.0), tilt))])
    if off_axis["x"].size != 1 or not np.isclose(off_axis["x"][0], 10.0, atol=1e-6):
        failures.append("SAMPLES: RELAY of a tilted terminal segment did not land at x = 10 mm")

    # Only FREE-FLIGHT terminations may relay (bugs/0289): a ray that ended ON something -- absorbed at
    # a mechanical face, vignetted at a UDA aperture stop (bugs/0179), stopped at a hard-stop target --
    # deposited its light there; extending it would shine through the blocker.
    for blocked in ("absorb", "termination", "target_termination", "detector"):
        ended_on = sample([
            _record(termination=blocked, traced_polyline_world=_polyline((0.0, 0.0, 100.0), (0.0, 0.0, -1.0)))
        ])
        if ended_on["x"].size != 0:
            failures.append(f"SAMPLES: a ray that ended ON a surface ({blocked!r}) was relayed through it")

    # A segment travelling AWAY from the plane never reaches it.
    backward = sample([_record(traced_polyline_world=_polyline((0.0, 0.0, 100.0), (0.0, 0.0, 1.0)))])
    if backward["x"].size != 0:
        failures.append("SAMPLES: a terminal segment heading AWAY from the object plane was relayed")

    # Near-parallel blow-up: |d_z| -> 0 throws the intersection to ~1e11 mm.  The aperture clip is what
    # discards it -- no magic distance cut.  (This is why the naive 0287 relay read "+-1000 mm".)
    grazing = np.asarray([1.0, 0.0, -1e-9])
    grazing = grazing / np.linalg.norm(grazing)
    blowup = sample([_record(traced_polyline_world=_polyline((0.0, 0.0, 100.0), grazing))])
    if blowup["x"].size != 0:
        failures.append("SAMPLES: a near-parallel blow-up survived the object-aperture clip")

    # Off-aperture light is not relayed to the sensor by the imaging lens (bugs/0286).
    outside = sample([_record(hits=[{"surface": 0, "x": 30.0, "y": 0.0, "z": 0.0}])], radius=16.0)
    if outside["x"].size != 0:
        failures.append("SAMPLES: illumination outside the imaged object aperture was kept")

    # bugs/0289: the caller's IMAGED-FOV clip overrides the object row radius. On the vendor MV-150 the
    # row's 16.3 mm disc is SMALLER than the 19.5 mm half-square the lens actually images, so clipping
    # at the row erased real in-FOV illumination and carved a fabricated radial rim onto any large
    # footprint. A sample at x=18 (inside the imaged FOV, outside the row disc) must survive.
    in_fov = object_plane_illumination_samples(
        editor, None, 0,
        ray_records=[_record(hits=[{"surface": 0, "x": 18.0, "y": 0.0, "z": 0.0}])],
        object_plane_z=0.0, object_radius=16.0, clip_radius=27.6,
    )
    if in_fov["x"].size != 1:
        failures.append("SAMPLES: clip_radius did not widen the bound -- in-FOV light outside the row disc was dropped")
    beyond = object_plane_illumination_samples(
        editor, None, 0,
        ray_records=[_record(hits=[{"surface": 0, "x": 30.0, "y": 0.0, "z": 0.0}])],
        object_plane_z=0.0, object_radius=16.0, clip_radius=27.6,
    )
    if beyond["x"].size != 0:
        failures.append("SAMPLES: clip_radius failed to bound the samples (blow-up guard lost)")

    notes.append(
        "samples: on-plane DIRECT kept, off-plane launch rejected, relay lands geometrically, "
        "absorb/backward/blow-up/off-aperture dropped, imaged-FOV clip overrides the row disc"
    )


# --------------------------------------------------------------------------------------------------
# 3. _bilinear_zero_outside -- the soft penumbra sampler
# --------------------------------------------------------------------------------------------------
def _check_bilinear(failures: list[str]) -> None:
    from KrakenOS.UI.services.source_object_coupling import _bilinear_zero_outside

    density = np.array([[0.0, 1.0], [0.5, 0.25]], dtype=float)
    edges = np.array([0.0, 1.0, 2.0], dtype=float)  # bin centres 0.5, 1.5

    at_centres = _bilinear_zero_outside(
        density, edges, edges, np.array([[0.5, 1.5], [0.5, 1.5]]), np.array([[0.5, 0.5], [1.5, 1.5]])
    )
    if not np.allclose(at_centres, density):
        failures.append("BILINEAR: sampling at bin centres did not reproduce the density exactly")

    far = _bilinear_zero_outside(density, edges, edges, np.array([[-9.0, 9.0]]), np.array([[0.5, 0.5]]))
    if not np.allclose(far, 0.0):
        failures.append("BILINEAR: queries outside the padded extent must read 0 (unlit)")

    # One bin beyond the outer centre sits in the zero pad -> a ramp, not a cliff.
    ramp = _bilinear_zero_outside(
        density, edges, edges, np.array([[1.5, 2.0, 2.5]]), np.array([[0.5, 0.5, 0.5]])
    )
    if not (ramp[0, 0] > ramp[0, 1] > ramp[0, 2] and np.isclose(ramp[0, 2], 0.0)):
        failures.append("BILINEAR: the edge of the footprint is not a monotone ramp down to 0")


# --------------------------------------------------------------------------------------------------
# 4. project_footprint_onto_sensor -- true scale, under-fill vs over-fill, scale covariance
# --------------------------------------------------------------------------------------------------
def _check_true_scale_projection(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.services.source_object_coupling import (
        project_footprint_onto_sensor,
        project_object_map_onto_sensor,
    )

    half_sensor = 11.52
    m = 0.6
    under = _grid_map(half=7.0, bright_half=5.0, bins=14)  # a 10 mm LED patch, 20% zero border

    true_scale = project_footprint_onto_sensor(under, m, half_sensor, half_sensor)
    if true_scale is None:
        failures.append("PROJECT: an under-filling footprint produced no map")
        return
    bright = _bright_half(true_scale)
    expected = 5.0 * m
    if not (abs(bright - expected) <= 1.2):
        failures.append(f"PROJECT: imaged patch half-width {bright:.2f} mm != footprint*|m| {expected:.2f} mm")

    density = np.asarray(true_scale["density"], dtype=float)
    if not np.allclose(density[0, :], 0.0) or not np.allclose(density[:, 0], 0.0):
        failures.append("PROJECT: the sensor rim is not DARK for an under-filling footprint")

    # The bugs/0286 rescale hides exactly this: it always fills the sensor.
    stretched = project_object_map_onto_sensor(under, half_sensor, half_sensor)
    lit_true = _lit_fraction(true_scale)
    lit_stretch = _lit_fraction(stretched)
    if not (lit_true < 0.20):
        failures.append(f"PROJECT: true-scale lit fraction {lit_true:.2f} is too large for a 10 mm patch")
    if not (lit_stretch > 0.40):
        failures.append(f"PROJECT: the 0286 rescale should fill the sensor (lit {lit_stretch:.2f})")
    if not (lit_stretch > 2.0 * lit_true):
        failures.append("PROJECT: true-scale draw is not materially smaller than the 0286 rescale")

    # Soft roll-off, not a hard mask: the footprint boundary must be a ring of PARTIAL values.  (A hard
    # mask would hold exactly {0, 1}.  Count over the whole map, not one row -- with |m| < 1 the penumbra
    # is physically narrow, so whether any single row lands inside it is a bin-alignment accident.)
    graded = int(np.count_nonzero((density > 0.02) & (density < 0.98)))
    if graded < 4:
        failures.append(f"PROJECT: footprint edge is a hard mask, not a soft penumbra ({graded} graded cells)")

    # OVER-FILL -> uniform: no fabricated dark edges when the illumination covers the imaged FOV.
    over = _grid_map(half=56.0, bright_half=40.0, bins=14)
    over_map = project_footprint_onto_sensor(over, m, half_sensor, half_sensor)
    if over_map is None:
        failures.append("PROJECT: an over-filling footprint produced no map")
    elif float(np.min(over_map["density"])) < 0.9:
        failures.append(
            f"PROJECT: an over-filling footprint fabricated dark edges (min {float(np.min(over_map['density'])):.2f})"
        )

    # SCALE COVARIANCE == "no hardcoded value": the imaged patch is footprint*|m|, so halving |m| halves
    # it.  Nothing here may depend on a layout constant.
    half_m = project_footprint_onto_sensor(under, m / 2.0, half_sensor, half_sensor)
    ratio = _bright_half(half_m) / max(bright, 1e-9)
    if not (0.35 <= ratio <= 0.65):
        failures.append(f"PROJECT: imaged size is not driven by |m| (halving m scaled the patch by {ratio:.2f})")

    # Degenerate inputs stay None rather than fabricating a map.
    if project_footprint_onto_sensor(under, None, half_sensor, half_sensor) is not None:
        failures.append("PROJECT: a missing magnification must yield None")
    if project_footprint_onto_sensor(under, 0.0, half_sensor, half_sensor) is not None:
        failures.append("PROJECT: a zero magnification must yield None")
    if project_footprint_onto_sensor(under, m, 0.0, half_sensor) is not None:
        failures.append("PROJECT: a zero sensor half-extent must yield None")

    # A footprint that images entirely off the sensor draws nothing (annulus + strong magnification).
    annulus = _grid_map(half=56.0, bright_half=40.0, bins=14)
    ax = np.asarray(annulus["density"])
    centres = 0.5 * (annulus["x_edges"][:-1] + annulus["x_edges"][1:])
    gx, gy = np.meshgrid(centres, centres)
    ax[np.hypot(gx, gy) < 30.0] = 0.0
    if project_footprint_onto_sensor(annulus, 50.0, half_sensor, half_sensor) is not None:
        failures.append("PROJECT: a footprint imaged entirely off the sensor must yield None")

    notes.append(
        f"projection: patch half {bright:.2f} mm (= {5.0}x|m|={expected:.2f}), rim dark, "
        f"lit {lit_true*100:.0f}% vs 0286 rescale {lit_stretch*100:.0f}%; over-fill uniform; |m|-covariant"
    )


# --------------------------------------------------------------------------------------------------
# 5. footprint map + dispatcher wiring
# --------------------------------------------------------------------------------------------------
def _check_footprint_map(failures: list[str]) -> None:
    from KrakenOS.UI.services.source_object_coupling import object_footprint_irradiance_map

    rng = np.random.default_rng(7)
    xs, ys = rng.uniform(-5, 5, 400), rng.uniform(-5, 5, 400)
    samples = {"x": xs, "y": ys, "weights": np.ones(400), "source_ids": ["s"] * 400,
               "source_names": ["S"] * 400, "coord": "local", "direct_count": 400, "relayed_count": 0}
    got = object_footprint_irradiance_map(samples, 0)
    if got is None:
        failures.append("MAP: a well-populated footprint produced no map")
    else:
        if float(np.max(got["density"])) != 1.0:
            failures.append("MAP: footprint density is not peak-normalised")
        if got["direct_count"] != 400 or got["relayed_count"] != 0:
            failures.append("MAP: direct/relayed diagnostics were not carried through")
        if not (got["x_edges"][0] < -5.0 and got["x_edges"][-1] > 5.0):
            failures.append("MAP: the footprint extent does not enclose the data (no zero border to ramp into)")
    if object_footprint_irradiance_map(samples, 0, min_hits=10 ** 6) is not None:
        failures.append("MAP: min_hits gate did not suppress a sparse footprint")
    if object_footprint_irradiance_map(None, 0) is not None:
        failures.append("MAP: a None samples dict must yield None")


def _check_dispatcher_contract(failures: list[str]) -> None:
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    coupled = inspect.getsource(ThreeDSceneToolsMixin._compute_coupled_object_illumination_overlay_spec)
    for needed in (
        "object_plane_illumination_samples",
        "object_footprint_irradiance_map",
        "project_footprint_onto_sensor",
        "_object_surface_plane_z",
        "_current_finite_paraxial_magnification",
        "clip_radius",  # bugs/0289: samples clipped to the imaged FOV, not the object row disc
    ):
        if needed not in coupled:
            failures.append(f"WIRING: coupled compute does not use {needed}")
    if "project_object_map_onto_sensor" not in coupled:
        failures.append("WIRING: the no-conjugate fallback (bugs/0286 rescale) was dropped")
    for forbidden in ("build_system(", "_trace_preview_rays(", "_build_preview_system_rays_bundle("):
        if forbidden in coupled:
            failures.append(f"WIRING: coupled compute references {forbidden!r} -- it must stay render-only")

    if not hasattr(ThreeDSceneToolsMixin, "_object_surface_plane_z"):
        failures.append("WIRING: _object_surface_plane_z is missing")

    # bugs/0289: launched sources are traced ISOLATED so their records carry traced_polyline_world --
    # the relay needs the true post-exit direction (the hits-only last segment of a flood refracting out
    # of a solid is the IN-GLASS leg, which under-spreads the exit cone by ~n).
    records_src = inspect.getsource(ThreeDSceneToolsMixin._coupled_object_illumination_records)
    if "_isolated_scene_source_records" not in records_src:
        failures.append("WIRING: coupled records no longer isolated-trace launched sources (bugs/0289)")
    if not hasattr(ThreeDSceneToolsMixin, "_isolated_scene_source_records"):
        failures.append("WIRING: _isolated_scene_source_records is missing")
    else:
        iso_src = inspect.getsource(ThreeDSceneToolsMixin._isolated_scene_source_records)
        for needed in ("_build_scene_source_bundles", "_isolated_ray_analysis_records", "_force_nonseq_preview_trace"):
            if needed not in iso_src:
                failures.append(f"WIRING: _isolated_scene_source_records must use {needed}")
        if "_last_scene_bundle =" in iso_src:
            failures.append("WIRING: _isolated_scene_source_records must not replace the imaging scene bundle (bugs/0266)")

    # bugs/0289: the sensor anchor ranks detectors by RESOLVED dims (own or vendor override) so a flood
    # that never reaches the image still anchors the heatmap at the real sensor, and the density map's
    # enough-hits gate counts hits WITHIN the drawn window (stray leaks must not bin a garbage map).
    anchor_src = inspect.getsource(ThreeDSceneToolsMixin._source_illumination_anchor_target)
    if "_detector_target_half_extent" not in anchor_src:
        failures.append("WIRING: anchor target no longer ranks by resolved sensor dims (bugs/0289)")
    density_src = inspect.getsource(ThreeDSceneToolsMixin._compute_detector_density_illumination_overlay_spec)
    if "in_extent < 50" not in density_src:
        failures.append("WIRING: density gate no longer counts in-window hits (bugs/0289)")


# --------------------------------------------------------------------------------------------------
# 6. Real vendor scene -- optional (attachment gitignored; runs on the user's machines)
# --------------------------------------------------------------------------------------------------
def _check_real_vendor_scene(failures: list[str], notes: list[str]) -> None:
    from pathlib import Path

    path = Path(_ATTACHMENT)
    if not path.exists():
        notes.append(f"SKIP real vendor scene: {_ATTACHMENT} absent (gitignored -- see bugs/diag_0288_relay_probe)")
        return
    try:
        import KrakenOS as Kos
        from KrakenOS.UI.layout_editor import _load_python_data
        from KrakenOS.UI.render_layout_snapshot import (
            _build_runtime_system,
            _rows_from_layout_info,
            _snapshot_editor,
        )
        from KrakenOS.UI.services.source_object_coupling import (
            object_footprint_irradiance_map,
            object_plane_illumination_samples,
            project_object_map_onto_sensor,
        )
    except Exception as exc:
        notes.append(f"SKIP real vendor scene: import failed ({exc!r})")
        return

    try:
        info = _load_python_data(path)
        rows = _rows_from_layout_info(info)
        settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
        editor = _snapshot_editor(rows, settings)
        editor.current_layout_file = path
        editor._normalize_special_rows()
        editor.add_illumination_led_source(record_history=False)
        system = _build_runtime_system(path, editor.rows)
        wavelength = editor._current_wavelength()
        rays = Kos.raykeeper(system)
        max_radius = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
        editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
        bundle = editor._build_scene_bundle(system, rays, max_radius)
        editor.last_system, editor.last_rays, editor._last_scene_bundle = system, rays, bundle
        editor._last_preview_trace_signature = editor._preview_trace_signature()
        spec = editor.source_illumination_overlay_spec(system, bundle)
    except Exception as exc:
        failures.append(f"REAL: driving the vendor scene raised {exc!r}")
        return

    if not spec:
        failures.append("REAL: +LED overlay is None -- the footprint projection did not fire")
        return

    # The added LED seats ON the object plane, so every sample is DIRECT (nothing to relay).
    object_index = int(editor._source_object_coupling_object_index())
    radius = float(editor.rows[object_index].diameter) / 2.0
    records = editor._coupled_object_illumination_records(system, float(wavelength))
    samples = object_plane_illumination_samples(
        editor, system, object_index, ray_records=records,
        object_plane_z=editor._object_surface_plane_z(object_index), object_radius=radius,
    )
    if samples["relayed_count"] != 0 or samples["direct_count"] < 100:
        failures.append(
            f"REAL: expected DIRECT-only samples for an object-plane LED "
            f"(direct={samples['direct_count']} relayed={samples['relayed_count']})"
        )
    footprint_half = float(np.max(np.abs(samples["x"]))) if samples["x"].size else 0.0
    if not (3.0 <= footprint_half <= 8.0):
        failures.append(f"REAL: the 10 mm LED footprint measured half={footprint_half:.2f} mm on the object")

    magnification = editor._current_finite_paraxial_magnification()
    if magnification is None or not (0.1 < abs(float(magnification)) < 3.0):
        failures.append(f"REAL: no usable paraxial conjugate for the projection (m={magnification})")

    # The heatmap quad still spans the SENSOR (bugs/0275/0276/0277), and its rim is dark.
    points = np.asarray(spec["points"], dtype=float)
    span = float(points[:, 0].max() - points[:, 0].min()) if points.size else 0.0
    if not (20.0 <= span <= 26.0):
        failures.append(f"REAL: heatmap quad spans {span:.1f} mm, not the 23 mm sensor")
    for key in ("x_edge_ratio", "y_edge_ratio", "min_relative"):
        if float(spec.get(key, 1.0)) > 0.2:
            failures.append(f"REAL: sensor rim is not dark ({key}={spec.get(key)}) -- the stretch is back")

    # And the lit region is SMALL: the old rescale lit roughly half the sensor (the "heat map" flag).
    target = editor._source_illumination_anchor_target(bundle)
    half_w, half_h = editor._detector_target_half_extent(target)
    footprint = object_footprint_irradiance_map(samples, object_index)
    stretched = project_object_map_onto_sensor(footprint, half_w, half_h)
    lit_now = float(np.count_nonzero(np.asarray(spec["relative"], dtype=float) >= 0.5)) / float(
        np.asarray(spec["relative"]).size
    )
    lit_old = _lit_fraction(stretched)
    if not (lit_now < 0.25):
        failures.append(f"REAL: the imaged LED patch lights {lit_now*100:.0f}% of the sensor -- expected a small patch")
    if not (lit_old > lit_now):
        failures.append("REAL: the 0286 rescale did not light more of the sensor than the true-scale draw")

    relative = np.asarray(spec["relative"], dtype=float)
    graded = int(np.count_nonzero((relative > 0.02) & (relative < 0.98)))
    if graded < 4:
        failures.append(f"REAL: the patch edge is a hard mask, not a soft penumbra ({graded} graded cells)")

    notes.append(
        f"real vendor scene: LED footprint half {footprint_half:.2f} mm, |m|={abs(float(magnification)):.3f} -> "
        f"patch lights {lit_now*100:.0f}% of the {span:.0f} mm sensor (0286 rescale lit {lit_old*100:.0f}%), rim dark"
    )


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_terminal_ray(failures)
    _check_object_plane_samples(failures, notes)
    _check_bilinear(failures)
    _check_true_scale_projection(failures, notes)
    _check_footprint_map(failures)
    _check_dispatcher_contract(failures)
    _check_real_vendor_scene(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    os.environ.setdefault("MPLBACKEND", "Agg")
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    print(f"\n=== validate_open3d_illumination_footprint_projection: {'PASS' if passed else 'FAIL'} ===")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
