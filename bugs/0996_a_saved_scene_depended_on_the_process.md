# 0996 -- the same scene, saved twice, gave two different files

Found while widening the session of bugs/0993 (phase 7f of the Qt migration) to saving a file. It
is not about Tk: it happens in the Tk editor as it did before.

## Symptom

Load a scene, File > Save As. Quit, start again, load the same scene, save again. The two files
differ -- 50 lines of 800 in the two-arm doublets -- although nothing was changed. In version
control every save of a layout shows a diff; two people saving the same scene get different files.

Measured: three fresh processes, the same scene, three different SHA-1s.

## Cause

`_collect_layout_settings` gathers each merit operand's settings for the file. It went over

    all_labels = {spec.label for spec in OPERAND_REGISTRY.values()}

a SET of the eight labels. The order of a set of strings follows their hashes, and Python salts
string hashes per process. So the `'operands'` block was written in an order that is the process's:
`EFFL, MTF @ freq, Exit pupil z, ...` in one, `Entrance pupil z, MTF @ freq, EFFL, ...` in the
next.

As data the files were always equal -- loading does not care about the order -- which is why it
went unnoticed: the comparison of two editors only saw it when it compared the bytes of what each
had saved.

## Fix

The operands are written in the operand list's own order (the registry's, which is the order the
optimization panel shows them in): `Spot RMS, Wavefront RMS, EFFL, Magnification, Entrance pupil z,
Exit pupil z, Thickness penalty, MTF @ freq`.

A file saved before loads exactly as it did. Saving it again puts its operands in that order.

## Proof

`bugs/0996_save_across_processes.py` saves one scene from three fresh processes with different
hash seeds:

- before: three different files;
- after: one file, byte for byte -- and the same file again from a Tk-rooted editor;
- loaded as data, the three files written before and the ones written after are all equal.

The Tk-rooted editor's model is otherwise unchanged: `bugs/0993_tk_before_after.py` runs the
guard's session at the commit before (twice) and after. The two runs BEFORE disagree with each
other in exactly one thing, the saved file; with the fix nothing differs between runs.

## Guard: `validate_editor_without_tk_root` (phase 759), extended

The session grew by twelve steps -- choosing analyses, an input of an analysis, Save As, an edit,
Save, another edit, opening the saved file -- and its two processes now run under different hash
seeds on purpose.

- **F:** the editor with a Tk root and the one without, in two processes with hash seeds 1 and
  2, save the same scene as the same file byte for byte, at Save As and again at Save after an
  edit; the operands in it are in the operand list's order; opening the file brings back what was
  saved (thickness 6.5), not the edit made after (9.75).
- **S:** the saved file's digest, the analyses chosen and which inputs apply are among the
  attributes compared after every step; the list of known differences is still empty.
- **R:** the analyses chosen are the model's, and an input that belongs to an analysis (the
  tolerance view, the detector bins) applies exactly while that analysis is chosen.

Nothing else was found by the wider session: with the analyses and the file, the editor without a
Tk root is still the Tk-rooted editor's model in every plain attribute.
