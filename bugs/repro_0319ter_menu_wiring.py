"""Repro 0319-ter: does the LED right-click "Add Beam Splitter to LED -> Cube" CASCADE
actually carry a working command?

The 07:47 debug log proves add_beam_splitter_to_led was NEVER called when the user clicked
the cascade item (no status, no BS row, no "failed" append_debug line) -- yet direct menu
commands (Hide overlay) fired, and the command works when called directly. So the break is
the Tk menu wiring for the cascade. This builds the real LED context menu via
append_element_context_actions(), inspects the cascade + its submenu, and programmatically
invokes the "Cube" entry to see whether the command reaches add_beam_splitter_to_led.
"""
from __future__ import annotations

import sys
import tkinter as tk
import traceback
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def main() -> int:
    app = KrakenLayoutEditor()
    status: list[str] = []
    dbg: list[str] = []
    app.append_debug = lambda m, *a, **k: dbg.append(str(m))
    orig = app.status_var.set
    app.status_var.set = lambda s: (status.append(str(s)), orig(s))[1]
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.open_3d_view()
        insp = app._three_d_inspector
        insp.refresh_from_editor(
            sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True
        )
        insp.update_idletasks()
        insp.update()

        svc = insp._face_assignment_service()
        menu = tk.Menu(insp, tearoff=False)
        svc.append_element_context_actions(menu, step_label="led")

        end = menu.index("end")
        print(f"=== LED menu built: {None if end is None else end + 1} entries ===")
        bs_idx = None
        for i in range(0, (end or -1) + 1):
            typ = menu.type(i)
            try:
                label = menu.entrycget(i, "label")
            except Exception:
                label = f"<{typ}>"
            print(f"  [{i}] type={typ} label={label!r}")
            if typ == "cascade" and "Beam Splitter" in str(label):
                bs_idx = i

        if bs_idx is None:
            print("!!! No 'Add Beam Splitter to LED' cascade was added to the LED menu.")
            return 0

        subname = menu.entrycget(bs_idx, "menu")
        print(f"=== BS cascade at index {bs_idx}; submenu tk name={subname!r} ===")
        try:
            sub = insp.nametowidget(subname) if subname else None
        except Exception:
            print("  !!! nametowidget FAILED for the submenu:")
            traceback.print_exc()
            sub = None
        print("  submenu widget:", sub)
        if sub is None:
            print("!!! Submenu not resolvable -> cascade is dead.")
            return 0

        send = sub.index("end")
        for j in range(0, (send or -1) + 1):
            try:
                slabel = sub.entrycget(j, "label")
                scmd = sub.entrycget(j, "command")
            except Exception:
                slabel, scmd = "<?>", "<?>"
            print(f"    sub[{j}] label={slabel!r} command={scmd!r}")

        rows_before = len(app.rows)
        print(f"=== invoking submenu 'Cube' (sub[0]); rows before={rows_before} ===")
        try:
            sub.invoke(0)
        except Exception:
            print("  !!! sub.invoke(0) raised:")
            traceback.print_exc()
        insp.update_idletasks()
        insp.update()
        print(f"  rows after={len(app.rows)}")
        for i, r in enumerate(app.rows):
            print(f"    S{i}: {getattr(r, 'name', '?')}")
    except Exception:
        print("!!! TOP-LEVEL EXCEPTION")
        traceback.print_exc()
    finally:
        print("=== status lines ===")
        for s in status:
            print("  [status]", s)
        print("=== BS-related append_debug ===")
        for m in dbg:
            if any(k in m for k in ("Beam", "Promoted OPTICAL", "failed", "Splitter")):
                print("  [dbg]", m)
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
