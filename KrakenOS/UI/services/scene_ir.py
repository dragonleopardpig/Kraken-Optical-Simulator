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


def lower(editor: Any) -> SceneIR:
    """Lower a live editor to flat data. Pure and read-only: changes nothing."""
    from KrakenOS.UI.services import row_placement as rp
    from KrakenOS.UI.services.result_diagnostics import NO_REMEDY, WARNING, Finding

    rows = list(getattr(editor, "rows", []) or [])
    findings: list = []

    labels = [str(getattr(r, "name", "") or getattr(r, "surface", "") or "") for r in rows]
    surface_ids = _assign_ids("surface", labels)

    entities: list[EntityIR] = []
    for index, row in enumerate(rows):
        try:
            pose = rp.prescription_pose(editor, index)
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
        frame = FRAME_ALREADY_WORLD if space == rp.WORLD else FRAME_STRAIGHT_EQUIVALENT
        entities.append(EntityIR(
            id=surface_ids[index],
            kind="surface",
            to_world=_matrix(pose.position, rp.rotation_matrix(row)),
            frame=frame,
            placement_space=space,
            source_row=index,
            label=labels[index],
        ))

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
            "scene": str(getattr(editor, "current_layout_name", "") or ""),
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
        detail=f"row {row_index}: placement_offset_xyz is not a delta from the row pose "
               f"(its z equals bounds_min_world's z), so no datum reconstruction is available",
        remedy="Falling back to the authored snapshot, which goes stale the moment the row "
               "moves. Phase B must find this mechanism's real datum before the body can "
               "be derived.",
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
