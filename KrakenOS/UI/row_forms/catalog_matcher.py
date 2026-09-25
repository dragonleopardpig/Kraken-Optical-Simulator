"""The Camera + Lens Matcher record-list form (docs/design_qt_migration.md phase 3).

bugs/0634: enter the requirement -- the field of view, the resolution you need on it, a minimum
working distance and a wavelength -- and the matcher lists every registered camera x catalog lens
combination, passing ones first, with the reasons the others fail.

It REPORTS: there is nothing to write back, so `RowForm.read_only` drops Validate and Apply and
renames Cancel to Close. What it keeps is a verb -- Match -- because the first run scrapes the
lens datasheets and takes 10-20 s, which is not something to do on every keystroke.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormRefused, RecordList, RowForm

TITLE = "Camera + Lens Matcher"
NOTE = ("Enter the requirement, then Match. Every registered camera is tried against every "
        "catalog lens; passing combinations come first, and selecting a row explains it.")
COLUMNS = ("Camera", "Lens", "|m|", "WD mm", "Img circle", "f/#", "Result")
INPUTS = (("fov_w", "FOV W (mm)"), ("fov_h", "FOV H (mm)"), ("resolution_um", "Res (um/px)"),
          ("wd_min", "Min WD (mm)"), ("wavelength", "Wavelength (um)"))


def model(owner):
    """The matcher model, wherever the caller keeps it."""
    from types import SimpleNamespace

    from KrakenOS.UI.services import system_matcher
    from KrakenOS.UI.services.system_selection import gather_system_selection_prefill

    return SimpleNamespace(
        requirement=system_matcher.MatchRequirement,
        cameras=system_matcher.enumerate_cameras,
        lenses=system_matcher.enumerate_lenses,
        match=system_matcher.match_catalog,
        prefill=gather_system_selection_prefill,
    )


def build_catalog_matcher_form(owner, *_args, **_kwargs) -> RowForm:
    """The matcher over the registered cameras and the lens catalog."""
    parts = model(owner)
    fov, _sensor, _pixel = parts.prefill(owner)

    def prefilled(value) -> str:
        return f"{float(value):.6g}" if value else ""

    form = RowForm(
        title=TITLE,
        row_index=0,
        fields=tuple(FormField(key, label, kind="number", width=10) for key, label in INPUTS),
        note=NOTE,
        read_only=True,
        state={"owner": owner, "parts": parts, "results": [], "index": 0},
        records=RecordList(columns=COLUMNS, rows=_rows, select=_select),
    )
    form.values = {
        "fov_w": prefilled(fov[0] if fov else None),
        "fov_h": prefilled(fov[1] if fov else None),
        "resolution_um": "",
        "wd_min": "",
        "wavelength": "0.55",
    }
    form.summary = "Enter the requirement and click Match."
    form.actions = (FormAction("match", "Match", _match),)
    return form


def _positive(values: dict, key: str) -> "float | None":
    raw = str(values.get(key, "") or "").strip()
    if not raw:
        return None
    try:
        number = float(raw)
    except ValueError as exc:
        raise FormRefused("Enter a positive FOV width, height and resolution "
                          "(WD/wavelength optional).") from exc
    if number <= 0.0:
        raise FormRefused("Enter a positive FOV width, height and resolution "
                          "(WD/wavelength optional).")
    return number


def _format(value, digits: int = 4) -> str:
    return "—" if value is None else f"{float(value):.{digits}g}"


def _rows(form) -> tuple:
    rows = []
    for result in form.state["results"]:
        if result.lens_fnumber is None:
            fnumber = "—"
        elif result.max_nominal_fnumber is not None:
            fnumber = (f"f/{_format(result.lens_fnumber, 3)}"
                       f"<=f/{_format(result.max_nominal_fnumber, 3)}")
        else:
            fnumber = f"f/{_format(result.lens_fnumber, 3)}"
        rows.append((
            str(result.camera), str(result.lens), _format(result.magnification, 3),
            _format(result.working_distance_mm), _format(result.image_circle_mm), fnumber,
            "match" if result.passes else "no",
        ))
    return tuple(rows)


def _select(form, index: int) -> str:
    """Selecting a combination explains it -- why it passes, or every reason it does not."""
    results = form.state["results"]
    if not results:
        return form.summary
    index = min(max(int(index), 0), len(results) - 1)
    form.state["index"] = index
    result = results[index]
    if result.passes:
        note = ("" if result.fnumber_ok is not False else
                "  Note: lens f/# slower than the diffraction budget (advisory).")
        message = (f"MATCH {result.camera} + {result.lens}: "
                   f"|m|={result.magnification:.3g}, "
                   f"WD~{_format(result.working_distance_mm)} mm, image circle "
                   f"{_format(result.image_circle_mm)} mm.{note}")
    else:
        message = f"NO {result.camera} + {result.lens}: " + "; ".join(result.reasons)
    form.summary = message
    return message


def _match(form, _host) -> str:
    parts = form.state["parts"]
    values = dict(form.values)
    width = _positive(values, "fov_w")
    height = _positive(values, "fov_h")
    resolution = _positive(values, "resolution_um")
    if width is None or height is None or resolution is None:
        raise FormRefused("Enter a positive FOV width, height and resolution "
                          "(WD/wavelength optional).")
    wd_min = _positive(values, "wd_min")
    wavelength = _positive(values, "wavelength")
    try:
        requirement = parts.requirement(width, height, resolution, wd_min_mm=wd_min,
                                        wavelength_um=(wavelength or 0.55))
        cameras = parts.cameras()
        lenses = parts.lenses()
        results = parts.match(requirement, cameras, lenses)
    except Exception as exc:
        raise FormRefused(f"Match failed: {exc}") from exc
    form.state["results"] = list(results)
    form.state["index"] = 0
    passing = sum(1 for result in results if result.passes)
    message = (f"{passing} of {len(results)} combinations match "
               f"({len(cameras)} cameras x {len(lenses)} lenses). "
               "Select a row for details.")
    form.summary = message
    return message


build_catalog_matcher_form.TITLE = TITLE
