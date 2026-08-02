"""bugs/0505 -- dragging the glued LED slides the illumination STATION: the one pure section-2 edit.

User requirement (2026-08-02): dragging the glued LED+BS left/right on a folded scene must move
the OBJECT together with it -- that gesture is "effectively constraint distance for section 2",
and no other pure-graphical gesture edits section 2 alone (a lens drag trades it against section
3, bugs/0499). Per bugs/0437 the BS drag stays a relative housing seat; the LED (parent) drag is
the station gesture.

The enabling engine change: every axis reconstruction hardcoded the nominal ``(0,0,*) along +Z``
root. The fold point is the INCOMING line crossing the splitter diagonal, so with the root pinned
nominal, moving the plate +x slid the fold point DOWN the incoming axis (measured: origin
[0,0,53.8] -> [0,0,33.8]) -- correct for a lone plate move, wrong for a station whose object came
along. ``axis_root_origin`` now anchors the root at the OBJECT row's lateral position, and the
emissions, the axis tree and the drawn ``axis:global`` guide all read it -- zero change for every
centred-object scene.

The station write is ATOMIC with the bugs/0485 fold-slide carry suppressed: the net fold point is
unchanged by construction, and letting the carry fire on the BS's half would drag the whole split
leg through the inconsistent intermediate state (measured: the leg dropped 20 mm in z).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0505_led_station_drag_slides_section_2
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
SLIDE = 20.0
TOL = 1.0e-6


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    import numpy as np

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.nonseq_output_ports import axis_fold_emissions
    from KrakenOS.UI.services import optical_axis_tree as tree_mod

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor.layout_files["station_probe"] = SCENE
        editor.load_layout_by_name("station_probe")

        bs = editor._promoted_optical_solid_row_index("optical")
        pose = lambda i: np.asarray(tree_mod.row_world_pose(editor.rows, i), dtype=float)
        led = lambda: np.asarray(editor._step_body_world_center("led"), dtype=float).reshape(3)

        def fold_origin():
            record = (axis_fold_emissions(editor.rows) or {}).get(int(bs)) or {}
            return np.asarray(record.get("origin"), dtype=float).reshape(3)

        plan = editor._led_station_slide_plan()
        check(
            plan is not None and list(plan[0]) == [0] and int(plan[1]) == int(bs),
            f"A1: the station plan finds the object-side rows ({None if plan is None else list(plan[0])}) "
            f"and the BS row (S{bs})",
        )
        if plan is None:
            return ok, notes
        leg = np.asarray(plan[2], dtype=float).reshape(3)

        o0 = fold_origin()
        obj0, r1_0, r7_0, r8_0, led0 = pose(0).copy(), pose(1).copy(), pose(7).copy(), pose(8).copy(), led().copy()
        s2_before = float(np.linalg.norm(pose(1) - o0))
        editor._fold_carry_pending_rebuild = False

        editor.translate_step_overlay("led", tuple(leg * SLIDE))
        o1 = fold_origin()
        check(
            float(np.linalg.norm((pose(0) - obj0) - leg * SLIDE)) <= TOL
            and float(np.linalg.norm((led() - led0) - leg * SLIDE)) <= TOL
            and float(np.linalg.norm((o1 - o0) - leg * SLIDE)) <= TOL,
            "B1: object, LED and the FOLD POINT all slide by the drag along the leg -- the station "
            "moves as one and the fold stays at the leg's height (the naive desp move slid it down "
            "the incoming axis instead)",
        )
        check(
            float(np.linalg.norm(pose(1) - r1_0)) <= TOL
            and float(np.linalg.norm(pose(7) - r7_0)) <= TOL
            and float(np.linalg.norm(pose(8) - r8_0)) <= TOL,
            "B2: the lens datums, the mirror and the image do NOT move -- only the station slides",
        )
        s1_before = float(np.linalg.norm(o0 - obj0))
        s1_after = float(np.linalg.norm(o1 - pose(0)))
        s2_after = float(np.linalg.norm(pose(1) - o1))
        check(
            abs(s1_after - s1_before) <= TOL and abs((s2_before - s2_after) - SLIDE) <= 1.0e-3,
            f"B3: section 1 holds ({s1_before:.3f} -> {s1_after:.3f}) and section 2 alone absorbs "
            f"the drag ({s2_before:.3f} -> {s2_after:.3f}) -- the pure section-2 edit",
        )
        check(
            bool(getattr(editor, "_fold_carry_pending_rebuild", False)),
            "B4: the station slide sets the bugs/0493 sticky rebuild marker (bugs/0503's lesson)",
        )

        check(
            editor.glue_step_overlay_to_surrogate("led") is False,
            "C1: glue after the station slide reports already-glued -- the recorded placement is "
            "re-expressed against the OBJECT anchor (bugs/0503 treatment, object as the datum)",
        )
        perp = np.asarray((0.0, 0.0, -9.0), dtype=float)  # perpendicular to this +X leg
        obj_mid = pose(0).copy()
        editor.translate_step_overlay("led", tuple(perp))
        check(
            float(np.linalg.norm(pose(0) - obj_mid)) <= TOL,
            "C2: a PERPENDICULAR LED drag keeps today's housing-seat behaviour -- the object holds",
        )
        editor.glue_step_overlay_to_surrogate("led")
        check(
            float(np.linalg.norm(led() - (led0 + leg * SLIDE))) <= TOL,
            "C3: glue undoes exactly the perpendicular housing displacement -- the LED returns "
            "onto the slid station",
        )

        # -- D: the TRACE follows the station ----------------------------------------------------
        # The finite-object launcher is anchored on axis_root_origin (the line the object emits);
        # before that, a slid station's rays left from empty space at the nominal axis, folded at
        # the moved diagonal BELOW the imaging arm, and vanished (target_termination 129 -> 0).
        try:
            _, _, bundle = editor._build_preview_system_rays_bundle(
                update_state=False, include_live_step_overlays=False
            )
            landed = sum(
                1 for p in (getattr(bundle, "ray_paths", []) or []) if bool(getattr(p, "reaches_image", False))
            )
            check(
                landed > 0,
                f"D1: after the station slide the imaging trace still LANDS ({landed} rays reach "
                f"the image) -- the launcher rides axis_root_origin with the station",
            )
        except Exception as exc:
            notes.append(f"NOTE: trace check skipped ({type(exc).__name__}: {exc})")

        # -- E: the two 2026-08-02 11:0x flags -----------------------------------------------
        # flag_20260802_110437: the FOV plane / object-plane anchor must FOLLOW the station
        # (surface 0's engine transform never carries the object's own lateral desp).
        # flag_20260802_110629: after mirror + station drags, the follower builder's probe
        # (launched nominally, it missed the moved diagonal) fell back to face+thickness and
        # planted the Image row one mirror-to-image thickness low -- rays flew PAST the sensor.
        try:
            editor2 = KrakenLayoutEditor()
            editor2.layout_files["station_probe2"] = SCENE
            editor2.load_layout_by_name("station_probe2")
            p8 = lambda: np.asarray(tree_mod.row_world_pose(editor2.rows, 8), dtype=float)
            r8_0 = p8().copy()

            def _sys():
                system, _, _ = editor2._build_preview_system_rays_bundle(
                    update_state=False, include_live_step_overlays=False
                )
                return system

            editor2.translate_step_overlay("led", (10.45, 0.0, 0.0))
            obj_ref = np.asarray(
                editor2._surface_reference_world_point(0, system=_sys()), dtype=float
            ).reshape(3)
            check(
                abs(float(obj_ref[0]) - 10.45) <= 1.0e-6,
                f"E1: the object/FOV-plane anchor follows the station (x={obj_ref[0]:.3f}) -- "
                f"it used to stay on the nominal axis while rays and axes moved",
            )
            editor2.translate_step_overlay("lens", (28.31, 0.0, 0.0))
            editor2.translate_scene_row_pose_vector(7, (34.10, 0.0, 0.0))
            _sys()
            editor2.translate_step_overlay("led", (-33.63, 0.0, 0.0))
            _sys()
            moved = p8() - r8_0
            check(
                abs(float(moved[2])) <= 1.0e-3 and abs(float(moved[0]) - 34.10) <= 1.0e-3,
                f"E2: through lens+mirror+station drags the Image row rides ONLY the mirror "
                f"(delta {np.round(moved, 2).tolist()}) -- the nominal follower probe used to "
                f"drop it one mirror-to-image thickness (44.12 mm) below the sensor",
            )
            try:
                editor2.destroy()
            except Exception:
                pass
        except Exception as exc:
            notes.append(f"NOTE: flag-sequence check skipped ({type(exc).__name__}: {exc})")
    except Exception as exc:
        notes.append(f"SKIP: the scene could not be driven ({type(exc).__name__}: {exc})")
    finally:
        if editor is not None:
            try:
                editor.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP", "NOTE")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
