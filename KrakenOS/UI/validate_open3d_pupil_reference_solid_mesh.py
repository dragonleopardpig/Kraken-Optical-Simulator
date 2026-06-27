"""Display-free guard for bugs/0171: the first-order PUPIL REFERENCE must build real solid
meshes when the reference chain carries a promoted optical solid / beam-splitter cube,
otherwise its non-sequential PupilCalc launch dies on the dummy int-``EEE``.

`KrakenSys` builds ``EEE`` (per-surface mesh array) two ways: ``BUILD==1`` ->
``Prerequisites3DSolids`` (real PyVista meshes); else ``Prerequisites3DSolidsDummy`` which
appends the int ``0`` for every surface. A non-sequential trace on the int-``EEE`` system
raises ``MeshRayTraceError('non-sequential surface N: int has no ray_trace ...')``. The
0166 pupil reference built with ``build=0`` on the assumption it never NS-traces -- false
when a promoted solid is in the reference chain. The fix gates the reference build on
``_rows_require_geometry_build``.

This guard pins (display-free):

  * THE TRAP -- a ``build=0`` system's main ``EEE`` entries are ints (a future caller that
    routes a NON-seq trace through a build=0 system would break again);
  * THE REMEDY -- the same specs at ``build=1`` give real-mesh ``EEE`` (no ints);
  * THE GATE -- ``_pupil_model_inputs`` builds the reference with
    ``build=1 if _rows_require_geometry_build(...) else 0`` (non-seq -> meshes, sequential
    -> the 0166 build=0 speedup preserved);
  * INTEGRATION (only if the beam-splitter fixture is present) -- the reference pupil
    system on a real promoted-solid scene has no int ``EEE`` and ``PupilCalc.Pattern`` no
    longer raises.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_pupil_reference_solid_mesh

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from KrakenOS.UI import layout_editor as layout_editor_module
from KrakenOS.UI.services.analysis_compute_workflow import AnalysisComputeWorkflowMixin
from KrakenOS.UI.validate_open3d_best_focus_surface import _build_scene_bundle_for_double_gauss

_MEASURED_FIXTURE = Path(__file__).resolve().parents[2] / "attachment" / "machine_vision_150mm_measured_test.py"


def _eee_int_entries(system, count: int = 8) -> list[int]:
    eee = system.Pr3D.EEE
    n = min(len(eee), count)
    return [j for j in range(n) if isinstance(eee[j], int)]


def _check_trap_and_remedy(failures: list[str], notes: list[str]) -> None:
    editor, _system, _bundle = _build_scene_bundle_for_double_gauss()
    if editor is None:
        notes.append("SKIP trap/remedy: double-gauss fixture unavailable")
        return
    specs = editor._serializable_row_specs()
    cap = io.StringIO()
    with redirect_stdout(cap), redirect_stderr(cap):
        sys0 = layout_editor_module._build_system_from_specs(specs, build=0, apply_optical_solid_output_ports=False)
        sys1 = layout_editor_module._build_system_from_specs(specs, build=1, apply_optical_solid_output_ports=False)
    int0 = _eee_int_entries(sys0)
    int1 = _eee_int_entries(sys1)
    if not int0:
        failures.append("TRAP: a build=0 system's EEE main entries are NOT ints (the trap is gone -- guard stale?)")
    if int1:
        failures.append(f"REMEDY: a build=1 system still has int EEE entries {int1} (no real meshes)")
    notes.append(f"trap: build=0 int-EEE={bool(int0)} ; remedy: build=1 int-EEE={bool(int1)}")


def _check_source_gate(failures: list[str]) -> None:
    src = inspect.getsource(AnalysisComputeWorkflowMixin._pupil_model_inputs)
    if "_rows_require_geometry_build" not in src:
        failures.append("GATE: _pupil_model_inputs does not gate the reference build on _rows_require_geometry_build")
    if "build=1 if" not in src.replace(" ", "").replace("build=1if", "build=1 if"):
        # tolerate spacing; the gate must conditionally pick build=1
        if "build=1" not in src:
            failures.append("GATE: _pupil_model_inputs never builds the reference at build=1")


def _check_integration(failures: list[str], notes: list[str]) -> None:
    if not _MEASURED_FIXTURE.exists():
        notes.append("SKIP integration: beam-splitter fixture not present (attachment is Filen-synced)")
        return
    try:
        import KrakenOS as Kos
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data
        from KrakenOS.UI.render_layout_snapshot import _snapshot_editor

        info = _load_python_data(_MEASURED_FIXTURE)
        settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
        rows = [KrakenLayoutEditor._row_from_layout_item(it) for it in info["surfaces"]]
        rows[0].surface = "Object"
        rows[-1].surface = "Image"
        editor = _snapshot_editor(rows, settings)
        editor.tk = object()
        editor._normalize_special_rows()
        cap = io.StringIO()
        with redirect_stdout(cap), redirect_stderr(cap):
            system = editor.build_system()
            if not editor._layout_needs_paraxial_reference(editor.rows):
                notes.append("SKIP integration: fixture is not a non-seq reference scene")
                return
            psys, _prows, pidx = editor._pupil_model_inputs(system, build_reference=True)
        ints = _eee_int_entries(psys, count=12)
        if ints:
            failures.append(f"INTEGRATION: pupil reference still has int EEE entries {ints} on the solid scene")
        wl = float(editor._current_wavelength())
        with redirect_stdout(cap), redirect_stderr(cap):
            pc = Kos.PupilCalc(psys, int(pidx), wl, editor._current_aperture_type(), float(editor._current_aperture_value()))
            pc.Samp = 6
            pc.Ptype = "hexapolar"
            pc.FieldType = "height"
            pc.FieldX = 0.0
            pc.FieldY = 0.0
            pc.Pattern()
        notes.append("integration: beam-splitter pupil reference EEE has no ints + PupilCalc.Pattern OK")
    except Exception as exc:
        failures.append(f"INTEGRATION: pupil reference still fails on the solid scene: {type(exc).__name__}: {str(exc)[:80]}")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_trap_and_remedy(failures, notes)
    _check_source_gate(failures)
    _check_integration(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] pupil first-order reference must build solid meshes for non-seq scenes (bugs/0171)")
        return 1
    print("[PASS] pupil reference builds real meshes on promoted-solid scenes -- no int-EEE NS crash (0171)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
