# 0963 -- the ribbon folds by the window's height, not the screen's

Noticed in bugs/0958; recommended next. The user said "please proceed recommended next."

## What was wrong

The ribbon decided ONCE, at start-up, from the SCREEN's height (`FOLD_BELOW_SCREEN_HEIGHT`, 1100
px) whether to start folded.

- **On M90aPro (a 1440-px screen)** the shell's 1500x950 window opened with the ribbon open, and the
  3D view was 339 px high.
- **Nothing followed the window afterwards.** Made short, the window kept the open ribbon; made tall
  (maximised), it kept a folded one.

## Change

The window's height decides (`FOLD_BELOW_WINDOW_HEIGHT`, 1100 px), at start-up and whenever the
window is resized (`KrakenQtMainWindow.resizeEvent` -> `Ribbon.follow_window_height`):

- **On crossing the line only:** below 1100 px the ribbon folds, above it opens. A resize that
  stays on the same side changes nothing, so a ribbon opened by code (Clean 3D Scene putting it
  back, for example) is not refolded on every resize.
- **By hand, it is the user's:** the fold arrow or a double-click on a tab (`Ribbon.fold_by_hand`)
  ends the following. The choice holds through any resize for the rest of the session.
- **Not while the ribbon floats**: its own window opens fully, as before.
- **Not while Clean 3D Scene is on**, which puts the ribbon back itself when it ends.

On X299-SSD (a 1034-px window) the ribbon starts folded, as before. On M90aPro a maximised window
(about 1400 px) opens it, as before. A 950-px window on the 1440-px screen now starts folded.

## Guards

- **New, `validate_qt_ribbon_window_height` (phase 732),** on a private 2560x1440 virtual screen (a
  TALL screen, where the old rule left the ribbon open):
  - **S:** a 950-px window starts folded.
  - **G:** 1300 px opens it (the 3D view 515 -> 779 px with the panels open); 950 folds it again; a
    programmatic open at 950 survives a resize to 940.
  - **H:** opened or folded by the arrow, it stays so through resizes to 1300, 940 and 1300.
  - **C:** with Clean 3D Scene on, a resize to 1300 leaves it folded; turned off, it puts back what
    it saved.
- **`validate_qt_ribbon` (714):** claim F now reads the window's height.

**Mutation-checked:**
- the screen's height again: S and G fail;
- no resize hook: G fails;
- a hand fold not kept: H fails;
- Clean 3D Scene not respected: C fails;
- refolding on every resize: G fails.

## Gates

By the cadence of 2026-10-05: own guard plus the guards that read this code (ribbon 714, scene
layout 724, clean scene 731, the Qt-hosted inspector, the 5f toolbar guard, the shell flag 729).
The next batch gate covers this. Full gate owed since 3265c622; it also covers 0962.
