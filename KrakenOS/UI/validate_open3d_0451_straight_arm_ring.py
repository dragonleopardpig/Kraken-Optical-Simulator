"""bugs/0451 guard -- the dead-end straight arm draws no sensor ring (but still stops rays).

flag_20260726_191053 ("after RA mirror deletion"): with the fold mirror gone the straight
beam runs into the LED and stops, and its synthesized branch detector drew a
"Sensor 23.0x23.0 / Image circle" coverage ring INSIDE the housing -- sensor iconography
where no sensor exists. The designed Image is off on the frozen fold leg and this arm
never reaches it.

Per the bugs/0182 double-duty rule only the DRAW is gated: the detector TARGET stays as
the ray hard-stop (dropping it un-bounds the rays into a starburst). A genuine SPLIT
still draws both arms (bugs/0090).

Checks:
  SOURCE -- scene_builder gates the lone non-imaging arm's draw.
  REAL   -- post-delete: one branch detector, draw suppressed, still is_detector.
  SPLIT  -- a BS scene still draws arms (0090 untouched).
"""
from __future__ import annotations

import inspect as _inspect


def _branch_targets(bundle):
    out = []
    for t in list(getattr(bundle, "targets", []) or []):
        meta = getattr(t, "metadata", None) or {}
        if str(meta.get("target_source", "")) == "branch_detector":
            out.append((t, meta))
    return out


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI import scene_builder as _sb

        src = _inspect.getsource(_sb)
    except Exception as exc:
        return True, [f"SKIP: scene_builder unavailable ({exc!r})"]
    if "lone_dead_end_arm" in src:
        notes.append("SOURCE = scene_builder gates the lone non-imaging arm's draw")
    else:
        notes.append("SOURCE the 0451 lone-dead-end gate is missing")
        ok = False

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
        mirror1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([mirror1])
        _sys, _rays, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
        branch = _branch_targets(bundle)
        if (
            len(branch) >= 1
            and all(bool(meta.get("draw_suppressed")) for _t, meta in branch)
            and all(bool(getattr(t, "is_detector", False)) for t, _m in branch)
        ):
            notes.append("REAL = the dead-end arm keeps its ray stop and draws no ring")
        else:
            notes.append(
                f"REAL dead-end arm wrong: n={len(branch)} "
                f"suppressed={[bool(m.get('draw_suppressed')) for _t, m in branch]}"
            )
            ok = False

        app.load_layout_by_name("az85")
        try:
            app._select_table_indices([1], focus_index=1)
        except Exception:
            app._select_table_row(1)
        app.add_beam_splitter_to_led(kind="plate")
        _s2, _r2, bundle2 = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
        branch2 = _branch_targets(bundle2)
        if len(branch2) > 1:
            if any(not bool(meta.get("draw_suppressed")) for _t, meta in branch2):
                notes.append("SPLIT = a real split still draws its arms (0090 untouched)")
            else:
                notes.append("SPLIT a real split lost every arm draw (0090 regression)")
                ok = False
        else:
            notes.append(f"SPLIT = skipped ({len(branch2)} branch detector(s) on the BS scene)")
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
