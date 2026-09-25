"""The Tk view of a `RowForm` (docs/design_qt_migration.md phase 3).

The Tk half of what `qt/dialogs/row_form_dialog.py` does for Qt, and the only place in the Tk
tree that knows which widget a `FormField` becomes. Everything it draws -- the fields, their
kinds, their live locks, the master record list, the actions, the validation line -- belongs to
the form; this decides nothing.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.uihost import host_of

#: beyond this many fields a single column is taller than a screen, so pair them up
_TWO_COLUMN_THRESHOLD = 14


def render_row_form(owner: Any, form, *, wraplength: int = 520, on_close=None,
                    modal: bool = False) -> tk.Toplevel:
    """Show `form` in a Tk dialog and return the window."""
    # `or owner`, not a getattr default: the editor forwards unknown attributes to its Tk root,
    # and `editor.editor` comes back as None rather than raising. With ONE interpreter that was
    # invisible -- tk.Toplevel(None) picks the default root, which was the editor's anyway -- but
    # inside the penta harness, which already owns a root, the dialog was built in the WRONG
    # interpreter and the editor never saw it (bugs/0883).
    editor = getattr(owner, "editor", None) or owner
    window = tk.Toplevel(editor)
    window.withdraw()
    window.title(form.title)
    window.transient(editor)
    window.columnconfigure(0, weight=1)
    window.rowconfigure(0, weight=1)

    frame = ttk.Frame(window, padding=12)
    frame.grid(row=0, column=0, sticky="nsew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    ttk.Label(frame, text=form.note, wraplength=wraplength + 40,
              foreground="#475569").grid(row=0, column=0, columnspan=2, sticky="w",
                                         pady=(0, 10))

    body = ttk.Frame(frame)
    body.grid(row=1, column=0, columnspan=2, sticky="nsew")
    body.rowconfigure(0, weight=1)

    tree = None
    if form.records is not None:
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        columns = tuple(form.records.columns)
        tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse",
                            height=12)
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=130, anchor="w", stretch=True)
        tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(left, orient="vertical", command=tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scroll.set)
        fields_host = ttk.LabelFrame(body, text="Selected record", padding=10)
        fields_host.grid(row=0, column=1, sticky="nsew")
        body.columnconfigure(1, weight=2)
    else:
        fields_host = ttk.Frame(body)
        fields_host.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)

    variables: dict[str, tk.Variable] = {}
    widgets: dict[str, ttk.Widget] = {}
    texts: dict[str, tk.Text] = {}

    def build_fields(parent, fields) -> None:
        """One label and one widget per field, two columns once the page gets long."""
        two_column = len(fields) > _TWO_COLUMN_THRESHOLD
        for column in range(4 if two_column else 2):
            parent.columnconfigure(column, weight=1 if column % 2 else 0)
        for position, field in enumerate(fields):
            grid_row = position // 2 if two_column else position
            base = 2 * (position % 2) if two_column else 0
            value = form.values.get(field.key, "")
            if field.kind == "static":
                ttk.Label(parent, text=field.label).grid(
                    row=grid_row, column=base, sticky="w",
                    padx=(0 if base == 0 else 8, 10), pady=3)
                ttk.Label(parent, text=value, foreground="#334155",
                          wraplength=wraplength - 160).grid(row=grid_row, column=base + 1,
                                                            sticky="w", pady=3)
                continue
            if field.kind == "textarea":
                ttk.Label(parent, text=field.label).grid(
                    row=grid_row, column=base, sticky="nw",
                    padx=(0 if base == 0 else 8, 10), pady=3)
                text = tk.Text(parent, height=max(field.height, 3),
                               width=max(field.width, 40), wrap="word")
                text.insert("1.0", str(value))
                text.grid(row=grid_row, column=base + 1, sticky="ew", pady=3)
                texts[field.key] = text
                widgets[field.key] = text
                continue
            if field.kind == "bool":
                variable = tk.BooleanVar(
                    master=window,
                    value=str(value).strip().lower() in ("1", "true", "yes", "on"))
                widget = ttk.Checkbutton(parent, text=field.label, variable=variable)
                widget.grid(row=grid_row, column=base, columnspan=2, sticky="w",
                            padx=(0 if base == 0 else 8, 0), pady=3)
            else:
                ttk.Label(parent, text=field.label).grid(
                    row=grid_row, column=base, sticky="w",
                    padx=(0 if base == 0 else 8, 10), pady=3)
                variable = tk.StringVar(master=window, value=str(value))
                if field.kind == "choice":
                    widget = ttk.Combobox(parent, textvariable=variable,
                                          values=list(form.choices_for(field.key)),
                                          state="normal" if field.editable else "readonly",
                                          width=max(field.width, 20))
                else:
                    widget = ttk.Entry(parent, textvariable=variable, width=field.width)
                widget.grid(row=grid_row, column=base + 1, sticky="ew", pady=3)
            if not field.enabled or not form.is_enabled(field.key):
                try:
                    widget.configure(state="disabled")
                except Exception:
                    pass
            if field.hint:
                widget_hint = field.hint
                widget.bind("<Enter>", lambda _e, text=widget_hint: validation_var.set(text),
                            add="+")
            variables[field.key] = variable
            widgets[field.key] = widget

    if form.groups:
        # one tab per group. A canvas+scrollbar per tab keeps a 53-field page usable on a
        # laptop, which is what the hand-written Advanced Surface dialog did (bugs/0884).
        notebook = ttk.Notebook(fields_host)
        notebook.grid(row=0, column=0, sticky="nsew")
        fields_host.rowconfigure(0, weight=1)
        fields_host.columnconfigure(0, weight=1)
        for group in form.groups:
            host = ttk.Frame(notebook)
            host.rowconfigure(0, weight=1)
            host.columnconfigure(0, weight=1)
            notebook.add(host, text=group)
            canvas = tk.Canvas(host, highlightthickness=0)
            vscroll = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=vscroll.set)
            canvas.grid(row=0, column=0, sticky="nsew")
            vscroll.grid(row=0, column=1, sticky="ns")
            inner = ttk.Frame(canvas, padding=(0, 8, 0, 8))
            window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
            inner.bind("<Configure>",
                       lambda _e, c=canvas: c.configure(scrollregion=c.bbox("all")), add="+")
            canvas.bind("<Configure>",
                        lambda event, c=canvas, i=window_id: c.itemconfigure(
                            i, width=event.width), add="+")
            build_fields(inner, form.fields_in(group))
    else:
        build_fields(fields_host, form.fields)

    preview_canvas = None
    caption_var = None
    if form.preview is not None:
        preview_row = ttk.Frame(frame)
        preview_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        preview_canvas = tk.Canvas(preview_row, width=form.preview.width,
                                   height=form.preview.height, highlightthickness=1,
                                   highlightbackground="#bbbbbb", background="#fafafa")
        preview_canvas.grid(row=0, column=0, sticky="w")
        caption_var = tk.StringVar(master=window, value="")
        ttk.Label(preview_row, textvariable=caption_var, justify="left",
                  font=("TkFixedFont", 8), wraplength=wraplength - 140).grid(
                      row=0, column=1, sticky="nw", padx=(10, 0))

    validation_var = tk.StringVar(master=window, value=form.summary)
    ttk.Label(frame, textvariable=validation_var, foreground="#475569",
              wraplength=wraplength + 40).grid(row=3, column=0, columnspan=2, sticky="w",
                                               pady=(10, 0))

    def sync_enabled() -> None:
        """Follow `form.locked` -- a choice may turn other fields off while we are open."""
        for key, widget in widgets.items():
            field = form.field(key)
            if field is not None and field.kind not in ("choice", "bool"):
                widget.configure(state="normal" if form.is_enabled(key) else "disabled")

    def refresh_from_form() -> None:
        for key, text in texts.items():
            value = str(form.values.get(key, ""))
            if text.get("1.0", "end-1c") != value:
                text.delete("1.0", "end")
                text.insert("1.0", value)
        for key, variable in variables.items():
            value = str(form.values.get(key, ""))
            if isinstance(variable, tk.BooleanVar):
                variable.set(value.strip().lower() in ("1", "true", "yes", "on"))
            elif variable.get() != value:
                variable.set(value)
        for key, widget in widgets.items():
            field = form.field(key)
            if field is not None and field.kind == "choice":
                wanted = list(form.choices_for(key))
                if list(widget.cget("values")) != wanted:
                    widget.configure(values=wanted)
        sync_enabled()
        redraw_preview()

    def redraw_preview() -> None:
        """Ask the MODEL what to draw from the values as they stand right now."""
        if preview_canvas is None:
            return
        values = current_values()
        try:
            shapes = list(form.preview.shapes(form, values))
            caption = str(form.preview.caption(form, values))
        except Exception:
            return  # a half-typed number is not an error, it is just not drawable yet
        preview_canvas.delete("all")
        for shape in shapes:
            if shape.get("kind") == "polygon":
                points = [coordinate for point in shape.get("points", ()) for coordinate in point]
                if len(points) >= 6:
                    preview_canvas.create_polygon(*points, fill=shape.get("fill", ""),
                                                  outline=shape.get("outline", "#000000"),
                                                  width=1)
            elif shape.get("kind") == "text":
                preview_canvas.create_text(shape.get("x", 0), shape.get("y", 0),
                                           text=str(shape.get("text", "")),
                                           fill=shape.get("fill", "#000000"),
                                           font=("TkDefaultFont", int(shape.get("size", 7))))
        caption_var.set(caption)

    def refresh_records(select_index: "int | None" = None) -> None:
        if tree is None:
            return
        tree.delete(*tree.get_children())
        rows = list(form.records.rows(form))
        for position, row in enumerate(rows):
            tree.insert("", "end", iid=f"record_{position}", values=tuple(row))
        if not rows:
            return
        index = min(max(0, int(select_index if select_index is not None
                               else form.selected_index)), len(rows) - 1)
        iid = f"record_{index}"
        tree.selection_set(iid)
        tree.focus(iid)
        tree.see(iid)

    def on_record_selected(_event=None) -> None:
        selected = tree.selection() if tree is not None else ()
        if not selected:
            return
        try:
            index = int(str(selected[0]).split("_", 1)[1])
        except Exception:
            return
        if index == form.selected_index:
            return
        try:
            message = form.records.select(form, index)
        except FormRefused as exc:
            validation_var.set(str(exc))
            return
        refresh_from_form()
        if message:
            validation_var.set(message)

    def on_field_changed(field) -> None:
        """A field that rewrites others -- and, for a filter, the record list itself."""
        if field.on_change is None:
            return
        form.values[field.key] = variables[field.key].get()
        try:
            message = field.on_change(form, variables[field.key].get())
        except FormRefused as exc:
            messagebox.showerror(form.title, str(exc), parent=editor)
            return
        refresh_records()
        refresh_from_form()
        if message:
            validation_var.set(message)

    if preview_canvas is not None:
        for key, widget in widgets.items():
            if form.field(key) is not None and form.field(key).kind != "static":
                widget.bind("<KeyRelease>", lambda _event: redraw_preview(), add="+")
                widget.bind("<<ComboboxSelected>>", lambda _event: redraw_preview(), add="+")
                try:
                    widget.configure(command=redraw_preview)   # a checkbutton
                except Exception:
                    pass

    for field in form.fields:
        if field.on_change is None:
            continue
        if field.kind == "choice":
            widgets[field.key].bind("<<ComboboxSelected>>",
                                    lambda _event, f=field: on_field_changed(f), add="+")
        elif field.kind in ("text", "number", "int"):
            # a live filter: every keystroke re-asks the model for the rows
            widgets[field.key].bind("<KeyRelease>",
                                    lambda _event, f=field: on_field_changed(f), add="+")
    sync_enabled()
    if tree is not None:
        tree.bind("<<TreeviewSelect>>", on_record_selected, add="+")
        refresh_records()

    def current_values() -> dict[str, str]:
        collected: dict[str, str] = {key: text.get("1.0", "end-1c")
                                    for key, text in texts.items()}
        for key, variable in variables.items():
            if isinstance(variable, tk.BooleanVar):
                collected[key] = "true" if variable.get() else "false"
            else:
                collected[key] = variable.get()
        return collected

    # after current_values exists: the picture is drawn from the values, so it cannot be
    # painted any earlier than this
    redraw_preview()

    def close() -> None:
        window.destroy()
        if on_close is not None:
            on_close()

    def validate_form() -> bool:
        values = current_values()
        errors = list(form.validate(values))
        if errors:
            validation_var.set(errors[0])
            return False
        try:
            validation_var.set("Validation passed: " + form.describe(values))
        except FormRefused as exc:
            validation_var.set(str(exc))
            return False
        return True

    def apply_form() -> None:
        try:
            form.apply(current_values())
        except FormRefused as exc:
            validation_var.set(str(exc))
            return
        close()

    def run_action(action) -> None:
        # a record-list action edits the collection and stays open; a terminal one closes
        form.values.update(current_values())
        try:
            message = action.run(form, host_of(owner))
        except FormRefused as exc:
            validation_var.set(str(exc))
            return
        # A row form's action is terminal (Import, Clear) and closes; a record-list action
        # edits the collection and stays open -- unless it says otherwise by setting
        # form.state["close_after"], which is how "Use Source Panel Only" leaves.
        if form.records is None or form.state.pop("close_after", False):
            close()
            return
        refresh_records()
        refresh_from_form()
        validation_var.set(message or form.summary)

    footer = ttk.Frame(frame)
    footer.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))
    ttk.Button(footer, text="Validate", command=validate_form).pack(side="right", padx=(0, 8))
    ttk.Button(footer, text="Apply", command=apply_form).pack(side="right")
    for action in form.actions:
        ttk.Button(footer, text=action.label,
                   command=lambda a=action: run_action(a)).pack(side="right", padx=(0, 8))
    ttk.Button(footer, text="Cancel", command=close).pack(side="right", padx=(0, 8))
    owner._show_centered_dialog(window)
    if modal:
        # the 3D inspector's popups grab, so a click in the viewport behind cannot retrace
        # under a half-filled form
        try:
            window.grab_set()
        except Exception:
            pass
    return window
