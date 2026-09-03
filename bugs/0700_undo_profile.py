"""Profile: rotate the om05a station (0693 command) with the 3D view open, then
Ctrl-Z undo it. Wall-time both, and mine the open3d timing log for the undo's
span breakdown."""
import json
import time
from pathlib import Path


def main():
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.open3d_timing import open3d_timing_log_path

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    editor._build_preview_system_rays_bundle(trace_rays=True)
    editor.open_3d_view()
    editor.update_idletasks(); editor.update()
    insp = editor._three_d_inspector
    insp.refresh_from_editor(sampling_mode=editor._preview_3d_sampling_mode(), force_retrace=True)
    _settle(editor, 1.0)

    rows = editor.rows
    m1 = next(i for i, r in enumerate(rows) if str(getattr(r, "name", "")) == "RA mirror 1 (50 mm)")

    t0 = time.perf_counter()
    editor.rotate_scene_row_pose_world_axis(m1, "y", 90.0)
    editor.update_idletasks(); editor.update()
    t1 = time.perf_counter()
    print(f"ROTATE wall: {t1 - t0:.2f}s  undo_depth={len(editor._undo_stack)}")

    mark = time.time()
    t2 = time.perf_counter()
    editor.undo()
    editor.update_idletasks(); editor.update()
    t3 = time.perf_counter()
    print(f"UNDO wall: {t3 - t2:.2f}s")

    # mine the timing log for spans that ended after the undo started
    log = open3d_timing_log_path()
    if log.exists():
        spans = []
        for line in log.read_text().splitlines():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if float(rec.get("ts", 0.0) or 0.0) < mark - 0.5:
                continue
            dur = rec.get("duration_s")
            if dur is None:
                continue
            spans.append((float(dur), rec.get("event", "?"), {k: v for k, v in rec.items() if k in ("action", "reason", "label", "display_only_open3d_step", "force_retrace", "count")}))
        spans.sort(reverse=True)
        print("--- top undo-window spans ---")
        for dur, event, extra in spans[:20]:
            print(f"{dur:8.3f}s  {event}  {extra}")
    editor.destroy()


if __name__ == "__main__":
    main()
