"""bugs/0630: screenshot the object-FOV popup with the new target-mode checkboxes."""
from __future__ import annotations
import subprocess
from pathlib import Path

SCENE = Path("attachment/machine_vision_Apo75.py")
OUT = Path("bugs/_0630_fov_target_modes_dialog.png")


def main() -> int:
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)

        def shot():
            try:
                dialog = [w for w in insp.winfo_children()
                          if w.winfo_class() == "Toplevel" and "Field of View" in (w.title() or "")][-1]
                dialog.update_idletasks()
                x, y = dialog.winfo_rootx(), dialog.winfo_rooty()
                w, h = dialog.winfo_width(), dialog.winfo_height()
                OUT.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["import", "-window", "root", "-crop",
                                f"{w}x{h}+{x}+{y}", "+repage", str(OUT)], check=True)
                print(f"saved {OUT} ({w}x{h})")
            except Exception as exc:
                print("shot error:", type(exc).__name__, exc)
            finally:
                try:
                    dialog.destroy()
                except Exception:
                    pass

        insp.after(400, shot)
        insp._open_quick_estimation_fov_popup("object")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
