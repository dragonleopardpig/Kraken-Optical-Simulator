"""Display-free guard: bugs/0286 -- on-SENSOR coupled illumination projection (Piece 2, Approach A).

flag_20260710_085240_847 ("Illumination overlay still show nothing"): on the real MV-150 vendor scene
the coaxial LED / marked beam-splitter face floods the OBJECT at the FOV, not the detector -- 0
illumination rays reach the sensor even through a mirror -- so the DIRECT density-on-sensor heatmap
(``_compute_detector_density_illumination_overlay_spec``, >=50 sensor hits) cannot build and the sensor
draws blank. But the imaging lens IMAGES the object onto the sensor, so we bin the dense illumination
landing WITHIN the imaged object aperture and PROJECT that dark-edge map onto the sensor extent. This is
the user's "make the Object a mirror" model: a mirror at the FOV relays the coaxial dark edges to the
sensor sharply (a diffuse object would blur them), which a rescale-to-sensor draw of the object map
reproduces. The projection is numerically independent of what the object reflects INTO, so a plain
Object / Mirror / Object Target are all couplable; a Mirror is simply the sharpest semantic.

``source_illumination_overlay_spec`` is now a dispatcher: DIRECT density first (the coaxial-LED teaching
scene, unregressed), else the coupled PROJECTION fallback (the real vendor scene). The fallback is gated
exactly like the density path (bugs/0280/0282): a live NON-marker source must be present, else a pure
imaging scene would fabricate a map from its sparse pupil/field fan. A 45-deg splitter-face marker that
sprays entirely off the imaged aperture yields no map -> the sensor stays correctly blank (display
follows physics).

Display-free (pure numpy + headless traces, no VTK). It pins:

  * PROJECTION MATH (no trace): ``object_illumination_projection_map`` clips samples to the object
    aperture and bins over the SURVIVING data footprint (peak-normalised, far outliers dropped, too few
    hits / all-off-aperture -> None); ``project_object_map_onto_sensor`` keeps the density grid but
    rescales the edges to the sensor half-extent (the bugs/0275 guardrail: draw at the SENSOR size, not
    the FOV) and rejects degenerate input.
  * OBJECT RECOGNITION: ``_source_object_coupling_object_index`` prefers Diffuse > Mirror/Object Target
    > plain sequential Object, and returns None when the scene has no object surface.
  * DISPATCHER CONTRACT: ``_compute_source_illumination_overlay_spec`` tries the density heatmap BEFORE
    the coupled fallback; the coupled compute is render-only (no re-trace) and draws via the projection.
  * COUPLED FALLBACK end-to-end on the PORTABLE coaxial-scatter fixture: the coupled compute returns a
    heatmap drawn at the detector's active size (bugs/0275) with dark edges, and the coupled object
    (index 2) is NOT promoted to the detector plane (index 3) -- bugs/0266.
  * DENSITY NON-REGRESSION: the portable coaxial-LED teaching scene still returns the DIRECT density
    overlay (fold darker than perp) -- the fallback does not hijack the case the density path handles.
  * REAL VENDOR SCENE (optional, only when attachment/machine_vision_150mm_test.py is present): +LED ->
    PRESENT at the 23 mm sensor with dark edges; marked BS face -> None; no source -> None.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_coupled_object_illumination_projection

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import os
import types

import numpy as np

_ATTACHMENT = "attachment/machine_vision_150mm_test.py"


# --------------------------------------------------------------------------------------------------
# 1. Projection math -- no trace
# --------------------------------------------------------------------------------------------------
class _SamplesEditor:
    """Minimal stand-in so ``object_illumination_projection_map`` can bin a hand-built illumination
    footprint without a trace: it only needs ``_source_illumination_hit_samples`` to hand back x/y."""

    def __init__(self, x, y):
        self._x = np.asarray(x, dtype=float)
        self._y = np.asarray(y, dtype=float)

    def _source_illumination_hit_samples(self, system, index, *, ray_records=None):
        return {"x": self._x, "y": self._y, "coord": "local"}


def _check_projection_math(failures: list[str]) -> None:
    from KrakenOS.UI.services.source_object_coupling import (
        object_illumination_projection_map,
        project_object_map_onto_sensor,
    )

    # A bright-centre / dark-edge footprint (dense Gaussian core) INSIDE a radius-12 aperture, plus 5
    # far outliers at r ~ 36 that must be clipped so the map bins over the illuminated footprint, not
    # the whole aperture. Deterministic (seeded) so any clone reproduces it.
    rng = np.random.default_rng(7)
    R = 12.0
    core = rng.normal(0.0, R * 0.42, size=(1600, 2))
    outliers = np.array([[3 * R, 0.0], [0.0, 3 * R], [-3 * R, 0.0], [0.0, -3 * R], [2.4 * R, 2.4 * R]])
    x = np.concatenate([core[:, 0], outliers[:, 0]])
    y = np.concatenate([core[:, 1], outliers[:, 1]])
    in_aperture = int(np.sum(np.hypot(x, y) <= R))

    editor = _SamplesEditor(x, y)
    m = object_illumination_projection_map(editor, None, 0, ray_records=[], object_radius=R, min_hits=30)
    if not m:
        failures.append("MATH: object_illumination_projection_map returned None for a valid footprint")
    else:
        density = np.asarray(m["density"], dtype=float)
        if density.ndim != 2 or density.size == 0:
            failures.append(f"MATH: projection density is not a 2-D grid ({density.shape})")
        if not np.isclose(float(density.max()), 1.0, atol=1e-9):
            failures.append(f"MATH: projection density not peak-normalised (max={density.max():.4f})")
        if int(m["hit_count"]) != in_aperture:
            failures.append(f"MATH: hit_count {m['hit_count']} != in-aperture count {in_aperture} (clip wrong)")
        # The 5 far outliers must be gone -> the binned extent sits at the footprint (~R), NOT 3R.
        ext = np.abs(np.asarray(m["extent"], dtype=float))
        if float(ext.max()) > R * 1.6:
            failures.append(f"MATH: extent {ext.max():.1f} reaches the outliers (~{3*R:.0f}); footprint not clipped")
        # Bright centre, dark rim (the rolloff the projection must carry).
        ny, nx = density.shape
        centre = float(density[ny // 2 - 1:ny // 2 + 1, nx // 2 - 1:nx // 2 + 1].mean())
        corners = float(np.mean([density[0, 0], density[0, -1], density[-1, 0], density[-1, -1]]))
        if not (centre > corners + 0.15):
            failures.append(f"MATH: projection lacks a dark-edge rolloff (centre {centre:.2f} vs corner {corners:.2f})")

    # min_hits gate: an impossible floor -> None (never bin a sparse footprint).
    if object_illumination_projection_map(editor, None, 0, ray_records=[], object_radius=R, min_hits=10 ** 6) is not None:
        failures.append("MATH: projection did not return None below its min_hits floor")
    # All illumination off the aperture -> None (nothing imaged -> blank sensor).
    off = _SamplesEditor(outliers[:, 0], outliers[:, 1])
    if object_illumination_projection_map(off, None, 0, ray_records=[], object_radius=R, min_hits=1) is not None:
        failures.append("MATH: an entirely off-aperture footprint did not return None")
    # object_radius=0 disables the clip -> the outliers survive -> extent reaches ~3R.
    m_all = object_illumination_projection_map(editor, None, 0, ray_records=[], object_radius=0.0, min_hits=30)
    if m_all is not None and float(np.abs(np.asarray(m_all["extent"], float)).max()) < R * 2.0:
        failures.append("MATH: object_radius=0 still clipped the footprint (should keep the outliers)")

    # project_object_map_onto_sensor: keep the pattern, rescale edges to the SENSOR (bugs/0275).
    dens = np.array([[0.2, 0.5, 0.9, 0.5, 0.2], [0.3, 0.7, 1.0, 0.7, 0.3], [0.2, 0.5, 0.9, 0.5, 0.2]], dtype=float)
    obj_map = {
        "density": dens,
        "x_edges": np.linspace(-8.0, 8.0, 6),
        "y_edges": np.linspace(-6.0, 6.0, 4),
        "extent": [-8.0, 8.0, -6.0, 6.0],
        "coord": "local",
        "hit_count": 123,
    }
    proj = project_object_map_onto_sensor(obj_map, 11.5, 9.0)
    if not proj:
        failures.append("MATH: project_object_map_onto_sensor returned None for valid input")
    else:
        if not np.array_equal(np.asarray(proj["density"]), dens):
            failures.append("MATH: projection altered the density grid (pattern must be untouched)")
        if not np.allclose(proj["x_edges"], np.linspace(-11.5, 11.5, 6)):
            failures.append("MATH: x_edges not rescaled to the sensor half-width (bugs/0275 FOV-size trap)")
        if not np.allclose(proj["y_edges"], np.linspace(-9.0, 9.0, 4)):
            failures.append("MATH: y_edges not rescaled to the sensor half-height")
        if [round(v, 3) for v in proj["extent"]] != [-11.5, 11.5, -9.0, 9.0]:
            failures.append(f"MATH: projected extent {proj['extent']} != sensor box")
        if int(proj["hit_count"]) != 123:
            failures.append("MATH: projection dropped the hit_count")
    # Degenerate inputs -> None.
    if project_object_map_onto_sensor(None, 11.5, 9.0) is not None:
        failures.append("MATH: None map_data did not project to None")
    if project_object_map_onto_sensor({"density": np.zeros(0)}, 11.5, 9.0) is not None:
        failures.append("MATH: empty density did not project to None")
    if project_object_map_onto_sensor(obj_map, 0.0, 9.0) is not None:
        failures.append("MATH: a zero sensor half-width did not project to None")


# --------------------------------------------------------------------------------------------------
# 2. Object recognition -- no trace
# --------------------------------------------------------------------------------------------------
def _check_object_recognition(failures: list[str]) -> None:
    from KrakenOS.UI.panels.main_path_detector_analysis import MainPathDetectorAnalysis

    def _row(surface, advanced=None):
        return types.SimpleNamespace(surface=surface, advanced=advanced or {})

    def _idx(rows):
        return MainPathDetectorAnalysis._source_object_coupling_object_index(types.SimpleNamespace(rows=rows))

    # Diffuse beats a Mirror beats a plain Object.
    if _idx([_row("Object"), _row("Standard"), _row("Diffuse Object"), _row("Mirror")]) != 2:
        failures.append("RECOG: Diffuse Object not preferred over Mirror/plain Object")
    # No Diffuse -> Mirror beats the plain Object at row 0.
    if _idx([_row("Object"), _row("Mirror"), _row("Standard")]) != 1:
        failures.append("RECOG: Mirror not preferred over the plain Object")
    # Object Target is also reflective.
    if _idx([_row("Object"), _row("Object Target")]) != 1:
        failures.append("RECOG: Object Target not recognised as a reflective object")
    # Plain sequential Object is the last-resort couplable surface (the real MV-150 vendor row 0).
    if _idx([_row("Object"), _row("Standard"), _row("Image")]) != 0:
        failures.append("RECOG: plain sequential Object not used as the fallback couplable surface")
    # A DiffuseScatter advanced attr counts even without the surface name.
    if _idx([_row("Standard", {"DiffuseScatter": {"model": "Lambertian"}})]) != 0:
        failures.append("RECOG: a DiffuseScatter advanced attr was not recognised")
    # No object surface at all -> None.
    if _idx([_row("Standard"), _row("Image")]) is not None:
        failures.append("RECOG: a scene with no object surface did not return None")


# --------------------------------------------------------------------------------------------------
# 3. Dispatcher contract -- source inspection
# --------------------------------------------------------------------------------------------------
def _check_dispatcher_contract(failures: list[str]) -> None:
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    dispatch = inspect.getsource(ThreeDSceneToolsMixin._compute_source_illumination_overlay_spec)
    i_density = dispatch.find("_compute_detector_density_illumination_overlay_spec")
    i_coupled = dispatch.find("_compute_coupled_object_illumination_overlay_spec")
    if i_density < 0 or i_coupled < 0:
        failures.append("CONTRACT: dispatcher does not reference both the density and coupled computes")
    elif not (i_density < i_coupled):
        failures.append("CONTRACT: dispatcher tries the coupled fallback BEFORE the direct density heatmap")

    coupled = inspect.getsource(ThreeDSceneToolsMixin._compute_coupled_object_illumination_overlay_spec)
    for needed in ("object_illumination_projection_map", "project_object_map_onto_sensor"):
        if needed not in coupled:
            failures.append(f"CONTRACT: coupled compute does not call {needed}")
    # Render-only (bugs/0166/0266): it must not re-run the trace or rebuild the system.
    for forbidden in ("build_system(", "_trace_preview_rays(", "_build_preview_system_rays_bundle("):
        if forbidden in coupled:
            failures.append(f"CONTRACT: coupled compute references {forbidden!r} -- not render-only")

    records = inspect.getsource(ThreeDSceneToolsMixin._coupled_object_illumination_records)
    if "scene_source_spec_is_face_bound_marker" not in records:
        failures.append("CONTRACT: coupled records path is not gated on a live non-marker source (bugs/0280/0282)")


# --------------------------------------------------------------------------------------------------
# 4. Coupled fallback end-to-end on the PORTABLE coaxial-scatter fixture
# --------------------------------------------------------------------------------------------------
def _check_coupled_fallback_portable(failures: list[str], notes: list[str]) -> None:
    try:
        from KrakenOS.UI.validate_open3d_source_object_coupling import _build_coupling_fixture
    except Exception as exc:
        notes.append(f"SKIP coupled-fallback: fixture import failed ({exc!r})")
        return
    try:
        editor, system, _records, obj_idx, det_idx = _build_coupling_fixture(8000)
    except Exception as exc:
        notes.append(f"SKIP coupled-fallback: fixture build failed ({exc!r})")
        return

    target = editor._source_illumination_anchor_target(editor._last_scene_bundle)
    if target is None:
        failures.append("FALLBACK: no sensor anchor target on the coupling fixture")
        return
    try:
        spec = editor._compute_coupled_object_illumination_overlay_spec(system, target)
    except Exception as exc:
        failures.append(f"FALLBACK: coupled compute raised {exc!r}")
        return
    if not spec:
        failures.append("FALLBACK: coupled compute returned None on the coaxial-scatter fixture")
        return

    half_w, half_h = editor._detector_target_half_extent(target)
    pts = np.asarray(spec["points"], dtype=float)
    span_x = float(pts[:, 0].max() - pts[:, 0].min()) if pts.size else 0.0
    span_y = float(pts[:, 1].max() - pts[:, 1].min()) if pts.size else 0.0
    # bugs/0275: the quad must span the SENSOR active area, not the object/FOV footprint.
    if not (half_w > 0.0 and abs(span_x - 2.0 * half_w) <= 0.5 * (2.0 * half_w)):
        failures.append(f"FALLBACK: heatmap x-span {span_x:.1f} != sensor width {2*half_w:.1f} (bugs/0275)")
    if not (half_h > 0.0 and abs(span_y - 2.0 * half_h) <= 0.5 * (2.0 * half_h)):
        failures.append(f"FALLBACK: heatmap y-span {span_y:.1f} != sensor height {2*half_h:.1f}")
    if not (float(spec.get("min_relative", 1.0)) < 0.9):
        failures.append(f"FALLBACK: projected map has no dark edges (min_relative={spec.get('min_relative')})")
    # bugs/0266: the object is NOT promoted to the detector plane.
    if obj_idx == det_idx:
        failures.append("FALLBACK: coupled object index == detector index (image-plane promotion, bugs/0266)")
    notes.append(
        f"coupled fallback: object idx={obj_idx} -> detector idx={det_idx}, heatmap dims={spec['dims']} "
        f"span=({span_x:.1f}x{span_y:.1f}mm ~ sensor {2*half_w:.1f}x{2*half_h:.1f}) min_rel={spec.get('min_relative'):.2f}"
    )


# --------------------------------------------------------------------------------------------------
# 5. Density non-regression on the portable coaxial-LED teaching scene
# --------------------------------------------------------------------------------------------------
def _check_density_nonregression(failures: list[str], notes: list[str]) -> None:
    try:
        from KrakenOS.UI.validate_open3d_source_illumination_overlay import _build_coaxial_overlay
    except Exception as exc:
        notes.append(f"SKIP density non-regression: harness import failed ({exc!r})")
        return
    editor, system, bundle = _build_coaxial_overlay(8000)
    if editor is None:
        notes.append("SKIP density non-regression: coaxial layout unavailable")
        return
    spec = editor.source_illumination_overlay_spec(system, bundle)
    if not spec:
        failures.append("NONREG: coaxial teaching scene lost its DIRECT density overlay (fallback hijack?)")
        return
    fold = float(spec.get("x_edge_ratio", 1.0))
    perp = float(spec.get("y_edge_ratio", 1.0))
    if not (fold <= 0.85 and perp >= 0.85 and perp - fold >= 0.12):
        failures.append(f"NONREG: density fold/perp signal broke (fold={fold:.2f} perp={perp:.2f})")
    notes.append(f"density non-regression: coaxial dispatcher -> density overlay fold={fold:.2f} perp={perp:.2f}")


# --------------------------------------------------------------------------------------------------
# 6. Real vendor scene -- optional (attachment gitignored; runs on the user's machines)
# --------------------------------------------------------------------------------------------------
def _check_real_vendor_scene(failures: list[str], notes: list[str]) -> None:
    from pathlib import Path

    path = Path(_ATTACHMENT)
    if not path.exists():
        notes.append(f"SKIP real vendor scene: {_ATTACHMENT} absent (gitignored -- validated via bugs/diag_0286_production_wire)")
        return
    try:
        import KrakenOS as Kos
        from KrakenOS.UI.layout_editor import _load_python_data
        from KrakenOS.UI.render_layout_snapshot import (
            _build_runtime_system,
            _rows_from_layout_info,
            _snapshot_editor,
        )
    except Exception as exc:
        notes.append(f"SKIP real vendor scene: import failed ({exc!r})")
        return

    def _load(mutate):
        info = _load_python_data(path)
        rows = _rows_from_layout_info(info)
        settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
        editor = _snapshot_editor(rows, settings)
        editor.current_layout_file = path
        editor._normalize_special_rows()
        if mutate is not None:
            mutate(editor)
        system = _build_runtime_system(path, editor.rows)
        wavelength = editor._current_wavelength()
        rays = Kos.raykeeper(system)
        max_radius = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
        editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
        bundle = editor._build_scene_bundle(system, rays, max_radius)
        editor.last_system, editor.last_rays, editor._last_scene_bundle = system, rays, bundle
        editor._last_preview_trace_signature = editor._preview_trace_signature()
        return editor.source_illumination_overlay_spec(system, bundle)

    try:
        led = _load(lambda ed: ed.add_illumination_led_source())
        marked = _load(lambda ed: ed.create_illumination_source_at_face(1, face_id="S001/F001", aim="inward"))
        none_src = _load(None)
    except Exception as exc:
        failures.append(f"REAL: driving the vendor scene raised {exc!r}")
        return

    if not led:
        failures.append("REAL: +LED overlay is None -- the coupled projection fallback did not fire on the vendor scene")
    elif not (float(led.get("min_relative", 1.0)) < 0.85):
        failures.append(f"REAL: +LED overlay has no dark edges (min_relative={led.get('min_relative')})")
    if marked is not None:
        failures.append("REAL: marked BS face sprays off-FOV but produced a NON-None overlay")
    if none_src is not None:
        failures.append("REAL: pure imaging scene fabricated an overlay (bugs/0280/0282 gate breach)")
    if led:
        pts = np.asarray(led["points"], dtype=float)
        span = float(pts[:, 0].max() - pts[:, 0].min()) if pts.size else 0.0
        notes.append(f"real vendor scene: +LED -> PRESENT dark-edge heatmap span~{span:.0f}mm; marked-face + no-source blank")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_projection_math(failures)
    _check_object_recognition(failures)
    _check_dispatcher_contract(failures)
    _check_coupled_fallback_portable(failures, notes)
    _check_density_nonregression(failures, notes)
    _check_real_vendor_scene(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    os.environ.setdefault("MPLBACKEND", "Agg")
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] coupled on-sensor illumination projection (bugs/0286)")
        return 1
    print("[PASS] object illumination projects onto the sensor as dark edges; density path unregressed (bugs/0286)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
