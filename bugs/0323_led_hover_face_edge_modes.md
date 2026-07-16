# 0323 — Imported-LED STEP hover: plain=face / Alt=edge, depth-guarded, jitter-tolerant

## Flag
Follow-up to 0317. The user reported three separate defects on the imported-LED STEP hover:

1. **Inconsistent face-vs-edge.** *"so many edges and surfaces in the LED STEP and yet the hover
   highlight only a few. Sometime highlight edge, sometime I orbit the scene, the surface highlight, not
   edge, very inconsistent."* They asked for *"detail finding of edges and faces, perhaps let Ctrl +
   mouse click or Shift or Alt mouse click does different selection."*
2. **Phantom edges.** *"it highlight edges that does not match with drawn outline of the part."*
3. **Click jitter.** *"sometime hover highlight is what I want, but during left or right click, a little
   bit of mouse movement will make the highlight disappear."*

Agreed design (user confirmed *"yes, build face + edge"*): **plain hover = whole FACE** (never
auto-collapse to an edge); **Alt held = nearest DRAWN EDGE**. The modifier governs the HOVER; the
left/right click simply inherits whatever is currently highlighted (WYSIWYG). Ctrl (orbit) and Shift
(pan) are already taken; a corner/vertex mode is reserved for later.

## Root causes (each measured, not theorised — `bugs/probe_0323_led_edge_vs_drawn.py`)

**(1) Inconsistency = edge refinement ran on EVERY hover.** 0317 introduced `_edge_refined_feature` and
called it *unconditionally* on every whole-face hover: whenever the cursor fell within a 14 px
screen-space band of any projected outline segment it collapsed the whole-face highlight to a single
edge. A sub-pixel mouse move or a scene orbit slid the cursor across that band, so the highlight flipped
face↔edge frame-to-frame — exactly *"sometime highlight edge … sometime surface … very inconsistent."*

**(2) Phantom edges = a real-but-occluded far-side edge won the pure-2D contest.** The picked face
*outline itself is 100% drawn-correct* — the probe found **0% phantom segments in 3D** (every outline
edge is a genuine boundary of the picked analytic face group). The defect is a *projection* artifact:
**105 of 1452** LED face groups span **> 15 mm** front-to-back (a bore / cylinder wraps around, up to
**134 mm** on the ILS0202 LED). `nearest_display_edge` ranked candidates purely by 2D screen distance,
so a **far-side** boundary segment — behind the solid, invisible to the user — could project nearer the
cursor than the front edge and win. The highlighted edge then "does not match the drawn outline" the
user is looking at, because it belongs to the hidden back face.

**(3) Jitter.** Two mechanisms:
- *Left:* `drag_threshold_px = 4` — a small press-time wobble crossed 4 px, set `_left_drag_moved`, the
  press was reclassified as a camera orbit (`should_pick` → false) and the selection was abandoned.
- *Right:* `<B3-Motion>` was **unbound**, so a right-drag fell through to the VTK interactor default,
  which re-hovered and dropped the highlight the context menu was about to act on.

## Fix

**Gate the edge refinement on Alt (root cause 1 + phantom in plain mode).**
`open3d_round_lens_pick.py::step_feature_pick_for_display_xy` now calls `_edge_refined_feature` **only
when `inspector._edge_pick_alt_active`** (both the metadata cell-pick path and the raw per-cell fallback
path); plain hover returns the whole-face feature verbatim. So plain hover is stable whole-face by
construction — no band to flicker across — and the target edge gesture is a deliberate Alt-hold.

`Kraken3DInspector._event_alt_pressed` (new staticmethod) reads Alt as **X11 Mod1 `0x0008`** OR **Mod5
`0x20000`**, matching the two-bit convention already used by `open3d_interaction_event.py` and
`open3d_event_recorder.py` (so it fires on either keyboard layout). The mouse layer records the live
modifier in two places:
- `hover_motion` (the passive `<Motion>` that drives VTK-side feature hover) sets
  `_edge_pick_alt_active` **before any early return**, so an orbit/idle frame can't leave a stale mode.
- `left_press` re-captures it at press time, because the committed pick fires on **release** with no
  motion in between — the press-time modifier is the authoritative read for the click.

Tk's subset rule means a plain `<ButtonPress-1>` still catches an Alt+click (no `<Alt-ButtonPress-1>`
binding needed; verified no conflicting `<Alt-…>` bindings exist).

**Depth-rank the edge candidates (root cause 2, Alt mode).**
`nearest_display_edge(..., *, depth_reference=None)` — when given the world-space **front pick point**
under the cursor, among the candidates within `tolerance_px` it ranks by **3D distance to that point
first**, 2D screen distance as tiebreak, so the FRONT edge the user is pointing at wins over an occluded
far-side edge. `_edge_refined_feature` forwards `depth_reference=pick_point`; both call sites pass
`pick_point=pick_point`. Passing `None` reproduces the original pure-2D behaviour **byte-for-byte** (a
`(distance,)` 1-tuple rank), so nothing that doesn't opt in regresses.

**Jitter tolerance (root cause 3).**
- `drag_threshold_px` **4 → 8**: an ordinary click tolerates a little hand wobble before it is treated
  as an orbit, without making a deliberate drag feel sticky.
- Right button: `right_press` sets `_right_button_active = True` and `_on_mouse_move`
  (`Open3DInteractionService`) **early-returns while it is set**, freezing the scene hover so a press-time
  wobble can't re-pick the highlight away. `<B3-Motion>` is bound to a `"break"` swallow (no VTK-default
  re-hover). `<ButtonRelease-3>` clears the flag, and `hover_motion` **self-heals** it (a bare `<Motion>`
  ⇒ no button held) in case a grabbed context menu swallows the matching release.

Per *"guard the invariant, not the instance"* — the invariant is **plain hover is whole-face and stable;
the edge refinement is an explicit Alt gesture, and when it runs it must prefer the edge the user can
actually see.**

## Verified (display-free)
`KrakenOS/UI/validate_open3d_led_edge_pick_modes.py` — **PASS**:
- **A** gate behavioural: on a synthetic raw-fallback mesh, plain hover returns the whole face (`F000`),
  Alt hover returns a suffixed edge (`F000eN`).
- **B** depth guard pure: a FAR boundary wins (ordinal 0) with no reference; with a FRONT reference the
  near-side edge wins (ordinal 1); `depth_reference=None` is unchanged from pure-2D.
- **C** `_edge_refined_feature` threads `pick_point`: a far reference yields an `…e0` face_id, a front
  reference `…e1`.
- **D** modifier bits: `0x0008` and `0x20000` → Alt True; `0x0004` (Control-only) → Alt False; and the
  Control predicate stays orthogonal.
- **E** source contract: both edge calls are gated on `_edge_pick_alt_active` and both forward
  `pick_point=pick_point`; `_edge_refined_feature` passes `depth_reference=pick_point`.
- **F** mouse/interaction wiring: `drag_threshold_px = 8`; `hover_motion` and `left_press` each record
  Alt; right-button flag set + cleared; `<B3-Motion>` and `<ButtonRelease-3>` bound; `_on_mouse_move`
  early-returns on `_right_button_active`.

Penta **phase 287** (`phase_287_led_edge_pick_modes`) delegates to the guard; baseline updated
(`"287": "pass"`). The 0317 guard (phase 279) still passes — plain-hover coverage is unchanged.

## Files
- `KrakenOS/UI/open3d_inspector.py` — `_event_alt_pressed` staticmethod; `_edge_pick_alt_active` /
  `_right_button_active` flag init.
- `KrakenOS/UI/services/open3d_round_lens_pick.py` — Alt gate on both edge-refine call sites;
  `_edge_refined_feature(pick_point=…)` → `depth_reference`.
- `KrakenOS/UI/services/open3d_face_index_edges.py` — `nearest_display_edge(*, depth_reference=None)`
  front-depth ranking.
- `KrakenOS/UI/services/open3d_mouse_bindings.py` — `drag_threshold_px` 4→8; Alt capture in
  `left_press` + `hover_motion`; right-button `right_press`/`right_motion`/`right_release` bindings.
- `KrakenOS/UI/services/open3d_interaction.py` — `_on_mouse_move` freezes hover while
  `_right_button_active`.
- `KrakenOS/UI/validate_open3d_led_edge_pick_modes.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_287`.
- `tools/penta_validator_baseline.json` — phase 287 baseline + title.
- `bugs/probe_0323_led_edge_vs_drawn.py` — characterization probe (0% outline phantom in 3D; 105/1452
  face groups span >15 mm, up to 134 mm).

## Notes / remaining
- The LED STEP and its analytic cache are **gitignored**, so a fresh clone can't run the real-LED probe;
  the synthetic guard carries the guarantee.
- Ctrl and Shift are the camera orbit/pan modifiers; a **corner/vertex** hover mode is reserved for a
  future modifier once a third gesture is free.
- In-app eyeball owed (needs a GLX display): import the LED STEP and confirm (a) plain hover stays
  whole-face while orbiting — no face↔edge flicker; (b) holding **Alt** lights the nearest **drawn**
  (front) edge, never a hidden back-face edge; (c) a small wobble during a left OR right click no longer
  drops the highlight.
