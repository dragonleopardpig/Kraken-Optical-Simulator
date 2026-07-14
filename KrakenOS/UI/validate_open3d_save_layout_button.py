"""Display-free guard: the Open 3D inspector can save the layout .py from inside the 3D window.

A folded 54x54 solve can be driven entirely from Open 3D (FOV popup, carry, snap...). Before
this, the only way to persist it was to return to the main window's File -> Save, so the source
.py silently drifted from the exported STEP / flagged scene. ``Kraken3DInspector.save_layout``
plus a "Save Layout" toolbar button close that gap.

The correctness hinge: ``_write_layout_file`` reads the editor TABLE back through
``_read_rows_from_table`` (the table is the source of truth for the writer), while the inspector
mutates ``self.editor.rows`` in place. So the inspector's save MUST re-sync the table from rows
first, then delegate to the editor's own ``save_layout`` -- in that order -- or a 3D-only edit is
written stale.

  (A) METHOD EXISTS: Kraken3DInspector.save_layout is defined.
  (B) DELEGATES + SYNCS: its source syncs the editor table and calls the editor's save_layout.
  (C) ORDER + SUCCESS: on a fake editor, save_layout syncs the table BEFORE saving, returns True,
      and reports the saved file name in the status line.
  (D) CANCEL IS HONEST: when the editor's save_layout returns False (Save As dismissed), the
      inspector returns False and says "Save cancelled" (it does not claim a save happened).
  (E) TOOLBAR WIRES IT: the View toolbar packs a "Save Layout" button bound to save_layout.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_save_layout_button
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


class _StatusVar:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class _FakeEditor:
    """Minimal stand-in for KrakenLayoutEditor's save surface."""

    def __init__(self, *, current_file, save_returns: bool) -> None:
        self.current_layout_file = current_file
        self._save_returns = save_returns
        self.calls: list[str] = []
        self.progress: list[str] = []
        self.debug: list[str] = []

    def _sync_table(self) -> None:
        self.calls.append("sync")

    def save_layout(self) -> bool:
        self.calls.append("save")
        return self._save_returns

    def append_progress(self, message: str) -> None:
        self.progress.append(message)

    def append_debug(self, message: str) -> None:
        self.debug.append(message)


class _FakeInspector:
    def __init__(self, editor: _FakeEditor) -> None:
        self.editor = editor
        self.status_var = _StatusVar()


def validate() -> list[Check]:
    from pathlib import Path

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel

    checks: list[Check] = []

    has_method = callable(getattr(Kraken3DInspector, "save_layout", None))
    checks.append(Check(
        "METHOD EXISTS: Kraken3DInspector.save_layout is defined",
        has_method,
        f"save_layout present: {has_method}",
    ))

    src = inspect.getsource(Kraken3DInspector.save_layout) if has_method else ""
    delegates = "self.editor._sync_table()" in src and "self.editor.save_layout()" in src
    checks.append(Check(
        "DELEGATES + SYNCS: save_layout re-syncs the editor table and calls editor.save_layout",
        delegates,
        f"sync={'self.editor._sync_table()' in src} delegate={'self.editor.save_layout()' in src}",
    ))

    editor = _FakeEditor(current_file=Path("/tmp/machine_vision_AZ85_RA_Mirror.py"), save_returns=True)
    inspector = _FakeInspector(editor)
    result = Kraken3DInspector.save_layout(inspector)
    ordered_ok = editor.calls == ["sync", "save"]
    status_ok = inspector.status_var.value == "Saved machine_vision_AZ85_RA_Mirror.py"
    checks.append(Check(
        "ORDER + SUCCESS: syncs BEFORE saving, returns True, reports the saved file name",
        bool(result) and ordered_ok and status_ok,
        f"result={result} calls={editor.calls} status={inspector.status_var.value!r}",
    ))

    cancel_editor = _FakeEditor(current_file=None, save_returns=False)
    cancel_inspector = _FakeInspector(cancel_editor)
    cancel_result = Kraken3DInspector.save_layout(cancel_inspector)
    cancel_ok = (cancel_result is False) and cancel_inspector.status_var.value == "Save cancelled"
    checks.append(Check(
        "CANCEL IS HONEST: a dismissed Save As returns False and says 'Save cancelled'",
        cancel_ok,
        f"result={cancel_result} status={cancel_inspector.status_var.value!r}",
    ))

    toolbar_src = inspect.getsource(Open3DTopControlsPanel.build_view_toolbar)
    has_label = '"Save Layout"' in toolbar_src
    has_command = "self.inspector.save_layout" in toolbar_src
    checks.append(Check(
        "TOOLBAR WIRES IT: the View toolbar packs a 'Save Layout' button bound to save_layout",
        has_label and has_command,
        f"label={has_label} command={has_command}",
    ))

    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate()
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if any(not c.ok for c in checks):
        raise SystemExit(1)
    print("Open 3D Save-Layout button validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
