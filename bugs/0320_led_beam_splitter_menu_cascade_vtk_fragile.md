# 0320 — "Add Beam Splitter to LED" did nothing: the cascade submenu never posts over VTK

## Flags
- `flag_20260716_074704_854` — *"right click add BS cube still functioning. No status
  bar message."* (i.e. still NOT functioning)
- `flag_20260716_073108_117` — *"After right click add BS cube, nothing happened."*

Both post-restart, on the fixed 0319 checkout. State: `promoted_solid_rows = [1, 8]`
(no BS row), no status line.

## Why the 0319 "restart fixes it" conclusion was wrong
The 0319 follow-up (`e33ac3ab`) fixed a real `TypeError` (`path=` missing from the mixin
wrapper) and concluded the user's failing recording was a *stale pre-fix app* — restart
to pick up the fix. The user restarted **and it still failed**. The `path=` fix was
necessary but not the whole story.

## Root cause — the Tk cascade submenu is unreliable inside the VTK-embedded inspector
The arbiter is the live debug log (`~/.cache/krakenos/logs/kraken_debug_latest.log`),
which records every menu command that fires. On a **fresh** process (07:45:30, fixed
code):
- the user right-clicked the LED (`right_click_step_face_match led F002` — the menu was
  built and posted, cascade included);
- **direct** commands in that same menu fired fine — `hide_step_overlay_from_context`
  for `lens` and `camera`;
- there was **no** `add_beam_splitter…` and **no** `Add Beam Splitter to LED … failed`
  line anywhere → the cascade command **was never invoked**.

Proven by two headless repros that the command, the menu build and a programmatic submenu
invoke are all fine:
- `bugs/repro_0319bis_context_path.py` — `add_beam_splitter_to_led("cube")` through the
  real context object adds S9/S10 + coats the diagonal.
- `bugs/repro_0319ter_menu_wiring.py` — builds the real LED menu, resolves the "Add Beam
  Splitter to LED" cascade's submenu via `nametowidget`, and `submenu.invoke(0)` fires the
  Cube command end to end (rows 10→11, S9, coating S001/F003, all status lines).

So neither the command nor the menu construction is broken. The only untested link was the
**interactive** cascade in the real window — and that is exactly where it fails:

The Open 3D inspector embeds a **VTK render-window interactor** (`vtkTkRenderWidget`)
that competes for the pointer inside its window. A Tk **cascade** needs a hover /
pointer-enter to *post* its submenu; under the VTK interactor that submenu frequently
never posts. The user clicks the "Add Beam Splitter to LED ▸" parent, no submenu opens,
nothing fires, and there is no status line — precisely the recording. A **direct**
single-click command needs no hover-to-post, which is why "Hide `<STEP>`" always worked in
the same menu. (The 2D main table uses cascades heavily — Material, Coating, Convert
Type — and those work, because there is no VTK interactor stealing the pointer there. So
this is scoped to the 3D inspector's menu, not Tk cascades in general.)

## Fix
`open3d_face_assignment.py` (`append_element_context_actions`, LED branch): replace the
`"Add Beam Splitter to LED" ▸ {Cube, Plate}` **cascade** with two **direct** commands:
- `Add Beam Splitter to LED (Cube)`
- `Add Beam Splitter to LED (Plate)`

Same `_add_beam_splitter_to_led_from_context(kind)` handler, no submenu, single click.
The BS action is a fixed two-way choice, so a cascade bought nothing; other inspector
cascades (Row Actions / Register STEP camera / Aberration exaggeration) group long or
dynamic lists where a cascade is still the right UX — if any of *those* prove unreachable
in the VTK window, they get the same treatment, but they are not reported.

## Verified (display-free)
`KrakenOS/UI/validate_open3d_led_beam_splitter_menu_command.py` — **PASS**:
- **A** the LED menu adds **no** cascade whose label mentions "Beam Splitter";
- **B** it adds exactly two direct commands, `…(Cube)` and `…(Plate)`;
- **C** invoking each reaches the real handler and calls
  `editor.add_beam_splitter_to_led("cube")` then `("plate")` — a single click fires the
  orchestration.

Red-green confirmed: a synthetic pre-fix menu (cascade + no direct commands) trips checks
A/B; the fixed code is green.

Penta **phase 284** (`phase_284_led_beam_splitter_menu_command`); baseline
`"284": "pass"`.

## Files
- `KrakenOS/UI/services/open3d_face_assignment.py` — cascade → two direct commands.
- `KrakenOS/UI/validate_open3d_led_beam_splitter_menu_command.py` — the guard (`phase_284`).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_284`.
- `tools/penta_validator_baseline.json` — phase 284 baseline + title.
- `bugs/repro_0319bis_context_path.py`, `bugs/repro_0319ter_menu_wiring.py` — the two
  headless repros that isolated the interactive cascade as the sole remaining failure.
