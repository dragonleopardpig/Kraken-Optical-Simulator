"""The Stock Lens Importer record-list form (docs/design_qt_migration.md phase 3).

A catalogue search that INSERTS rows: pick a .ZMF catalogue, search it, choose a part, and the
Apply turns that catalogue item into a rigid block of surface rows. In path mode (opened from a
path-component command) it also takes the placement -- distance along the arm plus a local
decenter and tilt -- and inserts the block on that path instead of after the selected row.

Two record-list `on_change` fields do the work: the catalogue choice LOADS a catalogue (the
expensive step, so it reports what it loaded) and the search box filters it live.
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RecordList, RowForm

TITLE = "Import Stock Lens"
PATH_TITLE = "Add Stock Lens to Path"
NOTE = ("Edmund and Thorlabs .ZMF catalogs from attachment/ or KrakenOS/LensCat. Pick a part, "
        "then Apply to insert it as a rigid block of surface rows.")
COLUMNS = ("Part", "Description", "Surf", "Dia mm")
#: the Tk importer drew at most this many matches, however many matched
SHOWN_LIMIT = 500
PATH_KEYS = ("local_decenter_x", "local_decenter_y", "local_tilt_x", "local_tilt_y",
             "local_tilt_z")


def model(owner):
    """The stock-lens model, wherever the caller keeps it."""
    from types import SimpleNamespace

    from KrakenOS.UI.services import catalog_metadata

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        available=held("available_stock_lens_catalogs",
                       catalog_metadata._available_stock_lens_catalogs),
        load=held("load_stock_lens_catalog", catalog_metadata._load_stock_lens_catalog),
        summary=held("stock_lens_summary", catalog_metadata._stock_lens_summary),
    )


def build_stock_lens_form(owner, *_args, path_placement: "dict | None" = None,
                          **_kwargs) -> RowForm:
    """The importer over one .ZMF catalogue at a time."""
    parts = model(owner)
    catalogs = dict(parts.available())
    if not catalogs:
        raise FormRefused("No Edmund/Thorlabs .ZMF catalogs were found in attachment/ or "
                          "KrakenOS/LensCat.")
    placement = dict(path_placement or {})
    path_mode = bool(placement)

    fields = [
        FormField("catalog", "Catalog", kind="choice", choices=tuple(catalogs),
                  on_change=lambda form, value: _load_catalog(form, value)),
        FormField("search", "Search", kind="text", width=32,
                  on_change=lambda form, _text: _refilter(form)),
        FormField("part", "Selected part", kind="static"),
        FormField("inverse", "Reverse element", kind="bool"),
        FormField("gap_after", "Gap after [mm]", kind="number"),
    ]
    if path_mode:
        fields.append(FormField("distance", "Path distance [mm]", kind="number"))
        fields.extend(FormField(key, key.replace("_", " ").title(), kind="number")
                      for key in PATH_KEYS)

    form = RowForm(
        title=PATH_TITLE if path_mode else TITLE,
        row_index=0,
        fields=tuple(fields),
        note=NOTE,
        state={"owner": owner, "parts": parts, "catalogs": catalogs, "placement": placement,
               "path_mode": path_mode, "summaries": [], "catalog": {}, "index": 0},
        records=RecordList(columns=COLUMNS, rows=_rows, select=_select),
    )
    form.values = {"catalog": next(iter(catalogs)), "search": "", "part": "",
                   "inverse": "false", "gap_after": "25.0"}
    if path_mode:
        form.values["distance"] = "60.0"
        form.values.update({key: "0" for key in PATH_KEYS})
    _load_catalog(form, form.values["catalog"])

    def validate(values: dict) -> list[str]:
        try:
            _selected_part(form, values)
            _options(form, values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        part = _selected_part(form, values)
        options = _options(form, values)
        return (f"{part} ({'reversed' if options['inverse'] else 'as drawn'}), "
                f"gap after {options['gap_after']:.6g} mm")

    def apply(values: dict) -> str:
        return _import_selected(form, values)

    form.validate = validate
    form.describe = describe
    form.apply = apply
    return form


# ---- the record list ---------------------------------------------------------------------
def matching(form) -> list:
    terms = [term for term in str(form.values.get("search", "")).strip().lower().split()
             if term]
    summaries = list(form.state.get("summaries", []))
    if not terms:
        return summaries
    return [summary for summary in summaries
            if all(term in f"{summary['part_number']} {summary['description']}".lower()
                   for term in terms)]


def _rows(form) -> tuple:
    rows = []
    for summary in matching(form)[:SHOWN_LIMIT]:
        diameter = float(summary.get("diameter", 0.0) or 0.0)
        rows.append((str(summary["part_number"]), str(summary["description"]),
                     str(summary["surface_count"]),
                     f"{diameter:.6g}" if diameter > 0 else ""))
    return tuple(rows)


def _select(form, index: int) -> str:
    shown = matching(form)
    if not shown:
        form.values["part"] = ""
        form.summary = "0 match(es)."
        return form.summary
    index = min(max(int(index), 0), min(len(shown), SHOWN_LIMIT) - 1)
    form.state["index"] = index
    form.values["part"] = str(shown[index]["part_number"])
    drawn = min(len(shown), SHOWN_LIMIT)
    suffix = "" if len(shown) <= drawn else f" showing first {drawn}"
    form.summary = f"{len(shown)} match(es){suffix}. {form.values['part']} selected."
    return form.summary


def _refilter(form) -> str:
    return _select(form, 0)


def _load_catalog(form, label: str) -> str:
    """Read one .ZMF. The expensive step, so it says what it loaded -- or why it could not."""
    owner = form.state["owner"]
    parts = form.state["parts"]
    path = form.state["catalogs"].get(str(label).strip())
    if path is None:
        raise FormRefused(f"Unknown catalog: {label}")
    try:
        catalog = parts.load(path)
        summaries = [parts.summary(part, item) for part, item in sorted(catalog.items())]
    except Exception as exc:
        form.state["catalog"] = {}
        form.state["summaries"] = []
        _select(form, 0)
        raise FormRefused(f"Could not load {label}: {exc}") from exc
    form.state["catalog"] = catalog
    form.state["summaries"] = summaries
    _select(form, 0)
    form.summary = f"{label}: {len(summaries)} parts from {path}. {form.summary}"
    return form.summary


# ---- parsing + apply ---------------------------------------------------------------------
def _selected_part(form, values: dict) -> str:
    part = str(values.get("part", "")).strip()
    if not part:
        raise FormRefused("Select a part number first.")
    catalog = form.state.get("catalog") or {}
    if not isinstance(catalog, dict) or part not in catalog:
        raise FormRefused(f"Catalog item not loaded: {part}")
    return part


def _number(values: dict, key: str, label: str) -> float:
    try:
        value = float(str(values.get(key, "")).strip() or "0")
    except Exception as exc:
        raise FormRefused(f"{label} must be numeric.") from exc
    if not np.isfinite(value):
        raise FormRefused(f"{label} must be finite.")
    return float(value)


def _options(form, values: dict) -> dict:
    options = {
        "inverse": str(values.get("inverse", "")).strip().lower() in ("1", "true", "yes", "on"),
        "gap_after": _number(values, "gap_after", "Gap after"),
    }
    if not form.state["path_mode"]:
        return options
    distance = _number(values, "distance", "Path distance")
    if distance <= 0.0:
        raise FormRefused("Path distance must be positive.")
    options["distance"] = distance
    options["local"] = tuple(
        _number(values, key, "Local offset and tilt values") for key in PATH_KEYS)
    return options


def _import_selected(form, values: dict) -> str:
    owner = form.state["owner"]
    part = _selected_part(form, values)
    options = _options(form, values)
    catalog = form.state["catalog"]
    try:
        rows = owner._stock_lens_rows_from_catalog_item(
            part, catalog[part], inverse=options["inverse"], gap_after=options["gap_after"])
    except Exception as exc:
        raise FormRefused(f"Could not convert {part}: {exc}") from exc

    owner._commit_pending_table_edit()
    try:
        owner._read_rows_from_table()
    except Exception as exc:
        raise FormRefused(f"Could not read the surface table: {exc}") from exc

    placement_label = ""
    try:
        if form.state["path_mode"]:
            placement = form.state["placement"]
            context = owner._path_stock_lens_context(
                splitter_index=int(placement.get("splitter_index", -1)),
                arm_role=str(placement.get("arm_role", "") or ""),
                branch_path=str(placement.get("branch_path", "") or ""),
            )
            local = options["local"]
            rows = owner._stock_lens_rows_for_path_context(
                rows,
                part_number=part,
                context=context,
                distance_mm=float(options["distance"]),
                local_decenter_x=local[0],
                local_decenter_y=local[1],
                local_tilt_x=local[2],
                local_tilt_y=local[3],
                local_tilt_z=local[4],
            )
            insert_index = max(1, min(int(context.get("insert_index", len(owner.rows) - 1)),
                                      len(owner.rows) - 1))
            insert_after = insert_index - 1
            placement_label = str(context.get("placement_label", "path") or "path")
        else:
            insert_after = owner._selected_insert_index()
    except FormRefused:
        raise
    except Exception as exc:
        raise FormRefused(f"Could not place {part} on the selected path: {exc}") from exc

    owner._begin_history_capture()
    insert_at = owner._insert_surface_rows(rows, insert_after=insert_after)
    owner._commit_history_capture()
    owner.current_layout_file = None
    if form.state["path_mode"]:
        message = (f"Inserted stock lens {part} as a rigid {len(rows)}-row block at "
                   f"S{insert_at} on {placement_label}. Click Update.")
    else:
        message = f"Imported stock lens {part} as {len(rows)} surface rows at S{insert_at}."
    owner.status_var.set(message)
    owner.append_progress(message)
    owner.refresh_plot(suppress_analysis=True)
    return message


build_stock_lens_form.TITLE = TITLE
