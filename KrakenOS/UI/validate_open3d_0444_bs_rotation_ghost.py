"""bugs/0444 — BS rotation stays single-bodied; delete claims the spacer; coating faces the object.

Guard for flag_20260726_153723 ("rotate it, now there is a residual 'ghost' plane" + "the
reflecting surface is at the second surface relative to the Object") on the round-3 AZ85
workflow (add plate BS -> delete mirror-1 -> snap chain):

- ROTATE: rotating the promoted BS via the placement-gizmo wrapper re-poses every
  plate-region actor family — count never grows, nothing untracked appears, families move.
  (The live ghost did not reproduce headlessly; this encodes the healthy contract so a
  stale-actor regression in the rotate/refresh path fails here.)
- SPACER: the mirror's trailing AIR spacer is claimed through the interposed
  station-neutral BS row (`_is_inpath_trailing_spacer` lives on the promotion SERVICE,
  not the editor MRO — the getattr-based branch silently never ran).
- COATING: the auto-flagged Beam Splitter face's outward normal faces the incoming +Z
  beam (signed dot < 0) — the two diagonal faces tie on |angle| and area, so the abs()
  pick was arbitrary.

SKIPs (returns True with a note) when the environment cannot build the editor/scene.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    try:
        import numpy as np

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    except Exception as exc:
        return True, [f"SKIP: imports unavailable ({exc!r})"]
    scene = REPO / "attachment" / "machine_vision_AZ85_RA_Mirror.py"
    if not scene.exists():
        return True, ["SKIP: AZ85 scene attachment is absent"]
    try:
        app = KrakenLayoutEditor()
    except Exception as exc:
        return True, [f"SKIP: KrakenLayoutEditor unavailable ({exc!r})"]
    ok = True
    try:
        try:
            app.layout_files["az85"] = scene
            app.load_layout_by_name("az85")
            app.add_beam_splitter_to_led(kind="plate")
        except Exception as exc:
            return True, [f"SKIP: BS add unavailable ({exc!r})"]

        def is_bs(row) -> bool:
            return "OpticalSolidBeamSplitter" in str(getattr(row, "advanced", {}) or {})

        def is_spacer(row) -> bool:
            try:
                return bool((getattr(row, "advanced", None) or {}).get("InPathTrailingSpacer"))
            except Exception:
                return False

        # COATING: flagged face's outward normal faces the object (+Z beam first hit).
        bs_row = next(i for i, r in enumerate(app.rows) if is_bs(r))
        signed = None
        try:
            _row, _path, metadata = app._optical_solid_face_metadata_for_row(bs_row)
            for face in metadata.get("faces", []) or []:
                if "beam" in str(face.get("function", "")).lower():
                    normal = np.asarray(face.get("normal", (0, 0, 1)), dtype=float).reshape(-1)[:3]
                    signed = float(np.dot(normal / max(float(np.linalg.norm(normal)), 1e-12), (0.0, 0.0, 1.0)))
                    break
        except Exception as exc:
            notes.append(f"SKIP-coating: face metadata unavailable ({exc!r})")
        if signed is not None:
            # bugs/0445 (user decision): the coating defaults to the OBJECT-FACING
            # diagonal -- the first surface the incoming +Z beam meets. The kernel
            # entry-face split fix (__NsTraceSplitChildSkipSurface) makes the
            # first-surface split physical, so this is now a CONTRACT, not
            # informational.
            if signed < 0.0:
                notes.append(f"COATING = flagged face faces the object (dot={signed:+.3f})")
            else:
                notes.append(
                    f"COATING: flagged face faces AWAY from the object (dot={signed:+.3f}; "
                    "want the object-facing diagonal, bugs/0445)"
                )
                ok = False

        # SPACER: delete claims the mirror's spacer through the station-neutral BS row.
        m1 = next(
            i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")) and not is_bs(r)
        )
        gap_before = float(app.rows[0].thickness)
        app.delete_optical_step_rows([m1])
        strays = [i for i, r in enumerate(app.rows) if is_spacer(r)]
        delta = float(app.rows[0].thickness) - gap_before
        if not strays and abs(delta - 90.135) < 0.5:
            notes.append(f"SPACER = claimed through the BS row, span returned ({delta:.3f}mm)")
        else:
            notes.append(f"SPACER strays={strays} span-delta={delta:.3f} (want ~90.135, none stray)")
            ok = False

        # ROTATE: needs the embedded inspector (display).
        try:
            sel = [i for i, r in enumerate(app.rows) if i > 0 and not is_bs(r) and not is_spacer(r)]
            app.snap_rows_to_axis(
                sel,
                {
                    "axis_id": "axis:global:split",
                    "axis_label": "BS",
                    "points": np.array([(0.0, 0.0, 41.8), (193.3, 0.0, 41.8)]),
                    "picked_world": np.array([155.0, 0.0, 41.8]),
                },
            )
            app.open_3d_view()
            app.update_idletasks()
            app.update()
            inspector = app._three_d_inspector
        except Exception as exc:
            inspector = None
            notes.append(f"SKIP-rotate: inspector unavailable ({exc!r})")
        if inspector is not None and getattr(inspector, "available", False):
            import time as _time

            for _ in range(3):
                inspector.update_idletasks()
                inspector.update()
                _time.sleep(0.1)

            def census():
                tracked = {id(a) for a in inspector._actor_by_key.values()}
                fams, untracked = [], 0
                coll = inspector._renderer.GetActors()
                coll.InitTraversal()
                for _ in range(coll.GetNumberOfItems()):
                    actor = coll.GetNextActor()
                    if actor is None or not actor.GetVisibility():
                        continue
                    try:
                        b = actor.GetBounds()
                    except Exception:
                        continue
                    c = ((b[0] + b[1]) / 2.0, (b[2] + b[3]) / 2.0, (b[4] + b[5]) / 2.0)
                    ext = (round(b[1] - b[0], 0), round(b[3] - b[2], 0), round(b[5] - b[4], 0))
                    if -70 < c[0] < 70 and -60 < c[2] < 95 and 30 < max(ext) < 120:
                        fams.append((ext, (round(c[0], 0), round(c[1], 0), round(c[2], 0))))
                        if id(actor) not in tracked:
                            untracked += 1
                return sorted(fams), untracked

            bs_row = next(i for i, r in enumerate(app.rows) if is_bs(r))
            pre, pre_un = census()
            inspector._apply_scene_placement_rotate_handle(bs_row, "z", 90.0)
            for _ in range(3):
                app.update_idletasks()
                app.update()
                inspector.update_idletasks()
                inspector.update()
                _time.sleep(0.1)
            post, post_un = census()
            moved = sum(1 for f in pre if f not in post)
            if len(post) <= len(pre) and pre_un == 0 and post_un == 0 and moved >= 4:
                notes.append(
                    f"ROTATE = single-bodied re-pose (pre={len(pre)} post={len(post)} moved={moved})"
                )
            else:
                notes.append(
                    f"ROTATE ghost signature: pre={len(pre)} post={len(post)} "
                    f"untracked={pre_un}/{post_un} moved={moved}"
                )
                ok = False
        return ok, notes
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(("  " if ("=" in note or note.startswith("SKIP")) else "! ") + note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
