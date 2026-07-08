"""Display-free guard: a face-bound illumination marker must NOT hijack the imaging trace (bugs/0266).

Feature B (bugs/0264) lets a user mark a CAD/STL face as an illumination source. That created a real
``SceneSource3D`` (physical, enabled, role="illumination"). But the live preview trace treats ANY
physical+enabled scene source as a launch that REPLACES the object-driven imaging trace: in
``TracePreviewService._trace_preview_rays`` the first non-empty ``_build_scene_source_bundles`` result is
traced and the method RETURNS EARLY, skipping every imaging launch path (per-branch, world-envelope,
full-pupil grid, finite-object). So marking a face silently swapped the imaging trace for a lone
illumination bundle, and the image plane / detector / optical axis / image circle -- all IMAGING
conjugates fixed by the object -- were then recomputed from that degenerate bundle and RELOCATED onto the
beam-splitter's illumination face (the flag: "after setting illumination surface, the image plane and
detector shifted to the illumination plane of the BS").

The fix keys on a resolved ``face_anchor_row`` >= 0 (``scene_source_spec_is_face_bound_marker``): a
face-bound marker is a DESIGNATION that tracks a face for display, never a trace driver. It is excluded
from the imaging trace at every source-driven launch path, so a marker-only scene falls through to the
imaging trace and the conjugates stay put. A DELIBERATE scene source (no face anchor) is untouched.

This guard has three display-free parts:

* PREDICATE -- pure unit cases on ``scene_source_spec_is_face_bound_marker`` for the dict-spec form AND
  the ``SceneSource3D`` dataclass form (positive rows, row 0, negatives/None/garbage -> not a marker).
* WIRING (source inspection) -- the three source-driven launch paths
  (``_build_scene_source_bundles``, ``_collect_scene_sources``, ``build_saved_layout_rays``) all consult
  the predicate to exclude markers, and ``_trace_preview_rays`` still early-returns on a non-empty bundle
  list (the structure that makes the exclusion load-bearing). ``scene_sources_from_settings`` is
  DELIBERATELY not filtered -- it must faithfully round-trip every source (bugs/0264 depends on the marker
  surviving), and its caller applies the exclusion.
* BEHAVIOUR (headless editor, STEP-free hand-built specs, always runs) -- a marker-only scene yields ZERO
  imaging-trace bundles (so the imaging trace runs) and ``_collect_scene_sources``[0] is the non-marker
  imaging reference (correct ray tagging) with the marker appended for display; a deliberate physical
  source still yields >= 1 bundle; a mixed scene launches ONLY the deliberate source.
"""

from __future__ import annotations

import inspect
import os

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")


def _deliberate_spec() -> dict:
    """A user-authored physical scene source (Collimated disk != the 'Pupil / field' default -> physical).
    No face anchor: this is a real launch that legitimately drives the trace."""
    return {
        "source_id": "source:deliberate",
        "name": "Deliberate emitter",
        "source_model": "Collimated disk source",
        "physical": True,
        "enabled": True,
        "source_x": 0.0,
        "source_y": 0.0,
        "source_z": -60.0,
        "source_l": 0.0,
        "source_m": 0.0,
        "source_n": 1.0,
        "radius": 6.0,
        "ray_count": 12,
    }


def _marker_spec(row_index: int = 1) -> dict:
    """A face-bound illumination marker (Feature B): physical+enabled like the deliberate source, but
    carrying a ``face_anchor_row`` so it designates + tracks a face rather than driving the trace."""
    spec = _deliberate_spec()
    spec.update(
        {
            "source_id": "source:marker",
            "name": "Face illumination marker",
            "role": "illumination",
            "face_anchor_row": int(row_index),
            "face_anchor_face_id": "S001/F002",
        }
    )
    return spec


def _check_predicate(failures: list[str]) -> None:
    from KrakenOS.UI.scene_geometry import SceneSource3D
    from KrakenOS.UI.scene_source_analysis import scene_source_spec_is_face_bound_marker as is_marker

    # Dict-spec form (as stored in layout_scene_source_specs / normalized specs).
    dict_cases = [
        ("row 1", {"face_anchor_row": 1}, True),
        ("row 0 (a real row)", {"face_anchor_row": 0}, True),
        ("coercible string row", {"face_anchor_row": "3"}, True),
        ("float row", {"face_anchor_row": 2.0}, True),
        ("negative row (unbound)", {"face_anchor_row": -1}, False),
        ("None row", {"face_anchor_row": None}, False),
        ("garbage row", {"face_anchor_row": "not-a-row"}, False),
        ("no anchor key (deliberate source)", {"physical": True, "enabled": True}, False),
        ("empty spec", {}, False),
    ]
    for label, spec, expected in dict_cases:
        got = bool(is_marker(spec))
        if got != expected:
            failures.append(f"PREDICATE dict[{label}]: expected {expected}, got {got}")

    # Dataclass form (face_anchor_row rides in SceneSource3D.settings after scene_source_from_spec).
    dataclass_cases = [
        ("settings row 5", SceneSource3D(settings={"face_anchor_row": 5}), True),
        ("settings row 0", SceneSource3D(settings={"face_anchor_row": 0}), True),
        ("settings negative", SceneSource3D(settings={"face_anchor_row": -2}), False),
        ("settings no key", SceneSource3D(settings={"radius": 4.0}), False),
        ("settings None dict", SceneSource3D(settings={}), False),
    ]
    for label, source, expected in dataclass_cases:
        got = bool(is_marker(source))
        if got != expected:
            failures.append(f"PREDICATE dataclass[{label}]: expected {expected}, got {got}")

    # The full spec builder must carry the anchor into the dataclass so the predicate fires end-to-end.
    from KrakenOS.UI.scene_source_analysis import scene_source_from_spec

    built = scene_source_from_spec(_marker_spec(row_index=2), 0, wavelength=0.55)
    if not is_marker(built):
        failures.append("PREDICATE: scene_source_from_spec dropped face_anchor_row -> marker not detected")
    built_deliberate = scene_source_from_spec(_deliberate_spec(), 0, wavelength=0.55)
    if is_marker(built_deliberate):
        failures.append("PREDICATE: a deliberate source was misclassified as a face-bound marker")


def _check_wiring(failures: list[str]) -> None:
    from KrakenOS.UI import source_trace_helpers as helpers
    from KrakenOS.UI.services.source_modeling import SourceModelingMixin
    from KrakenOS.UI.services.trace_preview import TracePreviewService

    def _src(obj, label: str) -> str:
        try:
            return inspect.getsource(obj)
        except Exception as exc:  # pragma: no cover - defensive
            failures.append(f"WIRING: could not read {label} source ({exc!r})")
            return ""

    marker = "scene_source_spec_is_face_bound_marker"

    bundles_src = _src(SourceModelingMixin._build_scene_source_bundles, "_build_scene_source_bundles")
    if marker not in bundles_src or "continue" not in bundles_src:
        failures.append(
            "WIRING: _build_scene_source_bundles must skip a face-bound marker (it feeds the live "
            "preview trace via _trace_preview_rays)"
        )

    collect_src = _src(SourceModelingMixin._collect_scene_sources, "_collect_scene_sources")
    if marker not in collect_src:
        failures.append(
            "WIRING: _collect_scene_sources must exclude markers from the physical-source short-circuit "
            "so a marker-only scene falls through to the imaging reference"
        )

    saved_src = _src(helpers.build_saved_layout_rays, "build_saved_layout_rays")
    if marker not in saved_src:
        failures.append("WIRING: build_saved_layout_rays must exclude markers from the saved-layout imaging trace")

    # The root-cause structure: a non-empty scene-source bundle list short-circuits the imaging launch
    # paths with an early return. This is WHY excluding markers from the bundles matters.
    preview_src = _src(TracePreviewService._trace_preview_rays, "_trace_preview_rays")
    if "_build_scene_source_bundles" not in preview_src or "if scene_source_bundles:" not in preview_src:
        failures.append(
            "WIRING: _trace_preview_rays no longer gates on _build_scene_source_bundles -- the marker "
            "exclusion guards this early-return path; re-verify the regression context"
        )

    # scene_sources_from_settings must NOT drop markers (bugs/0264 round-trip depends on it); the
    # exclusion lives at its caller. Guard against a future well-meaning edit filtering it there.
    settings_src = _src(helpers.scene_sources_from_settings, "scene_sources_from_settings")
    if marker in settings_src:
        failures.append(
            "WIRING: scene_sources_from_settings must NOT filter markers itself -- it has to round-trip "
            "every source for display (bugs/0264); apply the exclusion at the call site instead"
        )


def _check_behaviour(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.scene_source_analysis import scene_source_spec_is_face_bound_marker as is_marker

    app = KrakenLayoutEditor(headless=True)
    try:
        # (1) Marker-only scene: no imaging-trace bundle -> _trace_preview_rays falls through to the
        #     object-driven imaging launch, so the image plane / detector / optical axis stay put.
        app.layout_scene_source_specs = [_marker_spec(row_index=1)]
        bundles, records = app._build_scene_source_bundles(0.55)
        if len(bundles) != 0:
            failures.append(
                f"BEHAVIOUR: a marker-only scene produced {len(bundles)} imaging-trace bundle(s); it must "
                "produce 0 so the object-driven imaging trace runs (the flag: image plane shifted to the BS)"
            )
        if records:
            failures.append(f"BEHAVIOUR: a marker-only scene yielded {len(records)} bundle source records; expected 0")

        collected = app._collect_scene_sources(wavelength=0.55)
        if not collected:
            failures.append("BEHAVIOUR: _collect_scene_sources returned nothing for a marker-only scene")
        else:
            if is_marker(collected[0]):
                failures.append(
                    "BEHAVIOUR: _collect_scene_sources[0] is the marker -- imaging rays would be tagged with "
                    "the illumination marker; the imaging reference must be first"
                )
            if str(getattr(collected[0], "role", "")) != "pupil_field_reference":
                failures.append(
                    f"BEHAVIOUR: the imaging reference role is {getattr(collected[0], 'role', None)!r}, "
                    "not 'pupil_field_reference'"
                )
            if not any(is_marker(src) for src in collected):
                failures.append(
                    "BEHAVIOUR: the face-bound marker was dropped from _collect_scene_sources -- it must ride "
                    "along (appended) for the source table / overlays even though it does not drive the trace"
                )

        # (2) Deliberate physical source (no face anchor): still drives the trace, exactly as before.
        app.layout_scene_source_specs = [_deliberate_spec()]
        del_bundles, del_records = app._build_scene_source_bundles(0.55)
        if len(del_bundles) < 1:
            failures.append(
                "BEHAVIOUR: a deliberate physical scene source produced 0 bundles -- the fix must not disturb "
                "genuine source-driven tracing"
            )
        if len(del_records) != len(del_bundles):
            failures.append("BEHAVIOUR: deliberate-source bundle/record count mismatch")

        # (3) Mixed scene: only the deliberate source launches; the marker is excluded.
        app.layout_scene_source_specs = [_deliberate_spec(), _marker_spec(row_index=1)]
        mix_bundles, mix_records = app._build_scene_source_bundles(0.55)
        if len(mix_bundles) != 1:
            failures.append(
                f"BEHAVIOUR: a deliberate+marker scene produced {len(mix_bundles)} bundle(s); expected exactly 1 "
                "(the deliberate source only -- the marker must be excluded)"
            )
        if any(is_marker(src) for src in mix_records):
            failures.append("BEHAVIOUR: a marker leaked into the mixed-scene imaging-trace launch set")

        if not failures:
            notes.append(
                "behaviour OK: marker-only -> 0 imaging bundles (imaging trace runs) + imaging reference first; "
                "deliberate -> >=1 bundle; mixed -> deliberate only"
            )
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_predicate(failures)
    _check_wiring(failures)
    _check_behaviour(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] illumination-source imaging-trace hijack guard")
        return 1
    print("[PASS] a face-bound illumination marker does not hijack the imaging trace")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
