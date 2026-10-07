"""The Tk view of a `Report` (docs/design_qt_migration.md phase 4).

The Tk half of what `qt/dialogs/report_dialog.py` does for Qt. A report dialog is a summary
line, some controls that rebuild it, a table (or a tree) and an export; none of that is report
specific, so all four of the Tk report windows are this one view over their own builder. What
a report SHOWS lives in `KrakenOS/UI/reports/`; this decides only how it is laid out.

The HANDLE the model talks to -- open, refresh, close, the selection, copy, export, the verbs --
is `reports/window.ReportWindow`, which has no toolkit in it (bugs/0984). It keeps the widgets
this module makes (`handle.window`, `.table`, `.detail_table`, `.detail_widget`, `.summary_var`,
`.controls`, `.control_widgets`) and calls the functions below when Tk is what draws. Under a
shell that draws its own dialogs it never imports this module at all.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from KrakenOS.UI.reports.window import ReportWindow  # noqa: F401 -- its home until bugs/0984; still named here


def window_exists(handle) -> bool:
    """Is the handle's Tk window still there?"""
    try:
        return bool(handle.window.winfo_exists())
    except tk.TclError:
        return False


def raise_window(handle):
    """Bring the open Tk window forward and return it."""
    window = handle.window
    window.deiconify()
    window.lift()
    window.focus_force()
    return window


def destroy_window(window) -> None:
    """Take a report's Tk window down (the handle has already forgotten it)."""
    try:
        if window.winfo_exists():
            window.destroy()
    except tk.TclError:
        pass


def make_window(handle, report) -> None:
    editor = handle.editor
    window = tk.Toplevel(editor)
    window.withdraw()
    window.title(report.title)
    window.geometry(handle.geometry)
    window.minsize(*handle.minsize)
    window.transient(editor)
    window.protocol("WM_DELETE_WINDOW", handle.close)
    window.columnconfigure(0, weight=1)
    window.rowconfigure(2, weight=1)
    handle.window = window

    toolbar = ttk.Frame(window, padding=(8, 8, 8, 0))
    toolbar.grid(row=0, column=0, sticky="ew")
    ttk.Button(toolbar, text="Refresh", command=handle.refresh).pack(side="left")
    if report.text:
        # a report the model can render as text; the others have nothing to copy
        ttk.Button(toolbar, text="Copy", command=handle.copy_text).pack(side="left", padx=(6, 0))
    ttk.Button(toolbar, text="Export CSV", command=handle.export_csv).pack(side="left", padx=(6, 0))
    for action in report.actions:
        ttk.Button(toolbar, text=action.label,
                   command=lambda action=action: handle.run_action(action)).pack(
                       side="left", padx=(6, 0))
    ttk.Button(toolbar, text="Close", command=handle.close).pack(side="left", padx=(6, 0))
    for control in report.controls:
        ttk.Label(toolbar, text=control.label).pack(side="left", padx=(18, 4))
        var = tk.StringVar(master=window, value=str(control.value))
        if hasattr(control, "choices"):
            widget = ttk.Combobox(toolbar, textvariable=var, state="readonly", width=36,
                                  values=list(control.choices))
            widget.bind("<<ComboboxSelected>>", lambda _event: handle.refresh(), add="+")
        else:
            # a typed-in value: rebuild when the field is committed, not per keystroke
            widget = ttk.Entry(toolbar, textvariable=var, width=max(control.width, 6))
            widget.bind("<Return>", lambda _event: handle.refresh(), add="+")
            widget.bind("<FocusOut>", lambda _event: handle.refresh(), add="+")
        widget.pack(side="left")
        handle.controls[control.key] = var
        handle.control_widgets[control.key] = widget

    handle.summary_var = tk.StringVar(master=window, value=report.summary)
    ttk.Label(window, textvariable=handle.summary_var, padding=(8, 6, 8, 0), anchor="w",
              justify="left").grid(row=1, column=0, sticky="ew")

    body = ttk.Frame(window, padding=8)
    body.grid(row=2, column=0, sticky="nsew")
    body.columnconfigure(0, weight=1)
    body.rowconfigure(0, weight=3)
    handle.table = handle._make_table(body, report)
    if report.detail is not None:
        body.rowconfigure(2, weight=2)
        ttk.Label(body, text=report.detail.label, anchor="w").grid(row=1, column=0,
                                                                  sticky="ew", pady=(8, 2))
        handle.detail_table = handle._make_detail_table(body, report.detail)
    elif report.detail_text is not None:
        body.rowconfigure(2, weight=0)
        frame = ttk.LabelFrame(body, text=report.detail_text.label, padding=(8, 6, 8, 8))
        frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        frame.columnconfigure(0, weight=1)
        widget = tk.Text(frame, height=report.detail_text.height, wrap="word",
                         borderwidth=0, relief="flat")
        widget.grid(row=0, column=0, sticky="ew")
        widget.configure(state="disabled")
        for binder in ("_bind_text_copy_shortcuts", "_bind_text_context_menu"):
            bind = getattr(handle.owner, binder, None)
            if bind is not None:
                bind(widget)
        handle.detail_widget = widget

    show = getattr(handle.owner, "_show_centered_dialog", None)
    if show is not None:
        show(window)
    else:
        window.deiconify()


def make_table(handle, parent, report) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    frame.grid(row=0, column=0, sticky="nsew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    columns = list(report.keys)
    if report.tree is not None:
        table = ttk.Treeview(frame, columns=columns, show="tree headings",
                             selectmode="browse")
        table.heading("#0", text=report.tree_heading)
        table.column("#0", width=200, stretch=False)
    else:
        table = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
    for column in report.columns:
        table.heading(column.key, text=column.heading)
        table.column(column.key, width=column.width, stretch=column.stretch,
                     anchor={"l": "w", "c": "center", "r": "e"}[column.alignment])
    table.grid(row=0, column=0, sticky="nsew")
    y_scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=table.xview)
    x_scroll.grid(row=1, column=0, sticky="ew")
    table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
    table.bind("<<TreeviewSelect>>", lambda _event: handle.refresh_detail(), add="+")
    activate = next((action for action in report.actions if action.on_activate), None)
    if activate is not None:
        table.bind("<Double-1>", lambda _event, action=activate: handle.run_action(action),
                   add="+")
    return table


def make_detail_table(handle, parent, detail) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    frame.grid(row=2, column=0, sticky="nsew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    columns = [column.key for column in detail.columns]
    table = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
    for column in detail.columns:
        table.heading(column.key, text=column.heading)
        table.column(column.key, width=column.width, stretch=column.stretch,
                     anchor={"l": "w", "c": "center", "r": "e"}[column.alignment])
    table.grid(row=0, column=0, sticky="nsew")
    y_scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
    y_scroll.grid(row=0, column=1, sticky="ns")
    table.configure(yscrollcommand=y_scroll.set)
    return table


def render(handle, report) -> None:
    # a refresh must land where the user was, not back at the top: Update rebuilds these
    # windows behind them, and the Ray Inspector's own dialog always kept its row
    previous = handle.selected_key() if handle.report is not None else None
    if handle.summary_var is not None:
        handle.summary_var.set(report.summary)
    handle._refresh_controls(report)
    table = handle.table
    if table is not None:
        table.delete(*table.get_children())
        handle._tree_keys = {}
        if report.tree is not None:
            handle._insert_tree(table, "", report.tree)
        else:
            for index in range(len(report.rows)):
                table.insert("", "end", iid=str(index),
                             values=[report.cell(index, column)
                                     for column in range(len(report.columns))])
    handle.select_key(previous if previous is not None else report.initial_key)
    handle._set_status(report.status)


def insert_tree(handle, table, parent, rows) -> None:
    for position, row in enumerate(rows):
        iid = f"{parent or 'root'}_{position}"
        table.insert(parent, "end", iid=iid, text=str(row.label),
                     values=[str(cell) for cell in row.cells],
                     open=bool(row.expanded))
        handle._tree_keys[iid] = row.detail_key
        if row.children:
            handle._insert_tree(table, iid, row.children)


def refresh_controls(handle, report) -> None:
    """Follow the data: a filter's choices change with the trace, so the combobox must too.

    Writing a StringVar does not raise <<ComboboxSelected>> (Tk raises that only for a
    user's pick) nor <Return>/<FocusOut>, so this cannot re-enter the rebuild that called it.
    """
    for control in report.controls:
        var = handle.controls.get(control.key)
        widget = handle.control_widgets.get(control.key)
        if var is None:
            continue
        if hasattr(control, "choices"):
            choices = list(control.choices)
            if widget is not None:
                widget["values"] = choices
            if var.get() not in choices:
                var.set(str(control.value) if str(control.value) in choices
                        else (choices[0] if choices else ""))
        elif var.get() != str(control.value):
            var.set(str(control.value))


def selected_key(handle):
    """The detail key of the row selected in the Tk table: its index, or its node key in a tree."""
    table = handle.table
    selection = table.selection()
    if not selection:
        return None
    iid = str(selection[0])
    if handle.report is not None and handle.report.tree is not None:
        return handle._tree_keys.get(iid)
    try:
        return int(iid)
    except ValueError:
        return None


def select_key(handle, key) -> None:
    """Select the Tk row or node carrying `key`, falling back to the first row."""
    table = handle.table
    if key is not None:
        if handle.report.tree is not None:
            for iid, node_key in handle._tree_keys.items():
                if node_key == key:
                    table.selection_set(iid)
                    table.see(iid)
                    handle.refresh_detail()
                    return
        elif isinstance(key, int) and 0 <= key < len(handle.report.rows):
            handle.select_row(key)
            return
    handle.select_row(0)


def select_row(handle, index: int) -> None:
    """Select master row `index` in the Tk table (or the index-th node that carries a key)."""
    table = handle.table
    if handle.report.tree is not None:
        nodes = [iid for iid, key in handle._tree_keys.items() if key is not None]
        if not nodes:
            handle._show_detail(None)
            return
        index = max(0, min(int(index), len(nodes) - 1))
        table.selection_set(nodes[index])
        table.see(nodes[index])
        # <<TreeviewSelect>> is delivered through the event loop, so show the detail here
        # too: a caller that selects a row must not have to pump Tk to see it
        handle.refresh_detail()
        return
    if not handle.report.rows:
        handle._show_detail(None)
        return
    index = max(0, min(int(index), len(handle.report.rows) - 1))
    table.selection_set(str(index))
    table.focus(str(index))
    table.see(str(index))
    handle.refresh_detail()


def show_detail(handle, key) -> None:
    """Fill the Tk detail table, or the detail text, for `key`."""
    report = handle.report
    if handle.detail_table is not None and report.detail is not None:
        handle.detail_table.delete(*handle.detail_table.get_children())
        if key is None:
            return
        for index, row in enumerate(report.detail.rows(key)):
            handle.detail_table.insert("", "end", iid=str(index),
                                     values=[str(cell) for cell in row])
        return
    if handle.detail_widget is not None and report.detail_text is not None:
        text = report.detail_text.empty if key is None else report.detail_text.text(key)
        widget = handle.detail_widget
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", str(text or ""))
        widget.configure(state="disabled")
