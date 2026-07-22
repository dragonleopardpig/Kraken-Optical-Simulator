# 0403 — retire the *inspector's* Source panel (correct 0402) + dialog/menu fixes

Three items from the user after eyeballing 0402.

## 1. 0402 retired the WRONG Source panel

**Feedback:** "I still see the Left Panel with Source panel." then "the 2D should remain while the 3D
one should be removed." Rationale: "the 3D left panel is getting long, and it's more intuitive for the
user to right-click the components at the right panel to set source parameters."

0402 hid the **2D editor's** left Source panel. Wrong target. The panel to retire is the **Open 3D
inspector's Live-Controls "Source" field section** (`open3d_live_controls.py` `build()` line 78) — the
inspector's left "Live Controls" panel (`open3d_inspector.py:830`, `main_pane` weight 0) was getting
long. Source parameters are set more intuitively by right-clicking the right-hand Scene Components
(Scene Sources group → "Scene Source Manager…"; a source row → "Edit Source…"), both shipped in 0402.

**Fix:**
- **Restore** the 2D editor's Source panel (`main_window.py`) — back to a visible `text="Source"`
  LabelFrame, gridded. Reverts the 0402 hide.
- **Retire** the inspector Live-Controls "Source" section — the ~14-row field block
  (`self.build_source_controls(source)`) is replaced by a single compact "Scene Source Manager…"
  button, shortening the panel. `build_source_controls` is kept (a guard asserts it exists + a dead
  inspector wrapper references it); it's just no longer built into the visible stack.

The 0402 Manager superset (pupil + Gaussian controls) and the right-click shortcut are unchanged and
correct — the Manager is now the rich source editor those retired fields point to.

## 2. Edit Source dialog spawned under the AGS bar

**Feedback:** "Right-click Edit Source, the pop-up dialog at the Monitor Left Corner, partially
overlapped by the AGS bar." The dialog (`open3d_source_edit_dialog.py`) created a `Toplevel` with no
positioning → OS default top-left, under the desktop panel bar. **Fix:** call
`editor._show_centered_dialog(dialog)` (the same helper the Scene Source Manager uses) — it caps to the
usable screen and keeps the title clear of a top bar.

## 3. Right-click menu didn't dismiss on click-elsewhere

**Feedback:** "After right-click pop-up at the right panel, clicking elsewhere does not close it." The
Scene Components browser menus used a plain `menu.tk_popup` + `grab_release`, which **sticks** in the
inspector: the heavyweight VTK render window swallows `tk_popup`'s pointer grab (bugs/0336), so the
outside-click never unposts the menu. **Fix:** a new inspector helper `_popup_scene_component_menu`
reuses the face-assignment service's proven robust popup (`_popup_context_menu`, bugs/0336/0348:
deferred `<Unmap>`/`<FocusOut>` dismiss, identity-guarded so a clicked entry still delivers before
teardown). All three step-admin browser menus (Scene Sources group, element group, per-element/source
row) route through it.

## Verification (`validate_open3d_source_panel_into_manager`, penta phase 330 — updated)

The guard's panel check is flipped to the corrected contract, plus two new assertions:

| check | asserts |
|---|---|
| WIRING-2D | the 2D editor Source panel STAYS visible (LabelFrame + gridded + built); no `source_hidden_panel` |
| WIRING-3D | the inspector Live-Controls Source FIELD section is retired (no `build_source_controls(source)` call), Manager shortcut present |
| SHORTCUT | browser menus route via `_popup_scene_component_menu` (no direct `menu.tk_popup`); inspector defines the helper; Edit Source dialog calls `_show_centered_dialog` |

6/6 pass. **Regression-checked against a clean worktree:** `validate_3d_interaction_contract` (17
pre-existing headless fails) and `validate_open3d_live_mode` (1 pre-existing STEP-placement fail) are
**identical** with/without this change — zero regressions added.

## Files

- `KrakenOS/UI/panels/main_window.py` — restore the visible 2D Source panel.
- `KrakenOS/UI/panels/open3d_live_controls.py` — retire the inspector Source field section → button.
- `KrakenOS/UI/panels/open3d_source_edit_dialog.py` — center the Edit Source dialog.
- `KrakenOS/UI/open3d_inspector.py` — `_popup_scene_component_menu` robust-popup helper.
- `KrakenOS/UI/panels/open3d_step_admin.py` — route the 3 browser menus through it.
- `KrakenOS/UI/validate_open3d_source_panel_into_manager.py` — corrected contract (phase 330).

## In-app eyeball still owed

2D editor keeps its Source panel; the inspector's Live-Controls left panel is shorter (Source fields
gone, one "Scene Source Manager…" button); right-click Edit Source opens centered; any browser
right-click menu closes when you click elsewhere.
