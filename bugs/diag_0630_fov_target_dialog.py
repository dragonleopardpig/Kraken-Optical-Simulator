"""bugs/0630 integration: the FOV popup's magnification/resolution modes drive the solve.

Loads the Apo75 scene (hr25MCX camera), opens the object-plane FOV popup, and -- via a
scheduled callback (the popup is modal: grab_set + wait_window) -- ticks "Set
Magnification", types a target, and clicks "Solve for Thickness". The real solve is
stubbed to RECORD its arguments, so this proves the DIALOG WIRING (mode supersedes the
Width/Height boxes and feeds the converted object field) fast, without the minutes-long
conjugate solve (which bugs/0626 already verifies end to end).

Run:  taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u bugs/diag_0630_fov_target_dialog.py
"""

from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_Apo75.py")


def main() -> int:
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    captured: dict = {}
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)

        # Stub the real solve so we only test the dialog wiring (fast).
        def _record_solve(plane, mode, width, height, aspect=None, segment=None, image_segment=None):
            captured.update(plane=plane, mode=mode, width=width, height=height)
        insp._apply_quick_estimation_fov_solve = _record_solve

        target_mag = 0.5
        want_w = 23.04 / target_mag  # sensor / m

        def _walk(widget):
            out = [widget]
            for child in widget.winfo_children():
                out.extend(_walk(child))
            return out

        def drive():
            try:
                tops = [w for w in insp.winfo_children()
                        if w.winfo_class() == "Toplevel" and "Field of View" in (w.title() or "")]
                dialog = tops[-1]
                widgets = _walk(dialog)
                def find(cls, text_sub):
                    for w in widgets:
                        if w.winfo_class() == cls:
                            try:
                                if text_sub in str(w.cget("text")):
                                    return w
                            except Exception:
                                pass
                    return None
                mag_cb = find("TCheckbutton", "Magnification")
                mag_cb.invoke()  # tick + sync (grays Width/Height)
                # set the magnification entry's variable
                var_name = mag_cb.cget("variable")  # use_mag_var (bool) -> already ticked
                # find the entry next to the checkbutton (its textvariable is mag_var)
                entries = [w for w in widgets if w.winfo_class() == "TEntry"]
                # the magnification entry is the first ENABLED entry after ticking
                mag_entry = None
                for e in entries:
                    if str(e.cget("state")) == "normal":
                        mag_entry = e
                        break
                mag_entry.tk.call(mag_entry.cget("textvariable")) if False else None
                insp.setvar(mag_entry.cget("textvariable"), str(target_mag))
                btn = find("TButton", "Solve for Thickness")
                btn.invoke()  # run("thickness") -> _record_solve, then dialog.destroy()
            except Exception as exc:
                captured["error"] = f"{type(exc).__name__}: {exc}"
                try:
                    dialog.destroy()
                except Exception:
                    pass

        insp.after(300, drive)
        insp._open_quick_estimation_fov_popup("object")  # blocks until drive() closes it

        print("captured:", captured)
        ok = True
        if captured.get("error"):
            print("FAIL: dialog drive error:", captured["error"]); ok = False
        elif captured.get("mode") != "thickness":
            print(f"FAIL: solve mode {captured.get('mode')!r} != 'thickness'"); ok = False
        elif captured.get("width") is None or abs(float(captured["width"]) - want_w) > 1e-3:
            print(f"FAIL: solved width {captured.get('width')} != sensor/m {want_w:.3f} "
                  "-- the magnification mode did not supersede the FOV box"); ok = False
        else:
            print(f"PASS: ticking Magnification={target_mag} solved for object width "
                  f"{captured['width']:.3f} mm (sensor/m), mode=thickness")
        return 0 if ok else 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
