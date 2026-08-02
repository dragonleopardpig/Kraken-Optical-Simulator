"""bugs/0512 -- a glued illumination source rides the LED/BS assembly.

flag_20260802_204536 ("dragged to BS, LED follows, but the Illumination source is
not followed"): the parametric emitter is a world-anchored spec, so the 0505
station slide and the 0508 B assembly drag moved the housing while the amber
source stayed behind. Fix: sources carry ``glued_to_led`` (new adds default True;
browser right-click toggles it), and every LED-motion chokepoint -- the atomic
station write's leg component, the perpendicular carry remainder, the
distance-dialog movers, the glue-restore -- shifts glued sources by the LED's
world delta via ``_carry_glued_scene_sources``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0512_source_glue_rides_led
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_150mm_test.py")


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    from KrakenOS.UI.scene_source_analysis import source_spec_bool, source_spec_vector
    from KrakenOS.UI.services.source_modeling import SourceModelingMixin

    # -- B: portable -- the carry helper on a minimal fake ------------------------------
    class _Fake:
        _normalize_scene_source_specs = SourceModelingMixin._normalize_scene_source_specs
        _carry_glued_scene_sources = SourceModelingMixin._carry_glued_scene_sources

        def __init__(self, specs):
            self.layout_scene_source_specs = specs

    fake = _Fake([
        {"source_id": "source:led-1", "glued_to_led": True, "source_x": 1.0, "source_y": 2.0, "source_z": 3.0},
        {"source_id": "source:free", "source_x": 10.0, "source_y": 0.0, "source_z": 0.0},
    ])
    moved = fake._carry_glued_scene_sources((5.0, -1.0, 2.0))
    specs = fake._normalize_scene_source_specs(fake.layout_scene_source_specs)
    glued_spec = next(s for s in specs if s["source_id"] == "source:led-1")
    free_spec = next(s for s in specs if s["source_id"] == "source:free")

    def origin(spec):
        return np.asarray(
            source_spec_vector(spec, ("origin",), ("source_x", "source_y", "source_z"), (0.0, 0.0, 0.0)),
            dtype=float,
        ).reshape(3)

    check(moved == 1 and np.allclose(origin(glued_spec), (6.0, 1.0, 5.0)), "B1: glued source shifts by the delta")
    check(np.allclose(origin(free_spec), (10.0, 0.0, 0.0)), "B2: a free-placed source stays put")
    check(
        source_spec_bool(glued_spec, "glued_to_led", False),
        "B3: normalization keeps the glue key (passthrough persistence)",
    )

    # -- A: the flagged workflow on the real scene (skip-if-absent) ---------------------
    if not SCENE.exists():
        notes.append("SKIP: the 150mm test scene is not checked out (gitignored attachment)")
        return ok, notes

    editor = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        editor = KrakenLayoutEditor()
        editor.layout_files["source_glue_probe"] = SCENE
        editor.load_layout_by_name("source_glue_probe")
        sid = editor.add_illumination_led_source()

        def live_spec():
            return next(
                s
                for s in editor._normalize_scene_source_specs(editor.layout_scene_source_specs)
                if s.get("source_id") == sid
            )

        check(
            source_spec_bool(live_spec(), "glued_to_led", False),
            "A1: a new Illumination Source (LED) is glued by default",
        )
        o0 = origin(live_spec())
        editor.translate_step_overlay("led", (7.0, 0.0, -4.0))
        check(
            np.allclose(origin(live_spec()) - o0, (7.0, 0.0, -4.0), atol=1e-6),
            "A2: an LED drag carries the glued source by the full delta",
        )
        editor.update_scene_source_spec(sid, {"glued_to_led": True})
        bs = editor._promoted_optical_solid_row_index("optical")
        if bs is not None:
            editor.set_optical_led_glue(True)  # the user's flagged workflow: glue, then drag the BS
            o1 = origin(live_spec())
            editor.translate_scene_row_pose_vector(bs, (5.0, 0.0, 0.0))
            check(
                np.allclose(origin(live_spec()) - o1, (5.0, 0.0, 0.0), atol=1e-6),
                "A3: the 0508 B BS assembly drag carries the glued source too",
            )
        editor.update_scene_source_spec(sid, {"glued_to_led": False})
        o2 = origin(live_spec())
        editor.translate_step_overlay("led", (3.0, 0.0, 0.0))
        check(
            np.allclose(origin(live_spec()), o2, atol=1e-9),
            "A4: an UNGLUED source stays put on an LED drag",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass

    return ok, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
