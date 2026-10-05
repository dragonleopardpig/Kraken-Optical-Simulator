"""The Tk window over a missing-CAD-assets session (bugs/0965).

What it does -- Locate, Locate folder..., Skip, Skip all remaining, Reset, and the rebuild when it
closes -- is `KrakenOS.UI.services.missing_assets_session.MissingAssetsSession`, shared with the Qt
window (`qt/dialogs/missing_assets_dialog.py`). This is the Tk view: a list of the session's entries
and its buttons. The layout load opens it NOT modal (bugs/0810), after the session has found what
it could by name (bugs/0965), and only when something is still missing.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Optional

from KrakenOS.UI.services.missing_assets_scan import MissingAsset
from KrakenOS.UI.services.missing_assets_session import MissingAssetsSession


class MissingAssetsDialog(tk.Toplevel):
    """Tk window that lists a session's missing assets and lets the user resolve them.

    ``session`` -- the `MissingAssetsSession` to show; or ``editor`` + ``assets`` (+ ``on_resolve``)
    to make one, as the callers before bugs/0965 did.
    """

    _COLUMNS = ("scope", "key", "path", "status")

    def __init__(
        self,
        parent: tk.Misc,
        *,
        editor: Any = None,
        assets: Optional[list[MissingAsset]] = None,
        on_resolve: Optional[Callable[[], None]] = None,
        session: Optional[MissingAssetsSession] = None,
    ) -> None:
        super().__init__(parent)
        self.session = session or MissingAssetsSession(editor, list(assets or []), on_resolve=on_resolve)
        self.editor = self.session.editor

        self.title(self.session.title)
        self.geometry("960x520")
        self.minsize(720, 360)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, padding=(12, 10, 12, 6), wraplength=920, text=self.session.prompt).grid(
            row=0, column=0, sticky="ew")

        frame = ttk.Frame(self, padding=(12, 0, 12, 6))
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(frame, columns=self._COLUMNS, show="headings", selectmode="browse")
        self._tree.heading("scope", text="Where")
        self._tree.heading("key", text="Reference")
        self._tree.heading("path", text="Expected path")
        self._tree.heading("status", text="Status")
        self._tree.column("scope", width=140, anchor="w", stretch=False)
        self._tree.column("key", width=180, anchor="w", stretch=False)
        self._tree.column("path", width=380, anchor="w", stretch=True)
        self._tree.column("status", width=100, anchor="w", stretch=False)
        self._tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=scrollbar.set)

        # located / skipped entries stand out even after the user scrolls past them
        self._tree.tag_configure("located", background="#d8f5d6")
        self._tree.tag_configure("skipped", background="#f5e2d6")

        # per-entry buttons act on the selected row; batch buttons on every still-missing entry, so
        # the user doesn't click through 18 of them when the cache is wiped on a fresh machine
        action_bar = ttk.Frame(self, padding=(12, 0, 12, 6))
        action_bar.grid(row=2, column=0, sticky="ew")
        action_bar.columnconfigure(7, weight=1)

        self._locate_btn = ttk.Button(action_bar, text="Locate...", command=self._on_locate_selected)
        self._locate_btn.grid(row=0, column=0, padx=(0, 6))
        self._skip_btn = ttk.Button(action_bar, text="Skip", command=self._on_skip_selected)
        self._skip_btn.grid(row=0, column=1, padx=(0, 6))
        self._reset_btn = ttk.Button(action_bar, text="Reset", command=self._on_reset_selected)
        self._reset_btn.grid(row=0, column=2, padx=(0, 18))
        ttk.Separator(action_bar, orient="vertical").grid(row=0, column=3, sticky="ns", padx=(0, 18))
        self._folder_btn = ttk.Button(action_bar, text="Locate folder...", command=self._on_locate_folder)
        self._folder_btn.grid(row=0, column=4, padx=(0, 6))
        self._skip_all_btn = ttk.Button(action_bar, text="Skip all remaining", command=self._on_skip_all)
        self._skip_all_btn.grid(row=0, column=5, padx=(0, 6))
        ttk.Button(action_bar, text="Continue", command=self._on_close).grid(row=0, column=8, padx=(18, 0), sticky="e")

        self._status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._status_var, padding=(12, 0, 12, 8)).grid(row=3, column=0, sticky="ew")

        self._populate()
        self._tree.bind("<Double-1>", self._on_tree_double_click)

    @classmethod
    def run(
        cls,
        parent: tk.Misc,
        *,
        editor: Any = None,
        assets: Optional[list[MissingAsset]] = None,
        on_resolve: Optional[Callable[[], None]] = None,
        modal: bool = True,
        session: Optional[MissingAssetsSession] = None,
    ) -> None:
        if session is None and not assets:
            return
        dialog = cls(parent, editor=editor, assets=assets, on_resolve=on_resolve, session=session)
        if not modal:
            # bugs/0810: the layout load does not wait here -- the session redraws on close
            return
        try:
            dialog.grab_set()
        except Exception:
            # grab_set can fail while the parent is not yet mapped (first open); the window still
            # works, it just doesn't lock the parent
            pass
        try:
            parent.wait_window(dialog)
        except Exception:
            pass

    # ---- the list ------------------------------------------------------------------------------
    def _populate(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for index, (where, key, path, status) in enumerate(self.session.rows()):
            tag = status if status in {"located", "skipped"} else ""
            self._tree.insert("", "end", iid=str(index), values=(where, key, path, status),
                              tags=(tag,) if tag else ())
        self._status_var.set(self.session.summary())

    def _selected_index(self) -> Optional[int]:
        selection = self._tree.selection()
        if not selection:
            return None
        try:
            return int(selection[0])
        except (TypeError, ValueError):
            return None

    # ---- the buttons ---------------------------------------------------------------------------
    def _on_tree_double_click(self, _event: tk.Event) -> None:
        self._on_locate_selected()

    def _on_locate_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Select a row", "Pick a row in the list first.", parent=self)
            return
        initial_dir = self.session.initial_dir(index)
        path = filedialog.askopenfilename(
            title=f"Locate file for {self.session.assets[index].short_label()}",
            initialdir=str(initial_dir) if initial_dir else "",
            filetypes=self.session.file_types,
            parent=self,
        )
        if not path:
            return
        problem = self.session.locate(index, path)
        if problem:
            messagebox.showerror("Not located", problem, parent=self)
        self._populate()

    def _on_skip_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Select a row", "Pick a row in the list first.", parent=self)
            return
        self.session.skip(index)
        self._populate()

    def _on_reset_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        self.session.reset(index)
        self._populate()

    def _on_locate_folder(self) -> None:
        directory = filedialog.askdirectory(
            title="Pick a folder that contains the missing STEP / STL files", parent=self)
        if not directory:
            return
        _matched, message = self.session.locate_folder(directory)
        self._populate()
        if message:
            messagebox.showinfo("No matches", message, parent=self)

    def _on_skip_all(self) -> None:
        self.session.skip_all()
        self._populate()

    def _on_close(self) -> None:
        self.session.close()
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
