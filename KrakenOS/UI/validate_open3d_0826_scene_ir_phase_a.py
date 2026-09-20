"""Guard for bugs/0826 -- Phase A of the Scene IR: lower a scene to flat data, read it from nowhere.

``docs/design_scene_ir.md``. Step 2 of the earlier design stalled because nobody could find
the producer of the drawn geometry: one patch was inert, and wrapping both curve builders
plus every ``_compute_*_layout_geometry*`` showed none of them fire while twelve row actors
drew. You cannot re-point a consumer you cannot locate, so Phase A builds the thing that can
say what every consumer believes, and moves nothing.

Three properties this pins, each of which I got wrong on the first pass and which would each
have shipped a confident, precise, wrong number:

  * a fallback is NOT a derivation. An entity whose pose came from the authored snapshot must
    not also claim ``DERIVE_ROW_POSE``, and must WITHHOLD ``authored_center`` -- comparing a
    value with itself yields 0.0000 and reads as agreement.
  * ``compare_to_consumer`` must not pair across kinds. A surface entity and a body derived
    from it share a ``source_row``, and a body's centre is not its row's surface vertex;
    differencing them produced 132-480 mm of nonsense in the pose audit.
  * the ``frame`` tag must be honest. The design's invariant is "``to_world`` is always
    post-fold"; today it is not, because ``row_placement.world_pose`` does not fold. The tag
    makes the invariant CHECKABLE, and ``is_fully_post_fold()`` is expected FALSE until
    Phase D.

Checks (display-free except D, which drives two real scenes):
  A  lowering is pure -- the editor is unchanged, and re-lowering is identical;
  B  identity is (kind, label, ordinal) and duplicate labels get distinct ids;
  C  the frame tag is honest and the post-fold invariant reads FALSE today, on purpose;
  D  the real gate scenes lower, and the IR agrees with the prescription consumer;
  E  a fallback never claims a derivation and never reports a fake-zero authored delta;
  F  cycle detection names the WHOLE cycle, self-reference included;
  G  a dangling anchor is reported;
  H  compare_to_consumer does not cross kinds, and unpaired is never agreement.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0826_scene_ir_phase_a
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GATE_SCENES = ("attachment/machine_vision_ELS85.py", "attachment/om05a_folded.py")


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.scene_ir import (
        DERIVE_NONE,
        DERIVE_OUTPUT_PORT,
        FRAME_ALREADY_WORLD,
        FRAME_POST_FOLD,
        FRAME_STRAIGHT_EQUIVALENT,
        EntityIR,
        SceneIR,
        compare_to_consumer,
        detect_cycles,
        entity_id,
        lower,
    )

    # ---- B: identity ----------------------------------------------------------------------------
    ok(entity_id("surface", "air", 0) != entity_id("surface", "air", 1),
       "B1: the ordinal separates duplicate labels")
    ok(entity_id("surface", "air", 0) != entity_id("body", "air", 0),
       "B2: kind is part of the identity, so a body never collides with a surface")
    ok("(unnamed)" in entity_id("surface", "", 0),
       "B3: an empty label still yields a usable id rather than a bare ordinal")

    # ---- F: cycles ------------------------------------------------------------------------------
    two = detect_cycles({"a": "b", "b": "a"})
    ok(len(two) == 1 and sorted(two[0]) == ["a", "b"],
       f"F1: a two-body cycle is reported with BOTH members (got {two})")
    three = detect_cycles({"a": "b", "b": "c", "c": "a"})
    ok(len(three) == 1 and sorted(three[0]) == ["a", "b", "c"],
       f"F2: a three-body cycle names all three, not the node the walk noticed (got {three})")
    ok(detect_cycles({"a": "a"}) == [["a"]],
       "F3: self-reference is the degenerate cycle and is reported")
    ok(detect_cycles({"a": "b", "b": None}) == [],
       "F4: an acyclic chain reports nothing")
    deep = {f"n{i}": f"n{i+1}" for i in range(50)}
    deep["n50"] = None
    ok(detect_cycles(deep) == [],
       "F5: a 50-deep chain terminates and is clean -- no depth limit is imposed")

    # ---- H: cross-kind pairing --------------------------------------------------------------------
    surf = EntityIR(id="surface:x#0", kind="surface", to_world=np.eye(4),
                    frame=FRAME_STRAIGHT_EQUIVALENT, placement_space="sequential", source_row=3)
    body_tf = np.eye(4); body_tf[:3, 3] = [100.0, 0.0, 0.0]
    body = EntityIR(id="body:x#0", kind="body", to_world=body_tf,
                    frame=FRAME_ALREADY_WORLD, placement_space="promoted", source_row=3)
    ir = SceneIR(entities=(surf, body))
    default = compare_to_consumer(ir, {3: np.zeros(3)})
    ok([r["id"] for r in default] == ["surface:x#0"],
       f"H1: the default consumer comparison is surfaces only (got {[r['id'] for r in default]})")
    ok(default[0]["status"] == "agree",
       "H2: and the surface agrees with a consumer holding the same position")
    both = compare_to_consumer(ir, {3: np.zeros(3)}, kind=None)
    ok(len(both) == 2 and any(r["status"] == "DISAGREE" for r in both),
       "H3: kind=None opts in to both, and then the body's 100 mm shows as a disagreement")
    unp = compare_to_consumer(ir, {})
    ok(unp[0]["status"] == "unpaired" and unp[0]["delta_mm"] is None,
       "H4: an entity the consumer has no opinion on is UNPAIRED, never agreement")

    # ---- C + A + D + E: the real scenes -----------------------------------------------------------
    scenes = [PROJECT_ROOT / s for s in GATE_SCENES]
    missing = [s.name for s in scenes if not s.exists()]
    if missing:
        notes.append(f"SKIP: gate scenes absent (gitignored attachment): {missing}")
        passed = not any(n.startswith("FAIL") for n in notes)
        if verbose:
            for n in notes:
                print(n)
        return passed, notes

    editor = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        editor = KrakenLayoutEditor(headless=True)
        for scene in scenes:
            editor.layout_files["gate"] = scene
            editor.load_layout_by_name("gate")
            rows_before = [
                (float(r.desp_x), float(r.desp_y), float(r.desp_z)) for r in editor.rows
            ]
            ir = lower(editor)
            rows_after = [
                (float(r.desp_x), float(r.desp_y), float(r.desp_z)) for r in editor.rows
            ]
            name = scene.name

            # A: pure
            ok(rows_before == rows_after,
               f"A[{name}]: lowering left every row's desp untouched")
            again = lower(editor)
            ok(len(again.entities) == len(ir.entities)
               and all(np.allclose(a.to_world, b.to_world)
                       for a, b in zip(ir.entities, again.entities, strict=True)),
               f"A[{name}]: re-lowering is identical -- no hidden state accumulates")

            # C: the frame tag is honest
            ok(all(e.frame in (FRAME_POST_FOLD, FRAME_STRAIGHT_EQUIVALENT, FRAME_ALREADY_WORLD)
                   for e in ir.entities),
               f"C[{name}]: every entity declares a known frame")
            ok(ir.is_fully_post_fold() is False,
               f"C[{name}]: the post-fold invariant reads FALSE today -- Phase D is what "
               f"makes it true, and a guard that passed now would be measuring nothing")
            seq = [e for e in ir.of_kind("surface") if e.placement_space == "sequential"]
            ok(all(e.frame == FRAME_STRAIGHT_EQUIVALENT for e in seq),
               f"C[{name}]: every SEQUENTIAL surface is tagged straight_equivalent, never "
               f"post_fold -- world_pose does not fold")

            # D: the IR agrees with the consumer it was extracted from
            from KrakenOS.UI.services import row_placement as rp

            consumer = {i: rp.prescription_pose(editor, i).position
                        for i in range(len(editor.rows))}
            cmp = compare_to_consumer(ir, consumer)
            bad = [r for r in cmp if r["status"] != "agree"]
            ok(not bad,
               f"D[{name}]: all {len(cmp)} surface entities agree with the prescription "
               f"consumer (got {bad[:3]})")
            ok(len(ir.of_kind("surface")) == len(editor.rows),
               f"D[{name}]: one surface entity per row, none dropped silently")
            ok(len({e.id for e in ir.entities}) == len(ir.entities),
               f"D[{name}]: every entity id is unique")

            # E: a fallback is not a derivation
            for entity in ir.of_kind("body"):
                if entity.fallback is not None:
                    ok(entity.derivation == DERIVE_NONE,
                       f"E[{name}]: {entity.id} fell back, so it claims no derivation")
                    ok(entity.authored_center is None,
                       f"E[{name}]: {entity.id} withholds authored_center -- comparing a "
                       f"value with itself is not a check")
                else:
                    ok(entity.derivation != DERIVE_NONE,
                       f"E[{name}]: {entity.id} has a live pose, so it names its mechanism")
            derived = [e for e in ir.of_kind("body") if e.derivation == DERIVE_OUTPUT_PORT]
            if derived:
                worst = max(
                    float(np.linalg.norm(e.position - e.authored_center))
                    for e in derived if e.authored_center is not None
                )
                ok(worst < 1e-3,
                   f"D[{name}]: every output-port-derived body matches its authored "
                   f"snapshot (worst {worst:.4f} mm) -- the bugs/0750 healthy reading")
    except Exception as exc:  # pragma: no cover - defensive
        ok(False, f"driving the real scenes raised {exc!r}")
    finally:
        if editor is not None:
            try:
                editor.destroy()
            except Exception:
                pass

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0826 scene-IR phase-A validation PASSED")
        return 0
    print("0826 scene-IR phase-A validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
