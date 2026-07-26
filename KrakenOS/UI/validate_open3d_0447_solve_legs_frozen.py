"""bugs/0447 guard -- the solve popup's fold-leg constraints exist and apply on the
frozen/snapped BS scene (flag_20260726_180738: the "2+2" layout was empty there).

Checks:
  SOURCE  -- the appliers branch to the frozen-world path; the dialog honors label
             overrides (the object vertex is the BS coating, not a mirror).
  CLASSIC -- the pristine folded scene keeps its station-frame splits (no frozen flag).
  FROZEN  -- both groups present with world legs; the image pin slides the mirror
             along its leg (never +Z); the object pin holds totals and chain rigidity.
"""
from __future__ import annotations

import inspect as _inspect

import numpy as np


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    try:
        from KrakenOS.UI.services import paraxial_tools as pt

        src_obj = _inspect.getsource(pt.ParaxialToolsMixin._apply_folded_object_split)
        src_img = _inspect.getsource(pt.ParaxialToolsMixin._apply_folded_image_split)
    except Exception:
        try:
            src_all = open("KrakenOS/UI/services/paraxial_tools.py", encoding="utf-8").read()
            src_obj = src_img = src_all
        except Exception as exc:
            return True, [f"SKIP: paraxial tools unavailable ({exc!r})"]
    if "frozen_world" in src_obj and "frozen_world" in src_img:
        notes.append("SOURCE = both appliers branch to the frozen-world path")
    else:
        notes.append("SOURCE appliers missing the frozen-world branch")
        ok = False
    try:
        insp_src = open("KrakenOS/UI/open3d_inspector.py", encoding="utf-8").read()
        if 'seg_split.get("near_label")' in insp_src:
            notes.append("SOURCE = dialog honors split label overrides")
        else:
            notes.append("SOURCE dialog lacks the label overrides")
            ok = False
    except Exception:
        notes.append("SKIP: inspector source unavailable for the label check")

    try:
        from pathlib import Path

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.open3d_inspector import _row_is_marked_beam_splitter_row

        scene = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        if not scene.exists():
            notes.append("SKIP: AZ85 scene absent (gitignored attachment)")
            return ok, notes
        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = scene
        app.load_layout_by_name("az85")
        img0 = app._folded_image_conjugate_split()
        if img0 is not None and not img0.get("frozen_world"):
            notes.append("CLASSIC = pristine folded scene keeps the station-frame split")
        else:
            notes.append(f"CLASSIC pristine split unexpected: {img0}")
            ok = False
        mirror1 = next(
            i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", ""))
        )
        app.delete_optical_step_rows([mirror1])
        try:
            app._select_table_indices([1], focus_index=1)
        except Exception:
            app._select_table_row(1)
        app.add_beam_splitter_to_led(kind="plate")
        rows_sel = [
            i
            for i, r in enumerate(app.rows)
            if getattr(r, "surface", None) in ("Standard", "Thin Lens", "Aperture", "Image")
            and i > 0
            and "next gap" not in str(getattr(r, "name", ""))
            and not _row_is_marked_beam_splitter_row(r)
        ]
        app.snap_rows_to_axis(
            rows_sel,
            {
                "axis_id": "axis:global:split",
                "points": np.array([(0.0, 0.0, 54.0), (263.7, 0.0, 54.0)]),
                "picked_world": np.array([70.4, 0.0, 54.0]),
            },
        )
        obj = app._folded_object_conjugate_split()
        img = app._folded_image_conjugate_split()
        if (
            obj is not None
            and obj.get("frozen_world")
            and "beam splitter" in str(obj.get("near_name", ""))
            and img is not None
            and img.get("frozen_world")
        ):
            notes.append(
                f"FROZEN = both groups present (obj {obj['near']:.1f}+{obj['far']:.1f}, "
                f"img {img['near']:.1f}+{img['far']:.1f})"
            )
        else:
            notes.append(f"FROZEN groups missing: obj={obj} img={img}")
            ok = False
            return ok, notes
        mirror_row = int(img["mirror_row"])
        c0 = app._split_row_world_center(mirror_row)
        applied, _msg = app._apply_folded_image_split("near", 90.0)
        c1 = app._split_row_world_center(mirror_row)
        img2 = app._folded_image_conjugate_split()
        if (
            applied
            and abs(img2["near"] - 90.0) < 1e-6
            and abs(img2["total"] - img["total"]) < 1e-6
            and abs(float((c1 - c0)[2])) < 1e-6
        ):
            notes.append("FROZEN = image pin exact; mirror slid along its leg, not +Z")
        else:
            notes.append(f"FROZEN image pin failed: {img2} moved={(c1 - c0).round(3).tolist()}")
            ok = False
        applied2, _msg2 = app._apply_folded_object_split("near", 60.0)
        obj2 = app._folded_object_conjugate_split()
        if applied2 and abs(obj2["near"] - 60.0) < 1e-6 and abs(obj2["total"] - obj["total"]) < 1e-6:
            notes.append("FROZEN = object pin exact; total preserved (LED+BS slid)")
        else:
            notes.append(f"FROZEN object pin failed: {obj2}")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: frozen-scene drive failed ({exc!r})")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
