"""Probe (bugs/0348): does a REAL click on a right-click menu entry deliver its command?

flag_20260717_204504_767 ("still unable to right click and snap the CA to optical axis")
on an LED-only scene: the opening menu posts with the snap entry, direct handler calls
and ``menu.invoke()`` both snap fine -- yet in the live app clicking the entry does
NOTHING and ``right_click_diagnostics`` stays empty.

Tk delivers a clicked entry's command AFTER unposting the menu (Tk menu.tcl,
``tk::MenuInvoke``: ``MenuUnpost $menu`` first, then ``$menu invoke $active``).
``_popup_context_menu`` binds the menu's ``<Unmap>`` to the bugs/0336 dismiss, whose
``menu.destroy()`` therefore lands BETWEEN the unpost and the invoke -- the command is
dropped with the widget. This probe replays that exact internal order on the real
posted menu:

    tk::MenuUnpost <menu>     # fires <Unmap> -> our dismiss handler
    menu.invoke(<snap index>) # what MenuInvoke does next

and reports whether the snap actually ran (opening moved / status changed).

Run under Xvfb:
    DISPLAY=:99 .devenv/state/venv/bin/python bugs/probe_0348_menu_entry_click_delivery.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np
import tkinter as tk

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

LED_STEP = Path("attachment/LED/OPT-CO90-X-V1.6.2-H.STEP").resolve()


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        edge = app._default_led_object_edge_distance()
        app.imported_led_step_path = LED_STEP
        app.led_step_rotation_x_deg = 0.0
        app.led_step_rotation_y_deg = 0.0
        app.led_step_rotation_z_deg = 0.0
        app.led_step_object_edge_local_z = None
        app.led_step_axis_offset_xy = (0.0, 0.0)
        app.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        app._clear_step_overlay_axis_anchor("led")
        app._selected_step_label = "led"
        app.led_object_edge_distance_mm = float(max(edge, 0.0))
        app._live_step_overlay_trace_plan_cache = {}
        app._invalidate_preview_scene_trace()
        app.open_3d_view()
        app.update_idletasks(); app.update()
        insp = app._three_d_inspector
        insp.update_idletasks(); insp.update()
        svc = insp._face_assignment_service()

        c0, n0 = svc._clear_aperture_opening_center_normal("led")
        off0 = float(np.linalg.norm(np.asarray(c0, float)[:2]))
        print(f"[before] CA XY-off={off0:.3f}")

        # Post the OPENING menu for real: pin the opening, then right-click through
        # the real dispatcher (tk_popup runs under Xvfb; grab_release in finally).
        insp._selected_opening_label = "led"
        insp._selected_opening_center = np.asarray(c0, dtype=float)
        insp._selected_opening_normal = np.asarray(n0, dtype=float)
        insp._selected_opening_face_id = "F164"

        class Ev:
            x = 900; y = 500; x_root = 900; y_root = 500
            widget = insp._vtk_widget; state = 0

        posted = svc._show_selected_opening_context_menu(Ev())
        insp.update_idletasks(); insp.update()
        menu = getattr(insp, "_active_context_menu", None)
        print(f"[post] opening menu posted={posted} active_menu={'yes' if menu is not None else 'None'}")
        if menu is None:
            print("[post] no active menu -> cannot exercise the click path")
            return 1
        snap_index = None
        end = menu.index("end")
        for i in range(end + 1):
            if menu.type(i) == "command" and "Snap Clear Aperture" in str(menu.entrycget(i, "label")):
                snap_index = i
                break
        print(f"[post] snap entry index={snap_index}")
        if snap_index is None:
            return 1

        # The Tk-internal entry-click order: unpost (fires <Unmap>) THEN invoke --
        # run back-to-back with NO event-loop pump in between, exactly like
        # tk::MenuInvoke does inside one ButtonRelease callback.
        delivered = None
        try:
            menu.tk.call("tk::MenuUnpost", menu._w)
        except tk.TclError as exc:
            print(f"[click] tk::MenuUnpost raised: {exc}")
        try:
            menu.invoke(snap_index)
            delivered = True
        except tk.TclError as exc:
            delivered = False
            print(f"[click] invoke after unpost FAILED: {exc}")
        insp.update_idletasks(); insp.update()

        c1, _n1 = svc._clear_aperture_opening_center_normal("led")
        off1 = float(np.linalg.norm(np.asarray(c1, float)[:2]))
        moved = float(np.linalg.norm(np.asarray(c1, float)[:3] - np.asarray(c0, float)[:3]))
        print(f"[after] invoke_ok={delivered} moved={moved:.3f} CA XY-off={off1:.3f}")
        print(f"[after] status={insp.status_var.get()!r}")
        verdict = delivered and moved > 1.0
        print(f"[verdict] menu-entry click {'DELIVERS its command (good)' if verdict else 'is DROPPED (the bug)'}")
        return 0 if verdict else 2
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
