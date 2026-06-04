# 0015 — A beam splitter (any non-Image element) on the terminal surface makes every ray vanish

**Status:** Fixed (2026-06-04).
**Component:** Open 3D inspector — terminal-surface detector classification
(`KrakenLayoutEditor._scene_detector_surface_indices`, in
`KrakenOS/UI/services/analysis_reports.py`) feeding the ray-display filter
(`_iter_3d_scene_ray_records`, `services/three_d_scene_tools.py`).
**Reported via:** in-app recorder, flag `flag_20260604_160044_387`
(2026-06-04T16:00:44). **Repro bundles are gitignored**, so the evidence below
is transcribed here.

## Symptoms (user's words)

> check/uncheck Show Rays, click Trace Now, the ray still missing.

The user was probing robustness by dropping a random optical element at a random
position along the ray path — here a **beam splitter on the terminal Image row**
(`picked_row_index = 6`). After that, toggling *Show Rays* and clicking *Trace
Now* showed **no rays at all** (`state.json` `ray_actor_count = 0`), even though
the rays physically trace straight through the system.

The user's invariant (saved to memory): *rays must trace according to physics no
matter what element is placed where; an element should never make rays silently
disappear.* The beam splitter was just the random element that happened to land
on the terminal surface — the fix must be general, not specific to beam
splitters.

## Root cause (confirmed 2026-06-04, headless)

`BEAM_SPLITTER_SURFACE` ("Beam Splitter") is its own **surface type** in the
editor's surface combobox, mutually exclusive with `"Image"`. Converting the
terminal Image row to a beam splitter changes `row.surface` from `"Image"` to
`"Beam Splitter"`, so the row is no longer literally an Image.

`_scene_detector_surface_indices` recognised the terminal image plane **only**
by a literal `surface == "Image"` test (and the explicit nonseq target). With
the terminal row now typed "Beam Splitter", **no surface was classified as a
detector** (`detectors == []`). Consequences, all per the trace pipeline:

1. `_build_ray_paths` sets `reaches_image = last_surface in detector_surface_indices`
   — always `False` with an empty detector set, so every branch is tagged
   `escaped` / `reaches_image=False` (`scene_builder.py`).
2. The beam splitter correctly forces **non-sequential** (North Star — a beam
   splitter is an explicit nonseq trigger; this is *not* the bug). The transmit
   branch passes through the terminal plane and continues; the reflect branch
   goes back out the front. Neither lands on a "detector".
3. The default display filter keeps only `ray_path_reaches_image_from_events`
   (terminal status `hit_detector`) when *Show Clipped Rays* is off
   (`three_d_scene_tools.py`). With nothing classified `hit_detector`, it
   **silently drops every ray** — exactly the North Star invariant-4 violation
   (ambiguous geometry must emit diagnostics, never a silent drop).

Headless reproduction (object at 300 mm, BK7 singlet, terminal row):

| terminal row type | `use_nonseq` | detectors | displayed (clipped off) |
|---|---|---|---|
| Image (control)   | False | `[N]` | 5 |
| Beam Splitter (bug) | True | **`[]`** | **0** |

A beam splitter on any *non-terminal* row (front datum, aperture, rear datum)
always displayed fine — only the **terminal** position triggered the vanish,
because only there did the missing detector classification matter.

## Fix

`KrakenOS/UI/services/analysis_reports.py`, `_scene_detector_surface_indices`:
the **final prescription surface is the system's terminal image plane for
display / terminal-status purposes regardless of its optical type.** The old
clause only added the last row when `not use_nonseq and surface == "Image"`; it
now adds the last row whenever that row is not an Object/source surface
(`Object`, `OBJECT_TARGET_SURFACE`, `DIFFUSE_OBJECT_SURFACE`):

```python
if self.rows:
    last_surface = str(getattr(self.rows[-1], "surface", "") or "").strip()
    if last_surface not in {"Object", OBJECT_TARGET_SURFACE, DIFFUSE_OBJECT_SURFACE}:
        detectors.add(len(self.rows) - 1)
```

The physics is unchanged — the beam splitter still splits, branches still trace
non-sequentially. Only the *display/terminal classification* changes: the
forward (transmitted) branch reaching the terminus now registers as a detector
hit (`reaches_image=True` → terminal status `hit_detector`) and stays visible by
default. The backward reflect branch still reads `escaped` and is hidden unless
*Show Clipped Rays* is on — correct, it left the front of the system. This is a
**general** fix: any element (mirror, grating, thin lens, …) dropped on the
terminal row keeps that row's terminal role.

After the fix the bug-row case shows 5 forward rays by default (was 0), and 10
(both branches) with *Show Clipped Rays* on.

## Tests

* **Display-free unit** — `KrakenOS/UI/validate_random_terminal_element_ray_display.py`
  (`python -m KrakenOS.UI.validate_random_terminal_element_ray_display`). Asserts:
  (1) a beam splitter on the terminal surface keeps that index in the detector
  set and shows forward rays by default; (2) the **no-silent-drop** invariant —
  with *Show Clipped Rays* on, displayed rays == traced ray paths for *every*
  element at *every* position; (3) a **seeded random-element-along-the-path**
  sweep (Beam Splitter / Mirror / Thin Lens / Grating / Standard at random rows,
  terminal included) confirms the trace is non-empty and nothing is silently
  dropped. Teeth: pre-fix the terminal beam-splitter case gives `detectors=[]`
  and `displayed=0`, so checks (1) fail loudly.
* **Regression / end-to-end** — `Phase 24`
  (`phase_24_random_terminal_element_ray_display`) in
  `validate_open3d_penta_telescope_comprehensive.py` wraps the display-free
  `run_checks()` so the guard (including the random-element sweep the user asked
  for) runs in the gated harness. Gate baseline regenerated
  (`tools/penta_validator_baseline.json`).
* **Visual** — scene rendered off-screen to PNG with the terminal beam splitter;
  emerald ray polylines confirmed present (was a blank scene).
