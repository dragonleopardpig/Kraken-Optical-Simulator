"""Drive the REAL Tk app through the user's Done-2D flow (bugs/0298).

  load scene -> open 3D -> right-click "Snap detector to image plane (remove defocus)" -> Done 2D

and report whether the main 2D actually re-plots. finish_stl_placement re-plots ONLY when
_stl_placement_dirty is set; the snap used to retrace the 3D without setting it, so "Done 2D"
silently skipped the re-plot and the 2D kept the OLD prescription.

Run: DISPLAY=:77 .devenv/state/venv/bin/python bugs/diag_done2d_refresh.py   (needs an X display)
"""
from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data

SCENE = Path(__file__).resolve().parent.parent / "attachment" / "machine_vision_AZ85_RA_Mirror.py"


def fingerprint(app) -> dict:
    ax = getattr(app, "ax", None)
    if ax is None:
        return {}
    return {
        "xlim": tuple(round(float(v), 3) for v in ax.get_xlim()),
        "rows": [round(float(r.thickness), 3) for r in app.rows],
    }


def main() -> int:
    info = _load_python_data(SCENE)
    app = KrakenLayoutEditor()
    app.rows = [KrakenLayoutEditor._row_from_layout_item(it) for it in info["surfaces"]]
    app._apply_layout_settings(dict(info.get("settings", {}) or {}))
    app._sync_table()
    app.refresh_plot()

    app.open_3d_view()
    app.update_idletasks()
    app.update()
    inspector = app._three_d_inspector
    if inspector is None or not inspector.available:
        print("!! inspector unavailable")
        return 1

    # Force a real defocus so the snap has something to do (what the saved file has).
    app.rows[8].thickness = 40.0
    inspector.refresh_from_editor(force_retrace=True)
    app.refresh_plot()
    before = fingerprint(app)
    inspector._stl_placement_dirty = False       # clean slate: only the snap may dirty it
    print(f"2D before the snap : {before}")

    # THE USER'S ACTION: right-click -> "Snap detector to image plane (remove defocus)"
    inspector._snap_detector_to_image_plane()
    print(f"rows after the snap: {[round(float(r.thickness), 3) for r in app.rows]}")
    print(f"2D marked stale    : {inspector._stl_placement_dirty}   <-- Done 2D re-plots only if True")

    # THE USER'S NEXT CLICK: "Done 2D"  (finish_stl_placement, minus the window teardown)
    replotted = False
    if inspector._stl_placement_dirty:
        app.refresh_plot(
            suppress_analysis=True,
            sampling_mode=inspector._active_refresh_sampling_mode(),
        )
        replotted = True
    after = fingerprint(app)
    print(f"2D after 'Done 2D' : {after}")
    print(f"\nre-plotted: {replotted}   2D CHANGED: {before != after}")
    return 0 if (replotted and before != after) else 1


if __name__ == "__main__":
    raise SystemExit(main())
