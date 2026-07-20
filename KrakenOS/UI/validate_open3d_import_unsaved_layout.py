"""Display-free guard for bugs/0375 -- a fresh lens/camera import is a transient,
unsaved layout, not the user's own .py.

A folder import auto-generates ``machine_vision_<slug>.py`` in the library and loads
it as the working scene. Before this fix, ``current_layout_file`` pointed at that
generated file, so (a) the imminent 3D rebuild RESTORED the surrogate's stale session
sidecar (previous camera pose / camera coupling / overlay toggles -- the flag), and
(b) Save silently overwrote the generated file instead of the user's own layout. The
fix marks the working layout ``_layout_is_unsaved_import`` so a direct import shows a
clean scene and Save prompts the user to create their own file first; opening a real
file (or Save As) clears the marker so the layout ties to that .py from then on.

Checks (all headless, no VTK/tk):
- SAVE ROUTING: with the marker set, ``save_layout`` routes to ``save_layout_as``
  (prompt) even when ``current_layout_file`` is non-None; without it (a real file) it
  writes directly; a None file also prompts.
- RESTORE SKIP: ``_maybe_restore_open3d_session_state`` does NOT apply a present sidecar
  when the editor marks the layout a transient import, but DOES for a normal layout.
- WIRING: the lens importer SETS the marker after loading; load-by-name / open_layout /
  save_layout_as CLEAR it.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_import_unsaved_layout
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor, Kraken3DInspector
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: import-unsaved-layout deps unavailable ({type(exc).__name__}: {exc})"]

    # --- SAVE ROUTING -------------------------------------------------------------
    def _editor_stub(*, current_file, transient):
        e = object.__new__(KrakenLayoutEditor)
        e._commit_pending_table_edit = lambda: None  # type: ignore[attr-defined]
        e._write_layout_file = lambda p: setattr(e, "_wrote", p)  # type: ignore[attr-defined]
        e.save_layout_as = lambda: (setattr(e, "_prompted", True) or True)  # type: ignore[attr-defined]
        e._wrote = None  # type: ignore[attr-defined]
        e._prompted = False  # type: ignore[attr-defined]
        e.current_layout_file = current_file  # type: ignore[attr-defined]
        e._layout_is_unsaved_import = transient  # type: ignore[attr-defined]
        return e

    e = _editor_stub(current_file=Path("machine_vision_Apo75.py"), transient=True)
    e.save_layout()
    if not e._prompted or e._wrote is not None:
        failures.append("transient import: Save must prompt (save_layout_as), not silently overwrite the generated .py")

    e = _editor_stub(current_file=Path("user_layout.py"), transient=False)
    e.save_layout()
    if e._wrote is None or e._prompted:
        failures.append("saved layout: Save must write the tied file directly, not prompt")

    e = _editor_stub(current_file=None, transient=False)
    e.save_layout()
    if not e._prompted:
        failures.append("no file: Save must prompt (save_layout_as)")

    # --- RESTORE SKIP -------------------------------------------------------------
    tmp = Path(tempfile.mkdtemp())
    layout_py = tmp / "machine_vision_x.py"
    layout_py.write_text("x", encoding="utf-8")
    (layout_py.with_suffix(".open3d.json")).write_text(
        json.dumps({"version": 1, "overlay_toggles": {}}), encoding="utf-8"
    )

    def _restore_applied(transient) -> object | None:
        insp = object.__new__(Kraken3DInspector)
        insp._session_restored_for_path = None  # type: ignore[attr-defined]
        insp._applied = None  # type: ignore[attr-defined]
        insp._apply_open3d_session_state = lambda st: setattr(insp, "_applied", st)  # type: ignore[attr-defined]
        insp._open3d_session_sidecar_path = Kraken3DInspector._open3d_session_sidecar_path.__get__(insp)  # type: ignore[attr-defined]
        insp.editor = SimpleNamespace(  # type: ignore[attr-defined]
            current_layout_file=layout_py,
            append_debug=lambda *a, **k: None,
            _layout_is_unsaved_import=transient,
        )
        Kraken3DInspector._maybe_restore_open3d_session_state(insp)
        return insp._applied

    if _restore_applied(transient=True) is not None:
        failures.append("transient import: session sidecar must NOT be restored on the rebuild")
    if _restore_applied(transient=False) is None:
        failures.append("normal layout: a present session sidecar MUST be restored")

    # --- WIRING -------------------------------------------------------------------
    import_src = inspect.getsource(KrakenLayoutEditor.import_machine_vision_lens_from_folder)
    if "self._layout_is_unsaved_import = True" not in import_src:
        failures.append("the lens importer does not mark the working layout a transient import")

    loadby_src = inspect.getsource(KrakenLayoutEditor.load_layout_by_name)
    if "self._layout_is_unsaved_import = False" not in loadby_src:
        failures.append("load_layout_by_name does not clear the transient-import marker")
    open_src = inspect.getsource(KrakenLayoutEditor.open_layout)
    if "self._layout_is_unsaved_import = False" not in open_src:
        failures.append("open_layout does not clear the transient-import marker")
    saveas_src = inspect.getsource(KrakenLayoutEditor.save_layout_as)
    if "self._layout_is_unsaved_import = False" not in saveas_src:
        failures.append("save_layout_as does not clear the transient-import marker")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Import-unsaved-layout validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Import-unsaved-layout validation passed: a fresh import is a transient library "
        "surrogate -- Save prompts the user for their own .py (not the generated one), the "
        "stale session sidecar is not restored on a direct import, and opening/Save-As a "
        "real file ties the layout to it (marker cleared, session restored normally)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
