"""Main layout-editor analysis controls and information panel."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from KrakenOS.UI.analysis_modes import (MODE_GROUPS, MODE_TOOLTIPS, MODES, PICKER_HINT,
                                        selection_label)


class _EditorBackedPanel:
    """Delegate widget-owned state back to the layout editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)


class MainAnalysisToolbarPanel(_EditorBackedPanel):
    """Build the 2D plot analysis toolbar."""

    def build(self, parent: tk.Widget) -> None:
        # the plots, their grouping and their tooltips are data now (bugs/0899), so the Qt
        # shell can offer the same 24
        mode_button_groups = MODE_GROUPS
        mode_tooltips = MODE_TOOLTIPS
        self.analysis_mode_vars = {mode: tk.BooleanVar(value=False) for mode in MODES}
        ttk.Label(parent, text="Analysis").pack(side="left", padx=(0, 4))
        # Custom multi-select dropdown instead of a tk.Menu: a tk.Menu unposts on
        # every checkbutton click, but the user wants to tick several plots in one
        # pass, so this panel stays open until they click away / press Esc / Close.
        trigger = ttk.Button(
            parent, text="Select plots ▾", style="Toolbutton",
            command=self._toggle_analysis_dropdown,
        )
        trigger.pack(side="left", padx=(4, 0))
        self.analysis_mode_menubutton = trigger
        self.analysis_mode_menu = None
        self._analysis_dropdown_groups = mode_button_groups
        self._analysis_dropdown_tooltips = mode_tooltips
        self._analysis_dropdown_popup = None
        self._analysis_dropdown_outside_bind = None
        self._add_widget_tooltip(trigger, PICKER_HINT)

        # Real (z-buffered) 3D wavefront surface, alongside the 2D Zemax waterfall.
        wavefront_3d_button = ttk.Button(
            parent,
            text="WFront 3D",
            style="Toolbutton",
            command=self.open_wavefront_3d_view,
        )
        wavefront_3d_button.pack(side="left", padx=(6, 0))
        self.wavefront_3d_button = wavefront_3d_button
        self._add_widget_tooltip(
            wavefront_3d_button,
            "Open the latest Wavefront analysis as a real, rotatable 3D surface "
            "(PyVista/VTK). Run the Wavefront plot first.",
        )

    # -- Multi-select analysis dropdown (stays open across ticks) -------------

    def _toggle_analysis_dropdown(self) -> None:
        popup = getattr(self, "_analysis_dropdown_popup", None)
        if popup is not None and popup.winfo_exists():
            self._close_analysis_dropdown()
        else:
            self._open_analysis_dropdown()

    def _open_analysis_dropdown(self) -> None:
        trigger = self.analysis_mode_menubutton
        if trigger is None or not trigger.winfo_exists():
            return
        popup = tk.Toplevel(trigger)
        # Build hidden, then map at an explicit geometry: an override-redirect
        # window otherwise maps at the screen origin first (it lands top-left,
        # partly under the desktop bar) before any +x+y request is honoured.
        popup.withdraw()
        popup.wm_overrideredirect(True)
        try:
            popup.attributes("-topmost", True)
        except Exception:
            pass
        # Thin border (override-redirect windows have no frame of their own).
        border = tk.Frame(popup, background="#888c94")
        border.pack(fill="both", expand=True)
        body = ttk.Frame(border, padding=6)
        body.pack(fill="both", expand=True, padx=1, pady=1)
        ttk.Label(
            body, text="Analysis plots — tick multiple",
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor="w", pady=(0, 4))
        for group_index, group in enumerate(self._analysis_dropdown_groups):
            if group_index > 0:
                ttk.Separator(body, orient="horizontal").pack(fill="x", pady=3)
            for text, mode in group:
                ttk.Checkbutton(
                    body,
                    text=self._analysis_dropdown_tooltips.get(mode, text),
                    variable=self.analysis_mode_vars[mode],
                    command=lambda m=mode: self.toggle_analysis_mode(m),
                ).pack(anchor="w", fill="x")
        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=3)
        ttk.Button(
            body, text="Close", style="Toolbutton",
            command=self._close_analysis_dropdown,
        ).pack(anchor="e")

        popup.update_idletasks()
        pop_w = max(popup.winfo_reqwidth(), 1)
        pop_h = max(popup.winfo_reqheight(), 1)
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        # Anchor just below the trigger button (absolute screen coords), clamped
        # on-screen in both axes so it never lands under the bar or off an edge.
        x = trigger.winfo_rootx()
        y = trigger.winfo_rooty() + trigger.winfo_height()
        x = max(0, min(int(x), screen_w - pop_w))
        y = max(0, min(int(y), screen_h - pop_h))
        # Full WxH+x+y, then map: deiconify after the geometry is set so it
        # appears at the requested spot rather than the origin.
        popup.wm_geometry(f"{pop_w}x{pop_h}+{x}+{y}")
        popup.deiconify()
        popup.lift()
        popup.update_idletasks()
        try:
            popup.focus_set()
        except Exception:
            pass
        popup.bind("<Escape>", lambda _e: self._close_analysis_dropdown())
        toplevel = trigger.winfo_toplevel()
        self._analysis_dropdown_outside_bind = toplevel.bind(
            "<Button-1>", self._analysis_dropdown_outside_click, add="+"
        )
        self._analysis_dropdown_popup = popup

    def _analysis_dropdown_outside_click(self, event) -> None:
        popup = getattr(self, "_analysis_dropdown_popup", None)
        if popup is None or not popup.winfo_exists():
            return
        px, py = event.x_root, event.y_root

        def _inside(widget) -> bool:
            try:
                wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
                return (
                    wx <= px <= wx + widget.winfo_width()
                    and wy <= py <= wy + widget.winfo_height()
                )
            except Exception:
                return False

        if not _inside(popup) and not _inside(self.analysis_mode_menubutton):
            self._close_analysis_dropdown()

    def _close_analysis_dropdown(self) -> None:
        popup = getattr(self, "_analysis_dropdown_popup", None)
        self._analysis_dropdown_popup = None
        bind_id = getattr(self, "_analysis_dropdown_outside_bind", None)
        if bind_id:
            try:
                self.analysis_mode_menubutton.winfo_toplevel().unbind("<Button-1>", bind_id)
            except Exception:
                pass
            self._analysis_dropdown_outside_bind = None
        if popup is not None:
            try:
                popup.destroy()
            except Exception:
                pass


class MainInformationPanel(_EditorBackedPanel):
    """Build the right-side information table."""

    def build(self, parent: tk.Widget) -> None:
        self.results_table = ttk.Treeview(parent, columns=("property", "value"), show="headings", selectmode="none")
        self.results_table.heading("property", text="Property")
        self.results_table.heading("value", text="Value")
        self.results_table.column("property", width=96, anchor="w", stretch=False)
        self.results_table.column("value", width=40, anchor="w", stretch=True)
        self.results_table.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.results_table.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.results_table.configure(yscrollcommand=scroll.set)
