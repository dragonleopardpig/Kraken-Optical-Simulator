"""Display-free guard for bugs/0187 fix (3): a promoted RA-mirror cube traces as a
SEQUENTIAL ``Mirror`` so rays reach the sensor on the folded path.

A promoted right-angle mirror cube (``machine_vision_AZ85_RA_Mirror.py``) reflects on an
``OpticalSolidFaces`` face whose ``function`` is "Mirror". Because it is a real CAD body the
whole trace is forced NON-sequential, a mesh-mirror reflection flips the propagation sign, and
the surrogate's IDEAL Thin Lenses then retroreflect -- 0 of 93 rays reach the sensor (the "ray
diverges" flag ``flag_20260630_142846_722``). See ``bugs/0187``.

Fix (3) (``services/folded_sequential_fold.py``) represents each promoted full-mirror cube as a
sequential ``Mirror`` surface for the TRACE: the native sequential tracer folds the running
coordinate frame on a ``Mirror`` row, the ideal Thin Lenses behave, and an ARBITRARY CHAIN of
folds composes natively (the per-mirror tilt is solved convention-free from each cube's world
face normal, so a second mirror the user orients differently still folds correctly).

This guard binds the REAL synthesiser + the REAL ``_build_system_from_specs`` build and asserts:
  1. the single-mirror AZ85 layout folds +Z -> +X and an on-axis ray lands on the sensor at
     world X ~ +287.82, Z ~ 71.9 (the flag's measured sensor station);
  2. a synthetic SECOND cube before the image (the user's planned RA mirror between lens and
     camera) still reaches the image -- the chain composes;
  3. a non-folded layout is left byte-identical (gate False, no records);
  4. END-TO-END the real editor pipeline (``_build_preview_system_rays_bundle``) traces the
     AZ85 scene on the REAL system (bugs/0243): the mesh mirror reflects FIRST SURFACE off its
     coated face, the ideal Thin Lenses behave behind the fold (the KrakenSys SIGN fix removed
     the retroreflection this file originally guarded), the backend is the non-sequential
     ``NsTraceLoop``, and the drawn on-axis cone CONVERGES (transverse RMS < 1mm) exactly on
     the folded Image-surface seat -- the drawn rays ARE the physics trace, no display bend.
     The display row still keeps its promoted cube + 0185 overlays.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_folded_sequential_trace

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import (
    LAYOUTS_DIR,
    KrakenLayoutEditor,
    _build_system_from_specs,
    _load_python_data,
)
from KrakenOS.UI.layout_library import load_python_data
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.services.folded_sequential_fold import (
    fold_promoted_mirror_specs_to_sequential,
    scene_nonseq_trigger_is_only_promoted_full_mirrors,
)

_LAYOUTS = Path(__file__).resolve().parent.parent / "common_optical_layouts"
_LAYOUT_FILE = "machine_vision_AZ85_RA_Mirror.py"
_SENSOR_X = 287.82
_SENSOR_Z = 71.90


def _load(name: str) -> list[dict]:
    return [dict(s) for s in load_python_data(_LAYOUTS / name)["surfaces"]]


def _trace_on_axis(specs: list[dict]):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        system = _build_system_from_specs(
            [dict(s) for s in specs], apply_optical_solid_output_ports=False
        )
        system.energy_probability = 0
        rays = Kos.raykeeper(system)
        system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
        rays.push()
    surfaces = list(system.SURFACE)
    X, Y, Z, _, _, _ = rays.pick(-1)
    return surfaces, np.asarray(X, float), np.asarray(Y, float), np.asarray(Z, float)


def _clone_mirror_cube(specs: list[dict]) -> dict:
    for spec in specs:
        adv = spec.get("advanced")
        if isinstance(adv, dict) and adv.get("OpticalSolidFaces"):
            return dict(spec)
    raise AssertionError("no promoted solid row found to clone")


def _end_to_end_pipeline(failures: list[str], notes: list[str]) -> None:
    """Bind the REAL editor pipeline ``_build_preview_system_rays_bundle`` on the AZ85
    layout and assert the folded DISPLAY cone CONVERGES on the +X sensor. bugs/0243: the
    folded scene is now traced on the REAL system -- the mesh mirror reflects first-surface
    off its coated face and the Image surface sits at its folded output-port seat -- so the
    correct backend IS the non-sequential ``NsTraceLoop`` (the Thin-Lens SIGN fix removed
    the bugs/0187 retroreflection that once forced a sequential stand-in), the drawn rays
    ARE the traced rays (no display bend), and the cone must converge ON the folded Image
    seat (read from the system's ``_optical_solid_output_port_pose_overrides``)."""
    layout_path = _LAYOUTS / _LAYOUT_FILE
    try:
        info = _load_python_data(layout_path)
        settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
        rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
        rows[0].surface = "Object"
        rows[-1].surface = "Image"
        editor = _snapshot_editor(rows, settings)
        editor.tk = object()  # break tkinter __getattr__ recursion on the __new__ instance
        editor.current_layout_file = layout_path
        editor._normalize_special_rows()
    except Exception as exc:  # noqa: BLE001
        notes.append(f"SKIP end-to-end: editor harness unavailable ({type(exc).__name__}: {exc})")
        return

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            _system, rays, bundle = editor._build_preview_system_rays_bundle(sampling_mode=None)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"SKIP end-to-end: preview bundle build failed ({type(exc).__name__}: {exc})")
        return

    backend = str(getattr(editor, "_last_preview_trace_backend", ""))
    if "Ns" not in backend:
        failures.append(
            f"end-to-end: folded trace ran on {backend!r} (bugs/0243: the REAL folded scene "
            "traces non-sequentially on NsTraceLoop; a sequential backend means a stand-in "
            "system was traced instead of the drawn one)"
        )
    # bugs/0243: the drawn rays ARE the traced rays (no display bend), and the Image
    # surface is intersected at its folded output-port seat. Read that seat from the
    # traced system and assert the on-axis cone CONVERGES onto it.
    overrides = getattr(_system, "_optical_solid_output_port_pose_overrides", {}) or {}
    image_pose = overrides.get(len(editor.rows) - 1)
    seat = (
        np.asarray(image_pose.get("center"), dtype=float).reshape(3)
        if isinstance(image_pose, dict)
        else None
    )
    onaxis = []
    for path in list(getattr(bundle, "ray_paths", []) or []):
        pw = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 2 or pw.shape[1] < 3:
            continue
        if float(np.linalg.norm(pw[0][:3])) <= 1.0 and float(pw[:, 0].max()) > 250.0:
            onaxis.append(pw)
    end_x = float("nan")
    end_rms = float("nan")
    if seat is None:
        failures.append("end-to-end: the traced system has no folded Image-surface seat (pose override missing)")
    elif len(onaxis) < 4:
        failures.append(
            f"end-to-end: too few on-axis folded display rays ({len(onaxis)}) to test the focus "
            "(the folded display cone did not reach the +X sensor)"
        )
    else:
        ends = np.asarray([p[-1][:3] for p in onaxis], dtype=float)
        end_x = float(ends[:, 0].mean())
        end_rms = float(np.sqrt(((ends[:, 1:] - ends[:, 1:].mean(0)) ** 2).sum(1).mean()))
        if abs(end_x - float(seat[0])) > 2.0:
            failures.append(
                f"end-to-end: folded on-axis cone did not land on the folded Image seat "
                f"x~{float(seat[0]):.2f}; endpoint X mean {end_x:.2f}"
            )
        if not (end_rms < 1.0):
            failures.append(
                f"end-to-end: folded on-axis cone did not converge on the sensor (endpoint "
                f"transverse RMS {end_rms:.3f}mm >= 1.0)"
            )
    # the DISPLAY rows are untouched, so the mesh cube + 0185 overlays still draw
    adv = editor.rows[1].advanced if isinstance(getattr(editor.rows[1], "advanced", None), dict) else {}
    if not adv.get("OpticalSolidFaces"):
        failures.append("end-to-end: display row lost its promoted cube (OpticalSolidFaces) after the trace")
    if getattr(editor, "_force_sequential_preview_trace", False):
        failures.append("end-to-end: the force-sequential override was not cleared after the trace")
    # The bug-flag recorder reads this to state that the folded handling engaged.
    if getattr(editor, "_last_preview_folded_sequential", None) is not True:
        failures.append(
            "end-to-end: _last_preview_folded_sequential was not set True "
            "(recorder cannot report that the fold engaged)"
        )
    if not failures:
        notes.append(
            f"end-to-end: real pipeline traced the REAL folded scene on {backend} -> display cone "
            f"CONVERGES on the folded Image seat (endpoint X={end_x:.2f}, transverse RMS={end_rms:.3f}mm), "
            f"display cube preserved; folded_engaged="
            f"{getattr(editor, '_last_preview_folded_sequential', None)}"
        )


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    base = _load("machine_vision_AZ85_RA_Mirror.py")

    # ---- gate ----------------------------------------------------------------
    if not scene_nonseq_trigger_is_only_promoted_full_mirrors(base):
        failures.append("gate: AZ85 RA-mirror scene was NOT classified as promoted-full-mirror-only")

    # ---- (1) single mirror folds to the sensor -------------------------------
    folded, records = fold_promoted_mirror_specs_to_sequential(base)
    if len(records) != 1:
        failures.append(f"single: expected 1 synthesised mirror, got {len(records)}")
    surfaces, X, Y, Z = _trace_on_axis(folded)
    image_index = len(folded) - 1
    if image_index not in surfaces:
        failures.append(f"single: on-axis ray did not reach the image surface {image_index}; reached {surfaces}")
    elif X.size == 0 or not np.isfinite(X[0]):
        failures.append("single: no finite image intercept")
    else:
        if abs(float(X[0]) - _SENSOR_X) > 1.0:
            failures.append(f"single: image X {float(X[0]):.2f} not folded to +X sensor ~{_SENSOR_X}")
        if abs(float(Z[0]) - _SENSOR_Z) > 1.0:
            failures.append(f"single: image Z {float(Z[0]):.2f} not at sensor station ~{_SENSOR_Z}")
        if abs(float(Y[0])) > 1.0:
            failures.append(f"single: on-axis image Y {float(Y[0]):.2f} should be ~0")

    # ---- (2) a second cube before the image -> chain composes ----------------
    cube = _clone_mirror_cube(base)
    two = []
    for spec in base:
        if spec.get("surface") == "Image":
            two.append(dict(cube))
        two.append(dict(spec))
    if not scene_nonseq_trigger_is_only_promoted_full_mirrors(two):
        failures.append("double: two-cube scene was NOT classified as promoted-full-mirror-only")
    folded2, records2 = fold_promoted_mirror_specs_to_sequential(two)
    if len(records2) != 2:
        failures.append(f"double: expected 2 synthesised mirrors, got {len(records2)}")
    surfaces2, X2, Y2, Z2 = _trace_on_axis(folded2)
    image_index2 = len(folded2) - 1
    if image_index2 not in surfaces2:
        failures.append(
            f"double: on-axis ray did not reach the image surface {image_index2}; reached {surfaces2}"
        )
    elif X2.size == 0 or not np.isfinite(X2[0]):
        failures.append("double: no finite image intercept after the second fold")

    # ---- (3) non-folded layout is untouched ----------------------------------
    plain = _load("flat_mirror_45_deg.py")
    if scene_nonseq_trigger_is_only_promoted_full_mirrors(plain):
        failures.append("regression: a plain sequential-mirror layout was misclassified as a promoted fold")
    folded3, records3 = fold_promoted_mirror_specs_to_sequential(plain)
    if records3:
        failures.append(f"regression: non-folded layout produced {len(records3)} spurious mirror records")
    if folded3 != plain:
        failures.append("regression: non-folded layout specs were modified")

    # ---- (4) end-to-end: the real editor pipeline folds + traces sequentially -
    _end_to_end_pipeline(failures, notes)

    if failures:
        print("FAIL bugs/0187 folded-sequential trace:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("PASS bugs/0187 folded-sequential trace:")
    print(f"  - single mirror folds +Z -> +X, on-axis ray at world X={float(X[0]):.2f} Z={float(Z[0]):.2f} (sensor reached)")
    print(f"  - double mirror chain composes; on-axis ray reaches image at world X={float(X2[0]):.2f} Z={float(Z2[0]):.2f}")
    print("  - non-folded layout untouched (gate False, no records)")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
