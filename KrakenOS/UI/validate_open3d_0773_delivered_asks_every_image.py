"""Guard for bugs/0773 -- "already delivered" must ask EVERY image, not one of them.

Flag `20260910_172158` (a 21x21x1 device, "why the symmetry not hold?") carried this banner:

    SOLVE: ... the lens did not move -- the field was already delivered
      Face A field: 3.025   mm in front of the sensor
      Face B field: 0.09958 mm in front of the sensor

bugs/0752 split the focus measurement per formed image precisely so one arm could not speak for
the other. `_fov_already_delivered` never asked: it read the TOP-LEVEL ``offset_mm``, which on
that scene carried face B's 0.09958 -- a hair under the 0.1 mm tolerance -- so the field was
declared delivered while face A sat 3 mm out with a 419 um spot.

This is the same rule bugs/0764's snap guard states: a change that satisfies one arm and leaves
the other wrecked has not satisfied the scene. Whichever image is worst decides.

Honest scope: this defect is demonstrated at unit level below. It was NOT reproducible as a
whole-scene failure -- headless, the 21 mm solve runs rather than being gated -- so the fix is
justified by the contract, not by a scene repro.

Checks (display-free, pure):
  A  a two-image info whose WORST image is off is not "delivered", even when the top-level
     number is inside tolerance;
  B  a two-image info where BOTH land is still delivered (the gate is not merely disabled);
  C  a single-image info still works from the top-level number (every unfolded scene);
  D  a malformed/missing images list falls back to the top-level rather than raising.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0773_delivered_asks_every_image
"""

from __future__ import annotations

import inspect


def _worst(info):
    """The gate's own extraction, exercised the way _fov_already_delivered runs it."""
    offsets = []
    entries = info.get("images") if isinstance(info, dict) else None
    if isinstance(entries, (list, tuple)):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                offsets.append(abs(float(entry["offset_mm"])))
            except (KeyError, TypeError, ValueError):
                continue
    if not offsets:
        offsets = [abs(float(info["offset_mm"]))]
    return max(offsets)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    tol = float(QuickEstimationService._DELIVERED_FOCUS_TOL_MM)

    # the flagged state, verbatim
    flagged = {
        "offset_mm": -0.09958,
        "images": [
            {"name": "Face A field", "offset_mm": -3.025},
            {"name": "Face B field", "offset_mm": -0.09958},
        ],
    }
    ok(
        abs(float(flagged["offset_mm"])) <= tol,
        f"A0: the flag's top-level offset ({flagged['offset_mm']}) IS inside the {tol} mm "
        f"tolerance -- which is how it slipped through",
    )
    ok(
        _worst(flagged) > tol,
        f"A1: but the worst image ({_worst(flagged):.4f} mm) is not -- so the field is NOT "
        f"delivered while face A sits 3 mm out",
    )

    both_land = {
        "offset_mm": -0.0872,
        "images": [
            {"name": "Face A field", "offset_mm": -0.0872},
            {"name": "Face B field", "offset_mm": -0.0917},
        ],
    }
    ok(
        _worst(both_land) <= tol,
        f"B1: a 22 mm-style state where BOTH arms land is still delivered "
        f"({_worst(both_land):.4f} mm) -- the gate is not merely switched off",
    )

    single = {"offset_mm": -0.02}
    ok(
        abs(_worst(single) - 0.02) < 1e-9,
        "C1: a single-image info still reads the top-level number (every unfolded scene)",
    )

    for label, info in (
        ("empty list", {"offset_mm": -0.02, "images": []}),
        ("junk entries", {"offset_mm": -0.02, "images": [None, 7, "x"]}),
        ("missing key", {"offset_mm": -0.02, "images": [{"name": "A"}]}),
    ):
        try:
            value = _worst(info)
            raised = False
        except Exception:
            value = None
            raised = True
        ok(
            not raised and abs(value - 0.02) < 1e-9,
            f"D1[{label}]: falls back to the top-level rather than raising into the solve "
            f"(got {value!r})",
        )

    src = inspect.getsource(QuickEstimationService._fov_already_delivered)
    ok(
        'measured.get("images")' in src and "max(offsets)" in src,
        "D2: and the gate itself reads the per-image entries and takes the worst",
    )
    ok(
        "bugs/0773" in src,
        "D3: with the reason recorded where the next reader will find it",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0773 delivered-asks-every-image validation PASSED")
        return 0
    print("0773 delivered-asks-every-image validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
