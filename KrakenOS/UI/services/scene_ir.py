"""bugs/0826 -- Phase A of ``docs/design_scene_ir.md``: lower a scene to flat data.

READ FROM NOWHERE. Nothing in the app imports this yet; it exists so the audits can
compare the IR's answer against each consumer's, which is the instrument no previous
attempt had. Step 2 of the earlier design stalled because nobody could find the producer
of the drawn geometry -- three sites eliminated by measurement. You cannot re-point a
consumer you cannot locate, so first you build the thing that can say what every consumer
believes, and only then start moving them.

Phase A must change no behaviour, and Phase B must reproduce TODAY including today's bugs.
So `to_world` here is whatever the current code produces, and every entity says which
frame that actually is. It is NOT yet post-fold for a sequential row, because
``row_placement.world_pose`` does not fold -- that is Phase D, the only phase that changes
physics.

That honesty is load-bearing. The design's invariant is "``to_world`` is always post-fold";
an implementation that silently shipped a straight-equivalent under that name would be the
exact defect the invariant exists to prevent. The ``frame`` tag makes the invariant
CHECKABLE instead of aspirational: a guard can assert the IR is fully post-fold, and that
assertion is red until Phase D lands, on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

#: ``to_world`` is a real world pose: the fold has been applied. The design's goal state.
FRAME_POST_FOLD = "post_fold"
#: ``to_world`` is the straight-equivalent chain pose, fold NOT applied. What a SEQUENTIAL
#: row produces today, and never an answer to "where is it" (bugs/0593).
FRAME_STRAIGHT_EQUIVALENT = "straight_equivalent"
#: The row's own numbers are already absolute and already folded (the 0433 freeze / axis
#: snap), so there is nothing to apply.
FRAME_ALREADY_WORLD = "already_world"

#: How a body's pose was derived. There is not one mechanism in the wild, there are two,
#: and they are differently shaped -- surfacing that is a Phase A result, not a detail.
DERIVE_OUTPUT_PORT = "output-port chain"   # om05a: a solid's exit frame re-frames downstream
DERIVE_ROW_POSE = "row pose + datum"       # ELS85: ScenePlacement.anchor='row_pose'
DERIVE_NONE = "not derived"


@dataclass(frozen=True)
class EntityIR:
    """One thing in the scene, as plain data.

    ``to_world`` is a ``(4, 4)`` homogeneous transform. ``frame`` says what that transform
    actually is -- never assume it is post-fold, ask.
    """

    id: str
    kind: str                       # "surface" | "body"
    to_world: np.ndarray
    frame: str
    placement_space: str            # row_placement.SEQUENTIAL / WORLD
    source_row: int | None = None
    label: str = ""
    derived_from: str | None = None     # provenance: the anchor entity's id
    derivation: str = DERIVE_NONE
    datum_delta: np.ndarray | None = None
    authored_center: np.ndarray | None = None   # the promotion snapshot: a CHECK value
    fallback: str | None = None
    #: True when the source row carried tilts. The IR stores identity in ``to_world`` when
    #: it did not, and identity is indistinguishable from a real identity rotation -- while
    #: ``row_placement.world_frame`` returns None there. A consumer that derives a normal
    #: from a rotation behaves differently on None than on identity (bugs/0556 hardcoded
    #: (0,0,1) for a flipped sensor by making exactly that conflation), so the distinction
    #: is carried explicitly rather than inferred back out of the matrix.
    has_orientation: bool = False

    @property
    def position(self) -> np.ndarray:
        return np.asarray(self.to_world, dtype=float)[:3, 3]


@dataclass(frozen=True)
class SceneIR:
    entities: tuple[EntityIR, ...]
    provenance: dict = field(default_factory=dict)
    findings: tuple = ()

    def by_id(self, entity_id: str) -> EntityIR | None:
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None

    def of_kind(self, kind: str) -> tuple[EntityIR, ...]:
        return tuple(e for e in self.entities if e.kind == kind)

    def is_fully_post_fold(self) -> bool:
        """The design's invariant. Red until Phase D, deliberately."""
        return all(e.frame in (FRAME_POST_FOLD, FRAME_ALREADY_WORLD) for e in self.entities)


def _matrix(position, rotation=None) -> np.ndarray:
    out = np.eye(4, dtype=float)
    out[:3, 3] = np.asarray(position, dtype=float).reshape(3)
    if rotation is not None:
        r = np.asarray(rotation, dtype=float)
        if r.shape == (3, 3) and np.all(np.isfinite(r)):
            out[:3, :3] = r
    return out


def entity_id(kind: str, label: str, ordinal: int) -> str:
    """``(kind, label, ordinal)`` -- the decided scheme.

    A label alone is not unique: ELS85 carries 'Promoted OPTICAL STEP optical solid' twice
    in nine rows and om05a_folded carries 'air' twice in twenty-five, so the ordinal among
    same-``(kind, label)`` entities is required rather than defensive.
    """
    return f"{kind}:{label or '(unnamed)'}#{int(ordinal)}"


def _assign_ids(kind: str, labels: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for label in labels:
        ordinal = seen.get(label, 0)
        seen[label] = ordinal + 1
        out.append(entity_id(kind, label, ordinal))
    return out


def detect_cycles(edges: dict[str, str | None]) -> list[list[str]]:
    """Every cycle in a child -> parent map, as lists of entity ids.

    Reports the WHOLE cycle rather than the node the walk happened to notice, because a
    warning that names one member of a three-body cycle sends the reader to the wrong
    place. Self-reference is the degenerate case and is reported the same way.
    """
    cycles: list[list[str]] = []
    seen: set[str] = set()
    for start in edges:
        if start in seen:
            continue
        path: list[str] = []
        node: str | None = start
        local: dict[str, int] = {}
        while node is not None and node in edges:
            if node in local:
                cycle = path[local[node]:]
                if cycle and sorted(cycle) not in [sorted(c) for c in cycles]:
                    cycles.append(cycle)
                break
            if node in seen:
                break
            local[node] = len(path)
            path.append(node)
            node = edges.get(node)
        seen.update(path)
    return cycles


def lower(editor: Any, *, bodies: bool = True) -> SceneIR:
    """Lower a live editor to flat data. Pure and read-only: changes nothing.

    ``bodies=False`` lowers surfaces ONLY. Body lowering runs the output-port pose walk and
    the promotion scrape, which is real work a caller asking "where is row N" never needs --
    and more than work: measured, it reaches editor attributes that a partially-constructed
    editor answers with unbounded ``tkinter.__getattr__`` recursion, so making every
    ``world_frame`` call lower bodies turned a cheap single-row read into a RecursionError
    (caught by bugs/0546's swap guard during Phase C).
    """
    from KrakenOS.UI.services import row_placement as rp
    from KrakenOS.UI.services.result_diagnostics import NO_REMEDY, WARNING, Finding

    # ``rows`` is a REQUIRED attribute, so getattr is safe here. Do not copy this shape
    # for an OPTIONAL one: the editor is a tk.Tk subclass and tkinter's __getattr__
    # recurses on an unknown name rather than raising, so the default never applies.
    rows = list(getattr(editor, "rows", []) or [])
    findings: list = []

    labels = [str(getattr(r, "name", "") or getattr(r, "surface", "") or "") for r in rows]
    surface_ids = _assign_ids("surface", labels)
    # bugs/0826 Phase D: resolved ONCE for the whole walk -- per row it would be quadratic.
    port_overrides = _output_port_overrides(editor)

    entities: list[EntityIR] = []
    for index, row in enumerate(rows):
        try:
            # rp.world_pose, NOT rp.prescription_pose. world_pose's own docstring calls it
            # "**The** resolver"; prescription_pose is the lower-level function behind it.
            # Reading the public one matters beyond tidiness: bugs/0572's guard stubs
            # row_placement.world_pose to drive the method with a probe object, and reaching
            # past it to prescription_pose bypassed the stub and hit the real resolver, which
            # needs a full editor. Phase C turned that into a silent None -- the caller's
            # "unbounded leg" signal -- so a lens could be told it had room to slide into a
            # fold mirror. Read the public resolver and the seam stays a seam.
            pose = rp.world_pose(editor, index)
            rotation = rp.rotation_matrix(row)
        except Exception as exc:
            findings.append(Finding(
                code="scene_ir.unlowerable_row",
                severity=WARNING,
                summary=f"row {index} has no readable pose",
                detail=f"{labels[index]!r}: {exc!r}",
                remedy="The IR cannot describe this row; every consumer comparison for it "
                       "is blind until the row's numbers can be read.",
            ))
            continue
        space = pose.space
        # bugs/0826 Phase D: the fold is resolved HERE, so to_world is a real world pose.
        position, rotation, frame = _post_fold_surface_pose(
            editor, index, pose, rotation, overrides=port_overrides
        )
        entities.append(EntityIR(
            id=surface_ids[index],
            kind="surface",
            to_world=_matrix(position, rotation),
            frame=frame,
            placement_space=space,
            source_row=index,
            label=labels[index],
            has_orientation=rotation is not None,
        ))

    if bodies:
        entities.extend(_lower_bodies(editor, rows, labels, surface_ids, findings))

    edges = {e.id: e.derived_from for e in entities if e.derived_from is not None}
    for cycle in detect_cycles(edges):
        findings.append(Finding(
            code="scene_ir.derivation_cycle",
            severity=WARNING,
            summary=f"{len(cycle)} entities form a derivation cycle",
            detail=" -> ".join(cycle + [cycle[0]]),
            remedy="Re-seat one of these bodies against a surface row. Until then they fall "
                   "back to their authored snapshot and their poses may be stale.",
        ))
        cycled = set(cycle)
        entities = [
            replace(e, derived_from=None, fallback="authored snapshot (cycle)")
            if e.id in cycled else e
            for e in entities
        ]

    known = {e.id for e in entities}
    for entity in entities:
        if entity.derived_from is not None and entity.derived_from not in known:
            findings.append(Finding(
                code="scene_ir.dangling_anchor",
                severity=WARNING,
                summary=f"{entity.id} names an anchor that does not exist",
                detail=f"anchor {entity.derived_from!r}",
                remedy=NO_REMEDY if entity.authored_center is None else
                       "Falling back to the authored snapshot; re-seat the body to fix it.",
            ))

    return SceneIR(
        entities=tuple(entities),
        provenance={
            "rows": len(rows),
            # NOT getattr: the editor is a tk.Tk subclass, and tkinter's Misc.__getattr__
            # answers an unknown name with getattr(self.tk, name), which RECURSES instead of
            # raising AttributeError -- so getattr's default never applies and a probe for a
            # name the editor happens not to carry dies with RecursionError. bugs/0546's swap
            # guard caught exactly that during Phase C. Read the instance dict directly.
            "scene": str(editor.__dict__.get("current_layout_name", "") or ""),
            "lowering": "phase-A",
        },
        findings=tuple(findings),
    )


def _lower_bodies(editor, rows, labels, surface_ids, findings) -> list[EntityIR]:
    """Promoted bodies, by whichever mechanism the scene actually uses.

    Measured across the gate scenes, the metadata is NOT uniform:

        machine_vision_ELS85.py   3 rows declare ScenePlacement.anchor='row_pose',
                                  2 carry StepOverlayPromotion.placement_offset_xyz
        om05a_folded.py           NO anchors and NO placement offsets at all --
                                  yet its 11 promoted bodies resolve at 0.0000 mm
                                  through the output-port pose graph

    So there are two derivation mechanisms in the wild and they are differently shaped.
    Surfacing that is a Phase A result: a design that assumed one uniform ``derived_from``
    would have been wrong on half the gate set, and nothing before the IR could see it.
    """
    from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides
    from KrakenOS.UI.services.scene_placement_audit import _promoted_center

    try:
        walked = optical_solid_output_port_pose_overrides(None, rows) or {}
    except Exception as exc:
        findings.append(_body_walk_failed(exc))
        walked = {}

    body_rows = [i for i, r in enumerate(rows) if _promoted_center(r) is not None]
    body_ids = _assign_ids("body", [labels[i] for i in body_rows])

    out: list[EntityIR] = []
    for body_id, index in zip(body_ids, body_rows, strict=True):
        row = rows[index]
        authored = _promoted_center(row)
        advanced = row.advanced if isinstance(getattr(row, "advanced", None), dict) else {}
        promo = advanced.get("StepOverlayPromotion") or {}
        placement = advanced.get("ScenePlacement") or {}

        pose = walked.get(index)
        centre = None
        if isinstance(pose, dict) and pose.get("center") is not None:
            try:
                centre = np.asarray(pose["center"], dtype=float).reshape(3)
            except (TypeError, ValueError):
                centre = None

        datum, derivation, anchor, fallback = None, DERIVE_NONE, None, None
        if centre is not None:
            derivation, anchor = DERIVE_OUTPUT_PORT, surface_ids[index]
        elif str(placement.get("anchor", "")) == "row_pose":
            # The scene DECLARES this mode, but Phase A cannot reconstruct it. Measured on
            # ELS85 row 6: center_world (6.295, 0, 47.615) is not the row pose (-0.12, 0,
            # 54.46) plus placement_offset_xyz (6.295, 0, 9.926) -- that would give
            # (6.17, 0, 64.39). placement_offset_xyz's z equals bounds_min_world's z, so it
            # is not a datum delta from the row at all. Saying DERIVE_ROW_POSE here would
            # label a derivation that did not happen.
            raw = promo.get("placement_offset_xyz")
            if raw is not None:
                try:
                    datum = np.asarray(raw, dtype=float).reshape(3)
                except (TypeError, ValueError):
                    datum = None
            findings.append(_anchor_not_reconstructible(body_id, index))

        if centre is None:
            # NOT a derivation. The authored snapshot IS the value, so an "authored delta"
            # computed against it would be a fake 0.0000 -- a precise, confident number
            # meaning only that a value equals itself.
            centre = authored
            fallback = "authored snapshot (no live derivation)"

        out.append(EntityIR(
            id=body_id,
            kind="body",
            to_world=_matrix(centre),
            frame=FRAME_ALREADY_WORLD,
            placement_space="promoted",
            source_row=index,
            label=labels[index],
            derived_from=anchor,
            derivation=derivation,
            datum_delta=datum,
            # Withheld when the pose fell back to it: comparing a value with itself is not
            # a check, and reporting that 0.0000 as agreement is how 0457 happened.
            authored_center=None if (authored is None or fallback is not None)
            else np.asarray(authored, dtype=float),
            fallback=fallback,
        ))
    return out


def _anchor_not_reconstructible(body_id: str, row_index: int):
    from KrakenOS.UI.services.result_diagnostics import WARNING, Finding

    return Finding(
        code="scene_ir.anchor_not_reconstructible",
        severity=WARNING,
        summary=f"{body_id} declares anchor='row_pose' but the IR cannot rebuild its pose",
        detail=f"row {row_index}: measured on ELS85 -- placement_offset_xyz is the AUTHORED "
               f"pose, not a delta. cw - po = R @ (0,0,half_z) holds exactly for the "
               f"station-neutral solid (row 6) and fails for the 45-degree plate (row 7, "
               f"|cw-po|=8.84 against |R@(0,0,hz)|=12.5, whose bounds say a 25 mm cube while "
               f"its axial_reserve says 40 mm). Even where it holds it reconstructs one "
               f"AUTHORED value from another, which is circular: a datum must relate the body "
               f"to its anchor ROW, and cw - row_pose can only be computed from the CURRENT "
               f"pose, so it is right only while nothing has moved -- exactly the case it "
               f"cannot detect",
        remedy="No lowering-side fix exists. The promotion WRITER must record the datum at "
               "promote time; until then these bodies fall back to a snapshot that goes "
               "stale the moment their row moves.",
    )


def _body_walk_failed(exc):
    from KrakenOS.UI.services.result_diagnostics import WARNING, Finding

    return Finding(
        code="scene_ir.body_walk_failed",
        severity=WARNING,
        summary="the output-port pose walk raised",
        detail=repr(exc),
        remedy="Every promoted body falls back to its authored snapshot, which may be stale.",
    )


def compare_to_consumer(scene_ir: SceneIR, consumer_positions: dict, *,
                        kind: str | None = "surface", tol_mm: float = 1e-3):
    """Per-entity disagreement between the IR and one consumer's positions.

    ``consumer_positions`` maps row index -> ``(3,)`` world position. ``kind`` defaults to
    "surface" because a surface entity and a body derived from it SHARE a ``source_row``,
    and a body's centre is not its row's surface vertex -- differencing them manufactured
    132-480 mm of nonsense in the pose audit before this default existed. Pass kind=None
    only for a consumer that genuinely holds both. This is the Phase A
    instrument: it answers "who produced this pose", which is what could not be answered
    before. Entities the consumer has no opinion on are reported as unpaired, never as
    agreement -- silence is not a measurement.
    """
    rows: list[dict] = []
    for entity in scene_ir.entities:
        if entity.source_row is None:
            continue
        if kind is not None and entity.kind != kind:
            continue
        theirs = consumer_positions.get(entity.source_row)
        if theirs is None:
            rows.append({"id": entity.id, "row": entity.source_row,
                         "delta_mm": None, "status": "unpaired"})
            continue
        delta = float(np.linalg.norm(np.asarray(theirs, dtype=float).reshape(3) - entity.position))
        rows.append({"id": entity.id, "row": entity.source_row, "delta_mm": delta,
                     "status": "agree" if delta <= tol_mm else "DISAGREE"})
    return rows



def _surface_entity_for_row(editor, row_index: int) -> "EntityIR | None":
    """Build the ONE surface entity for ``row_index`` WITHOUT lowering the scene.

    bugs/0572 caught why this must exist: routing ``world_frame`` through a whole-scene
    ``lower()`` made a single-row question demand that EVERY row be lowerable. The guard's
    probe supplies two rows, the real code needs one -- and in production a scene carrying a
    single unreadable row would break a query about an unrelated one. The original
    ``world_pose`` call asked about one row and touched one row; this restores that.
    """
    from KrakenOS.UI.services import row_placement as rp

    rows = list(getattr(editor, "rows", []) or [])
    if not (0 <= int(row_index) < len(rows)):
        return None
    row = rows[int(row_index)]
    try:
        pose = rp.world_pose(editor, int(row_index))
        rotation = rp.rotation_matrix(row)
    except Exception:
        return None
    space = getattr(pose, "space", rp.SEQUENTIAL)
    # bugs/0826 Phase D: the same resolver lower() uses, so one row and every row agree.
    position, rotation, frame = _post_fold_surface_pose(editor, int(row_index), pose, rotation)
    label = str(getattr(row, "name", "") or getattr(row, "surface", "") or "")
    return EntityIR(
        id=entity_id("surface", label, 0),
        kind="surface",
        to_world=_matrix(position, rotation),
        frame=frame,
        placement_space=space,
        source_row=int(row_index),
        label=label,
        has_orientation=rotation is not None,
    )

def _output_port_overrides(editor: Any) -> dict:
    """Every output-port pose override in the scene, once. bugs/0826 Phase D.

    ``lower()`` walks every row, so it resolves this ONCE and passes it down; the single-row
    path builds it for the one row it is asked about. Computing it per row inside a whole-scene
    lowering would be quadratic.
    """
    try:
        from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides

        overrides = optical_solid_output_port_pose_overrides(None, editor.rows)
    except Exception:
        return {}
    return overrides if isinstance(overrides, dict) else {}


def _post_fold_surface_pose(editor: Any, row_index: int, pose, rotation, overrides=None):
    """``(position, rotation, frame)`` for a surface, with the fold RESOLVED. Phase D.

    This is the change the whole design was for: ``to_world`` is a real world pose. A row
    repositioned by a promoted solid's output port is placed AT that override -- measured in
    bugs/0836 to reproduce the DRAWN scene on all 23 such rows of ``om05a_folded``, to the
    0.08 mm an actor's bbox centre differs from its surface. A row with no override is not
    repositioned by anything, so its own numbers already are its world pose.

    The fold TRANSFORM is deliberately not used here. ``_optical_axis_fold_world_transform_for_row``
    is ``F(v) = C + R (v - S)`` with ``S`` the straight-axis STATION, so it is only valid on a
    row whose prescription IS ``[0, 0, z]``; on om05a it mis-places 8 of the 23 override rows,
    flinging RA mirror 2 to ``[124.49, 0, 244.14]`` instead of ``[-269.14, 56.31, -25.0]``.
    Phase D is the override, not the transform (bugs/0836).

    Both lowering paths call THIS, so the pre-lowered and single-row answers cannot drift --
    a divergence there would be invisible and would break exactly the consumers Phase C
    re-pointed.
    """
    from KrakenOS.UI.services import row_placement as rp

    space = getattr(pose, "space", rp.SEQUENTIAL)
    position = getattr(pose, "position", None)
    table = _output_port_overrides(editor) if overrides is None else overrides
    port = table.get(int(row_index)) if isinstance(table, dict) else None
    if isinstance(port, dict) and port.get("center") is not None:
        try:
            centre = np.asarray(port.get("center"), dtype=float).reshape(3)
        except Exception:
            centre = None
        if centre is not None and np.all(np.isfinite(centre)):
            turned = rotation
            try:
                candidate = np.asarray(port.get("rotation"), dtype=float).reshape(3, 3)
                if np.all(np.isfinite(candidate)):
                    turned = candidate
            except Exception:
                pass
            return centre, turned, FRAME_POST_FOLD
    return position, rotation, (FRAME_ALREADY_WORLD if space == rp.WORLD else FRAME_POST_FOLD)


def _output_port_pose(editor: Any, row_index: int):
    """The output-port pose override for a row, or None. bugs/0836."""
    try:
        from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides

        overrides = optical_solid_output_port_pose_overrides(None, editor.rows)
    except Exception:
        return None
    pose = overrides.get(int(row_index)) if isinstance(overrides, dict) else None
    return pose if isinstance(pose, dict) else None


def drawn_world_frame(editor: Any, row_index: int, *, scene_ir: "SceneIR | None" = None):
    """``(position, rotation_3x3_or_None, frame)`` where the row is DRAWN.

    **Phase D has landed, so this is now exactly :func:`world_frame`.** It survives as a name
    because bugs/0836's callers say what they need -- the drawn frame -- and because the
    distinction it drew was real for the day it existed: before Phase D, ``world_frame``
    answered in the straight-equivalent for a SEQUENTIAL row, and anything comparing a row
    against drawn geometry got a number with no meaning.

    Kept deliberately rather than inlined: a caller that means "wherever this row's own numbers
    put it" and one that means "where the user sees it" are different intents, and only one of
    them stayed correct across Phase D.
    """
    return world_frame(editor, row_index, scene_ir=scene_ir)


def drawn_leg_unit(editor: Any, row_index: int, leg_unit) -> "np.ndarray | None":
    """bugs/0836: a leg direction expressed in the DRAWN frame.

    The lens slide plan's direction is the PRE-FOLD leg, because that is the frame its ``desp``
    bookkeeping writes in -- right for the write, wrong for measuring against bodies. On
    ``om05a_folded`` the plan says ``(0, 0, 1)`` while the drawn leg runs along ``-x``, so a
    room measure handed the plan's direction found NO obstacle at all on a bench whose filter
    is 16 mm away.

    Turned by the row's own output-port rotation, which is the same thing that places it.
    Unchanged when the row has no override, and None when the input is not a direction.
    """
    try:
        unit = np.asarray(leg_unit, dtype=float).reshape(3)
    except Exception:
        return None
    norm = float(np.linalg.norm(unit))
    if not np.isfinite(norm) or norm <= 1.0e-12:
        return None
    unit = unit / norm
    pose = _output_port_pose(editor, row_index)
    if pose is None:
        return unit
    try:
        rotation = np.asarray(pose.get("rotation"), dtype=float).reshape(3, 3)
    except Exception:
        return unit
    if not np.all(np.isfinite(rotation)):
        return unit
    turned = rotation @ unit
    norm = float(np.linalg.norm(turned))
    return turned / norm if np.isfinite(norm) and norm > 1.0e-12 else unit


def world_frame(editor: Any, row_index: int, *, scene_ir: "SceneIR | None" = None):
    """``(position, rotation_3x3_or_None, space)`` for a row, read from the IR.

    A drop-in for :func:`row_placement.world_frame`, returning the identical shape --
    including ``None`` for a row that carries no tilts, which is why ``EntityIR`` records
    ``has_orientation`` rather than letting a stored identity masquerade as one.

    Today the two are the same answer: the IR's surface entities are built from
    ``prescription_pose``, which is exactly what ``row_placement`` returns. **That is the
    point of Phase C** -- re-pointing changes no behaviour now, and at Phase D, when the fold
    moves inside :func:`lower`, every consumer reading through here gets the fold while the
    ones still calling ``row_placement`` do not.

    ``scene_ir`` lets a caller that already lowered this refresh pass it in. Lowering costs
    0.17-0.38% of a refresh, so lowering per call is affordable rather than free -- one
    lowering shared across a refresh is the architecture, and persisting one ACROSS refreshes
    is the thing the design forbids.
    """
    if scene_ir is not None:
        for entity in scene_ir.of_kind("surface"):
            if entity.source_row is not None and int(entity.source_row) == int(row_index):
                matrix = np.asarray(entity.to_world, dtype=float)
                return (matrix[:3, 3],
                        matrix[:3, :3] if entity.has_orientation else None,
                        entity.placement_space)
        raise IndexError(f"row {row_index} has no surface entity in the IR")
    # No pre-lowered IR: build JUST this row. Lowering the scene to answer about one row
    # is what bugs/0572 caught -- see _surface_entity_for_row.
    entity = _surface_entity_for_row(editor, row_index)
    if entity is None:
        raise IndexError(f"row {row_index} has no readable pose")
    matrix = np.asarray(entity.to_world, dtype=float)
    return (matrix[:3, 3],
            matrix[:3, :3] if entity.has_orientation else None,
            entity.placement_space)
