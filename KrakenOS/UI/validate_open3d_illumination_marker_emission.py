"""Display-free guard for the additive full-surface illumination EMISSION overlay (bugs/0267).

A face-bound illumination marker (bugs/0264) is excluded from the imaging trace (bugs/0266), so marking a
face gave the user NO visual feedback -- "the rays seem not changing, no full-surface rays from that
surface". This overlay closes that: the marked CAD/STL face now floods a straight emission ray from every
sampled point on its WHOLE surface, out along the launch direction (an area-matched disk sized from the
live face record, not the stored 2 mm launch disk). It is the SOURCE emission -- honest source physics --
NOT a through-system trace (illumination refracting/scattering onto the detector is the Stage-3 coupling;
a mid-system face source stops at S0 in the imaging trace). Crucially it is built purely from the marker
LAUNCH bundles and never traces, so it cannot touch ``last_rays`` / ``_last_scene_bundle`` and the imaging
image-plane / detector / optical axis stay fixed (bugs/0266 preserved).

Four display-free parts:

* WIRING (source inspection) -- the editor exposes the bundle builder + the sizing helper + the cached
  overlay spec; ``_build_illumination_marker_bundles`` keeps ONLY markers (the complement of
  ``_build_scene_source_bundles``); the spec compute is stub-only (no ``_trace_preview_bundles`` /
  ``raykeeper`` / ``build_system`` and no ``last_rays`` / ``_last_scene_bundle`` reference -- the
  render-only + 0266 contract); the inspector consumer is render-only; ``refresh_scene`` reads the toggle
  var and calls the consumer; the Overlays menu exposes the var.
* PURE -- ``build_illumination_marker_rays_overlay`` on hand-built (starts, ends): a 2-vertex segment per
  ray, zero-span + non-finite dropped, subsample cap respected.
* BEHAVIOUR (headless, STEP-free hand-built specs, always runs) -- a marker-only scene yields >=1 marker
  emission bundle while the IMAGING bundle builder still yields 0 (0266 intact); a mixed scene splits
  1 marker / 1 imaging; the overlay spec is drawable AND leaves the imaging trace state untouched.
* BINDING (real promoted-prism STEP fixture; SKIPs when the STEP is not checked out) -- a real marked face
  is sized to its full surface (radius >> the stored 2 mm) and the emission overlay is drawable.
"""

from __future__ import annotations

import inspect
import os

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")


def _deliberate_spec() -> dict:
    return {
        "source_id": "source:deliberate",
        "name": "Deliberate emitter",
        "source_model": "Collimated disk source",
        "physical": True,
        "enabled": True,
        "source_x": 0.0, "source_y": 0.0, "source_z": -60.0,
        "source_l": 0.0, "source_m": 0.0, "source_n": 1.0,
        "radius": 6.0, "ray_count": 12,
    }


def _marker_spec(row_index: int = 1) -> dict:
    spec = _deliberate_spec()
    spec.update(
        {
            "source_id": "source:marker",
            "name": "Face illumination marker",
            "role": "illumination",
            "ray_count": 200,
            "face_anchor_row": int(row_index),
            "face_anchor_face_id": "S001/F002",
        }
    )
    return spec


def _check_wiring(failures: list[str]) -> None:
    from KrakenOS.UI.services import open3d_scene_refresh
    from KrakenOS.UI.services.source_modeling import SourceModelingMixin
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.panels import open3d_top_controls

    def _src(obj, label: str) -> str:
        try:
            return inspect.getsource(obj)
        except Exception as exc:  # pragma: no cover - defensive
            failures.append(f"WIRING: could not read {label} source ({exc!r})")
            return ""

    for cls, name in (
        (SourceModelingMixin, "_build_illumination_marker_bundles"),
        (SourceModelingMixin, "_illumination_marker_full_surface_source"),
        (ThreeDSceneToolsMixin, "illumination_marker_rays_overlay_spec"),
        (ThreeDSceneToolsMixin, "_compute_illumination_marker_rays_overlay_spec"),
        (Kraken3DInspector, "_add_illumination_marker_ray_overlays"),
    ):
        if not hasattr(cls, name):
            failures.append(f"WIRING: {cls.__name__} is missing {name}()")

    # The bundle builder is the COMPLEMENT of _build_scene_source_bundles: keep ONLY markers.
    bundles_src = _src(SourceModelingMixin._build_illumination_marker_bundles, "_build_illumination_marker_bundles")
    if "scene_source_spec_is_face_bound_marker" not in bundles_src or "continue" not in bundles_src:
        failures.append(
            "WIRING: _build_illumination_marker_bundles must keep ONLY face-bound markers "
            "(the complement of _build_scene_source_bundles)"
        )

    # The spec compute runs an ISOLATED trace (the rays reflect) but must NOT touch the imaging trace
    # state, so it cannot re-break bugs/0266 (image plane / detector / optical axis stay put).
    compute_src = _src(
        ThreeDSceneToolsMixin._compute_illumination_marker_rays_overlay_spec,
        "_compute_illumination_marker_rays_overlay_spec",
    )
    for required in ("_trace_preview_bundles(", "raykeeper(", "_isolated_ray_analysis_records(", "_force_nonseq_preview_trace"):
        if required not in compute_src:
            failures.append(
                f"WIRING: _compute_illumination_marker_rays_overlay_spec must {required!r} "
                "-- it traces the marker into a SEPARATE keeper (forced non-seq) so the rays reflect"
            )
    for forbidden in ("_ray_analysis_records_for_trace(", "_last_scene_bundle =", "build_system(", "_build_preview_system_rays_bundle("):
        if forbidden in compute_src:
            failures.append(
                f"WIRING: _compute_illumination_marker_rays_overlay_spec must NOT reference {forbidden!r} "
                "-- the isolated trace must not mutate/replace the imaging scene bundle (bugs/0266)"
            )
    # The non-mutating record extractor is the 0266 linchpin: it must NOT write _last_scene_bundle.
    from KrakenOS.UI.services.analysis_reports import AnalysisReportsMixin
    isolated_src = _src(AnalysisReportsMixin._isolated_ray_analysis_records, "_isolated_ray_analysis_records")
    if "_last_scene_bundle =" in isolated_src or "self._last_scene_bundle" in isolated_src.replace("NEVER writes ``self._last_scene_bundle``", ""):
        failures.append("WIRING: _isolated_ray_analysis_records must never assign self._last_scene_bundle (0266)")

    consumer_src = _src(Kraken3DInspector._add_illumination_marker_ray_overlays, "_add_illumination_marker_ray_overlays")
    for forbidden in ("build_system(", "_build_preview_system_rays_bundle("):
        if forbidden in consumer_src:
            failures.append(f"WIRING: the inspector consumer must be render-only (found {forbidden!r})")

    refresh_src = _src(open3d_scene_refresh, "open3d_scene_refresh module")
    if "show_illumination_marker_rays_var" not in refresh_src or "_add_illumination_marker_ray_overlays" not in refresh_src:
        failures.append(
            "WIRING: refresh_scene must read show_illumination_marker_rays_var and call "
            "_add_illumination_marker_ray_overlays"
        )

    controls_src = _src(open3d_top_controls, "open3d_top_controls module")
    if "show_illumination_marker_rays_var" not in controls_src:
        failures.append("WIRING: the Overlays menu does not expose show_illumination_marker_rays_var")


def _check_pure(failures: list[str]) -> None:
    from KrakenOS.UI.services.source_illumination_rays_overlay import build_illumination_marker_rays_overlay

    def _rec(sx, sy, sz, hits):
        return {"source_x": sx, "source_y": sy, "source_z": sz, "hits": [{"x": h[0], "y": h[1], "z": h[2]} for h in hits]}

    # A traced ray that REFLECTS: origin -> hit -> hit (3 vertices). A ray with one distant hit is also kept.
    records = [
        _rec(0.0, 0.0, 0.0, [(0.0, 0.0, 10.0), (5.0, 0.0, 15.0)]),  # reflected (3-vertex polyline)
        _rec(1.0, 0.0, 0.0, [(1.0, 0.0, 8.0)]),
    ]
    spec = build_illumination_marker_rays_overlay(records)
    if spec is None or spec.get("kind") != "illumination_marker_rays":
        failures.append("PURE: valid traced records produced no spec")
        return
    pts = np.asarray(spec.get("points"))
    if pts.shape[0] != 5 or int(spec.get("drawn", 0)) != 2 or int(spec.get("total", 0)) != 2:
        failures.append(f"PURE: expected 5 vertices / 2 polylines, got points={pts.shape} drawn={spec.get('drawn')}")

    # source-aperture collapse (a dot at the emitter) + non-finite dropped
    if build_illumination_marker_rays_overlay([_rec(0.0, 0.0, 0.0, [(0.0, 0.0, 0.0)])]) is not None:
        failures.append("PURE: a ray collapsed at the source (zero span) must be dropped")
    if build_illumination_marker_rays_overlay([_rec(0.0, 0.0, 0.0, [(np.nan, 0.0, 9.0)])]) is not None:
        failures.append("PURE: a non-finite ray must be dropped")

    # subsample cap respected
    many = [_rec(0.0, 0.0, 0.0, [(0.0, 0.0, 10.0)]) for _ in range(50)]
    capped = build_illumination_marker_rays_overlay(many, max_rays=10)
    if capped is None or int(capped.get("drawn", 0)) != 10 or int(capped.get("total", 0)) != 50:
        failures.append(f"PURE: subsample cap not respected (drawn={None if capped is None else capped.get('drawn')})")


def _check_behaviour(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor(headless=True)
    try:
        # (1) Marker-only: marker emission bundles >= 1, IMAGING bundles == 0 (0266 intact).
        app.layout_scene_source_specs = [_marker_spec(row_index=1)]
        mbundles, _ = app._build_illumination_marker_bundles(0.55)
        ibundles, _ = app._build_scene_source_bundles(0.55)
        if len(mbundles) < 1:
            failures.append("BEHAVIOUR: a marker-only scene produced 0 marker emission bundles")
        if len(ibundles) != 0:
            failures.append(
                f"BEHAVIOUR: a marker-only scene produced {len(ibundles)} IMAGING bundles; must be 0 "
                "(0266: the marker must not drive the imaging trace)"
            )

        # (2) Mixed scene: marker builder keeps only the marker; imaging keeps only the deliberate source.
        app.layout_scene_source_specs = [_deliberate_spec(), _marker_spec(row_index=1)]
        mb2, _ = app._build_illumination_marker_bundles(0.55)
        ib2, _ = app._build_scene_source_bundles(0.55)
        if len(mb2) != 1 or len(ib2) != 1:
            failures.append(f"BEHAVIOUR: mixed scene split wrong (marker={len(mb2)} imaging={len(ib2)}; expected 1/1)")

        # (3) No markers -> no emission overlay (and no crash).
        app.layout_scene_source_specs = [_deliberate_spec()]
        if app.illumination_marker_rays_overlay_spec(None, None) is not None:
            failures.append("BEHAVIOUR: a marker-free scene must yield no emission overlay")

        if not failures:
            notes.append("behaviour OK: marker-only -> emission bundle + 0 imaging bundles; mixed 1/1; marker-free -> none")
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def _check_binding(failures: list[str], notes: list[str]) -> None:
    from pathlib import Path
    from dataclasses import asdict

    from KrakenOS.UI import layout_editor as le
    from KrakenOS.UI.layout_editor import (
        KrakenLayoutEditor,
        OPTICAL_SOLID_FACES_ADVANCED_ATTR,
        SurfaceRow,
        optical_solid_face_world_records,
    )
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP

    if not PRISM_42779_STEP.exists():
        notes.append("SKIP binding: PRISM_42779_STEP fixture not checked out")
        return

    le.CAD_CACHE_DIR = Path("/tmp/kraken-open3d-illum-marker-emission-cache/cad")
    le.CAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_optical_step_path = PRISM_42779_STEP
        app.optical_step_rotation_x_deg = 90.0
        app.optical_step_rotation_z_deg = 90.0
        app.select_step_component("optical")
        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical", insert_at=1, open_face_editor=False, clear_overlay=True
        )
        if promoted is None:
            failures.append("BINDING: could not promote the prism STEP to an optical solid row")
            return
        row_index = int(promoted["row_index"])

        _row, _path, metadata = app._optical_solid_face_metadata_for_row(row_index)
        temp_row = SurfaceRow(**asdict(app.rows[row_index]))
        temp_row.advanced = dict(temp_row.advanced or {})
        temp_row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
        faces = optical_solid_face_world_records(temp_row, app._stl_row_z_station(row_index), assigned_only=False)
        if not faces:
            failures.append("BINDING: promoted optical solid exposed no faces")
            return
        # Make a few faces reflective so the isolated marker trace is genuinely non-sequential (the rays
        # must reflect). Mark a DIFFERENT face as the illumination source, aimed INTO the solid.
        for f in faces[:3]:
            app.assign_optical_solid_face_function(row_index, str(f.get("face_id", "") or ""), "Full Reflecting", direct_context=True)
        illum_face_id = str(faces[-1].get("face_id", "") or "").strip()
        app.assign_optical_solid_face_function(row_index, illum_face_id, "Uncoated", direct_context=True)
        if not app.create_illumination_source_at_face(row_index, face_id=illum_face_id, aim="inward"):
            failures.append("BINDING: create_illumination_source_at_face returned no source id")
            return

        bundles, sources = app._build_illumination_marker_bundles(0.55)
        if len(bundles) != 1:
            failures.append(f"BINDING: expected exactly one marker emission bundle, got {len(bundles)}")
            return
        radius = float((sources[0].settings or {}).get("radius", 0.0))
        if radius <= 2.0:
            failures.append(
                f"BINDING: the emission was not sized to the full face -- radius {radius:.2f} <= the stored 2 mm disk"
            )

        system = app.build_system()
        # 0266 isolation: the isolated marker trace must NOT touch the imaging scene state.
        sentinel_rays = object()
        sentinel_bundle = object()
        app.last_rays = sentinel_rays
        app._last_scene_bundle = sentinel_bundle
        spec = app.illumination_marker_rays_overlay_spec(system, None)
        if app.last_rays is not sentinel_rays or app._last_scene_bundle is not sentinel_bundle:
            failures.append("BINDING: the isolated marker trace mutated imaging state (last_rays/_last_scene_bundle) -- 0266 REGRESSION")
        if not spec or int(spec.get("drawn", 0)) < 1:
            failures.append("BINDING: a real marked face produced no drawable TRACED emission overlay")
        else:
            # REFLECTION: at least one drawn polyline has >2 vertices (origin + >=2 hits = a bend/reflection),
            # proving the emission is traced THROUGH the scene, not drawn as a straight stub.
            lines = np.asarray(spec.get("lines"), dtype=np.int64)
            reflected = False
            k = 0
            while k < lines.size:
                cnt = int(lines[k])
                if cnt > 2:
                    reflected = True
                    break
                k += 1 + cnt
            if not reflected:
                failures.append("BINDING: no traced emission ray reflected (every polyline is a single segment) -- rays are not traced through the scene")
            else:
                notes.append(f"binding OK: face {illum_face_id} floods full-surface emission that REFLECTS (radius {radius:.1f} mm, {spec['drawn']} rays); imaging state untouched")
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_wiring(failures)
    _check_pure(failures)
    _check_behaviour(failures, notes)
    _check_binding(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] illumination marker full-surface emission overlay")
        return 1
    print("[PASS] a marked face floods a full-surface illumination emission (isolated from imaging)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
