"""bugs/0441 live-path diagnostic: drive the REAL inspector (the recorder's own
actor registry) through the round-2 workflow and report the aperture ring's
thin-axis + actor markers at each stage, alongside its neighbours."""
from pathlib import Path

import numpy as np

import KrakenOS.UI.validate_open3d_penta_telescope_comprehensive as V


def dump(app, inspector, tag):
    print(f"--- {tag}")
    ap_keys = []
    for row_index, row in enumerate(app.rows):
        surf = str(getattr(row, "surface", ""))
        if surf not in ("Aperture", "Standard", "Thin Lens"):
            continue
        keys = (getattr(inspector, "_row_actor_map", {}) or {}).get(row_index) or []
        for key in keys:
            actor = (getattr(inspector, "_actor_by_key", {}) or {}).get(key)
            if actor is None:
                continue
            try:
                b = actor.GetBounds()
            except Exception:
                continue
            ext = (round(b[1] - b[0], 1), round(b[3] - b[2], 1), round(b[5] - b[4], 1))
            thin = int(np.argmin(ext))
            center = (
                round((b[0] + b[1]) / 2, 1),
                round((b[2] + b[3]) / 2, 1),
                round((b[4] + b[5]) / 2, 1),
            )
            marks = [a for a in dir(actor) if a.startswith("_kraken")]
            print(
                f"  row {row_index} {surf:9s} {str(getattr(row, 'name', ''))[:20]:22s} "
                f"ext={ext} thin={'XYZ'[thin]} c={center} marks={marks[:3]}"
            )
            if surf == "Aperture":
                ap_keys.append((key, actor))
    return ap_keys


def main() -> int:
    app = V.KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        app.load_layout_by_name("az85")
        inspector = V._open_inspector(app)
        dump(app, inspector, "PRISTINE (live fold)")
        # round-2 user order: DELETE FIRST (freeze on the live fold), THEN add the BS
        m1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([m1])
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks()
        dump(app, inspector, "POST-FREEZE (delete first)")
        app.add_beam_splitter_to_led(kind="plate")
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks()
        dump(app, inspector, "POST-BS-ADD (after freeze)")
        rows = [
            i
            for i, r in enumerate(app.rows)
            if getattr(r, "surface", None) in ("Standard", "Thin Lens", "Aperture", "Image")
            and i > 0
            and "next gap" not in str(getattr(r, "name", ""))
        ]
        rec = {
            "axis_id": "axis:global:split",
            "axis_label": "BS reflect",
            "points": np.array([(0.0, 0.0, 41.8), (193.3, 0.0, 41.8)]),
        }
        app.snap_rows_to_axis(rows, rec)
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks()
        dump(app, inspector, "POST-SNAP")
    finally:
        app.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
