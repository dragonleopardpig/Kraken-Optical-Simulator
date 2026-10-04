"""A bug flag written by the shell, for when there is no 3D inspector to write it (bugs/0959).

The inspector's `flag_bug` writes a flag bundle and, under a shell, asks the shell for its pictures
and state (`capture_flag_shell`). A flag must also work when the inspector could not be built --
that is when one is wanted most. This writes the same bundle without the 3D parts:

    screenshot.png   the shell's window (the shell's capture draws it)
    description.txt  empty until the prompt is answered
    state.json       version, time, build, layout identity, and the shell's block under "shell"

It is toolkit-free: the shell passes how to capture itself, where to say what happened and how to
ask for the description.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Callable


def flag_shell_window(editor, capture: Callable, *, set_status: Callable[[str], None],
                      show_description: Callable) -> "Path | None":
    """Write a window-only flag bundle and open its description prompt. Returns the bundle
    directory, or None when nothing could be written. Never raises."""
    from KrakenOS.UI import open3d_inspector
    from KrakenOS.UI.services.flag_description import FlagDescription

    def debug(message: str) -> None:
        try:
            editor.append_debug(message)
        except Exception:
            pass

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    bundle_dir = open3d_inspector.ATTACHMENT_DIR / "recorded_bug_repros" / f"flag_{stamp}"
    try:
        bundle_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        set_status(f"Flag bug failed: could not create the bundle ({exc}).")
        return None
    shell_state: dict = {}
    try:
        shell_state = dict(capture(bundle_dir, as_screenshot=True) or {})
    except Exception as exc:
        debug(f"Flag: shell capture failed: {exc}")
    screenshot = bundle_dir / "screenshot.png"
    try:
        (bundle_dir / "description.txt").write_text("", encoding="utf-8")
    except Exception:
        pass
    try:
        identity = open3d_inspector.Kraken3DInspector._flag_layout_identity(SimpleNamespace(editor=editor))
    except Exception:
        identity = {}
    state_path = bundle_dir / "state.json"
    payload = {
        "version": 1,
        "captured_at_iso": datetime.now().isoformat(timespec="seconds"),
        "build": open3d_inspector._open3d_running_build_stamp(),
        "source": "shell_window",
        "description": "",
        "screenshot": "screenshot.png" if screenshot.exists() else None,
        "screenshot_kind": str(shell_state.get("screenshot_of") or "window"),
        "layout": identity,
        "shell": shell_state,
    }
    try:
        state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:
        debug(f"Flag: state write failed: {exc}")
    set_status(f"Flagged bug: {bundle_dir.name}. Type a description in the popup.")
    try:
        editor.append_progress(f"Flagged bug (window): {bundle_dir}")
    except Exception:
        pass
    show_description(FlagDescription(
        bundle_dir=bundle_dir, state_path=state_path, flag_event_payload=None, set_status=set_status,
        debug=debug, discard=lambda: open3d_inspector.Kraken3DInspector._discard_flag_bundle(bundle_dir)))
    return bundle_dir
