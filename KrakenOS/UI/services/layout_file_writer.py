"""Layout file serialization service."""

from __future__ import annotations

from pathlib import Path
from pprint import pformat
from typing import Any

import numpy as np


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class LayoutFileWriterService:
    """Write self-contained Python layout files from editor rows and settings."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _write_layout_file(self, path: Path) -> None:
        le = _layout_module()
        BEAM_SPLITTER_ADVANCED_ATTR = le.BEAM_SPLITTER_ADVANCED_ATTR
        BEAM_SPLITTER_DEFAULT_SETTINGS = le.BEAM_SPLITTER_DEFAULT_SETTINGS
        BEAM_SPLITTER_SURFACE = le.BEAM_SPLITTER_SURFACE
        REFLECTIVE_PROXY_SURFACES = le.REFLECTIVE_PROXY_SURFACES
        _UNSERIALIZABLE_LAYOUT_VALUE = le._UNSERIALIZABLE_LAYOUT_VALUE
        _beam_splitter_coating_for_settings = le._beam_splitter_coating_for_settings
        _layout_literal_value = le._layout_literal_value
        self._read_rows_from_table()
        title = path.stem.replace("_", " ").title()
        settings = self._collect_layout_settings()
        settings_text = pformat(settings, sort_dicts=False, width=100)
        omitted_complex_fields: list[str] = []
        lines = [
            "#!/usr/bin/env python3",
            f'TITLE = "{title}"',
            "",
            f"SETTINGS = {settings_text}",
            "",
            "from pathlib import Path",
            "import KrakenOS as Kos",
            "import numpy as np",
            "from KrakenOS.UI.custom_surfaces import decode_custom_surface_value",
            "from KrakenOS.UI.nonseq_output_ports import apply_optical_solid_output_port_system_overrides",
            "from KrakenOS.UI.saved_layout_plot import display_saved_layout_2d",
            "from KrakenOS.UI.source_trace_helpers import build_saved_layout_rays",
            "",
            "",
            "def build_system():",
            "    surfaces = []",
        ]
        for index, row in enumerate(self.rows):
            var_name = f"s{index}"
            rc_bounds_repr = repr(tuple(row.optimize_rc_bounds)) if row.optimize_rc_bounds is not None else "None"
            thickness_bounds_repr = repr(tuple(row.optimize_thickness_bounds)) if row.optimize_thickness_bounds is not None else "None"
            uda_literal = _layout_literal_value(row.uda)
            extra_data_literal = _layout_literal_value(row.extra_data)
            advanced_literals: dict[str, object] = {}
            for attr, value in sorted((row.advanced or {}).items()):
                literal = _layout_literal_value(value)
                if literal is _UNSERIALIZABLE_LAYOUT_VALUE:
                    omitted_complex_fields.append(f"{row.name or var_name}: {attr}")
                else:
                    advanced_literals[attr] = literal
            lines.extend(
                [
                    f"    {var_name} = Kos.surf()",
                    f"    {var_name}.Name = {row.name!r}",
                    f"    {var_name}.Rc = {float(row.rc)!r}",
                    f"    {var_name}.k = {float(row.k)!r}",
                    f"    {var_name}.Axicon = {float(row.axicon)!r}",
                    f"    {var_name}.Diff_Ord = {float(row.diff_ord)!r}",
                    f"    {var_name}.Grating_D = {float(row.grating_d)!r}",
                    f"    {var_name}.Grating_Angle = {float(row.grating_angle)!r}",
                    f"    {var_name}.Thickness = {float(row.thickness)!r}",
                    f"    {var_name}.Diameter = {float(row.diameter)!r}",
                    f"    {var_name}.InDiameter = {float(row.in_diameter)!r}",
                    f"    {var_name}.Drawing = {float(row.drawing)!r}",
                    f"    {var_name}.TiltX = {float(row.tilt_x)!r}",
                    f"    {var_name}.TiltY = {float(row.tilt_y)!r}",
                    f"    {var_name}.TiltZ = {float(row.tilt_z)!r}",
                    f"    {var_name}.DespX = {float(row.desp_x)!r}",
                    f"    {var_name}.DespY = {float(row.desp_y)!r}",
                    f"    {var_name}.DespZ = {float(row.desp_z)!r}",
                    f"    {var_name}.AxisMove = {float(row.axis_move)!r}",
                    f"    {var_name}.Glass = {row.glass!r}",
                ]
            )
            if uda_literal is not _UNSERIALIZABLE_LAYOUT_VALUE and uda_literal != "None":
                lines.append(f"    {var_name}.UDA = decode_custom_surface_value({pformat(uda_literal, width=100)})")
            elif row.uda != "None":
                omitted_complex_fields.append(f"{row.name or var_name}: UDA")
            if extra_data_literal is not _UNSERIALIZABLE_LAYOUT_VALUE:
                try:
                    has_extra_data = not np.all(np.asarray(row.extra_data, dtype=object) == 0)
                except Exception:
                    has_extra_data = row.extra_data not in (0, 0.0, "None", None)
                if has_extra_data:
                    lines.append(f"    {var_name}.ExtraData = decode_custom_surface_value({pformat(extra_data_literal, width=100)})")
            else:
                try:
                    if not np.all(np.asarray(row.extra_data, dtype=object) == 0):
                        omitted_complex_fields.append(f"{row.name or var_name}: ExtraData")
                except Exception:
                    if row.extra_data not in (0, 0.0, "None", None):
                        omitted_complex_fields.append(f"{row.name or var_name}: ExtraData")
            for attr, literal in advanced_literals.items():
                lines.append(f"    {var_name}.{attr} = {pformat(literal, width=100)}")
            if row.surface in REFLECTIVE_PROXY_SURFACES:
                lines.append(f"    {var_name}.Glass = 'MIRROR'")
            if row.surface == BEAM_SPLITTER_SURFACE:
                splitter_literal = advanced_literals.get(
                    BEAM_SPLITTER_ADVANCED_ATTR,
                    _layout_literal_value(BEAM_SPLITTER_DEFAULT_SETTINGS),
                )
                coating_literal = _beam_splitter_coating_for_settings(splitter_literal, advanced_literals.get("Coating"))
                lines.append(f"    {var_name}.BeamSplitter = {pformat(splitter_literal, width=100)}")
                lines.append(f"    {var_name}.Coating = {pformat(coating_literal, width=100)}")
                lines.append(f"    {var_name}.Glass = 'AIR' if {var_name}.Glass == 'MIRROR' else {var_name}.Glass")
            if row.optimize_rc:
                lines.append(f"    {var_name}.optimize_rc = True")
            if row.optimize_rc_bounds is not None:
                lines.append(f"    {var_name}.optimize_rc_bounds = {tuple(row.optimize_rc_bounds)!r}")
            if row.optimize_thickness:
                lines.append(f"    {var_name}.optimize_thickness = True")
            if row.optimize_thickness_bounds is not None:
                lines.append(f"    {var_name}.optimize_thickness_bounds = {tuple(row.optimize_thickness_bounds)!r}")
            if row.surface == "Thin Lens":
                focal = float(row.rc) if float(row.rc) != 0.0 else 100.0
                lines.append(f"    {var_name}.Thin_Lens = {focal!r}")
                lines.append(f"    {var_name}.Rc = 0.0")
            elif row.surface == "Grating":
                if abs(float(row.diff_ord)) < 1e-12:
                    lines.append(f"    {var_name}.Diff_Ord = 1.0")
                if abs(float(row.grating_d)) < 1e-12:
                    lines.append(f"    {var_name}.Grating_D = 1.0")
            lines.append(
                "    surfaces.append({"
                f"'surface': {row.surface!r}, "
                f"'element': {row.element!r}, "
                f"'name': {row.name!r}, "
                f"'rc': {float(row.rc)!r}, "
                f"'k': {float(row.k)!r}, "
                f"'axicon': {float(row.axicon)!r}, "
                f"'diff_ord': {float(row.diff_ord)!r}, "
                f"'grating_d': {float(row.grating_d)!r}, "
                f"'grating_angle': {float(row.grating_angle)!r}, "
                f"'thickness': {float(row.thickness)!r}, "
                f"'diameter': {float(row.diameter)!r}, "
                f"'in_diameter': {float(row.in_diameter)!r}, "
                f"'drawing': {float(row.drawing)!r}, "
                f"'extra_data': {repr(extra_data_literal if extra_data_literal is not _UNSERIALIZABLE_LAYOUT_VALUE else 0.0)}, "
                f"'uda': {repr(uda_literal if uda_literal is not _UNSERIALIZABLE_LAYOUT_VALUE else 'None')}, "
                f"'advanced': {repr(advanced_literals)}, "
                f"'tilt_x': {float(row.tilt_x)!r}, "
                f"'tilt_y': {float(row.tilt_y)!r}, "
                f"'tilt_z': {float(row.tilt_z)!r}, "
                f"'desp_x': {float(row.desp_x)!r}, "
                f"'desp_y': {float(row.desp_y)!r}, "
                f"'desp_z': {float(row.desp_z)!r}, "
                f"'axis_move': {float(row.axis_move)!r}, "
                f"'glass': {row.glass!r}, "
                f"'optimize_rc': {row.optimize_rc!r}, "
                f"'optimize_rc_bounds': {rc_bounds_repr}, "
                f"'optimize_thickness': {row.optimize_thickness!r}, "
                f"'optimize_thickness_bounds': {thickness_bounds_repr}"
                "})"
            )
            lines.append("")
        lines.extend(
            [
                "    return surfaces",
                "",
                "",
                "SURFACES = build_system()",
                "",
                "",
                "def build_runtime_system():",
                "    surface_dicts = SURFACES",
                "    runtime_surfaces = []",
                "    clear_aperture = max((max(float(spec['diameter']), 1.0) for spec in surface_dicts if spec['surface'] not in {'Object', 'Image'}), default=100.0) * 4.0",
                "    for spec in surface_dicts:",
                "        s = Kos.surf()",
                "        s.Name = spec['name']",
                "        s.Rc = spec['rc']",
                "        s.k = spec.get('k', spec.get('K', 0.0))",
                "        s.Axicon = spec.get('axicon', 0.0)",
                "        s.Diff_Ord = spec.get('diff_ord', spec.get('Diff_Ord', 0.0))",
                "        s.Grating_D = spec.get('grating_d', spec.get('Grating_D', 0.0))",
                "        s.Grating_Angle = spec.get('grating_angle', spec.get('Grating_Angle', 0.0))",
                "        s.Thickness = spec['thickness']",
                "        s.Diameter = clear_aperture if spec['surface'] == 'Object' else spec['diameter']",
                "        s.InDiameter = spec.get('in_diameter', spec.get('InDiameter', 0.0))",
                "        s.Drawing = spec.get('drawing', spec.get('Drawing', 1.0))",
                "        if 'ExtraData' in spec or 'extra_data' in spec:",
                "            s.ExtraData = decode_custom_surface_value(spec.get('extra_data', spec.get('ExtraData', s.ExtraData)))",
                "        if 'UDA' in spec or 'uda' in spec:",
                "            s.UDA = decode_custom_surface_value(spec.get('uda', spec.get('UDA', s.UDA)))",
                "        for attr, value in spec.get('advanced', {}).items():",
                "            if attr in {'AspherData', 'ZNK'}:",
                "                value = np.asarray(value, dtype=float).ravel()",
                "                min_len = 200 if attr == 'AspherData' else 36",
                "                if value.size < min_len:",
                "                    value = np.pad(value, (0, min_len - value.size), mode='constant')",
                "            elif attr == 'Error_map':",
                "                x_values, y_values, z_values, space = value",
                "                space_arr = np.asarray(space, dtype=float).ravel()",
                "                spacing = float(space_arr[0]) if space_arr.size else 1.0",
                "                value = [np.asarray(x_values, dtype=float).ravel().tolist(), np.asarray(y_values, dtype=float).ravel().tolist(), np.asarray(z_values, dtype=float).ravel().tolist(), spacing]",
                "            setattr(s, attr, value)",
                "        s.TiltX = spec.get('tilt_x', 0.0)",
                "        s.TiltY = spec.get('tilt_y', 0.0)",
                "        s.TiltZ = spec.get('tilt_z', 0.0)",
                "        s.DespX = spec.get('desp_x', 0.0)",
                "        s.DespY = spec.get('desp_y', 0.0)",
                "        s.DespZ = spec.get('desp_z', 0.0)",
                "        s.AxisMove = spec.get('axis_move', 0.0)",
                "        s.Glass = spec['glass']",
                "        if spec['surface'] in {'Mirror', 'Object Target', 'Diffuse Object'}:",
                "            s.Glass = 'MIRROR'",
                "            if abs(s.AxisMove) < 1e-9:",
                "                s.AxisMove = 2.0",
                "        if spec['surface'] == 'Diffuse Object':",
                "            s.DiffuseScatter = spec.get('advanced', {}).get('DiffuseScatter', {'model': 'Lambertian', 'backend': 'Built-in', 'backend_model': 'Microroughness_BRDF_Model', 'backend_parameters': {}, 'reflectance': 0.8, 'sample_count': 9, 'max_scatter_angle_deg': 90.0, 'lobe_exponent': 20.0, 'roughness_deg': 20.0, 'min_branch_power': 1e-4, 'max_branch_depth': 2, 'polarization': 'Preserve projected Jones'})",
                "        if spec['surface'] == 'Beam Splitter':",
                "            splitter = spec.get('advanced', {}).get('BeamSplitter', {'reflectance': 0.5, 'absorption': 0.0})",
                "            r = min(max(float(splitter.get('reflectance', 0.5)), 0.0), 1.0)",
                "            a = min(max(float(splitter.get('absorption', 0.0)), 0.0), 1.0 - r)",
                "            wl = [0.45, 0.55, 0.65]",
                "            th = [0.0, 45.0, 70.0]",
                "            s.BeamSplitter = splitter",
                "            mode = str(splitter.get('split_mode', '')).lower()",
                "            existing_coating = spec.get('advanced', {}).get('Coating')",
                "            if 'coating table' in mode and existing_coating not in (None, [[], [], [], []]):",
                "                s.Coating = existing_coating",
                "            else:",
                "                s.Coating = [[[r for _w in wl] for _t in th], [[a for _w in wl] for _t in th], wl, th]",
                "            if str(s.Glass).upper() == 'MIRROR':",
                "                s.Glass = 'AIR'",
                "        if spec['surface'] == 'Thin Lens':",
                "            s.Thin_Lens = spec['rc'] if spec['rc'] != 0 else 100.0",
                "            s.Rc = 0.0",
                "        elif spec['surface'] == 'Grating':",
                "            if abs(float(s.Diff_Ord)) < 1e-12:",
                "                s.Diff_Ord = 1.0",
                "            if abs(float(s.Grating_D)) < 1e-12:",
                "                s.Grating_D = 1.0",
                "        runtime_surfaces.append(s)",
                "    setup = Kos.Setup()",
                "    for metal in SETTINGS.get('metal_catalogs', []):",
                "        try:",
                "            path = Path(str(metal.get('path', ''))).expanduser()",
                "            name = str(metal.get('name') or path.stem).strip() or path.stem",
                "            catalog_type = int(metal.get('type', 1))",
                "            if path.exists() and name.lower() not in {str(item).lower() for item in getattr(setup, 'Name_met', [])}:",
                "                setup.LoadMetal(str(path), name, catalog_type)",
                "        except Exception as exc:",
                "            print(f'Could not load metal catalog {metal!r}: {exc}')",
                "    system = Kos.system(runtime_surfaces, setup)",
                "    apply_optical_solid_output_port_system_overrides(system, surface_dicts)",
                "    return system",
                "",
                "",
                "def build_rays(system):",
                "    return build_saved_layout_rays(system, SURFACES, SETTINGS, Kos)",
                "",
                "",
                "if __name__ == '__main__':",
                "    system = build_runtime_system()",
                "    rays = build_rays(system)",
                "    display_saved_layout_2d(SURFACES, SETTINGS, system=system, rays=rays, layout_path=Path(__file__))",
                "",
            ]
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        if omitted_complex_fields:
            self.append_debug("Layout save omitted non-serializable fields: " + ", ".join(omitted_complex_fields))
        self._mark_saved_state()
        self.status_var.set(f"Saved {path.name}")
