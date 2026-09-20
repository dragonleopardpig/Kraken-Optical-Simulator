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
  E  a fallback never claims a derivation and never reports a fake-zero authored delta,
     and the ELS85 not-reconstructible finding is pinned against a circular 'fix';
  F  cycle detection names the WHOLE cycle, self-reference included;
  G  a dangling anchor is reported;
  H  compare_to_consumer does not cross kinds, and unpaired is never agreement;
  I  only DELIBERATELY converted consumers import the IR, and every listed conversion
     is real -- Phase C relaxes read-from-nowhere one consumer at a time without
     discarding the protection;
  J  scene_ir.world_frame is a byte-identical drop-in for row_placement.world_frame,
     including returning None for a row carrying no tilts.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0826_scene_ir_phase_a
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GATE_SCENES = ("attachment/machine_vision_ELS85.py", "attachment/om05a_folded.py")

#: Phase C converts consumers ONE PER COMMIT. This list is the record of which are
#: deliberate; anything else importing the IR is an accidental wiring and fails I1.
#: Keeping it explicit is what lets the read-from-nowhere protection survive Phase C
#: instead of being deleted the moment the first consumer lands.
PHASE_C_CONVERTED = (
    "KrakenOS/UI/services/geometric_analysis.py",
    "KrakenOS/UI/services/three_d_scene_tools.py",
)


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

    # ---- I: read from nowhere --------------------------------------------------------------------
    # Phase A's whole safety argument is that it changes nothing, which holds only while no
    # APP code consumes it. A later commit wiring it into a service would silently end that
    # without any test noticing -- so the invariant is enforced here rather than trusted.
    # Phase C is when this check is deliberately relaxed, one consumer at a time.
    consumers = []
    for path in sorted(PROJECT_ROOT.glob("KrakenOS/**/*.py")) + sorted(PROJECT_ROOT.glob("tools/**/*.py")):
        if path.name == "scene_ir.py":
            continue
        try:
            if "scene_ir" not in path.read_text(encoding="utf-8"):
                continue
        except Exception:
            continue
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if path.name.startswith("validate_") or rel.startswith("tools/"):
            continue
        consumers.append(rel)
    unexpected = sorted(set(consumers) - set(PHASE_C_CONVERTED))
    ok(not unexpected,
       f"I1: only DELIBERATELY converted consumers import the IR (unexpected: {unexpected})")
    missing = sorted(set(PHASE_C_CONVERTED) - set(consumers))
    ok(not missing,
       f"I2: every listed conversion is real -- a stale entry would hide an accidental "
       f"wiring behind it (listed but not importing: {missing})")

    # ---- J: the world_frame drop-in ---------------------------------------------------------
    from KrakenOS.UI.services import scene_ir as _sir

    _no_rot = EntityIR(id="surface:n#0", kind="surface", to_world=np.eye(4),
                       frame=FRAME_STRAIGHT_EQUIVALENT, placement_space="sequential",
                       source_row=0, has_orientation=False)
    _rot = np.eye(4); _rot[:3, :3] = np.diag([1.0, -1.0, -1.0])
    _has_rot = EntityIR(id="surface:r#0", kind="surface", to_world=_rot,
                        frame=FRAME_STRAIGHT_EQUIVALENT, placement_space="world",
                        source_row=1, has_orientation=True)
    _ir = SceneIR(entities=(_no_rot, _has_rot))
    _p, _r, _s = _sir.world_frame(None, 0, scene_ir=_ir)
    ok(_r is None,
       "J1: a row carrying no tilts returns rotation=None, not a stored identity -- the "
       "conflation bugs/0556 made when it hardcoded (0,0,1) for a flipped sensor")
    ok(_s == "sequential", "J2: and its placement space is carried through")
    _p2, _r2, _s2 = _sir.world_frame(None, 1, scene_ir=_ir)
    ok(_r2 is not None and np.allclose(_r2, np.diag([1.0, -1.0, -1.0])),
       "J3: a row WITH orientation returns the real rotation")
    ok(_s2 == "world", "J4: and its space too")
    try:
        _sir.world_frame(None, 99, scene_ir=_ir)
        _raised = False
    except IndexError:
        _raised = True
    ok(_raised, "J5: a row the IR has no entity for raises rather than returning a default")

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
            # E2 (Phase B): the ELS85 negative result is PINNED. cw - po equals
            # R @ (0,0,half_z) for the station-neutral solid and not for the 45-degree
            # plate, and even where it holds it reconstructs one AUTHORED value from
            # another -- circular. A later "fix" that derives from authored metadata alone
            # must fail here rather than quietly re-introducing that.
            if name == "machine_vision_ELS85.py":
                anchor_warnings = [f for f in ir.findings
                                   if f.code == "scene_ir.anchor_not_reconstructible"]
                ok(len(anchor_warnings) == 2,
                   f"E2[{name}]: both anchor='row_pose' bodies report unreconstructible "
                   f"(got {len(anchor_warnings)})")
                ok(all("circular" in f.detail for f in anchor_warnings),
                   "E2: the warning states WHY -- reconstructing one authored value from "
                   "another is circular, not merely unavailable")
                ok(all(e.derivation == DERIVE_NONE and e.authored_center is None
                       for e in ir.of_kind("body")),
                   "E2: no ELS85 body claims a derivation or offers an authored check value")

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
