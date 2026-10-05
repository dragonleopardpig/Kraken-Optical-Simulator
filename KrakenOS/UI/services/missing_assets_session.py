"""What the missing-CAD-assets window does, whichever toolkit shows it (bugs/0965).

A layout can name STEP / STL files that are not on disk -- a fresh machine, a moved folder, a cache
that was never synced. `scan_missing_assets` lists them; this session resolves them:

* **find by name first** (`auto_locate`): on load, every missing file whose name matches exactly ONE
  file under the project's `attachment/` folder or the layout's own folder is pointed at that file.
  A name that matches two different files is left for the user -- a guess there could put the
  wrong part in the scene;
* **Locate** one entry at a chosen file, **Locate folder** -- every unresolved entry whose file name
  is found under a chosen folder -- **Skip** (the renderer draws a "missing asset" placeholder for
  the row), **Skip all**, **Reset** an entry back to missing;
* **close** once: the editor rebuilds what the relocations made possible and redraws.

A view (the Tk window, `panels/missing_assets_dialog.py`; the Qt one,
`qt/dialogs/missing_assets_dialog.py`) shows `rows()` and calls these; nothing here is toolkit code.
Until bugs/0965 the logic lived in the Tk window, which in the Qt shell was a Tk window on the hidden
Tk root with no Tk event loop -- invisible or frozen.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Optional

from KrakenOS.UI.services.missing_assets_scan import (
    MissingAsset,
    clear_row_skip,
    mark_row_skipped,
    relocate_advanced_path,
)

#: a folder walk is bounded, so a picked Desktop or home folder does not freeze the UI. Users point
#: at a catalogue root (attachment/Lens/ has < 200 files within 3-4 levels)
FOLDER_SCAN_MAX_DEPTH = 6
FOLDER_SCAN_MAX_FILES = 50_000
#: folders a walk never enters
_SKIPPED_DIRS = {".git", "__pycache__", ".devenv", ".direnv", "node_modules"}

TITLE = "Missing CAD assets"
PROMPT = (
    "This layout references files that are not on disk. The renderer would otherwise silently fall "
    "back to a partial drawing of each affected row (a half-sphere instead of a ball lens, a flat "
    "disc instead of a meniscus, and so on).\n\n"
    "Choose Locate to point at the file directly, Locate folder... to batch-match by file name across "
    "a directory tree, or Skip to render an explicit \"missing asset\" placeholder for the row."
)
FILE_TYPES = [("CAD/STL", "*.step *.stp *.stl *.STEP *.STP *.STL"), ("All files", "*")]


def walk_capped(root: Path):
    """Like ``os.walk``, bounded in depth, skipping tool folders."""
    root_depth = len(Path(root).parts)
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _SKIPPED_DIRS and not name.startswith(".")]
        if len(Path(current_root).parts) - root_depth >= FOLDER_SCAN_MAX_DEPTH:
            dirs[:] = []
        yield current_root, dirs, files


def index_folders(roots) -> dict[str, list[Path]]:
    """Lower-case file name -> every DIFFERENT file of that name under ``roots`` (bounded walk)."""
    found: dict[str, list[Path]] = {}
    total = 0
    for root in roots:
        root = Path(root).expanduser()
        if not root.is_dir():
            continue
        for current_root, _dirs, files in walk_capped(root):
            for filename in files:
                total += 1
                if total > FOLDER_SCAN_MAX_FILES:
                    return found
                path = (Path(current_root) / filename).resolve(strict=False)
                paths = found.setdefault(filename.lower(), [])
                if path not in paths:
                    paths.append(path)
    return found


def auto_locate_roots(editor: Any) -> list[Path]:
    """Where `auto_locate` looks: the layout's own folder, then the project's attachment/ folder."""
    from KrakenOS.UI.services.cad_cache_paths import PROJECT_ROOT

    roots: list[Path] = []
    layout = getattr(editor, "current_layout_file", None)
    if layout:
        roots.append(Path(str(layout)).expanduser().resolve(strict=False).parent)
    roots.append(Path(PROJECT_ROOT) / "attachment")
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


class MissingAssetsSession:
    """The missing files of one layout, and what has been done about each."""

    title = TITLE
    prompt = PROMPT
    file_types = FILE_TYPES

    def __init__(self, editor: Any, assets: list[MissingAsset], *,
                 on_resolve: Optional[Callable[[], None]] = None) -> None:
        self.editor = editor
        self.assets = list(assets)
        #: per entry: "missing" | "located" | "skipped"
        self.status: list[str] = ["missing"] * len(self.assets)
        #: (entry, file) for each entry `auto_locate` resolved
        self.auto_located: list[tuple[int, Path]] = []
        self._on_resolve = on_resolve
        self.closed = False

    # ---- what a view shows -------------------------------------------------------------------
    def where(self, index: int) -> str:
        asset = self.assets[index]
        if asset.scope != "row":
            return "Overlay import"
        return f"Row {asset.row_index} {asset.label or asset.short_label()}"

    def resolved_path(self, index: int) -> Path:
        """The path the entry points at NOW (a Locate rewrote it)."""
        asset = self.assets[index]
        if asset.scope == "editor":
            value = getattr(self.editor, asset.key, None)
            if value is not None:
                try:
                    return Path(str(value)).expanduser()
                except Exception:
                    pass
            return asset.expected_path
        try:
            advanced = getattr(self.editor.rows[asset.row_index], "advanced", None) or {}
        except Exception:
            return asset.expected_path
        if "." in asset.key:
            outer, _, inner = asset.key.partition(".")
            nested = advanced.get(outer)
            value = nested.get(inner) if isinstance(nested, dict) else None
        else:
            value = advanced.get(asset.key)
        return Path(value).expanduser() if isinstance(value, str) and value else asset.expected_path

    def rows(self) -> list[tuple[str, str, str, str]]:
        """(where, reference, path, status) per entry."""
        return [(self.where(i), asset.key, str(self.resolved_path(i)), self.status[i])
                for i, asset in enumerate(self.assets)]

    def counts(self) -> dict:
        return {state: sum(1 for value in self.status if value == state) for state in ("missing", "located", "skipped")}

    def summary(self) -> str:
        counts = self.counts()
        return f"{counts['missing']} unresolved   |   {counts['located']} located   |   {counts['skipped']} skipped"

    def unresolved(self) -> list[int]:
        return [index for index, state in enumerate(self.status) if state == "missing"]

    def initial_dir(self, index: int) -> Optional[Path]:
        """The nearest existing folder above the expected path -- where a file picker opens."""
        current = self.assets[index].expected_path.parent
        for _ in range(8):
            if current.exists() and current.is_dir():
                return current
            if current.parent == current:
                break
            current = current.parent
        return None

    # ---- what a view asks for ----------------------------------------------------------------
    def locate(self, index: int, new_path) -> str:
        """Point entry ``index`` at ``new_path``. Returns "" when done, else why not."""
        new_path = Path(new_path).expanduser()
        if not new_path.exists() or not new_path.is_file():
            return f"{new_path}\nis not a regular file. Pick the actual STEP / STL."
        asset = self.assets[index]
        if asset.scope == "editor":
            try:
                setattr(self.editor, asset.key, new_path)
            except Exception as exc:
                return f"Could not assign {asset.key} = {new_path}\n{exc}"
            self.status[index] = "located"
            return ""
        try:
            row = self.editor.rows[asset.row_index]
        except Exception as exc:
            return f"Could not find row {asset.row_index}: {exc}"
        advanced = getattr(row, "advanced", None)
        if not isinstance(advanced, dict):
            advanced = {}
            setattr(row, "advanced", advanced)
        if relocate_advanced_path(advanced, asset.key, new_path):
            clear_row_skip(advanced, asset.key)
        # bugs/0021: a relocated SOURCE STEP rebuilds its derived body cache -- the analytic body or
        # the file-backed optical solid -- so the user need not promote again. Best effort: the
        # relocate itself already succeeded.
        body_key = ("StepAnalyticBodyStlPath" if asset.key.endswith(".source_step_path")
                    else "Solid_3d_stl" if asset.key == "OpticalSolidSourcePath" else None)
        if body_key is not None:
            try:
                self.editor._rebuild_row_body_cache(advanced, body_key=body_key, source_path=new_path)
            except Exception:
                pass
        self.status[index] = "located"
        return ""

    def locate_folder(self, directory) -> tuple[int, str]:
        """Resolve every unresolved entry whose file name is found under ``directory``.
        Returns (how many, a message for the user when none)."""
        root = Path(directory).expanduser()
        if not root.is_dir():
            return 0, f"{root} is not a folder."
        try:
            names = index_folders([root])
        except Exception as exc:
            return 0, f"Could not scan {root}:\n{exc}"
        matched = 0
        for index in self.unresolved():
            candidates = names.get(self.assets[index].expected_path.name.lower())
            if candidates and not self.locate(index, candidates[0]):
                matched += 1
        if matched:
            return matched, ""
        return 0, (f"Scanned {root}\n\nNo unresolved entries matched a file in that tree by name. Try a "
                   "directory closer to the vendor catalog (e.g. attachment/Lens) or pick each entry "
                   "individually with Locate...")

    def auto_locate(self, roots) -> list[tuple[int, Path]]:
        """Find by name: each unresolved entry whose file name matches exactly ONE file under
        ``roots`` is pointed at it. Returns (entry, file) for each one resolved."""
        names = index_folders(roots)
        done: list[tuple[int, Path]] = []
        for index in self.unresolved():
            candidates = names.get(self.assets[index].expected_path.name.lower()) or []
            if len(candidates) == 1 and not self.locate(index, candidates[0]):
                done.append((index, candidates[0]))
        self.auto_located.extend(done)
        return done

    def skip(self, index: int) -> None:
        asset = self.assets[index]
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
        self.status[index] = "skipped"

    def skip_all(self) -> None:
        for index in self.unresolved():
            self.skip(index)

    def reset(self, index: int) -> None:
        """Undo a Locate's status or a Skip: the entry is missing again."""
        asset = self.assets[index]
        if asset.scope == "row":
            try:
                clear_row_skip(getattr(self.editor.rows[asset.row_index], "advanced", None) or {}, asset.key)
            except Exception:
                pass
        self.status[index] = "missing"

    def close(self) -> None:
        """The window closed (or nothing was left to ask): rebuild and redraw -- once."""
        if self.closed:
            return
        self.closed = True
        if self._on_resolve is not None:
            try:
                self._on_resolve()
            except Exception:
                pass
