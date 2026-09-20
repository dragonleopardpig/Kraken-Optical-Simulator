"""Guard for bugs/0825 -- one shared shape for "this number should not be believed".

optiland's NSQ quick-start ends ``print(result.report())  # self-diagnosing summary --
read this first``. KrakenOS has fifteen separate report/summary surfaces and, before
bugs/0822, no shared way for any of them to say a number is untrustworthy. Each
invented its own or said nothing.

Three rules are enforced by the vocabulary rather than left to each caller, because
each already cost a bug:

  1. silence never means fine (bugs/0822) -- an empty finding list renders as
     "nothing was measured", so a caller that forgot to run its diagnostics cannot
     look identical to a result that passed them;
  2. a warning names a remedy, or states that none exists (bugs/0777 shipped
     "move the device stage / camera focus to land it" for a blur no move could
     shrink -- an unfollowable remedy is worse than none);
  3. warnings lead.

Checks (display-free, pure):
  A  warnings render above info, with their numbers and their remedy;
  B  an empty list says nothing was measured, and does NOT read as clean;
  C  a WARNING with no remedy is refused AT CONSTRUCTION -- the 0777 rule is
     structural, not a convention;
  D  NO_REMEDY is accepted, counted as unactionable, and surfaced in the text;
  E  a bad severity or an empty code is refused;
  F  summary_line gives the worst finding for a status bar, and distinguishes
     "nothing ran" from "all passed";
  G  illumination_findings reproduces the bugs/0822 conclusions under stable codes,
     on the real MV-150 8000-ray shape;
  H  the bugs/0822 text function is untouched, so existing readers do not shift.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0825_read_this_first
"""

from __future__ import annotations

import numpy as np


def _mv150_counts():
    """The measured 8000-ray MV-150 map: 1726 FOV hits across 1479 lit bins."""
    counts = np.zeros(124 * 124, dtype=float)
    counts[:1479] = 1726 / 1479
    return counts


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.result_diagnostics import (
        INFO,
        NO_REMEDY,
        WARNING,
        Finding,
        read_this_first,
        summary_line,
        warnings_of,
    )
    from KrakenOS.UI.source_illumination_analysis import (
        illumination_diagnostic_lines,
        illumination_findings,
    )

    warn = Finding("a.warn", WARNING, "the map is noise", "1.2 hits/bin", "Launch more rays.")
    info = Finding("a.info", INFO, "ledger closes", "in = hit + missed")

    # ---- A: warnings lead ------------------------------------------------------------------------
    text = read_this_first([info, warn])
    body = "\n".join(text)
    warn_at = next(i for i, ln in enumerate(text) if "a.warn" in ln)
    info_at = next(i for i, ln in enumerate(text) if "a.info" in ln)
    ok(warn_at < info_at,
       f"A1: the warning renders above the info line even when listed after it "
       f"({warn_at} < {info_at})")
    ok("1.2 hits/bin" in body, "A2: the warning carries its numbers, not just a verdict")
    ok("-> Launch more rays." in body, "A3: and its remedy, marked as the action")
    ok(body.splitlines()[1].startswith("1 warning"),
       f"A4: the count is the first thing after the title (got {body.splitlines()[1]!r})")

    # ---- B: empty is not clean --------------------------------------------------------------------
    empty = "\n".join(read_this_first([]))
    ok("Nothing was measured" in empty and "NOT a clean result" in empty,
       "B1: an empty finding list says nothing ran, and says it is not a pass")
    ok("No warnings" not in empty,
       "B2: and it must NOT read like the no-warnings case")
    clean = "\n".join(read_this_first([info]))
    ok("No warnings. What was checked:" in clean and "ledger closes" in clean,
       "B3: a genuinely clean result still prints what it checked (bugs/0822 rule)")

    # ---- C: a warning without a remedy cannot be built -- the 0777 rule ---------------------------
    try:
        Finding("a.bad", WARNING, "something is wrong")
        refused = False
    except ValueError as exc:
        refused = "0777" in str(exc) and "remedy" in str(exc)
    ok(refused,
       "C1: a WARNING with no remedy is refused at construction, citing 0777")
    ok(Finding("a.ok", INFO, "fine") is not None,
       "C2: an INFO finding needs no remedy -- the rule is about warnings")

    # ---- D: NO_REMEDY is a stated conclusion -----------------------------------------------------
    blocked = Finding("a.blocked", WARNING, "the blur is not defocus", "230 um both", NO_REMEDY)
    ok(blocked.actionable is False, "D1: a NO_REMEDY warning is not actionable")
    ok(warn.actionable is True, "D2: a warning with a real remedy is")
    blocked_text = "\n".join(read_this_first([blocked]))
    ok("no available action" in blocked_text and NO_REMEDY in blocked_text,
       "D3: the text both counts it and states that no action exists")
    ok("no available action" not in "\n".join(read_this_first([warn])),
       "D4: and does not say that when every warning is actionable")

    # ---- E: malformed findings are refused -------------------------------------------------------
    for bad_kwargs, label in (
        (dict(code="x", severity="fatal", summary="s"), "an unknown severity"),
        (dict(code="   ", severity=INFO, summary="s"), "an empty code"),
    ):
        try:
            Finding(**bad_kwargs)
            raised = False
        except ValueError:
            raised = True
        ok(raised, f"E: {label} is refused")

    # ---- F: the status-bar line ------------------------------------------------------------------
    ok(summary_line([]) == "no diagnostic ran",
       "F1: nothing measured is distinguishable from everything passing")
    ok(summary_line([info]) == "1 check passed", f"F2: a clean run says so (got {summary_line([info])!r})")
    ok(summary_line([warn, info]).startswith("1 warning: the map is noise"),
       f"F3: the worst finding leads (got {summary_line([warn, info])!r})")
    ok("no available action" in summary_line([blocked]),
       "F4: an unactionable warning is flagged as such in one line")
    ok(len(warnings_of([warn, info, blocked])) == 2, "F5: warnings_of filters to warnings")

    # ---- G: the 0822 conclusions, under stable codes, on the real MV-150 shape --------------------
    recs = [{"input_power": 1.0, "hit_power": 0.7, "missed_power": 0.3,
             "launched_rays": 8000, "hit_rays": 1726, "missed_rays": 6274}]
    found = illumination_findings(map_data={"counts": _mv150_counts()},
                                  records=recs, launched_rays=8000)
    codes = {f.code for f in found}
    ok("illumination.undersampled" in codes,
       f"G1: the 8000-ray MV-150 map is flagged undersampled (codes {sorted(codes)})")
    ok("illumination.ledger" in codes,
       "G2: and its closing flux ledger is reported as an INFO finding, not omitted")
    under = next(f for f in found if f.code == "illumination.undersampled")
    ok(under.severity == WARNING and under.actionable,
       "G3: the undersampling warning is actionable -- a ray count exists")
    ok("1.17" in under.detail and "92" in under.detail,
       f"G4: it carries the measured density and error (got {under.detail!r})")
    ok("bin coarser" in under.remedy,
       "G5: and the remedy offers the cheap fix the rebin sweep found, not only more rays")
    leaky = illumination_findings(
        records=[{"input_power": 1.0, "hit_power": 0.4, "missed_power": 0.2,
                  "launched_rays": 1000, "hit_rays": 400, "missed_rays": 200}])
    leak_codes = {f.code for f in leaky}
    ok({"illumination.ray_ledger", "illumination.power_ledger"} <= leak_codes,
       f"G6: both ledger leaks surface as separate coded findings (got {sorted(leak_codes)})")
    ok(illumination_findings() == [],
       "G7: nothing measured yields no findings -- read_this_first names that, not this")

    # ---- H: the bugs/0822 text surface is unchanged ----------------------------------------------
    legacy = illumination_diagnostic_lines(map_data={"counts": _mv150_counts()}, launched_rays=8000)
    ok(any(ln.startswith("WARNING:") and "shot noise" in ln for ln in legacy),
       "H1: the 0822 line renderer still emits its original WARNING text")
    ok(len(legacy) == 1, f"H2: and still exactly one line for a map alone (got {len(legacy)})")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0825 read-this-first validation PASSED")
        return 0
    print("0825 read-this-first validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
