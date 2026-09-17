"""bugs/0535 repro -- live report: after "Add Illumination Source (LED)" from the browser
panel, selecting the source froze the app in an endless ~3.4 s refresh loop.

py-spy on the live process caught the driver:
    _on_tree_select (open3d_step_admin) -> select_scene_source_from_admin
      -> refresh_from_editor -> tree rebuild -> deferred <<TreeviewSelect>> (0049)
      -> select_scene_source_from_admin -> ...

`select_scene_source_from_admin` refreshed unconditionally; the deferred programmatic
re-selection of the SAME source re-armed it forever. Fix: re-selecting the current
source with its gizmo already raised is a no-op.

This repro counts refresh_from_editor calls across repeated re-selection (the deferred
re-fire pattern) and across a pumped event loop. Pre-fix: one refresh per re-selection,
unbounded. Post-fix: exactly one for the first selection.
"""
from __future__ import annotations

import time
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        app._three_d_inspector = insp

        sid = app.add_illumination_led_source().split(":", 1)[1]
        print(f"source added: {sid}")
        _settle(insp)

        counts = [0]
        real_refresh = insp.refresh_from_editor

        def counted_refresh(*a, **k):
            counts[0] += 1
            return real_refresh(*a, **k)

        insp.refresh_from_editor = counted_refresh

        # The deferred-re-fire pattern: the first call is the user's click; the
        # repeats are the tree rebuild's programmatic re-selection events.
        for _ in range(4):
            insp.select_scene_source_from_admin(sid)
            insp.update()
        print(f"refreshes across 4 re-selections: {counts[0]} (want 1)")
        first_ok = counts[0] == 1

        # And the free-running check: pump the loop; no further refreshes may arrive.
        counts[0] = 0
        deadline = time.time() + 10.0
        while time.time() < deadline:
            insp.update()
            time.sleep(0.02)
        print(f"refreshes in 10 s idle pump: {counts[0]} (want 0)")
        print("FIXED" if (first_ok and counts[0] == 0) else "LOOP STILL PRESENT")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
