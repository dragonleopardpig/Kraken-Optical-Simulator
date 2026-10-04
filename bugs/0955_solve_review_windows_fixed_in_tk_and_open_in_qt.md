# 0955 -- a table-cell solve's review window works again in Tk, and opens in Qt

Step 5 of "what is left" in `docs/design_qt_migration.md` (the paraxial solve prompts). It turned
out to be a bug in the Tk app first.

## What was broken, and since when

Three solves on the surface table compute a result and ask "apply this?" before they write:
Paraxial Solve This Thickness, Best Image Solve, and the folded mirror solve.

**In the Tk app, since 2026-05-24** (`d4c6642d`, "Move paraxial solve dialogs into panel"), every one
of them ended in an error box and applied nothing:

```
bad window path name "<KrakenOS.UI.panels.main_paraxial_analysis_dialogs.MainParaxialAnalysisDialogs object at 0x...>"
```

The three windows moved into a panel class that is not a widget: it only borrows the editor's
attributes. They kept `tk.Toplevel(self)` and `dialog.transient(self)`, which hands that object to
Tk as the parent. Measured at HEAD in the Tk app on the Pyrite 90 0.3X fixture: both menu entries
failed that way.

**In the Qt shell** the same code ran and failed with the same message (0948 listed "Best Image
Solve" as the one table-menu entry still ending in Tk).

## Change

- **One description** (`solve_reviews.py`, toolkit-free): `SolveReview` holds the title, the line
  saying what was solved, the (label, value) rows and the rule that produced them. Three builders
  make it from a solve's result.
- **One Tk window** (`_show_solve_review`) for all three, with the EDITOR as its parent. The three
  hand-built functions (about 210 lines) became three one-line calls.
- **A Qt dialog** (`qt/dialogs/solve_review_dialog.py`), modal, behind a `show_solve_review` seam:
  the solve waits for Apply / Cancel before it writes.

## Guards

**`validate_solve_review_windows` (phase 727):**
- **P:** the three descriptions from sample results: title, intro per target, rows (10 for an
  image or object solve, 14 for a thickness solve, 10 folded, 9 best image, +1 with a target path),
  and the rule.
- **T:** in the Tk app each of the three opens its window with no error box. Cancel leaves the
  row alone and says so; Apply writes the solved value.
- **Q:** in the Qt shell each opens a modal Qt dialog, with no Tk window and no error box; Cancel
  and Apply do the same. The two that are on the right-click menu are run from that menu.
- **E:** the Tk window and the Qt dialog show the same title, intro, row labels and rule, and the
  same numbers for the two paraxial solves.

Measured values (identical in both shells):

| Solve | Scene, row | Before | Solved | After Apply |
|---|---|---|---|---|
| Paraxial Solve This Thickness | Pyrite 90 0.3X, row 2 | 16.17883 | 16.1788 | 16.17884 |
| Best Image Solve | Pyrite 90 0.3X, row 5 | 95.0892 | 95.3389 | 95.3389 |
| Folded mirror solve | coating_polarization_example, row 3 | 25.0 | -42.1133 | -42.1133 |

**`validate_qt_table_context_menu` (phase 722):** its list of entries that still end in Tk is now
empty. All 118 distinct entries of the table's right-click menu run in Qt without a Tk window.

**Mutation-checked:**
- the Tk parent put back to the panel object, and the Qt seam removed: T and Q fail, with the
  original error text;
- the description dropping a row and swapping the rule: P fails.

**Re-pointed:** the interaction contract (phase 655) pinned the two window titles as literals in
the panel. They live in `solve_reviews` now; the contract checks that, and that the panel builds
and shows the three descriptions.

**Re-pointed too:** the reports guard (phase 684) carried the same title pin. The first targeted
gate failed on it (8 of 9); re-pointed and re-gated, 9 of 9 pass.

**Seen by eye:** the Qt dialog for a thickness solve, rendered to PNG.

**Swept for the same mistake:** every class that forwards attributes with `__getattr__` and is not
a widget was searched for `Toplevel(self)`, `transient(self)` and menus built on `self`. No other
instance.

## Found, not changed

- **The folded mirror solve has no menu entry.** `solve_current_folded_mirror_distance` exists and
  works, but nothing on any menu calls it, in either shell. The guard runs it by its command.
- **The image- and object-distance paraxial solves are switched off.**
  `_paraxial_solve_target_for_cell` returns `None` for every cell, so "Paraxial Solve Image
  Distance", "Paraxial Solve Object Distance" and the 2F entries are never offered. Their review
  description is covered by P.
- **The folded mirror solve returned a negative thickness** (-42.11 mm) on the example scene. That
  is the solve's own arithmetic (straight image gap minus the gap before the mirror); it is shown
  for review and applied as computed.
