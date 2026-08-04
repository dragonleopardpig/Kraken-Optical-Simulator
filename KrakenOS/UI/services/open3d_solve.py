"""Open 3D Variable thickness + Best Focus / Best Collimation solves.

Brings the 2D "mark a thickness Variable, solve for best image" workflow into
the embedded Open 3D inspector. A thickness is marked *Variable* by setting the
shared ``SurfaceRow.optimize_thickness`` flag -- the same flag the 2D
optimization path uses -- so a thickness flagged in 3D shows up Variable in 2D
and vice versa.

Two solves run over the variable thickness gaps, reusing the editor's existing
1-D minimisers:

* **Best Focus** minimises the image-plane spot RMS
  (``editor._compute_best_focus_result``); the Object and terminal Image gaps
  are not valid focus targets.
* **Best Collimation** minimises the exit-ray angular spread
  (``editor._compute_best_collimation_result``); the object gap *is* a valid
  collimation target (moving the source toward the focal point parallelises the
  exit beam), only the terminal image gap is excluded.

For a single Variable each solve is the editor's 1-D solve; for several the
service runs a few coordinate-descent passes (solve each gap in turn against the
current layout until the gaps stop moving). The service only mutates
``editor.rows[i].thickness`` -- the caller owns history capture and the retrace.
"""

from __future__ import annotations

from typing import Any

FOCUS = "focus"
COLLIMATION = "collimation"

# Coordinate-descent stops when every gap moves less than this between passes.
_CONVERGENCE_TOL_MM = 1e-4
_MAX_PASSES = 4


class Open3DSolveService:
    """Variable-thickness Best Focus / Best Collimation solver for Open 3D."""

    def __init__(self, inspector: Any) -> None:
        self.inspector = inspector
        self.editor = inspector.editor

    # ----------------------------------------------------------------- rows
    def _rows(self) -> list:
        return list(getattr(self.editor, "rows", None) or [])

    def thickness_gap_rows(self) -> list[tuple[int, str]]:
        """``(row_index, label)`` for every gap whose thickness can be a Variable.

        Every row carries a thickness gap except the terminal Image plane, which
        is the axial reference, not a free gap.
        """
        rows = self._rows()
        gaps: list[tuple[int, str]] = []
        for index, row in enumerate(rows):
            if str(getattr(row, "surface", "")) == "Image":
                continue
            label = str(getattr(row, "name", "") or getattr(row, "surface", "") or f"Row {index}")
            gaps.append((index, f"{index}: {label}"))
        return gaps

    def is_variable(self, row_index: int) -> bool:
        rows = self._rows()
        if not (0 <= row_index < len(rows)):
            return False
        return bool(getattr(rows[row_index], "optimize_thickness", False))

    def set_variable(self, row_index: int, enabled: bool) -> None:
        rows = self._rows()
        if 0 <= row_index < len(rows):
            rows[row_index].optimize_thickness = bool(enabled)

    def toggle_variable(self, row_index: int) -> bool:
        new_state = not self.is_variable(row_index)
        self.set_variable(row_index, new_state)
        return new_state

    def variable_rows(self) -> list[int]:
        return [index for index, _label in self.thickness_gap_rows() if self.is_variable(index)]

    def _valid_rows_for(self, objective: str) -> list[int]:
        rows = self._rows()
        valid: list[int] = []
        for index in self.variable_rows():
            surface = str(getattr(rows[index], "surface", ""))
            if surface == "Image":
                continue
            if objective == FOCUS and surface == "Object":
                continue  # the object gap is not a focus target
            valid.append(index)
        return valid

    # ---------------------------------------------------------------- solve
    def _compute(self, objective: str, row_index: int) -> dict[str, Any]:
        if objective == COLLIMATION:
            return self.editor._compute_best_collimation_result(row_index)
        return self.editor._compute_best_focus_result(row_index)

    def solve(self, objective: str) -> tuple[bool, str]:
        """Solve the variable thickness gaps for ``objective`` ("focus" or
        "collimation"). Mutates ``editor.rows[i].thickness`` in place; does NOT
        capture history or retrace -- the caller owns that."""
        if objective not in (FOCUS, COLLIMATION):
            return False, f"Unknown solve objective: {objective!r}."
        if not self.variable_rows():
            return False, "Mark at least one thickness as Variable first."
        target_rows = self._valid_rows_for(objective)
        if not target_rows:
            if objective == FOCUS:
                return False, "No Variable gap is a valid Best Focus target (the object gap is collimation-only)."
            return False, "No Variable gap is a valid Best Collimation target."

        verb = "collimation" if objective == COLLIMATION else "focus"
        passes = 1 if len(target_rows) == 1 else _MAX_PASSES
        last_metric: float | None = None
        per_row: dict[int, float] = {}
        clamped: list[int] = []
        try:
            for _pass in range(passes):
                max_change = 0.0
                for row_index in target_rows:
                    result = self._compute(objective, row_index)
                    solved = float(result["solved_distance"])
                    metric = result.get("best_rms", result.get("best_metric"))
                    if metric is not None:
                        last_metric = float(metric)
                    # bugs/0550 (flag_20260805_072959, "Extra rays out of bound"): a gap is a
                    # DISTANCE, so it may never go negative -- a negative thickness makes the
                    # station chain run BACKWARDS across that row (measured on
                    # machine_vision_Apo75: rear datum 83.381, then -13.595, so station
                    # 252.355 -> 238.760) and the trace loses its next surface. Census on that
                    # scene: 375 no_next_intersection / 93 reaching, against 279 / 225 with the
                    # gap merely zeroed -- i.e. the negative gap accounts for essentially all
                    # the out-of-bound rays. This writer had NO lower bound at all; the
                    # paraxial solvers it calls bound their own search at 0, so a negative here
                    # means the objective wanted to pull the element THROUGH its predecessor.
                    # Clamp and SAY SO rather than committing a chain that cannot be traced.
                    if solved < 0.0:
                        clamped.append(int(row_index))
                        solved = 0.0
                    change = abs(solved - float(self.editor.rows[row_index].thickness))
                    self.editor.rows[row_index].thickness = solved
                    per_row[row_index] = solved
                    if change > max_change:
                        max_change = change
                if max_change < _CONVERGENCE_TOL_MM:
                    break
        except Exception as exc:  # pragma: no cover - defensive
            return False, f"Best {verb} solve failed: {exc}"

        gaps = ", ".join(f"row {i} -> {per_row[i]:.6g} mm" for i in target_rows)
        metric_text = ""
        if last_metric is not None:
            if objective == COLLIMATION:
                metric_text = f" | output vergence={last_metric:.6g} /mm"
            else:
                metric_text = f" | spot RMS={last_metric:.6g} mm"
        clamp_text = ""
        if clamped:
            rows_text = ", ".join(f"row {i}" for i in sorted(set(clamped)))
            clamp_text = (
                f" | CLAMPED to 0 mm at {rows_text}: best {verb} wants that element AHEAD of its "
                "predecessor -- move the element itself, or free a different gap"
            )
        return True, f"Best {verb} solve: {gaps}{metric_text}{clamp_text}."
