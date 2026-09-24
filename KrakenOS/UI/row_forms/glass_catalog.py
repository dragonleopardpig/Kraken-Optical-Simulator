"""The Glass Catalog Browser record-list form (docs/design_qt_migration.md phase 3).

A catalogue browser is a record-list form with nothing to edit: a filter, a list, and an Apply
that writes the picked glass onto the selected surface row. The only new thing it needed is a
LIVE filter -- an `on_change` on a text field, after which the view re-asks the model for its
rows -- which the record list gave the Stock Lens Importer too.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RecordList, RowForm

TITLE = "Glass Catalog Browser"
NOTE = ("Every glass in the KrakenOS catalogs. Filter by name, index or Abbe number, then apply "
        "the highlighted glass to the selected surface row.")
COLUMNS = ("#", "Glass", "n(d)", "V(d)", "Formula")


def model(owner):
    """The catalogue model, wherever the caller keeps it."""
    from types import SimpleNamespace

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    def shared_setup():
        import KrakenOS as Kos

        return Kos.Setup()

    return SimpleNamespace(setup=held("shared_setup", shared_setup))


def catalog_records(owner) -> list:
    """Every catalogue glass as a record. The model owns the arithmetic, not the view."""
    setup = model(owner).setup()
    # NAMES/NM are numpy arrays, so `or []` raises "truth value ... is ambiguous" -- the Tk
    # browser tested `is not None` for exactly this reason. Keep that.
    names_raw = getattr(setup, "NAMES", None)
    rows_raw = getattr(setup, "NM", None)
    names = list(names_raw) if names_raw is not None else []
    rows = list(rows_raw) if rows_raw is not None else []
    records = []
    for index, name in enumerate(names):
        text = str(name).strip()
        if not text:
            continue
        nd = vd = formula = ""
        try:
            entry = list(rows[index])
            if len(entry) >= 1:
                formula = f"{float(entry[0]):.0f}"
            if len(entry) >= 4:
                nd = f"{float(entry[2]):.8g}"
                vd = f"{float(entry[3]):.8g}"
        except Exception:
            pass
        records.append({"index": index, "name": text, "nd": nd, "vd": vd, "formula": formula})
    return records


def matching(form) -> list:
    """The records the current filter keeps, in catalogue order."""
    query = str(form.values.get("filter", "")).strip().lower()
    records = form.state["records"]
    if not query:
        return list(records)
    return [record for record in records
            if query in (f"{record['name']} {record['nd']} {record['vd']} "
                         f"{record['formula']}").lower()]


def build_glass_catalog_form(owner, *_args, **_kwargs) -> RowForm:
    """The browser over the whole glass catalogue."""
    records = catalog_records(owner)
    if not records:
        raise FormRefused("No glass names were found in the KrakenOS catalogs.")

    form = RowForm(
        title=TITLE,
        row_index=0,
        fields=(
            FormField("filter", "Filter", kind="text", width=32,
                      on_change=lambda current, _text: _refilter(current)),
            FormField("glass", "Selected glass", kind="static"),
        ),
        note=NOTE,
        state={"owner": owner, "records": records, "index": 0},
        records=RecordList(columns=COLUMNS, rows=_rows, select=_select),
    )
    form.values = {"filter": "", "glass": ""}
    _select(form, 0)

    def validate(values: dict) -> list[str]:
        if not str(values.get("glass", "")).strip():
            return ["Pick a glass from the list first."]
        if owner._selected_surface_row_index() is None:
            return ["Select a surface row first, then apply the glass."]
        return []

    def describe(values: dict) -> str:
        return f"{values.get('glass', '')} -> row {owner._selected_surface_row_index()}"

    def apply(values: dict) -> str:
        glass = str(values.get("glass", "")).strip()
        if not glass:
            raise FormRefused("Pick a glass from the list first.")
        row_index = owner._selected_surface_row_index()
        if row_index is None or not (0 <= row_index < len(owner.rows)):
            raise FormRefused("Select a surface row first, then apply the glass.")
        owner._commit_pending_table_edit()
        owner._begin_history_capture()
        owner.rows[row_index].glass = glass
        if owner.rows[row_index].surface == "Mirror":
            # a glass surface is not a mirror; the Tk browser did this silently too
            owner.rows[row_index].surface = "Standard"
        owner._sync_table()
        owner._select_table_row(row_index)
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        message = f"Applied glass {glass} to row {row_index}. Click Update."
        owner.status_var.set(message)
        return message

    form.validate = validate
    form.describe = describe
    form.apply = apply
    return form


def _rows(form) -> tuple:
    return tuple((str(record["index"]), record["name"], record["nd"], record["vd"],
                  record["formula"]) for record in matching(form))


def _select(form, index: int) -> str:
    shown = matching(form)
    if not shown:
        form.values["glass"] = ""
        form.summary = f"0 / {len(form.state['records'])} catalog glasses"
        return form.summary
    index = min(max(int(index), 0), len(shown) - 1)
    form.state["index"] = index
    form.values["glass"] = str(shown[index]["name"])
    form.summary = (f"{len(shown)} / {len(form.state['records'])} catalog glasses - "
                    f"{form.values['glass']} selected")
    return form.summary


def _refilter(form) -> str:
    """The filter changed: the list is a different list, so re-select its first row."""
    return _select(form, 0)


build_glass_catalog_form.TITLE = TITLE
