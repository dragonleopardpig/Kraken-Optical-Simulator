"""Validate the import-from-inspector use-after-free fix (bug 0294).

"Import Lens from Folder" can be launched from *inside* the Open-3D inspector
(:class:`Kraken3DInspector`).  The import replaces the working layout, which runs
``KrakenLayoutEditor._close_scene_viewers_for_layout_replacement`` and -- before
the fix -- **destroyed the 3D inspector**, i.e. the very widget whose handler was
still running.  Control then returned to the handler, which refreshed the now
dead ``vtkTkRenderWindowInteractor``: a use-after-free that SIGSEGVs on real GL
drivers (NVIDIA GLX; llvmpipe survives, which is why it never reproduced under
Xvfb).  Reproduced live on an RTX 4070 with ``bugs/probe_0294_import_crash.py``
(exit 139 before the fix, clean exit 0 after -- the inspector is the *same*
object afterward, refreshed in place).

The fix keeps the initiating inspector alive across the swap and refreshes it in
place:

* the inspector handler sets ``editor._keep_scene_viewers_across_layout_replacement``
  around the editor import (restored in ``finally``) and guards ``winfo_exists()``
  before touching any widget (re-opening a fresh view if it was torn down anyway);
* the workbench ``_close_scene_viewers_for_layout_replacement`` honours that flag
  and skips the inspector destroy.

This guard is a display-free source contract (the real crash needs an NVIDIA GLX
display, absent in CI/Xvfb).  It asserts the handler sets+restores the keep flag
and guards the dead-widget case, and that the workbench honours the flag.  The
live NVIDIA repro is the ``bugs/probe_0294_import_crash.py`` eyeball.
"""

from __future__ import annotations

from pathlib import Path

_UI_DIR = Path(__file__).resolve().parent
INSPECTOR_PATH = _UI_DIR / "open3d_inspector.py"
WORKBENCH_PATH = _UI_DIR / "services" / "layout_table_workbench.py"

_KEEP_FLAG = "_keep_scene_viewers_across_layout_replacement"


def _method_src(text: str, signature: str) -> str | None:
    """Return the body of a top-level-in-class ``def`` (4-space indent) from its
    signature line up to the next same-indent ``def``/``@``/``class``, or ``None``."""
    start = text.find(signature)
    if start < 0:
        return None
    rest = text[start + len(signature):]
    end = len(rest)
    for marker in ("\n    def ", "\n    @", "\nclass "):
        idx = rest.find(marker)
        if 0 <= idx < end:
            end = idx
    return signature + rest[:end]


def run_checks():
    """Return (passed, failures) without printing -- usable as a phase body."""
    failures: list[str] = []

    inspector_src = INSPECTOR_PATH.read_text(encoding="utf-8") if INSPECTOR_PATH.exists() else ""
    workbench_src = WORKBENCH_PATH.read_text(encoding="utf-8") if WORKBENCH_PATH.exists() else ""

    if not inspector_src:
        failures.append("open3d_inspector.py not found")
    if not workbench_src:
        failures.append("layout_table_workbench.py not found")
    if failures:
        return (False, failures)

    # --- inspector handler keeps itself alive across the import layout swap ---
    handler = _method_src(
        inspector_src, "    def import_machine_vision_lens_from_folder(self) -> None:"
    )
    if handler is None:
        failures.append("inspector has no import_machine_vision_lens_from_folder handler")
    else:
        set_flag = handler.find(f"{_KEEP_FLAG} = True")
        editor_import = handler.find("import_machine_vision_lens_from_folder(dialog_parent=self)")
        refresh = handler.find("refresh_from_editor(force_retrace=True)")
        guard = handler.find("winfo_exists()")
        restore = handler.find(f'pop("{_KEEP_FLAG}"')

        if set_flag < 0:
            failures.append(
                "import handler does not set the keep-inspector flag before the "
                "layout swap (0294 use-after-free: the swap would destroy this "
                "inspector out from under the handler)"
            )
        elif editor_import >= 0 and set_flag > editor_import:
            failures.append(
                "import handler sets the keep-inspector flag AFTER calling the "
                "editor import (too late -- the swap already destroyed the inspector)"
            )
        if editor_import < 0:
            failures.append("import handler does not call the editor folder import")
        if guard < 0:
            failures.append(
                "import handler does not guard winfo_exists() before touching its "
                "widgets after the import (0294 use-after-free safety net)"
            )
        elif refresh >= 0 and guard > refresh:
            failures.append(
                "import handler refreshes the inspector BEFORE checking it survived "
                "the swap (winfo_exists must gate the refresh)"
            )
        if refresh < 0:
            failures.append("import handler does not refresh the inspector after import")
        if restore < 0:
            failures.append(
                "import handler does not restore/clear the keep-inspector flag "
                "(leaks: later menu preset loads would then never close the 3D view)"
            )

    # --- workbench honours the keep flag (does NOT destroy a kept inspector) --
    closer = _method_src(
        workbench_src, "    def _close_scene_viewers_for_layout_replacement(self) -> None:"
    )
    if closer is None:
        failures.append(
            "workbench has no _close_scene_viewers_for_layout_replacement method"
        )
    else:
        if _KEEP_FLAG not in closer:
            failures.append(
                "_close_scene_viewers_for_layout_replacement ignores the keep flag "
                "(0294: it would destroy the inspector that launched the import)"
            )
        if "inspector.destroy()" not in closer:
            failures.append(
                "_close_scene_viewers_for_layout_replacement no longer tears the "
                "inspector down at all (should still close it on ordinary swaps)"
            )
        elif "not keep_inspector" not in closer:
            failures.append(
                "_close_scene_viewers_for_layout_replacement destroys the inspector "
                "without gating on the keep flag (0294 use-after-free)"
            )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Import-from-inspector survival validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Import-from-inspector survival validation passed: importing a lens from "
        "inside the Open-3D inspector keeps that inspector alive across the layout "
        "swap and refreshes it in place (no use-after-free segfault on NVIDIA GLX); "
        "live NVIDIA repro (bugs/probe_0294_import_crash.py) is the in-app eyeball."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
