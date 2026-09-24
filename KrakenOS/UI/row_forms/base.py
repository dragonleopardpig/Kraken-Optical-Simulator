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
    kind: str = "number"  # number | int | choice | text | textarea | static
    choices: tuple[str, ...] = ()
    hint: str = ""
    width: int = 14
    #: rows of a textarea; ignored by the other kinds
    height: int = 8


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
    note: str = ""

    def field(self, key: str) -> "FormField | None":
        return next((item for item in self.fields if item.key == key), None)
