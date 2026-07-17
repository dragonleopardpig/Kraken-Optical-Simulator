# bugs/0339 — "Add Beam Splitter to LED" is unreachable while a CA opening is pinned

**Flag `flag_20260717_135905_151`** (latest live test, imported LED):

> "after snapping the CA to optical axis, right click add BS Cube or Plate not
> working."

and the clarifying follow-up:

> "The snapping is not from the right click menu."

## The defect

The one-click **"Add Beam Splitter to LED (Cube)/(Plate)"** commands (bugs/0319) live
**only** in the whole-body STEP overlay menu (`open3d_face_assignment.py`, gated on
`step_label == "led"`).

But once a clear-aperture **opening** is *pinned* (bugs/0334 left-click), the
right-click dispatch in `_show_surface_function_context_menu` short-circuits:

```python
if self._has_selected_step_opening() and self._show_selected_opening_context_menu(event):
    return "break"
```

`_show_selected_opening_context_menu` builds an **opening-only** menu (Snap CA →
axis, Set / Center / Forget CA, Deselect) — it never offered "Add Beam Splitter".

So the workflow the user actually does — pin the LED clear-aperture opening, snap it
onto the optical axis **from a non-right-click path** (which leaves the opening
pinned), then right-click to add a beam splitter — always lands on the opening menu.
"Add BS Cube or Plate not working": the item simply isn't there. The right-click
diagnostics on the flag confirm the pick resolves the LED (`hovered_label='led'`,
`override_eligible=False`), yet the pinned-opening branch claims the event first.

The stale live report before this ("right click snap optical axis still not
working") was a **stale app** — both flags carry a single `axis:global` optical axis
(from z=-286 to z=+252), the exact case the 0337 one-click snap handles, and this
flag's own text ("after snapping the CA to optical axis") confirms the snap now
works once the app is restarted onto commit 261d70b8.

## Fix — offer Add BS from the pinned-opening menu (`open3d_face_assignment.py`)

`_show_selected_opening_context_menu` now adds, when the pinned opening belongs to
the LED (`step_label == "led"`):

```python
menu.add_separator()
menu.add_command(label="Add Beam Splitter to LED (Cube)",
                 command=lambda: self._add_beam_splitter_to_led_from_context("cube"))
menu.add_command(label="Add Beam Splitter to LED (Plate)",
                 command=lambda: self._add_beam_splitter_to_led_from_context("plate"))
```

It routes to the **same** `_add_beam_splitter_to_led_from_context` pipeline as the
body menu. That handler auto-detects the LED clear-aperture opening from the current
mesh (not from the pinned geometry), so it works post-snap regardless of where the
opening moved. The pinned opening *is* the LED clear aperture the BS centres on, so
this is exactly where the user expects the action — and it is now reachable whether
or not an opening is pinned.

## Guard & regression

`KrakenOS/UI/validate_open3d_opening_menu_add_bs.py` (penta **Phase 296**),
display-free:
- build the opening menu for a pinned **LED** opening (fake Tk) → both
  "Add Beam Splitter to LED (Cube)" and "(Plate)" labels present;
- build it for a **non-LED** overlay opening → **no** Add-BS labels (the pipeline is
  LED-only);
- source contract: the `step_label == "led"` gate + routing to
  `_add_beam_splitter_to_led_from_context`.

## Files touched
- `KrakenOS/UI/services/open3d_face_assignment.py` — `_show_selected_opening_context_menu`
  adds the two Add-BS items for the LED.
- `KrakenOS/UI/validate_open3d_opening_menu_add_bs.py` — new guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 296.
- `tools/penta_validator_baseline.json` — Phase 296 = pass.
