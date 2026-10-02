# 0943 -- menu parity, part 2: the tolerance and path-detector commands ask through the UI host

After 0942, 21 Tk menu-bar commands had no Qt route. Probing showed 18 of them failed in the Qt
shell for one reason: they called `tkinter.messagebox`, `simpledialog` or `filedialog` directly.
Those dialogs never appear in the Qt shell, because its Tk root is withdrawn. The model's other
commands already ask through `host_of(...)`.

## Change

`panels/main_tolerance_report_dialogs.py` (36 calls) and `panels/main_path_detector_analysis.py`
(15 calls) now ask and report through `host_of(self)`. That is the editor's own UI host: Qt's
dialogs in the Qt shell, Tk's in the Tk editor.
- Their `tkinter` imports are gone.
- Tk is unchanged. Both panels resolve to the editor's `TkUiHost`, which looks tkinter up at call
  time, so validators that patch `tkinter.messagebox` keep working (0891, 0892).

That made 16 commands work in the Qt shell. Each got an `editor:` action:
- **Analysis → Tolerance**, a new submenu, in Tk's order (each report followed by its CSV):
  - the two preset actions move in from Analysis;
  - Monte Carlo, Worst-Sample, Stack-Up, Compensator Sweep and Multi-Compensator reports;
  - their CSVs, plus the overlay CSV.
- **File → Export Analysis CSV**, a new submenu:
  - Path PSF / MTF, Detector Map, Coherent Detector, Branch Field;
  - the wavefront and Zernike CSVs move in from File.

**Submenus.** The menu builder now nests submenus. A menu path like `"&Analysis/&Tolerance"` is a
submenu titled `&Tolerance`, placed in its parent where its first action is declared.

**Ribbon.** A new **Tolerance** tab has three groups: Run (Monte Carlo, Worst Sample, Stack-Up),
Compensators and Presets. The five reports have new icons.
- Measured: on the Analysis tab, the reports made that page 1478 px wide and the WINDOW at least
  1498 px (1240 before).
- With their own tab, Analysis is 1097 px and the window minimum is 1117 px, narrower than before.
- The Multi-Compensator icon was redrawn after a look at the render: the first version's nested
  ellipses read as an eye.

The 11 CSV exports are menu + palette only. Each needs its report or a trace first, so a ribbon
button would mostly refuse.

**Reclassified, not converted:** Lens Drawing Properties / Export Lens Drawing. Their real blocker
is a modal 1360x700 Tk window (`tk.Toplevel` + `wait_window`), not the message boxes. The gap
reason now says so.

## Guard: `validate_qt_menu_parity` (phase 718) gains a second Qt shell

The new claims run on `common_optical_layouts/native_variable_breadth_example.py`, the native
Var/VarBounds layout that `validate_tolerance_monte_carlo` uses:
- **E:** before any run, the 6 tolerance CSVs and the 3 reports that need a Monte Carlo run each
  refuse with exactly one host message ("... first").
- **T:** Monte Carlo asks its sample count and seed through the host and runs EXACTLY the 3
  asked. Worst-sample, stack-up, compensator sweep (steps asked) and multi-compensator (steps +
  passes asked) all run. Each of their 5 CSVs is asked for through the host and written.
- **P:** after Refresh Plot, the 5 path/detector exports ask through the host and write rows
  (2116 / 23 / 2116 / 3364 / 3364).
- **K:** across E, T and P, not one Tk dialog call. The guard records every
  messagebox / simpledialog / filedialog function.

The overlay CSV is covered through E's refusal path. A full overlay export takes 83 s here
(73k rows).

**S** now reads 75 Tk commands: 70 routed, 5 known gaps.

**Mutation-checked:**
- The tolerance panel at HEAD (Tk dialogs) fails E, T and K.
- The path-detector panel at HEAD fails P and K.

**Also re-run:** 0855 (Q1 now compares menu paths and submenu titles), the ribbon guard (51 ribbon
actions, every icon distinct), and the ungated `validate_tolerance_monte_carlo` and
`validate_machine_vision_case_study`.

## Remaining gaps (5)

- Lens drawing properties + export: one modal Tk window, which needs a session + Qt dialog port.
- Path-view component / stock-lens placement: these end in Tk row forms.
- Atmospheric Settings: a Tk window.
