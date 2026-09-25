"""The analysis picker and Update in Qt (docs/design_qt_migration.md phase 6).

The Qt shell could open every dialog and, since 0898, show every result -- but it could not set
an analysis up: the 24 plots, their grouping and their tooltips were literals inside the Tk
toolbar's `build()`. They are `KrakenOS/UI/analysis_modes.py` now, so this is layout only.

Ticking a plot calls the model's own `toggle_analysis_mode`, and the model answers through
`show_analysis_modes(modes, caption)` -- the same seam the Tk button's caption comes from -- so
neither shell decides what is selected.
"""
from __future__ import annotations

from KrakenOS.UI.analysis_modes import MODE_GROUPS, MODE_TOOLTIPS, PICKER_HINT, mode_label


class AnalysisToolbar:
    """A "Select plots" menu over the model's modes, an Update button, and WFront 3D."""

    def __init__(self, main_window) -> None:
        from PySide6.QtWidgets import QToolBar, QToolButton

        self.main_window = main_window
        self.editor = main_window.editor
        self.actions: dict = {}

        self.toolbar = QToolBar("Analysis", main_window)
        self.toolbar.setObjectName("AnalysisToolBar")

        self.button = QToolButton()
        self.button.setText("Select plots")
        self.button.setToolTip(PICKER_HINT)
        self.button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu = self._build_menu()
        self.button.setMenu(self.menu)
        self.toolbar.addWidget(self.button)

        self.update_action = self.toolbar.addAction("Update")
        self.update_action.setToolTip("Run the selected analyses and redraw")
        self.update_action.triggered.connect(self.run_update)

        self.wavefront_action = self.toolbar.addAction("WFront 3D")
        self.wavefront_action.setToolTip(
            "Open the latest Wavefront analysis as a real, rotatable 3D surface. "
            "Run the Wavefront plot first.")
        self.wavefront_action.triggered.connect(self.open_wavefront_3d)

        main_window.addToolBar(self.toolbar)
        self.editor.show_analysis_modes = self.show_analysis_modes
        self.show_analysis_modes(list(getattr(self.editor, "selected_analysis_modes", [])),
                                 None)

    def _build_menu(self):
        """One checkable entry per plot, separated exactly as the picker groups them.

        A Qt menu closes on every click by default; `setMenuStayOpenOnClick`-style behaviour is
        what the Tk dropdown was hand-rolled for, so the same multi-select works here.
        """
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self.main_window)
        for index, group in enumerate(MODE_GROUPS):
            if index:
                menu.addSeparator()
            for caption, mode in group:
                action = menu.addAction(f"{caption} — {mode_label(mode)}")
                action.setCheckable(True)
                action.setToolTip(MODE_TOOLTIPS.get(mode, ""))
                action.triggered.connect(
                    lambda _checked=False, mode=mode: self.toggle(mode))
                self.actions[mode] = action
        menu.setToolTipsVisible(True)
        # keep the menu up across ticks, as the Tk dropdown does
        menu.triggered.connect(lambda _action: menu.show())
        return menu

    # ---- model -> view ---------------------------------------------------------------------
    def show_analysis_modes(self, modes, caption=None) -> None:
        """The model's selection changed: tick what it says and read back its own caption."""
        selected = set(modes or [])
        for mode, action in self.actions.items():
            if action.isChecked() != (mode in selected):
                action.blockSignals(True)
                try:
                    action.setChecked(mode in selected)
                finally:
                    action.blockSignals(False)
        if caption is None:
            from KrakenOS.UI.analysis_modes import selection_label

            caption = selection_label(len(selected))
        # the arrow is the Tk button's own; Qt draws its own menu indicator
        self.button.setText(str(caption).replace("▾", "").strip())

    # ---- view -> model ---------------------------------------------------------------------
    def toggle(self, mode: str) -> None:
        self.editor.toggle_analysis_mode(mode)

    def run_update(self) -> None:
        """What the Tk Update button does: commit, run the selected analyses, redraw."""
        self.editor._manual_update_plot()
        self.main_window.refresh_from_model()

    def open_wavefront_3d(self) -> None:
        self.editor.open_wavefront_3d_view()

    def selected(self) -> list:
        """What the menu is showing as ticked -- what a guard compares."""
        return sorted(mode for mode, action in self.actions.items() if action.isChecked())
