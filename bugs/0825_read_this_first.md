# 0825 -- one shared shape for "this number should not be believed"

Not a flag. optiland's NSQ quick-start ends:

    print(result.report())       # self-diagnosing summary -- read this first

KrakenOS has fifteen separate `*_report_text` / `*_summary_text` surfaces and, before
bugs/0822, no shared way for any of them to say a number is untrustworthy. Each
analysis either invented its own wording or said nothing, and saying nothing was
indistinguishable from passing.

## Three rules, enforced by the vocabulary

Each of these already cost a bug, so none is left to the caller's discretion.

**1. Silence never means fine.** An empty finding list renders as *"Nothing was
measured. This is NOT a clean result -- no diagnostic ran."* A caller that forgot to
run its diagnostics cannot look like a result that passed them. (bugs/0822)

**2. A warning names a remedy, or states that none exists.** bugs/0777 shipped a
banner ending *"move the device stage / camera focus to land it"* for a blur no move
could shrink -- the sensor already sat at the waist. An unfollowable remedy is worse
than no remedy. `Finding.__post_init__` **refuses to construct** a WARNING with an
empty remedy and names 0777 in the error; `NO_REMEDY` is the way to say nothing can
be done, which is itself the finding and is counted and printed as such.

**3. Warnings lead.** A reader who stops after the first screen must have seen the
problems. The count is the first line after the title.

## What shipped

`KrakenOS/UI/services/result_diagnostics.py`: `Finding` (stable dotted `code`,
severity, summary, detail, remedy), `read_this_first(findings)`, `summary_line` for a
status bar, `warnings_of`. Codes are stable so a guard asserts on
`illumination.undersampled` rather than on prose.

`source_illumination_analysis.illumination_findings()` re-expresses the bugs/0822
verdicts in that vocabulary. The original `illumination_diagnostic_lines` is
**untouched** and still emits its own text, so no existing reader shifts -- the 0822
guard passes unchanged, and that is asserted here rather than assumed.

The undersampling remedy now also offers the cheap fix the MV-150 rebin sweep found:
*"or bin coarser, which buys the same confidence far cheaper"*. At 120k rays the auto
128-bin grid reads 49.7% error while 32 bins read 13.3% on the same data.

## Deliberately not done

The other thirteen report surfaces are not converted. The vocabulary exists and the
first analysis uses it; converting the rest is mechanical but each needs its own
thresholds argued, and inventing thresholds to fill a template is how a diagnostic
becomes decoration.

## Guard

`KrakenOS/UI/validate_open3d_0825_read_this_first.py`, penta phase 604. Display-free:
warning ordering and content, empty-is-not-clean in both directions, construction-time
refusal of a remedy-less warning, `NO_REMEDY` accounting, malformed-finding refusal,
the status line, the 0822 conclusions under stable codes on the real MV-150 8000-ray
shape, and the 0822 text surface being unchanged.
