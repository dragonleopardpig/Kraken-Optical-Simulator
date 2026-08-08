"""bugs/0456 guard -- a constrained frozen solve keeps every STEP body on its row.

flag_20260727_195719 ("changed FOV to 20x20 and set constraint, elements shifted off
optical axis"): the solve moved every ROW -4.3 mm while every BODY moved +16.8 mm, so
the surrogate detached from its CAD. A body is anchored to its row's z-STATION, so the
gap edits inside the solve drag it -- and the fold-leg split then only NUDGED the
persisted offset by its own delta, double-counting. The split now seats each body on an
absolute world target measured after the row re-bake.

Checks:
  SOURCE -- the frozen appliers seat bodies absolutely (no bare offset nudge).
  REAL   -- on the frozen BS scene, FOV solve + object-leg pin leaves the lens barrel
            and camera body exactly where their anchor rows are (pre-fix: 35 / 30 mm).
"""
from __future__ import annotations

import inspect as _inspect

import numpy as np


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


def _pairings(app) -> dict:
    out = {}
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


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin as _Mixin
    except Exception:
        try:
            from KrakenOS.UI.services import paraxial_tools as _pt

            _Mixin = next(
                obj for name, obj in vars(_pt).items() if name.endswith("Mixin") and isinstance(obj, type)
            )
        except Exception as exc:
            return True, [f"SKIP: paraxial mixin unavailable ({exc!r})"]

    try:
        obj_src = _inspect.getsource(_Mixin._apply_frozen_bs_object_split)
        img_src = _inspect.getsource(_Mixin._apply_frozen_image_split)
        # bugs/0585: the image applier now delegates its world work to the stage-(b) settle
        # (bugs/DESIGN_world_authority_settle.md), so the absolute seat lives one call-hop down.
        # Follow the delegation rather than grepping one function's body -- the INVARIANT is
        # "the frozen appliers seat bodies absolutely", not "this exact function contains the
        # call". (Phase 435 needed the same correction for the near-leg spill.)
        if "_settle_image_fold_world" in img_src:
            img_src += _inspect.getsource(_Mixin._settle_image_fold_world)
    except Exception as exc:
        return True, [f"SKIP: frozen appliers unavailable ({exc!r})"]
    if "_seat_step_body_world_center" in obj_src and "_seat_step_body_world_center" in img_src:
        notes.append("SOURCE = both frozen appliers seat bodies on absolute world targets")
    else:
        notes.append("SOURCE a frozen applier still nudges the body offset (0456 regression)")
        ok = False

    try:
        from pathlib import Path

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

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
        before = _pairings(app)
        split = app._folded_object_conjugate_split()
        if not isinstance(split, dict) or len(before) < 2:
            notes.append("SKIP: the frozen object split / bodies are unavailable on this scene")
            return ok, notes
        insp = _open_inspector(app)
        insp._quick_estimation_service().fov_solve("object", "thickness", 20.0, 20.0, None)
        app._apply_folded_object_split("near", float(split["near"]) + 10.0)
        after = _pairings(app)
        drifts = {
            label: float(np.linalg.norm(after[label] - before[label]))
            for label in before
            if label in after
        }
        if drifts and all(d < 1.0 for d in drifts.values()):
            notes.append(
                "REAL = bodies stayed on their rows through the constrained solve "
                f"({', '.join(f'{k} {v:.3f} mm' for k, v in drifts.items())})"
            )
        else:
            notes.append(f"REAL bodies drifted off their rows: {drifts}")
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
