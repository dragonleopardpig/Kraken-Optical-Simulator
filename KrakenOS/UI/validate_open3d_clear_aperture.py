"""Guard for bugs/0134 -- the dedicated clear-aperture (CA) pick + persisted CA.

Regression context
------------------
The LED component (`OPT-CO90-X-V1.6.2-H.STEP`) carries a square rounded-corner
"clear aperture" window on its front face. Two layers had broken the user's
ability to select and highlight it:

1. Coarse face metadata: the LED was forced through the planar-cluster path, so a
   right-click "Center Picked Face -> Optical Axis" grabbed a housing cluster, not
   the fine CA window. (Layer 2 fix: the editor now records a *fine* analytic face.)

2. Stray ``VTK_LINE`` cells: the saved analytic vtp gained 14 degenerate line cells
   (a ``clean()`` artifact). VTK numbers per-cell ``kraken_step_*face_index`` over
   the FULL cell space (verts, then lines, then polys), so the poly-only reindexed
   triangle array is OFF BY the stray-line count versus the picker. Indexing the
   reindexed array by a picker cell id therefore resolves the WRONG face. The fix is
   ``face_index_for_display_cell`` -- a direct picker-aligned ``cell_data[cell_id]``
   read -- and routing ``face_pick_from_display_cell`` through it.

This guard is display-free. It builds a tiny synthetic mesh that reproduces the
exact failure shape (14 stray line cells in front of tagged triangles) so the core
contract is checked on EVERY machine, then exercises the real editor CA methods
(set / read / center / clear) against that mesh via a ScenePlacementMixin subclass.
A best-effort block also confirms the resolver on the real LED vtp when the CAD
cache is present. Source contracts pin the pick routing, the inspector pick mode,
the right-click menu items, the persistent highlight in both refresh paths, and the
save/reload of the persisted CA.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_clear_aperture

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

try:  # PyVista is optional outside Open 3D.
    import pyvista as pv
except Exception:  # pragma: no cover
    pv = None


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SEL = "kraken_step_selection_face_index"
# The real LED analytic vtp (gitignored cache; only present on a synced machine).
_LED_VTP = _REPO_ROOT / "attachment/cad_cache/OPT-CO90-X-V1.6.2-H_1766991920_3951195.analytic.v2.vtp"


class _FakeStatusVar:
    def __init__(self) -> None:
        self._text = ""

    def set(self, text) -> None:
        self._text = str(text)

    def get(self) -> str:
        return self._text


def _synthetic_strayline_mesh():
    """Two unit-square faces (index 100 at z=5, 200 at z=0) preceded by 14 stray
    line cells -- the exact cell-ordering shape that broke the LED CA pick. Cell ids
    0..13 are lines, 14..17 are the polys, and the per-cell selection array is stored
    in that full order so ``cell_data[14]`` is the first poly's face index."""
    if pv is None:
        return None
    points = np.array(
        [
            [0.0, 0.0, 5.0], [1.0, 0.0, 5.0], [1.0, 1.0, 5.0], [0.0, 1.0, 5.0],  # face 100
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],  # face 200
        ],
        dtype=float,
    )
    faces = np.hstack(
        [[3, 0, 1, 2], [3, 0, 2, 3], [3, 4, 5, 6], [3, 4, 6, 7]]
    ).astype(np.int64)
    lines = np.hstack(
        [[2, i % 8, (i + 1) % 8] for i in range(14)]
    ).astype(np.int64)
    mesh = pv.PolyData(points, faces=faces, lines=lines)
    # Full-cell-space selection array: 14 line sentinels (-1), then the 4 poly faces.
    sel = np.array([-1] * 14 + [100, 100, 200, 200], dtype=int)
    mesh.cell_data[_SEL] = sel
    return mesh


class _FakeCAEditorBase:
    """Leaf-stub half of the CA test host. Composed with ScenePlacementMixin inside
    ``run_checks`` (stubs first in MRO so they OVERRIDE the mixin's real leaves) so
    the CA methods under test (set/step/clear/center_clear_aperture) and the centre
    they delegate to run as production code; only the leaf dependencies (mesh source,
    offset get/set, global axis frame, anchor/refresh/history) are stubbed."""

    def __init__(self, mesh, current_offset=(0.0, 0.0, 0.0)) -> None:
        self._mesh = mesh
        self.status_var = _FakeStatusVar()
        self._offset = np.asarray(current_offset, dtype=float).reshape(3)
        self.set_offset_calls: list[np.ndarray] = []
        self.rotation_calls: list[tuple] = []
        self.anchor_records: list[dict] = []
        self.refreshed_labels: list[str] = []
        self.plot_marks = 0
        self._cad_axis_pick_label = "sentinel"
        self._cad_axis_pick_any = True
        self._cad_led_object_edge_pick = True
        self._selected_step_label = None

    def _step_path_for_label(self, label):
        return f"/tmp/{label}.step"

    def _transformed_imported_step_mesh_for_label(self, label):
        return self._mesh

    def _mark_plot_update_pending(self) -> None:
        self.plot_marks += 1

    def _global_optical_axis_frame_near_point(self, reference_point):
        ref = np.asarray(reference_point, dtype=float).reshape(-1)[:3]
        return {
            "target_point": np.asarray((0.0, 0.0, float(ref[2])), dtype=float),
            "direction": np.asarray((0.0, 0.0, 1.0), dtype=float),
            "axis_label": "global optical axis",
            "ray_index": -1,
            "branch_path": "",
        }

    def _step_placement_offset_xyz(self, label):
        return np.asarray(self._offset, dtype=float).reshape(3)

    def _set_step_placement_offset_xyz(self, label, offset) -> None:
        arr = np.asarray(offset, dtype=float).reshape(3)
        self._offset = arr
        self.set_offset_calls.append(arr)

    def _set_step_rotation_deg_tuple(self, *args) -> None:
        self.rotation_calls.append(args)

    def _begin_history_capture(self) -> None:
        return None

    def _commit_history_capture(self) -> None:
        return None

    def _record_step_overlay_axis_anchor(self, label, **kwargs):
        record = {"label": label}
        record.update(kwargs)
        self.anchor_records.append(record)
        return record

    def _refresh_open_3d_views(self, *, step_label=None) -> None:
        self.refreshed_labels.append(step_label)


def _read(rel_path: str) -> str:
    try:
        return (_REPO_ROOT / rel_path).read_text(encoding="utf-8")
    except Exception:
        return ""


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    if pv is None:
        notes.append("FAIL: pyvista unavailable -- cannot validate the CA pick data path")
        return False, notes

    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
    from KrakenOS.UI.services.open3d_interaction_mode import (
        InteractionMode,
        derive_interaction_mode,
    )
    from KrakenOS.UI.services import open3d_face_index_edges as fie

    # A. Picker alignment on the synthetic stray-line mesh: the 14 line cells push
    #    the first poly to cell id 14, and the picker-aligned resolver must read its
    #    face index straight from cell_data -- not from the poly-only reindexed array.
    mesh = _synthetic_strayline_mesh()
    if mesh is None or int(getattr(mesh, "n_cells", 0)) != 18:
        notes.append(
            f"FAIL: synthetic mesh build failed (n_cells={getattr(mesh, 'n_cells', None)}, expected 18)"
        )
        return False, notes
    if int(mesh.GetNumberOfLines()) != 14:
        notes.append(f"FAIL: synthetic mesh has {mesh.GetNumberOfLines()} line cells, expected 14")
        passed = False

    got_14 = fie.face_index_for_display_cell(mesh, 14)
    got_16 = fie.face_index_for_display_cell(mesh, 16)
    if got_14 != 100:
        notes.append(
            f"FAIL: face_index_for_display_cell(cell 14) = {got_14}, expected 100 "
            "(picker cell id must read the full-cell selection array, not the 14-shifted poly array)"
        )
        passed = False
    if got_16 != 200:
        notes.append(f"FAIL: face_index_for_display_cell(cell 16) = {got_16}, expected 200")
        passed = False
    # A line cell never comes from a surface pick: its sentinel resolves to None.
    if fie.face_index_for_display_cell(mesh, 0) is not None:
        notes.append("FAIL: a stray line cell (id 0) resolved to a face index; it should be None")
        passed = False

    # The poly-only reindexed array has just 4 entries -- proving that indexing it by
    # the picker cell id 14 (the OLD path) would be out of range / wrong.
    tris, fidx = fie.triangle_array_and_face_index(mesh)
    if int(fidx.shape[0]) != 4:
        notes.append(
            f"FAIL: triangle_array_and_face_index returned {fidx.shape[0]} faces, expected 4 "
            "(stray lines must be repaired out of the poly-only array)"
        )
        passed = False
    elif 14 < fidx.shape[0]:
        notes.append("FAIL: poly-only array unexpectedly long -- offset proof invalid")
        passed = False

    outline = fie.face_outline_from_face_indices(mesh, (100,))
    if outline is None or int(getattr(outline, "n_points", 0)) <= 0:
        notes.append("FAIL: face_outline_from_face_indices((100,)) produced no CA edge points")
        passed = False

    # B. Editor CA data path against the synthetic mesh. Compose the stub leaves with
    #    the real mixin (stubs first so they override the mixin's real leaves) and call
    #    the CA methods on the instance so internal self.* hops resolve to production.
    _FakeCAEditor = type("_FakeCAEditor", (_FakeCAEditorBase, ScenePlacementMixin), {})
    fake = _FakeCAEditor(mesh)
    record = fake.set_step_clear_aperture("led", 100)
    if not isinstance(record, dict) or int(record.get("face_index", -1)) != 100:
        notes.append(f"FAIL: set_step_clear_aperture did not persist face 100 (got {record!r})")
        passed = False
    elif abs(float(record.get("area_mm2", 0.0)) - 1.0) > 1e-6:
        notes.append(f"FAIL: recorded CA area {record.get('area_mm2')} != 1.0 mm^2 for the unit square")
        passed = False
    read_back = fake.step_clear_aperture("led")
    if not isinstance(read_back, dict) or int(read_back.get("face_index", -1)) != 100:
        notes.append(f"FAIL: step_clear_aperture read-back mismatch (got {read_back!r})")
        passed = False

    centre_result = fake.center_clear_aperture_on_optical_axis("led")
    if centre_result is None:
        notes.append("FAIL: center_clear_aperture_on_optical_axis returned None for a recorded CA")
        passed = False
    elif not fake.set_offset_calls:
        notes.append("FAIL: centring the CA never set a placement offset")
        passed = False
    else:
        centred = np.asarray((0.5, 0.5, 5.0)) + fake.set_offset_calls[-1]
        if not (abs(centred[0]) < 1e-6 and abs(centred[1]) < 1e-6):
            notes.append(
                f"FAIL: CA centre not on the axis: centroid+offset={tuple(round(float(v), 4) for v in centred)} "
                "(expected x=0, y=0)"
            )
            passed = False
        if abs(centred[2] - 5.0) > 1e-6:
            notes.append(f"FAIL: CA centring changed along-axis z ({centred[2]:.4g} != 5)")
            passed = False
    if fake.rotation_calls:
        notes.append("FAIL: CA centring rotated the body -- it must be translate-only")
        passed = False

    cleared = fake.clear_step_clear_aperture("led")
    if cleared is None or fake.step_clear_aperture("led") is not None:
        notes.append("FAIL: clear_step_clear_aperture did not forget the recorded CA")
        passed = False

    # C. Best-effort confirmation on the real LED vtp (only when the cache exists).
    if _LED_VTP.exists():
        try:
            led = pv.read(str(_LED_VTP))
            sel = np.asarray(led.cell_data[_SEL], dtype=int)
            tris_r, fidx_r = fie.triangle_array_and_face_index(led)
            ca_fid = None
            for fid in np.unique(fidx_r):
                if fid < 0:
                    continue
                sub = tris_r[fidx_r == fid]
                cross = np.cross(sub[:, 1] - sub[:, 0], sub[:, 2] - sub[:, 0])
                area = float(0.5 * np.linalg.norm(cross, axis=1).sum())
                n = cross.sum(axis=0)
                n = n / max(np.linalg.norm(n), 1e-12)
                if abs(n[2]) > 0.9 and 3500 < area < 4500:
                    ca_fid = int(fid)
                    break
            if ca_fid is None:
                notes.append("FAIL: real LED vtp present but no axis-facing CA window face (~4000 mm^2) found")
                passed = False
            else:
                ca_cells = np.flatnonzero(sel == ca_fid)
                sample = int(ca_cells[ca_cells.size // 2])
                resolved = fie.face_index_for_display_cell(led, sample)
                if resolved != ca_fid:
                    notes.append(
                        f"FAIL: real LED CA cell {sample} resolved to {resolved}, expected {ca_fid}"
                    )
                    passed = False
                real_outline = fie.face_outline_from_face_indices(led, (ca_fid,))
                if real_outline is None or int(getattr(real_outline, "n_points", 0)) <= 0:
                    notes.append("FAIL: real LED CA outline is empty")
                    passed = False
                elif verbose:
                    notes.append(f"real LED vtp: CA face {ca_fid} resolves + outlines ({real_outline.n_points} pts)")
        except Exception as exc:
            notes.append(f"FAIL: real LED vtp check raised: {exc!r}")
            passed = False
    elif verbose:
        notes.append("note: real LED vtp cache absent -- synthetic stray-line guard covers the contract")

    # D. Source contract: the cell pick routes through the picker-aligned resolver.
    pick_src = inspect.getsource(fie.face_pick_from_display_cell)
    if "face_index_for_display_cell(display_mesh, cell_id)" not in pick_src:
        notes.append(
            "FAIL: face_pick_from_display_cell no longer routes through face_index_for_display_cell "
            "-- a picker cell id must not index the 14-shifted poly array (bugs/0134)"
        )
        passed = False

    # E. Editor mixin exposes the full CA surface.
    for name in (
        "step_clear_aperture",
        "set_step_clear_aperture",
        "clear_step_clear_aperture",
        "center_clear_aperture_on_optical_axis",
        "clear_aperture_face_index_for_display_cell",
        "_step_overlay_fine_face_centroid_normal",
    ):
        if not hasattr(ScenePlacementMixin, name):
            notes.append(f"FAIL: ScenePlacementMixin is missing {name}")
            passed = False

    # F. Interaction mode + inspector pick mode.
    if not hasattr(InteractionMode, "STEP_CLEAR_APERTURE_PICK"):
        notes.append("FAIL: InteractionMode is missing STEP_CLEAR_APERTURE_PICK")
        passed = False
    else:
        class _ModeProbe:
            _step_clear_aperture_pick_mode = True
        if derive_interaction_mode(_ModeProbe()) != InteractionMode.STEP_CLEAR_APERTURE_PICK:
            notes.append("FAIL: derive_interaction_mode does not map the CA pick flag to STEP_CLEAR_APERTURE_PICK")
            passed = False

    inspector_src = _read("KrakenOS/UI/open3d_inspector.py")
    for token in (
        "def start_step_clear_aperture_pick",
        "def _apply_step_clear_aperture_pick",
        "def _clear_aperture_outline",
        "def _add_clear_aperture_highlight_actor",
        "def _update_clear_aperture_hover_highlight",
        "_step_clear_aperture_pick_mode",
        "_step_clear_aperture_pick_label",
    ):
        if token not in inspector_src:
            notes.append(f"FAIL: open3d_inspector.py is missing '{token}' (CA pick mode wiring)")
            passed = False

    interaction_src = _read("KrakenOS/UI/services/open3d_interaction.py")
    if "_apply_step_clear_aperture_pick" not in interaction_src:
        notes.append("FAIL: the click handler never calls _apply_step_clear_aperture_pick")
        passed = False
    if "_update_clear_aperture_hover_highlight" not in interaction_src:
        notes.append("FAIL: the hover handler never calls _update_clear_aperture_hover_highlight")
        passed = False

    # G. Right-click menu items.
    menu_src = inspect.getsource(Open3DFaceAssignmentService)
    for label in (
        "Set Clear Aperture (pick window face)...",
        "Center Clear Aperture -> Optical Axis",
        "Forget Clear Aperture",
    ):
        if label not in menu_src:
            notes.append(f"FAIL: the right-click menu no longer offers '{label}'")
            passed = False
    for handler in ("_center_clear_aperture_from_context", "_clear_clear_aperture_from_context"):
        if not hasattr(Open3DFaceAssignmentService, handler):
            notes.append(f"FAIL: Open3DFaceAssignmentService is missing {handler}")
            passed = False

    # H. Persistent highlight in BOTH draw paths.
    if "_add_clear_aperture_highlight_actor(label)" not in _read(
        "KrakenOS/UI/services/open3d_step_overlay_refresh.py"
    ):
        notes.append("FAIL: the partial overlay refresh does not draw the persistent CA highlight")
        passed = False
    if "_add_clear_aperture_highlight_actor(label)" not in _read(
        "KrakenOS/UI/services/open3d_scene_refresh.py"
    ):
        notes.append("FAIL: the full scene refresh does not draw the persistent CA highlight")
        passed = False

    # I. Save/reload of the persisted CA.
    settings_src = _read("KrakenOS/UI/services/layout_settings.py")
    if settings_src.count("step_clear_aperture_by_label") < 2:
        notes.append(
            "FAIL: layout_settings.py does not both save and load 'step_clear_aperture_by_label' "
            "-- a recorded CA must survive save/reload (bugs/0134)"
        )
        passed = False

    if verbose:
        notes.append(
            "checked: picker-aligned cell->face on a 14-stray-line mesh; editor set/read/center/clear; "
            "real LED vtp (when cached); pick routing, inspector pick mode, right-click menu, "
            "persistent highlight in both refresh paths, and CA save/reload"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0134: clear-aperture pick + persisted CA")
        return 0
    print("[FAIL] bugs/0134 clear-aperture guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
