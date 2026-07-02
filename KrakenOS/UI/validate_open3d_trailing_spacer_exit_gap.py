"""Display-free guard for bugs/0202 (#3): a promoted solid's trailing AIR spacer must
anchor its NEAR thickness arrow to the solid's EXIT face, not the reserve origin past it.

Flag_20260701_201444 ("S2 thickness overlay: one side arrow still point to wrong
location"): on the folded AZ85 RA-mirror scene the mirror cube (row 1) is promoted with a
40 mm axial reserve, but the physical cube exit face sits only 12.5 mm past the fold
vertex. The trailing AIR spacer (row 2, ``InPathTrailingSpacer``) took its NEAR endpoint
from the row reference (X=40, ~27.5 mm downstream of the cube exit at X=12.5), so its near
arrow + leader floated in mid-air on the beam instead of landing on the mirror's exit face.

Fix (bugs/0202): ``_solid_exit_gap_for_trailing_spacer`` -- the exit-side mirror of the
"gap to solid" entry handling -- re-anchors the near endpoint to the solid EXIT face and
labels the REAL air gap (mirror exit -> front datum = 69.95 mm). The displayed gap differs
from the stored thickness by the reserve dead-space (27.5 mm), so the edit dialog prefill +
``apply_dimension_value`` round-trip that offset (``_trailing_spacer_gap_offset``) to stay
WYSIWYG with the drawn value.

Asserts (real methods bound onto light fakes; the exit face is synthesised from the cube
world bounds so the guard runs headless without a renderer):
  1. the helper anchors the NEAR endpoint to the cube exit (X=12.5), not the reserve
     origin (X=40) -- the ~27.5 mm float is gone;
  2. the drawn gap is the true mirror-exit -> front-datum distance (~69.95 mm) and the
     offset = gap - stored thickness = ~27.5 mm;
  3. NON-spacer rows + a scene with no promoted solid return None (no false anchor);
  4. editing the drawn gap round-trips: apply(row, G) stores thickness G - offset, so the
     front datum lands exactly G past the mirror exit;
  5. source contract: add_overlays records the offset + uses solid_exit_gap_label; the
     edit dialog + apply consult _trailing_spacer_gap_offset.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_trailing_spacer_exit_gap
Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import inspect as _inspect
import io
import sys

import numpy as np

from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService as S

# Cube world bounds along the folded +X beam: [-12.5, 12.5] at Y=0, Z=71.9 (the RA-mirror
# right-angle prism promoted in machine_vision_AZ85_RA_Mirror.py).
_CUBE_MIN_X = -12.5
_CUBE_EXIT_X = 12.5
_SOLID_ROW = 1
_SPACER_ROW = 2


class _CubeInspector:
    """Feeds the cube's rendered axial extent for row 1 (row 2 = the trailing spacer)."""

    def _all_actor_keys_for_row(self, ri):
        return ["cube"] if int(ri) == _SOLID_ROW else None

    def _axial_extent_from_actor_keys(self, keys, axis):
        pts = np.array([[_CUBE_MIN_X, 0.0, 71.9], [_CUBE_EXIT_X, 0.0, 71.9]])
        proj = pts @ np.asarray(axis, dtype=float)
        return {"proj_min": float(proj.min()), "proj_max": float(proj.max())}


class _GeomSvc:
    _solid_exit_gap_for_trailing_spacer = S._solid_exit_gap_for_trailing_spacer
    _optical_solid_span_points = S._optical_solid_span_points
    _row_optical_solid_stl = staticmethod(S._row_optical_solid_stl)
    _row_short_name = staticmethod(S._row_short_name)

    def __init__(self, inspector):
        self.inspector = inspector


# ---- edit round-trip fakes (mirror validate_open3d_gap_to_solid_slide) ----
class _QE:
    def is_enabled(self):
        return False

    def solve_dependent(self, _i):
        return True, ""

    def update_readout(self):
        pass


class _Var:
    def set(self, message):
        self.last = message


class _Ed:
    def __init__(self, rows):
        self.rows = rows
        self.status_var = _Var()

    def _dimension_anchor_override_for_row(self, _i):
        return None

    def _begin_history_capture(self):
        pass

    def _commit_history_capture(self):
        pass

    def _sync_table(self):
        pass

    def _select_table_row(self, _i):
        pass

    def _invalidate_preview_scene_trace(self):
        pass

    def _sync_trace_state_badge(self):
        pass

    def append_debug(self, _m):
        pass


class _Insp:
    def __init__(self):
        self.status_var = _Var()

    def _quick_estimation_service(self):
        return _QE()

    def refresh_from_editor(self, **_k):
        pass


class _EditSvc:
    apply_dimension_value = S.apply_dimension_value
    _solid_slide_compensation_row = S._solid_slide_compensation_row
    _row_optical_solid_stl = staticmethod(S._row_optical_solid_stl)

    def __init__(self, editor, inspector):
        self.editor = editor
        self.inspector = inspector


def _az85_rows():
    from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
    return editor.rows


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    rows = _az85_rows()
    svc = _GeomSvc(_CubeInspector())

    # The spacer's own reference points (near = reserve origin X=40, far = front datum X=82.45).
    p0 = np.array([40.0, 0.0, 71.9])
    p1 = np.array([82.4528629414, 0.0, 71.9])
    thickness = float(rows[_SPACER_ROW].thickness)

    exit_pt, label, gap = svc._solid_exit_gap_for_trailing_spacer(rows, _SPACER_ROW, p0, p1)

    # (1) near endpoint re-anchored to the cube exit, not the floating reserve origin.
    if exit_pt is None:
        failures.append("helper returned None on the trailing spacer (the exit anchor did not engage)")
    else:
        float_before = float(abs(p0[0] - _CUBE_EXIT_X))  # 27.5 mm float in the OLD path
        if abs(float(exit_pt[0]) - _CUBE_EXIT_X) > 1e-6:
            failures.append(
                f"near endpoint not on the cube exit: X={float(exit_pt[0]):.3f} vs {_CUBE_EXIT_X}"
            )
        if float(abs(exit_pt[1])) > 1e-6 or abs(float(exit_pt[2]) - 71.9) > 1e-6:
            failures.append(f"near endpoint left the beam line: {np.round(exit_pt, 4).tolist()}")
        if not (float_before > 20.0):
            failures.append("sanity: the OLD reserve origin was not ~27.5mm past the exit")

    # (2) drawn gap = true mirror-exit -> front-datum distance; offset = gap - thickness.
    if gap is not None:
        expected_gap = float(abs(p1[0] - _CUBE_EXIT_X))  # 69.95
        if abs(float(gap) - expected_gap) > 1e-3:
            failures.append(f"drawn gap {gap:.4f} != true exit->datum {expected_gap:.4f}")
        offset = float(gap) - thickness
        if abs(offset - 27.5) > 1e-2:
            failures.append(f"reserve dead-space offset {offset:.4f} != 27.5 (gap {gap:.4f} - thk {thickness:.4f})")
        if label is None or "gap from" not in label:
            failures.append(f"label is not a 'gap from solid' measurement: {label!r}")
        else:
            notes.append(f"drawn gap={gap:.4f}mm (thk {thickness:.4f}, offset {offset:.4f}); label={label!r}")

    # (3) non-spacer rows + a solid-less scene return None (no false anchor).
    if svc._solid_exit_gap_for_trailing_spacer(rows, 3, np.array([82.45, 0, 71.9]), np.array([100.09, 0, 71.9]))[0] is not None:
        failures.append("front-datum row wrongly claimed a trailing-spacer exit anchor")
    if svc._solid_exit_gap_for_trailing_spacer(rows, _SOLID_ROW, np.array([0.0, 0, 71.9]), p0)[0] is not None:
        failures.append("the solid row itself wrongly claimed a trailing-spacer exit anchor")

    # (4) editing the drawn gap round-trips to the stored thickness (WYSIWYG).
    edit_rows = _az85_rows()
    edit_svc = _EditSvc(_Ed(edit_rows), _Insp())
    edit_svc._trailing_spacer_gap_offset = {_SPACER_ROW: 27.5}
    typed_gap = 80.0
    ok = edit_svc.apply_dimension_value(_SPACER_ROW, typed_gap)
    stored = float(edit_rows[_SPACER_ROW].thickness)
    if not ok:
        failures.append("apply_dimension_value returned False on the trailing spacer")
    if abs(stored - (typed_gap - 27.5)) > 1e-6:
        failures.append(
            f"edit did not round-trip: typed gap {typed_gap} -> stored thk {stored:.4f} "
            f"(expected {typed_gap - 27.5:.4f}); drawn gap would read {stored + 27.5:.4f}"
        )
    else:
        notes.append(f"edit round-trip: typed gap {typed_gap} -> stored thk {stored:.4f} -> redraw gap {stored + 27.5:.4f}")

    # A row with NO recorded offset edits its raw thickness unchanged (plain WYSIWYG).
    plain_rows = _az85_rows()
    plain_svc = _EditSvc(_Ed(plain_rows), _Insp())
    plain_svc._trailing_spacer_gap_offset = {}
    plain_svc.apply_dimension_value(3, 20.0)
    if abs(float(plain_rows[3].thickness) - 20.0) > 1e-6:
        failures.append("a non-spacer row's edit was wrongly offset")

    # (5) source contract.
    add_src = _inspect.getsource(S.add_overlays)
    if "_solid_exit_gap_for_trailing_spacer" not in add_src or "_trailing_spacer_gap_offset" not in add_src:
        failures.append("add_overlays source does not record the trailing-spacer exit gap/offset")
    if "solid_exit_gap_label" not in _inspect.getsource(S.add_overlays):
        failures.append("add_overlays source does not label the exit gap")
    if "_trailing_spacer_gap_offset" not in _inspect.getsource(S.apply_dimension_value):
        failures.append("apply_dimension_value does not consult the trailing-spacer offset")
    if "_trailing_spacer_gap_offset" not in _inspect.getsource(S.edit_dimension):
        failures.append("edit_dimension does not prefill the trailing-spacer drawn gap")

    if failures:
        print("FAIL bugs/0202 trailing-spacer exit gap:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("PASS bugs/0202 trailing spacer anchors its near arrow to the solid exit face:")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
