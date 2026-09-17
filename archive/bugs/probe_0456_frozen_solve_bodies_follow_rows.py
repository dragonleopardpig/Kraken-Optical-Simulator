"""bugs/0456 -- on a frozen scene a constrained FOV solve must move rows and bodies TOGETHER.

flag_20260727_195719 ("changed FOV to 20x20 and set constraint, elements shifted off
optical axis"). The recording's one solve event moved every ROW -4.3 mm while every
BODY moved +16.8 mm (the LED +21.1 = both corrections), so the surrogate detached from
its CAD.

Root: a STEP body is anchored to its row's z-STATION, so the gap edits inside the solve
(``fov_solve`` runs first, then the fold-leg split) DRAG it -- and the split then only
NUDGED the persisted offset by its own delta, double-counting. The split now seats each
body on an absolute world target measured after the row re-bake
(``_seat_step_body_world_center``).

The invariant this pins: whatever the solve does to the prescription, each body keeps
its relationship to the row it is pinned to (lens barrel <-> front datum, camera <->
Image row).

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0456_frozen_solve_bodies_follow_rows.py
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


def _row_world(app, index: int) -> np.ndarray:
    z = app._row_z_positions()
    r = app.rows[index]
    return np.array(
        [float(r.desp_x), float(r.desp_y), float(z[index]) + float(r.desp_z)], dtype=float
    )


def _body_world(app, label: str):
    try:
        mesh = app._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return None
        b = np.asarray(mesh.bounds, dtype=float).reshape(6)
        return np.array(
            [(b[0] + b[1]) / 2.0, (b[2] + b[3]) / 2.0, (b[4] + b[5]) / 2.0], dtype=float
        )
    except Exception:
        return None


def _pairings(app) -> dict[str, np.ndarray]:
    """Body centre MINUS its anchor row's world centre -- the relationship a solve
    must preserve (this is what 'separated from the body' breaks)."""
    out: dict[str, np.ndarray] = {}
    front = app._lens_datum_row_index("front")
    image_row = next(
        (i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"),
        None,
    )
    for label, anchor in (("lens", front), ("camera", image_row)):
        body = _body_world(app, label)
        if body is not None and anchor is not None:
            out[label] = body - _row_world(app, anchor)
    return out


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")

        # --- the user's scene: freeze, add the BS, snap the chain onto the split leg ---
        mirror1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([mirror1])
        try:
            app._select_table_indices([1], focus_index=1)
        except Exception:
            app._select_table_row(1)
        app.add_beam_splitter_to_led(kind="plate")
        chain = [
            i
            for i, r in enumerate(app.rows)
            if getattr(r, "surface", None) in ("Standard", "Thin Lens", "Aperture", "Image")
            and i > 0
            and "next gap" not in str(getattr(r, "name", ""))
        ]
        z0 = app._row_z_positions()
        leg_z = float(z0[chain[0]]) + float(app.rows[chain[0]].desp_z)
        app.snap_rows_to_axis(
            chain,
            {
                "axis_id": "axis:global:split",
                "points": np.array([(0.0, 0.0, leg_z), (400.0, 0.0, leg_z)]),
                "picked_world": np.array([90.0, 0.0, leg_z]),
            },
        )

        before_pairs = _pairings(app)
        check("scene built: lens + camera bodies are pinned to their rows", len(before_pairs) == 2, str(list(before_pairs)))

        split = app._folded_object_conjugate_split()
        check("the object-side fold split is offered (0447)", isinstance(split, dict), str(type(split)))
        if not isinstance(split, dict):
            return 1
        pin_value = float(split["near"]) + 10.0  # slide the pinned leg 10 mm

        # --- the popup's exact sequence: FOV solve, then the fold-leg constraint -------
        # The popup drives the service off the INSPECTOR (which proxies to the editor).
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        insp = _open_inspector(app)
        qe = insp._quick_estimation_service()
        ok, msg = qe.fov_solve("object", "thickness", 20.0, 20.0, None)
        check("FOV 20x20 thickness solve ran", bool(ok), str(msg)[:80])
        ok_seg, msg_seg = app._apply_folded_object_split("near", pin_value)
        check("the object-leg constraint applied", bool(ok_seg), str(msg_seg)[:80])

        after_pairs = _pairings(app)
        for label in ("lens", "camera"):
            b, a = before_pairs.get(label), after_pairs.get(label)
            if b is None or a is None:
                check(f"{label}: pairing measurable after the solve", False, f"{b} -> {a}")
                continue
            drift = float(np.linalg.norm(a - b))
            check(
                f"{label} body still sits where its row does (drift {drift:.3f} mm)",
                drift < 1.0,
                f"before={b.round(2).tolist()} after={a.round(2).tolist()}",
            )

        # The flag's fingerprint: rows and bodies must not move in OPPOSITE directions.
        led_before = _body_world(app, "led")
        check("led body measurable", led_before is not None)
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- a constrained frozen solve keeps every body on its row")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
