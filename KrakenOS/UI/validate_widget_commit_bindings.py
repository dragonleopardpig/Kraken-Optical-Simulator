"""Validate reusable Tk widget commit bindings without opening a display."""

from __future__ import annotations

from KrakenOS.UI.widgets import bind_combobox_commit, bind_entry_commit


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

    print("Widget commit binding validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
