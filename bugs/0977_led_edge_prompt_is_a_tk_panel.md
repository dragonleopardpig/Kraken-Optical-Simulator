# 0977 -- the LED edge-distance window: out of the placement service

Phase 7d of the Qt migration (docs/design_qt_migration.md), second part, third service.

## What was there

`services/scene_placement_commands.py` imported tkinter for one small window: "LED Edge Distance",
a value with Save and Cancel, which the Tk app opens for **Set LED edge distance**. Under another
shell the same method already asked through the shell's own number prompt (bugs/0950). The rest of
the service's tkinter was four `tk.Misc` annotations and an unused `messagebox`.

## Change

- The window is `panels/main_led_edge_prompt.py`, class `MainLedEdgePrompt` -- the same window, moved:
  hand-centred on the screen, Return saves, Escape cancels, a value that is no number says so on
  the status line and leaves the window open.
- The service's `_ask_led_edge_distance` keeps its name and its two answers: a shell is asked
  first; otherwise it delegates to the panel.
- The service imports no tkinter. Phase 738's list goes from five services to **four**.

Nothing a user sees changes in either interface.

## Guard: `validate_led_edge_prompt_view` (phase 744)

What the two interfaces do with the whole command on a real scene is phase 723's (its Q2 and T).
This guard holds what that one does not:

- **S:** the service imports and names no tkinter and builds no window; the method reaches the shell
  before it delegates; the panel defines the method.
- **M:** under a shell, with no display -- the prompt's title, text, prefill and floor of zero; the
  answer, a negative answer as zero, a cancel as None; the Tk panel never built.
- **T:** the Tk window in a real Tk editor -- title, prompt, prefill, buttons, keys; Save takes the
  value, a negative one as zero; "abc" leaves the window open with "Invalid LED edge distance.";
  Cancel gives None.

## Checks

**Mutations: 9 of 9 caught** -- under a shell a negative answer not floored, the prompt asked with
no floor, the Tk panel asked for anyway; the service importing tkinter again; the Tk window not
flooring a negative value, closing on a value that is no number, not prefilled, Escape unbound, or
parented to the panel object.

**Neighbouring guards, all pass:** the tkinter-import list (738), the inspector's popups in both
interfaces (723), the panel delegations, the two LED distance guards (139, 280), the interaction
contract (655). **Baseline:** phase 744 recorded.
