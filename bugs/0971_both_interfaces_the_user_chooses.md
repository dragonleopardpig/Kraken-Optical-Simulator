# 0971 -- both interfaces stay, and the user chooses which one opens

Phase 7h and 7i of the Qt migration (docs/design_qt_migration.md), decided by the user.

Asked whether Tk would be kept or retired once Qt was the default (2026-10-06): **"I would like to
have both TK and QT available, let user to choose his usage preference."**

So Tk is not retired, there is no single default to flip, and which interface opens belongs to
whoever starts the program.

## What there was

Two commands, one per interface, and no way to say which you wanted without knowing both:
`python -m KrakenOS.UI.layout_editor` (Tk, the only one the README names) and
`python -m KrakenOS.UI.qt.app` (Qt). Nothing was remembered between runs; the program kept no
per-user settings at all.

## Change

**One command: `python -m KrakenOS.UI [layout.py]`.** Which interface it opens is decided, in order,
by:

1. the command line -- `--shell qt`, `--shell=tk`, `--qt`, `--tk` -- for this run only;
2. the environment -- `KRAKEN_UI_SHELL=qt` -- for this run only;
3. the saved preference;
4. nothing decides: **the user is asked**, once, in a small window offering both with a line about
   each. "Remember my choice" is ticked; untick it to be asked again next time.

- **The preference is changed from inside either interface:** File > **Interface Preference...** in
  the Tk interface, Help > **Interface Preference...** in the Qt ribbon (and its command palette).
  It is ONE form (`row_forms/interface_preference.py`) that both interfaces show: the interfaces
  that can run here, plus "Ask me at every start". It names the interface that is running, and says
  the change takes effect at the next start -- the running window is not swapped under the user.
- **An interface that cannot run here is not offered,** and asking for it falls back to the other
  with a line saying why (Qt needs PySide6, which a plain pip install does not bring).
- **`user_preferences.py`** is the per-user file: `preferences.json` under `~/.config/krakenos`
  (`%APPDATA%/KrakenOS`, `~/Library/Application Support/KrakenOS`). A missing or broken file reads
  as no preferences; a folder that cannot be written is reported, never raised.
  `KRAKEN_CONFIG_DIR` moves it -- every guard uses a temp folder.
- **`launcher.py`** holds the decision, toolkit-free but for the first-run window.
- The Tk entry point takes a layout to open, as the Qt one already did.
- The two old commands still start their own interface directly.

The README's "Running" section names the new command.

## Guard: `validate_interface_preference` (phase 739)

- **P1:** the file -- round trip, another key kept, None removes, a non-JSON file read as nothing
  and saved over, an unwritable folder reported.
- **P2:** the decision -- the four spellings; command line over environment over saved; the request
  removed from what is passed on; an unknown name refused on the command line and ignored in the
  environment or the file; fallback with a note; a refusal when nothing can run.
- **P3:** the first-run question -- both offered, Qt first; remembered only when told to; closing
  it starts nothing; with one interface installed nothing is asked.
- **P4:** the form -- what it offers, what it opens on; Apply writes the file and the START
  DECISION reads it back; "ask me" removes it; an unknown choice refused.
- **L:** the launcher run as the real command (a dry run that starts nothing): with nothing set it
  says it would ask and asks nothing; each source; exit 2 on an unknown interface; and the dispatch
  to each interface's entry point.
- **W:** the first-run window itself.
- **T:** the Tk File menu's entry opens the form's window; Apply there writes the file.
- **Q:** the Qt action is in the Help dropdown, opens a Qt dialog and no Tk window, on the saved
  choice and naming the running interface; a real click on Apply writes the file.

**Seen by eye:** the first-run window and the form in the Qt interface.

## Checks (2026-10-06, X299-SSD; every run alone, at low priority)

**Mutations: 19 of 19 caught, each by the claim it targets**; every one restored from a copy, the
tree clean afterwards.

| Mutation | Caught by |
|---|---|
| a preferences file that is not JSON is fatal; saving one preference drops the others; an unwritable folder raises | P1 |
| the command line does not decide; the environment is ignored | P2, L |
| the request is passed on to the interface; an interface that cannot run here is started anyway | P2 |
| the first-run answer is saved though "remember" is unticked; asked with one interface installed; the question opens on Tk | P3 |
| the form does not save | P4, T, Q |
| the form opens on "ask me" whatever is saved | P4, Q |
| the form does not name the running interface | Q |
| asking for Qt starts Tk; the Tk interface is started without the layout | L |
| "Remember my choice" starts unticked | W |
| the Tk File menu loses the entry | T |
| the Qt action is in no dropdown | Q |
| the editor's command opens nothing | T, Q |

**What the first mutation run found, in the program and in the guard** (dc16f325):
- with the command line or the environment not deciding, the launcher's DRY RUN opened the first-run
  question and waited on it. A dry run must start nothing and ask nothing: it now reports
  `shell=(ask)` and stops. (The guard hung five minutes on it, then crashed.)
- a claim that raised took the whole guard down with it. Each claim now fails on its own, a hung
  dry run is a failed claim after 90 s, and a view's check that crashes is reported under its own
  letter.

**Neighbouring guards, all pass:**
- the ribbon (714): 68 buttons + 6 dropdowns listing 34 commands reach 102 of 102 actions; the
  window's minimum width is unchanged at 1234 px (the command sits in a dropdown);
- menu parity (718): 76 Tk menu-bar commands, 76 routed in Qt;
- the model-forms census (721), the interaction contract (655), the tkinter-import list (738) and
  the model-variable registry (631).

**The real preferences folder was never touched** (`~/.config/krakenos` does not exist after all of
this): every run pointed `KRAKEN_CONFIG_DIR` at a temp folder.

**Baseline:** phase 739 recorded (1 pass, 0 fail). The full Tk gate is owed since 8403abde.

