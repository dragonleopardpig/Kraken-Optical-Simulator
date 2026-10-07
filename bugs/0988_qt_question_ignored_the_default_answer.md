# 0988 -- in the Qt shell, Enter answered Yes to "Replace the scene now?"

Found while moving the table's Tk code (0987): one question in the model is asked with a default
answer, and the two shells did not agree on what Enter does.

## What happened

"Import Lens from Folder" loads a fresh single-lens layout and throws the working scene away. When
that scene holds a camera body, an LED, an imported optical STEP or a promoted solid, the model asks
first (bugs/0381):

> Importing a lens from a folder REPLACES the entire working scene ... Replace the scene now?

and asks it with `default="no"`, so that Enter keeps the scene.

- **Tk:** the message box honours the default. Enter answers No.
- **Qt:** the host's `askyesno` dropped the option. Measured on the real dialog: no default button,
  the focus on Yes, and Enter answered Yes -- the scene was replaced.

The same was true of the host's other three questions; no other caller passes a default today.

## Fix

`uihost/qt_host.py`: `askyesno`, `askokcancel`, `askyesnocancel` and `askretrycancel` hand Qt the
default button that Tk's `default=` names ("yes", "no", "ok", "cancel", "retry"). With no default,
or a word that is no button of that dialog, nothing changes: the affirmative button answers, which
is Tk's first button.

The Tk interface is unchanged.

## Guard: `validate_qt_question_default` (phase 754)

- **P:** the Tk host hands `default` to tkinter unchanged, for each of the four questions.
- **M:** the model's question, on a headless editor -- not asked when there is nothing to discard;
  with a camera body attached, asked once with `default="no"`, and answered no the scene is kept,
  the status says so, and no folder is asked for.
- **Q:** sixteen real Qt dialogs opened by the host and answered by pressing Enter -- with a default,
  that button is the dialog's default button, has the focus, and is what Enter answers.
