"""bugs/0843: a GEOMETRY TRANSACTION -- try a multi-step move and, when it does not work out,
put the scene back BYTE-IDENTICAL.

The measured failure: the FOV solve's bugs/0573 rescue slid the fold arm 197.138 mm to make
room, the lens move it made room FOR was refused anyway, and the solve reported the refusal
with the arm still slid -- row 12 read 276.819 mm where it had been 79.681, and the paraxial
magnification was None. "Refused" has to mean "nothing moved".

A SNAPSHOT, never the inverse move:

* ``(79.681 + 197.138) - 197.138 == 79.68100000000001``, and the history bracket compares
  with ``==`` -- an inverse leaves a phantom undo entry and clears redo;
* the inverse re-plans from the slid scene and can early-return having reverted nothing;
* ``_set_step_placement_offset_xyz`` POPS the label's axis anchor on every call, so neither
  the forward move nor an inverse brings the anchor back.

STATE   every row's thickness / desp / tilt / axis_move (RAW objects, no float() coercion, so
        ``-0.0``, an int-valued thickness and a ``None`` all survive), every overlay label's
        ``<label>_step_placement_offset_xyz`` (or its ABSENCE), the axis-anchor table, plus the
        data attributes a caller names in ``also``.
NOT     the refusal channels (``_lens_move_refusal`` ..., ``_fov_solve_refusal_info``): they
        are the EXPLANATION and must outlive the put-back -- hence an allow-list, never
        ``__dict__`` wholesale.
NOT     history: never begin/commit here. The put-back is exact, so the caller's bracket sees
        ``snapshot == current`` and records nothing; after commit() it records its usual ONE.
NOT     display flags: a put-back that changed anything re-dirties the preview trace and
        leaves ``_fold_carry_pending_rebuild`` SET. The forward move's ``append_debug`` pumps
        idle tasks, so a refresh may already have drawn the state that just vanished.

Independent value snapshots nest as savepoints -- no registry, no depth counter.  No Tk, no
VTK, no numpy: it is driven display-free by its guard.
"""

from __future__ import annotations

from KrakenOS.UI.services.step_overlay_labels import STEP_OVERLAY_LABELS

#: Every field a PLACEMENT write can touch. Today's writers move only thickness and desp; the
#: tilts and axis_move are cheap insurance that keeps the class right for a fold ROTATE or a
#: gap rebalance without a second look at this tuple.
_ROW_FIELDS = (
    "thickness", "desp_x", "desp_y", "desp_z", "tilt_x", "tilt_y", "tilt_z", "axis_move",
)
_OFFSET_SUFFIX = "_step_placement_offset_xyz"
_ANCHORS = "_step_overlay_axis_anchor_by_label"
_ABSENT = object()


def _differs(now, then) -> bool:
    if now is then:
        return False
    if now is _ABSENT or then is _ABSENT:
        return True
    # repr, not ==: 79.68100000000001 vs 79.681, -0.0 vs 0.0 and 1 vs 1.0 all have to count.
    return repr(now) != repr(then)


class GeometryTransaction:
    """``begin`` / ``commit`` / ``rollback`` and the ``with`` protocol.

    Leaving the block uncommitted -- or by exception -- puts the geometry back.
    ``state``: new -> open -> committed | rolled_back | stuck.
    """

    def __init__(self, editor, label: str = "", *, also: "tuple[str, ...]" = ()) -> None:
        self.editor = editor
        self.label = str(label or "geometry move")
        self.state = "new"
        self.restored = 0
        self._also = tuple(str(name) for name in also)
        self._rows: list = []
        self._values: list = []
        self._attrs: dict = {}
        self._anchors = _ABSENT

    def _held(self) -> dict:
        # __dict__, never getattr-with-default, for DATA: the editor is a Tk widget whose
        # __getattr__ recurses on a missing name instead of raising.
        held = getattr(self.editor, "__dict__", None)
        return held if isinstance(held, dict) else {}

    def _say(self, message: str) -> None:
        try:
            self.editor.append_debug(message)
        except Exception:
            pass

    def begin(self) -> "GeometryTransaction":
        held = self._held()
        self._rows = list(getattr(self.editor, "rows", None) or [])
        self._values = [
            tuple(getattr(row, field, _ABSENT) for field in _ROW_FIELDS) for row in self._rows
        ]
        names = [f"{label}{_OFFSET_SUFFIX}" for label in STEP_OVERLAY_LABELS]
        self._attrs = {name: held.get(name, _ABSENT) for name in (*names, *self._also)}
        anchors = held.get(_ANCHORS, _ABSENT)
        # Every writer REBINDS a copy rather than mutating in place; the copy here is belt
        # and braces against one that one day does not.
        self._anchors = dict(anchors) if isinstance(anchors, dict) else anchors
        self.state = "open"
        return self

    def commit(self) -> None:
        if self.state == "open":
            self.state = "committed"

    def rollback(self) -> bool:
        """True when the scene equals the snapshot again (also when nothing had moved).

        False when the row list is no longer the captured objects: then NOTHING is written --
        restoring values onto rows that are not the ones captured would be a guess -- and
        ``state`` is 'stuck' so the caller can say so instead of claiming "nothing moved".
        """
        if self.state != "open":
            return self.state == "rolled_back"
        editor = self.editor
        rows = list(getattr(editor, "rows", None) or [])
        if len(rows) != len(self._rows) or any(
            now is not then for now, then in zip(rows, self._rows)
        ):
            self.state = "stuck"
            self._say(
                f"{self.label}: the geometry could NOT be put back -- the row list changed "
                f"under the move ({len(self._rows)} rows captured, {len(rows)} now); nothing "
                f"was written"
            )
            return False
        restored = 0
        for row, values in zip(rows, self._values):
            for field, value in zip(_ROW_FIELDS, values):
                if value is _ABSENT:
                    continue
                if _differs(getattr(row, field, _ABSENT), value):
                    restored += 1
                    setattr(row, field, value)
        held = self._held()
        setter = getattr(editor, "_set_step_placement_offset_xyz", None)
        for name, value in self._attrs.items():
            if not _differs(held.get(name, _ABSENT), value):
                continue
            restored += 1
            if name.endswith(_OFFSET_SUFFIX) and callable(setter):
                # THROUGH the setter on purpose: its invalidation drops the label's
                # face-metadata and trace-plan caches, which the forward move left describing
                # a pose that no longer exists.
                try:
                    setter(
                        name[: -len(_OFFSET_SUFFIX)],
                        (0.0, 0.0, 0.0) if value is _ABSENT else value,
                    )
                except Exception:
                    pass
            # ... then the exact object: the setter re-packs the tuple and silently refuses a
            # non-finite one, so by itself it is not a byte-exact restore.
            if value is _ABSENT:
                held.pop(name, None)
            else:
                setattr(editor, name, value)
        # LAST, and only when it changed: the setter above pops each restored label's anchor
        # all over again. A put-back that finds nothing to do must write nothing.
        if _differs(held.get(_ANCHORS, _ABSENT), self._anchors):
            restored += 1
            if self._anchors is _ABSENT:
                held.pop(_ANCHORS, None)
            else:
                setattr(
                    editor,
                    _ANCHORS,
                    dict(self._anchors) if isinstance(self._anchors, dict) else self._anchors,
                )
        if restored:
            invalidate = getattr(editor, "_invalidate_preview_scene_trace", None)
            if callable(invalidate):
                try:
                    invalidate()
                except Exception:
                    pass
            try:
                editor._fold_carry_pending_rebuild = True
            except Exception:
                pass
        self.restored = restored
        self.state = "rolled_back"
        if restored:
            # AFTER the restore: append_debug pumps idle tasks, which must see the OLD scene.
            self._say(
                f"{self.label}: put back exactly ({restored} value(s) restored; the refusal "
                f"text is kept)"
            )
        return True

    def __enter__(self) -> "GeometryTransaction":
        return self.begin() if self.state == "new" else self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if self.state == "open":
            try:
                self.rollback()
            except Exception as failure:  # never mask the body's own exception
                self.state = "stuck"
                self._say(
                    f"{self.label}: the put-back itself failed "
                    f"({type(failure).__name__}: {failure})"
                )
        return False
