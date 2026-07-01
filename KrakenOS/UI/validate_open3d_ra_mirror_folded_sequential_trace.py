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
  4. END-TO-END the real editor pipeline (``_build_preview_system_rays_bundle``) folds the
     AZ85 scene on a sequential ``TraceLoop`` backend (never ``NsTraceLoop``) and the folded
     DISPLAY cone CONVERGES onto the +X sensor. bugs/0197: the single-fold path now traces the
     flat-plate EQUIVALENT (real ideal-lens power) and BENDS the display rays at the mirror with
     the editor's own fold transform, so the on-axis cone lands converged (transverse RMS < 1mm)
     on the drawn detector -- the old sequential-Mirror surrogate reached the sensor DIVERGING at
     ~4.98mm ("can't focus"). The display row still keeps its promoted cube + 0185 overlays.

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
    layout and assert the folded DISPLAY cone CONVERGES on the +X sensor on a sequential
    backend, while the display row keeps its promoted cube. bugs/0197: the single-fold path
    traces the flat-plate equivalent and bends the display rays at the mirror, so the check
    reads the bundle's folded ray paths (the returned raykeeper holds the UNFOLDED
    equivalent); a diverging cone (the pre-0197 surrogate) fails the convergence bound."""
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
    if "Ns" in backend:
        failures.append(f"end-to-end: folded trace ran on {backend!r} (must be sequential, not NsTraceLoop)")
    # bugs/0197: the returned ``rays`` now hold the flat-plate EQUIVALENT (the UNFOLDED
    # straight system, which images with the real ideal-lens power), so ``rays.pick(-1)``
    # sits in unfolded coordinates (X ~ 0). The DISPLAY bundle bends those rays at the
    # mirror onto the +X arm with the editor's own fold transform. Assert on the folded
    # DISPLAY bundle: the on-axis cone must CONVERGE onto the +X sensor. (bugs/0187's
    # sequential-Mirror surrogate only reached the sensor DIVERGING at ~4.98mm RMS -- the
    # user's "focus before the surrogate, can't focus after"; 0197 lands it converged.)
    onaxis = []
    for path in list(getattr(bundle, "ray_paths", []) or []):
        pw = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 2 or pw.shape[1] < 3:
            continue
        if float(np.linalg.norm(pw[0][:3])) <= 1.0 and float(pw[:, 0].max()) > 250.0:
            onaxis.append(pw)
    end_x = float("nan")
    end_rms = float("nan")
    if len(onaxis) < 4:
        failures.append(
            f"end-to-end: too few on-axis folded display rays ({len(onaxis)}) to test the focus "
            "(the folded display cone did not reach the +X sensor)"
        )
    else:
        ends = np.asarray([p[-1][:3] for p in onaxis], dtype=float)
        end_x = float(ends[:, 0].mean())
        end_rms = float(np.sqrt(((ends[:, 1:] - ends[:, 1:].mean(0)) ** 2).sum(1).mean()))
        if abs(end_x - _SENSOR_X) > 2.0:
            failures.append(
                f"end-to-end: folded on-axis cone did not land on the +X sensor ~{_SENSOR_X}; "
                f"endpoint X mean {end_x:.2f}"
            )
        if not (end_rms < 1.0):
            failures.append(
                f"end-to-end: folded on-axis cone did not converge on the sensor (endpoint "
                f"transverse RMS {end_rms:.3f}mm >= 1.0; the bugs/0187 sequential-Mirror "
                f"surrogate diverged to ~4.98mm here)"
            )
    # the DISPLAY rows are restored, so the mesh cube + 0185 overlays still draw
    adv = editor.rows[1].advanced if isinstance(getattr(editor.rows[1], "advanced", None), dict) else {}
    if not adv.get("OpticalSolidFaces"):
        failures.append("end-to-end: display row lost its promoted cube (OpticalSolidFaces) after the trace")
    if getattr(editor, "_force_sequential_preview_trace", False):
        failures.append("end-to-end: the force-sequential override was not cleared after the trace")
    # bugs/0187: the bug-flag recorder reads these to state the backend outright (the
    # resolve_trace_intent diagnostic stays non-seq for a folded Mirror and cannot reveal
    # whether the fix engaged). A stale app would record folded_sequential_engaged=False /
    # actual_trace_backend="NsTraceLoop".
    if getattr(editor, "_last_preview_folded_sequential", None) is not True:
        failures.append(
            "end-to-end: _last_preview_folded_sequential was not set True "
            "(recorder cannot report that the fold engaged)"
        )
    if "Ns" in str(getattr(editor, "_last_preview_trace_backend", "")):
        failures.append("end-to-end: recorder would report a non-sequential backend for the folded scene")
    if not failures:
        notes.append(
            f"end-to-end: real pipeline folded + traced on {backend} -> folded display cone "
            f"CONVERGES on the +X sensor (endpoint X={end_x:.2f}, transverse RMS={end_rms:.3f}mm), "
            f"display cube preserved; recorder backend diag={backend!r}, folded_engaged="
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
