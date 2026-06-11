"""Validate that the Open 3D Ray count control stays in sync with the 2D view.

The 2D trace/display controls create ``editor.ray_count_var`` (label "Ray fan
count"). The embedded Open 3D inspector must surface a Ray count too, and editing
it has to move the *same* variable so the 2D and 3D counts never diverge.

This guards both halves of the contract:

* runtime: ``Open3DLiveControlsPanel.editor_var`` returns the editor's existing
  ``ray_count_var`` by identity (the shared accessor the toolbar entry uses), so
  changes flow both directions; unknown names fall back to a fresh StringVar.
* source: the always-visible top View toolbar builds a "Ray count" entry wired to
  that shared accessor and the field-sync commit path.

Needs a Tk root (run under Xvfb) but no VTK/Open 3D viewer.
"""

from __future__ import annotations

import inspect
import tkinter as tk

from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.panels.open3d_live_controls import Open3DLiveControlsPanel
from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel


class _StubEditor:
    pass


class _StubInspector:
    def __init__(self, editor: _StubEditor) -> None:
        self.editor = editor


def main() -> int:
    root = tk.Tk()
    root.withdraw()
    try:
        editor = _StubEditor()
        # Mimic what MainTraceDisplayControlsPanel.build() sets on the editor.
        editor.ray_count_var = tk.StringVar(value="31")
        panel = Open3DLiveControlsPanel(
            _StubInspector(editor),
            source_model_values=(),
            pupil_pattern_values=(),
            field_type_values=(),
            source_direction_preset_values=(),
            camera_none_label="(none)",
            camera_names=lambda: (),
        )

        shared = panel.editor_var("ray_count_var")
        shared.set("77")
        editor_reads_toolbar = editor.ray_count_var.get() == "77"
        editor.ray_count_var.set("9")
        toolbar_reads_editor = shared.get() == "9"
        fallback = panel.editor_var("missing_var_zzz")

        normalized_top = inspect.getsource(Open3DTopControlsPanel).replace("self.inspector.", "self.")
        toolbar_source = inspect.getsource(Kraken3DInspector.__init__) + "\n" + normalized_top

        checks = [
            ("live panel shares the editor's ray_count_var by identity", shared is editor.ray_count_var),
            ("editing the 3D ray count updates the 2D var", editor_reads_toolbar),
            ("editing the 2D ray count updates the 3D entry", toolbar_reads_editor),
            (
                "editor_var falls back to a fresh StringVar for unknown names",
                isinstance(fallback, tk.StringVar) and fallback is not editor.ray_count_var,
            ),
            ("top View toolbar builds a Ray count entry", '"Ray count"' in toolbar_source),
            ('toolbar Ray count binds the shared accessor', '_editor_var("ray_count_var")' in toolbar_source),
            (
                "toolbar Ray count commits via the field-sync path",
                "_commit_live_control_update(sync_fields=True)" in toolbar_source,
            ),
        ]
    finally:
        root.destroy()

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Open 3D ray count toolbar sync validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Open 3D ray count toolbar sync validation passed (3D Ray count shares the 2D ray_count_var).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
