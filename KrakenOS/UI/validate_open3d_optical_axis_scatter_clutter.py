"""Display-free guard: a diffuse double-pass scene must NOT spawn stray optical axes.

Regression guard for bugs/0181. The folded MV-150 coaxial area-LED scene
(LED -> beam-splitter reflect -> diffuse object -> scatter back -> BS transmit ->
imaging lens) was promoting its diffusely-scattered return rays -- and the
extended LED cone's down arm -- into up to six scene-spanning "Optical Axis"
guide lines reaching +/-900 mm. Those poisoned the camera-fit bounds and turned
both the 3D and 2D (YZ) views into an unreadable mess of crisscrossing lines.

A diffuse double-pass has NO single chief-ray optical axis: the object scatters
every ray off in its own random direction, so neither the return spray nor the
diverging area-source down arm defines one axis. The fix is two layered guards,
both asserted here:

  1. PER-SEGMENT -- ``_dotted_axis_records_from_ray_path`` drops every segment at
     or after a diffuse-scatter event (a post-scatter ray is random), while a
     genuine fold with NO upstream scatter still earns its axis.
  2. SCENE-LEVEL -- ``_optical_axis_records_for_3d`` suppresses ALL traced axes
     for a scene that contains any diffuse-scatter path; only the global dotted
     guide remains. A clean (scatter-free) fold scene is untouched.

Plus an end-to-end check on the REAL folded layout: it yields the global guide
ONLY (zero traced segments), the exact symptom the user flagged.
"""
from __future__ import annotations

import os

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.scene_geometry import RayEvent3D, RayPath3D, SceneBundle
from KrakenOS.UI.services.ray_display_geometry import _dotted_axis_records_from_ray_path

_REAL_RAYS = int(os.environ.get("AXIS_CLUTTER_REAL_RAYS", "16"))
_BOUNDS = np.asarray([-50.0, 50.0, -50.0, 50.0, -90.0, 90.0], dtype=float)


def _surface_event(event_type: str, surface_id: int, point) -> RayEvent3D:
    return RayEvent3D(
        event_id=f"surface:{surface_id}",
        event_kind="surface",
        event_type=event_type,
        surface_id=surface_id,
        mesh_face_id=f"F{surface_id:03d}",
        point_world=np.asarray(point, dtype=float),
    )


class _FakeRenderer:
    def ComputeVisiblePropBounds(self):
        return tuple(float(v) for v in _BOUNDS)


class _FakeBoolVar:
    def __init__(self, value: bool) -> None:
        self._value = bool(value)

    def get(self) -> bool:
        return self._value


def _records_for(bundle: SceneBundle) -> list[dict[str, object]]:
    inspector = object.__new__(Kraken3DInspector)
    inspector._renderer = _FakeRenderer()
    inspector.show_rays_var = _FakeBoolVar(True)
    inspector._cached_traced_axis_signature = None
    inspector._cached_traced_axis_records = []
    return Kraken3DInspector._optical_axis_records_for_3d(inspector, bundle)


def _traced(records) -> list[dict[str, object]]:
    return [r for r in records if str(r.get("axis_kind", "")) == "traced_chief_ray_segment"]


# --- Part 1: per-segment exclusion --------------------------------------------

def _scatter_then_fold_path() -> RayPath3D:
    """launch +Z -> refract -> SCATTER -> reflect off-axis -> escape.

    The reflect tail is a genuine direction change, so WITHOUT the fix it would
    be promoted to a fold axis. It sits downstream of the scatter, so it must be
    dropped."""
    return RayPath3D(
        ray_index=11,
        points_world=np.asarray(
            [
                [0.0, 0.0, -40.0],
                [0.0, 0.0, -10.0],   # S1 refract
                [0.0, 0.0, 10.0],    # S2 scatter
                [0.0, 0.0, 30.0],    # S3 reflect (turns the ray)
                [40.0, 0.0, 30.0],   # escape (+X tail = would-be fold)
            ],
            dtype=float,
        ),
        events=[
            _surface_event("refraction", 1, [0.0, 0.0, -10.0]),
            _surface_event("scatter", 2, [0.0, 0.0, 10.0]),
            _surface_event("reflect", 3, [0.0, 0.0, 30.0]),
        ],
    )


def _clean_fold_path() -> RayPath3D:
    """launch +Z -> reflect off-axis -> escape (+X). No scatter: keeps its axis."""
    return RayPath3D(
        ray_index=12,
        points_world=np.asarray(
            [
                [0.0, 0.0, -40.0],
                [0.0, 0.0, 0.0],    # S1 reflect
                [40.0, 0.0, 0.0],   # escape (+X fold tail)
            ],
            dtype=float,
        ),
        events=[_surface_event("reflect", 1, [0.0, 0.0, 0.0])],
    )


def _check_segment_level(notes: list[str]) -> bool:
    ok = True
    scatter_recs = _dotted_axis_records_from_ray_path(_scatter_then_fold_path(), _BOUNDS)
    if scatter_recs:
        dirs = [tuple(round(float(v), 2) for v in r.get("segment_direction", ())) for r in scatter_recs]
        notes.append(f"post-scatter fold tail was promoted ({len(scatter_recs)} segs, dirs={dirs})")
        ok = False
    else:
        notes.append("post-scatter fold tail correctly dropped (0 segments)")
    clean_recs = _dotted_axis_records_from_ray_path(_clean_fold_path(), _BOUNDS)
    if not clean_recs:
        notes.append("a clean (scatter-free) fold lost its axis -> exclusion too aggressive")
        ok = False
    else:
        notes.append(f"clean fold keeps its axis ({len(clean_recs)} segment)")
    return ok


# --- Part 2: scene-level gate -------------------------------------------------

def _scatter_bundle() -> SceneBundle:
    return SceneBundle(ray_paths=[_scatter_then_fold_path()], has_off_axis=True)


def _clean_fold_bundle() -> SceneBundle:
    return SceneBundle(ray_paths=[_clean_fold_path()], has_off_axis=True)


def _check_scene_gate(notes: list[str]) -> bool:
    ok = True
    scatter_traced = _traced(_records_for(_scatter_bundle()))
    if scatter_traced:
        notes.append(f"diffuse-scatter scene still drew {len(scatter_traced)} traced axes")
        ok = False
    else:
        notes.append("diffuse-scatter scene shows the global guide only (0 traced)")
    clean_traced = _traced(_records_for(_clean_fold_bundle()))
    if not clean_traced:
        notes.append("scatter-free fold scene lost its traced axis -> gate too broad")
        ok = False
    else:
        notes.append(f"scatter-free fold scene keeps {len(clean_traced)} traced axis (gate precise)")
    return ok


# --- Part 3: the real flagged scene -------------------------------------------

def _build_folded_bundle(ray_count: int):
    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
    from KrakenOS.UI.scene_builder import build_scene_bundle
    from KrakenOS.common_optical_layouts import machine_vision_150mm_coaxial_led_folded as layout

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
    return build_scene_bundle(
        rows=rows, system=system, rays=rays, sources=sources,
        field_count=len(sources),
        ray_count_per_field=max((getattr(s, "ray_count", 1) for s in sources), default=1),
    )


def _check_real_scene(notes: list[str]) -> bool:
    try:
        bundle = _build_folded_bundle(_REAL_RAYS)
    except Exception as exc:  # pragma: no cover - build failure
        notes.append(f"real folded-scene build raised: {exc!r}")
        return False
    records = _records_for(bundle)
    traced = _traced(records)
    notes.append(
        f"real folded coaxial-LED scene: {len(records)} axis records, {len(traced)} traced"
    )
    if traced:
        spans = []
        for r in traced:
            pts = np.asarray(r.get("points"), dtype=float)
            spans.append((float(pts.min()), float(pts.max())))
        notes.append(f"traced axes remain (spans={spans}) -> clutter not suppressed")
        return False
    if not records:
        notes.append("no axis records at all -> lost even the global guide")
        return False
    return True


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    ok &= _check_segment_level(notes)
    ok &= _check_scene_gate(notes)
    ok &= _check_real_scene(notes)
    return bool(ok), notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(("PASS " if ok else "") + note)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
