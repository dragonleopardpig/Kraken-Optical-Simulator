# 0862 -- the Qt reports show what the Tk dialogs show, cell for cell

The user, after opening all five in the Qt shell: *"they pop up dialog with table and values in it
(although I can't verify they are correct)."*

A fair objection. The guards behind 0859-0861 compared each Qt table against the FORMATTERS the Tk
dialogs use -- a good argument, but not a demonstration: nothing had opened the two applications'
dialogs and compared what they actually display.

## What this adds

`validate_open3d_0862_qt_tk_report_parity.py` (penta phase 641) loads `om05a_folded.py`, runs the
same trace the Qt shell's redraw runs, then:

- opens all five **Tk** dialogs through the editor's own menu methods and reads each Treeview back
  -- headings and every cell;
- opens all five **Qt** dialogs in a subprocess and reads each table model back the same way;
- compares headings, shape, and a **SHA-256 over every cell**.

Result on `om05a_folded.py`:

| report | table | verdict |
|---|---|---|
| Paraxial Matrix | 25 x 17 | identical |
| Branch Gaussian Q | 2 670 x 15 | identical |
| Detector Aperture | 1 x 12 | identical |
| Path Throughput | 2 x 11 | identical |
| Source Illumination | 2 x 13 | identical |

So the Qt reports are not a second opinion: they are the same numbers the Tk editor has always
shown, and any question about whether those numbers are right is a question about the model, not
about the port.

A detail that would otherwise have hung the guard: a report dialog with nothing to show raises a
MODAL info box. The Tk half therefore replaces `messagebox.showinfo` / `showerror` /
`showwarning` for its duration and FAILS if any of them fired -- a blocked guard and an empty
report now both show up as a failure instead of a hang.
