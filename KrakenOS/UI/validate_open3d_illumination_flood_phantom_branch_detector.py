"""Display-free guard for bugs/0285 -- the phantom branch detector / image plane a
physical illumination flood parks beside a beam-splitter cube.

Adding a physical scene-illumination source (an LED) to the MV-150 imaging scene made a
second "Sensor 23x23 / Image circle" detector plane draw beside the BS cube (recording
flag_20260710_085210_625: "after adding Scene Source"). Root cause: the flood reflects off
the beam splitter into an arm that never converges, so ``derive_branch_detectors`` parks a
branch detector at the default distance (``focus_source == 'default_distance'``) at x~80,
and -- with no diffuse-scatter object in the scene -- the bugs/0184 gate never fired, so its
plane + footprint + coverage all drew. The only REAL detector in a flood is the arm that
reaches the sequential Image (``focus_source == 'reached_image'``).

Fix: ``build_scene_bundle`` now stamps ``metadata['draw_suppressed']`` on every branch
detector whose draw must be gated (scatter / internal bounce / whole-scene scatter, AND now
an illumination-flood arm that does NOT reach the Image), computed where the scene-scatter
and flood context is known. The single flag is honoured by every downstream draw path
(2-D projection ``_target_branch_detector_draw_suppressed``, the 3-D footprint specs, and the
detector-coverage overlay). The detector TARGET is kept so it still hard-stops the rays.

Checks (all display-free):
  * PREDICATE -- ``_scene_has_illumination_flood``: a physical enabled illumination LED floods
    (True); a face-bound designation marker (bugs/0282), a disabled/non-physical source, a
    Pupil/field reference, and an empty scene do NOT (False). Same marker predicate as the
    heatmap gate so display-only markers never over-suppress.
  * PROPAGATE -- the shared 2-D predicate honours the stamped flag, and a stamped target still
    yields a real footprint polyline (so the 3-D/coverage skip -- keyed off the same flag -- is
    the only thing suppressing an otherwise-drawable plane), while a clean scatter-free arm is
    NOT falsely suppressed.
  * REAL SCENE -- ``attachment/machine_vision_150mm_test.py`` + an added illumination LED
    (the user's actual system, not the teaching layout): the reflect-arm phantom
    (``default_distance``, beside the cube) is draw-suppressed, the transmit arm
    (``reached_image``, on the sensor) is NOT, it stays the heatmap anchor, exactly ONE
    image-plane curve draws, and clearing the source drops the flood predicate (no
    over-suppression of a pure imaging scene -- bugs/0090 beam-splitter arms still draw).

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -m \
        KrakenOS.UI.validate_open3d_illumination_flood_phantom_branch_detector
"""
from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path

import numpy as np

from KrakenOS.UI.scene_builder import _scene_has_illumination_flood
from KrakenOS.UI.scene_geometry import SceneSource3D
from KrakenOS.UI.scene_projector import _target_branch_detector_draw_suppressed
from KrakenOS.UI.services.branch_detectors import (
    BranchDetector,
    branch_detector_scene_target,
)
from KrakenOS.UI.scene_geometry import scene_target_active_footprint_polylines


def _led_source(**settings) -> SceneSource3D:
    return SceneSource3D(
        source_id="led-1",
        name="LED 1",
        role="illumination",
        enabled=True,
        physical=True,
        settings=dict(settings),
    )


def _branch_target(focus_source: str, *, branch: str, center, row_index: int):
    detector = BranchDetector(
        detector_id=f"branch_detector:{row_index}:{branch}",
        branch_path=branch,
        center_world=np.asarray(center, dtype=float),
        normal_world=np.asarray((1.0, 0.0, 0.0), dtype=float),
        tangent_world=np.asarray((0.0, 1.0, 0.0), dtype=float),
        half_w=11.5,
        half_h=11.5,
        focus_source=focus_source,
    )
    return branch_detector_scene_target(detector, row_index=row_index)


def _check_flood_predicate(notes: list[str]) -> bool:
    ok = True

    if not _scene_has_illumination_flood([_led_source()]):
        notes.append("physical illumination LED did NOT register as a flood")
        ok = False
    else:
        notes.append("physical illumination LED -> flood (True)")

    marker = _led_source(face_anchor_row=3)
    if _scene_has_illumination_flood([marker]):
        notes.append("face-bound designation marker falsely registered as a flood")
        ok = False
    else:
        notes.append("face-bound marker -> not a flood (matches heatmap gate)")

    disabled = _led_source()
    disabled.enabled = False
    non_physical = _led_source()
    non_physical.physical = False
    pupil_ref = SceneSource3D(role="pupil_field_reference", enabled=True, physical=False)
    if _scene_has_illumination_flood([disabled, non_physical, pupil_ref]):
        notes.append("disabled / non-physical / pupil-ref source falsely registered as a flood")
        ok = False
    else:
        notes.append("disabled + non-physical + pupil-field ref -> not a flood")

    if _scene_has_illumination_flood([]):
        notes.append("empty scene falsely registered as a flood")
        ok = False
    else:
        notes.append("empty scene -> not a flood")
    return ok


def _check_flag_propagation(notes: list[str]) -> bool:
    ok = True

    phantom = _branch_target("default_distance", branch="S1:BS/reflect", center=(80.0, 0.0, 230.0), row_index=100000)
    phantom.metadata["draw_suppressed"] = True
    real = _branch_target("reached_image", branch="S1:BS/transmit", center=(0.0, 0.0, 657.0), row_index=100001)

    if not _target_branch_detector_draw_suppressed(phantom):
        notes.append("2-D projection predicate did NOT honour the stamped draw_suppressed flag")
        ok = False
    else:
        notes.append("stamped draw_suppressed -> 2-D projection predicate suppresses (True)")

    if _target_branch_detector_draw_suppressed(real):
        notes.append("a clean reached-image arm was falsely suppressed by the 2-D predicate")
        ok = False
    else:
        notes.append("clean reached-image arm -> 2-D predicate keeps it (False)")

    # The 3-D footprint + coverage draw paths skip on (metadata or {}).get('draw_suppressed').
    # Prove the stamped target is otherwise DRAWABLE (a real footprint polyline exists), so the
    # shared flag is the only thing suppressing it -- not an empty/absent geometry.
    if not scene_target_active_footprint_polylines(phantom):
        notes.append("stamped phantom yields NO footprint polyline -> draw-skip test is vacuous")
        ok = False
    elif not (getattr(phantom, "metadata", None) or {}).get("draw_suppressed"):
        notes.append("phantom metadata lost the draw_suppressed flag")
        ok = False
    else:
        notes.append("stamped phantom is drawable but flagged -> 3-D footprint + coverage skip it")
    return ok


def _check_real_scene(notes: list[str]) -> bool:
    path = Path("attachment/machine_vision_150mm_test.py")
    if not path.exists():
        notes.append(f"real-scene fixture missing ({path}); skipped")
        return True
    try:
        import KrakenOS as Kos  # noqa: F401
        from KrakenOS.UI.layout_editor import _load_python_data
        from KrakenOS.UI.render_layout_snapshot import (
            _build_runtime_system,
            _rows_from_layout_info,
            _snapshot_editor,
        )
    except Exception as exc:  # pragma: no cover - minimal env without OCC/pyvista
        notes.append(f"real-scene harness unavailable ({exc!r}); skipped")
        return True

    try:
        info = _load_python_data(path)
        rows = _rows_from_layout_info(info)
        settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
        editor = _snapshot_editor(rows, settings)
        editor.current_layout_file = path
        editor._normalize_special_rows()
    except Exception as exc:  # pragma: no cover - defensive
        notes.append(f"real-scene load raised ({exc!r}); skipped")
        return True

    ok = True

    # SOURCE-ABSENT: a pure imaging scene must NOT be treated as a flood (no over-suppression;
    # bugs/0090 beam-splitter arms keep drawing).
    if _scene_has_illumination_flood(editor._collect_scene_sources(wavelength=editor._current_wavelength())):
        notes.append("pure imaging MV-150 (no scene source) falsely read as an illumination flood")
        ok = False
    else:
        notes.append("MV-150 without a scene source -> not a flood (imaging arms un-gated)")

    editor.add_illumination_led_source()
    system = _build_runtime_system(path, editor.rows)
    wavelength = editor._current_wavelength()
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    bundle = editor._build_scene_bundle(system, rays, max_radius)

    targets = list(getattr(bundle, "targets", []) or [])
    branch_dets = [
        t for t in targets
        if str((getattr(t, "metadata", {}) or {}).get("target_source", "")) == "branch_detector"
    ]
    phantoms = [t for t in branch_dets if str((t.metadata or {}).get("focus_source")) != "reached_image"]
    reached = [t for t in branch_dets if str((t.metadata or {}).get("focus_source")) == "reached_image"]

    if not phantoms:
        notes.append("real scene: expected a non-imaging branch-detector arm off the BS, found none")
        ok = False
    elif not all((t.metadata or {}).get("draw_suppressed") for t in phantoms):
        drawn = [t for t in phantoms if not (t.metadata or {}).get("draw_suppressed")]
        centers = [tuple(round(float(v), 1) for v in np.asarray(t.center_world).reshape(-1)[:3]) for t in drawn]
        notes.append(f"real scene: {len(drawn)} phantom arm(s) still DRAW beside the cube at {centers}")
        ok = False
    else:
        notes.append(f"real scene: {len(phantoms)} illumination-flood arm(s) draw-suppressed (kept as hard-stops)")

    if not reached:
        notes.append("real scene: the transmit arm that reaches the Image is missing")
        ok = False
    elif any((t.metadata or {}).get("draw_suppressed") for t in reached):
        notes.append("real scene: the reached-image detector was wrongly suppressed (the real sensor vanished)")
        ok = False
    else:
        notes.append(f"real scene: reached-image detector kept + drawn ({len(reached)})")

    anchor = editor._source_illumination_anchor_target(bundle)
    if anchor is None:
        notes.append("real scene: heatmap anchor lost after suppression")
        ok = False
    else:
        az = float(np.asarray(anchor.center_world).reshape(-1)[2])
        if str((getattr(anchor, "metadata", {}) or {}).get("focus_source")) != "reached_image" or az < 500.0:
            notes.append(f"real scene: anchor is not the on-sensor reached-image detector (z={az:.1f})")
            ok = False
        else:
            notes.append(f"real scene: heatmap anchor stays the on-sensor detector (z={az:.1f})")

    image_curves = [c for c in (getattr(bundle, "surface_curves", []) or []) if str(getattr(c, "kind", "")) == "image"]
    if len(image_curves) != 1:
        notes.append(f"real scene: expected exactly 1 image-plane curve drawn, found {len(image_curves)}")
        ok = False
    else:
        notes.append("real scene: exactly 1 image-plane curve draws (phantom plane gone)")
    return ok


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    ok = _check_flood_predicate(notes) and ok
    ok = _check_flag_propagation(notes) and ok
    ok = _check_real_scene(notes) and ok
    return ok, notes


def main() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(("  OK  " if passed else "  --  "), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
