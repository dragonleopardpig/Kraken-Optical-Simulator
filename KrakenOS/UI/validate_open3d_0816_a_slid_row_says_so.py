"""Guard for bugs/0816 -- an edit that slides a pinned row off its authored placement says so.

bugs/0769 split a leg in `om05a_folded.py` (RA mirror 2's 45.13 -> 36.31 + an 8.82 mm sensor
standoff), preserved the sum AT THE SENSOR and recorded "nothing moves". Seven free-placed prism
rows sat BETWEEN the row that lost the 8.82 mm and the row that gained it, so their station -- and
their world z -- dropped by exactly that. The scene then traced 6 rays of 1103 until the user
looked at it and said the prisms were off centre. Nothing in the app had said a word.

The bugs/0750 audit has had the right instrument since: the DELTA form is silent on an unmoved
scene and on a merely stale snapshot, so it can run on every model change. It now does.

Checks:
  A  PURE: moves_since reports the slid row and stays silent on a stale snapshot and across a
     scene load (renumbered rows); prune_resolved_moves clears a row that came back;
     format_placement_move_lines reports without proposing that anything be moved back.
  B  LIVE (SKIP when the Filen-synced scene is absent): the REAL inspector methods, driven
     through a shim on the user's scene -- a sum-preserving leg split slides the seven prism
     rows and is caught with the right rows and amounts; undoing it clears the notice by itself;
     an edit downstream of every pinned row says nothing.
  C  WIRING: the model-change chokepoint takes the reading, the scene painter refreshes the
     baseline, and the banner carries the lines.

Display-free (row math only; the LIVE section needs a Tk editor, as bugs/0672's guard does).

Run:
    xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0816_a_slid_row_says_so

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/om05a_folded.py"

# the seven rows bugs/0769's split slid (bugs/0815 re-seated them)
ASSEMBLY = {
    "First RA mirror B", "BS cube B", "Centre RA mirror B",
    "BS cube A (far half)", "BS cube B (far half)", "LED panel A", "LED panel B",
}


def _check_pure(ok) -> None:
    from KrakenOS.UI.services import scene_placement_audit as audit

    before = [
        {"row": 7, "name": "RA mirror 1", "drift_mm": 3.563},     # stale snapshot (bugs/0760)
        {"row": 16, "name": "First RA mirror B", "drift_mm": 0.0},
    ]
    after = [
        {"row": 7, "name": "RA mirror 1", "drift_mm": 3.563},
        {"row": 16, "name": "First RA mirror B", "drift_mm": 8.82},
    ]
    moved = audit.moves_since(before, after)
    ok(
        len(moved) == 1
        and int(moved[0]["row"]) == 16
        and abs(float(moved[0]["moved_mm"]) - 8.82) < 1e-9,
        f"A1: the slid row is reported and the already-stale row stays silent ({moved})",
    )
    ok(
        audit.moves_since(before, before) == [],
        "A2: an unmoved scene reports nothing",
    )
    renumbered = [{"row": 16, "name": "Some other row", "drift_mm": 99.0}]
    ok(
        audit.moves_since(before, renumbered) == [],
        "A3: a reading across a scene LOAD (same index, different row) reports nothing",
    )
    back = [{"row": 16, "name": "First RA mirror B", "drift_mm": 0.0}]
    ok(
        audit.prune_resolved_moves(moved, back) == [],
        "A4: a row that came back to its seat clears its own notice",
    )
    still = [{"row": 16, "name": "First RA mirror B", "drift_mm": 8.82}]
    ok(
        len(audit.prune_resolved_moves(moved, still)) == 1,
        "A5: a row still off its seat stays flagged",
    )
    lines = audit.format_placement_move_lines(moved)
    text = " ".join(lines).lower()
    ok(
        bool(lines)
        and lines[0].startswith("PLACEMENT:")
        and "8.82" in " ".join(lines)
        and "first ra mirror b" in text
        and "nothing was moved for you" in text,
        f"A6: the notice names the row and the amount and moves nothing ({len(lines)} lines)",
    )
    ok(
        audit.format_placement_move_lines([]) == [],
        "A7: no moves -> no notice",
    )


def _check_live(ok, skip) -> None:
    if not SCENE.exists():
        skip("B: the om05a folded scene is not on this machine (Filen-synced)")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    editor = None
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor = KrakenLayoutEditor()
            editor._prompt_for_missing_cad_assets = lambda: None
            editor.layout_files["omf"] = SCENE
            editor.load_layout_by_name("omf")
    except Exception as exc:  # pragma: no cover - env dependent
        skip(f"B: the scene could not be loaded here ({type(exc).__name__}: {exc})")
        with contextlib.suppress(Exception):
            editor.destroy()
        return
    try:
        shim = SimpleNamespace(
            editor=editor,
            status_var=SimpleNamespace(set=lambda *_a: None),
        )
        editor.status_var = SimpleNamespace(set=lambda *_a: None)
        note = Kraken3DInspector._note_pinned_placement_moves.__get__(shim, type(shim))
        base = Kraken3DInspector._refresh_pinned_placement_baseline.__get__(shim, type(shim))
        read = Kraken3DInspector._pinned_placement_reading.__get__(shim, type(shim))
        shim._pinned_placement_reading = read

        rows = list(editor.rows)
        arm = next((i for i, r in enumerate(rows) if str(r.name) == "RA mirror 2 (40 mm)"), -1)
        pad = next((i for i, r in enumerate(rows) if str(r.name) == "sensor standoff"), -1)
        if arm < 0 or pad < 0:
            skip("B: the scene carries no RA mirror 2 / sensor standoff pair")
            return

        base()   # the scene as painted
        ok(
            not (editor.__dict__.get("_pinned_placement_moves") or []),
            "B1: a freshly painted scene carries no placement notice",
        )

        # bugs/0769's edit, smaller: move 5 mm from the arm leg to the standoff. The SUM at the
        # sensor is preserved, which is why it read as "nothing moves".
        delta = 5.0
        rows[arm].thickness = float(rows[arm].thickness) - delta
        rows[pad].thickness = float(rows[pad].thickness) + delta
        note()
        moved = list(editor.__dict__.get("_pinned_placement_moves") or [])
        names = {str(record["name"]) for record in moved}
        amounts_ok = all(abs(float(r["moved_mm"]) - delta) < 0.01 for r in moved)
        ok(
            names == ASSEMBLY and amounts_ok,
            f"B2: the sum-preserving leg split is caught on all {len(ASSEMBLY)} prism rows at "
            f"{delta} mm ({len(moved)} flagged, amounts {'ok' if amounts_ok else 'WRONG'})",
        )

        # undo it: the notice must clear itself at the next paint
        rows[arm].thickness = float(rows[arm].thickness) + delta
        rows[pad].thickness = float(rows[pad].thickness) - delta
        base()
        ok(
            not (editor.__dict__.get("_pinned_placement_moves") or []),
            "B3: undoing the edit clears the notice at the next paint, with nothing to remember",
        )

        # an edit downstream of every pinned row moves the sensor, not the prisms
        rows[pad].thickness = float(rows[pad].thickness) + 3.0
        note()
        ok(
            not (editor.__dict__.get("_pinned_placement_moves") or []),
            "B4: an edit downstream of every pinned row says nothing",
        )
        rows[pad].thickness = float(rows[pad].thickness) - 3.0
        base()
    finally:
        with contextlib.suppress(Exception):
            editor.destroy()


def _check_wiring(ok) -> None:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    ok(
        "_note_pinned_placement_moves()" in inspect.getsource(Kraken3DInspector._apply_model_change),
        "C1: the model-change chokepoint takes the reading before the redraw",
    )
    ok(
        "_refresh_pinned_placement_baseline()" in inspect.getsource(Kraken3DInspector.refresh_scene),
        "C2: the scene painter refreshes the baseline (both the sync and async traces)",
    )
    ok(
        "format_placement_move_lines" in inspect.getsource(
            Kraken3DInspector._update_solve_refusal_banner
        ),
        "C3: the in-scene banner carries the placement lines",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    _check_pure(ok)
    _check_live(ok, skip)
    _check_wiring(ok)

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Open 3D slid-row notice validation passed.")
        return 0
    print("Open 3D slid-row notice validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
