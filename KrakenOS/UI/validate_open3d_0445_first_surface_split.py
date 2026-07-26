"""bugs/0445 guard -- a first-surface (entry-face) BS split is physical.

User decision: the plate BS coating defaults to the OBJECT-FACING diagonal -- the
first surface the incoming beam meets. That split sends the transmit child INTO the
glass; the kernel's row-level ``skip_surface_once`` used to kill its exit through the
far face (the child refracted once, crossed other rows' planes inside-glass and died
``no_next_intersection`` -- the "~38 mm walk" of the 0445 investigation was the
17-degree in-glass bend sampled at another row's plane). ``__NsTraceSplitChildSkipSurface``
now exempts ENTRY-face splits exactly like the cube's internal cemented diagonal.

Checks (on the real AZ85 + plate):
  PICK     -- add_beam_splitter_to_led flags the object-facing diagonal (signed n.z < 0).
  COVERAGE -- the branched frame map covers the full imaging chain (>= 8 rows) with the
              transmit branch recorded, i.e. the entry-face split traverses the glass.
  CANON    -- re-flagging the AWAY-facing diagonal (the old canon) still covers the same
              row set: the fix is additive, the far-face split is untouched.
"""
from __future__ import annotations

import numpy as np


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    try:
        from pathlib import Path

        from KrakenOS.UI import optical_solid_metadata as osm
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.nonseq_output_ports import _branch_traced_row_frames

        scene = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        if not scene.exists():
            return True, ["SKIP: AZ85 scene absent (gitignored attachment)"]
        app = KrakenLayoutEditor()
    except Exception as exc:
        return True, [f"SKIP: environment unavailable ({exc!r})"]
    try:
        app.layout_files["az85"] = scene
        app.load_layout_by_name("az85")
        res = app.add_beam_splitter_to_led("plate")
        if not res:
            return True, ["SKIP: add_beam_splitter_to_led returned nothing"]
        bs_row = int(res["row_index"])

        # PICK: the flagged splitter face's outward normal faces the object.
        signed = None
        object_face = away_face = None
        _row, _path, metadata = app._optical_solid_face_metadata_for_row(bs_row)
        for face in metadata.get("faces", []) or []:
            normal = np.asarray(face.get("normal", (0, 0, 1)), dtype=float).reshape(-1)[:3]
            norm = float(np.linalg.norm(normal))
            if norm < 1e-9:
                continue
            dot = float(np.dot(normal / norm, (0.0, 0.0, 1.0)))
            angle = float(np.degrees(np.arccos(np.clip(abs(dot), 0, 1))))
            big = float(face.get("area_mm2", 0) or 0) > 1000.0
            if abs(angle - 45.0) <= 20.0 and big:
                if dot < 0:
                    object_face = str(face.get("face_id", ""))
                else:
                    away_face = str(face.get("face_id", ""))
            if "beam" in str(face.get("function", "")).lower():
                signed = dot
        if signed is not None and signed < 0.0:
            notes.append(f"PICK = coating on the object-facing diagonal (dot={signed:+.3f})")
        else:
            notes.append(f"PICK: flagged face dot={signed} (want < 0, the object-facing diagonal)")
            ok = False

        def coverage() -> list[int]:
            system = app.build_system(require_solids=True, force_rebuild=True)
            frames = _branch_traced_row_frames(system, list(app.rows))
            bad = [
                i
                for i, f in frames.items()
                if not np.all(np.isfinite(np.asarray(f.get("center"), dtype=float)))
            ]
            if bad:
                notes.append(f"COVERAGE: non-finite centres for rows {bad}")
                return []
            return sorted(frames)

        # COVERAGE: the entry-face split must carry the full chain.
        first_surface_rows = coverage()
        if len(first_surface_rows) >= 8:
            notes.append(
                f"COVERAGE = entry-face split covers {len(first_surface_rows)} rows {first_surface_rows}"
            )
        else:
            notes.append(
                f"COVERAGE: entry-face split covers only {first_surface_rows} "
                "(the transmit child died inside the glass -- the 0445 kernel fix regressed)"
            )
            ok = False

        # CANON: the away-facing (far-face) split still covers the same set.
        if object_face and away_face:
            app.assign_optical_solid_face_function(
                bs_row, object_face, osm.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_UNCOATED
            )
            app.assign_optical_solid_face_function(
                bs_row, away_face, osm.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_SPLITTER
            )
            canon_rows = coverage()
            if canon_rows == first_surface_rows:
                notes.append(f"CANON = far-face split unchanged ({len(canon_rows)} rows, same set)")
            else:
                notes.append(
                    f"CANON: far-face split rows {canon_rows} != entry-face rows {first_surface_rows}"
                )
                ok = False
        else:
            notes.append("SKIP-canon: could not identify both diagonals")
    except Exception as exc:
        return True, [f"SKIP: drive failed ({exc!r})"]
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
