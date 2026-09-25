"""Row forms: a dialog that edits ONE surface row (docs/design_qt_migration.md phase 3).

The sixth dialog family, and the shape most of the remaining 53 take -- Coating/Material,
Advanced Surface, Diffuse/BRDF, Error Map, the CAD face-roles editor: pick a row, show its
settings, validate them, write them back.

Only the LAYOUT differs between toolkits, so a form declares its fields and hands over three
callables the model owns: read the row, validate a candidate, apply it. A refusal ("select a row
first", "this is not a beam splitter") is a `FormRefused` carrying the message to show.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class FormRefused(Exception):
    """The form cannot open, or cannot apply, and says why."""


@dataclass(frozen=True)
class FormField:
    """One editable value. ``kind`` is what a view needs to pick a widget."""

    key: str
    label: str
    kind: str = "number"  # number | int | bool | choice | text | textarea | static
    choices: tuple[str, ...] = ()
    hint: str = ""
    width: int = 14
    #: rows of a textarea; ignored by the other kinds
    height: int = 8
    #: the tab this field belongs to; a form whose fields carry groups is laid out in tabs
    group: str = ""
    #: a field the model will not accept edits to (a literal it cannot parse back, a shape
    #: parameter on an Object/Image row) is shown but not editable
    enabled: bool = True
    #: a `choice` the user may also TYPE into -- the list is a convenience, not the whole domain
    #: (a parent splitter may name an element the current scene does not hold yet)
    editable: bool = False
    #: called with (form, new value) when this field changes, for a field that rewrites ANOTHER
    #: one -- a coating preset filling the table, a catalog choice setting the metal index.
    #: Returns the message to show; the view refreshes from the form afterwards.
    on_change: "Callable[[Any, str], str] | None" = None


@dataclass(frozen=True)
class FormAction:
    """A button that runs model code and may change what the form shows.

    `run(form, host)` returns the message to display. It may rewrite `form.values`, `form.summary`
    and `form.state` -- the view refreshes from them afterwards -- and asks the user for anything
    it needs (a file, a confirmation) through the UI HOST, so the same action works in both
    toolkits. It raises `FormRefused` when it will not proceed.
    """

    key: str
    label: str
    run: Callable[[Any, Any], str] = lambda _form, _host: ""


@dataclass(frozen=True)
class FormPreview:
    """A small picture the MODEL draws from its own numbers (docs/design_qt_migration.md).

    bugs/0828 replaced a dense explanatory paragraph in the Inspection Part dialog with a picture
    of the part at true proportions, because "a dense sentence does not attach to the fields above
    it". The picture is model data -- polygons and a derivation chain computed from the typed
    dimensions -- so it belongs here rather than in either toolkit: `shapes(form, values)` returns
    what to draw and `caption(form, values)` the text beside it, and both views redraw on every
    keystroke so the consequence of a number is visible BEFORE Apply.

    A shape is a dict: {"kind": "polygon", "points": [(x, y), ...], "fill": "#rrggbb",
    "outline": "#rrggbb"} or {"kind": "text", "x": .., "y": .., "text": "..", "fill": "#rrggbb",
    "size": 7}. Coordinates are pixels inside (width, height), so the model decides the layout
    and neither view has to.
    """

    width: int = 210
    height: int = 150
    shapes: Callable[[Any, dict], tuple] = lambda _form, _values: ()
    caption: Callable[[Any, dict], str] = lambda _form, _values: ""


@dataclass(frozen=True)
class FormFigure:
    """A matplotlib figure the MODEL draws into (docs/design_qt_migration.md phase 3/6).

    `FormPreview` covers a picture with no dependencies -- polygons and text. A few dialogs need
    a real plot instead (an imshow of the sag map with a colorbar, an aperture footprint), and
    matplotlib already has a canvas for both toolkits. So the model draws INTO a figure the view
    supplies -- the view owns the canvas and its lifecycle -- and `draw` returns the status line
    to show, which is where a validation warning about the drawn candidate belongs.
    """

    width: float = 7.2
    height: float = 5.4
    dpi: int = 100
    #: form, values, figure -> the status line; the view clears the figure first
    draw: Callable[[Any, dict, Any], str] = lambda _form, _values, _figure: ""


@dataclass(frozen=True)
class RecordList:
    """A master list whose selected item the form edits (docs/design_qt_migration.md phase 3).

    The seventh dialog family. A row form edits ONE record; a record-list form also owns the
    collection it comes from -- add, duplicate, delete, reorder -- and applies the whole list at
    once. The list itself is model data: the view draws `columns` and `rows(form)`, and tells the
    model which item the user picked by calling `select(form, index)`, which rewrites
    `form.values` and returns the line to show.
    """

    columns: tuple[str, ...]
    #: form -> one tuple of display strings per record, in list order
    rows: Callable[[Any], tuple] = lambda _form: ()
    #: form, index -> the message to show; rewrites form.values for the newly selected record
    select: Callable[[Any, int], str] = lambda _form, _index: ""
    #: the `form.state` key holding the selected index
    selected_key: str = "index"


@dataclass
class RowForm:
    """Everything a row-editing dialog shows and does."""

    title: str
    row_index: int
    fields: tuple[FormField, ...] = ()
    #: the row's current values, as text, keyed by field
    values: dict[str, str] = field(default_factory=dict)
    #: a line describing the current settings
    summary: str = ""
    #: candidate values -> the model's own error messages ([] when valid)
    validate: Callable[[dict[str, str]], list[str]] = lambda _values: []
    #: candidate values -> the status line; raises FormRefused when it will not apply
    apply: Callable[[dict[str, str]], str] = lambda _values: ""
    #: what a view should say when validation passes
    describe: Callable[[dict[str, str]], str] = lambda _values: ""
    #: buttons beyond Validate / Apply / Cancel -- Import, Clear, Browse...
    actions: tuple = ()
    #: whatever the actions need to carry between themselves and apply (a loaded file's data)
    state: dict = field(default_factory=dict)
    #: live choice lists, when an action grows one (a metal catalog just loaded)
    choices: dict = field(default_factory=dict)
    #: live LABEL overrides -- the same field means a different number under a different choice
    #: ("Focal length [mm]" for a thin lens, "Radius of curvature [mm]" for a refracting one).
    #: Views read `label_for(key)`, never `field.label`.
    labels: dict = field(default_factory=dict)
    #: the collection this form edits one item of, when it edits a list rather than a row
    records: "RecordList | None" = None
    #: a picture the model draws from the values as they are typed
    preview: "FormPreview | None" = None
    #: a matplotlib figure the model draws into, when a plot is what explains the values
    figure: "FormFigure | None" = None
    #: fields the form has locked SINCE it was built -- `FormField.enabled` is the static answer
    #: (a value the model will never take edits to), this is the live one (a role choice that
    #: turns the detector fields off). Views ask `is_enabled(key)`, never `field.enabled`.
    locked: set = field(default_factory=set)
    note: str = ""

    def field(self, key: str) -> "FormField | None":
        return next((item for item in self.fields if item.key == key), None)

    @property
    def groups(self) -> tuple:
        """The tabs this form wants, in field order; empty when it is a single page."""
        seen: list = []
        for item in self.fields:
            if item.group and item.group not in seen:
                seen.append(item.group)
        return tuple(seen)

    def fields_in(self, group: str) -> tuple:
        return tuple(item for item in self.fields if item.group == group)

    def label_for(self, key: str) -> str:
        """The label a view should show NOW -- a choice may have renamed the field."""
        if key in self.labels:
            return str(self.labels[key])
        found = self.field(key)
        return str(found.label) if found is not None else key

    def is_enabled(self, key: str) -> bool:
        """Whether a view should accept edits to this field NOW."""
        found = self.field(key)
        return bool(found is not None and found.enabled) and key not in self.locked

    def lock(self, *keys: str, locked: bool = True) -> None:
        """Lock or unlock fields -- what an `on_change` calls to follow its own choice."""
        for key in keys:
            if locked:
                self.locked.add(key)
            else:
                self.locked.discard(key)

    @property
    def selected_index(self) -> int:
        """Which record the form is editing; 0 for a form that edits a single row."""
        if self.records is None:
            return 0
        try:
            return int(self.state.get(self.records.selected_key, 0))
        except Exception:
            return 0

    def choices_for(self, key: str) -> tuple:
        """The choices a view should offer NOW -- an action may have grown the list."""
        if key in self.choices:
            return tuple(self.choices[key])
        found = self.field(key)
        return tuple(found.choices) if found is not None else ()
