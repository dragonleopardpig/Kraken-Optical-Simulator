"""Show a form wherever the running shell shows forms -- without importing a toolkit to ask.

`present_row_form` is what a command that ends in a form calls (bugs/0944, 0947). It lived in the
Tk form view, `panels/row_form_view.py`, so every module that wanted to SHOW a form imported
tkinter with it: the dialog panels, and through them three services (bugs/0983). The Tk renderer
is imported here, at the moment a form is actually drawn by Tk.
"""
from __future__ import annotations

from typing import Any


def present_row_form(owner: Any, form, *, wraplength: int = 520, on_close=None, modal: bool = False,
                     geometry: "str | None" = None, wait: bool = False):
    """Show `form` wherever the running shell shows forms (bugs/0944).

    A shell that draws its own dialogs installs `show_row_form` on the editor -- the Qt shell,
    whose Tk root is withdrawn -- and gets the form; otherwise it is Tk's `render_row_form`. A
    command that ends in a form calls this, so it works in both shells unchanged.

    `geometry` ("1080x620") sizes the window and `wait` returns only once it has closed -- what
    callers did to the Tk window they got back, which a shell's dialog is not (bugs/0947).
    """
    editor = getattr(owner, "editor", None) or owner
    shell = editor.__dict__.get("show_row_form") if hasattr(editor, "__dict__") else None
    if callable(shell):
        return shell(form, on_close=on_close, modal=modal, geometry=geometry, wait=wait)
    from KrakenOS.UI.panels.row_form_view import render_row_form      # Tk draws: its view, now

    window = render_row_form(owner, form, wraplength=wraplength, on_close=on_close, modal=modal)
    if geometry:
        window.geometry(geometry)
    if wait:
        owner.wait_window(window)
    return window
