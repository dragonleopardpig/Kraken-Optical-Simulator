"""The Inspection Cell record-list form (docs/design_qt_migration.md phase 3).

Six faces of one part, each slotted with its own station layout, plus the part's dimensions, the
cell-level solve, and the verbs that compose them -- cell view, interference report, cell STEP,
save and load.

The six faces ARE the record list, which is what makes this a record-list form rather than
twelve loose fields: selecting a face and pressing "Browse Layout..." replaces six per-face
Browse buttons with one verb that acts on the face you picked.

The embedded cell VIEW (`panels/inspection_cell_window.py`) is a VTK plotter and stays in phase 5
-- this form only asks it to open.
"""
from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormRefused, RecordList, RowForm

TITLE = "Inspection Cell (6 stations)"
NOTE = ("Design each face's station as its own layout (Actions -> Inspection Part, inspected "
        "face = that face), then slot the layouts here. The cell view/STEP place every station "
        "on its face.")
COLUMNS = ("Face", "Enabled", "Station layout (.py)")
LAYOUT_FILETYPES = [("KrakenOS layout", "*.py"), ("All files", "*")]
STEP_FILETYPES = [("STEP", "*.step *.stp *.STEP *.STP"), ("All files", "*")]


def model(owner):
    """The inspection-cell model, wherever the caller keeps it."""
    from types import SimpleNamespace

    from KrakenOS.UI.services import inspection_cell as cell_module
    from KrakenOS.UI.services.inspection_part import FACE_ORDER, normalize_inspection_part_spec

    return SimpleNamespace(
        faces=tuple(FACE_ORDER),
        normalize_cell=cell_module.normalize_cell_spec,
        normalize_part=normalize_inspection_part_spec,
        save=cell_module.save_cell,
        load=cell_module.load_cell,
        suffix=cell_module.CELL_SUFFIX,
        compose=cell_module.compose_cell_plotter,
        summary=cell_module.cell_summary,
        export=cell_module.export_cell_step,
    )


def build_inspection_cell_form(owner, *_args, **_kwargs) -> RowForm:
    """The six-station cell around one part."""
    parts = model(owner)
    spec = parts.normalize_cell(getattr(owner, "inspection_cell_spec", None))
    if not getattr(owner, "inspection_cell_spec", None):
        # seed the part from the layout's own part, if it has one
        spec["part"] = parts.normalize_part(getattr(owner, "inspection_part_spec", None))
        spec["part"]["enabled"] = True

    form = RowForm(
        title=TITLE,
        row_index=0,
        fields=(
            FormField("width_mm", "Part width [mm]", kind="number", width=10),
            FormField("height_mm", "Part height [mm]", kind="number", width=10),
            FormField("depth_mm", "Part depth [mm]", kind="number", width=10),
            FormField("step_path", "Part STEP (optional)", kind="text", width=40),
            FormField("face", "Face", kind="static"),
            FormField("enabled", "Station enabled", kind="bool"),
            FormField("layout", "Station layout (.py)", kind="text", width=52),
            FormField("defect_mm", "Smallest defect [mm]", kind="number", width=10),
            FormField("px_per_defect", "px per defect", kind="number", width=8),
            FormField("wd_min_mm", "Min WD [mm, 0 = any]", kind="number", width=10),
            FormField("out_dir", "Solve output folder", kind="text", width=58),
        ),
        note=NOTE,
        state={"owner": owner, "parts": parts, "spec": spec, "index": 0},
        records=RecordList(columns=COLUMNS, rows=_rows, select=_select),
    )
    form.values = {
        "width_mm": f"{float(spec['part']['width_mm']):g}",
        "height_mm": f"{float(spec['part']['height_mm']):g}",
        "depth_mm": f"{float(spec['part']['depth_mm']):g}",
        "step_path": str(spec["part"].get("step_path", "") or ""),
        "defect_mm": "0.1",
        "px_per_defect": "3",
        "wd_min_mm": "0",
        "out_dir": str(_default_out_dir()),
    }
    _select(form, 0)

    def validate(values: dict) -> list[str]:
        try:
            _cell_from_values(form, values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        cell = _cell_from_values(form, values)
        slotted = [face for face in parts.faces if cell["stations"][face]["enabled"]]
        part = cell["part"]
        return (f"{float(part['width_mm']):g} x {float(part['height_mm']):g} x "
                f"{float(part['depth_mm']):g} mm part, "
                f"{len(slotted)} station(s) enabled: {', '.join(slotted) or 'none'}")

    def apply(values: dict) -> str:
        cell = _cell_from_values(form, values)
        owner.inspection_cell_spec = cell
        slotted = sum(1 for face in parts.faces if cell["stations"][face]["enabled"])
        message = f"Inspection cell set: {slotted} of {len(parts.faces)} stations enabled."
        try:
            owner.status_var.set(message)
        except Exception:
            pass
        return message

    form.validate = validate
    form.describe = describe
    form.apply = apply
    form.actions = (
        FormAction("browse_layout", "Browse Layout...", _browse_layout),
        FormAction("browse_step", "Browse Part STEP...", _browse_part_step),
        FormAction("solve", "Solve & Build Stations", _solve_and_build),
        FormAction("view", "Open Cell View", _open_cell_view),
        FormAction("report", "Interference Report", _interference_report),
        FormAction("export", "Export Cell STEP...", _export_cell_step),
        FormAction("save", "Save Cell...", _save_cell),
        FormAction("load", "Load Cell...", _load_cell),
    )
    return form


def _default_out_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "attachment" / "cells" / "solved"


# ---- the record list -------------------------------------------------------------------------
def _rows(form) -> tuple:
    spec = form.state["spec"]
    return tuple((face.capitalize(),
                  "yes" if spec["stations"][face]["enabled"] else "no",
                  str(spec["stations"][face]["layout"] or ""))
                 for face in form.state["parts"].faces)


def _select(form, index: int) -> str:
    parts = form.state["parts"]
    index = min(max(int(index), 0), len(parts.faces) - 1)
    form.state["index"] = index
    face = parts.faces[index]
    station = form.state["spec"]["stations"][face]
    form.values["face"] = face.capitalize()
    form.values["enabled"] = "true" if station["enabled"] else "false"
    form.values["layout"] = str(station["layout"] or "")
    form.summary = f"Editing the {face} station."
    return form.summary


def _face(form) -> str:
    return form.state["parts"].faces[form.selected_index]


def _store_selected(form, values: dict) -> None:
    """Fold the per-face fields back into the spec before anything reads the whole cell."""
    station = form.state["spec"]["stations"][_face(form)]
    station["layout"] = str(values.get("layout", "")).strip()
    station["enabled"] = str(values.get("enabled", "")).strip().lower() in ("1", "true", "yes",
                                                                           "on")


def _number(values: dict, key: str, label: str, *, minimum: float | None = None) -> float:
    try:
        value = float(str(values.get(key, "")).strip() or "0")
    except Exception as exc:
        raise FormRefused(f"{label} expects a number.") from exc
    if minimum is not None and value < minimum:
        raise FormRefused(f"{label} must be >= {minimum:g}.")
    return float(value)


def _cell_from_values(form, values: dict) -> dict:
    parts = form.state["parts"]
    _store_selected(form, values)
    raw = {
        "part": {
            "enabled": True,
            "width_mm": _number(values, "width_mm", "Part width", minimum=0.0),
            "height_mm": _number(values, "height_mm", "Part height", minimum=0.0),
            "depth_mm": _number(values, "depth_mm", "Part depth", minimum=0.0),
            "step_path": str(values.get("step_path", "")).strip(),
        },
        "stations": {face: dict(form.state["spec"]["stations"][face]) for face in parts.faces},
    }
    cell = parts.normalize_cell(raw)
    form.state["spec"] = cell
    return cell


# ---- the verbs -------------------------------------------------------------------------------
def _browse_layout(form, host) -> str:
    face = _face(form)
    path = host.askopenfilename(title=f"Station layout for the {face} face",
                                filetypes=LAYOUT_FILETYPES)
    if not path:
        return "Browse cancelled."
    form.state["spec"]["stations"][face]["layout"] = str(path)
    form.state["spec"]["stations"][face]["enabled"] = True
    _select(form, form.selected_index)
    return f"Slotted {Path(path).name} on the {face} face."


def _browse_part_step(form, host) -> str:
    from KrakenOS.UI.services.inspection_part import apply_step_bounds

    owner = form.state["owner"]
    path = host.askopenfilename(title="Part STEP", filetypes=STEP_FILETYPES)
    if not path:
        return "Browse cancelled."
    form.values["step_path"] = str(path)
    try:
        mesh = owner._load_step_mesh(Path(path), largest_component=False)
        sized = apply_step_bounds({key: form.values[key]
                                   for key in ("width_mm", "height_mm", "depth_mm")}, mesh)
    except Exception as exc:
        return f"Part STEP loaded but bounds failed: {exc}"
    for key in ("width_mm", "height_mm", "depth_mm"):
        form.values[key] = f"{float(sized[key]):g}"
    return (f"Part dims from the STEP bounds: {float(sized['width_mm']):g} x "
            f"{float(sized['height_mm']):g} x {float(sized['depth_mm']):g} mm")


def _solve_and_build(form, host) -> str:
    from KrakenOS.UI.services.inspection_cell_solve import choice_summary, solve_and_build_cell

    cell = _cell_from_values(form, dict(form.values))
    defect = _number(form.values, "defect_mm", "Smallest defect", minimum=0.0)
    per_defect = _number(form.values, "px_per_defect", "px per defect", minimum=0.0)
    wd_min = _number(form.values, "wd_min_mm", "Min WD", minimum=0.0)
    try:
        new_cell, report = solve_and_build_cell(
            cell["part"], defect, str(form.values.get("out_dir", "")),
            px_per_defect=per_defect, wd_min_mm=(wd_min if wd_min > 0 else None),
            name="solved",
        )
    except Exception as exc:
        raise FormRefused(f"Cell solve failed: {exc}") from exc
    form.state["spec"] = new_cell
    form.state["owner"].inspection_cell_spec = new_cell
    _select(form, form.selected_index)
    lines = [choice_summary(report["choices"])]
    lines.extend("NOTE " + error for error in report.get("errors", []))
    lines.append(f"Stations built: {len(report['built'])}; cell saved: "
                 f"{Path(report['cell_path']).name}")
    return "\n".join(lines)


def _open_cell_view(form, _host) -> str:
    from KrakenOS.UI.panels.inspection_cell_window import open_inspection_cell_window

    owner = form.state["owner"]
    cell = _cell_from_values(form, dict(form.values))
    try:
        window = open_inspection_cell_window(owner, cell)
    except Exception as exc:
        raise FormRefused(f"Cell view failed: {exc}") from exc
    if window is None:
        return "Cell shown in the pyvista window (embedded view unavailable)."
    owner.inspection_cell_window = window
    return window.status_var.get() or "Cell view open."


def _interference_report(form, _host) -> str:
    parts = form.state["parts"]
    cell = _cell_from_values(form, dict(form.values))
    try:
        plotter, report = parts.compose(cell, off_screen=True)
        try:
            plotter.close()
        except Exception:
            pass
    except Exception as exc:
        raise FormRefused(f"Report failed: {exc}") from exc
    return parts.summary(report)


def _export_cell_step(form, host) -> str:
    parts = form.state["parts"]
    cell = _cell_from_values(form, dict(form.values))
    path = host.asksaveasfilename(title="Export Cell STEP", defaultextension=".step",
                                  filetypes=[("STEP", "*.step *.stp"), ("All files", "*")])
    if not path:
        return "Export cancelled."
    try:
        report = parts.export(cell, path)
    except Exception as exc:
        raise FormRefused(f"Cell STEP failed: {exc}") from exc
    errors = "; ".join(report.get("errors", []))
    return (f"Cell STEP written: {Path(path).name} ({len(report['stations'])} stations)"
            + (f" -- errors: {errors}" if errors else ""))


def _save_cell(form, host) -> str:
    parts = form.state["parts"]
    cell = _cell_from_values(form, dict(form.values))
    path = host.asksaveasfilename(
        title="Save Cell", defaultextension=parts.suffix,
        filetypes=[("Inspection cell", "*" + parts.suffix), ("All files", "*")])
    if not path:
        return "Save cancelled."
    return f"Cell saved: {parts.save(path, cell).name}"


def _load_cell(form, host) -> str:
    parts = form.state["parts"]
    path = host.askopenfilename(
        title="Load Cell",
        filetypes=[("Inspection cell", "*" + parts.suffix), ("All files", "*")])
    if not path:
        return "Load cancelled."
    try:
        cell = parts.load(path)
    except Exception as exc:
        raise FormRefused(f"Load failed: {exc}") from exc
    form.state["spec"] = cell
    form.state["owner"].inspection_cell_spec = cell
    form.values["width_mm"] = f"{float(cell['part']['width_mm']):g}"
    form.values["height_mm"] = f"{float(cell['part']['height_mm']):g}"
    form.values["depth_mm"] = f"{float(cell['part']['depth_mm']):g}"
    form.values["step_path"] = str(cell["part"].get("step_path", "") or "")
    _select(form, form.selected_index)
    return f"Cell loaded: {Path(path).name}"


build_inspection_cell_form.TITLE = TITLE
