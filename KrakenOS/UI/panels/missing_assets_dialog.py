"""Modal that surfaces missing STEP / STL references after layout load.

The dialog lists every reference returned by
:func:`KrakenOS.UI.services.missing_assets_scan.scan_missing_assets` and
gives the user three exits per entry:

* **Locate...** -- open a per-entry file picker. On success, the row's
  ``advanced`` dict is rewritten in place to point at the chosen file
  (the layout is marked dirty so a later Save persists the new path).
* **Locate folder...** -- one click resolves every unresolved entry
  whose basename appears under the selected directory tree. The match
  is by basename only so the user can drop files in arbitrary
  subdirectories without renaming.
* **Skip** -- record the key in :data:`MISSING_RESOURCE_STATE_ATTR` so
  the renderer draws a placeholder for the row instead of silently
  falling back to a single-face analytic mesh. The scanner will not
  surface the entry again until the user clears the skip.

The dialog returns nothing -- it mutates the rows in place and the
caller refreshes the table afterward.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Optional

from KrakenOS.UI.services.missing_assets_scan import (
    MissingAsset,
    clear_row_skip,
    mark_row_skipped,
    relocate_advanced_path,
)


# Limit the folder-scan walk depth so a 100k-file Desktop folder doesn't
# freeze the UI. Users typically point the picker at the catalog root
# (e.g. attachment/Lens/) which has < 200 files within 3-4 levels deep.
_FOLDER_SCAN_MAX_DEPTH = 6
_FOLDER_SCAN_MAX_FILES = 50_000


class MissingAssetsDialog(tk.Toplevel):
    """Tk modal that lists missing assets and lets the user resolve them.

    Constructor parameters:

    * ``parent`` -- a Tk window (usually the layout editor) to anchor
      the modal on.
    * ``editor`` -- the layout editor instance. Used for two things:
      reading rows to mutate their ``advanced`` dicts in place, and
      writing relocated ``imported_*_step_path`` attributes back.
    * ``assets`` -- the result of :func:`scan_missing_assets`.
    * ``on_resolve`` -- optional callback invoked once with no
      arguments after the user closes the dialog. The layout-load path
      uses this to mark the layout dirty and re-run the scanner so the
      table reflects the new paths.
    """

    _COLUMNS = ("scope", "key", "path", "status")

    def __init__(
        self,
        parent: tk.Misc,
        *,
        editor: Any,
        assets: list[MissingAsset],
        on_resolve: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.editor = editor
        self._assets = list(assets)
        self._on_resolve = on_resolve
        # Per-entry status: "missing" | "located" | "skipped".
        # Mirrors the dict-backed source of truth on each row so the
        # tree view can repaint without re-running the full scan.
        self._status: list[str] = ["missing"] * len(self._assets)

        self.title("Missing CAD assets")
        self.geometry("960x520")
        self.minsize(720, 360)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        intro = ttk.Label(
            self,
            padding=(12, 10, 12, 6),
            wraplength=920,
            text=(
                "This layout references files that are not on disk. The "
                "renderer would otherwise silently fall back to a partial "
                "drawing of each affected row (a half-sphere instead of a "
                "ball lens, a flat disc instead of a meniscus, and so on).\n\n"
                "Choose Locate to point at the file directly, Locate "
                "folder... to batch-match by basename across a directory "
                "tree, or Skip to render an explicit \"missing asset\" "
                "placeholder for the row."
            ),
        )
        intro.grid(row=0, column=0, sticky="ew")

        frame = ttk.Frame(self, padding=(12, 0, 12, 6))
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            frame,
            columns=self._COLUMNS,
            show="headings",
            selectmode="browse",
        )
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

        # Color tags so located / skipped entries stand out even after
        # the user scrolls past them.
        self._tree.tag_configure("located", background="#d8f5d6")
        self._tree.tag_configure("skipped", background="#f5e2d6")

        # Bottom button row. Per-entry buttons act on the currently
        # selected tree row; batch buttons act on every still-missing
        # entry, so the user doesn't have to click through 18 of them
        # when the cache is wiped on a fresh machine.
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

        self._folder_btn = ttk.Button(
            action_bar,
            text="Locate folder...",
            command=self._on_locate_folder,
        )
        self._folder_btn.grid(row=0, column=4, padx=(0, 6))
        self._skip_all_btn = ttk.Button(action_bar, text="Skip all remaining", command=self._on_skip_all)
        self._skip_all_btn.grid(row=0, column=5, padx=(0, 6))

        close_btn = ttk.Button(action_bar, text="Continue", command=self._on_close)
        close_btn.grid(row=0, column=8, padx=(18, 0), sticky="e")

        # Status line summarising the dialog as a whole so a glance at
        # the bottom of the window tells the user how much is left.
        self._status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._status_var, padding=(12, 0, 12, 8)).grid(
            row=3, column=0, sticky="ew"
        )

        self._populate()
        self._refresh_status_line()
        self._tree.bind("<Double-1>", self._on_tree_double_click)

    # ------------------------------------------------------------------
    # Modal entry point used by the layout-load hook. Keeping it as a
    # classmethod means callers don't have to remember to call
    # ``grab_set`` / ``wait_window`` themselves.
    # ------------------------------------------------------------------

    @classmethod
    def run(
        cls,
        parent: tk.Misc,
        *,
        editor: Any,
        assets: list[MissingAsset],
        on_resolve: Optional[Callable[[], None]] = None,
    ) -> None:
        if not assets:
            return
        dialog = cls(parent, editor=editor, assets=assets, on_resolve=on_resolve)
        try:
            dialog.grab_set()
        except Exception:
            # ``grab_set`` can fail when the parent isn't yet mapped
            # (e.g. on first-open). Fall through to ``wait_window`` --
            # the dialog still functions, it just doesn't lock the
            # parent. This keeps the load path from blowing up during
            # startup races.
            pass
        try:
            parent.wait_window(dialog)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Tree population / status tracking.
    # ------------------------------------------------------------------

    def _populate(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for index, asset in enumerate(self._assets):
            scope = "Layout row" if asset.scope == "row" else "Loaded overlay"
            label_prefix = asset.label or asset.short_label()
            if asset.scope == "row":
                where = f"Row {asset.row_index} {label_prefix}"
            else:
                where = "Overlay import"
            status = self._status[index]
            tag = status if status in {"located", "skipped"} else ""
            self._tree.insert(
                "",
                "end",
                iid=str(index),
                values=(where, asset.key, str(asset.expected_path), status),
                tags=(tag,) if tag else (),
            )

    def _refresh_status_line(self) -> None:
        located = sum(1 for s in self._status if s == "located")
        skipped = sum(1 for s in self._status if s == "skipped")
        missing = sum(1 for s in self._status if s == "missing")
        self._status_var.set(
            f"{missing} unresolved   |   {located} located   |   {skipped} skipped"
        )

    def _selected_index(self) -> Optional[int]:
        selection = self._tree.selection()
        if not selection:
            return None
        try:
            return int(selection[0])
        except (TypeError, ValueError):
            return None

    def _set_status(self, index: int, status: str) -> None:
        if not (0 <= index < len(self._status)):
            return
        self._status[index] = status
        item_id = str(index)
        asset = self._assets[index]
        tag = status if status in {"located", "skipped"} else ""
        # Re-fetch the path because Locate may have rewritten it.
        path_value = str(self._resolved_path_for(asset))
        self._tree.item(
            item_id,
            values=(self._tree.set(item_id, "scope"), asset.key, path_value, status),
            tags=(tag,) if tag else (),
        )

    def _resolved_path_for(self, asset: MissingAsset) -> Path:
        """Re-read the on-disk path for an asset after a relocate."""
        if asset.scope == "editor":
            value = getattr(self.editor, asset.key, None)
            if value is not None:
                try:
                    return Path(str(value)).expanduser()
                except Exception:
                    pass
            return asset.expected_path
        try:
            row = self.editor.rows[asset.row_index]
        except Exception:
            return asset.expected_path
        advanced = getattr(row, "advanced", None) or {}
        key = asset.key
        if "." in key:
            outer, _, inner = key.partition(".")
            nested = advanced.get(outer)
            if isinstance(nested, dict):
                value = nested.get(inner)
                if isinstance(value, str) and value:
                    return Path(value).expanduser()
        else:
            value = advanced.get(key)
            if isinstance(value, str) and value:
                return Path(value).expanduser()
        return asset.expected_path

    # ------------------------------------------------------------------
    # Per-entry actions.
    # ------------------------------------------------------------------

    def _on_tree_double_click(self, _event: tk.Event) -> None:
        self._on_locate_selected()

    def _on_locate_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Select a row", "Pick a row in the list first.", parent=self)
            return
        self._locate(index)

    def _on_skip_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Select a row", "Pick a row in the list first.", parent=self)
            return
        self._skip(index)

    def _on_reset_selected(self) -> None:
        """Undo a previous Locate / Skip for the selected entry.

        Restores the entry to ``missing`` state. Used when the user
        clicks the wrong button or wants to try a different file.
        """
        index = self._selected_index()
        if index is None:
            return
        asset = self._assets[index]
        if asset.scope == "row":
            try:
                row = self.editor.rows[asset.row_index]
                advanced = getattr(row, "advanced", None) or {}
                clear_row_skip(advanced, asset.key)
            except Exception:
                pass
        self._set_status(index, "missing")
        self._refresh_status_line()

    def _on_locate_folder(self) -> None:
        directory = filedialog.askdirectory(
            title="Pick a folder that contains the missing STEP / STL files",
            parent=self,
        )
        if not directory:
            return
        root = Path(directory).expanduser()
        if not root.is_dir():
            return
        # Build a basename → path index up-front so we don't re-walk the
        # tree once per asset. Walk is bounded to keep the UI responsive
        # against accidental Desktop / Home selections.
        try:
            index_by_basename = self._index_folder(root)
        except Exception as exc:
            messagebox.showerror(
                "Folder scan failed",
                f"Could not scan {root}:\n{exc}",
                parent=self,
            )
            return
        matched = 0
        for index, asset in enumerate(self._assets):
            if self._status[index] != "missing":
                continue
            basename = asset.expected_path.name
            candidate = index_by_basename.get(basename.lower())
            if candidate is None:
                continue
            if self._apply_relocation(index, candidate):
                matched += 1
        self._refresh_status_line()
        if matched == 0:
            messagebox.showinfo(
                "No matches",
                (
                    f"Scanned {root}\n\nNo unresolved entries matched a file in "
                    "that tree by basename. Try a directory closer to the "
                    "vendor catalog (e.g. attachment/Lens) or pick each "
                    "entry individually with Locate..."
                ),
                parent=self,
            )

    def _on_skip_all(self) -> None:
        for index, status in enumerate(self._status):
            if status == "missing":
                self._skip(index)

    def _on_close(self) -> None:
        if self._on_resolve is not None:
            try:
                self._on_resolve()
            except Exception:
                pass
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    # ------------------------------------------------------------------
    # Mutation helpers.
    # ------------------------------------------------------------------

    def _locate(self, index: int) -> None:
        asset = self._assets[index]
        initial_dir = self._initial_dir_for(asset)
        path = filedialog.askopenfilename(
            title=f"Locate file for {asset.short_label()}",
            initialdir=str(initial_dir) if initial_dir else "",
            filetypes=[
                ("CAD/STL", "*.step *.stp *.stl *.STEP *.STP *.STL"),
                ("All files", "*"),
            ],
            parent=self,
        )
        if not path:
            return
        self._apply_relocation(index, Path(path).expanduser())

    def _skip(self, index: int) -> None:
        asset = self._assets[index]
        if asset.scope == "row":
            try:
                row = self.editor.rows[asset.row_index]
            except Exception:
                row = None
            if row is not None:
                advanced = getattr(row, "advanced", None)
                if not isinstance(advanced, dict):
                    advanced = {}
                    setattr(row, "advanced", advanced)
                mark_row_skipped(advanced, asset.key, expected_path=asset.expected_path)
        self._set_status(index, "skipped")
        self._refresh_status_line()

    def _apply_relocation(self, index: int, new_path: Path) -> bool:
        asset = self._assets[index]
        if not new_path.exists() or not new_path.is_file():
            messagebox.showerror(
                "Not a file",
                f"{new_path}\nis not a regular file. Pick the actual STEP / STL.",
                parent=self,
            )
            return False
        if asset.scope == "editor":
            try:
                setattr(self.editor, asset.key, new_path)
            except Exception as exc:
                messagebox.showerror(
                    "Update failed",
                    f"Could not assign {asset.key} = {new_path}\n{exc}",
                    parent=self,
                )
                return False
            self._set_status(index, "located")
            self._refresh_status_line()
            return True
        try:
            row = self.editor.rows[asset.row_index]
        except Exception as exc:
            messagebox.showerror(
                "Update failed",
                f"Could not find row {asset.row_index}: {exc}",
                parent=self,
            )
            return False
        advanced = getattr(row, "advanced", None)
        if not isinstance(advanced, dict):
            advanced = {}
            setattr(row, "advanced", advanced)
        if relocate_advanced_path(advanced, asset.key, new_path):
            clear_row_skip(advanced, asset.key)
        # bugs/0021: relocating a source STEP regenerates its derived body-STL
        # cache so the user doesn't have to re-run Promote -- both the analytic
        # body (StepAnalyticBodyStlPath) and the file-backed optical solid
        # (Solid_3d_stl). In most cases the cache was simply never synced (a
        # fresh machine, or it lived in ~/.cache) and the source STEP is the
        # only thing the user needs to re-supply.
        if asset.key.endswith(".source_step_path"):
            self._maybe_regenerate_body_stl(
                asset.row_index, advanced, new_path, body_key="StepAnalyticBodyStlPath"
            )
        elif asset.key == "OpticalSolidSourcePath":
            self._maybe_regenerate_body_stl(
                asset.row_index, advanced, new_path, body_key="Solid_3d_stl"
            )
        self._set_status(index, "located")
        self._refresh_status_line()
        return True

    def _maybe_regenerate_body_stl(
        self,
        row_index: int,
        advanced: dict,
        source_step_path: Path,
        *,
        body_key: str = "StepAnalyticBodyStlPath",
    ) -> None:
        """Best-effort body-STL regeneration after a source STEP relocate.

        Rebuilds the derived ``body_key`` cache -- the analytic
        ``StepAnalyticBodyStlPath`` or the file-backed optical-solid
        ``Solid_3d_stl`` -- from the relocated source STEP. Silently no-ops on
        any failure: the relocate already succeeded, and a still-missing cache
        just keeps the row's placeholder. The rebuilt path is stored
        project-relative (bugs/0021) so it stays portable across machines.
        """
        body_stl_value = advanced.get(body_key)
        if not isinstance(body_stl_value, str) or not body_stl_value:
            return
        # Skip when the current cache is already on disk -- nothing to rebuild.
        try:
            from KrakenOS.UI.layout_editor import _resolve_project_file_path

            if _resolve_project_file_path(body_stl_value).exists():
                return
        except Exception:
            try:
                if Path(body_stl_value).expanduser().exists():
                    return
            except Exception:
                return
        label = "optical"
        optical_axis: Optional[tuple[float, float, float]] = None
        # The file-backed Solid_3d_stl body is cached WITHOUT the optical-axis
        # +Z re-orientation; only the analytic body carries one. Read the label
        # from whichever promotion dict the row has.
        for promo_key in ("StepOverlayPromotion", "StepAnalyticPromotion"):
            promotion = advanced.get(promo_key)
            if not isinstance(promotion, dict):
                continue
            label_value = promotion.get("step_label")
            if isinstance(label_value, str) and label_value.strip():
                label = label_value.strip().lower()
            if body_key == "StepAnalyticBodyStlPath":
                axis_value = promotion.get("optical_axis")
                if isinstance(axis_value, (list, tuple)) and len(axis_value) == 3:
                    try:
                        optical_axis = (
                            float(axis_value[0]),
                            float(axis_value[1]),
                            float(axis_value[2]),
                        )
                    except Exception:
                        optical_axis = None
        try:
            service = self.editor._step_overlay_promotion_service()
        except Exception:
            return
        try:
            new_stl_path = service.regenerate_promoted_body_stl_from_source(
                source_step_path,
                label=label,
                optical_axis=optical_axis,
            )
        except Exception:
            new_stl_path = None
        if not new_stl_path:
            return
        try:
            new_stl_path = self.editor._portable_cache_path(new_stl_path)
        except Exception:
            pass
        advanced[body_key] = new_stl_path
        # Forget any cached "this path is missing" entry on the
        # renderer so the next refresh picks the regenerated STL up
        # immediately, without waiting for the 5-second TTL.
        try:
            self.editor._clear_missing_path(new_stl_path)
            self.editor._clear_missing_path(body_stl_value)
        except Exception:
            pass

    def _initial_dir_for(self, asset: MissingAsset) -> Optional[Path]:
        parent = asset.expected_path.parent
        # Walk up until we find an existing ancestor so the picker
        # opens somewhere useful instead of a non-existent path.
        current = parent
        for _ in range(8):
            if current.exists() and current.is_dir():
                return current
            if current.parent == current:
                break
            current = current.parent
        return None

    def _index_folder(self, root: Path) -> dict[str, Path]:
        """Walk ``root`` and return a basename → path map.

        Returns an empty dict if the walk hits the max-files cap; in
        practice that means the user pointed the picker at a directory
        much too broad, and the dialog responds with the "no matches"
        branch instead of producing a spurious resolution.
        """
        out: dict[str, Path] = {}
        total = 0
        for current_root, dirs, files in self._walk_capped(root):
            for filename in files:
                total += 1
                if total > _FOLDER_SCAN_MAX_FILES:
                    return out
                key = filename.lower()
                if key not in out:
                    out[key] = Path(current_root) / filename
        return out

    def _walk_capped(self, root: Path):
        """Like ``os.walk`` but bounded by depth, to keep the UI snappy."""
        import os

        root_depth = len(root.parts)
        for current_root, dirs, files in os.walk(root):
            depth = len(Path(current_root).parts) - root_depth
            if depth >= _FOLDER_SCAN_MAX_DEPTH:
                # Prune the descent. ``os.walk`` will skip these dirs
                # because we cleared the list in place.
                dirs[:] = []
            yield current_root, dirs, files
