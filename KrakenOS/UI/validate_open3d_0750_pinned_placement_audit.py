"""Guard for bugs/0750 -- catch an edit that moves rows off their authored placement.

bugs/0748 changed the SUM of the two lens sliding gaps in om05a_folded_80mm.py. Every row after
those gaps inherits the change through its station, so the whole arm-B block slid 8.54 mm while
arm A stayed put. The user flagged it twice ("hay wired prism assembly", "Both big RA mirror is not
aligned") before it was found. bugs/0749 reverted it.

The guard keys on `advanced["StepOverlayPromotion"]["center_world"]` -- each promoted row's AUTHORED
world placement -- and compares it with the live follower-walk pose.

Three designs were measured and REJECTED before this one; the checks below pin the reasons so they
are not re-proposed:

  * pairing rows by an " A"/" B" name suffix -- a relationship the codebase uses nowhere else, and
    one that misfires on any unrelated pair;
  * the absolute test `z_a + z_b == 2 * split_plane` -- red AT REST on historical scenes carrying
    1.0-2.9 mm of authored slop, so no single tolerance is both quiet and useful;
  * a "spread" formulation -- blind to common-mode drift: move the object row and every pair slides
    together, leaving the spread at 0.000000 while every mirror has moved.

Checks (display-free, no app -- the follower walk is driven from statically parsed rows):
  A  the module's contract: drifts, the DELTA comparison, and unmeasurable rows never dropped.
  B  the real scene reads a clean floor, with the one known stale snapshot reported not hidden.
  C  the bugs/0748 edit lights up the downstream block at 8.5400 mm.
  D  the delta form is silent on an unchanged reading, and a pre-existing stale row stays silent
     unless the edit made it worse.
  E  the rejected designs stay documented.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0750_pinned_placement_audit
"""

from __future__ import annotations

import inspect
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/om05a_folded_80mm.py"
GAP_FRONT, GAP_REAR = 8, 13          # the two gaps bracketing the imaging lens block
BREAK_FRONT, BREAK_REAR = 6.219, 2.321   # the bugs/0748 edit; sum +8.540


def _rows_from_scene(path):
    """Build editor rows from a scene file, without starting the app."""
    from KrakenOS.UI.surface_table_model import SurfaceRow
    from KrakenOS.UI.validate_open3d_0738_phantom_spacer_surfaces import _scene_rows

    rows = []
    for index, spec in enumerate(_scene_rows(path)):
        rows.append(SurfaceRow(
            label=str(index),
            surface=str(spec.get("surface") or "Standard"),
            element=str(spec.get("element") or ""),
            name=str(spec.get("name") or ""),
            thickness=float(spec.get("thickness") or 0.0),
            diameter=float(spec.get("diameter") or 0.0),
            glass=str(spec.get("glass") or "AIR"),
            advanced=dict(spec.get("advanced") or {}),
            tilt_x=float(spec.get("tilt_x") or 0.0),
            tilt_y=float(spec.get("tilt_y") or 0.0),
            tilt_z=float(spec.get("tilt_z") or 0.0),
            desp_x=float(spec.get("desp_x") or 0.0),
            desp_y=float(spec.get("desp_y") or 0.0),
            desp_z=float(spec.get("desp_z") or 0.0),
        ))
    return rows


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import scene_placement_audit as audit

    # ---- A: the contract ------------------------------------------------------------------------
    ok(
        callable(getattr(audit, "pinned_placement_drifts", None))
        and callable(getattr(audit, "compare_drifts", None)),
        "A1: the module exposes a drift reading and a DELTA comparison",
    )
    fake_rows = _rows_from_scene(SCENE)
    base = audit.pinned_placement_drifts(fake_rows)
    ok(
        bool(base) and all({"row", "name", "authored", "live", "drift_mm"} <= set(r) for r in base),
        f"A2: every record carries row/name/authored/live/drift_mm ({len(base)} records)",
    )
    unmeasurable = [r for r in base if r["drift_mm"] is None]
    ok(
        all(r["live"] is None for r in unmeasurable),
        f"A3: a row with a snapshot but NO walked pose is reported unmeasurable, never silently "
        f"dropped ({len(unmeasurable)} such row(s))",
    )

    # ---- B: the real scene's floor ----------------------------------------------------------------
    measured = [r for r in base if r["drift_mm"] is not None]
    clean = [r for r in measured if r["drift_mm"] <= audit.NOISE_FLOOR_MM]
    stale = [r for r in measured if r["drift_mm"] > 1.0]
    ok(
        len(clean) >= 9,
        f"B1: the healthy scene sits on a clean floor -- {len(clean)} of {len(measured)} promoted "
        f"rows within {audit.NOISE_FLOOR_MM} mm",
    )
    ok(
        len(stale) == 1 and stale[0]["row"] == 16,
        f"B2: the ONE known stale snapshot (row 16 'RA mirror 2') is reported, not hidden "
        f"({[(r['row'], round(r['drift_mm'], 1)) for r in stale]})",
    )

    # ---- C: the real defect ------------------------------------------------------------------------
    broken = _rows_from_scene(SCENE)
    broken[GAP_FRONT].thickness += BREAK_FRONT
    broken[GAP_REAR].thickness += BREAK_REAR
    moved = audit.compare_drifts(base, audit.pinned_placement_drifts(broken))
    big = [m for m in moved if abs(m["moved_mm"] - 8.54) < 1e-3]
    ok(
        len(big) >= 7,
        f"C1: the bugs/0748 gap-SUM edit moves the downstream block by 8.5400 mm "
        f"({len(big)} rows at 8.5400 of {len(moved)} reported)",
    )
    names = {m["name"] for m in big}
    ok(
        any("B" in n for n in names) and "LED panel A" in names,
        f"C2: the moved rows are the arm-B block and its neighbours -- {sorted(names)}",
    )
    ok(
        not any(m["name"] in ("BS cube A", "Centre RA mirror A", "RA mirror 1 (50 mm)") for m in moved),
        "C3: the arm-A rows AHEAD of the edited gaps do NOT move -- which is precisely the "
        "asymmetry the user saw",
    )

    # ---- D: quiet when it should be -----------------------------------------------------------------
    ok(
        audit.compare_drifts(base, base) == [],
        "D1: an unchanged reading reports nothing -- the delta form is silent by construction",
    )
    ok(
        not any(m["row"] == 16 for m in audit.compare_drifts(base, base)),
        "D2: the pre-existing stale row does not fire on its own; only a change fires it",
    )
    nudged = _rows_from_scene(SCENE)
    nudged[GAP_FRONT].thickness += 1.0
    nudged[GAP_REAR].thickness -= 1.0          # a PAIR move: sum invariant, like the 0719 solve
    ok(
        audit.compare_drifts(base, audit.pinned_placement_drifts(nudged)) == [],
        "D3: a thickness PAIR that keeps the SUM invariant moves nothing -- the bugs/0719 solve "
        "stays silent, which is why it was always safe",
    )

    # ---- E: the rejected designs stay documented -------------------------------------------------------
    doc = inspect.getdoc(audit) or ""
    ok(
        "spread" in doc and "common-mode" in doc,
        "E1: the module records WHY a spread formulation was rejected (blind to common-mode drift)",
    )
    ok(
        "authored slop" in doc and "split plane" in doc,
        "E2: ...and why the absolute split-plane test was rejected (red at rest on real scenes)",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0750 pinned-placement-audit validation PASSED")
        return 0
    print("0750 pinned-placement-audit validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
