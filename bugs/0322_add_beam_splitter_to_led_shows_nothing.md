# 0322 — "right click add BS cube still shows nothing" (the outcome is invisible in the 3D inspector)

## Flag
- `flag_20260716_083417_394` — *"The Nav Cube works as expected. But right click add BS
  cube still shows nothing."* The user then confirmed the running app is current: *"your
  Nav Cube fixes works, meaning all code should be latest and in use."*

This is the third report of the same complaint (0319 → 0320 → 0322). The two prior
root-cause attempts were **both wrong**:
- 0319/earlier: blamed `_led_beam_splitter_opening_plan()` returning None (auto-detect
  empty). **False** — see below, auto-detect returns 5 candidates on this exact scene.
- 0320: blamed a Tk `... > Cube/Plate` cascade never posting over the VTK interactor;
  flattened to direct commands. Helped the menu build, but the user still saw nothing.

## What the evidence actually shows

On the user's exact scene (`attachment/machine_vision_AZ85_RA_Mirror.py`, ILS0202 LED),
driven headless via `.devenv/state/venv/bin/python`:

1. `auto_detect_step_clear_aperture_candidates("led")` returns **5** candidates (face 266,
   score 0.955, −Z along-axis). So `_led_beam_splitter_opening_plan()` does **not** return
   None — the opening-plan early-return is never hit. (probe_0319_ils0202_openings.py)
2. `add_beam_splitter_to_led("cube")` runs **end to end and succeeds** — it promotes a real
   85 mm BS cube to a new optical-solid row (S9), assigns 9 faces, auto-flags the 45° diagonal
   coating, and sets a success status. It even works twice in a row.
   (probe_0322_add_bs_to_led_end_to_end.py, probe_0322_bs_second_run_and_led_offset.py)
3. The flag snapshot's `promoted_solid_rows` reads the **live model** (open3d_event_recorder.py
   line 414, `inspector.editor.rows`) and shows only the two AZ85 lens groups — **no BS row**.
   So in the real app the command never completed a row-add.

So: the command is correct and works everywhere I can test it, but produced nothing in the
user's live session, with **zero feedback** either way.

## Root cause — the outcome is reported on the INVISIBLE status bar

`add_beam_splitter_to_led` lives on the **editor**. Every one of its outcomes —
success (`scene_placement_commands.py` ~5065) and all six graceful stops (unknown kind,
LED not imported, no opening, BS-gen failed, overlay failed, promotion failed) — is written
to `self.status_var`, which is the **editor's main-window** status bar.

But the user is looking at the **3D-inspector Toplevel** (`Kraken3DInspector`), which has its
**own** visible status bar (`open3d_inspector.py:688` + the Label at `:865`). The editor's
main-window bar is hidden behind it.

The right-click handler `_add_beam_splitter_to_led_from_context` (a method on the
`Open3DFaceAssignmentService`, whose attribute access **proxies to the inspector**, so inside
it `self.status_var` IS the inspector bar and `self.editor.status_var` is the hidden main bar):

```python
try:
    self.editor.add_beam_splitter_to_led(str(kind))
except Exception as exc:
    self.editor.append_debug(...)
    self.editor.status_var.set(f"Add Beam Splitter to LED failed: {exc}")  # HIDDEN bar
```

It **ignored the return value** (so it could not tell success from a graceful stop) and only
ever wrote to the **hidden** `editor.status_var`, and only on an exception. Net effect for the
user: whether the command succeeded, stopped gracefully, or raised, the 3D inspector showed
**nothing** — no BS and no message. That is the literal "shows nothing".

## Fix

`open3d_face_assignment.py` — the handler now mirrors the command's own message onto the
**visible inspector bar** for every outcome, via a small `_set_inspector_status` helper
(`self.status_var` → the inspector):

```python
result = self.editor.add_beam_splitter_to_led(str(kind))   # (in try/except -> visible failure line)
message = self.editor.status_var.get() or (<computed success/stop fallback>)
if result is None:
    self.editor.append_debug(f"... added nothing: {message}")
self._set_inspector_status(message)     # <- the visible 3D-inspector status bar
```

So a success shows *"Added cube beam splitter to the LED (S9 …)"*, a graceful stop shows the
exact reason (e.g. *"could not find the LED clear-aperture opening. Right-click the LED window
→ Set as Clear Aperture, then retry."*), and an exception shows *"Add Beam Splitter to LED
failed: …"* — always where the user is looking. The success path already refreshes the 3D
view, so a real BS also appears.

## Verified (display-free)
`KrakenOS/UI/validate_open3d_led_beam_splitter_status_visible.py` — **PASS**, red/green
confirmed by `git stash` of the fix:
- **A** success dict → the rich success line is mirrored to the inspector bar;
- **B** graceful stop (None + reason on the main bar) → the exact reason is relayed **and** logged;
- **C** graceful stop with no reason → a non-empty computed fallback shows (never blank);
- **D** exception → a visible "Add Beam Splitter to LED failed: …" line + logged;
- **E** source contract: the handler reads `self.editor.status_var` and routes through
  `_set_inspector_status` → `self.status_var` (the visible bar).

Pre-fix source fails A–E (inspector bar stays empty; D sets only the editor bar; the helper is
absent). Integration on the **real** inspector (probe_0322_handler_routes_to_inspector_bar.py,
Xvfb) confirms `insp.status_var` shows the BS success line after the handler runs.

Penta **phase 286** (`phase_286_led_beam_splitter_status_visible`); baseline `"286": "pass"`.

## Honest scope + next step
I could **not** reproduce "the click does nothing" — the command and menu wiring work in every
headless/Xvfb test on the exact scene, and the app is now closed so the live session can't be
inspected. This fix removes the invisibility that made any stop/error read as "nothing" and
makes the next attempt **self-diagnosing**: whatever the click does now, the inspector bar will
say so. Asked the user to restart + re-record "Add Beam Splitter to LED (Cube)" so the captured
status reveals the true outcome (success, a named stop, or — if the bar never changes — a genuine
menu-click-delivery problem to chase separately).

## Observed follow-up (not fixed here)
The auto-sized cube comes out **85 mm** (the opening in-plane span hit the 90 mm clamp) — far
larger than the ~25 mm LED aperture. That is a 0319 sizing concern, orthogonal to "shows
nothing"; noted for a later pass.

## Files
- `KrakenOS/UI/services/open3d_face_assignment.py` — `_add_beam_splitter_to_led_from_context`
  relays the outcome to the inspector bar; new `_set_inspector_status` helper.
- `KrakenOS/UI/validate_open3d_led_beam_splitter_status_visible.py` — new guard (`phase_286`).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_286`.
- `tools/penta_validator_baseline.json` — phase 286 baseline + title.
