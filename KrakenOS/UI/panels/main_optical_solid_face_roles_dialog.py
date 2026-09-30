"""Optical CAD/STL face-role assignment dialog -- the Tk view.

The editor's state and actions are `face_roles_session.FaceRolesSession` and its 3D preview is
`face_roles_preview.FaceRolesPreview` (bugs/0933); this module lays them out in Tk. Under the Qt
shell the same session opens in `qt/dialogs/face_roles_dialog.py` instead.
"""

from __future__ import annotations

from pathlib import Path
import textwrap
import tkinter as tk
from tkinter import messagebox, ttk
import tkinter.font as tkfont
from typing import Any

import numpy as np

from KrakenOS.UI import face_roles_session as frs


def _open_face_coating_table_editor(parent, layout_module, initial_table, initial_met, on_apply):
    """A focused per-face coating-table editor: pick a shared preset OR hand-edit the
    ``[R, A, W, THETA]`` table, validate (`frs.parse_face_coating_table`), and hand the result to
    ``on_apply(table, coating_met)``."""
    presets = frs.coating_presets()
    window = tk.Toplevel(parent)
    window.withdraw()
    window.title("Face coating table")
    window.transient(parent)
    window.columnconfigure(0, weight=1)
    window.rowconfigure(1, weight=1)

    header = ttk.Frame(window, padding=(10, 10, 10, 4))
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(1, weight=1)
    ttk.Label(header, text="Preset").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
    preset_var = tk.StringVar(master=window, value="Custom")
    preset_menu = ttk.Combobox(
        header, textvariable=preset_var,
        values=("Custom",) + tuple(presets.keys()), state="readonly", width=28,
    )
    preset_menu.grid(row=0, column=1, sticky="w", pady=3)
    ttk.Label(header, text=frs.COATING_TABLE_HINT, foreground="#5f6b7a").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))

    body = ttk.Frame(window, padding=(10, 4, 10, 8))
    body.grid(row=1, column=0, sticky="nsew")
    body.columnconfigure(1, weight=1)
    body.rowconfigure(0, weight=1)
    ttk.Label(body, text="Coating table").grid(row=0, column=0, sticky="nw", padx=(0, 8), pady=3)
    table_text = tk.Text(body, height=10, wrap="none")
    table_text.insert("1.0", frs.format_coating_table(initial_table))
    table_text.grid(row=0, column=1, sticky="nsew", pady=3)
    scroll = ttk.Scrollbar(body, orient="vertical", command=table_text.yview)
    scroll.grid(row=0, column=2, sticky="ns")
    table_text.configure(yscrollcommand=scroll.set)
    ttk.Label(body, text="CoatingMet").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
    met_var = tk.StringVar(master=window, value=str(int(initial_met or 0)))
    ttk.Entry(body, textvariable=met_var, width=12).grid(row=1, column=1, sticky="w", pady=(6, 0))

    def _use_preset(_event=None):
        name = preset_var.get()
        if name in presets:
            table_text.delete("1.0", "end")
            table_text.insert("1.0", frs.format_coating_table(presets[name]))
    preset_menu.bind("<<ComboboxSelected>>", _use_preset)

    footer = ttk.Frame(window, padding=(10, 0, 10, 10))
    footer.grid(row=2, column=0, sticky="ew")

    def _apply():
        table, met, error = frs.parse_face_coating_table(table_text.get("1.0", "end"), met_var.get())
        if error:
            messagebox.showerror("Face coating", error, parent=window)
            return
        on_apply(table, met)
        window.destroy()

    ttk.Button(footer, text="Apply", command=_apply).pack(side="right")
    ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
    window.update_idletasks()
    window.deiconify()
    window.lift()
    window.focus_force()


class MainOpticalSolidFaceRolesDialog:
    """Open the optical-solid face-role editor for a row -- in Tk, or in the Qt shell when one has
    installed ``editor.show_face_roles_dialog``."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _open_optical_solid_faces_for_row(self, row_index: int, row: Any, path: Path) -> None:
        from KrakenOS.UI.uihost import host_of

        try:
            session = frs.FaceRolesSession(self.editor, row_index, row, path)
        except frs.FaceRolesUnavailable as exc:
            show = host_of(self.editor).showinfo if exc.severity == "info" else host_of(self.editor).showerror
            show(frs.FaceRolesSession.TITLE, str(exc))
            return
        shell_opener = self.editor.__dict__.get("show_face_roles_dialog")
        if callable(shell_opener):
            self._view = shell_opener(session)
            return
        self._view = TkFaceRolesView(self.editor, session)


class TkFaceRolesView:
    """The Tk window over a :class:`FaceRolesSession`: a face table, the 3D preview and the
    assignment form. Widgets write into ``session.form`` before an action (`_push`); the window
    redraws from the session whenever it notifies (`sync`)."""

    def __init__(self, editor: Any, session: Any) -> None:
        self.editor = editor
        self.session = session
        self.le = le = session.le
        self.preview = None            # FaceRolesPreview (VTK), else the Matplotlib fallback below
        self.preview_widget = None
        self.preview_canvas_widget = None
        self._mpl_render = None
        self.mpl_axis = None           # the fallback's 3D axis
        self._syncing = False
        self._resize_after_id = None
        try:
            le._load_3d_backends()
        except Exception:
            pass
        self._build_window()
        session.listeners.append(self.sync)
        self.window.bind("<Destroy>", self._on_destroy, add="+")
        self.sync(render=False)
        if session.records:
            session.select([0], 0)  # the first face, as the dialog always opened
        self.window.after(80, lambda: self.render(reset_camera=True))
        editor._show_centered_dialog(self.window)

    # ---- layout ---------------------------------------------------------------------------------
    def _build_window(self) -> None:
        editor, session = self.editor, self.session
        window = self.window = tk.Toplevel(editor)
        window.title(session.title())
        window.geometry("1440x760")
        window.minsize(1080, 560)
        window.transient(editor)
        self._install_snapshot_key()
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)
        header = ttk.Frame(window, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text=session.header_text()).pack(side="left", fill="x", expand=True)
        body = ttk.Panedwindow(window, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=6)
        self._build_tree(body)
        self._build_preview_pane(body)
        self._build_form_pane(body)
        footer = ttk.Frame(window, padding=(10, 4, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        ttk.Button(footer, text="Open 3D Placement", command=session.open_placement_view).pack(side="left")
        ttk.Button(footer, text="Native Surface Props", command=session.open_native_surface_props).pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="Use Face As Source Target",
                   command=lambda: self._act(session.use_as_source_target)).pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="Set as Illumination Source",
                   command=lambda: self._act(session.use_as_illumination_source)).pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="Save Roles", command=lambda: self._act(session.save_roles)).pack(side="right")
        ttk.Button(footer, text="Copy Summary", command=session.copy_summary).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Close", command=window.destroy).pack(side="right", padx=(0, 8))

    def _install_snapshot_key(self) -> None:
        """The `s` bug-flag / scene-snapshot hotkey is bound on the Open 3D inspector window; this
        face editor is a separate Toplevel whose Treeview swallows `s` before a Toplevel-level
        binding can fire (a plain window.bind did not work). Use an application-wide bind_all,
        scoped by focused-toplevel to this window so it never double-fires alongside the
        inspector's own `s`, and torn down when the window closes. It forwards to the inspector's
        _flag_bug_event, which itself no-ops while the user is typing in an entry/combobox."""
        editor, window = self.editor, self.window

        def forward(event=None):
            inspector = getattr(editor, "_three_d_inspector", None)
            handler = getattr(inspector, "_flag_bug_event", None) if inspector is not None else None
            if not callable(handler):
                return None
            try:
                focused = window.focus_get()
                if focused is None or focused.winfo_toplevel() is not window:
                    return None  # focus elsewhere -> let the inspector's own binding handle it
            except Exception:
                return None
            return handler(event)

        for seq in ("<KeyPress-s>", "<KeyPress-S>"):
            try:
                editor.bind_all(seq, forward, add="+")
            except Exception:
                pass

    def _on_destroy(self, event=None) -> None:
        if event is not None and getattr(event, "widget", None) is not self.window:
            return  # child <Destroy> events bubble up; only act on the window's own
        for seq in ("<KeyPress-s>", "<KeyPress-S>"):
            try:
                self.editor.unbind_all(seq)
            except Exception:
                pass
        if self.sync in self.session.listeners:
            self.session.listeners.remove(self.sync)

    def _build_tree(self, body) -> None:
        session = self.session
        frame = ttk.Frame(body)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.columns = session.columns()
        self.tree_style = f"OpticalSolidFaces{session.row_index}.Treeview"
        try:
            ttk.Style(self.window).configure(self.tree_style, rowheight=30)
        except Exception:
            self.tree_style = "Treeview"
        tree = self.tree = ttk.Treeview(frame, columns=self.columns, show="headings", selectmode="extended",
                                        style=self.tree_style)
        for column in self.columns:
            width = frs.TREE_WIDTHS[column]
            tree.heading(column, text=frs.TREE_HEADINGS[column])
            tree.column(column, width=width, minwidth=min(width, 70),
                        anchor="e" if column in {"area", "triangles", "split"} else "w", stretch=False)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        for index in range(len(session.records)):
            tree.insert("", "end", iid=f"face_{index}", values=())
        body.add(frame, weight=3)
        self.table_font = tkfont.nametofont("TkDefaultFont")
        try:
            self.heading_font = tkfont.nametofont("TkHeadingFont")
        except Exception:
            self.heading_font = self.table_font
        tree.bind("<<TreeviewSelect>>", self._on_tree_select, add="+")
        tree.bind("<ButtonRelease-1>", self._schedule_rewrap, add="+")
        tree.bind("<Configure>", self._schedule_rewrap, add="+")
        tree.bind("<Double-Button-1>", self._on_column_double_click, add="+")
        if session.show_face_groups:
            tree.bind("<Button-3>", self._show_group_menu, add="+")

    def _build_preview_pane(self, body) -> None:
        le, session = self.le, self.session
        frame = ttk.Frame(body, padding=(8, 0, 8, 0))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text=frs.PREVIEW_HINT, foreground="#334155", wraplength=430).grid(row=0, column=0, sticky="ew", pady=(0, 4))
        host = self.preview_host = ttk.Frame(frame)
        host.grid(row=1, column=0, sticky="nsew")
        host.columnconfigure(0, weight=1)
        host.rowconfigure(0, weight=1)
        self.preview_status_var = tk.StringVar(master=self.window, value=session.preview_status)
        ttk.Label(frame, textvariable=self.preview_status_var, foreground="#475569").grid(row=2, column=0, sticky="ew", pady=(4, 0))
        body.add(frame, weight=4)
        if le.pv is None or le.vtkTkRenderWindowInteractor is None or le.vtkRenderer is None:
            self._install_matplotlib_preview(le._VTK_TK_UNAVAILABLE_REASON or "VTK/Tk unavailable; Matplotlib/Tk picker active")
            return
        try:
            from KrakenOS.UI.face_roles_preview import FaceRolesPreview

            le._prepare_vtk_tk_widget(host)
            widget = self.preview_widget = le.vtkTkRenderWindowInteractor(host, width=480, height=520)
            widget.grid(row=0, column=0, sticky="nsew")
            renderer = le.vtkRenderer()
            widget.GetRenderWindow().AddRenderer(renderer)
            try:
                widget.Initialize()
            except Exception:
                pass
            self.preview = FaceRolesPreview(session, renderer, widget.GetRenderWindow())
            self._bind_vtk_mouse(widget)
        except Exception as exc:
            self.preview = None
            self.editor.append_debug(f"VTK/Tk CAD/STL face picker unavailable; using Matplotlib fallback: {exc}")
            self._install_matplotlib_preview("Matplotlib fallback picker")

    def _bind_vtk_mouse(self, widget) -> None:
        """Match Open 3D: click selects; left-drag rotates without default VTK acceleration. The
        preview takes VTK display coordinates, so y is flipped here."""
        def vtk_xy(event):
            return float(event.x), float(max(widget.winfo_height(), 1) - 1 - event.y)

        def press(event):
            self.preview.press(*vtk_xy(event))
            return "break"

        def motion(event):
            self.preview.motion(*vtk_xy(event))
            return "break"

        def release(event):
            self._push()
            self.preview.release(*vtk_xy(event))
            return "break"

        try:
            for prefix in ("", "Control-"):
                widget.bind(f"<{prefix}ButtonPress-1>", press)
                widget.bind(f"<{prefix}B1-Motion>", motion)
                widget.bind(f"<{prefix}ButtonRelease-1>", release)
        except Exception as exc:
            self.editor.append_debug(f"CAD/STL face preview mouse binding failed: {exc}")

    def _build_form_pane(self, body) -> None:
        editor, session = self.editor, self.session
        # The assignment form is taller than the dialog, so wrap it in a vertical scroll canvas --
        # otherwise the lower controls overflow off the bottom with no scrollbar. Both the mouse
        # wheel and the touchpad scroll it (X11 sends <Button-4>/<Button-5>, Windows/macOS +
        # hi-res touchpads send <MouseWheel> with a signed delta), bound recursively on every
        # control so hovering any field scrolls (matches the Scene Components panel idiom).
        editor_host = ttk.Frame(body)
        editor_host.columnconfigure(0, weight=1)
        editor_host.rowconfigure(0, weight=1)
        body.add(editor_host, weight=2)
        canvas = self.form_canvas = tk.Canvas(editor_host, highlightthickness=0, width=348)
        vscroll = self.form_vscroll = ttk.Scrollbar(editor_host, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        form = self.form_frame = ttk.Frame(canvas, padding=(12, 4, 4, 4))
        form.columnconfigure(1, weight=1)
        self.form_window = canvas.create_window((0, 0), window=form, anchor="nw")
        form.bind("<Configure>", lambda _e: self._update_form_scroll(), add="+")
        canvas.bind("<Configure>", self._on_form_canvas_configure, add="+")
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            canvas.bind(seq, self._on_form_wheel, add="+")

        self.vars: dict[str, tk.Variable] = {}
        for key, value in session.form.items():
            self.vars[key] = (tk.BooleanVar if isinstance(value, bool) else tk.StringVar)(master=self.window, value=value)
        self.combos: dict[str, ttk.Combobox] = {}
        row = 0
        for key, (label, values) in frs.form_choices().items():
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=(0, 2))
            combo = self.combos[key] = ttk.Combobox(form, textvariable=self.vars[key], values=values, state="readonly")
            combo.grid(row=row, column=1, sticky="ew", pady=(0, 6))
            combo.bind("<<ComboboxSelected>>", self._auto_apply, add="+")
            editor._add_widget_tooltip(combo, frs.TOOLTIPS[key])
            row += 1
        ttk.Label(form, text="Input snap U/V [mm]").grid(row=row, column=0, sticky="w", pady=(0, 2))
        snap = ttk.Frame(form)
        snap.grid(row=row, column=1, sticky="ew", pady=(0, 6))
        snap.columnconfigure(0, weight=1)
        snap.columnconfigure(1, weight=1)
        self.entries: dict[str, ttk.Entry] = {}
        for column, key in enumerate(("input_offset_u", "input_offset_v")):
            entry = self.entries[key] = ttk.Entry(snap, textvariable=self.vars[key], width=8)
            entry.grid(row=0, column=column, sticky="ew", padx=(0, 4) if column == 0 else 0)
            editor._add_widget_tooltip(entry, frs.TOOLTIPS[key])
        self.pick_text = tk.StringVar(master=self.window, value="Pick In 3D")
        self.pick_button = ttk.Button(snap, textvariable=self.pick_text, command=lambda: self._act(session.toggle_input_snap_pick))
        self.pick_button.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(4, 0))
        zero = ttk.Button(snap, text="Zero", command=lambda: self._act(session.clear_input_snap_offsets))
        zero.grid(row=1, column=1, sticky="ew", pady=(4, 0))
        editor._add_widget_tooltip(snap, frs.TOOLTIPS["input_offset"])
        editor._add_widget_tooltip(self.pick_button, frs.TOOLTIPS["pick"])
        editor._add_widget_tooltip(zero, frs.TOOLTIPS["zero"])
        row += 1
        for key, label in frs.FORM_TEXT_FIELDS:
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=(0, 2))
            entry = self.entries[key] = ttk.Entry(form, textvariable=self.vars[key], width=18 if key == "material" else 12)
            entry.grid(row=row, column=1, sticky="ew", pady=(0, 6))
            if key in frs.TOOLTIPS:
                editor._add_widget_tooltip(entry, frs.TOOLTIPS[key])
            row += 1
        ttk.Label(form, text="Coating").grid(row=row, column=0, sticky="w", pady=(0, 2))
        # Pick from the SAME shared coating library as the 2D "Coating..." editor; a chosen preset
        # is resolved per-face into the KrakenOS Coating table the non-seq trace applies via
        # CoatingFun. Editable so legacy free-text coatings still load (they read as a note -- no
        # preset -> no per-face coating physics).
        coating_frame = ttk.Frame(form)
        coating_frame.grid(row=row, column=1, sticky="ew", pady=(0, 6))
        coating_frame.columnconfigure(0, weight=1)
        coating = self.entries["coating"] = ttk.Combobox(coating_frame, textvariable=self.vars["coating"],
                                                          values=frs.coating_choices(), width=13)
        coating.grid(row=0, column=0, sticky="ew")
        coating.bind("<<ComboboxSelected>>", lambda _e: session.choose_coating(self.vars["coating"].get()))
        ttk.Button(coating_frame, text="Edit table…", width=11, command=self._edit_coating_table).grid(row=0, column=1, padx=(4, 0))
        row += 1
        ttk.Checkbutton(form, text="Flip normal for UI intent", variable=self.vars["flip"],
                        command=self._auto_apply).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        row += 1
        ttk.Label(form, text="Notes").grid(row=row, column=0, sticky="w", pady=(0, 2))
        self.entries["notes"] = ttk.Entry(form, textvariable=self.vars["notes"], width=28)
        self.entries["notes"].grid(row=row, column=1, sticky="ew", pady=(0, 6))
        row += 1
        for entry in self.entries.values():
            entry.bind("<FocusOut>", self._auto_apply, add="+")
            entry.bind("<Return>", self._auto_apply, add="+")
        self.validation_var = tk.StringVar(master=self.window, value=session.validation)
        ttk.Label(form, textvariable=self.validation_var, foreground="#475569", wraplength=330).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(4, 8))
        ttk.Label(form, text=frs.PHYSICS_HINT, foreground="#64748b", wraplength=330).grid(
            row=row + 1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        auto_orient = ttk.Checkbutton(form, text=frs.AUTO_ORIENT_LABEL, variable=self.vars["auto_orient"])
        auto_orient.grid(row=row + 2, column=0, columnspan=2, sticky="w", pady=(0, 6))
        editor._add_widget_tooltip(auto_orient, session.auto_orient_hint())
        row += 3
        quick_sides = ttk.LabelFrame(form, text="2D side")
        quick_sides.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 4))
        for label, side, tooltip in frs.quick_sides():
            button = ttk.Button(quick_sides, text=label, command=lambda s=side: self._act(session.set_side_and_apply, s))
            button.pack(side="left", padx=(0, 3), pady=2)
            editor._add_widget_tooltip(button, tooltip)
        quick_ports = ttk.LabelFrame(form, text="Port role")
        quick_ports.grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        for label, port, tooltip in frs.quick_ports():
            button = ttk.Button(quick_ports, text=label, command=lambda p=port: self._act(session.set_port_and_apply, p))
            button.pack(side="left", padx=(0, 3))
            editor._add_widget_tooltip(button, tooltip)
        row += 2
        for label, action in (("Apply Form to Selected", session.apply_selected), ("Auto Guess 2D Sides", session.auto_guess),
                              ("Suggest Optical Intent", session.refresh_suggestions),
                              ("Apply Suggestions to Empty", session.apply_suggestions_to_empty),
                              ("Clear Face Labels", session.clear_roles)):
            ttk.Button(form, text=label, command=lambda a=action: self._act(a)).grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=(0, 4))
            row += 1
        self._build_virtual_plane(form, row)
        self._bind_form_wheel(form)
        form.update_idletasks()
        self._update_form_scroll()

    def _build_virtual_plane(self, form, row: int) -> None:
        session, le = self.session, self.le
        frame = ttk.LabelFrame(form, text="Virtual Internal Plane")
        frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 4))
        frame.columnconfigure(1, weight=1)
        self.virtual_vars = {key: tk.StringVar(master=self.window, value=value) for key, value in session.virtual_form.items()}
        ttk.Label(frame, text="Diagonal").grid(row=0, column=0, sticky="w", pady=(0, 2))
        ttk.Combobox(frame, textvariable=self.virtual_vars["diagonal"], values=le.OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_VALUES,
                     state="readonly").grid(row=0, column=1, sticky="ew", pady=(0, 2))
        for index, (key, label) in enumerate(frs.VIRTUAL_TEXT_FIELDS, start=1):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", pady=(0, 2))
            ttk.Entry(frame, textvariable=self.virtual_vars[key], width=18 if key == "notes" else 12).grid(
                row=index, column=1, sticky="ew", pady=(0, 2))
        ttk.Label(frame, text=frs.VIRTUAL_HINT, foreground="#64748b", wraplength=330, justify="left").grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(2, 4))
        self.virtual_status_var = tk.StringVar(master=self.window, value=session.virtual_status)
        ttk.Label(frame, textvariable=self.virtual_status_var, foreground="#475569", wraplength=330).grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(frame, text="Auto Cube Splitter Plane", command=lambda: self._act(session.build_virtual_cube_plane)).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(0, 2))
        ttk.Button(frame, text="Clear Virtual Planes", command=lambda: self._act(session.clear_virtual_planes)).grid(
            row=9, column=0, columnspan=2, sticky="ew")

    # ---- the scrolled form ----------------------------------------------------------------------
    def _update_form_scroll(self) -> None:
        try:
            self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all"))
            overflow = self.form_frame.winfo_reqheight() > self.form_canvas.winfo_height()
            if overflow and not self.form_vscroll.grid_info():
                self.form_vscroll.grid(row=0, column=1, sticky="ns")
            elif not overflow and self.form_vscroll.grid_info():
                self.form_vscroll.grid_remove()
        except tk.TclError:
            pass

    def _on_form_canvas_configure(self, event) -> None:
        # Vertical-only scroll: the inner form fills the canvas width (so the column-1 stretch +
        # label wraplengths lay out) and at least the canvas height (so a short form is not clipped).
        fill_height = max(int(event.height), self.form_frame.winfo_reqheight())
        self.form_canvas.itemconfigure(self.form_window, width=int(event.width), height=fill_height)
        self._update_form_scroll()

    def _on_form_wheel(self, event) -> "str | None":
        if self.form_frame.winfo_reqheight() <= self.form_canvas.winfo_height():
            return None  # nothing to scroll; let the event through
        num, delta = getattr(event, "num", 0), getattr(event, "delta", 0)
        if num == 4 or delta > 0:
            self.form_canvas.yview_scroll(-1, "units")
        elif num == 5 or delta < 0:
            self.form_canvas.yview_scroll(1, "units")
        return "break"

    def _bind_form_wheel(self, node) -> None:
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            try:
                node.bind(seq, self._on_form_wheel, add="+")
            except Exception:
                pass
        try:
            children = node.winfo_children()
        except Exception:
            children = []
        for child in children:
            self._bind_form_wheel(child)

    # ---- widgets <-> session --------------------------------------------------------------------
    def _push(self) -> None:
        """Write what the widgets show into the session's form."""
        for key, var in self.vars.items():
            self.session.form[key] = bool(var.get()) if isinstance(var, tk.BooleanVar) else str(var.get())
        for key, var in self.virtual_vars.items():
            self.session.virtual_form[key] = str(var.get())

    def _act(self, action, *args) -> None:
        self._push()
        action(*args)

    def _auto_apply(self, _event=None) -> None:
        if self._syncing:
            return
        self._act(self.session.auto_apply)

    def _edit_coating_table(self) -> None:
        def apply(table, met) -> None:
            self._push()
            self.session.set_coating_table(table, met)

        _open_face_coating_table_editor(self.window, self.le, self.session.coating_state.get("table"),
                                        self.session.coating_state.get("met", 0), apply)

    def _on_tree_select(self, _event=None) -> None:
        if self._syncing:
            return
        indices = [self._index_of(iid) for iid in self.tree.selection()]
        indices = [i for i in indices if i is not None]
        focus = self._index_of(self.tree.focus())
        session = self.session
        if sorted(indices) == session.selection and (focus is None or focus == session.focus):
            return  # our own sync set this selection
        session.select(indices, focus)

    @staticmethod
    def _index_of(iid) -> int | None:
        try:
            return int(str(iid).split("_", 1)[1])
        except Exception:
            return None

    def sync(self, *, render: bool = True) -> None:
        """Redraw everything from the session."""
        try:
            if not self.window.winfo_exists():
                return
        except tk.TclError:
            return
        session = self.session
        self._syncing = True
        try:
            for key, var in self.vars.items():
                value = session.form[key]
                if var.get() != value:
                    var.set(value)
            for key, var in self.virtual_vars.items():
                if var.get() != session.virtual_form[key]:
                    var.set(session.virtual_form[key])
            states = session.field_states()
            for key in ("split", "loss", "phase"):
                self.entries[key].configure(state="normal" if states[key] else "disabled")
            self._rewrap_tree_values()
            wanted = [f"face_{i}" for i in session.selection]
            if list(self.tree.selection()) != wanted:
                self.tree.selection_set(wanted)
            if session.focus is not None:
                self.tree.focus(f"face_{session.focus}")
                self.tree.see(f"face_{session.focus}")
            self.pick_text.set("Picking..." if session.input_snap_pick_active else "Pick In 3D")
            self._set_pick_cursor(session.input_snap_pick_active)
            if render:
                self.render()
            self.validation_var.set(session.validation)
            self.preview_status_var.set(session.preview_status)
            self.virtual_status_var.set(session.virtual_status)
        finally:
            self._syncing = False

    def render(self, *, reset_camera: bool = False) -> None:
        if self.preview is not None:
            self.preview.render(reset_camera=reset_camera)
        elif self._mpl_render is not None:
            self._mpl_render(reset_camera=reset_camera)
        try:
            self.preview_status_var.set(self.session.preview_status)
        except tk.TclError:
            pass

    def _set_pick_cursor(self, active: bool) -> None:
        for widget in (self.preview_widget, self.preview_canvas_widget):
            if widget is not None:
                try:
                    widget.configure(cursor="crosshair" if active else "")
                except Exception:
                    pass

    # ---- the face table's cell wrapping (Tk rows have one height, so long cells wrap) ----------
    def _wrap_cell_text(self, column: str, value: str) -> str:
        text = str(value)
        if column in frs.NUMERIC_COLUMNS or column not in {"face", "function", "port", "suggestion", "fit_ref", "normal", "centroid"} or not text:
            return text
        try:
            width_px = int(self.tree.column(column, "width") or frs.TREE_WIDTHS.get(column, 90))
        except Exception:
            width_px = int(frs.TREE_WIDTHS.get(column, 90))
        available_px = max(width_px - 14, 28)
        if self.table_font.measure(text) <= available_px:
            return text
        sample = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        avg_char_px = max(self.table_font.measure(sample) / max(len(sample), 1), 5.0)
        width_chars = max(int(available_px / avg_char_px), 4)
        return "\n".join(textwrap.wrap(text, width=width_chars, break_long_words=True, break_on_hyphens=False) or [text])

    def _rewrap_tree_values(self) -> None:
        max_lines = 1
        for index, cells in enumerate(self.session.rows()):
            values = tuple(self._wrap_cell_text(column, cells[column]) for column in self.columns)
            self.tree.item(f"face_{index}", values=values)
            max_lines = max([max_lines] + [str(v).count("\n") + 1 for v in values])
        try:
            ttk.Style(self.window).configure(self.tree_style, rowheight=min(max(30, 22 * max_lines + 8), 118))
        except Exception:
            pass

    def _schedule_rewrap(self, _event=None) -> None:
        if self._resize_after_id is not None:
            try:
                self.window.after_cancel(self._resize_after_id)
            except Exception:
                pass

        def run() -> None:
            self._resize_after_id = None
            self._rewrap_tree_values()
        self._resize_after_id = self.window.after(60, run)

    def _on_column_double_click(self, event):
        """Double-clicking a column separator fits the column to its widest cell."""
        try:
            if self.tree.identify_region(event.x, event.y) != "separator":
                return None
            column_id = self.tree.identify_column(event.x)
            index = int(column_id[1:]) - 1 if column_id.startswith("#") else -1
        except Exception:
            return None
        if not 0 <= index < len(self.columns):
            return None
        column = self.columns[index]
        heading = frs.TREE_HEADINGS.get(column, column)
        widest = self.heading_font.measure(heading)
        for value in [heading] + [cells[column] for cells in self.session.rows()]:
            for line in str(value).splitlines() or [""]:
                widest = max(widest, self.table_font.measure(line))
        self.tree.column(column, width=max(int(frs.TREE_WIDTHS.get(column, 80)), min(int(widest + 34), 900)), stretch=False)
        self._rewrap_tree_values()
        return "break"

    def _show_group_menu(self, event) -> None:
        index = self._index_of(self.tree.identify_row(event.y))
        label = self.session.group_menu_label(index) if index is not None else None
        if label is None:
            return
        menu = tk.Menu(self.window, tearoff=0)
        menu.add_command(label=label, command=lambda i=index: self.session.select_group(i))
        try:
            menu.tk_popup(int(event.x_root), int(event.y_root))
        finally:
            menu.grab_release()

    # ---- the Matplotlib fallback preview (no VTK/Tk) --------------------------------------------
    def _install_matplotlib_preview(self, reason: str) -> None:
        # imported here: layout_editor never exported Poly3DCollection / MplPath / proj3d, so the
        # fallback used to raise AttributeError on its first draw -- the editor could not open at
        # all without VTK/Tk (found by 0933's gate run)
        from matplotlib.path import Path as MplPath
        from mpl_toolkits.mplot3d import proj3d
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        le, session = self.le, self.session
        for child in self.preview_host.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass
        figure = le.Figure(figsize=(5.2, 4.8), dpi=100)
        axis = figure.add_subplot(111, projection="3d")
        self.mpl_axis = axis
        canvas = le.FigureCanvasTkAgg(figure, master=self.preview_host)
        self.preview_canvas_widget = canvas.get_tk_widget()
        self.preview_canvas_widget.grid(row=0, column=0, sticky="nsew")
        tri_cache: dict[int, np.ndarray] = {}
        view = {"elev": 22.0, "azim": -55.0}
        drag: dict[str, object] = {"active": False, "start": None, "last": None, "moved": False}
        try:
            axis.disable_mouse_rotation()
        except Exception:
            pass

        def triangles_of(index: int) -> np.ndarray:
            if index in tri_cache:
                return tri_cache[index]
            try:
                triangles = session.face_source_triangles(index)
            except Exception as exc:
                self.editor.append_debug(f"Matplotlib CAD/STL face triangles failed for S{session.row_index} F{index + 1}: {exc}")
                triangles = np.empty((0, 3, 3), dtype=float)
            if triangles.size:
                triangles = session.to_world(triangles.reshape((-1, 3))).reshape((-1, 3, 3))
            tri_cache[index] = np.asarray(triangles, dtype=float)
            return tri_cache[index]

        def render(*, reset_camera: bool = False) -> None:
            axis.clear()
            try:
                axis.disable_mouse_rotation()
            except Exception:
                pass
            selected_index = session.selected_index()
            all_points: list[np.ndarray] = []
            visible = 0
            for index in range(len(session.records)):
                triangles = triangles_of(index)
                if triangles.size == 0:
                    continue
                visible += 1
                all_points.append(triangles.reshape((-1, 3)))
                colour, assigned = session.face_colour(index, selected_index)
                alpha = 0.3 if index == selected_index else 0.12 if assigned else 0.045
                axis.add_collection3d(Poly3DCollection(triangles, facecolors=[(*colour, alpha)],
                                                          edgecolors=[(0.08, 0.12, 0.16, 0.55)], linewidths=0.45))
                if index == selected_index:
                    centroid = np.mean(triangles.reshape((-1, 3)), axis=0)
                    normal = session.face_normal_world(index)
                    if normal is not None:
                        axis.quiver(*centroid, *normal, length=max(session.mesh_span * 0.18, 1.0), color=(1.0, 0.28, 0.0), linewidth=2.0)
                    face = session.world_face(index)
                    if face is not None:
                        anchor = np.asarray(face.get("anchor_world", face.get("centroid_world", (np.nan,) * 3)), dtype=float).reshape(-1)[:3]
                        if anchor.size == 3 and np.all(np.isfinite(anchor)):
                            axis.scatter([anchor[0]], [anchor[1]], [anchor[2]], s=42, color="#d62728", depthshade=False,
                                         edgecolors="white", linewidths=0.8)
                        u_axis = np.asarray(face.get("u_axis_world", (np.nan,) * 3), dtype=float).reshape(-1)[:3]
                        v_axis = np.asarray(face.get("v_axis_world", (np.nan,) * 3), dtype=float).reshape(-1)[:3]
                        if np.all(np.isfinite(u_axis)) and np.all(np.isfinite(v_axis)) and np.all(np.isfinite(anchor)):
                            u_norm, v_norm = float(np.linalg.norm(u_axis)), float(np.linalg.norm(v_axis))
                            if u_norm > 1e-12 and v_norm > 1e-12:
                                scale = max(session.mesh_span * 0.1, 1.2)
                                u_dir, v_dir = u_axis / u_norm * scale, v_axis / v_norm * scale
                                axis.quiver(*anchor, *u_dir, color="#d62728", linewidth=1.8, arrow_length_ratio=0.16)
                                axis.quiver(*anchor, *v_dir, color="#2ca02c", linewidth=1.8, arrow_length_ratio=0.16)
                                axis.text(*(anchor + u_dir), "U", color="#d62728", fontsize=8)
                                axis.text(*(anchor + v_dir), "V", color="#2ca02c", fontsize=8)
            if all_points:
                points = np.vstack(all_points)
                low, high = np.min(points, axis=0), np.max(points, axis=0)
                center, radius = 0.5 * (low + high), max(float(np.max(high - low)) * 0.55, 1.0)
                axis.set_xlim(center[0] - radius, center[0] + radius)
                axis.set_ylim(center[1] - radius, center[1] + radius)
                axis.set_zlim(center[2] - radius, center[2] + radius)
                try:
                    axis.set_box_aspect((1, 1, 1))
                except Exception:
                    pass
            axis.set_title("Click a face to select it", fontsize=10)
            axis.set_xlabel("X [mm]")
            axis.set_ylabel("Y [mm]")
            axis.set_zlabel("Z [mm]")
            if reset_camera:
                view.update(elev=22.0, azim=-55.0)
            axis.view_init(elev=float(view["elev"]), azim=float(view["azim"]))
            figure.tight_layout(pad=0.3)
            canvas.draw_idle()
            session.render_status(session.preview_status_text(visible, reason))

        def point_on_face(index: int, clicked: np.ndarray, projection) -> np.ndarray | None:
            best_distance, best = float("inf"), None
            samples = 12
            for triangle in triangles_of(index):
                v0, v1, v2 = (np.asarray(vertex, dtype=float).reshape(3) for vertex in triangle)
                for i in range(samples + 1):
                    for j in range(samples + 1 - i):
                        a, b = i / samples, j / samples
                        point = a * v0 + b * v1 + (1.0 - a - b) * v2
                        px, py, _pz = proj3d.proj_transform(point[0], point[1], point[2], projection)
                        distance = float(np.linalg.norm(np.asarray(axis.transData.transform((px, py))) - clicked))
                        if distance < best_distance:
                            best_distance, best = distance, point
            return best

        def pick(event) -> tuple:
            if event.inaxes is not axis or event.x is None or event.y is None:
                return None, None
            clicked = np.asarray([float(event.x), float(event.y)])
            projection = axis.get_proj()
            hits, nearest = [], None
            for index in range(len(session.records)):
                triangles = triangles_of(index)
                if triangles.size == 0:
                    continue
                centroid = np.mean(triangles.reshape((-1, 3)), axis=0)
                cx, cy, _cz = proj3d.proj_transform(centroid[0], centroid[1], centroid[2], projection)
                distance = float(np.linalg.norm(clicked - np.asarray(axis.transData.transform((cx, cy)))))
                if nearest is None or distance < nearest[0]:
                    nearest = (distance, index)
                for triangle in triangles:
                    xs, ys, _zs = proj3d.proj_transform(triangle[:, 0], triangle[:, 1], triangle[:, 2], projection)
                    polygon = np.asarray(axis.transData.transform(np.column_stack([xs, ys])))
                    if MplPath(polygon).contains_point(clicked, radius=3.0):
                        hits.append((distance, index, point_on_face(index, clicked, projection)))
                        break
            if hits:
                _d, index, point = min(hits, key=lambda item: item[0])
                return int(index), point
            if nearest is not None and nearest[0] <= 55.0:
                return int(nearest[1]), None
            return None, None

        def on_press(event) -> None:
            if event.inaxes is not axis or event.button != 1 or event.x is None or event.y is None:
                return
            point = (int(event.x), int(event.y))
            drag.update(active=True, start=point, last=point, moved=False)

        def on_motion(event) -> None:
            if not drag["active"] or event.x is None or event.y is None:
                return
            current = (int(event.x), int(event.y))
            start, last = drag["start"] or current, drag["last"] or current
            if (current[0] - start[0]) ** 2 + (current[1] - start[1]) ** 2 >= 16:
                drag["moved"] = True
            if drag["moved"]:
                view["azim"] = float(view["azim"]) - float(current[0] - last[0]) * 0.22
                view["elev"] = max(-89.0, min(89.0, float(view["elev"]) + float(current[1] - last[1]) * 0.22))
                axis.view_init(elev=float(view["elev"]), azim=float(view["azim"]))
                canvas.draw_idle()
            drag["last"] = current

        def on_release(event) -> None:
            if event.button != 1:
                return
            should_pick = bool(drag["active"]) and not bool(drag["moved"])
            drag.update(active=False, start=None, last=None, moved=False)
            if not should_pick:
                return
            index, point = pick(event)
            self._push()
            if index is None:
                session.preview_status = ("Input snap pick: click closer to a coloured face candidate." if session.input_snap_pick_active
                                          else "Click closer to a coloured face candidate.")
                session.notify()
            elif session.input_snap_pick_active and point is None:
                session.preview_status = "Input snap pick requires a direct click on the selected face."
                session.notify()
            else:
                session.click_face(int(index), point, source="3D pick" if point is not None else "3D nearest")

        canvas.mpl_connect("button_press_event", on_press)
        canvas.mpl_connect("motion_notify_event", on_motion)
        canvas.mpl_connect("button_release_event", on_release)
        self._mpl_render = render
