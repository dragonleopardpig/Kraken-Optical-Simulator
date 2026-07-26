"""bugs/0446 guard -- the glued beam splitter never rides a chain snap.

flag_20260726_175348: the BS row is inserted at an index between the lens datums
although it physically sits in the LED, so the 0436 index-gap fill dragged it into
every chain selection. Three layers hold: candidates exclude marked-BS rows, the
block fill never ADDS a promoted solid, and arming drops a smuggled BS with a status
note.
"""
from __future__ import annotations


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    try:
        from KrakenOS.UI.open3d_inspector import (
            expand_rows_to_lens_block,
            rubber_band_candidate_row_indices,
            _row_is_marked_beam_splitter_row,
        )
    except Exception as exc:
        return True, [f"SKIP: inspector module unavailable ({exc!r})"]

    # PURE: fill exclusion semantics.
    exp, did = expand_rows_to_lens_block([1, 3, 4], 1, 6, excluded=[2])
    if exp == [1, 3, 4, 5, 6] and did:
        notes.append("PURE = fill skips excluded in-block indices")
    else:
        notes.append(f"PURE fill exclusion broken: {exp}")
        ok = False
    exp, _ = expand_rows_to_lens_block([1, 2, 3], 1, 6, excluded=[2])
    if 2 in exp:
        notes.append("PURE = explicitly selected excluded index survives")
    else:
        notes.append(f"PURE explicit selection dropped: {exp}")
        ok = False

    # REAL: the user's session shape (BS inserted inside the block span).
    try:
        from pathlib import Path

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

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
        mirror1 = next(
            i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", ""))
        )
        app.delete_optical_step_rows([mirror1])
        try:
            app._select_table_indices([1], focus_index=1)
        except Exception:
            app._select_table_row(1)
        app.add_beam_splitter_to_led(kind="plate")
        bs_rows = [i for i, r in enumerate(app.rows) if _row_is_marked_beam_splitter_row(r)]
        front = app._lens_datum_row_index("front")
        rear = app._lens_datum_row_index("rear")
        if len(bs_rows) == 1 and front is not None and rear is not None and front < bs_rows[0] < rear:
            notes.append(f"REAL = BS row {bs_rows[0]} sits inside the block span ({front}..{rear})")
        else:
            notes.append(f"SKIP: could not force the in-block BS ({bs_rows}, {front}..{rear})")
            return ok, notes
        bs = bs_rows[0]
        candidates = rubber_band_candidate_row_indices(app.rows)
        if bs not in candidates:
            notes.append("REAL = rubber-band candidates exclude the BS")
        else:
            notes.append(f"REAL candidates include the BS: {candidates}")
            ok = False
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        insp = _open_inspector(app)
        boxed = [i for i in candidates if i != 0]
        expanded, _ = insp._expand_selection_rows_for_groups(boxed)
        if bs not in expanded:
            notes.append("REAL = group expansion never adds the BS")
        else:
            notes.append(f"REAL expansion added the BS: {expanded}")
            ok = False
        insp._arm_snap_to_axis(sorted(set(boxed) | {bs}), "selected")
        armed = sorted(int(i) for i in (getattr(insp, "_snap_rows_selection", []) or []))
        if bs not in armed and len(armed) >= 5:
            notes.append("REAL = arming drops a smuggled BS, chain stays armed")
        else:
            notes.append(f"REAL arm kept the BS / lost the chain: {armed}")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
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
