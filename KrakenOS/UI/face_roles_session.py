"""The CAD/STL optical face-roles editor as a model (docs/design_qt_migration.md phase 5g, bugs/0933).

The editor used to be one 1 900-line Tk method whose state lived in closures and Tk variables.
Everything that is not layout is here now, toolkit-neutral: the face records and their groups,
the selection, the assignment form (as plain values), the messages the dialog shows, and every
action (apply, auto-apply, save, suggestions, virtual planes, input-snap picking, source
binding). The Tk dialog (`panels/main_optical_solid_face_roles_dialog.py`) and the Qt one
(`qt/dialogs/face_roles_dialog.py`) are views: they write the form into ``form`` before an action
and redraw from the session when it notifies. The 3D preview is `face_roles_preview.py`.
"""
from __future__ import annotations

import ast
from dataclasses import asdict
from pathlib import Path
from pprint import pformat
from typing import Any, Callable

import numpy as np

# the tree's columns (Group only when grouping consolidates), headings and starting widths
TREE_COLUMNS = ('face', 'group', 'side', 'function', 'port', 'suggestion', 'fit_ref', 'area',
                'triangles', 'normal', 'centroid', 'split', 'flip')
TREE_HEADINGS = {'face': 'Face', 'group': 'Group', 'side': '2D Side', 'function': 'Function',
                 'port': 'Port Role', 'suggestion': 'Suggested', 'fit_ref': 'Fit Ref',
                 'area': 'Area [mm2]', 'triangles': 'Triangles', 'normal': 'Normal',
                 'centroid': 'Centroid', 'split': 'Split', 'flip': 'Flip'}
TREE_WIDTHS = {'face': 62, 'group': 56, 'side': 76, 'function': 130, 'port': 126, 'suggestion': 168,
               'fit_ref': 92, 'area': 90, 'triangles': 76, 'normal': 180, 'centroid': 190,
               'split': 68, 'flip': 48}
NUMERIC_COLUMNS = {'area', 'triangles', 'split', 'flip'}

# the form's text fields, in order: (key, label) -- the choices are FORM_CHOICES
FORM_TEXT_FIELDS = (('split', 'Split ratio'), ('loss', 'Loss'), ('phase', 'Phase [deg]'),
                    ('aperture', 'Clear aperture [mm]'), ('material', 'Material override'))
VIRTUAL_TEXT_FIELDS = (('split', 'Split'), ('loss', 'Loss'), ('phase', 'Phase [deg]'),
                       ('aperture', 'Aperture [mm]'), ('notes', 'Notes'))

PREVIEW_HINT = ('Click a face in 3D to select it; left-drag rotates the view with the same fixed-speed '
                'behavior as Open 3D. Then assign the 2D side and optical function on the right.')
PHYSICS_HINT = ('Uncoated uses normal glass/air Snell-Fresnel physics; total internal reflection happens '
                'automatically when the incidence exceeds the critical angle. Fit ref normal fixes prism roll '
                'after the Input Port face is aligned. Input snap U/V shifts the anchor point within the '
                'selected Input Port face before Save Roles solves pose.')
VIRTUAL_HINT = ('Build a virtual internal diagonal for cube-style beam-splitter CAD. This is saved with the '
                'row and previewed in 3D, but traced branch physics still uses a Beam Splitter row or cube '
                'primitive today.')
AUTO_ORIENT_LABEL = 'On Save: snap Input Port to traced ray'
COATING_TABLE_HINT = 'Coating = [R, A, W, THETA]. R/A rows follow THETA; columns follow wavelength.'

TOOLTIPS = {
    'side': '2D prism side label relative to the YZ plot. Left/Right are along layout Z; Up/Down are along Y.',
    'function': ('Surface coating/interaction model for the selected CAD/STL face. Choose Uncoated for normal '
                 'Snell-Fresnel refraction; TIR then occurs automatically when geometry and index demand it. '
                 'Diffuse / Scatter Object marks the face as a diffuse scatterer (default Lambertian) so the '
                 'non-sequential trace spawns scatter rays off it, like a Diffuse Object surface (bugs/0271).'),
    'port': ('Port role separates the entrance anchor from interaction faces. Use Input for the incoming beam. '
             'Leave Output unset for normal traced exit physics, and use Output only as an advanced '
             'downstream-placement override. Use Interaction for reflective, splitter, absorbing, or uncoated '
             'fold faces.'),
    'fit_reference': ('Optional roll constraint used by Save Roles/Face Fit after the Input Port is aligned. '
                      'Example: choose +Y normal on a face that should point upward; choose -Y normal for a '
                      'Y-axis flip.'),
    'input_offset': ('Anchor offset used only when this face acts as the Input Port. U prefers the face-plane +Z '
                     'direction when available; V completes the in-plane orthogonal axis. Use this for '
                     'off-center vendor entrance points without global decenter trial and error.'),
    'input_offset_u': 'Input anchor offset along the face-plane U axis in millimetres.',
    'input_offset_v': 'Input anchor offset along the face-plane V axis in millimetres.',
    'pick': ('Arm click-to-pick mode in the 3D preview for the currently selected Input Port face and fill '
             'Input snap U/V from the chosen point.'),
    'zero': 'Reset Input snap U/V to 0 mm for the selected face.',
    'split': ('Partial-reflecting face field. It is disabled unless Coating / interaction is Partial Reflecting '
              '/ Transmitting.'),
    'loss': 'Interaction loss for reflective, splitter, or absorbing face models.',
    'phase': 'Phase retardance for reflective or partial-reflecting face models.',
}


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


def quick_sides() -> tuple:
    """The 2D-side quick buttons: (label, side, tooltip)."""
    return (('Left', 'Left', 'Left face in the YZ 2D plot, usually lower Z / earlier along the layout. Use Port '
                             'role=Input to make it the entrance anchor.'),
            ('Right', 'Right', 'Right face in the YZ 2D plot, usually higher Z / later along the layout.'),
            ('Up', 'Up', 'Upper face in the YZ 2D plot, higher Y.'),
            ('Down', 'Down', 'Lower face in the YZ 2D plot, lower Y.'))


def quick_ports() -> tuple:
    """The port-role quick buttons: (label, port role, tooltip)."""
    le = _layout_module()
    return (('Input', le.OPTICAL_SOLID_FACE_PORT_INPUT,
             'Entrance/anchor port. Save Roles snaps this face to the incoming traced ray.'),
            ('Output', le.OPTICAL_SOLID_FACE_PORT_OUTPUT,
             'Optional exit override. Leave this unset for normal traced physics; use it only when you want '
             'to force downstream placement to a specific exit face.'),
            ('Interact', le.OPTICAL_SOLID_FACE_PORT_INTERACTION,
             'Non-port optical interaction face. Use this for reflective, splitter, absorbing, or uncoated '
             'fold faces that should change the path without becoming the entrance/exit port.'),
            ('Auto', le.OPTICAL_SOLID_FACE_PORT_DEFAULT, 'Infer the port role from coating/interaction and 2D side.'))


def form_choices() -> dict:
    """The form's drop-down fields: key -> (label, values)."""
    le = _layout_module()
    return {'side': ('2D side', tuple(le.OPTICAL_SOLID_FACE_SIDE_VALUES)),
            'function': ('Coating / interaction', tuple(le.OPTICAL_SOLID_FACE_FUNCTION_VALUES)),
            'port': ('Port role', tuple(le.OPTICAL_SOLID_FACE_PORT_VALUES)),
            'fit_reference': ('Fit ref normal', tuple(le.OPTICAL_SOLID_FACE_FIT_REFERENCE_VALUES))}


def coating_choices() -> tuple:
    return ('Custom',) + tuple(_layout_module().COATING_PRESET_NAMES)


def format_vector(values) -> str:
    arr = np.asarray(values, dtype=float).reshape(-1)
    if arr.size < 3:
        arr = np.pad(arr, (0, 3 - arr.size), mode='constant')
    return '({:.4g}, {:.4g}, {:.4g})'.format(float(arr[0]), float(arr[1]), float(arr[2]))


def format_coating_table(table) -> str:
    return pformat(list(table) if table else [[], [], [], []], width=100)


def coating_presets() -> dict:
    return dict(getattr(_layout_module(), 'COATING_PRESETS', {}) or {})


def parse_face_coating_table(table_text: str, met_text: str) -> tuple:
    """The per-face coating-table editor's Apply: ``(table, met, None)`` or ``(None, None, error)``.

    A focused editor for a promoted-solid FACE's own ``[R, A, W, THETA]`` table (the same shape +
    ``COATING_PRESETS`` library as the 2D "Coating..." editor), decoupled from any surface row, so
    the non-sequential trace applies it through ``CoatingFun``."""
    from KrakenOS.UI.optical_solid_metadata import normalize_optical_solid_face_coating_table
    from KrakenOS.UI.services.advanced_surface_validation import _validate_coating_met, _validate_coating_table

    try:
        table = ast.literal_eval(str(table_text).strip() or '[[], [], [], []]')
    except Exception as exc:
        return None, None, f'Could not parse the coating table:\n\n{exc}'
    try:
        met = int(float(str(met_text).strip() or '0'))
    except Exception:
        return None, None, 'CoatingMet must be an integer metal index.'
    errors = list(_validate_coating_table(table)) + list(_validate_coating_met(met))
    if errors:
        return None, None, 'Invalid coating:\n\n' + '\n'.join(errors)
    normalized = normalize_optical_solid_face_coating_table(table)
    if not normalized:
        return None, None, ('An empty / clear table is not a custom coating. Pick a named preset instead, or '
                            'leave the coating blank for no per-face coating.')
    return normalized, met, None


class FaceRolesUnavailable(Exception):
    """The row has no face candidates to edit; ``severity`` is 'error' or 'info'."""

    def __init__(self, message: str, severity: str = 'error') -> None:
        super().__init__(message)
        self.severity = severity


class FaceRolesSession:
    """One face-roles editing session for one CAD/STL row. Views call the actions and redraw on
    ``notify``; ``form`` and ``virtual_form`` hold the fields as text (``flip`` / ``auto_orient``
    as bools), exactly what the widgets show."""

    TITLE = 'Assign CAD/STL Optical Faces'

    def __init__(self, editor: Any, row_index: int, row: Any, path: Path) -> None:
        le = self.le = _layout_module()
        self.editor = editor
        self.row_index = int(row_index)
        self.row = row
        self.path = path
        saved_metadata = (row.advanced or {}).get(le.OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        # Native OCC B-Rep faces (each a real optical surface, tagged with a surface_type and
        # triangle indices into the displayed STL) are listed verbatim -- no STL plane-clustering,
        # which would re-shatter a curved face into ~160 planar candidates. The flat-STL path is
        # unchanged.
        self.brep_backed = le.optical_solid_metadata_is_brep(saved_metadata)
        self.candidates: list = []
        if self.brep_backed:
            metadata = le.normalize_optical_solid_face_metadata(saved_metadata, source_stl=str(path))
        else:
            try:
                self.candidates = le.cluster_optical_solid_planar_faces(path)
            except Exception as exc:
                raise FaceRolesUnavailable(f'Could not read STL face candidates:\n\n{exc}') from exc
            if not self.candidates:
                raise FaceRolesUnavailable('No planar STL face candidates were found.', 'info')
            metadata = le.normalize_optical_solid_face_metadata(saved_metadata, self.candidates, source_stl=str(path))
        records = [le.normalize_optical_solid_face_record(face) for face in list(metadata.get('faces', []) or [])]
        self.records: list[dict] = le.suggest_optical_solid_face_roles(records)
        self.virtual_planes: list[dict] = [le.normalize_optical_solid_virtual_plane_record(plane)
                                           for plane in list(metadata.get('virtual_planes', []) or [])
                                           if isinstance(plane, dict)]
        self._group_faces()
        self.z_station = editor._stl_row_z_station(self.row_index)
        self.mesh_span = 1.0
        self.selection: list[int] = []
        self.focus: int | None = None
        self.input_snap_pick_active = False
        self.listeners: list[Callable[[], None]] = []
        self._retrace_handle = None
        self.form: dict[str, object] = {
            'side': le.OPTICAL_SOLID_FACE_SIDE_DEFAULT, 'function': le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
            'port': le.OPTICAL_SOLID_FACE_PORT_DEFAULT, 'fit_reference': le.OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT,
            'input_offset_u': '0', 'input_offset_v': '0', 'split': '0.5', 'loss': '0', 'phase': '0',
            'aperture': '0', 'material': str(row.glass or ''), 'coating': '', 'flip': False, 'notes': '',
            'auto_orient': not self._open3d_promoted_step_row(),
        }
        # Per-face CUSTOM coating table (the advanced "Edit table..." editor). When set it wins over
        # the preset NAME in form['coating']; picking a preset from the dropdown clears it.
        self.coating_state: dict[str, object] = {'table': None, 'met': 0}
        plane = self.virtual_planes[0] if self.virtual_planes else {}
        self.virtual_form: dict[str, object] = {}
        self._load_virtual_form(plane)
        self.mesh_cache_generation = 0  # the preview drops its per-face meshes when this moves
        self.validation = 'Select a face candidate, assign a 2D side/function, then Apply.'
        self._preview_status = '3D face preview loading...'
        self._preview_status_pinned = False
        self.virtual_status = ''
        self._set_virtual_status()

    # ---- the preview's status line ------------------------------------------------------------------
    @property
    def preview_status(self) -> str:
        return self._preview_status

    @preview_status.setter
    def preview_status(self, text: str) -> None:
        # an action's message outlives the re-render its notify causes (a render would otherwise
        # overwrite "Input snap stored ..." with the plain candidate count straight away)
        self._preview_status = str(text)
        self._preview_status_pinned = True

    def render_status(self, text: str) -> None:
        """A preview render's own status line -- unless an action's message is still pending."""
        if self._preview_status_pinned:
            self._preview_status_pinned = False
            return
        self._preview_status = str(text)

    # ---- listeners -----------------------------------------------------------------------------
    def notify(self) -> None:
        for listener in list(self.listeners):
            listener()

    # ---- groups ----------------------------------------------------------------------------------
    def _group_faces(self) -> None:
        """Display-only grouping: a curved (aspheric/spherical) lens face is fragmented by the
        planar clusterer into many candidates (e.g. 160). Group them by mesh connectivity + normal
        continuity so the editor can show a few logical surfaces and "Select all in group" can
        role-assign a whole curved face at once. The candidates themselves (and their planar
        fits/snapping) are unchanged."""
        le = self.le
        if self.brep_backed:
            # Most native B-Rep faces are already one whole optical surface, but the importer
            # splits a lens *rim* into several co-axial cylinder faces -- group those so the rim
            # reads as one edge and "Select all in group" can role-assign it at once (bugs/0013).
            try:
                group_ids = le.group_brep_optical_solid_faces(self.records)
            except Exception:
                group_ids = [-1] * len(self.records)
        else:
            try:
                group_ids = le.group_optical_solid_face_candidates(self.path, self.records, angle_deg=35.0)
            except Exception:
                group_ids = [-1] * len(self.records)
        self.group_index_by_record_index: dict[int, int] = {i: int(g) for i, g in enumerate(group_ids)}
        self.group_member_counts: dict[int, int] = {}
        for gid in group_ids:
            if int(gid) >= 0:
                self.group_member_counts[int(gid)] = self.group_member_counts.get(int(gid), 0) + 1
        # Only surface the Group column when grouping actually consolidates (more candidates than
        # groups); for a few flat faces it is just noise.
        self.distinct_groups = len(self.group_member_counts)
        self.show_face_groups = bool(self.distinct_groups) and len(self.records) > self.distinct_groups + 1
        self.group_label_by_face_id: dict[str, str] = {
            str(self.records[i].get('face_id', '') or ''): self._group_label(i) for i in range(len(self.records))}

    def _group_label(self, index: int) -> str:
        gid = self.group_index_by_record_index.get(int(index), -1)
        return f'G{gid + 1}' if gid >= 0 else ''

    def group_menu_label(self, index: int) -> str | None:
        """The row's right-click entry, or None when the row belongs to no group."""
        if not self.show_face_groups:
            return None
        gid = self.group_index_by_record_index.get(int(index), -1)
        if gid < 0:
            return None
        return f'Select all {self.group_member_counts.get(gid, 0)} faces in group G{gid + 1}'

    def select_group(self, index: int) -> None:
        gid = self.group_index_by_record_index.get(int(index), -1)
        if gid < 0:
            return
        members = [j for j, g in self.group_index_by_record_index.items() if g == gid and 0 <= j < len(self.records)]
        if not members:
            return
        self.selection = sorted(members)
        self.focus = members[0]
        self.preview_status = (f'Selected {len(members)} face(s) in group G{gid + 1}. Set a 2D side / '
                               'function / port on the right, then it applies to the whole surface.')
        self.notify()

    # ---- what the dialog shows -------------------------------------------------------------------
    def title(self) -> str:
        return f'CAD/STL Optical Faces - S{self.row_index}'

    def columns(self) -> tuple:
        return tuple(c for c in TREE_COLUMNS if c != 'group' or self.show_face_groups)

    def header_text(self) -> str:
        group_hint = (f' | {self.distinct_groups} surface group(s) -- right-click a row to "Select all in group" '
                      '(a curved lens face is split into many planar candidates).' if self.show_face_groups else '')
        return (f'S{self.row_index}: {self.row.name or self.row.surface} | {Path(self.path).name} | '
                f'{len(self.records)} planar face candidate(s), {len(self.virtual_planes)} virtual plane(s).'
                f'{group_hint} Assign optical intent; tracing still follows the STL solid.')

    def auto_orient_hint(self) -> str:
        if self._open3d_promoted_step_row():
            hint = 'This row was placed in Open 3D; Save Roles preserves its current pose unless this box is enabled.'
        else:
            hint = 'When enabled, Save Roles solves the row pose from the Input Port face.'
        return (hint + ' Solves Tilt/Decenter so the Input Port face is centred on the current Path view or nearest '
                'traced 3D ray. Falls back to the row plane +Z input if no traced ray is available.')

    def _open3d_promoted_step_row(self) -> bool:
        advanced = self.row.advanced if isinstance(self.row.advanced, dict) else {}
        placement = advanced.get(self.le.SCENE_PLACEMENT_ADVANCED_ATTR, {})
        return (isinstance(advanced.get('StepOverlayPromotion'), dict)
                or (isinstance(placement, dict)
                    and str(placement.get('promotion_source', '') or '').strip() == 'open3d_step_overlay'))

    def _illumination_label(self, face_id: str) -> str | None:
        """bugs/0268 + 0269: a face bound as an illumination source reads "Illumination Source"
        (+ aim) -- its underlying coating (often "Unassigned") would otherwise mask the role."""
        aim = self.editor.face_bound_illumination_aim(self.row_index, face_id) if face_id else None
        if aim is None:
            return None
        metadata = self.le.optical_solid_metadata
        return (metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ILLUMINATION_OUTWARD if aim == 'outward'
                else metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ILLUMINATION)

    def tree_values(self, record: dict) -> dict[str, str]:
        le = self.le
        function = le._normalize_optical_solid_face_function(record.get('function'), legacy_role=record.get('role'))
        function_display = le._optical_solid_face_function_display(function, legacy_role=record.get('role'))
        face_id = str(record.get('face_id', '') or '')
        function_display = self._illumination_label(face_id.strip()) or function_display
        fit = le._normalize_optical_solid_face_fit_reference(record.get('fit_reference'))
        return {'face': face_id, 'group': self.group_label_by_face_id.get(face_id, ''),
                'side': le._normalize_optical_solid_face_side(record.get('side_2d')), 'function': function_display,
                'port': le._optical_solid_face_authored_port_role(record),
                'suggestion': le._optical_solid_face_suggestion_label(record),
                'fit_ref': '' if fit == le.OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT else fit,
                'area': f"{float(record.get('area_mm2', 0.0) or 0.0):.6g}",
                'triangles': str(int(record.get('triangle_count', 0) or 0)),
                'normal': format_vector(record.get('normal', [0, 0, 1])),
                'centroid': format_vector(record.get('centroid', [0, 0, 0])),
                'split': f"{float(record.get('split_ratio', 0.5) or 0.0):.4g}" if function == 'Beam Splitter' else '',
                'flip': 'yes' if bool(record.get('flip_normal', False)) else ''}

    def rows(self) -> list[dict[str, str]]:
        """Every face's tree cells, in record order (row ``i`` is ``face_{i}``)."""
        return [self.tree_values(record) for record in self.records]

    def field_states(self) -> dict[str, bool]:
        """Which of split / loss / phase the chosen interaction uses."""
        function = self.le._optical_solid_face_function_from_ui_value(self.form['function'])
        return {'split': function == 'Beam Splitter', 'phase': function in {'Beam Splitter', 'Mirror'},
                'loss': function in {'Beam Splitter', 'Mirror', 'Absorber/Mechanical'}}

    # ---- selection ------------------------------------------------------------------------------
    def selected_index(self) -> int | None:
        """The focused face when it is selected, else the first selected one."""
        if not self.selection:
            return None
        if self.focus in self.selection:
            return self.focus
        return self.selection[0]

    def select(self, indices, focus: int | None = None, *, source: str = '') -> None:
        """A view's selection changed (a click, a pick): load the form from the focused face."""
        valid = sorted({int(i) for i in indices if 0 <= int(i) < len(self.records)})
        self.selection = valid
        self.focus = focus if focus in valid else (valid[0] if valid else None)
        self.load_form()
        if source and self.selected_index() is not None:
            record = self.records[self.selected_index()]
            self.validation = (f"{source}: selected {record.get('face_id')}. Choose 2D side, coating/interaction, "
                               'and port role, then Apply.')
        self.notify()

    def load_form(self) -> None:
        le = self.le
        index = self.selected_index()
        if index is None:
            return
        record = self.records[index]
        if not isinstance(record, dict):
            return
        function = le._optical_solid_face_function_display(record.get('function'), legacy_role=record.get('role'))
        self.form.update({
            'side': le._normalize_optical_solid_face_side(record.get('side_2d')),
            'function': self._illumination_label(str(record.get('face_id', '') or '').strip()) or function,
            'port': le._normalize_optical_solid_face_port_role(record.get('port_role')),
            'fit_reference': le._normalize_optical_solid_face_fit_reference(record.get('fit_reference')),
            'input_offset_u': f"{float(record.get('input_offset_u_mm', 0.0) or 0.0):.6g}",
            'input_offset_v': f"{float(record.get('input_offset_v_mm', 0.0) or 0.0):.6g}",
            'split': f"{float(record.get('split_ratio', 0.5) or 0.0):.6g}",
            'loss': f"{float(record.get('loss', 0.0) or 0.0):.6g}",
            'phase': f"{float(record.get('phase_deg', 0.0) or 0.0):.6g}",
            'aperture': f"{float(record.get('clear_aperture_mm', 0.0) or 0.0):.6g}",
            'material': str(record.get('material', '') or ''),
            'coating': str(record.get('coating', '') or ''),
            'flip': bool(record.get('flip_normal', False)),
            'notes': str(record.get('notes', '') or ''),
        })
        self.coating_state['table'] = record.get('coating_table') or None
        try:
            self.coating_state['met'] = int(record.get('coating_met', 0) or 0)
        except Exception:
            self.coating_state['met'] = 0
        authored_port = le._optical_solid_face_authored_port_role(record)
        effective_port = le._optical_solid_face_port_role(record)
        port_text = authored_port if authored_port == effective_port else f'{authored_port} -> effective {effective_port}'
        suggestion = le._optical_solid_face_suggestion_label(record)
        count = len(self.selection)
        self.validation = (f"{record.get('face_id')}: {self.form['side']} / {self.form['function']} / {port_text} | "
                           f"normal {format_vector(record.get('normal'))}, centroid {format_vector(record.get('centroid'))}"
                           f", snap_uv=({self.form['input_offset_u']},{self.form['input_offset_v']})"
                           + (f' | suggested {suggestion}' if suggestion else '')
                           + (f' | {count} faces selected' if count > 1 else ''))

    # ---- the form ---------------------------------------------------------------------------------
    def parse_form(self) -> dict | None:
        le, form = self.le, self.form
        function_value = str(form['function']).strip()
        valid_functions = set(le.OPTICAL_SOLID_FACE_FUNCTION_VALUES) | set(le.optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_VALUES)
        if function_value not in valid_functions:
            self.validation = 'Invalid surface coating / interaction.'
            return None
        if str(form['port']).strip() not in le.OPTICAL_SOLID_FACE_PORT_VALUES:
            self.validation = 'Invalid port role.'
            return None
        if str(form['fit_reference']).strip() not in le.OPTICAL_SOLID_FACE_FIT_REFERENCE_VALUES:
            self.validation = 'Invalid fit reference normal.'
            return None
        number = le._float_or_default
        split, loss = number(form['split'], 0.5), number(form['loss'], 0.0)
        aperture = number(form['aperture'], 0.0)
        if not 0.0 <= split <= 1.0:
            self.validation = 'Split ratio must be between 0 and 1.'
            return None
        if not 0.0 <= loss <= 1.0:
            self.validation = 'Loss must be between 0 and 1.'
            return None
        if aperture < 0.0:
            self.validation = 'Clear aperture cannot be negative.'
            return None
        function = le._optical_solid_face_function_from_ui_value(function_value)
        return {'role': le._legacy_role_from_optical_solid_face_function(function), 'function': function,
                'side_2d': le._normalize_optical_solid_face_side(form['side']),
                'port_role': le._normalize_optical_solid_face_port_role(form['port']),
                'fit_reference': le._normalize_optical_solid_face_fit_reference(form['fit_reference']),
                'split_ratio': split, 'loss': loss, 'phase_deg': number(form['phase'], 0.0),
                'clear_aperture_mm': aperture, 'input_offset_u_mm': number(form['input_offset_u'], 0.0),
                'input_offset_v_mm': number(form['input_offset_v'], 0.0),
                'material': str(form['material']).strip(), 'coating': str(form['coating']).strip(),
                'coating_table': (self.coating_state.get('table') or []),
                'coating_met': int(self.coating_state.get('met', 0) or 0),
                'flip_normal': bool(form['flip']), 'notes': str(form['notes']).strip()}

    def _update_record(self, index: int, parsed: dict) -> None:
        record = self.records[index]
        record.update(parsed)
        refreshed = self.le.normalize_optical_solid_face_record(record)
        record.clear()
        record.update(refreshed)

    def apply_form_to_selection(self, *, quiet: bool = False) -> bool:
        le = self.le
        if not self.selection:
            if not quiet:
                self.validation = 'Select a face candidate first.'
            return False
        parsed = self.parse_form()
        if parsed is None:
            return False
        for index in self.selection:
            self._update_record(index, parsed)
        if quiet:
            return True
        if len(self.selection) == 1:
            record = self.records[self.selection[0]]
            self.validation = (f"Applied {le._normalize_optical_solid_face_side(record.get('side_2d'))} / "
                               f"{le._optical_solid_face_function_display(record.get('function'), legacy_role=record.get('role'))} "
                               f"to {record['face_id']}.")
        else:
            self.validation = (f"Applied {parsed['side_2d']} / {le._optical_solid_face_function_display(parsed['function'])} "
                               f'to {len(self.selection)} selected faces.')
        return True

    def choose_coating(self, name: str) -> None:
        """Choosing a NAMED preset drops any custom table (the name resolves at build instead)."""
        self.form['coating'] = name
        if str(name).strip() != 'Custom':
            self.coating_state['table'] = None
            self.coating_state['met'] = 0

    def set_coating_table(self, table, met) -> None:
        self.coating_state['table'] = table
        self.coating_state['met'] = int(met)
        self.form['coating'] = 'Custom'
        self.notify()

    # ---- persisting ---------------------------------------------------------------------------------
    def metadata(self) -> dict:
        return self.le.normalize_optical_solid_face_metadata(
            {'faces': self.records, 'virtual_planes': self.virtual_planes, 'source_stl': str(self.path)},
            source_stl=str(self.path))

    def cancel_pending_retrace(self) -> None:
        from KrakenOS.UI.uihost import host_of

        if self._retrace_handle is not None:
            try:
                host_of(self.editor).after_cancel(self._retrace_handle)
            except Exception:
                pass
            self._retrace_handle = None

    def schedule_retrace(self) -> None:
        """auto-apply (bound to every side/function/port/fit field) persisted the metadata AND ran
        a full Open 3D retrace on every change, so a few field tweaks fired several full system
        retraces -- the slow Face Editor the user reported. Persisting stays synchronous (no lost
        edits); the expensive retrace is debounced + coalesced -- on the HOST's timer, which the Qt
        shell pumps too (a Tk timer never fires there)."""
        from KrakenOS.UI.uihost import host_of

        self.cancel_pending_retrace()

        def run() -> None:
            self._retrace_handle = None
            try:
                self.editor._refresh_open_3d_views(force_retrace=True)
            except Exception as exc:
                self.editor.append_debug(f'Face Editor debounced retrace failed: {exc}')

        self._retrace_handle = host_of(self.editor).after(250, run)

    def persist(self, reason: str = 'Face Editor') -> None:
        le, editor = self.le, self.editor
        editor._begin_history_capture()
        target = editor.rows[self.row_index]
        target.advanced = dict(target.advanced or {})
        target.advanced[le.OPTICAL_SOLID_FACES_ADVANCED_ATTR] = self.metadata()
        editor._sync_table()
        editor._commit_history_capture()
        editor._mark_plot_update_pending()
        reason_text = str(reason or 'Face Editor')
        editor._invalidate_optical_solid_face_assignment_trace(self.row_index, reason_text)
        editor._clear_open3d_face_metadata_hover_state(self.row_index)
        self.schedule_retrace()
        assigned = sum(1 for record in self.records
                       if le._normalize_optical_solid_face_function(record.get('function'), legacy_role=record.get('role'))
                       != le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT)
        editor.append_debug(f'CAD/STL face editor saved S{self.row_index}: {reason_text}; {assigned} non-default face functions.')

    # ---- actions (each notifies) ---------------------------------------------------------------------
    def apply_selected(self) -> None:
        """Apply Form to Selected."""
        if self.apply_form_to_selection():
            self.persist('Apply Form to Selected')
            self.editor.status_var.set(f'Saved CAD/STL optical face changes for S{self.row_index}.')
        self.notify()

    def set_side_and_apply(self, side: str) -> None:
        self.form['side'] = self.le._normalize_optical_solid_face_side(side)
        self.apply_selected()

    def set_port_and_apply(self, port_role: str) -> None:
        self.form['port'] = self.le._normalize_optical_solid_face_port_role(port_role)
        self.apply_selected()

    def auto_apply(self) -> None:
        """A field was committed (a choice picked, an entry left or Returned, Flip toggled)."""
        le, editor = self.le, self.editor
        illum_inward = le.optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ILLUMINATION
        illum_outward = le.optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ILLUMINATION_OUTWARD
        index = self.selected_index()
        face_id = str(self.records[index].get('face_id', '') or '').strip() if index is not None else ''
        current = str(self.form['function'])
        if current in (illum_inward, illum_outward):
            # bugs/0268 + 0269: an Illumination Source is a scene source, NOT a coating -- bind it with
            # the chosen aim and skip the coating apply (which would reset the face's real function to
            # Unassigned). "into solid" aims INTO the element (the coupling case); "(outward)" floods.
            aim = 'outward' if current == illum_outward else 'inward'
            if not face_id:
                self.validation = 'Select one CAD/STL face first to make it an Illumination Source.'
            else:
                source_id = editor.create_illumination_source_at_face(self.row_index, face_id=face_id, aim=aim)
                if source_id:
                    where = 'into the solid' if aim == 'inward' else 'outward into the scene'
                    self.validation = (f'{face_id} is now an Illumination Source ({source_id}), aimed {where}; '
                                       'toggle Overlays -> "Illum emission".')
                    editor.status_var.set(f'Illumination source bound on S{self.row_index}.')
                    editor._refresh_open_3d_views(force_retrace=True)
                else:
                    self.validation = f'Could not bind an illumination source to {face_id} (face anchor unavailable).'
            self.notify()
            return
        # Not illumination: if this face WAS an Illumination Source, unbind it before applying a coating.
        if face_id and editor.face_bound_illumination_source_id(self.row_index, face_id):
            editor.unbind_face_illumination_source(self.row_index, face_id)
            editor._refresh_open_3d_views(force_retrace=True)
        if self.apply_form_to_selection(quiet=True):
            index = self.selected_index()
            record = self.records[index] if index is not None else {}
            shown_id = str(record.get('face_id', 'selected face') or 'selected face')
            function = le._optical_solid_face_function_display(record.get('function'), legacy_role=record.get('role'))
            self.persist(f'{shown_id} {function}')
            self.validation = f"Saved {shown_id}: {le._normalize_optical_solid_face_side(record.get('side_2d'))} / {function}."
            editor.status_var.set(f'Saved CAD/STL optical face changes for S{self.row_index}.')
        self.notify()

    def _replace_records(self, records: list, message: str, *, first: bool) -> None:
        self.records = records
        self.mesh_cache_generation += 1
        if first or not self.selection:
            self.selection, self.focus = ([0], 0) if self.records else ([], None)
        self.load_form()
        self.validation = message
        self.notify()

    def auto_guess(self) -> None:
        le = self.le
        records = le.suggest_optical_solid_face_roles(le.auto_assign_optical_solid_face_roles(self.records))
        self._replace_records(records, 'Auto guessed 2D side labels from face centroids. Review before saving.', first=True)

    def refresh_suggestions(self) -> None:
        records = self.le.suggest_optical_solid_face_roles(self.records)
        count = sum(1 for record in records if self.le._optical_solid_face_suggestion_label(record))
        self._replace_records(records, f'Updated {count} geometry suggestions. Suggestions use Uncoated physics; '
                                       'TIR remains a trace-time result.', first=False)

    def apply_suggestions_to_empty(self) -> None:
        records = self.le.apply_optical_solid_face_suggestions(self.records, overwrite=False)
        self._replace_records(records, 'Applied suggestions only to empty side/function/port fields. Existing '
                                       'authored face assignments were preserved.', first=False)

    def clear_roles(self) -> None:
        le = self.le
        for record in self.records:
            record.update({
                'role': le.OPTICAL_SOLID_FACE_ROLE_DEFAULT, 'function': le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
                'side_2d': le.OPTICAL_SOLID_FACE_SIDE_DEFAULT, 'port_role': le.OPTICAL_SOLID_FACE_PORT_DEFAULT,
                'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'flip_normal': False,
                'suggested_side_2d': le.OPTICAL_SOLID_FACE_SIDE_DEFAULT,
                'suggested_function': le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
                'suggested_port_role': le.OPTICAL_SOLID_FACE_PORT_DEFAULT, 'suggestion_confidence': 0.0,
                'suggestion_reason': '', 'suggestion_source': '', 'notes': ''})
        self.selection, self.focus = ([0], 0) if self.records else ([], None)
        self.load_form()
        self.validation = 'Cleared optical face roles in the dialog. Save to write this to the row.'
        self.notify()

    # ---- virtual internal plane ----------------------------------------------------------------------
    def _load_virtual_form(self, plane: dict) -> None:
        le = self.le
        self.virtual_form = {
            'diagonal': le._normalize_optical_solid_virtual_plane_diagonal(plane.get('diagonal_mode')),
            'split': f"{float(plane.get('split_ratio', 0.5) or 0.5):.6g}",
            'loss': f"{float(plane.get('loss', 0.0) or 0.0):.6g}",
            'phase': f"{float(plane.get('phase_deg', 0.0) or 0.0):.6g}",
            'aperture': f"{float(plane.get('aperture_mm', 0.0) or 0.0):.6g}",
            'notes': str(plane.get('notes', '') or '')}

    def _set_virtual_status(self) -> None:
        le = self.le
        if self.virtual_planes:
            plane = le.normalize_optical_solid_virtual_plane_record(self.virtual_planes[0])
            self.virtual_status = 'Saved virtual plane: {plane_id} | {diagonal} | aperture={aperture:.4g} mm | split={split:.4g}'.format(
                plane_id=plane.get('plane_id', 'VP001'),
                diagonal=le._normalize_optical_solid_virtual_plane_diagonal(plane.get('diagonal_mode')),
                aperture=float(plane.get('aperture_mm', 0.0) or 0.0), split=float(plane.get('split_ratio', 0.5) or 0.5))
        else:
            self.virtual_status = 'No virtual internal plane saved.'

    def build_virtual_cube_plane(self) -> None:
        le, form = self.le, self.virtual_form
        split, loss = le._float_or_default(form['split'], 0.5), le._float_or_default(form['loss'], 0.0)
        phase, aperture = le._float_or_default(form['phase'], 0.0), le._float_or_default(form['aperture'], 0.0)
        error = ('Virtual plane split ratio must be between 0 and 1.' if not 0.0 <= split <= 1.0
                 else 'Virtual plane loss must be between 0 and 1.' if not 0.0 <= loss <= 1.0
                 else 'Virtual plane aperture must be non-negative.' if aperture < 0.0 else '')
        if not error:
            try:
                plane = le.build_optical_solid_cube_splitter_virtual_plane(
                    {'faces': self.records, 'virtual_planes': self.virtual_planes, 'source_stl': str(self.path)},
                    diagonal_mode=form['diagonal'], split_ratio=split, loss=loss, phase_deg=phase,
                    aperture_mm=aperture, notes=form['notes'])
            except Exception as exc:
                error = f'Could not build cube splitter plane: {le._short_error_message(exc)}'
        if error:
            self.virtual_status = error
            self.notify()
            return
        self.virtual_planes = [plane]
        self._load_virtual_form(plane)
        self._set_virtual_status()
        self.notify()

    def clear_virtual_planes(self) -> None:
        self.virtual_planes = []
        self._set_virtual_status()
        self.notify()

    # ---- input snap ----------------------------------------------------------------------------------
    def selected_input_snap_face_index(self) -> int | None:
        index = self.selected_index()
        if index is None or self.le._optical_solid_face_port_role(self.records[index]) != self.le.OPTICAL_SOLID_FACE_PORT_INPUT:
            return None
        return int(index)

    def set_input_snap_pick_mode(self, active: bool) -> None:
        if active and self.selected_input_snap_face_index() is None:
            self.input_snap_pick_active = False
            self.preview_status = 'Pick In 3D requires the currently selected face to be the Input Port.'
            self.validation = 'Select the intended Input Port face first, then use Pick In 3D.'
            self.notify()
            return
        self.input_snap_pick_active = bool(active)
        if self.input_snap_pick_active:
            record = self.records[self.selected_input_snap_face_index()]
            self.preview_status = f"Input snap pick armed for {record.get('face_id')}: click the desired entrance point on that face."
        self.notify()

    def toggle_input_snap_pick(self) -> None:
        self.set_input_snap_pick_mode(not self.input_snap_pick_active)

    def clear_input_snap_offsets(self) -> None:
        self.form['input_offset_u'] = '0'
        self.form['input_offset_v'] = '0'
        if self.apply_form_to_selection(quiet=True):
            self.validation = 'Input snap offsets cleared for the selected face.'
        self.input_snap_pick_active = False
        self.notify()

    def preview_row(self, *, single_face: dict | None = None):
        """A copy of the row carrying the dialog's CURRENT faces (or just ``single_face``)."""
        le = self.le
        temp_row = le.SurfaceRow(**asdict(self.row))
        temp_row.advanced = dict(temp_row.advanced or {})
        faces = [single_face] if isinstance(single_face, dict) else self.records
        temp_row.advanced[le.OPTICAL_SOLID_FACES_ADVANCED_ATTR] = le.normalize_optical_solid_face_metadata(
            {'faces': faces, 'virtual_planes': self.virtual_planes, 'source_stl': str(self.path)}, source_stl=str(self.path))
        return temp_row

    def world_face(self, index: int) -> dict | None:
        if not 0 <= index < len(self.records):
            return None
        face_id = str(self.records[index].get('face_id', '') or '').strip()
        if not face_id:
            return None
        for face in self.le.optical_solid_face_world_records(self.preview_row(), self.z_station, assigned_only=False):
            if str(face.get('face_id', '') or '').strip() == face_id:
                return dict(face)
        return None

    def apply_input_snap_pick(self, index: int, point_world, *, source: str) -> bool:
        le = self.le
        selected = self.selected_input_snap_face_index()
        if selected is None:
            self.validation = 'Pick In 3D requires the selected face to be the Input Port.'
            self.input_snap_pick_active = False
            self.notify()
            return False
        if int(index) != int(selected):
            target = self.records[selected].get('face_id', 'selected input face')
            self.preview_status = f'Input snap pick is locked to {target}. Click that face directly.'
            self.validation = f'Pick In 3D only applies to the selected Input Port face ({target}).'
            self.notify()
            return False
        face = self.world_face(index)
        if face is None:
            self.validation = 'Selected face world geometry is not available for input snap.'
            self.notify()
            return False
        try:
            u_value, v_value, projected = le.optical_solid_metadata.optical_solid_face_project_world_point_to_uv(face, point_world)
        except Exception as exc:
            self.validation = f'Could not project picked point onto the face plane: {le._short_error_message(exc)}'
            self.notify()
            return False
        self.selection, self.focus = [int(index)], int(index)
        self.load_form()
        self.form['input_offset_u'] = f'{float(u_value):.6g}'
        self.form['input_offset_v'] = f'{float(v_value):.6g}'
        if not self.apply_form_to_selection(quiet=True):
            self.notify()
            return False
        self.input_snap_pick_active = False
        self.validation = (f"{source}: {face.get('face_id')} input snap set to U={float(u_value):.6g}, "
                           f'V={float(v_value):.6g} mm at world point {format_vector(projected)}.')
        self.preview_status = f"Input snap stored for {face.get('face_id')}: U={float(u_value):.6g}, V={float(v_value):.6g} mm"
        self.notify()
        return True

    def click_face(self, index: int | None, point_world=None, *, source: str = '3D pick') -> None:
        """A click in the 3D preview landed on face ``index`` (None: on nothing) at ``point_world``."""
        if index is None:
            self.preview_status = ('Input snap pick: click directly on a coloured planar face.' if self.input_snap_pick_active
                                   else 'Click directly on one of the coloured planar faces.')
            self.notify()
            return
        if self.input_snap_pick_active:
            point = np.asarray(point_world if point_world is not None else (np.nan,) * 3, dtype=float).reshape(-1)[:3]
            if point.size < 3 or not np.all(np.isfinite(point)):
                self.preview_status = 'Input snap pick failed: invalid picked 3D point.'
                self.notify()
                return
            self.apply_input_snap_pick(int(index), point, source='3D pick')
            return
        self.select([int(index)], int(index), source=source)

    # ---- save and the actions that leave the dialog ---------------------------------------------------
    def save_roles(self) -> bool:
        from KrakenOS.UI.uihost import host_of

        le, editor = self.le, self.editor
        if self.selection and not self.apply_form_to_selection(quiet=True):
            self.notify()
            return False
        functions = [le._normalize_optical_solid_face_function(r.get('function'), legacy_role=r.get('role')) for r in self.records]
        sides = [le._normalize_optical_solid_face_side(r.get('side_2d')) for r in self.records]
        if (any(f != le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT for f in functions)
                and not any(s != le.OPTICAL_SOLID_FACE_SIDE_DEFAULT for s in sides)
                and not host_of(editor).askyesno(self.TITLE, 'No 2D side labels are assigned. Save function-only metadata anyway?')):
            return False
        metadata_to_save = self.metadata()
        solution, error = None, ''
        if bool(self.form['auto_orient']):
            try:
                solution = editor._solve_optical_solid_path_input_pose(self.row_index, metadata_to_save)
                if solution is None:
                    solution = le.solve_optical_solid_left_input_pose(metadata_to_save)
                    if solution is not None:
                        solution['fit_source'] = 'row plane'
            except Exception as exc:
                error = le._short_error_message(exc)
                try:
                    solution = le.solve_optical_solid_left_input_pose(metadata_to_save)
                    if solution is not None:
                        solution['fit_source'] = 'row plane'
                except Exception:
                    pass
        editor._begin_history_capture()
        target = editor.rows[self.row_index]
        target.advanced = dict(target.advanced or {})
        target.advanced[le.OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata_to_save
        if solution is not None:
            target.tilt_x, target.tilt_y, target.tilt_z = (float(v) for v in solution['tilts'])
            target.desp_x, target.desp_y, target.desp_z = (float(v) for v in solution['desp'])
        editor._sync_table()
        editor._commit_history_capture()
        editor._mark_plot_update_pending()
        editor._invalidate_optical_solid_face_assignment_trace(self.row_index, 'Save Roles')
        editor._clear_open3d_face_metadata_hover_state(self.row_index)
        # Explicit save: cancel any debounced auto-apply retrace and do the one authoritative
        # retrace now (so we never double-retrace on Save Roles).
        self.cancel_pending_retrace()
        editor._refresh_open_3d_views(force_retrace=True)
        editor.append_debug(editor._optical_solid_faces_summary(self.row_index, target))
        if solution is not None:
            label = str(solution.get('label', '') or solution.get('face_id', '') or 'Input Port')
            roll_side = str(solution.get('roll_side', '') or '').strip()
            roll_text = f' with {roll_side} roll' if roll_side else ''
            fit_source = str(solution.get('fit_source', '') or 'row plane').strip()
            if fit_source == 'row plane':
                target_text, validation_target = 'input -Z', 'outward normal -> -Z, incoming ray -> +Z'
            else:
                target_text = fit_source
                validation_target = (f"outward normal -> -traced direction; target={solution.get('target_world_point')}, "
                                     f"direction={solution.get('path_direction')}")
            pose_text = 'Tilt=({:.6g},{:.6g},{:.6g}), Desp=({:.6g},{:.6g},{:.6g})'.format(
                float(target.tilt_x), float(target.tilt_y), float(target.tilt_z),
                float(target.desp_x), float(target.desp_y), float(target.desp_z))
            editor.append_debug(f'CAD/STL auto orientation S{self.row_index}: {label} -> {target_text}{roll_text}; {pose_text}')
            editor.status_var.set(f'Saved face roles and oriented S{self.row_index} from {target_text}.')
            self.validation = f'Saved roles. Auto-oriented {label} as the input face: {validation_target}{roll_text}. {pose_text}'
        elif bool(self.form['auto_orient']):
            detail = f' ({error})' if error else ' (assign an Input Port face to enable this)'
            editor.status_var.set(f'Saved CAD/STL optical face roles for S{self.row_index}; auto orientation skipped{detail}.')
            self.validation = ('Saved optical face roles and virtual planes. Auto orientation skipped because no valid '
                               'Input Port face was available' + detail + '.')
        else:
            editor.status_var.set(f'Saved CAD/STL optical face roles for S{self.row_index}.')
            self.validation = 'Saved optical face roles and virtual planes. Auto orientation is disabled for this save.'
        self.notify()
        return True

    def _commit_selected_face(self) -> str | None:
        """Write the form into the ONE selected face and save; its face id, or None (message set)."""
        index = self.selected_index()
        if index is None:
            self.validation = 'Select one CAD/STL face first.'
            return None
        parsed = self.parse_form()
        if parsed is None:
            return None
        self._update_record(index, parsed)
        face_id = str(self.records[index].get('face_id', '') or '').strip()
        if not face_id:
            self.validation = 'Selected face has no face ID.'
            return None
        self.selection, self.focus = [index], index
        if not self.save_roles():
            return None
        return face_id

    def use_as_source_target(self) -> None:
        face_id = self._commit_selected_face()
        if face_id is None:
            self.notify()
            return
        self.validation = f'Saved {face_id}; opening Scene Source Manager with this face preselected.'
        self.notify()
        self.editor.open_scene_source_manager(aim_row_index=self.row_index, aim_face_id=face_id)

    def use_as_illumination_source(self) -> None:
        face_id = self._commit_selected_face()
        if face_id is None:
            self.notify()
            return
        source_id = self.editor.create_illumination_source_at_face(self.row_index, face_id=face_id)
        if not source_id:
            self.validation = f'Could not bind an illumination source to {face_id} (face anchor unavailable).'
        else:
            self.validation = f'Bound illumination source {source_id} to {face_id}; the face now emits (toggle "Illum rays" in Open 3D).'
            self.editor._refresh_open_3d_views(force_retrace=True)
        self.notify()

    def open_placement_view(self) -> None:
        self.editor._select_table_row(self.row_index)
        self.editor.open_optical_stl_placement_assistant()

    def open_native_surface_props(self) -> None:
        self.editor.open_advanced_surface_editor(self.row_index)

    def summary_text(self) -> str:
        le = self.le
        temp_row = le.SurfaceRow(**asdict(self.editor.rows[self.row_index]))
        temp_row.advanced = dict(temp_row.advanced or {})
        temp_row.advanced[le.OPTICAL_SOLID_FACES_ADVANCED_ATTR] = self.metadata()
        return self.editor._optical_solid_faces_summary(self.row_index, temp_row)

    def copy_summary(self) -> None:
        text = self.summary_text()
        ok, backend = self.editor._copy_text_to_clipboard(text + '\n')
        self.editor.append_debug(text)
        self.editor.status_var.set(f'CAD/STL optical face summary copied ({backend}).' if ok
                                   else 'CAD/STL optical face summary written to Debug; clipboard unavailable.')

    # ---- geometry the previews draw --------------------------------------------------------------------
    def face_source_triangles(self, index: int) -> np.ndarray:
        """Triangles for face ``index``: by B-Rep triangle_indices, else planar cluster."""
        le = self.le
        if self.brep_backed:
            if 0 <= index < len(self.records):
                return le.optical_solid_face_record_triangles(self.path, self.records[index])
            return np.empty((0, 3, 3), dtype=float)
        if 0 <= index < len(self.candidates):
            return le.optical_solid_face_candidate_triangles(self.path, self.candidates[index])
        return np.empty((0, 3, 3), dtype=float)

    def row_rotation(self) -> np.ndarray:
        row = self.row
        return self.le._rotation_matrix_from_kraken_tilts(float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))

    def to_world(self, points) -> np.ndarray:
        """Row-local points placed as the row is: rotated, decentred, at its station."""
        pts = np.asarray(points, dtype=float)[:, :3] @ self.row_rotation().T
        pts[:, 0] += float(self.row.desp_x)
        pts[:, 1] += float(self.row.desp_y)
        pts[:, 2] += float(self.z_station) + float(self.row.desp_z)
        return pts

    def face_normal_world(self, index: int) -> np.ndarray | None:
        normal = np.asarray(self.records[index].get('normal', [0.0, 0.0, 1.0]), dtype=float).reshape(-1)[:3]
        if bool(self.records[index].get('flip_normal', False)):
            normal = -normal
        normal = normal @ self.row_rotation().T
        norm = float(np.linalg.norm(normal))
        if norm <= 1e-12 or not np.isfinite(norm):
            return None
        return normal / norm

    def face_colour(self, index: int, selected_index: int | None) -> tuple:
        """(colour, assigned) for a face: orange when selected, else its role colour."""
        le, record = self.le, self.records[index]
        role = le._legacy_role_from_optical_solid_face_function(record.get('function', record.get('role')))
        side = le._normalize_optical_solid_face_side(record.get('side_2d'))
        colour = (1.0, 0.48, 0.02) if index == selected_index else le.optical_solid_face_role_color(role)
        assigned = role != le.OPTICAL_SOLID_FACE_ROLE_DEFAULT or side != le.OPTICAL_SOLID_FACE_SIDE_DEFAULT
        return colour, assigned

    def preview_status_text(self, visible_faces: int, reason: str = '') -> str:
        reason_text = f' | {reason}' if reason else ''
        if self.input_snap_pick_active:
            index = self.selected_index()
            face = self.records[index] if index is not None else {}
            return (f"Input snap pick armed for {face.get('face_id', 'selected Input Port')}: click that face | "
                    f'candidates={visible_faces}{reason_text}')
        return f'3D face preview: click selects, left-drag rotates | candidates={visible_faces}{reason_text}'
