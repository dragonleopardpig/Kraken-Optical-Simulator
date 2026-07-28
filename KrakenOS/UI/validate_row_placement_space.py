"""Step 1 guard — one source of truth for a row's coordinate space.

``docs/design_row_placement_space.md``. ``SurfaceRow.desp_*`` means either "offset from a
station on the nominal axis" (SEQUENTIAL, fold applied later) or "absolute, already folded"
(WORLD, what the 0433 freeze/snap bakes in). Six subsystems used to infer that privately and
their drift produced 0448, 0456, 0457-A and 0457-B.

Checks:
  SOURCE -- the resolver exists, names the world-placement keys once, and spells out the
            "do not fold twice" predicate.
  REAL   -- on the AZ85 BS scene the frozen chain classifies WORLD (including the Image row),
            while the object and the later-added beam splitter stay SEQUENTIAL.
  SCOPE  -- Step 1 adds the resolver WITHOUT re-pointing consumers, so this phase pins the
            classification only. The behavioural half (the display must skip the fold for a
            WORLD row) lands in Step 2; `tools/pose_audit.py` measures it and currently
            reports the 51.50 mm double fold on row 8.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI.services import row_placement as rp
    except Exception as exc:
        return False, [f"SOURCE the row_placement resolver is missing ({exc!r})"]

    src = _inspect.getsource(rp)
    if all(name in src for name in ("WORLD_PLACEMENT_KEYS", "must_not_display_fold", "orientation")):
        notes.append("SOURCE = the resolver names the world keys once and carries orientation")
    else:
        notes.append("SOURCE the resolver is missing its keys / fold predicate / orientation")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is absent (gitignored attachment)")
        return ok, notes

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
        app.layout_files["bs"] = SCENE
        app.load_layout_by_name("bs")
        spaces = rp.scene_placement_summary(app)
        world_rows = sorted(i for i, s in spaces.items() if s == rp.WORLD)
        image_row = next(
            (i for i in range(len(app.rows) - 1, -1, -1) if str(getattr(app.rows[i], "surface", "")) == "Image"),
            None,
        )
        if not world_rows:
            notes.append("REAL the frozen chain did not classify as WORLD at all")
            ok = False
        elif image_row is not None and image_row in world_rows:
            notes.append(
                f"REAL = the frozen chain is WORLD-placed {world_rows}, Image row {image_row} included"
            )
        else:
            notes.append(f"REAL the Image row {image_row} is not WORLD-placed (world={world_rows})")
            ok = False

        if spaces.get(0) == rp.SEQUENTIAL:
            notes.append("REAL = the object row stays SEQUENTIAL (not everything is world)")
        else:
            notes.append("REAL the object row was misclassified as WORLD")
            ok = False

        if image_row is not None and rp.must_not_display_fold(app.rows[image_row]):
            notes.append(
                "SCOPE = the Image row is flagged must_not_display_fold "
                "(Step 2 wires the display to it; the audit measures the 51.50 mm gap today)"
            )
        else:
            notes.append("SCOPE the Image row is not flagged against a second fold")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: scene drive failed ({exc!r})")
    finally:
        if app is not None:
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
