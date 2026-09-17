"""bugs/0446 -- the promoted BS never rides a chain snap.

flag_20260726_175348: "Rubber band select + optical snap select BS eventhough it is
not within the selection area." The BS row is INSERTED at an index between the lens
datums although it physically sits inside the LED, so the 0436 lens-block index-gap
fill dragged it into every chain selection; and nothing stopped a chain snap from
moving the glued BS. Three layers fixed:

  1. `rubber_band_candidate_row_indices` excludes marked-BS rows (like the Object);
  2. `expand_rows_to_lens_block(..., excluded=...)` never ADDS a promoted solid;
  3. `_arm_snap_to_axis` drops marked-BS rows with a status note (belt for the
     Snap Selected / Assembly / programmatic paths).

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0446_bs_never_rides_chain_snap.py
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok " if ok else "XX "), label, (" " + detail if detail else ""))
    if not ok:
        FAILURES.append(label)


def main() -> int:
    from KrakenOS.UI.open3d_inspector import (
        expand_rows_to_lens_block,
        rubber_band_candidate_row_indices,
        _row_is_marked_beam_splitter_row,
    )

    # Pure core: the fill never introduces an excluded index; explicit selections keep it.
    exp, did = expand_rows_to_lens_block([1, 3, 4], 1, 6, excluded=[2])
    check("pure: fill skips the excluded in-block index", exp == [1, 3, 4, 5, 6] and did, str(exp))
    exp, did = expand_rows_to_lens_block([1, 2, 3, 4], 1, 6, excluded=[2])
    check("pure: an explicitly selected excluded index survives", 2 in exp, str(exp))
    exp, did = expand_rows_to_lens_block([1, 3, 4], 1, 6)
    check("pure: default excluded=() keeps 0436 behavior", exp == [1, 2, 3, 4, 5, 6] and did, str(exp))

    # Real scene: the user's exact flag state -- BS added, mirror deleted, chain boxed.
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        # Replicate the user's session state (flag row map: front datum 1, BS 2): the
        # BS insert index follows the TABLE selection (max(selected)+1), so delete the
        # mirror first and select row 1 before the add -- the BS lands INSIDE the
        # lens-block index span while physically sitting in the LED.
        mirror1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([mirror1])
        try:
            app._select_table_indices([1], focus_index=1)
        except Exception:
            app._select_table_row(1)
        app.add_beam_splitter_to_led(kind="plate")
        bs_rows = [i for i, r in enumerate(app.rows) if _row_is_marked_beam_splitter_row(r)]
        check("real: exactly one marked BS row exists", len(bs_rows) == 1, str(bs_rows))
        bs = bs_rows[0]
        front = app._lens_datum_row_index("front")
        rear = app._lens_datum_row_index("rear")
        check(
            "real: the BS row index sits INSIDE the lens-block span (the 0446 trap)",
            front is not None and rear is not None and front < bs < rear,
            f"front={front} bs={bs} rear={rear}",
        )
        candidates = rubber_band_candidate_row_indices(app.rows)
        check("real: rubber-band candidates exclude the BS row", bs not in candidates, str(candidates))
        image_row = next(
            i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"
        )
        check("real: the Image row stays a candidate", image_row in candidates, str(image_row))

        # The user's box: chain rows without the BS -- expansion must not pull it in.
        boxed = [i for i in candidates if i != 0 and i != image_row]
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        insp = _open_inspector(app)
        if insp is None:
            print("SKIP: no inspector available for the arm check")
        else:
            expanded, _ = insp._expand_selection_rows_for_groups(boxed)
            check("real: group expansion does not add the BS", bs not in expanded, str(expanded))
            insp._arm_snap_to_axis(sorted(set(boxed) | {bs}), "selected")
            armed = sorted(int(i) for i in (getattr(insp, "_snap_rows_selection", []) or []))
            check(
                "real: arming drops a BS smuggled into the selection, with a status note",
                bs not in armed and "beam splitter excluded" in insp.status_var.get(),
                f"armed={armed} status={insp.status_var.get()[:60]}",
            )
            check("real: the rest of the chain stays armed", len(armed) >= 5, str(armed))
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- the glued BS never rides a chain snap (candidates, fill, arm)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
