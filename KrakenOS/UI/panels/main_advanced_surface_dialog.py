"""Advanced native surface-attribute editor dialog."""

from __future__ import annotations

from dataclasses import asdict
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.advanced_surface import build_advanced_surface_form


class MainAdvancedSurfaceDialog:
    """Build the advanced surface dialog while keeping row state on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        advanced_row_shape_fields: tuple[tuple[str, str, str], ...],
        advanced_surface_field_groups: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
        advanced_surface_attr_names: tuple[str, ...],
        variable_registry: dict[str, object],
        column_labels: dict[str, str],
        literal_editor_text: Callable[[object], tuple[str, bool]],
        parse_literal_editor_text: Callable[[str], object],
        format_float_sequence: Callable[[object], str],
        parse_float_sequence_text: Callable[[str], list[float]],
        validate_advanced_surface_inputs: Callable[[dict[str, object], object, object], tuple[list[str], list[str]]],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "advanced_row_shape_fields", tuple(advanced_row_shape_fields))
        object.__setattr__(self, "advanced_surface_field_groups", tuple(advanced_surface_field_groups))
        object.__setattr__(self, "advanced_surface_attr_names", tuple(advanced_surface_attr_names))
        object.__setattr__(self, "variable_registry", dict(variable_registry))
        object.__setattr__(self, "column_labels", dict(column_labels))
        object.__setattr__(self, "literal_editor_text", literal_editor_text)
        object.__setattr__(self, "parse_literal_editor_text", parse_literal_editor_text)
        object.__setattr__(self, "format_float_sequence", format_float_sequence)
        object.__setattr__(self, "parse_float_sequence_text", parse_float_sequence_text)
        object.__setattr__(self, "validate_advanced_surface_inputs", validate_advanced_surface_inputs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "advanced_row_shape_fields",
            "advanced_surface_field_groups",
            "advanced_surface_attr_names",
            "variable_registry",
            "column_labels",
            "literal_editor_text",
            "parse_literal_editor_text",
            "format_float_sequence",
            "parse_float_sequence_text",
            "validate_advanced_surface_inputs",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open(self, row_index: int | None = None) -> None:
        # docs/design_qt_migration.md phase 3: the fields, their tabs, which ones are locked, the
        # validation and what Apply writes live in KrakenOS/UI/row_forms/advanced_surface.py,
        # which the Qt dialog uses too. What stays here is Tk layout -- the scrolling tabs and
        # their wheel binding, which have no counterpart on the other side.
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Advanced Surface",
                                 f"Could not read the surface table:\n\n{exc}",
                                 parent=self.editor)
            return

        try:
            form = build_advanced_surface_form(self, row_index)
        except FormRefused as exc:
            messagebox.showinfo("Advanced Surface", str(exc), parent=self.editor)
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(form.title)
        window.geometry("980x640")
        window.minsize(880, 560)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        ttk.Label(window, text=form.note, foreground="#5f6b7a", wraplength=940,
                  justify="left", padding=(10, 10, 10, 0)).grid(row=0, column=0, sticky="ew")

        notebook = ttk.Notebook(window)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 8))

        # Each tab scrolls its own body: the Diagnostics/Native group alone is ~30 rows (taller
        # than the screen), which used to grow the dialog past the screen edges with no scrollbar
        # (the title tucked under the top/AGS bar). A canvas+scrollbar per tab keeps the dialog
        # screen-sized and every field reachable.
        scroll_tabs: list[tuple[tk.Canvas, ttk.Frame]] = []

        def make_scroll_tab(title: str) -> ttk.Frame:
            host = ttk.Frame(notebook)
            host.columnconfigure(0, weight=1)
            host.rowconfigure(0, weight=1)
            notebook.add(host, text=title)
            canvas = tk.Canvas(host, highlightthickness=0)
            vscroll = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=vscroll.set)
            canvas.grid(row=0, column=0, sticky="nsew")
            inner = ttk.Frame(canvas, padding=(0, 8, 0, 8))
            window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

            def _update_scroll(_event=None) -> None:
                try:
                    canvas.configure(scrollregion=canvas.bbox("all"))
                    overflow = inner.winfo_reqheight() > canvas.winfo_height()
                    if overflow and not vscroll.grid_info():
                        vscroll.grid(row=0, column=1, sticky="ns")
                    elif not overflow and vscroll.grid_info():
                        vscroll.grid_remove()
                except tk.TclError:
                    pass

            def _on_canvas_configure(event) -> None:
                # the inner form fills the canvas width (the column-2 stretch + label wraplengths
                # lay out) and at least the canvas height (a short tab is not clipped); v-scroll only.
                fill_height = max(int(event.height), inner.winfo_reqheight())
                canvas.itemconfigure(window_id, width=int(event.width), height=fill_height)
                _update_scroll()

            inner.bind("<Configure>", lambda _e: _update_scroll(), add="+")
            canvas.bind("<Configure>", _on_canvas_configure, add="+")
            scroll_tabs.append((canvas, inner))
            return inner

        attr_entries: dict[str, tuple[ttk.Entry, bool]] = {}
        row_shape_entries: dict[str, tuple[ttk.Entry, bool]] = {}

        variables: dict[str, tk.StringVar] = {}
        booleans: dict[str, tk.BooleanVar] = {}

        for group in form.groups:
            frame = make_scroll_tab(group)
            frame.columnconfigure(2, weight=1)
            for offset, field in enumerate(form.fields_in(group)):
                ttk.Label(frame, text=field.label).grid(row=offset, column=0, sticky="w",
                                                        padx=(8, 6), pady=3)
                if field.kind == "bool":
                    variable = tk.BooleanVar(master=window,
                                             value=str(form.values.get(field.key, "")).strip()
                                             .lower() in ("1", "true", "yes", "on"))
                    booleans[field.key] = variable
                    widget = ttk.Checkbutton(frame, variable=variable)
                else:
                    variable = tk.StringVar(master=window,
                                            value=form.values.get(field.key, ""))
                    variables[field.key] = variable
                    widget = ttk.Entry(frame, textvariable=variable, width=field.width)
                widget.grid(row=offset, column=2, sticky="ew", padx=(0, 8), pady=3)
                if not form.is_enabled(field.key):
                    widget.configure(state="disabled")
                if field.hint:
                    ttk.Label(frame, text=field.hint, foreground="#6b7280", wraplength=320,
                              justify="left").grid(row=offset, column=3, sticky="w",
                                                   padx=(8, 8), pady=3)

        footer = ttk.Frame(window, padding=(10, 0, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        validation_var = tk.StringVar(master=window, value="Validation has not been run.")
        ttk.Label(footer, textvariable=validation_var, foreground="#5f6b7a").pack(
            side="left", fill="x", expand=True)

        def current_values() -> dict[str, str]:
            values = {key: variable.get() for key, variable in variables.items()}
            values.update({key: ("true" if variable.get() else "false")
                           for key, variable in booleans.items()})
            return values

        def validate_values(*, show_success: bool = True) -> list[str]:
            values = current_values()
            errors = list(form.validate(values))
            if errors:
                validation_var.set(f"Validation failed: {errors[0]}")
            elif show_success:
                validation_var.set(form.describe(values))
            return errors

        def apply_values() -> None:
            try:
                form.apply(current_values())
            except FormRefused as exc:
                messagebox.showerror("Advanced Surface Validation", str(exc), parent=window)
                return
            window.destroy()

        ttk.Button(footer, text="Validate",
                   command=lambda: validate_values(show_success=True)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))

        # The fields all exist now: bind the wheel recursively on each tab body so hovering any
        # field scrolls that tab, and size the initial scroll regions before the window is shown.
        def bind_tab_wheel(canvas: tk.Canvas, inner: ttk.Frame) -> None:
            def on_wheel(event):
                if inner.winfo_reqheight() <= canvas.winfo_height():
                    return None  # nothing to scroll -- let the event through
                num = getattr(event, "num", 0)
                delta = getattr(event, "delta", 0)
                if num == 4 or delta > 0:
                    canvas.yview_scroll(-1, "units")
                elif num == 5 or delta < 0:
                    canvas.yview_scroll(1, "units")
                return "break"

            def bind_recursive(node) -> None:
                for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                    try:
                        node.bind(seq, on_wheel, add="+")
                    except Exception:
                        pass
                try:
                    children = node.winfo_children()
                except Exception:
                    children = []
                for child in children:
                    bind_recursive(child)

            bind_recursive(canvas)
            bind_recursive(inner)

        for tab_canvas, tab_inner in scroll_tabs:
            bind_tab_wheel(tab_canvas, tab_inner)
        window.update_idletasks()
        for tab_canvas, _tab_inner in scroll_tabs:
            try:
                tab_canvas.configure(scrollregion=tab_canvas.bbox("all"))
            except tk.TclError:
                pass

        self._show_centered_dialog(window)
