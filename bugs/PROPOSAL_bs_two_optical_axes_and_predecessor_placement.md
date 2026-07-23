# Proposal — Beam splitter creates TWO optical axes, and every component follows its immediate predecessor

Status: **design proposal, no code changed** — for review (flag_20260723_141437, scene
`machine_vision_AZ85_RA_Mirror_BS.py`).

## Your requirements (verbatim, numbered)

1. `machine_vision_150mm_measured_test.py`: imaging path is the **TRANSMIT** leg of the BS (cube).
2. `machine_vision_AZ85_RA_Mirror_BS.py`: imaging path is the **REFLECT** leg of the BS (plate).
3. A BS should **automatically create 2 optical axes**.
4. The imaging path can follow **either leg, or BOTH**.
5. Replacing the RA mirror must **auto-retain** the current imaging-lens + camera placement, *provided (3)*.
6. The BS must **not** re-aim the camera. **Every component follows the component immediately before it** —
   e.g. the camera follows the 2nd RA mirror, not the BS.
7. This proposal.

## Why it fails today (root cause)

Two facts collide:

- **The BS is deliberately skipped as a fold source.** `build_optical_solid_output_port_pose_overrides`
  (`nonseq_output_ports.py:1362`) computes, for a promoted mirror, a reflected frame
  (`_reflected_frame_from_interaction_face`, `:1274`) and re-positions the downstream rows onto that
  folded leg. But it `continue`s over a beam splitter (`:1392` top-of-loop, `:1543` follower re-source) —
  the fix for bugs/0396–0399 ("the camera should not follow the BS"). So the BS produces **no** reflected
  frame → **no second axis**, and no follower ever folds onto it.
- **Followers fold onto a specific fold SOURCE, not onto their predecessor.** The RA mirror was that
  source. Remove it and the override map empties → the lens + camera collapse back onto the straight
  `axis:global` — the "misplaced" symptom, and the flag's single 2-point axis record.

So the current model is "a designated fold source repositions the whole downstream chain," with the BS
excluded. Your point 6 asks for a *different, cleaner* model: **each row follows the one immediately
before it.** Adopting that model is what makes 3–6 all fall out together.

## The proposed model

### A. Two output frames per BS → two axes (points 3, 4)

A beam splitter has **two** optical outputs, so it defines **two output frames**:

- **Transmit frame** — straight through (continues the incoming axis).
- **Reflect frame** — bent by the splitter face (via `_reflected_frame_from_interaction_face`, the same
  math the mirror uses, applied to the BS's `Mirror`/`Beam Splitter` interaction face).

The BS emits **both** as optical-axis guides: the transmit leg continues `axis:global`; the reflect leg
becomes a branch guide (`axis:global:split` / a per-branch id, alongside the existing
`axis:global:reflected` machinery in `_folded_reflected_axis_guide_record`,
`open3d_inspector.py:10706`). This is display-first and satisfies "BS creates 2 optical axes" **visibly**
even before any placement changes.

The **imaging leg** (which output the lens+camera follow) is chosen by the **output-port face role** you
already assign: the face flagged as the imaging `Transmit/Port` (150 mm cube → the transmit face) vs the
imaging reflect face (AZ85 plate → the reflect face). "Either or both" = one follower chain per assigned
output leg.

### B. Every row follows its immediate predecessor (points 5, 6)

Replace the "one global fold source repositions the chain" model with a **local chain**:

> row *i*'s world frame = **row *i−1*'s OUTPUT frame** ∘ (row *i*'s own tilt / desp / thickness).

- A plain surface's output frame = its input frame advanced by its thickness (no bend).
- A mirror's output frame = its **reflected** frame.
- A BS's output frame = its **assigned imaging** leg's frame (transmit or reflect); the *other* leg spawns
  a parallel branch chain (point 4, "both").

Consequences, exactly as you specified:

- **The camera follows the 2nd RA mirror** — its immediate predecessor — never the BS (point 6). The BS
  only sets the frame for *its own* immediate follower on the imaging leg.
- **Removing/replacing the first RA mirror retains placement** (point 5): the lens + camera keep following
  their predecessors; whatever occupies the fold slot (RA mirror, or the BS's reflect leg) hands the same
  kind of output frame to the next row. Nothing downstream jumps, because nothing downstream ever pointed
  at the *removed* element directly — only at its neighbour.
- **150 mm vs AZ85 differ only in which BS face is the imaging output** — transmit vs reflect — not in the
  code path.

This is the North Star's "sequential is the ordered-path special case of the scene" (invariant 1) made
literal: the chain is just per-row predecessor frames.

## Implementation plan (phased, each shippable + eyeball-able)

| Phase | Deliverable | Touches | Risk |
|---|---|---|---|
| **1. See it** | BS emits BOTH axis guides (transmit + reflect). Render-only; no placement change. Immediately answers "no second axis". | `_folded_reflected_axis_guide_record` / `_folded_multifold_axis_guide_records` (`open3d_inspector.py`); un-skip the BS for *axis-guide* purposes only. | Low — display only. |
| **2. Fold the imaging leg** | The BS's **assigned imaging output** becomes a fold source for **its immediate follower** (not the whole chain). AZ85 plate → reflect; 150 mm cube → transmit (a no-op bend). | `build_optical_solid_output_port_pose_overrides` — replace the blanket BS `continue` with "fold only the immediate follower onto the imaging output frame". | Med — must not resurrect the 0396–0399 whole-chain camera drag. |
| **3. Predecessor chain** | Generalize follower placement to "row *i* ← row *i−1* output frame", so RA-mirror removal retains placement and the camera follows the 2nd RA mirror. | The override builder + the follower walk (`:1543`); `two_arm_display_fold.py` for the ray/detector side. | Med/High — the central change; needs the pure-geometry validator below. |
| **4. Both legs** | A follower chain (+ detector) on **each** BS output; the non-imaging leg is a real second arm. | `two_arm_display_fold.py` (already models two arms); per-branch detectors (project_open3d_detector_redesign). | Med. |

Recommend building **1 → 2 → 3 → 4**, one at a time, with your eyeball between each (folded/BS geometry is
headless-untestable — the reason the Accept-cone fold took five in-app passes).

## Validators (North Star invariant 6)

- **Phase 1:** the axis-guide record set for a BS scene contains a transmit **and** a reflect guide
  (display-free check on the records).
- **Phase 2/3:** on a synthetic `[object, BS(reflect), lens, mirror, camera]` chain, assert *pure geometry*:
  each row's frame equals its predecessor's output frame; the camera's frame equals the **mirror's** output
  (not the BS's). Deleting the first fold leaves the lens+camera frames unchanged.
- **Fixtures:** `machine_vision_150mm_measured_test.py` (transmit imaging) and
  `machine_vision_AZ85_RA_Mirror_BS.py` (reflect imaging) as the two reference scenes.

## Open questions for you before Phase 2

1. **Imaging-leg selection** — confirm it's driven by the **output-port face role** you assign on the BS
   (imaging `Transmit/Port` face), so 150 mm picks the transmit face and AZ85 picks the reflect face. Or
   would you rather a one-click "this leg is the imaging path" toggle in the BS right-click menu?
2. **The non-imaging leg** — draw it as an axis guide only (Phase 1), or also auto-add a detector on it
   (Phase 4) so it's a usable second arm?
3. **"Both"** — when both legs image, do you want two independent cameras (one per leg), or a shared
   detector the two arms fold onto?

Nothing is committed beyond this document. Point me at any of the phases (or amend the model) and I'll
start — Phase 1 (draw the second axis) is the natural, low-risk first slice.
