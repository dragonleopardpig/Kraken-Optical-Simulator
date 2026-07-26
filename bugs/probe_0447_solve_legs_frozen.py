"""bugs/0447 -- the FOV/thickness-solve popup's fold-leg constraints on the frozen scene.

flag_20260726_180738: on the round-5 frozen/snapped AZ85+BS scene the popup lost the
"2+2" leg constraints (reference attachment/FOV-solve.png). Root: the object-side fold
vertex is the BS COATING (a marked BS is never a mirror fold -> object split None) and
the image-side mirror is BREADCRUMBED (station-frame appliers would slide it along +Z
instead of its leg). Shipped: world-geometry splits + frozen appliers --

  object: near = object -> coating crossing, far = crossing -> lens front; the solve
          slides LED+BS along the object axis and rigidly repackages the frozen chain;
  image:  near = lens rear -> mirror, far = mirror -> sensor (world); the solve slides
          the breadcrumbed mirror along its incoming leg and re-seats sensor + camera.

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0447_solve_legs_frozen.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok " if ok else "XX "), label, (" " + detail if detail else ""))
    if not ok:
        FAILURES.append(label)


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.open3d_inspector import _row_is_marked_beam_splitter_row

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")

        # 0: the PRISTINE folded scene keeps the classic splits (no frozen flag).
        img0 = app._folded_image_conjugate_split()
        check(
            "pristine: classic image split intact, not frozen-world",
            img0 is not None and not img0.get("frozen_world"),
            str({k: round(v, 2) for k, v in img0.items() if isinstance(v, float)}) if img0 else "None",
        )

        # Build the user's frozen scene: delete mirror-1, add plate BS, snap the chain.
        mirror1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
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

        # 1: BOTH groups present, frozen-world, self-consistent.
        obj = app._folded_object_conjugate_split()
        img = app._folded_image_conjugate_split()
        check("frozen: object split present (BS coating vertex)", obj is not None and obj.get("frozen_world") is True)
        check("frozen: image split present (breadcrumbed mirror)", img is not None and img.get("frozen_world") is True)
        if obj is None or img is None:
            print(f"FAIL: {FAILURES}")
            return 1
        check(
            "frozen: object near+far == total, BS labels",
            abs(obj["near"] + obj["far"] - obj["total"]) < 1e-6
            and "beam splitter" in str(obj.get("near_name", "")),
            f"near={obj['near']:.2f} far={obj['far']:.2f}",
        )
        # World truth: image legs measured between actual world centres.
        c_r = app._split_row_world_center(int(img["near_gap_row"]))
        c_m = app._split_row_world_center(int(img["mirror_row"]))
        near_world = float(np.linalg.norm(c_m - c_r))
        check(
            "frozen: image near equals the world lens-rear->mirror distance",
            abs(near_world - float(img["near"])) < 1e-6,
            f"{img['near']:.3f} vs world {near_world:.3f}",
        )

        # 2: IMAGE solve -- pin near=90, mirror slides along its leg, totals fixed.
        mirror_row = int(img["mirror_row"])
        c_m0 = app._split_row_world_center(mirror_row)
        ok, msg = app._apply_folded_image_split("near", 90.0)
        img2 = app._folded_image_conjugate_split()
        c_m1 = app._split_row_world_center(mirror_row)
        moved = c_m1 - c_m0
        check("image solve applies", bool(ok), msg[:60])
        check(
            "image solve: near exact, total preserved",
            abs(img2["near"] - 90.0) < 1e-6 and abs(img2["total"] - img["total"]) < 1e-6,
            f"near={img2['near']:.3f} total={img2['total']:.3f}",
        )
        check(
            "image solve: mirror slid ALONG ITS LEG (x), not +Z",
            abs(float(moved[0]) - (90.0 - img["near"])) < 1e-6 and abs(float(moved[2])) < 1e-6,
            f"moved={moved.round(3).tolist()}",
        )
        breadcrumb = (app.rows[mirror_row].advanced or {}).get("ScenePlacement", {})
        check("image solve: breadcrumb intact (walk keeps not re-sweeping)", bool(breadcrumb.get("last_axis_to_axis_move")))

        # 3: OBJECT solve -- pin near=60; LED+BS slide; chain repackages rigidly.
        chain_pair = (1, int(img["mirror_row"]))
        gap_before = app._split_row_world_center(chain_pair[1]) - app._split_row_world_center(chain_pair[0])
        ok2, msg2 = app._apply_folded_object_split("near", 60.0)
        obj2 = app._folded_object_conjugate_split()
        gap_after = app._split_row_world_center(chain_pair[1]) - app._split_row_world_center(chain_pair[0])
        check("object solve applies", bool(ok2), msg2[:60])
        check(
            "object solve: near exact, total preserved",
            abs(obj2["near"] - 60.0) < 1e-6 and abs(obj2["total"] - obj["total"]) < 1e-6,
            f"near={obj2['near']:.3f} total={obj2['total']:.3f}",
        )
        check(
            "object solve: chain internal geometry rigid",
            bool(np.allclose(gap_before, gap_after, atol=1e-9)),
            f"gap delta={np.abs(gap_after - gap_before).max():.2e}",
        )
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- frozen-scene 2+2 leg constraints detected and solvable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
