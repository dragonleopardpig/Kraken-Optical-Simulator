"""bugs/0524/0526 guard -- an along-leg lens drag must NOT corrupt the frozen scene.

History: 0524's first cut wrote the leg slide through to the neighbouring section gaps so
the FOV readout would follow. flag_20260803_162321 ("haywire") showed that on a frozen
chain those raw writes are NOT free knobs: the upstream write shifted every downstream
STATION (the glued BS re-seated by the drag -- a ghost second diagonal), and the near-leg
gap row DERIVES the mirror's world leg (bugs/0478: world = const - thickness), so the
prism re-seated up the unfolded axis. The write-through is REVERTED until it rides the
0505-class atomic accompaniment (glue re-express + breadcrumb const re-bake) -- that is
bugs/0526.

This guard pins the SAFE contract meanwhile:
  SOURCE -- the revert (with its reasoning) is in place, not a silent re-introduction.
  REAL   -- an along-leg lens drag leaves EVERY section gap byte-identical AND the
            fold-solid rows' world seats untouched (no ghost BS, no prism re-seat).
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import scene_placement_commands as _spc

    src = _inspect.getsource(_spc.ScenePlacementMixin.translate_step_overlay)
    if "bugs/0526" in src and "section write-through skipped by design" in src:
        notes.append("SOURCE = the 0524 write-through stays reverted pending the 0526 accompaniment")
    else:
        notes.append("SOURCE the 0524 revert marker is gone -- was the raw write re-introduced?")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services import optical_axis_tree as tree_mod

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        gaps0 = [float(r.thickness) for r in app.rows]
        prism0 = np.asarray(tree_mod.row_world_pose(app.rows, 7), dtype=float).reshape(-1)[:3]
        bs0 = np.asarray(tree_mod.row_world_pose(app.rows, 3), dtype=float).reshape(-1)[:3]
        app.translate_step_overlay("lens", (8.0, 0.0, 0.0))
        gaps1 = [float(r.thickness) for r in app.rows]
        prism1 = np.asarray(tree_mod.row_world_pose(app.rows, 7), dtype=float).reshape(-1)[:3]
        bs1 = np.asarray(tree_mod.row_world_pose(app.rows, 3), dtype=float).reshape(-1)[:3]
        if all(abs(b - a) < 1e-9 for a, b in zip(gaps0, gaps1)):
            notes.append("REAL = the along-leg drag leaves every section gap untouched")
        else:
            deltas = [round(b - a, 3) for a, b in zip(gaps0, gaps1)]
            notes.append(f"REAL the drag wrote section gaps again ({deltas}) -- the 162321 corruption")
            ok = False
        if float(np.linalg.norm(prism1 - prism0)) < 1e-6 and float(np.linalg.norm(bs1 - bs0)) < 1e-6:
            notes.append("REAL = the BS and prism world seats hold (no ghost, no re-seat)")
        else:
            notes.append(
                f"REAL fold solids moved (BS delta {np.round(bs1 - bs0, 3).tolist()}, "
                f"prism delta {np.round(prism1 - prism0, 3).tolist()})"
            )
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
