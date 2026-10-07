"""Lens drawing surface-property and PDF export dialogs."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import webbrowser

import numpy as np

from KrakenOS.UI.lens_drawing_export import export_lens_drawing
from KrakenOS.UI.lens_drawing_session import (MESSAGE_TITLE, NO_LENSES, LensDrawingPropertiesSession,
                                              has_lens_elements)
from KrakenOS.UI.uihost import host_of


class MainLensDrawingDialogs:
    """Own lens fabrication drawing dialogs while delegating row state to the editor."""

    def __init__(self, editor: Any, *, screenshot_dir: Path) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "screenshot_dir", Path(screenshot_dir))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "screenshot_dir"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _open_lens_drawing_surface_properties_dialog(self, *, for_export: bool = False) -> bool:
        """The surface-properties dialog; True when the caller may go on (bugs/0945: the state and
        actions are `lens_drawing_session`, shown by the Qt shell's dialog or by Tk's window)."""
        if not has_lens_elements(self.rows):
            host_of(self).showinfo(MESSAGE_TITLE, NO_LENSES, parent=self.editor)
            return False
        session = LensDrawingPropertiesSession(self, for_export=for_export, screenshot_dir=self.screenshot_dir)
        if not session.surface_indices:
            return True
        shell = self.editor.__dict__.get("show_lens_drawing_properties")
        if callable(shell):
            shell(session)          # modal: returns once the session is closed
        else:
            self._show_tk_lens_drawing_properties(session)
        return bool(session.result_ok)

    def _show_tk_lens_drawing_properties(self, session: LensDrawingPropertiesSession) -> None:
        """Tk draws: its window is `panels/lens_drawing_properties_view.py`, imported now (bugs/0986)."""
        from KrakenOS.UI.panels.lens_drawing_properties_view import show_tk_lens_drawing_properties

        show_tk_lens_drawing_properties(self, session)

    def export_lens_drawing(self) -> None:
        """Export an ISO 10110-style lens fabrication drawing as PDF."""
        self._commit_pending_table_edit()
        self._read_rows_from_table()
        if not self._open_lens_drawing_surface_properties_dialog(for_export=True):
            self.status_var.set("Lens drawing export cancelled.")
            return
        # Determine default filename from current layout
        stem = "lens_drawing"
        if self.current_layout_file:
            stem = self.current_layout_file.stem + "_drawing"
        try:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        # asks and reports through the UI host, so the Qt shell exports too (bugs/0945)
        path = host_of(self).asksaveasfilename(
            title="Export Lens Drawing (PDF)",
            initialdir=str(self.screenshot_dir),
            initialfile=f"{stem}.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            parent=self.editor,
        )
        if not path:
            return
        try:
            # Gather EFL/BFL from paraxial cardinals if computable
            efl = None
            bfl = None
            try:
                effl_val, ppa_val, ppp_val = self._exact_paraxial_cardinals()
                if np.isfinite(effl_val):
                    efl = float(effl_val)
                    # BFL = distance from last optical surface to rear focal point
                    # Approximate: effl + ppp (principal plane offset from last surface)
                    bfl_val = effl_val + ppp_val
                    if np.isfinite(bfl_val):
                        bfl = float(bfl_val)
            except Exception:
                pass
            title = ""
            if self.current_layout_file:
                title = self.current_layout_file.stem.replace("_", " ").title()
            elif hasattr(self, "layout_var"):
                sel = self.layout_var.get()
                if sel and sel != "Common Optical Layout":
                    title = sel
            if not title:
                title = "Lens Drawing"
            export_lens_drawing(
                self.rows, path, title=title,
                dwg_no=stem.upper(),
                efl=efl, bfl=bfl,
            )
            self.status_var.set(f"Lens drawing exported: {Path(path).name}")
            # Open the PDF
            webbrowser.open(str(Path(path).resolve()))
        except ValueError as exc:
            host_of(self).showwarning("Export", str(exc), parent=self.editor)
        except Exception as exc:
            host_of(self).showerror("Export Error",
                                    f"Failed to export lens drawing:\n{exc}",
                                    parent=self.editor)
