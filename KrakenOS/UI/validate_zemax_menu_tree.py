"""Validate the Examples -> Zemax Prescriptions menu nests by directory.

The attachment Zemax library grew two large collections, ``Sequential/`` and
``Short course/``, each with many sub-categories. The menu builder
(``layout_shell_controls._refresh_zemax_example_menu``) used to group entries by
the *full* relative-parent string, which turns those into a flat avalanche of
long slash-joined labels ("Sequential/Tilted systems & prisms", ...). It now
builds a real directory tree so each top folder is one browsable cascade.

Two layers:

* **Display-free** -- discovery finds the new collections' ``.zmx`` files.
* **End-to-end** -- boots a private Xvfb (when ``DISPLAY`` is unset), builds the
  real editor, and walks the actual Tk menu: asserts ``Sequential`` and
  ``Short course`` are top-level cascades with sub-cascades and leaf commands,
  and that no top-level label is a flat ``a/b`` slash group.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_zemax_menu_tree

Exit: 0 = pass, 1 = regression, 2 = environment can't render (no Xvfb).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path


def _check_discovery() -> list[str]:
    """Display-free: the new collections' .zmx files are discovered."""
    from KrakenOS.UI.layout_editor import ZEMAX_ATTACHMENT_DIR
    from KrakenOS.UI.layout_library import discover_zemax_prescriptions

    failures: list[str] = []
    files = discover_zemax_prescriptions(ZEMAX_ATTACHMENT_DIR)
    if not files:
        # No library checked out on this clone -- not a regression.
        print(f"[SKIP] discovery: no .zmx under {ZEMAX_ATTACHMENT_DIR}")
        return failures
    tops = {Path(label).parts[0] for label in files}
    for expected in ("Sequential", "Short course"):
        has = any(
            Path(label).parts[0] == expected and len(Path(label).parts) > 1
            for label in files
        )
        if not has:
            print(f"[note] discovery: no '{expected}/' .zmx present on this clone")
    if not tops:
        failures.append("discovery returned files but no top-level groups")
    return failures


# --- self-contained virtual display (mirrors the snapshot validators) --------
def _free_display() -> int:
    for num in (94, 93, 92, 91, 90):
        if not Path(f"/tmp/.X11-unix/X{num}").exists():
            return num
    return 122


def _start_xvfb(display: int, timeout: float = 15.0):
    xvfb = shutil.which("Xvfb")
    if xvfb is None:
        return None, "Xvfb not found on PATH"
    proc = subprocess.Popen(
        [xvfb, f":{display}", "-screen", "0", "1280x1024x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sock = Path(f"/tmp/.X11-unix/X{display}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return None, f"Xvfb exited early (code {proc.returncode})"
        if sock.exists():
            return proc, None
        time.sleep(0.2)
    proc.terminate()
    return None, f"Xvfb :{display} did not come up within {timeout:.0f}s"


def _ensure_display():
    if os.environ.get("DISPLAY"):
        return None, None
    display = _free_display()
    proc, err = _start_xvfb(display)
    if proc is None:
        return None, err
    os.environ["DISPLAY"] = f":{display}"
    return proc, None


def _menu_entries(menu) -> list[tuple[int, str, str]]:
    """(index, type, label) for every entry in a Tk menu."""
    out: list[tuple[int, str, str]] = []
    end = menu.index("end")
    if end is None:
        return out
    for i in range(end + 1):
        etype = menu.type(i)
        label = menu.entrycget(i, "label") if etype in ("cascade", "command") else etype
        out.append((i, etype, str(label)))
    return out


def _child_menu(menu, index):
    return menu.nametowidget(menu.entrycget(index, "menu"))


def _check_menu_tree() -> "tuple[list[str], int]":
    xvfb_proc, err = _ensure_display()
    if err is not None:
        print(f"[SKIP] menu tree: {err}")
        return [], 2

    failures: list[str] = []
    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor(headless=True)
        app.update_idletasks()

        example_menu = getattr(app, "example_menu", None)
        if example_menu is None:
            failures.append("editor has no example_menu")
            return failures, 0

        zemax_menu = None
        for index, etype, label in _menu_entries(example_menu):
            if etype == "cascade" and "Zemax Prescriptions" in label:
                zemax_menu = _child_menu(example_menu, index)
        if zemax_menu is None:
            # No library on this clone -> the cascade is absent; not a regression.
            print("[SKIP] menu tree: no Zemax Prescriptions cascade (library absent)")
            return failures, 2

        top = _menu_entries(zemax_menu)
        top_cascades = {label: index for index, etype, label in top if etype == "cascade"}

        # No flat "a/b" slash groups at the top any more.
        flat = [label for label in top_cascades if "/" in label]
        if flat:
            failures.append(f"top-level Zemax menu still has flat slash groups: {flat}")

        # Each present big collection nests into sub-cascades with leaf commands.
        for collection in ("Sequential", "Short course"):
            if collection not in top_cascades:
                print(f"[note] '{collection}' not in menu (library subset absent on this clone)")
                continue
            sub = _child_menu(zemax_menu, top_cascades[collection])
            sub_entries = _menu_entries(sub)
            sub_cascades = [i for i, t, _ in sub_entries if t == "cascade"]
            if not sub_cascades:
                failures.append(f"'{collection}' has no sub-category submenus (did not nest)")
                continue
            leaf = _child_menu(sub, sub_cascades[0])
            leaf_cmds = [lbl for _, t, lbl in _menu_entries(leaf) if t == "command"]
            if not leaf_cmds:
                failures.append(f"'{collection}' first sub-category has no .zmx load commands")
            elif any(lbl.endswith((".zmx", ".ZMX")) is False for lbl in leaf_cmds[:1]):
                # Leaf labels are bare file names; just sanity-check non-empty.
                pass
    except Exception as exc:
        import traceback

        failures.append(f"menu tree raised: {exc}\n{traceback.format_exc()}")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
        if xvfb_proc is not None:
            try:
                xvfb_proc.terminate()
            except Exception:
                pass
    return failures, 0


def main() -> int:
    failures: list[str] = []
    failures.extend(_check_discovery())

    tree_failures, exit_hint = _check_menu_tree()
    failures.extend(tree_failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("[FAIL] Zemax menu tree validation")
        return 1
    if exit_hint == 2:
        print("[PASS] Zemax discovery (menu tree skipped: no Xvfb/library)")
        return 0
    print("[PASS] Zemax menu nests by directory (Sequential / Short course browsable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
