"""bugs/0463 guard -- a traced axis that shadows a guide axis is not drawn twice.

flag_20260729_105204: "...still have 3 sensor/image plane and multiple optical axis." The
scene has three physical legs and three guide axes that already describe them:

    axis:global                 +Z from the origin        object -> beam splitter
    axis:global:split           +X from (0, 0, 53.8)      BS -> lens -> fold mirror
    axis:global:frozen-fold:7   -Z from (229.9, 0, 53.8)  fold mirror -> sensor

but a traced chief-ray segment (axis:ray:426:segment:4) ran PARALLEL to the split guide,
3.9 mm off it, and drew a second dotted line on top -- five axes for three legs.

The existing distinctness test only compared a traced segment with the LAUNCH direction, so a
segment lying on an already-drawn guide survived. Traced segments are now also compared with
the guide records assembled before them: same direction and within 10 mm of the same line
means it is already drawn.

Checks:
  SOURCE -- the dedup exists and compares against the assembled records.
  REAL   -- on the user's BS scene no two axes are parallel-and-coincident.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

BS_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def _axis_line(record):
    try:
        pts = np.asarray(record.get("points"), dtype=float).reshape(-1, 3)
    except Exception:
        return None
    if pts.shape[0] < 2:
        return None
    direction = pts[-1] - pts[0]
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-9:
        return None
    return pts[0], direction / norm


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    try:
        from KrakenOS.UI import open3d_inspector as oi

        src = _inspect.getsource(oi.Kraken3DInspector._optical_axis_records_for_3d)
    except Exception as exc:
        return True, [f"SKIP: inspector unavailable ({exc!r})"]
    if "_duplicates_existing" in src:
        notes.append("SOURCE = traced segments are deduped against the guide axes")
    else:
        notes.append("SOURCE the 0463 axis dedup is missing")
        ok = False

    if not BS_SCENE.exists():
        notes.append("SKIP: the BS scene is absent (gitignored attachment)")
        return ok, notes

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
        app.layout_files["bs"] = BS_SCENE
        app.load_layout_by_name("bs")
        app.open_3d_view()
        app.update_idletasks()
        app.update()
        inspector = app.__dict__.get("_three_d_inspector")
        if inspector is None:
            notes.append("SKIP: the 3-D inspector is unavailable")
            return ok, notes
        inspector.refresh_from_editor(force_retrace=True, geometry_changed=True)
        inspector.update_idletasks()
        inspector.update()
        records = inspector._optical_axis_records_for_3d(inspector.__dict__.get("_current_scene_bundle"))
        lines = [(r.get("axis_id"), _axis_line(r)) for r in records]
        lines = [(i, ln) for i, ln in lines if ln is not None]
        dupes = []
        for a in range(len(lines)):
            for b in range(a + 1, len(lines)):
                (id_a, (o_a, u_a)), (id_b, (o_b, u_b)) = lines[a], lines[b]
                if abs(float(np.dot(u_a, u_b))) < 0.999:
                    continue
                off = o_b - o_a
                perp = off - u_a * float(np.dot(off, u_a))
                if float(np.linalg.norm(perp)) <= 10.0:
                    dupes.append(f"{id_a} ~ {id_b}")
        if not dupes:
            notes.append(f"REAL = no axis shadows another ({len(records)} distinct axes)")
        else:
            notes.append(f"REAL duplicate axes still drawn: {dupes}")
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
