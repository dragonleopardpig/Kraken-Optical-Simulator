"""bugs/0825: one place a result says what is wrong with it, before its numbers.

optiland's NSQ result carries a `diagnostics` object and its quick-start says
``print(result.report())  # self-diagnosing summary -- read this first``. KrakenOS has
fifteen separate ``*_report_text`` / ``*_summary_text`` surfaces and no shared shape
for "this number should not be believed", so each analysis invents its own or says
nothing. bugs/0822 added the first real one; this is the vocabulary the rest can use.

Three rules are encoded here rather than left to each caller, because each already
cost a bug:

1. **Silence never means fine.** A clean result still prints what was checked
   (bugs/0822). An empty finding list renders "nothing was measured", never a blank.
2. **A finding names its remedy, or states that none exists.** bugs/0777 shipped a
   banner ending "move the device stage / camera focus to land it" for a blur no move
   could shrink. An unfollowable remedy is worse than no remedy, so ``remedy`` is
   required to be either actionable or explicitly absent.
3. **Warnings lead.** A reader who stops after the first screen must have seen the
   problems, not the preamble.
"""

from __future__ import annotations

from dataclasses import dataclass

WARNING = "warning"
INFO = "info"

#: A finding that has no action the user can take says exactly this, so "no remedy"
#: is a stated conclusion rather than an author forgetting the field.
NO_REMEDY = "No action can change this -- it is a property of the configuration."


@dataclass(frozen=True)
class Finding:
    """One thing an analysis concluded about its own result.

    Attributes:
        code: Stable dotted identifier, e.g. ``"illumination.undersampled"``. Stable
            so a guard can assert on it without matching prose.
        severity: ``WARNING`` (the number should not be believed as-is) or ``INFO``
            (measured and fine -- still printed, per rule 1).
        summary: One line stating the conclusion.
        detail: The numbers behind it. Optional but strongly preferred: a verdict
            without its measurement is the thing this module exists to replace.
        remedy: What to do about it. For a WARNING this must be non-empty -- pass
            ``NO_REMEDY`` when nothing can be done, which is itself the finding.
    """

    code: str
    severity: str
    summary: str
    detail: str = ""
    remedy: str = ""

    def __post_init__(self) -> None:
        if self.severity not in (WARNING, INFO):
            raise ValueError(f"unknown severity {self.severity!r}")
        if not str(self.code).strip():
            raise ValueError("a finding must carry a stable code")
        if self.severity == WARNING and not str(self.remedy).strip():
            raise ValueError(
                f"warning {self.code!r} has no remedy: pass an action, or NO_REMEDY "
                f"to state that none exists (bugs/0777)"
            )

    @property
    def actionable(self) -> bool:
        return self.severity == WARNING and self.remedy != NO_REMEDY


def warnings_of(findings) -> list[Finding]:
    return [f for f in findings if f.severity == WARNING]


def read_this_first(findings, *, title: str = "Read this first") -> list[str]:
    """Render findings with the problems at the top.

    An empty list is not silence: it renders an explicit statement that nothing was
    measured, so a caller that forgot to run its diagnostics cannot look identical to
    a result that passed them.
    """
    findings = list(findings)
    lines = [f"# {title}"]
    if not findings:
        lines.append(
            "Nothing was measured. This is NOT a clean result -- no diagnostic ran."
        )
        return lines

    warns = warnings_of(findings)
    infos = [f for f in findings if f.severity == INFO]

    if warns:
        unactionable = [f for f in warns if not f.actionable]
        lines.append(
            f"{len(warns)} warning{'s' if len(warns) != 1 else ''}"
            + (f", {len(unactionable)} with no available action" if unactionable else "")
            + ":"
        )
        for f in warns:
            lines.append(f"  WARNING [{f.code}] {f.summary}")
            if f.detail:
                lines.append(f"    {f.detail}")
            lines.append(f"    -> {f.remedy}")
    else:
        lines.append("No warnings. What was checked:")

    for f in infos:
        lines.append(f"  ok [{f.code}] {f.summary}")
        if f.detail:
            lines.append(f"    {f.detail}")
    return lines


def summary_line(findings) -> str:
    """One line for a status bar: the worst thing found, or that nothing ran."""
    findings = list(findings)
    if not findings:
        return "no diagnostic ran"
    warns = warnings_of(findings)
    if not warns:
        return f"{len(findings)} check{'s' if len(findings) != 1 else ''} passed"
    blocked = sum(1 for f in warns if not f.actionable)
    text = f"{len(warns)} warning{'s' if len(warns) != 1 else ''}: {warns[0].summary}"
    if blocked:
        text += f" ({blocked} with no available action)"
    return text
