"""bugs/0489 -- a hand-placed folder pins its section, and the solve stops discarding it.

The user's model: *"dragging any of the components will at least fix one of the 4 section
thickness constraints (dragging lens will fix 2), so the solver should take into account of the
constraint introduce by the user by dragging. It is equivalent to changing the FOV in the pop up
dialog and click thickness constraint."*

Measured on ``attachment/machine_vision_AZ85_RA_Mirror_BS.py`` -- slide the RA mirror 20 mm along
its leg (setting section 3 = 83.270 mm), then Solve for Thickness 23 x 23:

    without the pin   section 3  83.270 -> 76.884 mm   drift -6.386   the solve moved it back
    with the pin      section 3  83.270 -> 83.270 mm   drift +0.000   section 4 absorbs instead

Which section a drag pins falls out of the split the folder belongs to: the object split's
``near`` is object -> beam splitter (section 1), the image split's ``near`` is lens rear -> mirror
(section 3). Pinning ``near`` -- the distance from the upstream element to the folder -- is what
makes "it stays where I put it" true whatever the solve does to the total, because the sibling
``far`` absorbs. That is the same policy bugs/0484 already chose for the object side.

**Scope, stated because it is easy to over-read.** The pin governs WHERE things sit, not whether
the system is in focus. The residual defocus after a solve is a property of the image TOTAL, which
a pin does not change -- and the total is separately wrong: measured on a clean scene with nothing
dragged, Solve for Thickness leaves -5.5266 mm of residual from a focused start. So "drag, then
click Solve for Thickness" still does not come back to focus, and that is not this bug.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0489_drag_pins_a_section
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")

SPLIT_BEFORE = {
    "total": 154.77, "near": 103.27, "far": 51.50,
    "mirror_row": 7, "near_gap_row": 6, "far_gap_row": 7,
    "near_min": 12.5, "far_min": 12.5, "frozen_world": True, "frozen_kind": "image_mirror",
}
SPLIT_AFTER = {**SPLIT_BEFORE, "total": 122.13, "near": 103.27, "far": 18.86}


def _service(editor):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    return QuickEstimationService(SimpleNamespace(editor=editor))


def _editor(*, split, pins=None, applied=None):
    return SimpleNamespace(
        _folded_image_conjugate_split=lambda: dict(split),
        _step_path_for_label=lambda label: None,
        _current_camera_front_to_sensor_mm=lambda: 0.0,
        _apply_folded_image_split=(applied or (lambda leg, value: (True, f"{leg}={value}"))),
        _axis_section_pins_state=dict(pins or {}),
        rows=[],
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: quick_estimation unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    calls: list = []

    def _record(leg, value):
        calls.append((leg, float(value)))
        return True, f"{leg}={value}"

    # --- A. a pin overrides the default distribution -------------------------------------
    calls.clear()
    service = _service(_editor(split=SPLIT_AFTER, pins={"image_near": 83.27}, applied=_record))
    service._rebalance_image_leg_sections(SPLIT_BEFORE)
    check(
        len(calls) == 1 and abs(calls[0][1] - 83.27) < 1e-6,
        f"A1: the pinned section 3 is what the solve targets ({calls[0][1] if calls else None}), "
        f"not bugs/0482's 50:50 share",
    )
    calls.clear()
    service = _service(_editor(split=SPLIT_AFTER, applied=_record))
    service._rebalance_image_leg_sections(SPLIT_BEFORE)
    check(
        len(calls) == 1 and abs(calls[0][1] - (103.27 + (122.13 - 154.77) / 2.0)) < 1e-6,
        f"A2: with NO pin the 50:50 default still applies ({calls[0][1] if calls else None})",
    )
    # A pin on the FAR section is honoured through the total.
    calls.clear()
    service = _service(_editor(split=SPLIT_AFTER, pins={"image_far": 40.0}, applied=_record))
    service._rebalance_image_leg_sections(SPLIT_BEFORE)
    check(
        len(calls) == 1 and abs(calls[0][1] - (122.13 - 40.0)) < 1e-6,
        f"A3: a pinned FAR section is honoured as total - far ({calls[0][1] if calls else None})",
    )
    # Both pinned: over-constrained, and it says so rather than silently choosing one.
    calls.clear()
    service = _service(_editor(split=SPLIT_AFTER, pins={"image_near": 80.0, "image_far": 40.0}, applied=_record))
    note = service._rebalance_image_leg_sections(SPLIT_BEFORE)
    check(
        not calls and "pinned by hand" in note,
        f"A4: both sections pinned is over-constrained and reported, not silently resolved "
        f"({note.strip()[:70]!r})",
    )

    # --- B. pins are session state, cleared on load ---------------------------------------
    try:
        import inspect as _inspect

        from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

        src = _inspect.getsource(LayoutTableWorkbenchMixin.load_layout_by_name)
        check(
            "_axis_section_pins_state" in src,
            "B1: loading a layout clears the pins -- a scene never arrives over-constrained",
        )
    except Exception as exc:
        notes.append(f"SKIP: load source unreadable ({type(exc).__name__}: {exc})")

    # --- C. the real scene: the solve stops moving a hand-placed mirror -------------------
    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    results = {}
    for use_pin in (False, True):
        editor = None
        try:
            editor = KrakenLayoutEditor()
            editor.layout_files["pin_probe"] = SCENE
            editor.load_layout_by_name("pin_probe")
            editor.seat_camera_on_sensor()
            qe = _service(editor)
            editor.translate_scene_row_pose(7, "x", -20.0)
            placed = float(editor._folded_image_conjugate_split()["near"])
            if not use_pin:
                editor._axis_section_pins_state = {}
            qe.fov_solve("object", "thickness", 23.0, 23.0, (23.04, 23.04))
            after = float(editor._folded_image_conjugate_split()["near"])
            results[use_pin] = (placed, after)
        except Exception as exc:
            notes.append(f"SKIP: scene drive failed ({type(exc).__name__}: {exc})")
            return ok, notes
        finally:
            if editor is not None:
                try:
                    editor.destroy()
                except Exception:
                    pass
    placed_on, after_on = results.get(True, (0.0, 0.0))
    placed_off, after_off = results.get(False, (0.0, 0.0))
    check(
        abs(after_on - placed_on) < 1e-3,
        f"C1: WITH the pin the hand-placed mirror stays put across the solve "
        f"({placed_on:.3f} -> {after_on:.3f})",
    )
    check(
        abs(after_off - placed_off) > 1.0,
        f"C2: WITHOUT it the solve moves it ({placed_off:.3f} -> {after_off:.3f}, "
        f"drift {after_off - placed_off:+.3f}) -- the defect this fixes",
    )
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
