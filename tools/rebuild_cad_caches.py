#!/usr/bin/env python3
"""Rebuild the derived CAD caches every saved scene references (bugs/0810).

``attachment/cad_cache`` holds DERIVED files -- promoted-body STLs, generated beam-splitter template
STEPs -- that Filen syncs and can delete. Loading a scene rebuilds what it needs, but guards and
scripts that build rows without the load path never do, and a fresh clone has none of them. This walks
the scene files, runs the editor's own rebuild (``_regenerate_missing_optical_solid_caches``) on each,
and reports what was rebuilt, what was refused (a rebuild that does not reproduce the recorded optical
faces is never written) and what is genuinely unrecoverable (a vendor source STEP that is gone).

Scene files are never rewritten: an overlay-promoted body is rebuilt at the path the scene already
records, and a re-meshed file-backed body is re-meshed again, identically, at the next load.

Usage:
    .devenv/state/venv/bin/python tools/rebuild_cad_caches.py [scene.py ...]
(needs a Tk display; run under ``xvfb-run -a`` when headless)
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def default_scenes() -> list[Path]:
    return sorted((PROJECT_ROOT / "attachment").glob("*.py")) + sorted(
        (PROJECT_ROOT / "KrakenOS" / "common_optical_layouts").glob("*.py"))


def main(argv: list[str]) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import KrakenOS.UI.layout_editor as le
    from KrakenOS.UI.services.missing_assets_scan import scan_missing_assets

    scenes = [Path(a).resolve() for a in argv] if argv else default_scenes()
    editor = None
    refused = unrecoverable = rebuilt = 0
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            editor = le.KrakenLayoutEditor(headless=True)
        for scene in scenes:
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    info = le._load_python_data(scene)
            except Exception:
                continue
            items = info.get("surfaces") or []
            if "cad_cache" not in repr(items):
                continue
            editor.rows = [le.KrakenLayoutEditor._row_from_layout_item(item) for item in items]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                editor._regenerate_missing_optical_solid_caches()
            notes = list(getattr(editor, "_cad_cache_rebuild_notes", []) or [])
            missing = scan_missing_assets(editor.rows)
            if not notes and not missing:
                continue
            print(f"{scene.name}")
            for note in notes:
                tag = "REFUSED" if "refused" in note else ("rebuilt" if "rebuilt" in note or "re-meshed" in note else "note")
                refused += tag == "REFUSED"
                rebuilt += tag == "rebuilt"
                print(f"   {tag}: {note}")
            for asset in missing:
                unrecoverable += 1
                print(f"   MISSING: row {asset.row_index} {asset.key} -> {asset.expected_path}")
    finally:
        if editor is not None:
            with contextlib.suppress(Exception):
                editor.destroy()
    print(f"rebuilt {rebuilt}, refused {refused}, still missing {unrecoverable}")
    return 1 if (refused or unrecoverable) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
