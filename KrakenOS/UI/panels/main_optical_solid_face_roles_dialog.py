"""Optical CAD/STL face-role assignment dialog."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import textwrap
import tkinter as tk
from tkinter import messagebox, ttk
import tkinter.font as tkfont
from typing import Any

import numpy as np


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


def _open_face_coating_table_editor(parent, layout_module, initial_table, initial_met, on_apply):
    """A focused per-face coating-table editor: pick a shared preset OR hand-edit the
    ``[R, A, W, THETA]`` table (the same shape + ``COATING_PRESETS`` library the 2D "Coating..."
    editor uses), validate, and hand the result to ``on_apply(table, coating_met)``. Decoupled
    from any surface row, so a promoted-solid FACE can carry its own custom coating that the
    non-sequential trace applies through ``CoatingFun``."""
    import ast
    from pprint import pformat

    presets = dict(getattr(layout_module, "COATING_PRESETS", {}) or {})
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
    ttk.Label(
        header,
        text="Coating = [R, A, W, THETA]. R/A rows follow THETA; columns follow wavelength.",
        foreground="#5f6b7a",
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))

    body = ttk.Frame(window, padding=(10, 4, 10, 8))
    body.grid(row=1, column=0, sticky="nsew")
    body.columnconfigure(1, weight=1)
    body.rowconfigure(0, weight=1)
    ttk.Label(body, text="Coating table").grid(row=0, column=0, sticky="nw", padx=(0, 8), pady=3)
    table_text = tk.Text(body, height=10, wrap="none")
    table_text.insert("1.0", pformat(list(initial_table) if initial_table else [[], [], [], []], width=100))
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
            table_text.insert("1.0", pformat(presets[name], width=100))
    preset_menu.bind("<<ComboboxSelected>>", _use_preset)

    footer = ttk.Frame(window, padding=(10, 0, 10, 10))
    footer.grid(row=2, column=0, sticky="ew")

    def _apply():
        from KrakenOS.UI.optical_solid_metadata import normalize_optical_solid_face_coating_table
        from KrakenOS.UI.services.advanced_surface_validation import _validate_coating_met, _validate_coating_table
        try:
            table = ast.literal_eval(table_text.get("1.0", "end").strip() or "[[], [], [], []]")
        except Exception as exc:
            messagebox.showerror("Face coating", f"Could not parse the coating table:\n\n{exc}", parent=window)
            return
        try:
            met = int(float(str(met_var.get()).strip() or "0"))
        except Exception:
            messagebox.showerror("Face coating", "CoatingMet must be an integer metal index.", parent=window)
            return
        errors = list(_validate_coating_table(table)) + list(_validate_coating_met(met))
        if errors:
            messagebox.showerror("Face coating", "Invalid coating:\n\n" + "\n".join(errors), parent=window)
            return
        normalized = normalize_optical_solid_face_coating_table(table)
        if not normalized:
            messagebox.showerror(
                "Face coating",
                "An empty / clear table is not a custom coating. Pick a named preset instead, or "
                "leave the coating blank for no per-face coating.",
                parent=window,
            )
            return
        on_apply(normalized, met)
        window.destroy()

    ttk.Button(footer, text="Apply", command=_apply).pack(side="right")
    ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
    window.update_idletasks()
    window.deiconify()
    window.lift()
    window.focus_force()


class MainOpticalSolidFaceRolesDialog:
    """Own the large optical-solid face-role editor while delegating state to the editor."""

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
        le = _layout_module()
        saved_metadata = (row.advanced or {}).get(le.OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        # Native OCC B-Rep faces (each a real optical surface, tagged with a
        # surface_type and triangle indices into the displayed STL) are listed
        # verbatim -- no STL plane-clustering, which would re-shatter a curved
        # face into ~160 planar candidates. The flat-STL path is unchanged.
        brep_backed = le.optical_solid_metadata_is_brep(saved_metadata)
        candidates: list = []
        if brep_backed:
            metadata = le.normalize_optical_solid_face_metadata(saved_metadata, source_stl=str(path))
        else:
            try:
                candidates = le.cluster_optical_solid_planar_faces(path)
            except Exception as exc:
                messagebox.showerror('Assign CAD/STL Optical Faces', f'Could not read STL face candidates:\n\n{exc}', parent=self.editor)
                return
            if not candidates:
                messagebox.showinfo('Assign CAD/STL Optical Faces', 'No planar STL face candidates were found.', parent=self.editor)
                return
            metadata = le.normalize_optical_solid_face_metadata(saved_metadata, candidates, source_stl=str(path))
        records: list[dict[str, object]] = [le.normalize_optical_solid_face_record(face) for face in list(metadata.get('faces', []) or [])]
        records = le.suggest_optical_solid_face_roles(records)

        def _face_source_triangles(index: int) -> np.ndarray:
            """Triangles for face ``index``: by B-Rep triangle_indices, else planar cluster."""
            if brep_backed:
                if 0 <= index < len(records):
                    return le.optical_solid_face_record_triangles(path, records[index])
                return np.empty((0, 3, 3), dtype=float)
            if 0 <= index < len(candidates):
                return le.optical_solid_face_candidate_triangles(path, candidates[index])
            return np.empty((0, 3, 3), dtype=float)
        virtual_planes: list[dict[str, object]] = [le.normalize_optical_solid_virtual_plane_record(plane) for plane in list(metadata.get('virtual_planes', []) or []) if isinstance(plane, dict)]
        # Display-only grouping: a curved (aspheric/spherical) lens face is
        # fragmented by the planar clusterer into many candidates (e.g. 160).
        # Group them by mesh connectivity + normal continuity so the editor can
        # show a few logical surfaces and "Select all in group" lets the user
        # role-assign a whole curved face at once. The candidates themselves
        # (and their planar fits/snapping) are unchanged.
        if brep_backed:
            # Most native B-Rep faces are already one whole optical surface, but
            # the importer splits a lens *rim* into several co-axial cylinder
            # faces -- group those so the rim reads as one edge and "Select all
            # in group" can role-assign it at once (bugs/0013).
            try:
                _face_group_ids = le.group_brep_optical_solid_faces(records)
            except Exception:
                _face_group_ids = [-1] * len(records)
        else:
            try:
                _face_group_ids = le.group_optical_solid_face_candidates(path, records, angle_deg=35.0)
            except Exception:
                _face_group_ids = [-1] * len(records)
        group_index_by_record_index: dict[int, int] = {i: int(g) for i, g in enumerate(_face_group_ids)}
        group_member_counts: dict[int, int] = {}
        for _g in _face_group_ids:
            if int(_g) >= 0:
                group_member_counts[int(_g)] = group_member_counts.get(int(_g), 0) + 1
        # Only surface the Group column when grouping actually consolidates
        # (more candidates than groups); for a few flat faces it is just noise.
        _distinct_groups = len(group_member_counts)
        show_face_groups = bool(_distinct_groups) and len(records) > _distinct_groups + 1
        def group_label_for_record_index(index: int) -> str:
            gid = group_index_by_record_index.get(int(index), -1)
            return f"G{gid + 1}" if gid >= 0 else ""
        group_label_by_face_id: dict[str, str] = {
            str(records[i].get('face_id', '') or ''): group_label_for_record_index(i)
            for i in range(len(records))
        }
        window = tk.Toplevel(self.editor)
        window.title(f'CAD/STL Optical Faces - S{row_index}')
        window.geometry('1440x760')
        window.minsize(1080, 560)
        window.transient(self.editor)

        # The `s` bug-flag / scene-snapshot hotkey is bound on the Open 3D
        # inspector window; this face editor is a separate Toplevel whose
        # Treeview swallows `s` before a Toplevel-level binding can fire (a
        # plain window.bind did not work). Use an application-wide bind_all,
        # scoped by focused-toplevel to this window so it never double-fires
        # alongside the inspector's own `s`, and torn down when the window
        # closes. It forwards to the inspector's _flag_bug_event, which itself
        # no-ops while the user is typing in an entry/combobox.
        def _forward_snapshot_key(event=None):
            inspector = getattr(self.editor, '_three_d_inspector', None)
            handler = getattr(inspector, '_flag_bug_event', None) if inspector is not None else None
            if not callable(handler):
                return None
            try:
                focused = window.focus_get()
                if focused is None or focused.winfo_toplevel() is not window:
                    return None  # focus elsewhere -> let the inspector's own binding handle it
            except Exception:
                return None
            return handler(event)

        for _seq in ('<KeyPress-s>', '<KeyPress-S>'):
            try:
                self.editor.bind_all(_seq, _forward_snapshot_key, add='+')
            except Exception:
                pass

        def _release_snapshot_key(event=None):
            if event is not None and getattr(event, 'widget', None) is not window:
                return  # child <Destroy> events bubble up; only act on the window's own
            for _seq in ('<KeyPress-s>', '<KeyPress-S>'):
                try:
                    self.editor.unbind_all(_seq)
                except Exception:
                    pass

        window.bind('<Destroy>', _release_snapshot_key, add='+')
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)
        header = ttk.Frame(window, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky='ew')
        _group_hint = (
            f' | {_distinct_groups} surface group(s) -- right-click a row to "Select all in group" (a curved lens face is split into many planar candidates).'
            if show_face_groups else ''
        )
        ttk.Label(header, text=f'S{row_index}: {row.name or row.surface} | {Path(path).name} | {len(records)} planar face candidate(s), {len(virtual_planes)} virtual plane(s).{_group_hint} Assign optical intent; tracing still follows the STL solid.').pack(side='left', fill='x', expand=True)
        body = ttk.Panedwindow(window, orient='horizontal')
        body.grid(row=1, column=0, sticky='nsew', padx=10, pady=6)
        tree_frame = ttk.Frame(body)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        columns = ('face',) + (('group',) if show_face_groups else ()) + ('side', 'function', 'port', 'suggestion', 'fit_ref', 'area', 'triangles', 'normal', 'centroid', 'split', 'flip')
        tree_style = f'OpticalSolidFaces{row_index}.Treeview'
        try:
            ttk.Style(window).configure(tree_style, rowheight=30)
        except Exception:
            tree_style = 'Treeview'
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='extended', style=tree_style)
        headings = {'face': 'Face', 'group': 'Group', 'side': '2D Side', 'function': 'Function', 'port': 'Port Role', 'suggestion': 'Suggested', 'fit_ref': 'Fit Ref', 'area': 'Area [mm2]', 'triangles': 'Triangles', 'normal': 'Normal', 'centroid': 'Centroid', 'split': 'Split', 'flip': 'Flip'}
        widths = {'face': 62, 'group': 56, 'side': 76, 'function': 130, 'port': 126, 'suggestion': 168, 'fit_ref': 92, 'area': 90, 'triangles': 76, 'normal': 180, 'centroid': 190, 'split': 68, 'flip': 48}
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], minwidth=min(widths[column], 70), anchor='e' if column in {'area', 'triangles', 'split'} else 'w', stretch=False)
        tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree_scroll.grid(row=0, column=1, sticky='ns')
        tree_xscroll = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree.xview)
        tree_xscroll.grid(row=1, column=0, sticky='ew')
        tree.configure(yscrollcommand=tree_scroll.set, xscrollcommand=tree_xscroll.set)
        body.add(tree_frame, weight=3)
        preview_frame = ttk.Frame(body, padding=(8, 0, 8, 0))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        ttk.Label(preview_frame, text='Click a face in 3D to select it; left-drag rotates the view with the same fixed-speed behavior as Open 3D. Then assign the 2D side and optical function on the right.', foreground='#334155', wraplength=430).grid(row=0, column=0, sticky='ew', pady=(0, 4))
        preview_host = ttk.Frame(preview_frame)
        preview_host.grid(row=1, column=0, sticky='nsew')
        preview_host.columnconfigure(0, weight=1)
        preview_host.rowconfigure(0, weight=1)
        preview_status_var = tk.StringVar(master=window, value='3D face preview loading...')
        ttk.Label(preview_frame, textvariable=preview_status_var, foreground='#475569').grid(row=2, column=0, sticky='ew', pady=(4, 0))
        body.add(preview_frame, weight=4)
        # The assignment form below is taller than the dialog, so wrap it in a
        # vertical scroll canvas -- otherwise the lower controls overflow off the
        # bottom with no scrollbar. Both the mouse wheel and the touchpad scroll it
        # (X11 sends <Button-4>/<Button-5>, Windows/macOS + hi-res touchpads send
        # <MouseWheel> with a signed delta), bound recursively on every control so
        # hovering any field scrolls (matches the Scene Components panel idiom).
        editor_host = ttk.Frame(body)
        editor_host.columnconfigure(0, weight=1)
        editor_host.rowconfigure(0, weight=1)
        body.add(editor_host, weight=2)
        editor_canvas = tk.Canvas(editor_host, highlightthickness=0, width=348)
        editor_vscroll = ttk.Scrollbar(editor_host, orient='vertical', command=editor_canvas.yview)
        editor_canvas.configure(yscrollcommand=editor_vscroll.set)
        editor_canvas.grid(row=0, column=0, sticky='nsew')
        editor = ttk.Frame(editor_canvas, padding=(12, 4, 4, 4))
        for column in (1,):
            editor.columnconfigure(column, weight=1)
        editor_window = editor_canvas.create_window((0, 0), window=editor, anchor='nw')

        def _update_editor_scroll() -> None:
            try:
                editor_canvas.configure(scrollregion=editor_canvas.bbox('all'))
                overflow = editor.winfo_reqheight() > editor_canvas.winfo_height()
                if overflow and not editor_vscroll.grid_info():
                    editor_vscroll.grid(row=0, column=1, sticky='ns')
                elif not overflow and editor_vscroll.grid_info():
                    editor_vscroll.grid_remove()
            except tk.TclError:
                pass

        def _on_editor_canvas_configure(event) -> None:
            # Vertical-only scroll: the inner form fills the canvas width (so the
            # column-1 stretch + label wraplengths lay out) and at least the canvas
            # height (so a short form is not clipped).
            fill_height = max(int(event.height), editor.winfo_reqheight())
            editor_canvas.itemconfigure(editor_window, width=int(event.width), height=fill_height)
            _update_editor_scroll()

        def _on_editor_wheel(event) -> "str | None":
            if editor.winfo_reqheight() <= editor_canvas.winfo_height():
                return None  # nothing to scroll; let the event through
            num = getattr(event, 'num', 0)
            delta = getattr(event, 'delta', 0)
            if num == 4 or delta > 0:
                editor_canvas.yview_scroll(-1, 'units')
            elif num == 5 or delta < 0:
                editor_canvas.yview_scroll(1, 'units')
            return 'break'

        def _bind_editor_wheel(node) -> None:
            for seq in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                try:
                    node.bind(seq, _on_editor_wheel, add='+')
                except Exception:
                    pass
            try:
                children = node.winfo_children()
            except Exception:
                children = []
            for child in children:
                _bind_editor_wheel(child)

        editor.bind('<Configure>', lambda _e: _update_editor_scroll(), add='+')
        editor_canvas.bind('<Configure>', _on_editor_canvas_configure, add='+')
        for seq in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            editor_canvas.bind(seq, _on_editor_wheel, add='+')
        side_var = tk.StringVar(master=window, value=le.OPTICAL_SOLID_FACE_SIDE_DEFAULT)
        function_var = tk.StringVar(master=window, value=le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT)
        port_var = tk.StringVar(master=window, value=le.OPTICAL_SOLID_FACE_PORT_DEFAULT)
        fit_reference_var = tk.StringVar(master=window, value=le.OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT)
        input_offset_u_var = tk.StringVar(master=window, value='0')
        input_offset_v_var = tk.StringVar(master=window, value='0')
        split_var = tk.StringVar(master=window, value='0.5')
        loss_var = tk.StringVar(master=window, value='0')
        phase_var = tk.StringVar(master=window, value='0')
        aperture_var = tk.StringVar(master=window, value='0')
        material_var = tk.StringVar(master=window, value=str(row.glass or ''))
        coating_var = tk.StringVar(master=window, value='')
        # Per-face CUSTOM coating table (the advanced "Edit table..." editor). When set it wins
        # over the preset NAME in coating_var; picking a preset from the dropdown clears it.
        face_coating_state: dict[str, object] = {'table': None, 'met': 0}
        flip_var = tk.BooleanVar(master=window, value=False)
        notes_var = tk.StringVar(master=window, value='')
        validation_var = tk.StringVar(master=window, value='Select a face candidate, assign a 2D side/function, then Apply.')
        initial_virtual_plane = virtual_planes[0] if virtual_planes else {}
        virtual_diagonal_var = tk.StringVar(master=window, value=le._normalize_optical_solid_virtual_plane_diagonal(initial_virtual_plane.get('diagonal_mode')))
        virtual_split_var = tk.StringVar(master=window, value=f"{float(initial_virtual_plane.get('split_ratio', 0.5) or 0.5):.6g}")
        virtual_loss_var = tk.StringVar(master=window, value=f"{float(initial_virtual_plane.get('loss', 0.0) or 0.0):.6g}")
        virtual_phase_var = tk.StringVar(master=window, value=f"{float(initial_virtual_plane.get('phase_deg', 0.0) or 0.0):.6g}")
        virtual_aperture_var = tk.StringVar(master=window, value=f"{float(initial_virtual_plane.get('aperture_mm', 0.0) or 0.0):.6g}")
        virtual_notes_var = tk.StringVar(master=window, value=str(initial_virtual_plane.get('notes', '') or ''))
        row_advanced = row.advanced if isinstance(row.advanced, dict) else {}
        placement_settings = row_advanced.get(le.SCENE_PLACEMENT_ADVANCED_ATTR, {})
        open3d_promoted_step_row = (
            isinstance(row_advanced.get('StepOverlayPromotion'), dict)
            or (
                isinstance(placement_settings, dict)
                and str(placement_settings.get('promotion_source', '') or '').strip() == 'open3d_step_overlay'
            )
        )
        auto_orient_var = tk.BooleanVar(master=window, value=not open3d_promoted_step_row)
        auto_orient_hint = (
            'This row was placed in Open 3D; Save Roles preserves its current pose unless this box is enabled.'
            if open3d_promoted_step_row
            else 'When enabled, Save Roles solves the row pose from the Input Port face.'
        )
        virtual_status_var = tk.StringVar(master=window, value=f'{len(virtual_planes)} virtual internal plane(s) saved.' if virtual_planes else 'No virtual internal plane saved.')
        form_loading = False
        ttk.Label(editor, text='2D side').grid(row=0, column=0, sticky='w', pady=(0, 2))
        side_menu = ttk.Combobox(editor, textvariable=side_var, values=le.OPTICAL_SOLID_FACE_SIDE_VALUES, state='readonly')
        side_menu.grid(row=0, column=1, sticky='ew', pady=(0, 6))
        ttk.Label(editor, text='Coating / interaction').grid(row=1, column=0, sticky='w', pady=(0, 2))
        function_menu = ttk.Combobox(editor, textvariable=function_var, values=le.OPTICAL_SOLID_FACE_FUNCTION_VALUES, state='readonly')
        function_menu.grid(row=1, column=1, sticky='ew', pady=(0, 6))
        ttk.Label(editor, text='Port role').grid(row=2, column=0, sticky='w', pady=(0, 2))
        port_menu = ttk.Combobox(editor, textvariable=port_var, values=le.OPTICAL_SOLID_FACE_PORT_VALUES, state='readonly')
        port_menu.grid(row=2, column=1, sticky='ew', pady=(0, 6))
        ttk.Label(editor, text='Fit ref normal').grid(row=3, column=0, sticky='w', pady=(0, 2))
        fit_reference_menu = ttk.Combobox(editor, textvariable=fit_reference_var, values=le.OPTICAL_SOLID_FACE_FIT_REFERENCE_VALUES, state='readonly')
        fit_reference_menu.grid(row=3, column=1, sticky='ew', pady=(0, 6))
        ttk.Label(editor, text='Input snap U/V [mm]').grid(row=4, column=0, sticky='w', pady=(0, 2))
        input_offset_frame = ttk.Frame(editor)
        input_offset_frame.grid(row=4, column=1, sticky='ew', pady=(0, 6))
        input_offset_frame.columnconfigure(0, weight=1)
        input_offset_frame.columnconfigure(1, weight=1)
        input_offset_u_entry = ttk.Entry(input_offset_frame, textvariable=input_offset_u_var, width=8)
        input_offset_u_entry.grid(row=0, column=0, sticky='ew', padx=(0, 4))
        input_offset_v_entry = ttk.Entry(input_offset_frame, textvariable=input_offset_v_var, width=8)
        input_offset_v_entry.grid(row=0, column=1, sticky='ew')
        input_snap_pick_button_text = tk.StringVar(master=window, value='Pick In 3D')
        input_snap_pick_button = ttk.Button(input_offset_frame, textvariable=input_snap_pick_button_text)
        input_snap_pick_button.grid(row=1, column=0, sticky='ew', padx=(0, 4), pady=(4, 0))
        clear_input_snap_button = ttk.Button(input_offset_frame, text='Zero')
        clear_input_snap_button.grid(row=1, column=1, sticky='ew', pady=(4, 0))
        ttk.Label(editor, text='Split ratio').grid(row=5, column=0, sticky='w', pady=(0, 2))
        split_entry = ttk.Entry(editor, textvariable=split_var, width=12)
        split_entry.grid(row=5, column=1, sticky='ew', pady=(0, 6))
        ttk.Label(editor, text='Loss').grid(row=6, column=0, sticky='w', pady=(0, 2))
        loss_entry = ttk.Entry(editor, textvariable=loss_var, width=12)
        loss_entry.grid(row=6, column=1, sticky='ew', pady=(0, 6))
        ttk.Label(editor, text='Phase [deg]').grid(row=7, column=0, sticky='w', pady=(0, 2))
        phase_entry = ttk.Entry(editor, textvariable=phase_var, width=12)
        phase_entry.grid(row=7, column=1, sticky='ew', pady=(0, 6))
        ttk.Label(editor, text='Clear aperture [mm]').grid(row=8, column=0, sticky='w', pady=(0, 2))
        aperture_entry = ttk.Entry(editor, textvariable=aperture_var, width=12)
        aperture_entry.grid(row=8, column=1, sticky='ew', pady=(0, 6))
        ttk.Label(editor, text='Material override').grid(row=9, column=0, sticky='w', pady=(0, 2))
        material_entry = ttk.Entry(editor, textvariable=material_var, width=18)
        material_entry.grid(row=9, column=1, sticky='ew', pady=(0, 6))
        ttk.Label(editor, text='Coating').grid(row=10, column=0, sticky='w', pady=(0, 2))
        # Pick from the SAME shared coating library as the 2D "Coating..." editor
        # (le.COATING_PRESET_NAMES); a chosen preset is resolved per-face into the KrakenOS
        # Coating table the non-seq trace applies via CoatingFun. Editable so legacy free-text
        # coatings still load (they read as a note -- no preset -> no per-face coating physics).
        coating_frame = ttk.Frame(editor)
        coating_frame.grid(row=10, column=1, sticky='ew', pady=(0, 6))
        coating_frame.columnconfigure(0, weight=1)
        coating_entry = ttk.Combobox(
            coating_frame, textvariable=coating_var,
            values=('Custom',) + tuple(le.COATING_PRESET_NAMES), width=13,
        )
        coating_entry.grid(row=0, column=0, sticky='ew')

        def _on_coating_preset_chosen(_event=None) -> None:
            # Choosing a NAMED preset drops any custom table (the name resolves at build instead).
            if str(coating_var.get()).strip() != 'Custom':
                face_coating_state['table'] = None
                face_coating_state['met'] = 0
        coating_entry.bind('<<ComboboxSelected>>', _on_coating_preset_chosen)

        def _edit_face_coating_table() -> None:
            def _apply(table, met) -> None:
                face_coating_state['table'] = table
                face_coating_state['met'] = int(met)
                coating_var.set('Custom')
            _open_face_coating_table_editor(
                window, le, face_coating_state.get('table'), face_coating_state.get('met', 0), _apply,
            )
        coating_table_button = ttk.Button(coating_frame, text='Edit table…', width=11, command=_edit_face_coating_table)
        coating_table_button.grid(row=0, column=1, padx=(4, 0))
        flip_check = ttk.Checkbutton(editor, text='Flip normal for UI intent', variable=flip_var)
        flip_check.grid(row=11, column=0, columnspan=2, sticky='w', pady=(0, 8))
        ttk.Label(editor, text='Notes').grid(row=12, column=0, sticky='w', pady=(0, 2))
        notes_entry = ttk.Entry(editor, textvariable=notes_var, width=28)
        notes_entry.grid(row=12, column=1, sticky='ew', pady=(0, 6))
        ttk.Label(editor, textvariable=validation_var, foreground='#475569', wraplength=330).grid(row=13, column=0, columnspan=2, sticky='ew', pady=(4, 8))
        ttk.Label(editor, text='Uncoated uses normal glass/air Snell-Fresnel physics; total internal reflection happens automatically when the incidence exceeds the critical angle. Fit ref normal fixes prism roll after the Input Port face is aligned. Input snap U/V shifts the anchor point within the selected Input Port face before Save Roles solves pose.', foreground='#64748b', wraplength=330).grid(row=14, column=0, columnspan=2, sticky='ew', pady=(0, 6))
        preview_renderer = None
        preview_widget = None
        preview_canvas_widget = None
        preview_interactor = None
        preview_picker = None
        preview_actor_map: dict[str, int] = {}
        candidate_mesh_cache: dict[int, object] = {}
        # Cache the raw body mesh + its feature edges (both depend only on `path`,
        # which is constant for the dialog's lifetime). render_face_preview ran on
        # launch, every face selection AND every field auto-apply, and each call
        # re-read the STL from disk + re-extracted feature edges -- the slow Face
        # Editor / Save Roles the user reported. The rigid pose transform is cheap
        # and stays per-render, so a pose change still re-places the body.
        base_mesh_cache: dict[str, object] = {}
        preview_drag_active = False
        preview_drag_start_xy: tuple[int, int] | None = None
        preview_drag_last_xy: tuple[int, int] | None = None
        preview_drag_moved = False
        input_snap_pick_active = False
        z_station = self._stl_row_z_station(row_index)
        mesh_span = 1.0
        try:
            le._load_3d_backends()
        except Exception:
            pass

        def record_by_iid(iid: str) -> dict[str, object] | None:
            try:
                index = int(str(iid).split('_', 1)[1])
            except Exception:
                return None
            if 0 <= index < len(records):
                return records[index]
            return None

        def selected_record_index() -> int | None:
            selection = tree.selection()
            if not selection:
                return None
            focus = tree.focus()
            if focus in selection:
                try:
                    index = int(str(focus).split('_', 1)[1])
                    if 0 <= index < len(records):
                        return index
                except Exception:
                    pass
            try:
                index = int(str(selection[0]).split('_', 1)[1])
            except Exception:
                return None
            return index if 0 <= index < len(records) else None

        def selected_record_indices() -> list[int]:
            indices: list[int] = []
            for iid in tree.selection():
                try:
                    index = int(str(iid).split('_', 1)[1])
                except Exception:
                    continue
                if 0 <= index < len(records):
                    indices.append(index)
            return sorted(set(indices))

        def format_vector(values) -> str:
            arr = np.asarray(values, dtype=float).reshape(-1)
            if arr.size < 3:
                arr = np.pad(arr, (0, 3 - arr.size), mode='constant')
            return '({:.4g}, {:.4g}, {:.4g})'.format(float(arr[0]), float(arr[1]), float(arr[2]))
        face_table_font = tkfont.nametofont('TkDefaultFont')
        try:
            face_heading_font = tkfont.nametofont('TkHeadingFont')
        except Exception:
            face_heading_font = face_table_font
        wrap_columns = {'face', 'function', 'port', 'suggestion', 'fit_ref', 'normal', 'centroid'}
        numeric_columns = {'area', 'triangles', 'split', 'flip'}
        resize_after_id: str | None = None

        def raw_tree_values(record: dict[str, object]) -> dict[str, str]:
            function = le._normalize_optical_solid_face_function(record.get('function'), legacy_role=record.get('role'))
            authored_port = le._optical_solid_face_authored_port_role(record)
            return {'face': str(record.get('face_id', '') or ''), 'group': group_label_by_face_id.get(str(record.get('face_id', '') or ''), ''), 'side': le._normalize_optical_solid_face_side(record.get('side_2d')), 'function': le._optical_solid_face_function_display(function, legacy_role=record.get('role')), 'port': authored_port, 'suggestion': le._optical_solid_face_suggestion_label(record), 'fit_ref': '' if le._normalize_optical_solid_face_fit_reference(record.get('fit_reference')) == le.OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT else le._normalize_optical_solid_face_fit_reference(record.get('fit_reference')), 'area': f"{float(record.get('area_mm2', 0.0) or 0.0):.6g}", 'triangles': str(int(record.get('triangle_count', 0) or 0)), 'normal': format_vector(record.get('normal', [0, 0, 1])), 'centroid': format_vector(record.get('centroid', [0, 0, 0])), 'split': f"{float(record.get('split_ratio', 0.5) or 0.0):.4g}" if function == 'Beam Splitter' else '', 'flip': 'yes' if bool(record.get('flip_normal', False)) else ''}

        def wrap_cell_text(column: str, value: str) -> str:
            text = str(value)
            if column in numeric_columns or column not in wrap_columns or (not text):
                return text
            try:
                width_px = int(tree.column(column, 'width') or widths.get(column, 90))
            except Exception:
                width_px = int(widths.get(column, 90))
            available_px = max(width_px - 14, 28)
            if face_table_font.measure(text) <= available_px:
                return text
            sample = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            avg_char_px = max(face_table_font.measure(sample) / max(len(sample), 1), 5.0)
            width_chars = max(int(available_px / avg_char_px), 4)
            return '\n'.join(textwrap.wrap(text, width=width_chars, break_long_words=True, break_on_hyphens=False) or [text])

        def display_tree_values(record: dict[str, object]) -> tuple[str, ...]:
            raw = raw_tree_values(record)
            return tuple((wrap_cell_text(column, raw[column]) for column in columns))

        def update_face_property_field_states(*_args) -> None:
            function = le._optical_solid_face_function_from_ui_value(function_var.get())
            split_state = 'normal' if function == 'Beam Splitter' else 'disabled'
            phase_state = 'normal' if function in {'Beam Splitter', 'Mirror'} else 'disabled'
            loss_state = 'normal' if function in {'Beam Splitter', 'Mirror', 'Absorber/Mechanical'} else 'disabled'
            for widget, state in ((split_entry, split_state), (loss_entry, loss_state), (phase_entry, phase_state)):
                try:
                    widget.configure(state=state)
                except Exception:
                    pass

        def update_tree_rowheight() -> None:
            max_lines = 1
            for iid in tree.get_children(''):
                for value in tree.item(iid, 'values'):
                    max_lines = max(max_lines, str(value).count('\n') + 1)
            row_height = min(max(30, 22 * max_lines + 8), 118)
            try:
                ttk.Style(window).configure(tree_style, rowheight=row_height)
            except Exception:
                pass

        def rewrap_tree_values() -> None:
            selected = list(tree.selection())
            focus = tree.focus()
            for index, record in enumerate(records):
                iid = f'face_{index}'
                if iid in set(tree.get_children('')):
                    tree.item(iid, values=display_tree_values(record))
            update_tree_rowheight()
            valid = [iid for iid in selected if iid in set(tree.get_children(''))]
            if valid:
                tree.selection_set(valid)
            if focus in set(tree.get_children('')):
                tree.focus(focus)

        def schedule_tree_rewrap(_event=None) -> None:
            nonlocal resize_after_id
            if resize_after_id is not None:
                try:
                    window.after_cancel(resize_after_id)
                except Exception:
                    pass

            def _run_rewrap() -> None:
                nonlocal resize_after_id
                resize_after_id = None
                rewrap_tree_values()
            resize_after_id = window.after(60, _run_rewrap)

        def autosize_tree_column(column: str) -> None:
            values = [headings.get(column, column)]
            values.extend((raw_tree_values(record)[column] for record in records))
            widest = face_heading_font.measure(headings.get(column, column))
            for value in values:
                for line in str(value).splitlines() or ['']:
                    widest = max(widest, face_table_font.measure(line))
            width = max(int(widths.get(column, 80)), min(int(widest + 34), 900))
            tree.column(column, width=width, stretch=False)
            rewrap_tree_values()

        def column_from_separator_event(event) -> str | None:
            try:
                if tree.identify_region(event.x, event.y) != 'separator':
                    return None
                column_id = tree.identify_column(event.x)
                if not column_id.startswith('#'):
                    return None
                index = int(column_id[1:]) - 1
            except Exception:
                return None
            if 0 <= index < len(columns):
                return columns[index]
            return None

        def on_tree_column_double_click(event):
            column = column_from_separator_event(event)
            if column is None:
                return None
            autosize_tree_column(column)
            return 'break'

        def transformed_mesh(mesh):
            try:
                mesh = mesh.copy(deep=True)
                pts = np.asarray(mesh.points, dtype=float)
            except Exception:
                return mesh
            if pts.ndim != 2 or pts.shape[0] == 0 or pts.shape[1] < 3:
                return mesh
            rotation = le._rotation_matrix_from_kraken_tilts(float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))
            transformed = pts[:, :3] @ rotation.T
            transformed[:, 0] += float(row.desp_x)
            transformed[:, 1] += float(row.desp_y)
            transformed[:, 2] += float(z_station) + float(row.desp_z)
            mesh.points = transformed
            return mesh

        def set_preview_pick_cursor(active: bool) -> None:
            cursor = 'crosshair' if active else ''
            for widget in (preview_widget, preview_canvas_widget):
                if widget is None:
                    continue
                try:
                    widget.configure(cursor=cursor)
                except Exception:
                    pass

        def selected_input_snap_face_index() -> int | None:
            index = selected_record_index()
            if index is None or not 0 <= index < len(records):
                return None
            if le._optical_solid_face_port_role(records[index]) != le.OPTICAL_SOLID_FACE_PORT_INPUT:
                return None
            return int(index)

        def set_input_snap_pick_mode(active: bool) -> None:
            nonlocal input_snap_pick_active
            if active:
                index = selected_input_snap_face_index()
                if index is None:
                    input_snap_pick_active = False
                    input_snap_pick_button_text.set('Pick In 3D')
                    set_preview_pick_cursor(False)
                    preview_status_var.set('Pick In 3D requires the currently selected face to be the Input Port.')
                    validation_var.set('Select the intended Input Port face first, then use Pick In 3D.')
                    return
            input_snap_pick_active = bool(active)
            input_snap_pick_button_text.set('Picking...' if input_snap_pick_active else 'Pick In 3D')
            set_preview_pick_cursor(input_snap_pick_active)
            if input_snap_pick_active:
                record = records[index]
                preview_status_var.set(f"Input snap pick armed for {record.get('face_id')}: click the desired entrance point on that face.")

        def clear_input_snap_offsets() -> None:
            input_offset_u_var.set('0')
            input_offset_v_var.set('0')
            if apply_current_form_to_selection(quiet=True):
                index = selected_record_index()
                if index is not None:
                    render_face_preview(index)
                validation_var.set('Input snap offsets cleared for the selected face.')
            set_input_snap_pick_mode(False)

        def preview_world_face(index: int) -> dict[str, object] | None:
            if not 0 <= index < len(records):
                return None
            temp_row = preview_row_with_metadata()
            face_id = str(records[index].get('face_id', '') or '').strip()
            if not face_id:
                return None
            for face in le.optical_solid_face_world_records(temp_row, z_station, assigned_only=False):
                if str(face.get('face_id', '') or '').strip() == face_id:
                    return dict(face)
            return None

        def apply_input_snap_pick(index: int, point_world, *, source: str) -> bool:
            nonlocal form_loading
            selected_index = selected_input_snap_face_index()
            if selected_index is None:
                validation_var.set('Pick In 3D requires the selected face to be the Input Port.')
                set_input_snap_pick_mode(False)
                return False
            if int(index) != int(selected_index):
                target = records[selected_index].get('face_id', 'selected input face')
                preview_status_var.set(f'Input snap pick is locked to {target}. Click that face directly.')
                validation_var.set(f'Pick In 3D only applies to the selected Input Port face ({target}).')
                return False
            face = preview_world_face(index)
            if face is None:
                validation_var.set('Selected face world geometry is not available for input snap.')
                return False
            try:
                u_value, v_value, projected = le.optical_solid_metadata.optical_solid_face_project_world_point_to_uv(face, point_world)
            except Exception as exc:
                validation_var.set(f'Could not project picked point onto the face plane: {le._short_error_message(exc)}')
                return False
            iid = f'face_{index}'
            if iid in set(tree.get_children('')):
                tree.selection_set(iid)
                tree.focus(iid)
                tree.see(iid)
            load_selected()
            form_loading = True
            try:
                input_offset_u_var.set(f'{float(u_value):.6g}')
                input_offset_v_var.set(f'{float(v_value):.6g}')
            finally:
                form_loading = False
            if not apply_current_form_to_selection(quiet=True):
                return False
            render_face_preview(index)
            set_input_snap_pick_mode(False)
            validation_var.set(f"{source}: {face.get('face_id')} input snap set to U={float(u_value):.6g}, V={float(v_value):.6g} mm at world point {format_vector(projected)}.")
            preview_status_var.set(f"Input snap stored for {face.get('face_id')}: U={float(u_value):.6g}, V={float(v_value):.6g} mm")
            return True

        def preview_row_with_metadata(*, single_face: dict[str, object] | None=None) -> le.SurfaceRow:
            temp_row = le.SurfaceRow(**asdict(row))
            temp_row.advanced = dict(temp_row.advanced or {})
            faces_payload = [single_face] if isinstance(single_face, dict) else records
            temp_row.advanced[le.OPTICAL_SOLID_FACES_ADVANCED_ATTR] = le.normalize_optical_solid_face_metadata({'faces': faces_payload, 'virtual_planes': virtual_planes, 'source_stl': str(path)}, source_stl=str(path))
            return temp_row

        def mesh_from_triangles(triangles: np.ndarray):
            if le.pv is None:
                return None
            tris = np.asarray(triangles, dtype=float)
            if tris.ndim != 3 or tris.shape[0] == 0 or tris.shape[1:] != (3, 3):
                return None
            points = tris.reshape((-1, 3))
            faces = np.hstack([np.full((tris.shape[0], 1), 3, dtype=np.int64), np.arange(tris.shape[0] * 3, dtype=np.int64).reshape((-1, 3))]).ravel()
            try:
                return le.pv.PolyData(points, faces)
            except Exception:
                return None

        def candidate_mesh(index: int):
            if index in candidate_mesh_cache:
                return candidate_mesh_cache[index]
            if not 0 <= index < len(records):
                return None
            try:
                local_mesh = mesh_from_triangles(_face_source_triangles(index))
                mesh = transformed_mesh(local_mesh) if local_mesh is not None else None
            except Exception as exc:
                self.append_debug(f'CAD/STL face preview mesh failed for F{index + 1}: {exc}')
                mesh = None
            candidate_mesh_cache[index] = mesh
            return mesh

        def base_body_raw_and_edges():
            """Raw (untransformed) body surface mesh + its feature edges, read from
            disk and edge-extracted ONCE and cached -- both depend only on ``path``.
            render_face_preview applies the cheap pose transform per call, so this
            removes the per-render disk read + edge extraction (slow Face Editor)."""
            if "raw" in base_mesh_cache:
                return base_mesh_cache["raw"]
            body = edges = None
            if le.pv is not None:
                try:
                    body = le.pv.read(path).extract_surface(algorithm='dataset_surface').copy(deep=True)
                except Exception as exc:
                    self.append_debug(f'CAD/STL face preview base mesh read failed: {exc}')
                    body = None
            if body is not None and int(getattr(body, 'n_points', 0)) > 0:
                try:
                    edges = body.extract_feature_edges(feature_angle=15, boundary_edges=True, feature_edges=True, manifold_edges=False)
                except Exception:
                    edges = None
            base_mesh_cache["raw"] = (body, edges)
            return body, edges

        def offset_face_mesh(mesh, index: int, selected: bool):
            if mesh is None:
                return None
            try:
                mesh = mesh.copy(deep=True)
                normal = np.asarray(records[index].get('normal', [0.0, 0.0, 1.0]), dtype=float).reshape(-1)[:3]
                if bool(records[index].get('flip_normal', False)):
                    normal = -normal
                rotation = le._rotation_matrix_from_kraken_tilts(float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))
                normal = normal @ rotation.T
                norm = float(np.linalg.norm(normal))
                if norm <= 1e-12 or not np.isfinite(norm):
                    return mesh
                normal = normal / norm
                mesh.points = np.asarray(mesh.points, dtype=float) + normal * max(mesh_span * (0.0015 if selected else 0.0007), 0.01)
                return mesh
            except Exception:
                return mesh

        def add_preview_actor(mesh, *, color: tuple[float, float, float], opacity: float, pick_index: int | None=None, line_width: float=1.0, wireframe: bool=False):
            if preview_renderer is None or le.vtkActor is None or le.vtkDataSetMapper is None or (mesh is None):
                return None
            try:
                if int(getattr(mesh, 'n_points', 0)) <= 0:
                    return None
            except Exception:
                return None
            mapper = le.vtkDataSetMapper()
            mapper.SetInputData(mesh)
            actor = le.vtkActor()
            actor.SetMapper(mapper)
            prop = actor.GetProperty()
            prop.SetColor(*color)
            prop.SetOpacity(float(opacity))
            prop.SetLineWidth(float(line_width))
            if wireframe:
                prop.SetRepresentationToWireframe()
            else:
                prop.SetInterpolationToFlat()
                prop.SetAmbient(0.45)
                prop.SetDiffuse(0.55)
            if pick_index is None:
                actor.PickableOff()
            else:
                actor.PickableOn()
                actor_key = le.Kraken3DInspector._actor_key(actor)
                if actor_key is not None:
                    preview_actor_map[actor_key] = int(pick_index)
            preview_renderer.AddActor(actor)
            return actor

        def add_selected_normal_arrow(index: int) -> None:
            if le.pv is None or not 0 <= index < len(records):
                return
            try:
                temp_row = preview_row_with_metadata(single_face=records[index])
                markers = le.optical_solid_face_world_markers(temp_row, z_station, assigned_only=False)
                if not markers:
                    return
                marker = markers[0]
                length = le.Kraken3DInspector._face_role_marker_scale(marker, mesh_span)
                start = np.asarray(marker.centroid, dtype=float)
                normal = np.asarray(marker.normal, dtype=float)
                add_preview_actor(le.pv.Arrow(start=tuple(start[:3]), direction=tuple(normal[:3]), scale=length), color=(1.0, 0.48, 0.02), opacity=0.98, line_width=2.0)
            except Exception as exc:
                self.append_debug(f'CAD/STL selected face normal preview failed: {exc}')

        def add_selected_input_anchor_marker(index: int) -> None:
            if le.pv is None or not 0 <= index < len(records):
                return
            try:
                face = preview_world_face(index)
                if face is None:
                    return
                anchor = np.asarray(face.get('anchor_world', face.get('centroid_world', (np.nan, np.nan, np.nan))), dtype=float).reshape(-1)[:3]
                if anchor.size < 3 or not np.all(np.isfinite(anchor)):
                    return
                add_preview_actor(le.pv.Sphere(radius=max(mesh_span * 0.012, 0.22), center=tuple(anchor[:3])), color=(0.84, 0.12, 0.08), opacity=0.98)
            except Exception as exc:
                self.append_debug(f'CAD/STL input-anchor preview failed: {exc}')

        def add_selected_input_uv_gizmo(index: int) -> None:
            if le.pv is None or not 0 <= index < len(records):
                return
            try:
                face = preview_world_face(index)
                if face is None:
                    return
                anchor = np.asarray(face.get('anchor_world', face.get('centroid_world', (np.nan, np.nan, np.nan))), dtype=float).reshape(-1)[:3]
                u_axis = np.asarray(face.get('u_axis_world', (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)[:3]
                v_axis = np.asarray(face.get('v_axis_world', (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)[:3]
                if not (anchor.size >= 3 and u_axis.size >= 3 and (v_axis.size >= 3) and np.all(np.isfinite(anchor)) and np.all(np.isfinite(u_axis)) and np.all(np.isfinite(v_axis))):
                    return
                u_norm = float(np.linalg.norm(u_axis))
                v_norm = float(np.linalg.norm(v_axis))
                if u_norm <= 1e-12 or v_norm <= 1e-12:
                    return
                scale = max(mesh_span * 0.1, 1.2)
                add_preview_actor(le.pv.Arrow(start=tuple(anchor[:3]), direction=tuple((u_axis / u_norm)[:3]), scale=scale), color=(0.86, 0.18, 0.18), opacity=0.96, line_width=2.0)
                add_preview_actor(le.pv.Arrow(start=tuple(anchor[:3]), direction=tuple((v_axis / v_norm)[:3]), scale=scale), color=(0.15, 0.62, 0.24), opacity=0.96, line_width=2.0)
            except Exception as exc:
                self.append_debug(f'CAD/STL input U/V gizmo preview failed: {exc}')

        def add_virtual_plane_overlays_to_preview() -> None:
            if le.pv is None or not virtual_planes:
                return
            try:
                temp_row = preview_row_with_metadata()
                for marker in le.optical_solid_virtual_plane_world_markers(temp_row, z_station, assigned_only=True):
                    center = np.asarray(marker.centroid, dtype=float)
                    normal = np.asarray(marker.normal, dtype=float)
                    norm = float(np.linalg.norm(normal[:3]))
                    if norm <= 1e-12 or not np.isfinite(norm):
                        continue
                    normal = normal[:3] / norm
                    size = max(float(marker.aperture_mm), max(mesh_span * 0.18, 1.0))
                    plane = le.pv.Plane(center=tuple(center[:3]), direction=tuple(normal), i_size=size, j_size=size, i_resolution=1, j_resolution=1)
                    add_preview_actor(plane, color=marker.color, opacity=0.16)
                    try:
                        edges = plane.extract_feature_edges(boundary_edges=True, feature_edges=False, manifold_edges=False)
                        add_preview_actor(edges, color=marker.color, opacity=0.98, line_width=2.0)
                    except Exception:
                        pass
                    add_preview_actor(le.pv.Arrow(start=tuple(center[:3]), direction=tuple(normal), scale=max(size * 0.45, 1.0)), color=marker.color, opacity=0.96)
            except Exception as exc:
                self.append_debug(f'CAD/STL virtual plane preview failed: {exc}')

        def render_face_preview(selected_index: int | None=None, *, reset_camera: bool=False) -> None:
            if preview_renderer is None:
                return
            preview_renderer.RemoveAllViewProps()
            preview_actor_map.clear()
            raw_body, raw_edges = base_body_raw_and_edges()
            if raw_body is None or int(getattr(raw_body, 'n_points', 0)) <= 0:
                preview_status_var.set('3D preview unavailable: mesh has no points.')
                return
            base_mesh = transformed_mesh(raw_body)
            add_preview_actor(base_mesh, color=(0.12, 0.78, 0.86), opacity=0.18)
            if raw_edges is not None and int(getattr(raw_edges, 'n_points', 0)) > 0:
                try:
                    add_preview_actor(transformed_mesh(raw_edges), color=(0.05, 0.18, 0.24), opacity=1.0, line_width=1.2)
                except Exception:
                    pass
            selected_index = selected_record_index() if selected_index is None else selected_index
            visible_faces = 0
            offset_meshes: dict[int, object] = {}
            for index, record in enumerate(records):
                mesh = offset_face_mesh(candidate_mesh(index), index, selected=index == selected_index)
                if mesh is None:
                    continue
                visible_faces += 1
                role = le._legacy_role_from_optical_solid_face_function(record.get('function', record.get('role')))
                side = le._normalize_optical_solid_face_side(record.get('side_2d'))
                color = (1.0, 0.48, 0.02) if index == selected_index else le.optical_solid_face_role_color(role)
                assigned = role != le.OPTICAL_SOLID_FACE_ROLE_DEFAULT or side != le.OPTICAL_SOLID_FACE_SIDE_DEFAULT
                opacity = 0.3 if index == selected_index else 0.08 if assigned else 0.035
                add_preview_actor(mesh, color=color, opacity=opacity, pick_index=index)
                offset_meshes[index] = mesh
            # Feature edges drawn per logical GROUP, not per face: a curved
            # surface the importer split into several faces (a lens rim = several
            # co-axial cylinder faces, or the planar clusterer's ~160 micro
            # candidates) merges into one clean edge instead of a fragmented
            # wireframe, and non-selected groups are drawn faint so the selected
            # face stays the unambiguous highlight (bugs/0013). feature_angle=18
            # drops a curved surface's interior facets, keeping its real edges.
            edge_groups: dict[object, list[int]] = {}
            for index in offset_meshes:
                gid = group_index_by_record_index.get(index, -1)
                edge_groups.setdefault(gid if gid >= 0 else ('solo', index), []).append(index)
            for members in edge_groups.values():
                is_selected_group = selected_index is not None and selected_index in members
                merged = None
                for index in members:
                    piece = offset_meshes.get(index)
                    if piece is None:
                        continue
                    merged = piece.copy(deep=True) if merged is None else merged.merge(piece)
                if merged is None:
                    continue
                try:
                    welded = merged.clean(tolerance=1.0e-4) if hasattr(merged, 'clean') else merged
                    edges = welded.extract_feature_edges(feature_angle=18, boundary_edges=True, feature_edges=True, manifold_edges=False)
                except Exception:
                    continue
                rep = members[0]
                rep_role = le._legacy_role_from_optical_solid_face_function(records[rep].get('function', records[rep].get('role')))
                edge_color = (1.0, 0.28, 0.0) if is_selected_group else le.optical_solid_face_role_color(rep_role)
                add_preview_actor(edges, color=edge_color, opacity=1.0 if is_selected_group else 0.22, line_width=4.0 if is_selected_group else 1.1)
            if selected_index is not None:
                add_selected_normal_arrow(selected_index)
                add_selected_input_anchor_marker(selected_index)
                add_selected_input_uv_gizmo(selected_index)
            add_virtual_plane_overlays_to_preview()
            if reset_camera:
                preview_renderer.ResetCamera()
            try:
                preview_renderer.ResetCameraClippingRange()
                preview_widget.GetRenderWindow().Render()
            except Exception:
                pass
            if input_snap_pick_active:
                selected_face = records[selected_index] if selected_index is not None and 0 <= selected_index < len(records) else {}
                preview_status_var.set(f"Input snap pick armed for {selected_face.get('face_id', 'selected Input Port')}: click that face | candidates={visible_faces}")
            else:
                preview_status_var.set(f'3D face preview: click selects, left-drag rotates | candidates={visible_faces}')

        def select_face_index(index: int, *, source: str) -> None:
            if not 0 <= index < len(records):
                return
            iid = f'face_{index}'
            if iid not in set(tree.get_children('')):
                return
            tree.selection_set(iid)
            tree.focus(iid)
            tree.see(iid)
            load_selected()
            render_face_preview(index)
            record = records[index]
            validation_var.set(f"{source}: selected {record.get('face_id')}. Choose 2D side, coating/interaction, and port role, then Apply.")

        def on_preview_click(_obj, _event) -> None:
            if preview_picker is None or preview_renderer is None or preview_interactor is None:
                return
            try:
                x, y = preview_interactor.GetEventPosition()
                preview_picker.Pick(x, y, 0.0, preview_renderer)
                actor = preview_picker.GetActor()
                actor_key = le.Kraken3DInspector._actor_key(actor)
                index = preview_actor_map.get(actor_key) if actor_key is not None else None
                point_world = np.asarray(preview_picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
            except Exception:
                index = None
                point_world = np.asarray((np.nan, np.nan, np.nan), dtype=float)
            if index is None:
                preview_status_var.set('Input snap pick: click directly on a coloured planar face.' if input_snap_pick_active else 'Click directly on one of the coloured planar faces.')
                return
            if input_snap_pick_active:
                if point_world.size < 3 or not np.all(np.isfinite(point_world)):
                    preview_status_var.set('Input snap pick failed: invalid picked 3D point.')
                    return
                apply_input_snap_pick(int(index), point_world, source='3D pick')
                return
            select_face_index(int(index), source='3D pick')

        def rotate_preview_camera_fixed_drag(dx: int | float, dy: int | float) -> None:
            if preview_renderer is None:
                return
            camera = preview_renderer.GetActiveCamera()
            if camera is None:
                return
            try:
                dx_f = float(dx)
                dy_f = float(dy)
            except Exception:
                return
            if abs(dx_f) < 1e-12 and abs(dy_f) < 1e-12:
                return
            degrees_per_pixel = 0.22
            try:
                focal = tuple((float(value) for value in camera.GetFocalPoint()))
                camera.SetFocalPoint(*focal)
                camera.Azimuth(-dx_f * degrees_per_pixel)
                camera.Elevation(dy_f * degrees_per_pixel)
                camera.SetFocalPoint(*focal)
                camera.OrthogonalizeViewUp()
                preview_renderer.ResetCameraClippingRange()
                if preview_widget is not None:
                    preview_widget.GetRenderWindow().Render()
            except Exception as exc:
                self.append_debug(f'CAD/STL face preview camera rotate failed: {exc}')

        def install_vtk_face_preview_mouse_bindings() -> None:
            """Match Open 3D: click selects; left-drag rotates without default VTK acceleration."""
            if preview_widget is None:
                return
            drag_threshold_px = 4

            def set_event_info(event) -> None:
                if preview_interactor is not None:
                    try:
                        preview_interactor.SetEventInformationFlipY(event.x, event.y, 0, 0, chr(0), 0, None)
                    except Exception:
                        pass

            def left_press(event):
                nonlocal preview_drag_active, preview_drag_start_xy, preview_drag_last_xy, preview_drag_moved
                set_event_info(event)
                preview_drag_active = True
                preview_drag_start_xy = (int(event.x), int(event.y))
                preview_drag_last_xy = (int(event.x), int(event.y))
                preview_drag_moved = False
                return 'break'

            def left_motion(event):
                nonlocal preview_drag_last_xy, preview_drag_moved
                set_event_info(event)
                if not preview_drag_active:
                    return 'break'
                current = (int(event.x), int(event.y))
                start = preview_drag_start_xy or current
                last = preview_drag_last_xy or current
                total_dx = current[0] - start[0]
                total_dy = current[1] - start[1]
                if total_dx * total_dx + total_dy * total_dy >= drag_threshold_px * drag_threshold_px:
                    preview_drag_moved = True
                if preview_drag_moved:
                    rotate_preview_camera_fixed_drag(current[0] - last[0], current[1] - last[1])
                preview_drag_last_xy = current
                return 'break'

            def left_release(event):
                nonlocal preview_drag_active, preview_drag_start_xy, preview_drag_last_xy, preview_drag_moved
                set_event_info(event)
                should_pick = preview_drag_active and (not preview_drag_moved)
                preview_drag_active = False
                preview_drag_start_xy = None
                preview_drag_last_xy = None
                preview_drag_moved = False
                if should_pick:
                    on_preview_click(None, None)
                return 'break'
            try:
                preview_widget.bind('<ButtonPress-1>', left_press)
                preview_widget.bind('<B1-Motion>', left_motion)
                preview_widget.bind('<ButtonRelease-1>', left_release)
                preview_widget.bind('<Control-ButtonPress-1>', left_press)
                preview_widget.bind('<Control-B1-Motion>', left_motion)
                preview_widget.bind('<Control-ButtonRelease-1>', left_release)
            except Exception as exc:
                self.append_debug(f'CAD/STL face preview mouse binding failed: {exc}')

        def install_matplotlib_face_preview(reason: str) -> None:
            nonlocal render_face_preview, preview_canvas_widget
            from matplotlib.path import Path as MplPath
            from mpl_toolkits.mplot3d import proj3d
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection
            for child in preview_host.winfo_children():
                try:
                    child.destroy()
                except Exception:
                    pass
            figure = le.Figure(figsize=(5.2, 4.8), dpi=100)
            axis = figure.add_subplot(111, projection='3d')
            canvas = le.FigureCanvasTkAgg(figure, master=preview_host)
            preview_canvas_widget = canvas.get_tk_widget()
            preview_canvas_widget.grid(row=0, column=0, sticky='nsew')
            transformed_tri_cache: dict[int, np.ndarray] = {}
            mpl_view_state = {'elev': 22.0, 'azim': -55.0}
            mpl_drag_state: dict[str, object] = {'active': False, 'start': None, 'last': None, 'moved': False}
            try:
                axis.disable_mouse_rotation()
            except Exception:
                pass

            def transformed_triangles(index: int) -> np.ndarray:
                if index in transformed_tri_cache:
                    return transformed_tri_cache[index]
                if not 0 <= index < len(records):
                    return np.empty((0, 3, 3), dtype=float)
                try:
                    triangles = _face_source_triangles(index)
                except Exception as exc:
                    self.append_debug(f'Matplotlib CAD/STL face triangles failed for S{row_index} F{index + 1}: {exc}')
                    triangles = np.empty((0, 3, 3), dtype=float)
                if triangles.size:
                    rotation = le._rotation_matrix_from_kraken_tilts(float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))
                    points = triangles.reshape((-1, 3)) @ rotation.T
                    points[:, 0] += float(row.desp_x)
                    points[:, 1] += float(row.desp_y)
                    points[:, 2] += float(z_station) + float(row.desp_z)
                    triangles = points.reshape((-1, 3, 3))
                transformed_tri_cache[index] = np.asarray(triangles, dtype=float)
                return transformed_tri_cache[index]

            def set_equal_axes(points: np.ndarray) -> None:
                if points.size == 0:
                    return
                bounds_min = np.min(points, axis=0)
                bounds_max = np.max(points, axis=0)
                center = 0.5 * (bounds_min + bounds_max)
                radius = max(float(np.max(bounds_max - bounds_min)) * 0.55, 1.0)
                axis.set_xlim(center[0] - radius, center[0] + radius)
                axis.set_ylim(center[1] - radius, center[1] + radius)
                axis.set_zlim(center[2] - radius, center[2] + radius)
                try:
                    axis.set_box_aspect((1, 1, 1))
                except Exception:
                    pass

            def render_face_preview(selected_index: int | None=None, *, reset_camera: bool=False) -> None:
                axis.clear()
                try:
                    axis.disable_mouse_rotation()
                except Exception:
                    pass
                selected_index = selected_record_index() if selected_index is None else selected_index
                all_points: list[np.ndarray] = []
                visible_faces = 0
                for index, record in enumerate(records):
                    triangles = transformed_triangles(index)
                    if triangles.size == 0:
                        continue
                    visible_faces += 1
                    all_points.append(triangles.reshape((-1, 3)))
                    role = le._legacy_role_from_optical_solid_face_function(record.get('function', record.get('role')))
                    side = le._normalize_optical_solid_face_side(record.get('side_2d'))
                    color = (1.0, 0.48, 0.02) if index == selected_index else le.optical_solid_face_role_color(role)
                    assigned = role != le.OPTICAL_SOLID_FACE_ROLE_DEFAULT or side != le.OPTICAL_SOLID_FACE_SIDE_DEFAULT
                    alpha = 0.3 if index == selected_index else 0.12 if assigned else 0.045
                    collection = le.Poly3DCollection(triangles, facecolors=[(*color, alpha)], edgecolors=[(0.08, 0.12, 0.16, 0.55)], linewidths=0.45)
                    axis.add_collection3d(collection)
                    if index == selected_index:
                        centroid = np.mean(triangles.reshape((-1, 3)), axis=0)
                        normal = np.asarray(records[index].get('normal', [0.0, 0.0, 1.0]), dtype=float).reshape(-1)[:3]
                        if bool(records[index].get('flip_normal', False)):
                            normal = -normal
                        normal = normal @ le._rotation_matrix_from_kraken_tilts(float(row.tilt_x), float(row.tilt_y), float(row.tilt_z)).T
                        norm = float(np.linalg.norm(normal))
                        if norm > 1e-12 and np.isfinite(norm):
                            normal = normal / norm
                            length = max(mesh_span * 0.18, 1.0)
                            axis.quiver(centroid[0], centroid[1], centroid[2], normal[0], normal[1], normal[2], length=length, color=(1.0, 0.28, 0.0), linewidth=2.0)
                        face = preview_world_face(index)
                        if face is not None:
                            anchor = np.asarray(face.get('anchor_world', face.get('centroid_world', (np.nan, np.nan, np.nan))), dtype=float).reshape(-1)[:3]
                            if anchor.size == 3 and np.all(np.isfinite(anchor)):
                                axis.scatter([float(anchor[0])], [float(anchor[1])], [float(anchor[2])], s=42, color='#d62728', depthshade=False, edgecolors='white', linewidths=0.8)
                            u_axis = np.asarray(face.get('u_axis_world', (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)[:3]
                            v_axis = np.asarray(face.get('v_axis_world', (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)[:3]
                            if u_axis.size == 3 and v_axis.size == 3 and np.all(np.isfinite(u_axis)) and np.all(np.isfinite(v_axis)):
                                u_norm = float(np.linalg.norm(u_axis))
                                v_norm = float(np.linalg.norm(v_axis))
                                if u_norm > 1e-12 and v_norm > 1e-12:
                                    gizmo_scale = max(mesh_span * 0.1, 1.2)
                                    u_dir = u_axis / u_norm * gizmo_scale
                                    v_dir = v_axis / v_norm * gizmo_scale
                                    axis.quiver(anchor[0], anchor[1], anchor[2], u_dir[0], u_dir[1], u_dir[2], color='#d62728', linewidth=1.8, arrow_length_ratio=0.16)
                                    axis.quiver(anchor[0], anchor[1], anchor[2], v_dir[0], v_dir[1], v_dir[2], color='#2ca02c', linewidth=1.8, arrow_length_ratio=0.16)
                                    axis.text(float(anchor[0] + u_dir[0]), float(anchor[1] + u_dir[1]), float(anchor[2] + u_dir[2]), 'U', color='#d62728', fontsize=8)
                                    axis.text(float(anchor[0] + v_dir[0]), float(anchor[1] + v_dir[1]), float(anchor[2] + v_dir[2]), 'V', color='#2ca02c', fontsize=8)
                if all_points:
                    set_equal_axes(np.vstack(all_points))
                axis.set_title('Click a face to select it', fontsize=10)
                axis.set_xlabel('X [mm]')
                axis.set_ylabel('Y [mm]')
                axis.set_zlabel('Z [mm]')
                if reset_camera:
                    mpl_view_state['elev'] = 22.0
                    mpl_view_state['azim'] = -55.0
                axis.view_init(elev=float(mpl_view_state['elev']), azim=float(mpl_view_state['azim']))
                figure.tight_layout(pad=0.3)
                canvas.draw_idle()
                reason_text = f' | {reason}' if reason else ''
                if input_snap_pick_active:
                    selected_face = records[selected_index] if selected_index is not None and 0 <= selected_index < len(records) else {}
                    preview_status_var.set(f"Input snap pick armed for {selected_face.get('face_id', 'selected Input Port')}: click that face | candidates={visible_faces}{reason_text}")
                else:
                    preview_status_var.set(f'3D face preview: click selects, left-drag rotates | candidates={visible_faces}{reason_text}')

            def estimate_world_point_on_face(index: int, clicked_xy: np.ndarray, projection) -> np.ndarray | None:
                triangles = transformed_triangles(index)
                if triangles.size == 0:
                    return None
                best_distance = float('inf')
                best_point: np.ndarray | None = None
                samples_per_edge = 12
                for triangle in triangles:
                    v0, v1, v2 = (np.asarray(vertex, dtype=float).reshape(3) for vertex in triangle)
                    for i in range(samples_per_edge + 1):
                        for j in range(samples_per_edge + 1 - i):
                            a = float(i) / float(samples_per_edge)
                            b = float(j) / float(samples_per_edge)
                            c = 1.0 - a - b
                            point = a * v0 + b * v1 + c * v2
                            px, py, _pz = le.proj3d.proj_transform(point[0], point[1], point[2], projection)
                            screen = np.asarray(axis.transData.transform((px, py)), dtype=float)
                            distance = float(np.linalg.norm(screen - clicked_xy))
                            if distance < best_distance:
                                best_distance = distance
                                best_point = point
                return None if best_point is None else np.asarray(best_point, dtype=float)

            def pick_from_matplotlib_click(event) -> tuple[int | None, np.ndarray | None]:
                if event.inaxes is not axis or event.x is None or event.y is None:
                    return (None, None)
                clicked = np.asarray([float(event.x), float(event.y)], dtype=float)
                projection = axis.get_proj()
                hits: list[tuple[float, int, np.ndarray | None]] = []
                nearest: tuple[float, int] | None = None
                for index in range(len(records)):
                    triangles = transformed_triangles(index)
                    if triangles.size == 0:
                        continue
                    centroid = np.mean(triangles.reshape((-1, 3)), axis=0)
                    cx, cy, _cz = le.proj3d.proj_transform(centroid[0], centroid[1], centroid[2], projection)
                    centroid_xy = np.asarray(axis.transData.transform((cx, cy)), dtype=float)
                    distance = float(np.linalg.norm(clicked - centroid_xy))
                    if nearest is None or distance < nearest[0]:
                        nearest = (distance, index)
                    for triangle in triangles:
                        xs, ys, _zs = le.proj3d.proj_transform(triangle[:, 0], triangle[:, 1], triangle[:, 2], projection)
                        polygon = np.asarray(axis.transData.transform(np.column_stack([xs, ys])), dtype=float)
                        if le.MplPath(polygon).contains_point(clicked, radius=3.0):
                            hits.append((distance, index, estimate_world_point_on_face(index, clicked, projection)))
                            break
                if hits:
                    _distance, index, point = min(hits, key=lambda item: item[0])
                    return (int(index), point)
                if nearest is not None and nearest[0] <= 55.0:
                    return (int(nearest[1]), None)
                return (None, None)

            def on_matplotlib_press(event) -> None:
                if event.inaxes is not axis or event.button != 1 or event.x is None or (event.y is None):
                    return
                point = (int(event.x), int(event.y))
                mpl_drag_state['active'] = True
                mpl_drag_state['start'] = point
                mpl_drag_state['last'] = point
                mpl_drag_state['moved'] = False

            def on_matplotlib_motion(event) -> None:
                if not bool(mpl_drag_state.get('active')) or event.x is None or event.y is None:
                    return
                current = (int(event.x), int(event.y))
                start = mpl_drag_state.get('start') or current
                last = mpl_drag_state.get('last') or current
                total_dx = current[0] - start[0]
                total_dy = current[1] - start[1]
                if total_dx * total_dx + total_dy * total_dy >= 4 * 4:
                    mpl_drag_state['moved'] = True
                if bool(mpl_drag_state.get('moved')):
                    dx = current[0] - last[0]
                    dy = current[1] - last[1]
                    mpl_view_state['azim'] = float(mpl_view_state['azim']) - float(dx) * 0.22
                    mpl_view_state['elev'] = max(-89.0, min(89.0, float(mpl_view_state['elev']) + float(dy) * 0.22))
                    axis.view_init(elev=float(mpl_view_state['elev']), azim=float(mpl_view_state['azim']))
                    canvas.draw_idle()
                mpl_drag_state['last'] = current

            def on_matplotlib_release(event) -> None:
                if event.button != 1:
                    return
                should_pick = bool(mpl_drag_state.get('active')) and (not bool(mpl_drag_state.get('moved')))
                mpl_drag_state['active'] = False
                mpl_drag_state['start'] = None
                mpl_drag_state['last'] = None
                mpl_drag_state['moved'] = False
                if should_pick:
                    index, point = pick_from_matplotlib_click(event)
                    if index is None:
                        preview_status_var.set('Input snap pick: click closer to a coloured face candidate.' if input_snap_pick_active else 'Click closer to a coloured face candidate.')
                        return
                    if input_snap_pick_active:
                        if point is None:
                            preview_status_var.set('Input snap pick requires a direct click on the selected face.')
                            return
                        apply_input_snap_pick(int(index), point, source='3D pick')
                    else:
                        select_face_index(int(index), source='3D pick' if point is not None else '3D nearest')
            canvas.mpl_connect('button_press_event', on_matplotlib_press)
            canvas.mpl_connect('motion_notify_event', on_matplotlib_motion)
            canvas.mpl_connect('button_release_event', on_matplotlib_release)
            set_preview_pick_cursor(input_snap_pick_active)
            render_face_preview(selected_record_index(), reset_camera=True)
        if le.pv is None or le.vtkTkRenderWindowInteractor is None or le.vtkRenderer is None:
            install_matplotlib_face_preview(le._VTK_TK_UNAVAILABLE_REASON or 'VTK/Tk unavailable; Matplotlib/Tk picker active')
        else:
            try:
                le._prepare_vtk_tk_widget(preview_host)
                preview_widget = le.vtkTkRenderWindowInteractor(preview_host, width=480, height=520)
                preview_widget.grid(row=0, column=0, sticky='nsew')
                preview_renderer = le.vtkRenderer()
                preview_widget.GetRenderWindow().AddRenderer(preview_renderer)
                preview_renderer.SetBackground(1.0, 1.0, 1.0)
                preview_interactor = preview_widget.GetRenderWindow().GetInteractor()
                if le.vtkCellPicker is not None:
                    preview_picker = le.vtkCellPicker()
                    preview_picker.SetTolerance(0.0008)
                try:
                    preview_widget.Initialize()
                except Exception:
                    pass
                install_vtk_face_preview_mouse_bindings()
                set_preview_pick_cursor(input_snap_pick_active)
                try:
                    points = transformed_mesh(le.pv.read(path).extract_surface(algorithm='dataset_surface').copy(deep=True)).points
                    bounds_min = np.min(np.asarray(points, dtype=float), axis=0)
                    bounds_max = np.max(np.asarray(points, dtype=float), axis=0)
                    mesh_span = max(float(np.max(bounds_max - bounds_min)), 1.0)
                except Exception:
                    mesh_span = 1.0
            except Exception as exc:
                preview_renderer = None
                self.append_debug(f'VTK/Tk CAD/STL face picker unavailable; using Matplotlib fallback: {exc}')
                install_matplotlib_face_preview('Matplotlib fallback picker')
        input_snap_pick_button.configure(command=lambda: set_input_snap_pick_mode(not input_snap_pick_active))
        clear_input_snap_button.configure(command=clear_input_snap_offsets)

        def refresh_tree(select_iid: str | list[str] | tuple[str, ...] | None=None) -> None:
            existing_selection = list(tree.selection())
            tree.delete(*tree.get_children())
            for index, record in enumerate(records):
                iid = f'face_{index}'
                tree.insert('', 'end', iid=iid, values=display_tree_values(record))
            update_tree_rowheight()
            if select_iid is None:
                targets = existing_selection
            elif isinstance(select_iid, (list, tuple, set)):
                targets = [str(item) for item in select_iid]
            else:
                targets = [str(select_iid)]
            valid_targets = [target for target in targets if target in set(tree.get_children(''))]
            if valid_targets:
                tree.selection_set(valid_targets)
                tree.focus(valid_targets[0])

        def load_selected(_event=None) -> None:
            nonlocal form_loading
            index = selected_record_index()
            if index is None:
                return
            record = records[index]
            selected_count = len(selected_record_indices())
            if not isinstance(record, dict):
                return
            form_loading = True
            try:
                side_var.set(le._normalize_optical_solid_face_side(record.get('side_2d')))
                function_var.set(le._optical_solid_face_function_display(record.get('function'), legacy_role=record.get('role')))
                port_var.set(le._normalize_optical_solid_face_port_role(record.get('port_role')))
                fit_reference_var.set(le._normalize_optical_solid_face_fit_reference(record.get('fit_reference')))
                update_face_property_field_states()
                input_offset_u_var.set(f"{float(record.get('input_offset_u_mm', 0.0) or 0.0):.6g}")
                input_offset_v_var.set(f"{float(record.get('input_offset_v_mm', 0.0) or 0.0):.6g}")
                split_var.set(f"{float(record.get('split_ratio', 0.5) or 0.0):.6g}")
                loss_var.set(f"{float(record.get('loss', 0.0) or 0.0):.6g}")
                phase_var.set(f"{float(record.get('phase_deg', 0.0) or 0.0):.6g}")
                aperture_var.set(f"{float(record.get('clear_aperture_mm', 0.0) or 0.0):.6g}")
                material_var.set(str(record.get('material', '') or ''))
                coating_var.set(str(record.get('coating', '') or ''))
                face_coating_state['table'] = record.get('coating_table') or None
                try:
                    face_coating_state['met'] = int(record.get('coating_met', 0) or 0)
                except Exception:
                    face_coating_state['met'] = 0
                flip_var.set(bool(record.get('flip_normal', False)))
                notes_var.set(str(record.get('notes', '') or ''))
            finally:
                form_loading = False
            authored_port = le._optical_solid_face_authored_port_role(record)
            effective_port = le._optical_solid_face_port_role(record)
            port_text = authored_port
            if authored_port != effective_port:
                port_text = f'{authored_port} -> effective {effective_port}'
            suggestion = le._optical_solid_face_suggestion_label(record)
            suggestion_text = f' | suggested {suggestion}' if suggestion else ''
            validation_var.set(f"{record.get('face_id')}: {side_var.get()} / {function_var.get()} / {port_text} | normal {format_vector(record.get('normal'))}, centroid {format_vector(record.get('centroid'))}" + f', snap_uv=({input_offset_u_var.get()},{input_offset_v_var.get()})' + suggestion_text + (f' | {selected_count} faces selected' if selected_count > 1 else ''))
            render_face_preview(index)

        def parse_form() -> dict[str, object] | None:
            side = le._normalize_optical_solid_face_side(side_var.get())
            function_value = str(function_var.get()).strip()
            function = le._optical_solid_face_function_from_ui_value(function_value)
            port_role = le._normalize_optical_solid_face_port_role(port_var.get())
            valid_function_tokens = set(le.OPTICAL_SOLID_FACE_FUNCTION_VALUES) | set(le.optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_VALUES)
            if function_value not in valid_function_tokens:
                validation_var.set('Invalid surface coating / interaction.')
                return None
            if str(port_var.get()).strip() not in le.OPTICAL_SOLID_FACE_PORT_VALUES:
                validation_var.set('Invalid port role.')
                return None
            if str(fit_reference_var.get()).strip() not in le.OPTICAL_SOLID_FACE_FIT_REFERENCE_VALUES:
                validation_var.set('Invalid fit reference normal.')
                return None
            split = le._float_or_default(split_var.get(), 0.5)
            loss = le._float_or_default(loss_var.get(), 0.0)
            phase = le._float_or_default(phase_var.get(), 0.0)
            aperture = le._float_or_default(aperture_var.get(), 0.0)
            input_offset_u = le._float_or_default(input_offset_u_var.get(), 0.0)
            input_offset_v = le._float_or_default(input_offset_v_var.get(), 0.0)
            if not 0.0 <= split <= 1.0:
                validation_var.set('Split ratio must be between 0 and 1.')
                return None
            if not 0.0 <= loss <= 1.0:
                validation_var.set('Loss must be between 0 and 1.')
                return None
            if aperture < 0.0:
                validation_var.set('Clear aperture cannot be negative.')
                return None
            role = le._legacy_role_from_optical_solid_face_function(function)
            return {'role': role, 'function': function, 'side_2d': side, 'port_role': port_role, 'fit_reference': le._normalize_optical_solid_face_fit_reference(fit_reference_var.get()), 'split_ratio': split, 'loss': loss, 'phase_deg': phase, 'clear_aperture_mm': aperture, 'input_offset_u_mm': input_offset_u, 'input_offset_v_mm': input_offset_v, 'material': str(material_var.get()).strip(), 'coating': str(coating_var.get()).strip(), 'coating_table': (face_coating_state.get('table') or []), 'coating_met': int(face_coating_state.get('met', 0) or 0), 'flip_normal': bool(flip_var.get()), 'notes': str(notes_var.get()).strip()}

        def apply_current_form_to_selection(*, quiet: bool=False) -> bool:
            indices = selected_record_indices()
            if not indices:
                if not quiet:
                    validation_var.set('Select a face candidate first.')
                return False
            parsed = parse_form()
            if parsed is None:
                return False
            selected_iids = [f'face_{index}' for index in indices]
            for index in indices:
                record = records[index]
                record.update(parsed)
                refreshed = le.normalize_optical_solid_face_record(record)
                record.clear()
                record.update(refreshed)
            refresh_tree(selected_iids)
            render_face_preview(selected_record_index())
            if quiet:
                return True
            if len(indices) == 1:
                record = records[indices[0]]
                validation_var.set(f"Applied {le._normalize_optical_solid_face_side(record.get('side_2d'))} / {le._optical_solid_face_function_display(record.get('function'), legacy_role=record.get('role'))} to {record['face_id']}.")
            else:
                validation_var.set(f"Applied {parsed['side_2d']} / {le._optical_solid_face_function_display(parsed['function'])} to {len(indices)} selected faces.")
            return True

        # auto-apply (bound to every side/function/port/fit field) persisted the
        # metadata AND ran a full Open 3D retrace on every change, so a few field
        # tweaks fired several full system retraces -- the slow Face Editor the
        # user reported. Persisting stays synchronous (no lost edits); the
        # expensive retrace is debounced + coalesced onto the main editor's loop.
        face_editor_retrace_after: dict[str, object] = {"id": None}

        def cancel_pending_face_editor_retrace() -> None:
            pending = face_editor_retrace_after.get("id")
            if pending is not None:
                try:
                    self.after_cancel(pending)
                except Exception:
                    pass
                face_editor_retrace_after["id"] = None

        def schedule_face_editor_retrace() -> None:
            cancel_pending_face_editor_retrace()

            def _run_retrace() -> None:
                face_editor_retrace_after["id"] = None
                try:
                    self._refresh_open_3d_views(force_retrace=True)
                except Exception as exc:
                    self.append_debug(f"Face Editor debounced retrace failed: {exc}")

            face_editor_retrace_after["id"] = self.after(250, _run_retrace)

        def persist_face_editor_metadata(reason: str='Face Editor') -> None:
            metadata_to_save = le.normalize_optical_solid_face_metadata({'faces': records, 'virtual_planes': virtual_planes, 'source_stl': str(path)}, source_stl=str(path))
            self._begin_history_capture()
            target = self.rows[row_index]
            target.advanced = dict(target.advanced or {})
            target.advanced[le.OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata_to_save
            self._sync_table()
            self._commit_history_capture()
            self._mark_plot_update_pending()
            reason_text = str(reason or 'Face Editor')
            self._invalidate_optical_solid_face_assignment_trace(row_index, reason_text)
            self._clear_open3d_face_metadata_hover_state(row_index)
            schedule_face_editor_retrace()
            assigned_count = sum((1 for record in records if le._normalize_optical_solid_face_function(record.get('function'), legacy_role=record.get('role')) != le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT))
            self.append_debug(f'CAD/STL face editor saved S{row_index}: {reason_text}; {assigned_count} non-default face functions.')

        def apply_selected() -> None:
            if apply_current_form_to_selection():
                persist_face_editor_metadata('Apply Form to Selected')
                self.status_var.set(f'Saved CAD/STL optical face changes for S{row_index}.')

        def auto_apply_selected_face_identity(_event=None) -> None:
            if form_loading:
                return
            if apply_current_form_to_selection(quiet=True):
                index = selected_record_index()
                record = records[index] if index is not None and 0 <= index < len(records) else {}
                face_id = str(record.get('face_id', 'selected face') or 'selected face')
                function_display = le._optical_solid_face_function_display(record.get('function'), legacy_role=record.get('role'))
                persist_face_editor_metadata(f'{face_id} {function_display}')
                validation_var.set(f"Saved {face_id}: {le._normalize_optical_solid_face_side(record.get('side_2d'))} / {function_display}.")
                self.status_var.set(f'Saved CAD/STL optical face changes for S{row_index}.')

        def apply_current_form_to_selection_for_save() -> bool:
            return True if not selected_record_indices() else apply_current_form_to_selection(quiet=True)

        def auto_guess() -> None:
            nonlocal records
            records = le.auto_assign_optical_solid_face_roles(records)
            records = le.suggest_optical_solid_face_roles(records)
            candidate_mesh_cache.clear()
            refresh_tree('face_0')
            load_selected()
            validation_var.set('Auto guessed 2D side labels from face centroids. Review before saving.')

        def refresh_suggestions() -> None:
            nonlocal records
            records = le.suggest_optical_solid_face_roles(records)
            candidate_mesh_cache.clear()
            refresh_tree(tree.selection() or 'face_0')
            load_selected()
            suggested_count = sum((1 for record in records if le._optical_solid_face_suggestion_label(record)))
            validation_var.set(f'Updated {suggested_count} geometry suggestions. Suggestions use Uncoated physics; TIR remains a trace-time result.')

        def apply_suggestions_to_empty() -> None:
            nonlocal records
            records = le.apply_optical_solid_face_suggestions(records, overwrite=False)
            candidate_mesh_cache.clear()
            refresh_tree(tree.selection() or 'face_0')
            load_selected()
            validation_var.set('Applied suggestions only to empty side/function/port fields. Existing authored face assignments were preserved.')

        def clear_roles() -> None:
            for record in records:
                record['role'] = le.OPTICAL_SOLID_FACE_ROLE_DEFAULT
                record['function'] = le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
                record['side_2d'] = le.OPTICAL_SOLID_FACE_SIDE_DEFAULT
                record['port_role'] = le.OPTICAL_SOLID_FACE_PORT_DEFAULT
                record['input_offset_u_mm'] = 0.0
                record['input_offset_v_mm'] = 0.0
                record['flip_normal'] = False
                record['suggested_side_2d'] = le.OPTICAL_SOLID_FACE_SIDE_DEFAULT
                record['suggested_function'] = le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
                record['suggested_port_role'] = le.OPTICAL_SOLID_FACE_PORT_DEFAULT
                record['suggestion_confidence'] = 0.0
                record['suggestion_reason'] = ''
                record['suggestion_source'] = ''
                record['notes'] = ''
            refresh_tree('face_0')
            load_selected()
            validation_var.set('Cleared optical face roles in the dialog. Save to write this to the row.')

        def _set_virtual_status() -> None:
            if virtual_planes:
                plane = le.normalize_optical_solid_virtual_plane_record(virtual_planes[0])
                virtual_status_var.set('Saved virtual plane: {plane_id} | {diagonal} | aperture={aperture:.4g} mm | split={split:.4g}'.format(plane_id=plane.get('plane_id', 'VP001'), diagonal=le._normalize_optical_solid_virtual_plane_diagonal(plane.get('diagonal_mode')), aperture=float(plane.get('aperture_mm', 0.0) or 0.0), split=float(plane.get('split_ratio', 0.5) or 0.5)))
            else:
                virtual_status_var.set('No virtual internal plane saved.')

        def _virtual_plane_metadata_snapshot() -> dict[str, object]:
            return {'faces': records, 'virtual_planes': virtual_planes, 'source_stl': str(path)}

        def build_virtual_cube_plane() -> None:
            nonlocal virtual_planes
            split = le._float_or_default(virtual_split_var.get(), 0.5)
            loss = le._float_or_default(virtual_loss_var.get(), 0.0)
            phase = le._float_or_default(virtual_phase_var.get(), 0.0)
            aperture = le._float_or_default(virtual_aperture_var.get(), 0.0)
            if not 0.0 <= split <= 1.0:
                virtual_status_var.set('Virtual plane split ratio must be between 0 and 1.')
                return
            if not 0.0 <= loss <= 1.0:
                virtual_status_var.set('Virtual plane loss must be between 0 and 1.')
                return
            if aperture < 0.0:
                virtual_status_var.set('Virtual plane aperture must be non-negative.')
                return
            try:
                plane = le.build_optical_solid_cube_splitter_virtual_plane(_virtual_plane_metadata_snapshot(), diagonal_mode=virtual_diagonal_var.get(), split_ratio=split, loss=loss, phase_deg=phase, aperture_mm=aperture, notes=virtual_notes_var.get())
            except Exception as exc:
                virtual_status_var.set(f'Could not build cube splitter plane: {le._short_error_message(exc)}')
                return
            virtual_planes = [plane]
            virtual_diagonal_var.set(le._normalize_optical_solid_virtual_plane_diagonal(plane.get('diagonal_mode')))
            virtual_split_var.set(f"{float(plane.get('split_ratio', 0.5) or 0.5):.6g}")
            virtual_loss_var.set(f"{float(plane.get('loss', 0.0) or 0.0):.6g}")
            virtual_phase_var.set(f"{float(plane.get('phase_deg', 0.0) or 0.0):.6g}")
            virtual_aperture_var.set(f"{float(plane.get('aperture_mm', 0.0) or 0.0):.6g}")
            virtual_notes_var.set(str(plane.get('notes', '') or ''))
            _set_virtual_status()
            render_face_preview(selected_record_index())

        def clear_virtual_planes() -> None:
            nonlocal virtual_planes
            virtual_planes = []
            _set_virtual_status()
            render_face_preview(selected_record_index())

        def set_side_and_apply(side: str) -> None:
            side_var.set(le._normalize_optical_solid_face_side(side))
            apply_selected()

        def set_port_and_apply(port_role: str) -> None:
            port_var.set(le._normalize_optical_solid_face_port_role(port_role))
            apply_selected()

        def save_roles() -> bool:
            if not apply_current_form_to_selection_for_save():
                return False
            functions = [le._normalize_optical_solid_face_function(record.get('function'), legacy_role=record.get('role')) for record in records]
            sides = [le._normalize_optical_solid_face_side(record.get('side_2d')) for record in records]
            if any((function != le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT for function in functions)) and (not any((side != le.OPTICAL_SOLID_FACE_SIDE_DEFAULT for side in sides))) and (not messagebox.askyesno('Assign CAD/STL Optical Faces', 'No 2D side labels are assigned. Save function-only metadata anyway?', parent=window)):
                return False
            metadata_to_save = le.normalize_optical_solid_face_metadata({'faces': records, 'virtual_planes': virtual_planes, 'source_stl': str(path)}, source_stl=str(path))
            auto_orient_solution = None
            auto_orient_error = ''
            if bool(auto_orient_var.get()):
                try:
                    auto_orient_solution = self._solve_optical_solid_path_input_pose(row_index, metadata_to_save)
                    if auto_orient_solution is None:
                        auto_orient_solution = le.solve_optical_solid_left_input_pose(metadata_to_save)
                        if auto_orient_solution is not None:
                            auto_orient_solution['fit_source'] = 'row plane'
                except Exception as exc:
                    auto_orient_error = le._short_error_message(exc)
                    try:
                        auto_orient_solution = le.solve_optical_solid_left_input_pose(metadata_to_save)
                        if auto_orient_solution is not None:
                            auto_orient_solution['fit_source'] = 'row plane'
                    except Exception:
                        pass
            self._begin_history_capture()
            target = self.rows[row_index]
            target.advanced = dict(target.advanced or {})
            target.advanced[le.OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata_to_save
            if auto_orient_solution is not None:
                target.tilt_x, target.tilt_y, target.tilt_z = (float(value) for value in auto_orient_solution['tilts'])
                target.desp_x, target.desp_y, target.desp_z = (float(value) for value in auto_orient_solution['desp'])
            self._sync_table()
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self._invalidate_optical_solid_face_assignment_trace(row_index, 'Save Roles')
            self._clear_open3d_face_metadata_hover_state(row_index)
            # Explicit save: cancel any debounced auto-apply retrace and do the one
            # authoritative retrace now (so we never double-retrace on Save Roles).
            cancel_pending_face_editor_retrace()
            self._refresh_open_3d_views(force_retrace=True)
            summary = self._optical_solid_faces_summary(row_index, target)
            self.append_debug(summary)
            if auto_orient_solution is not None:
                label = str(auto_orient_solution.get('label', '') or auto_orient_solution.get('face_id', '') or 'Input Port')
                roll_side = str(auto_orient_solution.get('roll_side', '') or '').strip()
                roll_text = f' with {roll_side} roll' if roll_side else ''
                fit_source = str(auto_orient_solution.get('fit_source', '') or 'row plane').strip()
                if fit_source == 'row plane':
                    target_text = 'input -Z'
                    validation_target = 'outward normal -> -Z, incoming ray -> +Z'
                else:
                    target_text = fit_source
                    target_world = auto_orient_solution.get('target_world_point')
                    direction_world = auto_orient_solution.get('path_direction')
                    validation_target = f'outward normal -> -traced direction; target={target_world}, direction={direction_world}'
                pose_text = 'Tilt=({:.6g},{:.6g},{:.6g}), Desp=({:.6g},{:.6g},{:.6g})'.format(float(target.tilt_x), float(target.tilt_y), float(target.tilt_z), float(target.desp_x), float(target.desp_y), float(target.desp_z))
                self.append_debug(f'CAD/STL auto orientation S{row_index}: {label} -> {target_text}{roll_text}; {pose_text}')
                self.status_var.set(f'Saved face roles and oriented S{row_index} from {target_text}.')
                validation_var.set(f'Saved roles. Auto-oriented {label} as the input face: {validation_target}{roll_text}. {pose_text}')
            elif bool(auto_orient_var.get()):
                detail = f' ({auto_orient_error})' if auto_orient_error else ' (assign an Input Port face to enable this)'
                self.status_var.set(f'Saved CAD/STL optical face roles for S{row_index}; auto orientation skipped{detail}.')
                validation_var.set('Saved optical face roles and virtual planes. Auto orientation skipped because no valid Input Port face was available' + detail + '.')
            else:
                self.status_var.set(f'Saved CAD/STL optical face roles for S{row_index}.')
                validation_var.set('Saved optical face roles and virtual planes. Auto orientation is disabled for this save.')
            return True

        def open_placement_view() -> None:
            self._select_table_row(row_index)
            self.open_optical_stl_placement_assistant()

        def use_selected_face_as_source_target() -> None:
            index = selected_record_index()
            if index is None:
                validation_var.set('Select one CAD/STL face first.')
                return
            parsed = parse_form()
            if parsed is None:
                return
            record = records[index]
            record.update(parsed)
            refreshed = le.normalize_optical_solid_face_record(record)
            record.clear()
            record.update(refreshed)
            face_id = str(record.get('face_id', '') or '').strip()
            if not face_id:
                validation_var.set('Selected face has no face ID.')
                return
            refresh_tree(f'face_{index}')
            render_face_preview(index)
            if not save_roles():
                return
            validation_var.set(f'Saved {face_id}; opening Scene Source Manager with this face preselected.')
            self.open_scene_source_manager(aim_row_index=int(row_index), aim_face_id=face_id)

        def copy_summary() -> None:
            temp_row = le.SurfaceRow(**asdict(self.rows[row_index]))
            temp_row.advanced = dict(temp_row.advanced or {})
            temp_row.advanced[le.OPTICAL_SOLID_FACES_ADVANCED_ATTR] = le.normalize_optical_solid_face_metadata({'faces': records, 'virtual_planes': virtual_planes, 'source_stl': str(path)}, source_stl=str(path))
            text = self._optical_solid_faces_summary(row_index, temp_row)
            ok, backend = self._copy_text_to_clipboard(text + '\n')
            self.append_debug(text)
            self.status_var.set(f'CAD/STL optical face summary copied ({backend}).' if ok else 'CAD/STL optical face summary written to Debug; clipboard unavailable.')
        auto_orient_check = ttk.Checkbutton(editor, text='On Save: snap Input Port to traced ray', variable=auto_orient_var)
        auto_orient_check.grid(row=15, column=0, columnspan=2, sticky='w', pady=(0, 6))
        self._add_widget_tooltip(auto_orient_check, auto_orient_hint + ' Solves Tilt/Decenter so the Input Port face is centred on the current Path view or nearest traced 3D ray. Falls back to the row plane +Z input if no traced ray is available.')
        button_row = 16
        quick_sides = ttk.LabelFrame(editor, text='2D side')
        quick_sides.grid(row=button_row, column=0, columnspan=2, sticky='ew', pady=(4, 4))
        for label, side_name, tooltip in (('Left', 'Left', 'Left face in the YZ 2D plot, usually lower Z / earlier along the layout. Use Port role=Input to make it the entrance anchor.'), ('Right', 'Right', 'Right face in the YZ 2D plot, usually higher Z / later along the layout.'), ('Up', 'Up', 'Upper face in the YZ 2D plot, higher Y.'), ('Down', 'Down', 'Lower face in the YZ 2D plot, lower Y.')):
            button = ttk.Button(quick_sides, text=label, command=lambda side=side_name: set_side_and_apply(side))
            button.pack(side='left', padx=(0, 3), pady=2)
            self._add_widget_tooltip(button, tooltip)
        quick_ports = ttk.LabelFrame(editor, text='Port role')
        quick_ports.grid(row=button_row + 1, column=0, columnspan=2, sticky='ew', pady=(0, 4))
        for label, port_role_name, tooltip in (('Input', le.OPTICAL_SOLID_FACE_PORT_INPUT, 'Entrance/anchor port. Save Roles snaps this face to the incoming traced ray.'), ('Output', le.OPTICAL_SOLID_FACE_PORT_OUTPUT, 'Optional exit override. Leave this unset for normal traced physics; use it only when you want to force downstream placement to a specific exit face.'), ('Interact', le.OPTICAL_SOLID_FACE_PORT_INTERACTION, 'Non-port optical interaction face. Use this for reflective, splitter, absorbing, or uncoated fold faces that should change the path without becoming the entrance/exit port.'), ('Auto', le.OPTICAL_SOLID_FACE_PORT_DEFAULT, 'Infer the port role from coating/interaction and 2D side.')):
            button = ttk.Button(quick_ports, text=label, command=lambda port=port_role_name: set_port_and_apply(port))
            button.pack(side='left', padx=(0, 3))
            self._add_widget_tooltip(button, tooltip)
        self._add_widget_tooltip(side_menu, '2D prism side label relative to the YZ plot. Left/Right are along layout Z; Up/Down are along Y.')
        self._add_widget_tooltip(function_menu, 'Surface coating/interaction model for the selected CAD/STL face. Choose Uncoated for normal Snell-Fresnel refraction; TIR then occurs automatically when geometry and index demand it. Diffuse face scattering is not wired on imported CAD faces yet; use a Diffuse Object row for Lambertian/BRDF physics.')
        self._add_widget_tooltip(port_menu, 'Port role separates the entrance anchor from interaction faces. Use Input for the incoming beam. Leave Output unset for normal traced exit physics, and use Output only as an advanced downstream-placement override. Use Interaction for reflective, splitter, absorbing, or uncoated fold faces.')
        self._add_widget_tooltip(fit_reference_menu, 'Optional roll constraint used by Save Roles/Face Fit after the Input Port is aligned. Example: choose +Y normal on a face that should point upward; choose -Y normal for a Y-axis flip.')
        self._add_widget_tooltip(input_offset_frame, 'Anchor offset used only when this face acts as the Input Port. U prefers the face-plane +Z direction when available; V completes the in-plane orthogonal axis. Use this for off-center vendor entrance points without global decenter trial and error.')
        self._add_widget_tooltip(input_offset_u_entry, 'Input anchor offset along the face-plane U axis in millimetres.')
        self._add_widget_tooltip(input_offset_v_entry, 'Input anchor offset along the face-plane V axis in millimetres.')
        self._add_widget_tooltip(input_snap_pick_button, 'Arm click-to-pick mode in the 3D preview for the currently selected Input Port face and fill Input snap U/V from the chosen point.')
        self._add_widget_tooltip(clear_input_snap_button, 'Reset Input snap U/V to 0 mm for the selected face.')
        self._add_widget_tooltip(split_entry, 'Partial-reflecting face field. It is disabled unless Coating / interaction is Partial Reflecting / Transmitting.')
        self._add_widget_tooltip(loss_entry, 'Interaction loss for reflective, splitter, or absorbing face models.')
        self._add_widget_tooltip(phase_entry, 'Phase retardance for reflective or partial-reflecting face models.')
        ttk.Button(editor, text='Apply Form to Selected', command=apply_selected).grid(row=button_row + 2, column=0, columnspan=2, sticky='ew', pady=(0, 4))
        ttk.Button(editor, text='Auto Guess 2D Sides', command=auto_guess).grid(row=button_row + 3, column=0, columnspan=2, sticky='ew', pady=(0, 4))
        ttk.Button(editor, text='Suggest Optical Intent', command=refresh_suggestions).grid(row=button_row + 4, column=0, columnspan=2, sticky='ew', pady=(0, 4))
        ttk.Button(editor, text='Apply Suggestions to Empty', command=apply_suggestions_to_empty).grid(row=button_row + 5, column=0, columnspan=2, sticky='ew', pady=(0, 4))
        ttk.Button(editor, text='Clear Face Labels', command=clear_roles).grid(row=button_row + 6, column=0, columnspan=2, sticky='ew', pady=(0, 4))
        virtual_frame = ttk.LabelFrame(editor, text='Virtual Internal Plane')
        virtual_frame.grid(row=button_row + 7, column=0, columnspan=2, sticky='ew', pady=(4, 4))
        virtual_frame.columnconfigure(1, weight=1)
        ttk.Label(virtual_frame, text='Diagonal').grid(row=0, column=0, sticky='w', pady=(0, 2))
        ttk.Combobox(virtual_frame, textvariable=virtual_diagonal_var, values=le.OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_VALUES, state='readonly').grid(row=0, column=1, sticky='ew', pady=(0, 2))
        ttk.Label(virtual_frame, text='Split').grid(row=1, column=0, sticky='w', pady=(0, 2))
        ttk.Entry(virtual_frame, textvariable=virtual_split_var, width=12).grid(row=1, column=1, sticky='ew', pady=(0, 2))
        ttk.Label(virtual_frame, text='Loss').grid(row=2, column=0, sticky='w', pady=(0, 2))
        ttk.Entry(virtual_frame, textvariable=virtual_loss_var, width=12).grid(row=2, column=1, sticky='ew', pady=(0, 2))
        ttk.Label(virtual_frame, text='Phase [deg]').grid(row=3, column=0, sticky='w', pady=(0, 2))
        ttk.Entry(virtual_frame, textvariable=virtual_phase_var, width=12).grid(row=3, column=1, sticky='ew', pady=(0, 2))
        ttk.Label(virtual_frame, text='Aperture [mm]').grid(row=4, column=0, sticky='w', pady=(0, 2))
        ttk.Entry(virtual_frame, textvariable=virtual_aperture_var, width=12).grid(row=4, column=1, sticky='ew', pady=(0, 2))
        ttk.Label(virtual_frame, text='Notes').grid(row=5, column=0, sticky='w', pady=(0, 2))
        ttk.Entry(virtual_frame, textvariable=virtual_notes_var, width=18).grid(row=5, column=1, sticky='ew', pady=(0, 2))
        ttk.Label(virtual_frame, text='Build a virtual internal diagonal for cube-style beam-splitter CAD. This is saved with the row and previewed in 3D, but traced branch physics still uses a Beam Splitter row or cube primitive today.', foreground='#64748b', wraplength=330, justify='left').grid(row=6, column=0, columnspan=2, sticky='ew', pady=(2, 4))
        ttk.Label(virtual_frame, textvariable=virtual_status_var, foreground='#475569', wraplength=330).grid(row=7, column=0, columnspan=2, sticky='ew', pady=(0, 4))
        ttk.Button(virtual_frame, text='Auto Cube Splitter Plane', command=build_virtual_cube_plane).grid(row=8, column=0, columnspan=2, sticky='ew', pady=(0, 2))
        ttk.Button(virtual_frame, text='Clear Virtual Planes', command=clear_virtual_planes).grid(row=9, column=0, columnspan=2, sticky='ew')
        # The full assignment form is built; bind wheel/touchpad scroll recursively
        # on every control now that they all exist, and size the scrollregion.
        _bind_editor_wheel(editor)
        editor.update_idletasks()
        _update_editor_scroll()
        footer = ttk.Frame(window, padding=(10, 4, 10, 10))
        footer.grid(row=2, column=0, sticky='ew')
        ttk.Button(footer, text='Open 3D Placement', command=open_placement_view).pack(side='left')
        ttk.Button(footer, text='Native Surface Props', command=lambda: self.open_advanced_surface_editor(row_index)).pack(side='left', padx=(8, 0))
        ttk.Button(footer, text='Use Face As Source Target', command=use_selected_face_as_source_target).pack(side='left', padx=(8, 0))
        ttk.Button(footer, text='Save Roles', command=save_roles).pack(side='right')
        ttk.Button(footer, text='Copy Summary', command=copy_summary).pack(side='right', padx=(0, 8))
        ttk.Button(footer, text='Close', command=window.destroy).pack(side='right', padx=(0, 8))
        def select_face_group_for_iid(iid: str) -> None:
            try:
                idx = int(str(iid).split('_', 1)[1])
            except Exception:
                return
            gid = group_index_by_record_index.get(idx, -1)
            if gid < 0:
                return
            existing = set(tree.get_children(''))
            members = [
                f'face_{j}' for j, g in group_index_by_record_index.items()
                if g == gid and f'face_{j}' in existing
            ]
            if not members:
                return
            tree.selection_set(members)
            tree.focus(members[0])
            tree.see(members[0])
            try:
                preview_status_var.set(
                    f"Selected {len(members)} face(s) in group G{gid + 1}. Set a 2D side / "
                    "function / port on the right, then it applies to the whole surface."
                )
            except Exception:
                pass

        def show_face_group_menu(event) -> None:
            if not show_face_groups:
                return
            iid = tree.identify_row(event.y)
            if not iid:
                return
            try:
                idx = int(str(iid).split('_', 1)[1])
            except Exception:
                return
            gid = group_index_by_record_index.get(idx, -1)
            if gid < 0:
                return
            count = group_member_counts.get(gid, 0)
            menu = tk.Menu(window, tearoff=0)
            menu.add_command(
                label=f"Select all {count} faces in group G{gid + 1}",
                command=lambda chosen=iid: select_face_group_for_iid(chosen),
            )
            try:
                menu.tk_popup(int(event.x_root), int(event.y_root))
            finally:
                menu.grab_release()

        tree.bind('<<TreeviewSelect>>', load_selected, add='+')
        tree.bind('<ButtonRelease-1>', schedule_tree_rewrap, add='+')
        tree.bind('<Configure>', schedule_tree_rewrap, add='+')
        tree.bind('<Double-Button-1>', on_tree_column_double_click, add='+')
        if show_face_groups:
            tree.bind('<Button-3>', show_face_group_menu, add='+')
        side_menu.bind('<<ComboboxSelected>>', auto_apply_selected_face_identity, add='+')
        function_menu.bind('<<ComboboxSelected>>', auto_apply_selected_face_identity, add='+')
        port_menu.bind('<<ComboboxSelected>>', auto_apply_selected_face_identity, add='+')
        fit_reference_menu.bind('<<ComboboxSelected>>', auto_apply_selected_face_identity, add='+')
        for entry_widget in (input_offset_u_entry, input_offset_v_entry, split_entry, loss_entry, phase_entry, aperture_entry, material_entry, coating_entry, notes_entry):
            entry_widget.bind('<FocusOut>', auto_apply_selected_face_identity, add='+')
            entry_widget.bind('<Return>', auto_apply_selected_face_identity, add='+')
        flip_check.configure(command=auto_apply_selected_face_identity)
        function_var.trace_add('write', update_face_property_field_states)
        _set_virtual_status()
        refresh_tree('face_0')
        load_selected()
        window.after(80, lambda: render_face_preview(selected_record_index(), reset_camera=True))
        self._show_centered_dialog(window)
