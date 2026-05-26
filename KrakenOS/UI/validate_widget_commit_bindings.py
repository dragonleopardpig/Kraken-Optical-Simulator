"""Validate reusable Tk widget commit bindings without opening a display."""

from __future__ import annotations

import inspect
from tkinter import ttk

from KrakenOS.UI.widgets import (
    CommitCombobox,
    CommitEntry,
    bind_combobox_commit,
    bind_entry_commit,
    grid_labeled_commit_combobox,
    grid_labeled_commit_entry,
)


class FakeWidget:
    def __init__(self) -> None:
        self.bindings: list[tuple[str, object, str | None]] = []

    def bind(self, sequence: str, callback: object, add: str | None = None) -> str:
        self.bindings.append((sequence, callback, add))
        return f"{sequence}-id"


def _binding_sequences(widget: FakeWidget) -> list[str]:
    return [sequence for sequence, _callback, _add in widget.bindings]


def main() -> int:
    calls: list[tuple[str, object | None]] = []

    def _focus(event: object | None = None) -> None:
        calls.append(("focus", event))

    def _commit(event: object | None = None) -> None:
        calls.append(("commit", event))

    entry = FakeWidget()
    returned = bind_entry_commit(entry, _commit, on_focus_in=_focus)
    assert returned is entry
    assert _binding_sequences(entry) == ["<FocusIn>", "<FocusOut>", "<Return>", "<KP_Enter>"]
    assert all(add == "+" for _sequence, _callback, add in entry.bindings)

    combo = FakeWidget()
    bind_combobox_commit(combo, _commit, on_focus_in=_focus)
    assert _binding_sequences(combo) == [
        "<FocusIn>",
        "<<ComboboxSelected>>",
        "<Return>",
        "<KP_Enter>",
    ]

    combo_focus_out = FakeWidget()
    bind_combobox_commit(combo_focus_out, _commit, include_focus_out=True)
    assert _binding_sequences(combo_focus_out) == [
        "<<ComboboxSelected>>",
        "<Return>",
        "<KP_Enter>",
        "<FocusOut>",
    ]

    for _sequence, callback, _add in entry.bindings:
        callback("event")  # type: ignore[operator]
    assert calls == [
        ("focus", "event"),
        ("commit", "event"),
        ("commit", "event"),
        ("commit", "event"),
    ]

    commit_entry = FakeWidget()
    returned_commit_entry = CommitEntry.bind_commit(commit_entry, _commit, on_focus_in=_focus)
    assert returned_commit_entry is commit_entry
    assert _binding_sequences(commit_entry) == ["<FocusIn>", "<FocusOut>", "<Return>", "<KP_Enter>"]
    assert issubclass(CommitEntry, ttk.Entry)

    commit_combo = FakeWidget()
    returned_commit_combo = CommitCombobox.bind_commit(commit_combo, _commit, on_focus_in=_focus)
    assert returned_commit_combo is commit_combo
    assert _binding_sequences(commit_combo) == [
        "<FocusIn>",
        "<<ComboboxSelected>>",
        "<Return>",
        "<KP_Enter>",
    ]
    assert issubclass(CommitCombobox, ttk.Combobox)

    entry_helper_signature = inspect.signature(grid_labeled_commit_entry)
    assert "textvariable" in entry_helper_signature.parameters
    assert "on_commit" in entry_helper_signature.parameters
    assert "label_textvariable" in entry_helper_signature.parameters
    entry_helper_source = inspect.getsource(grid_labeled_commit_entry)
    assert "ttk.Label" in entry_helper_source
    assert "CommitEntry" in entry_helper_source
    assert "label_widget" in entry_helper_source
    assert "entry.grid" in entry_helper_source

    combo_helper_signature = inspect.signature(grid_labeled_commit_combobox)
    assert "textvariable" in combo_helper_signature.parameters
    assert "values" in combo_helper_signature.parameters
    assert "on_commit" in combo_helper_signature.parameters
    assert "combo_columnspan" in combo_helper_signature.parameters
    combo_helper_source = inspect.getsource(grid_labeled_commit_combobox)
    assert "ttk.Label" in combo_helper_source
    assert "CommitCombobox" in combo_helper_source
    assert "label_widget" in combo_helper_source
    assert "combo.grid" in combo_helper_source

    print("Widget commit binding validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
