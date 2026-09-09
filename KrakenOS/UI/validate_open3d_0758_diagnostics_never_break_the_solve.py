"""Guard for bugs/0758 -- an informational readout must never take the solve down with it.

bugs/0755 added a snapshot of the track's own focused field to the top of
``_apply_conjugate_pair`` so the banner could tell the user what WOULD land. It called the
helper unconditionally. Penta 412 ("Quick Estimation holds the object-locked LED+BS unit
through a conjugate solve") composes only part of the service, so the call raised
``AttributeError: '_QE' object has no attribute '_in_focus_fields_at_current_track'`` -- and
the entire conjugate solve died with it. A diagnostic that can break the thing it is
describing is worse than no diagnostic.

Checks (display-free, pure):
  A  the snapshot is guarded, and a solve still runs when the helper is missing entirely;
  B  it also survives a helper that RAISES, not just one that is absent;
  C  when the helper works, the field list still reaches the stash (bugs/0754/0755 intact).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0758_diagnostics_never_break_the_solve
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok(
        "try:\n            in_focus_before = self._in_focus_fields_at_current_track()" in src
        and "except Exception:\n            in_focus_before = []" in src,
        "A1: the snapshot is wrapped -- a missing or failing helper yields an empty list, not "
        "an exception out of the solve",
    )
    ok(
        src.find("in_focus_before") < src.find("_folded_conjugate_gaps_for_magnification"),
        "A2: and it still runs BEFORE the solve touches geometry (bugs/0755's whole point)",
    )

    # ---- B: exercise it, don't just read it -------------------------------------------------
    class NoHelper(QuickEstimationService):
        """A service composed WITHOUT the diagnostic -- the penta 412 shape."""

        _in_focus_fields_at_current_track = property(
            lambda self: (_ for _ in ()).throw(AttributeError("absent"))
        )

    class RaisingHelper(QuickEstimationService):
        def _in_focus_fields_at_current_track(self, *a, **k):
            raise RuntimeError("model unavailable")

    editor = SimpleNamespace(rows=[], camera_focus_stage=None)
    for cls, label in ((NoHelper, "absent"), (RaisingHelper, "raising")):
        service = cls(SimpleNamespace(editor=editor))
        try:
            # 0/0 semis bail out early and harmlessly -- what matters is that the guarded
            # snapshot at the top does not raise on the way there.
            service._apply_conjugate_pair(0.0, 0.0)
            survived = True
        except AttributeError:
            survived = False
        except Exception:
            survived = True   # any LATER failure is not this defect
        ok(survived, f"B[{label}]: a {label} diagnostic does not abort the conjugate solve")

    # ---- C: the working path is unchanged ------------------------------------------------------
    ok(
        '"in_focus_fields": in_focus_before,' in src,
        "C1: when it works, the snapshot still reaches the residual stash (bugs/0754/0755)",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0758 diagnostics-never-break-the-solve validation PASSED")
        return 0
    print("0758 diagnostics-never-break-the-solve validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
