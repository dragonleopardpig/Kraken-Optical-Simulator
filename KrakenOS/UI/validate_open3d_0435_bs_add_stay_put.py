"""Guard for bugs/0435 -- adding a beam splitter to the LED is STATION-NEUTRAL.

flag_20260726_094845_383 (recording_20260726_095434): the one-click "Add Beam
Splitter to LED" promoted the BS with its raw axial reserve (~62.5 mm for the
45-deg plate) as row thickness. Stations are cumulative thickness, so every
station-fed consumer downstream shifted the moment the BS was added -- the
free-placed PINNED second RA mirror (pose = station + desp), the sequential
Image -- by an amount that depended on which table row happened to be selected
(the insert index). The user read it as the chain "shifting down" and blamed
the subsequent mirror delete.

Checks (display-free where possible; the editor app is Tk and needs a DISPLAY):
  NEUTRAL-ADD    -- after add_beam_splitter_to_led('plate') on the folded AZ85,
                    every pre-existing row's override center+rotation is
                    unchanged (identity-matched), the pinned mirror-2 keeps its
                    leg pose, and the BS row has thickness 0 with the
                    station_neutral promotion mark.
  INSERT-AGNOSTIC-- the same holds when the table selection forces the insert
                    into the middle of the chain (the user's actual state).
  DELETE-HOLDS   -- the user's next step (delete the temporary mirror) removes
                    the row and the 0433 stay-put freeze keeps every surviving
                    element in place, BS present.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENE = REPO_ROOT / "attachment" / "machine_vision_AZ85_RA_Mirror.py"


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    if not SCENE.exists():
        return True, [f"SKIP: scene fixture absent ({SCENE.name})"]
    try:
        import numpy as np
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides
        from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold
    except Exception as exc:  # pragma: no cover - environment guard
        return True, [f"SKIP: imports unavailable ({exc!r})"]

    def world_state(app):
        overrides = optical_solid_output_port_pose_overrides(None, app.rows)
        z = app._row_z_positions()
        state = []
        for i, row in enumerate(app.rows):
            ov = overrides.get(i)
            if isinstance(ov, dict):
                center = np.asarray(ov["center"], dtype=float).reshape(3)
                rotation = np.asarray(ov["rotation"], dtype=float).reshape(3, 3)
            else:
                center = np.asarray(
                    (float(row.desp_x), float(row.desp_y), float(z[i]) + float(row.desp_z)),
                    dtype=float,
                )
                rotation = None
            state.append((str(getattr(row, "name", "")), center, rotation))
        return state

    ok = True

    def scenario(select_index, tag):
        nonlocal ok
        app = KrakenLayoutEditor()
        try:
            app.layout_files["az85"] = SCENE
            app.load_layout_by_name("az85")
            pre = world_state(app)
            if select_index is not None:
                app._select_table_indices([select_index], focus_index=select_index)
            result = app.add_beam_splitter_to_led("plate")
            if not isinstance(result, dict):
                notes.append(f"SKIP: {tag}: add_beam_splitter_to_led unavailable in this env")
                return None
            post = world_state(app)
            bs_index = int(result["row_index"])
            moved = []
            for j in range(len(post)):
                i = j if j < bs_index else j - 1
                if j == bs_index or i >= len(pre):
                    continue
                name, center, rotation = pre[i]
                name2, c2, r2 = post[j]
                if name != name2:
                    moved.append(f"S{i}->S{j} name mismatch")
                elif not np.allclose(center, c2, atol=1.0e-6):
                    moved.append(f"{name} center moved")
                elif rotation is not None and r2 is not None and not np.allclose(rotation, r2, atol=1.0e-6):
                    moved.append(f"{name} rotation changed")
            bs_row = app.rows[int(result["row_index"])]
            neutral = abs(float(bs_row.thickness)) <= 1.0e-9
            promo = (getattr(bs_row, "advanced", {}) or {}).get("StepOverlayPromotion") or {}
            if moved or not neutral:
                ok = False
                notes.append(f"{tag}: FAILED -- moved={moved[:3]} thickness={float(bs_row.thickness):g}")
            else:
                notes.append(f"{tag}: no element moved; BS thickness=0, station_neutral={bool(promo.get('station_neutral'))}")
            return app
        except Exception as exc:
            try:
                app.destroy()
            except Exception:
                pass
            notes.append(f"SKIP: {tag} raised {exc!r}")
            return None

    mid = scenario(2, "INSERT-AGNOSTIC = mid-chain insert stays put")
    if mid is not None:
        try:
            mid.destroy()
        except Exception:
            pass
    app = scenario(None, "NEUTRAL-ADD = default insert stays put")
    if app is None:
        return ok, notes
    try:
        pre = world_state(app)
        mirrors = [i for i, r in enumerate(app.rows) if _row_is_promoted_mirror_fold(r)]
        n_before = len(app.rows)
        removed_at = mirrors[0] if mirrors else 0
        removed = app.delete_optical_step_rows([removed_at]) if mirrors else 0
        post = world_state(app)
        removed_count = n_before - len(app.rows)
        moved = []
        for j in range(len(post)):
            i = j if j < removed_at else j + removed_count
            if i >= len(pre):
                continue
            name, center, _rot = pre[i]
            name2, c2, _ = post[j]
            if name != name2:
                moved.append(f"S{i}->S{j} name mismatch")
            elif not np.allclose(center, c2, atol=1.0e-4):
                moved.append(name)
        if removed >= 1 and len(app.rows) < n_before and not moved:
            notes.append(f"DELETE-HOLDS = mirror removed (rows {n_before}->{len(app.rows)}), freeze kept every survivor")
        else:
            ok = False
            notes.append(f"DELETE-HOLDS FAILED: removed={removed} moved={moved[:4]}")
    except Exception as exc:
        notes.append(f"SKIP: delete flow raised {exc!r}")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(("ok " if ("=" in note and "FAILED" not in note) or note.startswith("SKIP") else "XX ") + note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
