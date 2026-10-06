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
- **L:** the launcher run as the real command (a dry run that starts nothing) for each source, exit
  2 on an unknown interface; and the dispatch to each interface's entry point.
- **W:** the first-run window itself.
- **T:** the Tk File menu's entry opens the form's window; Apply there writes the file.
- **Q:** the Qt action is in the Help dropdown, opens a Qt dialog and no Tk window, on the saved
  choice and naming the running interface; a real click on Apply writes the file.

**Seen by eye:** the first-run window and the form in the Qt interface.
