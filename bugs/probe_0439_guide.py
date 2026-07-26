#!/usr/bin/env python3
"""bugs/0439 (guide half) — a FROZEN fold mirror draws its reflected axis guide.

flag_20260726_110657: after deleting the 1st RA mirror (0433 freeze) the 2nd RA
mirror keeps its baked pose but the override map carries no fold for it, so no
reflected guide is drawn — yet that leg is exactly what the user aligns the CAMERA
to. `_frozen_fold_axis_guide_records` rebuilds the leg from the baked pose:
Mirror-face world plane from desp/tilt + station, incoming = the baked upstream
neighbor direction (the entry leg), reflect d−2(d·n)n from the face centroid.

Checks:
  1. Pristine folded AZ85 (both mirrors are ACTIVE fold sources) -> ZERO synthetic
     records; the live guides are untouched (byte-identical live scenes).
  2. Delete mirror-1 (0433 freeze) -> exactly one `axis:global:frozen-fold:<row>`
     record; it starts at mirror-2's face centroid (== the mirror, not a displaced
     axis crossing), its direction is the fold of the entry leg (+X in, -Z out
     toward the camera), and the incoming it used matches the frozen chain line.
  3. The record is PICKABLE: `_optical_axis_info_near_display_xy` resolves it at
     its screen midpoint (the user's next click target for the camera snap).

Run:  DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0439_guide.py
(Needs an X display; start `Xvfb :N -screen 0 1600x1000x24` when headless.)
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
SCENE = REPO / "attachment" / "machine_vision_AZ85_RA_Mirror.py"


def _drain(widget, cycles: int = 3, sleep_s: float = 0.15) -> None:
    for _ in range(cycles):
        widget.update_idletasks()
        widget.update()
        time.sleep(sleep_s)


def _frozen_fold_records(insp) -> list[dict]:
    return [
        rec
        for rec in (getattr(insp, "_optical_axis_pick_records", []) or [])
        if str(rec.get("axis_id", "")).startswith("axis:global:frozen-fold")
    ]


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(("ok  " if ok else "XX  ") + name + ("  " + detail if detail else ""))
        if not ok:
            failures.append(name)

    if not SCENE.exists():
        print("SKIP: scene missing:", SCENE)
        return 0

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.open_3d_view()
        app.update_idletasks()
        app.update()
        insp = app._three_d_inspector
        insp.geometry("1280x860+80+60")
        insp.deiconify()
        insp.lift()
        _drain(insp)

        # 1: live folded scene -> no synthetic guides (both mirrors actively fold).
        live = _frozen_fold_records(insp)
        check("live folded scene emits NO synthetic frozen-fold guide", not live, str([r.get("axis_id") for r in live]))

        # find the promoted mirror rows (mirror-1 = first, mirror-2 = free-placed)
        from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold

        mirrors = [i for i, r in enumerate(app.rows) if _row_is_promoted_mirror_fold(r)]
        check("two promoted fold mirrors in the pristine scene", len(mirrors) == 2, str(mirrors))
        mirror1 = mirrors[0]

        # capture mirror-2's world center BEFORE the delete (freeze must keep it)
        z = app._row_z_positions()
        m2 = mirrors[1]
        m2_center_before = np.asarray(
            (float(app.rows[m2].desp_x), float(app.rows[m2].desp_y), float(z[m2]) + float(app.rows[m2].desp_z))
        )

        # 2: delete mirror-1 -> 0433 freeze -> synthetic guide for frozen mirror-2.
        app.delete_optical_step_rows([mirror1])
        insp.refresh_from_editor(force_retrace=True)
        _drain(insp)

        recs = _frozen_fold_records(insp)
        check("frozen mirror-2 draws exactly one synthetic fold guide", len(recs) == 1, str([r.get("axis_id") for r in recs]))
        if recs:
            rec = recs[0]
            pts = np.asarray(rec.get("points"), dtype=float)
            start, far = pts[0], pts[-1]
            # start anchors ON the mirror (face centroid is within the prism's extent
            # of the row center; the 87931 RA prism is ~51.5 mm)
            m2_now = next(i for i, r in enumerate(app.rows) if _row_is_promoted_mirror_fold(r))
            z2 = app._row_z_positions()
            m2_center = np.asarray(
                (
                    float(app.rows[m2_now].desp_x),
                    float(app.rows[m2_now].desp_y),
                    float(z2[m2_now]) + float(app.rows[m2_now].desp_z),
                )
            )
            check(
                "freeze kept mirror-2's world center",
                bool(np.linalg.norm(m2_center - m2_center_before) < 1e-3),
                f"{m2_center} vs {m2_center_before}",
            )
            check(
                "guide starts at the mirror (face centroid near the row center)",
                bool(np.linalg.norm(start - m2_center) < 60.0),
                f"start={np.round(start,1)} center={np.round(m2_center,1)}",
            )
            direction = far - start
            direction = direction / np.linalg.norm(direction)
            # entry leg is +X (the frozen chain), the fold sends the beam -Z (camera side)
            check(
                "guide direction folds the entry leg (-Z toward the camera)",
                bool(direction[2] < -0.9 and abs(direction[1]) < 0.1),
                f"dir={np.round(direction,3)}",
            )

            # 3: pickable at its screen midpoint (the user's snap-target click)
            mid_world = (np.asarray(start) + np.asarray(far)) / 2.0
            disp = insp._world_to_display_2d(mid_world)
            check("guide midpoint projects to display", disp is not None, str(disp))
            if disp is not None:
                info = insp._optical_axis_info_near_display_xy((float(disp[0]), float(disp[1])), tolerance_px=12.0)
                check(
                    "guide is pickable via the screen-space axis pick",
                    bool(info) and str(info.get("axis_id", "")).startswith("axis:global:frozen-fold"),
                    str(info.get("axis_id") if info else None),
                )
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)}): " + "; ".join(failures))
        return 1
    print("RESULT: PASS — frozen fold mirror draws its pickable reflected-axis guide")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
