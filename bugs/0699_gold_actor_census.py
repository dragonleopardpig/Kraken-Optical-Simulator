"""Identify the vertical golden line: walk ALL renderer actors, find slender
vertical yellow/gold ones, and cross-reference the inspector's actor registries."""
from pathlib import Path
import numpy as np

def main():
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

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

    # build reverse registries: actor address -> (registry name, key)
    owners = {}
    for attr in dir(insp):
        if not attr.startswith("_"):
            continue
        try:
            val = getattr(insp, attr)
        except Exception:
            continue
        if isinstance(val, dict):
            for k, v in list(val.items())[:400]:
                for cand in ([v] if not isinstance(v, (list, tuple)) else list(v)[:10]):
                    try:
                        addr = cand.GetAddressAsString("vtkActor")
                    except Exception:
                        continue
                    owners.setdefault(addr, (attr, str(k)[:40]))
        elif isinstance(val, list):
            for j, v in enumerate(val[:400]):
                try:
                    addr = v.GetAddressAsString("vtkActor")
                except Exception:
                    continue
                owners.setdefault(addr, (attr, f"[{j}]"))

    props = insp._renderer.GetViewProps()
    props.InitTraversal()
    found = 0
    while True:
        p = props.GetNextProp()
        if p is None:
            break
        try:
            if not p.GetVisibility():
                continue
            b = p.GetBounds()
            if b is None:
                continue
            dx, dy, dz = b[1]-b[0], b[3]-b[2], b[5]-b[4]
            if not (dy > 15 and dx < 3 and dz < 3):
                continue
            col = p.GetProperty().GetColor() if hasattr(p, "GetProperty") else (0,0,0)
            r, g, bl = col
            if not (r > 0.7 and g > 0.4 and bl < 0.5):
                continue
            addr = p.GetAddressAsString("vtkActor")
            who = owners.get(addr, ("?", "?"))
            print(f"GOLD VLINE: bounds x[{b[0]:.1f},{b[1]:.1f}] y[{b[2]:.1f},{b[3]:.1f}] "
                  f"z[{b[4]:.1f},{b[5]:.1f}] col=({r:.2f},{g:.2f},{bl:.2f}) "
                  f"owner={who[0]}:{who[1]}")
            found += 1
        except Exception:
            continue
    if not found:
        print("no slender vertical golden actors found")
    editor.destroy()

if __name__ == "__main__":
    main()
