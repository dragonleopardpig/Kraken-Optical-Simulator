"""Reusable "Constraints (Design)" widget -- pin first-order knowns, solve for the lens.

Embeds in the left Quick Estimation panel AND the FOV / detector double-click popups so
the same quick "what lens do I need?" UI is available wherever the user is working. All the
optics lives in ``quick_estimation`` (``resolve_design_system`` / ``design_quantity_states``);
this is pure Tk wiring over one service call (``design_constraint_view``). Advisory only --
it never moves the layout. Checkboxes gray out once the 2-DOF budget is spent, and the locked
quantities show their solved values; the result line shows the required EFL + conjugates.

Two layouts:

* full (left panel) -- all five constraint rows.
* ``compact`` (popups) -- a popup already fixes one constraint by context (the object-FOV
  plane fixes the object field; a detector fixes the image side). A ``context_provider``
  supplies those pre-pinned quantities live; the widget hides them (and the magnification
  twin of a pinned FOV), shows a one-line "From this view: ..." note, and asks only for the
  one remaining input -- "context fixes X, pin one more to size the lens".
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from KrakenOS.UI.services.quick_estimation import (
    DESIGN_IMAGE_DISTANCE,
    DESIGN_MAGNIFICATION,
    DESIGN_OBJECT_DISTANCE,
    DESIGN_OBJECT_FOV_SEMI,
    DESIGN_TOTAL_TRACK,
)

# (quantity, label, unit) in display order.
_DESIGN_ROWS = (
    (DESIGN_MAGNIFICATION, "Magnification", "x"),
    (DESIGN_OBJECT_DISTANCE, "Object distance", "mm"),
    (DESIGN_IMAGE_DISTANCE, "Image distance", "mm"),
    (DESIGN_TOTAL_TRACK, "Total track", "mm"),
    (DESIGN_OBJECT_FOV_SEMI, "Object FOV (semi)", "mm"),
)
_LABELS = {q: label for q, label, _unit in _DESIGN_ROWS}
# magnification and object FOV are the same DOF -- pinning one locks the other.
_TWIN = {DESIGN_MAGNIFICATION: DESIGN_OBJECT_FOV_SEMI, DESIGN_OBJECT_FOV_SEMI: DESIGN_MAGNIFICATION}
_STATUS_COLORS = {
    "balanced": "#1a6d2f",
    "under": "#7a5b00",
    "over": "#8a2b2b",
    "invalid": "#8a2b2b",
}


class DesignConstraintControls:
    """A drop-in design-mode constraint/solve block. Build it into any frame.

    ``context_provider`` (optional) returns a live ``{quantity: value}`` dict of
    constraints fixed by the host view (e.g. the object FOV of the plane that was
    double-clicked). In ``compact`` builds those rows are hidden and shown as a note.
    """

    def __init__(self, inspector: Any, *, context_provider: Callable[[], dict] | None = None) -> None:
        self.inspector = inspector
        self.context_provider = context_provider
        self._fix: dict[str, tk.BooleanVar] = {}
        self._val: dict[str, tk.StringVar] = {}
        self._checks: dict[str, ttk.Checkbutton] = {}
        self._entries: dict[str, ttk.Entry] = {}
        self._result_var: tk.StringVar | None = None
        self._result_label: ttk.Label | None = None
        self._context_var: tk.StringVar | None = None

    def _context(self) -> dict[str, float]:
        if self.context_provider is None:
            return {}
        try:
            raw = self.context_provider() or {}
        except Exception:
            return {}
        out: dict[str, float] = {}
        for q, v in raw.items():
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if fv == fv:  # not NaN
                out[q] = fv
        return out

    def build(self, parent: tk.Widget, *, start_row: int = 0, show_separator: bool = True, compact: bool = False) -> None:
        row = start_row
        if show_separator:
            ttk.Separator(parent, orient="horizontal").grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=4
            )
            row += 1
        ttk.Label(
            parent,
            text="Design lens -- pin knowns, solve for the EFL",
            foreground="#555555",
            justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        # Which rows are fixed by context (hidden in compact builds) -- a context FOV
        # pin also hides its magnification twin (same DOF).
        context_keys = set(self._context()) if compact else set()
        hidden = set(context_keys)
        for key in context_keys:
            if key in _TWIN:
                hidden.add(_TWIN[key])

        if compact:
            self._context_var = tk.StringVar(value="")
            ttk.Label(
                parent, textvariable=self._context_var, foreground="#1a6d2f", justify="left", wraplength=260
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 2))
            row += 1

        grid = ttk.Frame(parent)
        grid.grid(row=row, column=0, columnspan=2, sticky="ew")
        grid.columnconfigure(1, weight=1)
        row += 1
        grid_row = 0
        for quantity, label, unit in _DESIGN_ROWS:
            if quantity in hidden:
                continue
            fix = tk.BooleanVar(value=False)
            val = tk.StringVar(value="")
            self._fix[quantity] = fix
            self._val[quantity] = val
            chk = ttk.Checkbutton(grid, text=label, variable=fix, command=self.recompute)
            chk.grid(row=grid_row, column=0, sticky="w", pady=1)
            ent = ttk.Entry(grid, textvariable=val, width=10)
            ent.grid(row=grid_row, column=1, sticky="ew", padx=(6, 0), pady=1)
            ent.bind("<Return>", lambda _e: self.recompute())
            ent.bind("<FocusOut>", lambda _e: self.recompute())
            ttk.Label(grid, text=unit, foreground="#777777").grid(
                row=grid_row, column=2, sticky="w", padx=(2, 0)
            )
            self._checks[quantity] = chk
            self._entries[quantity] = ent
            grid_row += 1

        default_msg = (
            "Pin one more to size the lens." if context_keys else "Pin two knowns to size the lens."
        )
        self._result_var = tk.StringVar(value=default_msg)
        self._result_label = ttk.Label(
            parent, textvariable=self._result_var, foreground="#1a3b6d", justify="left", wraplength=260
        )
        self._result_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))
        row += 1
        buttons = ttk.Frame(parent)
        buttons.grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Button(buttons, text="Compute lens", command=self.recompute).grid(row=0, column=0, sticky="w")
        ttk.Button(buttons, text="Apply to layout", command=self.apply).grid(
            row=0, column=1, sticky="w", padx=(6, 0)
        )
        self.recompute()

    def _collect_pins(self) -> dict[str, float]:
        pins: dict[str, float] = {}
        for quantity, fix_var in self._fix.items():
            try:
                if not bool(fix_var.get()):
                    continue
            except Exception:
                continue
            raw = self._val[quantity].get().strip()
            if not raw:
                continue
            try:
                pins[quantity] = float(raw)
            except ValueError:
                continue
        return pins

    def recompute(self) -> None:
        if not self._fix and self.context_provider is None:
            return
        context = self._context()
        pins = {**context, **self._collect_pins()}
        try:
            view = self.inspector._quick_estimation_service().design_constraint_view(pins)
        except Exception:
            return
        states = view.get("states", {}) or {}
        result = view.get("result", {}) or {}
        for quantity, chk in self._checks.items():
            state = (states.get(quantity) or {}).get("state", "available")
            ent = self._entries[quantity]
            if state == "locked":
                chk.state(["disabled"])
                ent.state(["disabled"])
                value = (states.get(quantity) or {}).get("value")
                if value is not None:
                    try:
                        self._val[quantity].set(f"{float(value):.4g}")
                    except (TypeError, ValueError):
                        pass
            else:
                chk.state(["!disabled"])
                ent.state(["!disabled"])
        if self._context_var is not None:
            if context:
                note = ", ".join(f"{_LABELS.get(q, q)} = {v:.4g}" for q, v in context.items())
                self._context_var.set(f"From this view: {note}")
            else:
                self._context_var.set("")
        if self._result_var is not None:
            self._result_var.set(result.get("message") or "Pin the remaining knowns to size the lens.")
        if self._result_label is not None:
            try:
                self._result_label.configure(
                    foreground=_STATUS_COLORS.get(result.get("status"), "#1a3b6d")
                )
            except Exception:
                pass

    def apply(self) -> None:
        """Apply the solve to the LAYOUT: move the object/image gaps to the solved
        conjugates (the EFL stays advisory). Merges context + user pins and routes to
        the inspector, which owns history + retrace. No-op unless the system is
        balanced (apply_design rejects under/over/invalid)."""
        if not self._fix and self.context_provider is None:
            return
        pins = {**self._context(), **self._collect_pins()}
        try:
            self.inspector._apply_design_constraints(pins)
        except Exception:
            return
        self.recompute()
