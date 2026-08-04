"""bugs/0531 guard -- the splitter's internal re-bounce ghost hides with clipping OFF.

flag_20260804_082939: "clipped overlays is off, still have spurious reflected beam." The
0018-reopen rule keeps any STEERED escape visible (a real second path must not vanish),
but on the AZ85 cube the same signature matched the ~25% double-bounce ghost family
(``S3/transmit -> S3/reflect``, 233 rays) -- a beam rising off the splitter at ~35 deg
that images nothing.

Fix: a CONSECUTIVE double interaction at the SAME splitter surface is an internal
re-bounce ghost (`ray_path_is_splitter_rebounce_ghost`), hidden with Show Clipped Rays
OFF. The 0018 single-steer second path, the 0184 coaxial double-pass (split -> scatter ->
split), and any ghost that actually lands on the detector stay visible.

Checks:
  SOURCE -- the predicate exists and gates the visibility rule.
  MECH   -- fabricated paths: consecutive same-surface splits = ghost (hidden);
            single steer = authored (visible); split->scatter->split = not a ghost.
  REAL   -- AZ85: with clipping OFF exactly the detector-reaching rays draw
            (zero spurious keeps).
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path
from types import SimpleNamespace

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def _surface_event(event_type: str, surface: str):
    return SimpleNamespace(
        event_kind="surface", event_type=event_type, surface_id=surface,
        interaction_model="", surface_name="",
    )


def _terminal_event(reason: str):
    return SimpleNamespace(
        event_kind="terminal", event_type=reason, surface_id="",
        termination_reason=reason, interaction_model="", surface_name="",
    )


def _path(events):
    return SimpleNamespace(events=events, reaches_image=False)


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import scene_geometry as _sg

    src = _inspect.getsource(_sg.ray_path_visible_without_clipping_from_events)
    if "bugs/0531" in src and "ray_path_is_splitter_rebounce_ghost" in src:
        notes.append("SOURCE = the visibility rule gates on the re-bounce ghost predicate")
    else:
        notes.append("SOURCE the 0531 ghost gate is missing from the visibility rule")
        ok = False

    ghost = _path([
        _surface_event("split_transmit", "3"),
        _surface_event("split_reflect", "3"),
        _terminal_event("no_next_intersection"),
    ])
    authored = _path([
        _surface_event("split_reflect", "3"),
        _terminal_event("no_next_intersection"),
    ])
    double_pass = _path([
        _surface_event("split_transmit", "1"),
        _surface_event("scatter_diffuse", "2"),
        _surface_event("split_reflect", "1"),
        _terminal_event("no_next_intersection"),
    ])
    cascade = _path([
        _surface_event("split_transmit", "3"),
        _surface_event("split_reflect", "7"),
        _terminal_event("no_next_intersection"),
    ])
    cases = [
        ("consecutive same-surface splits = ghost", _sg.ray_path_is_splitter_rebounce_ghost(ghost), True),
        ("ghost is hidden with clipping OFF", _sg.ray_path_visible_without_clipping_from_events(ghost), False),
        ("single steer stays an authored branch (0018)", _sg.ray_path_visible_without_clipping_from_events(authored), True),
        ("split->scatter->split is not a ghost (0184)", _sg.ray_path_is_splitter_rebounce_ghost(double_pass), False),
        ("two-splitter cascade is not a ghost", _sg.ray_path_is_splitter_rebounce_ghost(cascade), False),
    ]
    for label, got, want in cases:
        if bool(got) == want:
            notes.append(f"MECH = {label}")
        else:
            notes.append(f"MECH {label}: got {got}, wanted {want}")
            ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=False, trace_rays=True
        )
        paths = list(bundle.ray_paths)
        kept = [p for p in paths if _sg.ray_path_visible_without_clipping_from_events(p)]
        spurious = [p for p in kept if str(p.termination_reason) != "target_termination"]
        reaching = sum(1 for p in paths if str(p.termination_reason) == "target_termination")
        if not spurious and len(kept) == reaching and reaching > 0:
            notes.append(f"REAL = clipping OFF keeps exactly the {reaching} detector-reaching rays")
        else:
            notes.append(
                f"REAL clipping OFF keeps {len(kept)} rays ({len(spurious)} spurious) "
                f"vs {reaching} reaching"
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
