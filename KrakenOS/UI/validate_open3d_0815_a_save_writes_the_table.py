"""Guard for bugs/0815 -- a save writes what the TABLE holds, and the om05a prism
assembly sits on its authored seat.

User: "I examine om05a_folded.py, the Prism Assembly itself hay wired, the prisms are all
off centered ... just copy the prism assembly from om05a_folded_80mm.py."

Two things came out of that repair and both are guarded here.

* **The writer's source of truth is the TABLE.** ``_write_layout_file`` begins with
  ``_read_rows_from_table()``, so a service (or a repair script) that edits ``editor.rows``
  and saves WITHOUT ``_sync_table()`` writes the stale table back and the edit vanishes with
  no error at all -- the first re-seat reported "drift 0.000000" and saved a file that still
  carried the old placement. bugs/0591/0608 hit the same trap in the lens refit and left the
  sync in with a comment; this makes the contract a test.
* **The assembly's seat.** The seven re-seated rows (the B-side train, both BS far halves and
  both LED panels) must sit on their authored ``StepOverlayPromotion.center_world``, which is
  the same authored placement the 80 mm bench carries.

Display-free (Tk needs a DISPLAY for the table; no VTK render).

Run:
    xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0815_a_save_writes_the_table

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
import tempfile
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/om05a_folded.py"

# bugs/0815: the rows the repair re-seated, with the authored centre each one must hold.
ASSEMBLY_SEATS = {
    "First RA mirror B": (0.0, 0.42, -59.0),
    "BS cube B": (0.0, 12.52, -57.25),
    "Centre RA mirror B": (0.0, 14.0, -30.97),
    "BS cube A (far half)": (0.0, 12.59, 7.32),
    "BS cube B (far half)": (0.0, 12.59, -57.32),
    "LED panel A": (0.0, 27.07, 4.95),
    "LED panel B": (0.0, 27.07, -54.95),
}


def _check_writer_reads_the_table(ok, skip) -> None:
    """A: an edited row reaches the saved file only through the table."""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data

    editor = None
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor = KrakenLayoutEditor()
    except Exception as exc:  # pragma: no cover - env dependent (no DISPLAY)
        skip(f"A: a Tk editor is unavailable here ({type(exc).__name__}: {exc})")
        return
    try:
        # a fresh editor carries Object + Image only -- give it one real surface to edit
        from KrakenOS.UI.layout_editor import SurfaceRow

        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor.rows = editor._normalized_rows_copy([
                SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
                SurfaceRow(surface="Standard", name="Front", rc=50.0, thickness=5.0, diameter=25.0, glass="BK7"),
                SurfaceRow(surface="Standard", name="Rear", rc=0.0, thickness=95.0, diameter=25.0, glass="AIR"),
                SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=10.0, glass="AIR"),
            ])
            editor._normalize_special_rows()
            editor._sync_table()
        rows = editor.rows
        index = next((i for i, r in enumerate(rows) if str(r.surface) == "Standard"), None)
        if index is None:
            skip("A: the default layout has no Standard row")
            return
        marker = 12.345
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "saved.py"

            # A1: edit the row objects only -- the table still holds the old value.
            setattr(rows[index], "desp_z", marker)
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                editor._write_layout_file(out)
            written = [
                float(item.get("desp_z", 0.0) or 0.0)
                for item in _load_python_data(out)["surfaces"]
            ]
            ok(
                not any(abs(value - marker) < 1e-9 for value in written),
                f"A1: an edit made on editor.rows alone does NOT reach the saved file -- the "
                f"writer re-reads the table first (saved desp_z {written[index]:.3f})",
            )

            # A2: the same edit, pushed through _sync_table, persists.
            setattr(editor.rows[index], "desp_z", marker)
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                editor._sync_table()
                editor._write_layout_file(out)
            written = [
                float(item.get("desp_z", 0.0) or 0.0)
                for item in _load_python_data(out)["surfaces"]
            ]
            ok(
                abs(written[index] - marker) < 1e-6,
                f"A2: _sync_table() then save persists the edited row (saved desp_z "
                f"{written[index]:.3f}, expected {marker})",
            )
    finally:
        with contextlib.suppress(Exception):
            editor.destroy()


def _check_source_contracts(ok) -> None:
    """B: the writer's first act, and the sites that must sync before saving."""
    from KrakenOS.UI.services.layout_file_writer import LayoutFileWriterService
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    writer_src = inspect.getsource(LayoutFileWriterService._write_layout_file)
    body = [line.strip() for line in writer_src.splitlines() if line.strip()]
    first = next((line for line in body[1:] if not line.startswith(('"""', "#"))), "")
    ok(
        "_read_rows_from_table()" in first,
        f"B1: _write_layout_file's first act is _read_rows_from_table() ({first[:60]!r})",
    )
    refit_src = inspect.getsource(ScenePlacementMixin.refit_lens_principal_to_datasheet_wd)
    ok(
        "_sync_table()" in refit_src and "_read_rows_from_table" in refit_src,
        "B2: the bugs/0591/0608 lens refit still pushes its rows into the table (with the "
        "comment naming the trap) before it returns",
    )


def _check_assembly_seat(ok, skip) -> None:
    """C: the om05a assembly sits on its authored placement (SKIP when the scene is absent)."""
    if not SCENE.exists():
        skip("C: the om05a folded scene is not on this machine (Filen-synced)")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data
    from KrakenOS.UI.services import scene_placement_audit as audit

    info = _load_python_data(SCENE)
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    drifts = {str(d["name"]): d for d in audit.pinned_placement_drifts(rows)}
    worst_name, worst = "", 0.0
    seated = 0
    for name, seat in ASSEMBLY_SEATS.items():
        record = drifts.get(name)
        if record is None or record.get("live") is None:
            continue
        live = np.asarray(record["live"], dtype=float)
        drift = float(record["drift_mm"])
        if np.allclose(live, np.asarray(seat, dtype=float), atol=0.05) and drift <= audit.DEFAULT_TOL_MM:
            seated += 1
        if drift > worst:
            worst_name, worst = name, drift
    ok(
        seated == len(ASSEMBLY_SEATS),
        f"C1: all {len(ASSEMBLY_SEATS)} re-seated assembly rows sit on their authored centre "
        f"({seated}/{len(ASSEMBLY_SEATS)}; worst drift {worst:.3f} mm"
        + (f" on {worst_name}" if worst_name else "") + ")",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    _check_writer_reads_the_table(ok, skip)
    _check_source_contracts(ok)
    _check_assembly_seat(ok, skip)

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Open 3D save-writes-the-table validation passed.")
        return 0
    print("Open 3D save-writes-the-table validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
