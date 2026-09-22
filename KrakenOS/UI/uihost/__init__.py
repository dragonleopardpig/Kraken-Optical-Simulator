"""Toolkit-neutral UI host -- the seam between KrakenOS's model/controller code and whichever
toolkit draws it (docs/design_qt_migration.md).

Model and controller code reaches the toolkit only through :func:`host_of`. Views (panels) stay
toolkit-specific and get a counterpart per toolkit instead of an abstraction.
"""
from __future__ import annotations

from KrakenOS.UI.uihost.base import UiHost
from KrakenOS.UI.uihost.scripted import ScriptedUiHost
from KrakenOS.UI.uihost.tk_host import TkUiHost

__all__ = ["UiHost", "TkUiHost", "ScriptedUiHost", "host_of"]


def host_of(owner) -> UiHost:
    """The UI host serving ``owner`` -- its ``ui`` attribute when it has one, otherwise a
    :class:`TkUiHost` wrapped around ``owner`` itself.

    The fallback is what keeps a converted call site behaving exactly as before on objects that
    predate the seam: guards bind real mixin methods onto small fakes, and a fake that stubbed
    ``after`` still gets its stub, because ``TkUiHost`` delegates scheduling to the object it
    wraps and dialogs to the tkinter modules, looked up at call time.
    """
    ui = getattr(owner, "ui", None)
    if isinstance(ui, UiHost):
        return ui
    editor = getattr(owner, "editor", None)
    ui = getattr(editor, "ui", None) if editor is not None else None
    if isinstance(ui, UiHost):
        return ui
    return TkUiHost(owner)
