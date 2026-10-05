# 0965 -- missing CAD files: found by name first, then a Qt window for the rest

The user chose option 1 (2026-10-05, "proceed"): find by name first, a Qt window only for what is
still missing, and a command to open it again.

## What was wrong

When a layout names STEP / STL files that are not on disk, the load opens the missing-assets
window (Locate, Locate folder, Skip). In the Qt shell that window was a Tk window on the hidden Tk
root, with no Tk event loop: invisible or frozen. The layout loaded with placeholders and there was
no way to fix it.

## Change

- **`services/missing_assets_session.py`** holds everything the window did -- Locate, Locate
  folder, Skip, Skip all, Reset, and the rebuild on close -- plus **find by name**
  (`auto_locate`). A missing file whose name matches exactly ONE file under the layout's folder or
  the project's `attachment/` folder is pointed at it. A name that matches two different files is
  left for the user, because a guess could put the wrong part in the scene.
- **The load** (`_prompt_for_missing_cad_assets`):
  - finds by name first, and logs each file found to the progress log;
  - the status line says "Found N missing CAD file(s) by name", and to save the layout to keep the
    new paths;
  - only what is still missing opens a window: the shell's (`show_missing_assets` -> a non-modal
    Qt dialog, `qt/dialogs/missing_assets_dialog.py`) or the Tk one (now a view of the same
    session).
- **Ribbon:** Scene > CAD > **Missing Files** ("Resolve Missing CAD Files..."), also in the command
  palette, opens it again, or says nothing is missing.

## Guard: `validate_missing_assets_found_by_name` (phase 734)

P1, P2 (the session), L (the load's step), Q (the Qt shell) and T (the Tk window) all pass.

## The commit shipped with a mutation in it (fixed, 6b44cf8f)

55af895d was committed while the mutation checks were under way (the user stopped the session to
leave), and one mutation was never undone: `_prompt_for_missing_cad_assets` read `shell = None`, so
the shell's `show_missing_assets` seam was never asked. In the Qt shell a layout with a missing CAD
file still opened the Tk window on the hidden Tk root -- the bug this report is about. Run at
55af895d the guard says so: **L, T and Q fail.**

6b44cf8f reads the seam off the editor again (`self.__dict__.get("show_missing_assets")`, the way
the sibling seams do); P1 P2 L T Q pass. The rest of the commit was read line by line and holds no
other leftover.

The rule it leaves: after a mutation check, `git diff` shows the fix and nothing else BEFORE the
commit. The checks below restore each mutation from a copy on every exit path, and end by asking
git whether the tree is clean.

## Checks (2026-10-05, M90aPro; every run alone, at low priority)

**Mutations: 28 of 28 caught, each by the claim it targets**; the tree was clean afterwards.

| Mutation | Caught by |
|---|---|
| an ambiguous name is guessed (`len(candidates) >= 1`) | P1 |
| an overlay's path is not rewritten; a row's path is not rewritten | P1 |
| Locate takes a folder; Skip writes no placeholder; Reset keeps the placeholder | P2 |
| `close()` redraws every time it is called; Locate folder resolves nothing | P2 |
| the layout's own folder is not searched | L |
| the load does not search by name; a file found by name is not logged; the status line does not say what was found | L |
| nothing left to ask: no redraw; a window opens although nothing is left | L |
| the shell is not asked (what 55af895d shipped) | L, Q |
| the Qt window does not install the seam; the window is made but never shown; it is modal | Q |
| the Qt Skip does nothing; Locate ignores the picked file; the list shows only the first entry | Q |
| closing the Qt window does not end the session (both `closeEvent` and `reject`) | Q |
| "nothing missing" is not said (the model's branch; the ribbon command's argument) | Q |
| the Tk Skip all does nothing; Continue does not end the session; the list is empty | T |
| the Tk window works on a session of its own instead of the one it was handed | T |

**Neighbouring guards, all pass:**
- phase 593 (0810): E1 the load still opens the Tk window non-modal, E2 it returns at once, F1 a
  real load rebuilds a moved-aside body with no dialog wait -- the search by name did not get in
  the way of the cache rebuild;
- phase 721 (model forms open in Qt): the census holds at 17 Tk-only calls in 7 listed windows (6 in
  `panels/missing_assets_dialog.py`); 20 form commands, 0 Tk windows;
- phase 714 (ribbon): 68 buttons + 6 dropdowns reach 101 of 101 actions, no blank or identical
  icon. The window's minimum width is 1234 px against the guard's 1240 cap -- 6 px left for the
  next ribbon button;
- phase 723 (inspector popups): 0 Tk popups, 0 waits on a Tk window;
- phase 718 (menu parity): 75 of 75.

**Baseline:** phase 734 is recorded (`penta_validator_gate.py --phases 734 --update-baseline`: 1 pass,
0 fail) -- so it passes inside the harness as well as alone.

## Full gate for the batch 0962-0965 (2026-10-05 evening, M90aPro, at 8403abde; the user's go)

**Tk: 733 of 733. Qt-hosted harness (`--shell qt`): 352 of 352.** Nothing is owed through 0965.

The Tk gate took two passes, and the reason is worth keeping:

- `tools/penta_parallel_gate.py --jobs 4`: 701 pass, 1 fail, **31 phases not reported**, 35.1 min.
  Another session started a test run in a different project while it ran (four workers, about
  8.5 GB of this machine's 15). Free memory fell to 2.0 GB; the watchdog requeued three groups and
  then gave up on seven that it had killed while each ran ALONE (448-456, 705-708, 717-734).
- The one failure, phase 704 claim W (the dispatched press-hold-drag carried the promoted row by
  nothing; the same gesture with Qt input carried it 8.901 mm), was the load: the guard passes
  alone, and passes in the harness in the second pass.
- Second pass, once that test run had ended: each unreported group through
  `penta_parallel_gate.py --jobs 1 --phases <group>`, started only above 7 GB free -- 448-456,
  701-704, 705-708, 717-720, 721-724, 725-728, 729-732, 733-734: **35 of 35 pass**. Counted from the
  `[PASS] Phase N` lines of both passes: every one of the baseline's 733 phases ends on a pass.

Two things about the tool this showed (not changed here):
- with nothing running it starts a group WHATEVER the free memory is (`not running or free >=
  start_gb`), so it cannot wait out another job's memory -- the caller has to;
- a group killed by the watchdog leaves its Xvfb's lock and socket behind (`/tmp/.X150-lock`,
  `/tmp/.X11-unix/X172` ...); they were removed by hand.
