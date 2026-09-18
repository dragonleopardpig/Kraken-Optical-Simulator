"""bugs/0821: the 7-row penta cascade is a RECIPE, not an asset to keep.

User: "I think we only need five_penta_prism_analytic_telescope_cascade.py, the rest of the
five_penta can be retired" -- and then, on the one the whole penta suite loads: "five_penta_prism_
analytic_telescope_cascade.py got more than five_penta_prism_cascade.py."

Measured, that is exactly right. The analytic telescope cascade carries 18 rows against the plain
cascade's 7, and its first six -- ``Object`` plus ``Penta prism 1..5`` -- are **byte-identical** to
the plain cascade's. The only difference is the tail: the plain file ends at an ``Image`` row where
the analytic one continues into ball lenses, a DCV, an achromat and a cylindrical before its own
Image. So the plain cascade is the analytic one's prism head plus an Image row at the origin, and
storing both is storing the same geometry twice (bugs/0810's doctrine, applied to a fixture).

``ensure_five_penta_cascade`` derives it on demand through the editor's own writer, so the file can
be deleted at any time and comes back identical -- verified row by row and by running penta phases
0-60 against the derived copy (60 pass, only the baseline-known phase 52 red, exactly as with the
stored file).
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CASCADE_PATH = PROJECT_ROOT / "attachment" / "five_penta_prism_cascade.py"
SOURCE_PATH = PROJECT_ROOT / "attachment" / "five_penta_prism_analytic_telescope_cascade.py"
PRISM_ROWS = 6      # Object + Penta prism 1..5


def ensure_five_penta_cascade(
    path: Path | None = None, *, source: Path | None = None
) -> "Path | None":
    """The 7-row cascade fixture, derived from the analytic cascade when it is absent.

    Returns the path, or None when neither the fixture nor its source is on this machine (the
    attachment tree is Filen-synced, so a checkout may legitimately have neither). Never raises:
    every caller of this fixture treats a missing scene as SKIP.
    """
    path = Path(path) if path is not None else CASCADE_PATH
    if path.exists():
        return path
    source = Path(source) if source is not None else SOURCE_PATH
    if not source.exists():
        return None
    buf = io.StringIO()
    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            app = KrakenLayoutEditor()
            app._prompt_for_missing_cad_assets = lambda: None
            app.layout_files["_penta_cascade_source"] = source
            app.load_layout_by_name("_penta_cascade_source")
            rows = list(app.rows)
            if len(rows) <= PRISM_ROWS:
                return None
            image = rows[-1]
            # the plain cascade's Image sits at the origin; the analytic one's has travelled
            # through the optics that follow the prisms
            for field in ("desp_x", "desp_y", "desp_z", "tilt_x", "tilt_y", "tilt_z"):
                setattr(image, field, 0.0)
            app.rows = rows[:PRISM_ROWS] + [image]
            app._normalize_special_rows()
            app._sync_table()          # bugs/0815: the writer reads the TABLE
            app.current_layout_file = path
            path.parent.mkdir(parents=True, exist_ok=True)
            app._write_layout_file(path)
    except Exception:
        return path if path.exists() else None
    finally:
        if app is not None:
            with contextlib.suppress(Exception):
                app.destroy()
    return path if path.exists() else None
