"""bugs/0441 -- PROOF OF FIX (parent applies the real patch in layout_import_export.py).

Root cause (bisected via probe_0441_bisect.py): ``_normalize_special_rows``
(layout_import_export.py:1226-1232) unconditionally zeroes an Aperture row's
``tilt_y``/``tilt_z``. After the 0433 stay-put freeze those tilts ARE the baked
world placement -- the next normalize (the BS add runs two) flattens the drawn
aperture ring back to +Z while its neighbours stay leg-facing: the user's
"Aperture plane still flipped" (flag_20260726_111606_491).

This probe monkeypatches the PROPOSED fix semantics onto the live editor --
preserve a breadcrumbed (stay_put_freeze / last_axis_to_axis_move) aperture's
tilt_y/tilt_z across normalize -- and proves the full user sequence then keeps
the ring leg-facing, while an un-breadcrumbed aperture still normalizes to 0.
"""
from pathlib import Path

import KrakenOS.UI.validate_open3d_penta_telescope_comprehensive as V

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
failures: list[str] = []


def check(ok: bool, note: str) -> None:
    print(("ok  " if ok else "FAIL"), note)
    if not ok:
        failures.append(note)


def _row_is_breadcrumbed(row) -> bool:
    placement = (getattr(row, "advanced", None) or {}).get("ScenePlacement")
    return isinstance(placement, dict) and bool(
        placement.get("stay_put_freeze") or placement.get("last_axis_to_axis_move")
    )


def install_proposed_fix(app) -> None:
    original = app._normalize_special_rows

    def patched():
        keep = {
            id(row): (float(row.tilt_y), float(row.tilt_z))
            for row in app.rows
            if str(getattr(row, "surface", "")) == "Aperture" and _row_is_breadcrumbed(row)
        }
        original()
        for row in app.rows:
            saved = keep.get(id(row))
            if saved is not None:
                row.tilt_y, row.tilt_z = saved

    app._normalize_special_rows = patched


def aperture_state(app, inspector):
    for i, row in enumerate(app.rows):
        if str(getattr(row, "surface", "")) == "Aperture":
            tilts = (round(float(row.tilt_x), 1), round(float(row.tilt_y), 1), round(float(row.tilt_z), 1))
            thin = None
            for key in (getattr(inspector, "_row_actor_map", {}) or {}).get(i) or []:
                actor = (getattr(inspector, "_actor_by_key", {}) or {}).get(key)
                if actor is None:
                    continue
                b = actor.GetBounds()
                ext = [b[1] - b[0], b[3] - b[2], b[5] - b[4]]
                thin = "XYZ"[ext.index(min(ext))]
                break
            return tilts, thin
    return None, None


def main() -> int:
    app = V.KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        inspector = V._open_inspector(app)
        install_proposed_fix(app)

        # user round-2 sequence: delete (freeze) -> add BS plate
        m1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([m1])
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks()
        tilts, thin = aperture_state(app, inspector)
        check(tilts == (0.0, -90.0, -180.0), f"post-freeze aperture tilts baked ({tilts})")
        check(thin == "X", f"post-freeze aperture ring faces the leg (thin={thin})")

        app.add_beam_splitter_to_led(kind="plate")
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks()
        tilts, thin = aperture_state(app, inspector)
        check(
            tilts == (0.0, -90.0, -180.0),
            f"WITH FIX: BS add preserves the breadcrumbed aperture tilts ({tilts})",
        )
        check(thin == "X", f"WITH FIX: aperture ring still faces the leg after BS add (thin={thin})")

        # negative control: pristine (un-breadcrumbed) aperture still normalizes.
        app.load_layout_by_name("az85")
        ap = next(i for i, r in enumerate(app.rows) if str(getattr(r, "surface", "")) == "Aperture")
        app.rows[ap].tilt_y = 12.0
        app._normalize_special_rows()
        check(
            float(app.rows[ap].tilt_y) == 0.0,
            "un-breadcrumbed aperture tilt_y still normalized to 0 (guard scoped)",
        )
    finally:
        app.destroy()

    if failures:
        print(f"RESULT: FAIL ({len(failures)})")
        return 1
    print("RESULT: PASS -- proposed normalize guard keeps the frozen aperture ring leg-facing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
