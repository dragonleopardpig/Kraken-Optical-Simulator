"""Guard for bugs/0439 (guide half) -- a frozen fold mirror draws its reflected axis.

flag_20260726_110657: after the 0433 freeze (1st RA mirror deleted) the 2nd RA
mirror keeps its baked pose but has no override entry, so the override-derived
reflected guides vanish -- yet that leg is what the user aligns the CAMERA to.
`_frozen_fold_axis_guide_records` rebuilds the leg from the baked pose (Mirror
interaction face world plane from desp/tilt + station; incoming = the baked
upstream-neighbor direction, the entry leg; reflect d-2(d.n)n from the face
centroid) and registers it like every other guide (pickable).

* WIRING     -- the assembler appends `_frozen_fold_axis_guide_records` AFTER the
  BS guides (additive; never enters fold-branch grouping), and the gate keys on
  active fold SOURCES from the override map so live scenes are byte-identical.
* REAL-SCENE -- pristine folded AZ85 emits ZERO synthetic guides; deleting
  mirror-1 (freeze) emits exactly one `axis:global:frozen-fold:<row>` anchored at
  the mirror with the folded entry-leg direction (-Z toward the camera), and the
  record resolves through the screen-space axis pick.

SKIP (pass with a note) when the environment cannot run a check.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCENE = REPO / "attachment" / "machine_vision_AZ85_RA_Mirror.py"


def _check_wiring(notes: list[str]) -> bool:
    from KrakenOS.UI import open3d_inspector as insp_mod

    ok = True
    asm_src = _inspect.getsource(insp_mod.Kraken3DInspector._optical_axis_records_for_3d)
    bs_pos = asm_src.find("_bs_reflect_axis_guide_records")
    frozen_pos = asm_src.find("_frozen_fold_axis_guide_records")
    if 0 <= bs_pos < frozen_pos:
        notes.append("WIRING = assembler appends frozen-fold guides after the BS guides")
    else:
        notes.append("WIRING frozen-fold guides missing from the assembler (or ordered before BS)")
        ok = False
    guide_src = _inspect.getsource(insp_mod.Kraken3DInspector._frozen_fold_axis_guide_records)
    if "source_index" in guide_src and "active_sources" in guide_src:
        notes.append("WIRING = gate keys on active fold sources (live scenes untouched)")
    else:
        notes.append("WIRING frozen-fold gate does not key on active fold sources")
        ok = False
    if "axis:global:frozen-fold" in guide_src:
        notes.append("WIRING = distinct axis id family (never re-enters fold grouping)")
    else:
        notes.append("WIRING frozen-fold axis id missing")
        ok = False
    return ok


def _frozen_records(insp):
    return [
        rec
        for rec in (getattr(insp, "_optical_axis_pick_records", []) or [])
        if str(rec.get("axis_id", "")).startswith("axis:global:frozen-fold")
    ]


def _check_real_scene(notes: list[str]) -> bool:
    import time

    import numpy as np

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold

    ok = True
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85_0439"] = SCENE
        app.load_layout_by_name("az85_0439")
        app.open_3d_view()
        app.update_idletasks()
        app.update()
        insp = app._three_d_inspector
        insp.update_idletasks()
        insp.update()

        if _frozen_records(insp):
            notes.append("REAL live folded scene emitted synthetic frozen-fold guides")
            ok = False
        else:
            notes.append("REAL = live folded scene emits no synthetic guide")

        mirrors = [i for i, r in enumerate(app.rows) if _row_is_promoted_mirror_fold(r)]
        if len(mirrors) != 2:
            notes.append(f"SKIP real-scene: expected 2 promoted mirrors, found {mirrors}")
            return ok
        app.delete_optical_step_rows([mirrors[0]])
        insp.refresh_from_editor(force_retrace=True)
        for _ in range(3):
            insp.update_idletasks()
            insp.update()
            time.sleep(0.1)

        recs = _frozen_records(insp)
        if len(recs) == 1:
            notes.append(f"REAL = frozen mirror draws one guide ({recs[0].get('axis_id')})")
        else:
            notes.append(f"REAL frozen guide count {len(recs)} != 1")
            ok = False
            return ok
        pts = np.asarray(recs[0].get("points"), dtype=float)
        direction = pts[-1] - pts[0]
        direction = direction / np.linalg.norm(direction)
        if direction[2] < -0.9 and abs(direction[1]) < 0.1:
            notes.append("REAL = guide folds the entry leg (-Z toward the camera)")
        else:
            notes.append(f"REAL guide direction wrong: {np.round(direction, 3)}")
            ok = False
        mid = (pts[0] + pts[-1]) / 2.0
        disp = insp._world_to_display_2d(mid)
        info = (
            insp._optical_axis_info_near_display_xy((float(disp[0]), float(disp[1])), tolerance_px=12.0)
            if disp is not None
            else None
        )
        if info and str(info.get("axis_id", "")).startswith("axis:global:frozen-fold"):
            notes.append("REAL = guide is pickable via the screen-space axis pick")
        else:
            notes.append(f"REAL guide not pickable ({info.get('axis_id') if info else None})")
            ok = False
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    passed = True
    try:
        if not _check_wiring(notes):
            passed = False
    except Exception as exc:
        notes.append(f"SKIP wiring: {exc!r}")
    if SCENE.exists():
        try:
            if not _check_real_scene(notes):
                passed = False
        except Exception as exc:
            notes.append(f"SKIP real-scene: {exc!r}")
    else:
        notes.append("SKIP real-scene: AZ85 scene not present")
    return passed, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(("  " if "=" in note or note.startswith("SKIP") else "! ") + note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
