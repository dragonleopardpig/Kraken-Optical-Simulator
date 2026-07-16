# 0328 — plain hover snaps to the NEAREST closed opening loop (incl. an inner hole loop of a wide face)

## Flag / redirect
After 0326/0327 shipped (snap to the auto-detected clear-aperture rim by screen proximity) the user
re-recorded `flag_20260716_134203_962`:

> no improvement at all

The recording is on a **fresh** app (0327 loaded), so this is not a stale-app miss — the fix simply
snapped to the wrong opening. It stands on the earlier directive that decided 0327:

> by right, all closed edges should be detected if your algorithm is right.

0327 detected the closed loops correctly but only ever offered **one** of them (the auto-detected
top candidate). 0328 makes *every* closed opening loop a hover target.

## Root cause — the opening the user points at is an INNER hole loop, not a face
The recorded cursor `vtk_xy = [850, 615]` sits on the **central emitting square** on the front (+x)
panel. That square is **not an analytic face of its own** — it is an **inner hole loop of the wide
front-panel face F0053**. The recorded hover confirms it: `hover_step_cell_key = ('step','led','F005')`
and `hover_outline_bounds` X = **51.43** ≈ face-53 centroid X (**51.4**) — i.e. plain hover resolved
the **whole front panel**, exactly the fallback 0327 was meant to replace.

Meanwhile 0327 snaps only to `candidates[0]` of the CA detector. On this LED the five auto-detected
clear-aperture candidates are all **top/side mechanical openings**; `candidates[0]` is the **+y tray
slot F266**, whose projected rim is **~144 px** from the cursor. None of the five candidates lies on
the front panel, so the per-face CA snap never fired anywhere near the cursor → hover fell back to the
whole-panel highlight → **"no improvement at all."**

The square *is* a clean closed edge loop; it is merely an **inner boundary** of a face, so a per-face
snap (0326/0327) structurally cannot see it.

## Fix — mine every closed opening loop, snap to the nearest rim
New display-free service **`KrakenOS/UI/services/open3d_opening_loops.py`**:

1. **Mine loops from the LARGE faces only** (`face_area ≥ 500 mm²`, mirroring the CA detector's gate —
   real apertures live in the housing panels). A global mine of *every* face is intractable
   (**904 loops / 4.9 s**); the area gate makes it **31 loops / 556 ms**, memoised per mesh
   (`id` + content token, LRU) like the surface-triangle / edge caches — paid once per layout pose.
2. `face_outline_from_face_indices` returns **unwelded** segments (each segment carries its own
   duplicate endpoints), so **weld by rounded coordinate** into a shared-vertex graph, then **trace
   clean closed cycles** (every interior vertex has degree 2).
3. **Drop each face's OUTER silhouette** (its largest-area loop) when the face has holes — that is the
   panel edge, not an opening. A **single-loop** face *is* itself an opening (e.g. the tray slot F266),
   so it is kept. Filter screw-hole slivers (`perimeter ≥ 12 mm`) and any loop spanning ≥ 0.9× the body
   diagonal (a silhouette that slipped through). → **22** opening loops.
   - Face 53 welds into 6 loops: outer panel **438.6 mm** (dropped), the **square 176.6 mm** (kept),
     and 4× **7.9 mm** screw holes (dropped by the perimeter filter).
4. **`nearest_opening_loop`** — a cheap centroid gate (one projection per loop) prunes far loops; the
   survivors are edge-tested with the existing `nearest_display_edge` in **screen space**
   (`depth_reference=None`, so a recessed rim that projects near the cursor still wins). Ties break
   toward the **smaller** opening (the tighter aperture pointed *into*, not a larger surrounding rim).

### Wiring
- **`_opening_loop_hover_feature(self, label, loop)`** (new, `open3d_inspector.py`) — builds the
  lines-only rim overlay via `loop_outline_polydata` → `_hover_overlay_for_feature`, returning the
  `(centroid, overlay, normal)` feature with `face_id = F%03d` of the **owning** face, so a click
  resolves to a real face group.
- **`_opening_loop_hover_pick` / `_step_opening_hover_pick`** (new, `services/open3d_round_lens_pick.py`)
  — `step_feature_pick_for_display_xy` now snaps with a stable priority: **(1)** a *manual*
  `STEP_CLEAR_APERTURE_PICK` still wins (0327 rim); **(2)** else the **nearest mined opening loop**
  (the square, the tray slot, any hole); **(3)** else the auto-detected CA face rim (for a CA face
  below the large-face area gate). No `cell_id` gate — proximity drives it; the click inherits the
  highlight (WYSIWYG).

## Verified (display-free + offscreen)
- **`bugs/diag_0328_verify.py`** on the **real** ILS0202 LED with the **recorded** flag camera/cursor:
  `mined opening loops: 22`, front-panel square present (`perim 176.6, area 2022, face 53`), and
  `nearest_opening_loop([850,615]) → the central square (PICK is the central square: True)`. Proof
  render `attachment/_diag_0328_verify.png`: the red loop is exactly the square **under the cursor**,
  while the old auto-CA face 266 (gold) is the far **+y tray slot** at the top.
- **`KrakenOS/UI/validate_open3d_led_opening_loop_hover.py`** — **PASS** (fake editor + a synthetic
  own-plane projector; no OCC/GLX): **A** the square is mined (`F053`, 176.6 mm) and its face's outer
  silhouette is dropped; **B** its hover feature is a LINE-loop overlay with a finite centroid/normal
  and an `F%03d` id; **C** a near-rim cursor (no `cell_id`) snaps to the square; **D** the hole centre
  and off-body stay selective (no snap).
- **`KrakenOS/UI/validate_open3d_led_ca_edge_hover.py`** (0326/0327 guard) — **reframed for 0328 and
  still PASS.** It no longer asserts "hover near F266 → *exactly* F266": F266 is one of a **dense
  cluster** of tray openings (F306/F167/F168/F166…) whose projected rims nearly coincide, so the
  nearest-rim rule may return a neighbour — which is correct (it highlights the rim under the cursor).
  What it now guards is the durable regression: **A** the CA edge-feature builder still yields a line
  loop; **B** the auto-detected slot **F266 survives 0328 as a first-class mined opening** with a line
  rim; **C** the tray region stays **opening-live** on plain hover (a rim-edge `F` id, not a fill, not
  None); **D** off-body returns None.
- Penta **phase 290** (`phase_290_led_opening_loop_hover`) delegates to the new guard; baseline records
  `"290": "pass"`. Phase 289 reworded (0328-aware) but stays `pass`.

## Notes / remaining
- **In-app eyeball owed** (needs a GLX display this box lacks): import the LED, hover the central
  emitting square from any angle and confirm its rim highlights and a click selects it; confirm the +y
  tray slot and the other openings each still highlight on hover.
- Generalises for free: an **LED-with-BS** has two clear-aperture openings (bugs/0319) — both are mined
  loops, so both become nearest-rim hover targets with no special-casing.
- Why the CA-edge guard was reframed rather than "fixed to still return F266": under **any** camera the
  tray openings are physically adjacent (rims within ~1 px at the best-separated vertex), so pinning the
  exact face is fiction; the honest invariant is "the region is opening-live and F266 remains reachable."
- Still paused (not touched here): the general fuzzy per-cell face/edge pick and the phantom whole-face
  fill (bugs/0325), and the Alt-live gremlin (bugs/0324).

## Files
- `KrakenOS/UI/services/open3d_opening_loops.py` — **new** loop-mining service (`opening_loops_for_mesh`,
  `nearest_opening_loop`, `loop_outline_polydata`, weld/trace/plane helpers, LRU cache).
- `KrakenOS/UI/open3d_inspector.py` — new `_opening_loop_hover_feature`.
- `KrakenOS/UI/services/open3d_round_lens_pick.py` — new `_opening_loop_hover_pick` /
  `_step_opening_hover_pick`; `step_feature_pick_for_display_xy` trigger now nearest-of-many.
- `KrakenOS/UI/validate_open3d_led_opening_loop_hover.py` — **new** display-free guard (A/B/C/D).
- `KrakenOS/UI/validate_open3d_led_ca_edge_hover.py` — reframed 0328-aware (F266 survives as a mined
  opening; tray region opening-live; off-body selective).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — new `phase_290_led_opening_loop_hover`
  (+ registered); phase 289 wording.
- `tools/penta_validator_baseline.json` — `"290": "pass"`.
- `bugs/diag_0328_verify.py`, `attachment/_diag_0328_verify.png` — end-to-end proof (PNG gitignored).
