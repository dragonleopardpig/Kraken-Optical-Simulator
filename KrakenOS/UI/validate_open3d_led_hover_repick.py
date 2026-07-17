#!/usr/bin/env python3
"""Display-free guard for bugs/0331 -- the LED clear-aperture opening stops
highlighting after an off-body hover (flags 978/798/718/630/408).

Two independent defects, both guarded here (no GLX, no Tk mainloop):

ROOT CAUSE -- the shared display mesh gets its face-index cell data STRIPPED.
    The off-body/miss hover pick runs ``_step_overlay_face_metadata_compute``,
    which strips every cell-data array off the mesh before ``extract_surface``/
    ``triangulate`` (to silence PyVista's InvalidMeshWarning chorus).  That mesh
    is the SHARED, memoized display mesh, and the strip ran IN PLACE -- poisoning
    the live mesh's ``kraken_step_*`` face indices.  With them gone,
    ``triangle_array_and_face_index`` returns empty, ``opening_loops_for_mesh``
    collapses 21 -> 0, and the opening-hover pick can never resolve the CA again.
    The strip also bumps the mesh MTime, so every id/MTime-keyed cache recomputes
    into the poisoned state -- the freeze is permanent until the mesh rebuilds.
    Fix: ``_step_overlay_face_metadata_compute`` deep-copies the fetched mesh
    BEFORE stripping, so the live mesh keeps its arrays.
    Section 1 proves ``opening_loops_for_mesh`` and the ``kraken_step_*`` cell
    arrays SURVIVE a metadata compute on the shared mesh.

THROTTLE -- the resting cursor never gets a hover pick.
    ``_mouse_move_due`` (35 ms) drops moves that arrive inside one interval, and
    a mouse coming to REST fires its last reports inside one window, so the FINAL
    resting position was never hovered -- the highlight froze 300-590 px behind
    the cursor even when the pick would resolve the opening correctly there.
    Fix: a debounced, one-shot trailing re-pick fires ~one interval after motion
    stops.  Section 2 asserts the timer CONTRACT (schedule / debounce / fire at
    rest / not-during-carry / cancel / no-widget no-op).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_hover_repick

Exit: 0 = pass (incl. a cache-absent skip of Section 1), 1 = regression.
"""
from __future__ import annotations

import tempfile
import types
from pathlib import Path

import numpy as np

_VTP = Path(
    "attachment/cad_cache/OPT-CO90-X-V1.6.2-H_1766991920_3951195.analytic.v2.vtp"
)


# ---------------------------------------------------------------------------
# Section 1 -- the shared display mesh must SURVIVE a metadata compute.


class _FakeEditor:
    """Binds the REAL ``_step_overlay_face_metadata_compute`` so the guard
    exercises the production stripper, not a copy.  ``led`` is placed in the
    no-analytic set so the compute skips the analytic short-circuit and reaches
    the cell-data strip -- exactly the off-body/miss path that poisoned the
    shared mesh."""

    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin as _M

    _step_overlay_face_metadata_compute = _M._step_overlay_face_metadata_compute
    del _M

    _DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC = frozenset({"led"})

    def __init__(self, mesh):
        self._mesh = mesh

    def _transformed_imported_step_mesh_for_label(self, label):
        return self._mesh

    def _step_path_for_label(self, label):
        return None

    def append_debug(self, message):  # pragma: no cover - defensive
        pass


def _cell_keys(mesh) -> list[str]:
    import pyvista as pv

    try:
        return list(pv.wrap(mesh).cell_data.keys())
    except Exception:
        return []


def _check_mesh_integrity(failures: list[str], notes: list[str]) -> None:
    if not _VTP.exists():
        notes.append(f"SKIP(1): analytic cache absent ({_VTP}); regenerate from the LED STEP to run")
        return

    import pyvista as pv

    import KrakenOS.UI.services.scene_placement_commands as spc
    from KrakenOS.UI.services.open3d_face_index_edges import (
        FACE_INDEX_CELL_DATA,
        SELECTION_FACE_INDEX_CELL_DATA,
    )
    from KrakenOS.UI.services.open3d_opening_loops import opening_loops_for_mesh

    mesh = pv.read(str(_VTP))

    keys_before = _cell_keys(mesh)
    has_face_index = any(
        k in keys_before for k in (SELECTION_FACE_INDEX_CELL_DATA, FACE_INDEX_CELL_DATA)
    )
    if not has_face_index:
        failures.append(
            "FAIL(1A): analytic cache carries no kraken_step_* face-index cell array "
            f"(keys={keys_before}); cannot exercise the strip -- regenerate the cache"
        )
        return

    loops_before = opening_loops_for_mesh(mesh)
    if not loops_before:
        failures.append(
            f"FAIL(1A): opening_loops_for_mesh found no openings on {_VTP.name} before compute"
        )
        return
    n_before = len(loops_before)

    # Drive the REAL stripper against the SHARED mesh. Patch the heavy,
    # side-effecting leaves (planar clustering + cache dir) so the guard stays
    # quick and writes only to a throwaway temp dir; the copy/strip we care
    # about runs BEFORE any of them.
    orig_cluster = spc.cluster_optical_solid_planar_faces
    orig_assign = spc.auto_assign_optical_solid_face_roles
    orig_cache_dir = spc._current_cad_cache_dir
    tmp = Path(tempfile.mkdtemp(prefix="kraken_0331_guard_"))
    spc.cluster_optical_solid_planar_faces = lambda _path: []
    spc.auto_assign_optical_solid_face_roles = lambda _records: []
    spc._current_cad_cache_dir = lambda: tmp
    try:
        editor = _FakeEditor(mesh)
        metadata = editor._step_overlay_face_metadata_compute("led")
    finally:
        spc.cluster_optical_solid_planar_faces = orig_cluster
        spc.auto_assign_optical_solid_face_roles = orig_assign
        spc._current_cad_cache_dir = orig_cache_dir

    if not isinstance(metadata, dict):
        failures.append(
            f"FAIL(1B): metadata compute returned {type(metadata).__name__}, not a dict "
            "-- the copy-before-strip fix broke the compute itself"
        )

    keys_after = _cell_keys(mesh)
    stripped = [
        k
        for k in (SELECTION_FACE_INDEX_CELL_DATA, FACE_INDEX_CELL_DATA)
        if k in keys_before and k not in keys_after
    ]
    if stripped:
        failures.append(
            "FAIL(1C): the metadata compute STRIPPED the shared display mesh's face-index "
            f"cell data {stripped} (keys {keys_before} -> {keys_after}) -- it mutated the "
            "memoized mesh in place instead of a private copy; the CA opening will never "
            "highlight again after this hover"
        )

    loops_after = opening_loops_for_mesh(mesh)
    if len(loops_after) != n_before:
        failures.append(
            f"FAIL(1D): opening_loops_for_mesh collapsed {n_before} -> {len(loops_after)} across a "
            "metadata compute -- the shared mesh was poisoned; the opening-hover pick can no "
            "longer resolve the clear aperture (the whole 978/798/718/630/408 freeze)"
        )
    else:
        notes.append(
            f"mesh integrity: openings {n_before} -> {len(loops_after)} (survived), "
            f"face-index arrays retained (keys {len(keys_before)} -> {len(keys_after)})"
        )


# ---------------------------------------------------------------------------
# Section 2 -- the debounced trailing re-pick timer contract.


class _FakeWidget:
    def __init__(self):
        self.scheduled: dict[str, tuple[int, object]] = {}
        self.cancelled: list[str] = []
        self._n = 0

    def after(self, delay_ms, callback):
        self._n += 1
        token = f"after#{self._n}"
        self.scheduled[token] = (int(delay_ms), callback)
        return token

    def after_cancel(self, token):
        self.cancelled.append(token)
        self.scheduled.pop(token, None)


def _make_inspector(widget):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K

    self = types.SimpleNamespace()
    self._vtk_widget = widget
    self._mouse_move_min_interval_s = 0.035
    self._trailing_hover_repick_after_id = None
    self._step_carry_drag_state = None
    self._step_carry_follow_state = None
    self._refires = 0

    def _refire():
        self._refires += 1

    self._refire_scene_hover_pick = _refire
    for name in (
        "_schedule_trailing_hover_repick",
        "_cancel_trailing_hover_repick",
        "_on_trailing_hover_repick",
    ):
        setattr(self, name, types.MethodType(getattr(K, name), self))
    return self


def _check_repick_contract(failures: list[str], notes: list[str]) -> None:
    def want(cond, ok_note, fail_note):
        if cond:
            notes.append(ok_note)
        else:
            failures.append(fail_note)

    # A. one throttled move schedules exactly one trailing timer ~= interval+5 ms.
    widget = _FakeWidget()
    insp = _make_inspector(widget)
    insp._schedule_trailing_hover_repick()
    tok1 = insp._trailing_hover_repick_after_id
    delay = widget.scheduled.get(tok1, (None, None))[0]
    want(
        tok1 in widget.scheduled and delay is not None and 35 <= delay <= 60,
        f"2A: throttled move schedules one trailing timer ({delay} ms)",
        f"FAIL(2A): a throttled move did not schedule a single ~interval+5ms timer (delay={delay})",
    )

    # B. a second throttled move DEBOUNCES: cancel prior, keep exactly one.
    insp._schedule_trailing_hover_repick()
    tok2 = insp._trailing_hover_repick_after_id
    want(
        tok1 in widget.cancelled and tok2 != tok1 and len(widget.scheduled) == 1,
        "2B: second throttled move debounces to exactly one pending timer",
        "FAIL(2B): the trailing timer did not debounce (should cancel prior, keep one)",
    )

    # C. firing at rest re-picks exactly once, id cleared.
    widget.scheduled[tok2][1]()
    want(
        insp._refires == 1 and insp._trailing_hover_repick_after_id is None,
        "2C: resting timer re-picks once and clears its id",
        f"FAIL(2C): resting timer did not re-pick once (refires={insp._refires})",
    )

    # D. while a carry drag/follow owns the mouse, the timer must NOT re-pick.
    w2 = _FakeWidget()
    insp2 = _make_inspector(w2)
    insp2._step_carry_drag_state = {"dragging": True}
    insp2._schedule_trailing_hover_repick()
    w2.scheduled[insp2._trailing_hover_repick_after_id][1]()
    drag_ok = insp2._refires == 0
    insp2._step_carry_drag_state = None
    insp2._step_carry_follow_state = {"following": True}
    insp2._schedule_trailing_hover_repick()
    w2.scheduled[insp2._trailing_hover_repick_after_id][1]()
    want(
        drag_ok and insp2._refires == 0,
        "2D: no re-pick while a carry drag/follow owns the mouse",
        "FAIL(2D): the trailing timer fired mid carry-gesture (should stay quiet)",
    )

    # E. explicit cancel drops the pending timer.
    w3 = _FakeWidget()
    insp3 = _make_inspector(w3)
    insp3._schedule_trailing_hover_repick()
    tok3 = insp3._trailing_hover_repick_after_id
    insp3._cancel_trailing_hover_repick()
    want(
        tok3 in w3.cancelled and insp3._trailing_hover_repick_after_id is None,
        "2E: explicit cancel drops the pending timer",
        "FAIL(2E): cancel did not drop the pending trailing timer",
    )

    # F. with no widget, schedule/cancel are inert and never raise.
    insp4 = _make_inspector(None)
    try:
        insp4._schedule_trailing_hover_repick()
        insp4._cancel_trailing_hover_repick()
        inert = insp4._trailing_hover_repick_after_id is None
    except Exception as exc:  # noqa: BLE001
        inert = False
        failures.append(f"FAIL(2F): no-widget schedule/cancel raised {exc!r}")
    want(
        inert,
        "2F: no-widget schedule/cancel is an inert no-op",
        "FAIL(2F): no-widget schedule/cancel did not stay inert",
    )


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_mesh_integrity(failures, notes)
    _check_repick_contract(failures, notes)
    return (not failures), failures + notes


def main() -> int:
    passed, notes = run_checks()
    hard = [n for n in notes if n.startswith("FAIL")]
    soft = [n for n in notes if not n.startswith("FAIL")]
    if hard:
        print("[FAIL] LED CA hover survives off-body hover (bugs/0331 mesh strip + trailing re-pick)")
        for item in hard:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] LED CA opening survives an off-body hover: the shared mesh keeps its face "
        "indices (no in-place strip) and the resting cursor gets a debounced re-pick (bugs/0331)"
    )
    for item in soft:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
