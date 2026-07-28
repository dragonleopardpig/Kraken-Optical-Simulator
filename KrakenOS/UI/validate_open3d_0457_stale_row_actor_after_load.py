"""bugs/0457 guard -- a layout load must rebuild a live Open 3D viewer.

flag_20260728_084648 ("direct loaded the file"): reopening
``machine_vision_AZ85_RA_Mirror_BS.py`` still drew a sensor plane at z = -48.8, while the
prescription, the camera body and the reached-image branch detector all said +2.73. The
scene bundle emits NO curve for that row (its sequential Image is superseded by branch
detectors), so the actor was a leftover from the PREVIOUS scene, parked at its old
position -- the invariant broken is "no actor outlives the geometry that justified it".

The full rebuild path already clears every actor map; ``load_layout_by_name`` simply never
asked for one -- it refreshed the 2-D plot only.

WHY THIS CHECK IS SOURCE-LEVEL: the bug is invisible without a live viewer (headless never
creates the actor), and driving one across a load segfaults THIS environment -- the known
llvmpipe/mesa 0294-class use-after-free (``reference_vtk_render_backend_segfault``), not a
product fault: the user confirmed the same gesture does not crash the real app. So this
phase pins the wiring and the guards; the behaviour is confirmed in-app.
"""
from __future__ import annotations

import inspect as _inspect


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI.services import layout_table_workbench as _ltw

        src = _inspect.getsource(_ltw)
    except Exception as exc:
        return True, [f"SKIP: workbench unavailable ({exc!r})"]

    if "_rebuild_live_open3d_after_layout_load" not in src:
        return False, ["SOURCE the 0457 post-load viewer rebuild is missing"]
    notes.append("SOURCE = the load path has a post-load viewer rebuild")

    try:
        hook = _inspect.getsource(_ltw.LayoutTableWorkbenchMixin._rebuild_live_open3d_after_layout_load)
    except Exception:
        hook = ""
        for name, obj in vars(_ltw).items():
            if not isinstance(obj, type):
                continue
            fn = getattr(obj, "_rebuild_live_open3d_after_layout_load", None)
            if fn is not None:
                try:
                    hook = _inspect.getsource(fn)
                except Exception:
                    hook = ""
                break
    if "geometry_changed=True" in hook and "force_retrace=True" in hook:
        notes.append("SOURCE = it asks for a full geometry rebuild, not a ray-only refresh")
    else:
        notes.append("SOURCE the rebuild does not force geometry_changed/force_retrace")
        ok = False

    # The load may have torn the viewer down immediately above
    # (_reset_complete_layout_runtime_state(close_viewers=True)), so the hook must be
    # unable to resurrect a dead one -- that combination dumped core while this fix was
    # first attempted.
    if "winfo_exists" in hook and hook.count("except Exception") >= 2:
        notes.append("SOURCE = it is guarded against a torn-down viewer (no resurrection)")
    else:
        notes.append("SOURCE the rebuild is not guarded against a destroyed viewer")
        ok = False

    try:
        loader = _inspect.getsource(_ltw.LayoutTableWorkbenchMixin.load_layout_by_name)
    except Exception:
        loader = src
    if "_rebuild_live_open3d_after_layout_load()" in loader:
        notes.append("SOURCE = load_layout_by_name calls it after the refresh")
    else:
        notes.append("SOURCE load_layout_by_name never calls the rebuild")
        ok = False

    # bugs/0457 round 2: there are TWO load entry points. Fixing only the menu-driven
    # one left File -> Open ("direct open") still showing the previous scene's sensor
    # plane -- flag_20260728_091045, on a process started AFTER the first fix landed.
    try:
        from KrakenOS.UI.services import layout_import_export as _lie

        opener = _inspect.getsource(_lie)
    except Exception as exc:
        notes.append(f"SKIP: import/export module unavailable ({exc!r})")
        return ok, notes
    if "_rebuild_live_open3d_after_layout_load()" in opener:
        notes.append("SOURCE = File -> Open rebuilds the viewer too (both entry points)")
    else:
        notes.append("SOURCE File -> Open does not rebuild the viewer (0457 round-2 gap)")
        ok = False

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
