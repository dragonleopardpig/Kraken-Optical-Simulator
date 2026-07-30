# 0480 — the camera seated on whichever arm sorted first, not on the arm that is its sensor

Fourth entry in the "the camera body ends up on the LED" family (bugs/0471 → 0473 → 0475).
Those three fixed *how* the body is moved. This one is about *which detector it is moved onto*.

Started life as an uncommitted precursor on this machine, written before 0474–0479 were pushed
from the other machine and numbered `0474` locally — a collision with the pushed
`0474_physics_star_import_regression`. Renumbered here, and the precursor's rule was measured
before being kept (it does not survive; see **Why not "nearest the Image"** below).

## The rule that was there

`seat_camera_on_sensor` chose the detector target it seats the body onto like this:

    for target in bundle.targets:
        if not target.is_detector: continue
        if target.metadata["focus_source"] == "reached_image":
            chosen = target; break
        if chosen is None:
            chosen = target          # <-- "the first one"

The second clause is the bug. A beam splitter derives a detector for **every terminal leaf**
(bugs/0088 B1), and `derive_branch_detectors` enumerates `sorted(leaves)` — *alphabetical by
branch path*, so `reflect` sorts before `transmit`. "The first detector" is therefore a fact
about string ordering, not about the scene. It is only ever consulted when NO arm is pinned to
the designed Image, which is exactly when the code has the least idea what it is looking at.

## Measured

Built-in layout **Beam Splitter Two Path Doublets** (`bugs/probe_0480_target_identity.py`):
5 detector targets, **0 pinned**, so the fallback decides.

    [0] row=6      Standard  Transmit path detector    centre=(0, -0.71, 140.00)   <-- OLD pick
    [1] row=10     Standard  Reflect path detector     centre=(0, 130.00,  45.00)
    [2] row=11     Image     Global diagnostic image   centre=(0,   0.00, 192.00)  <-- the sensor
    [3] row=100000 Image     Branch (S1/reflect)       centre=(0, 176.33,  45.00)
    [4] row=100001 Image     Branch (S1/transmit)      centre=(0,  -0.71, 184.33)

    _reached_image_target(...) -> row 11, (0, 0, 192)

The body was seated **52 mm short of the Image, on a diagnostic detector row**. Rotate the
target list and the answer changes — the guard asserts on exactly that (check A4).

`attachment/machine_vision_AZ85_RA_Mirror_BS.py` (`bugs/probe_0480_arm_selection.py`) is the
scene the family was reported on, and on **this** build the old rule happens to be right there:

    AS LOADED                       dets=3  pinned=[0]  reaches=[0]
      [0] S3:S3/reflect             reached_image  centre=(229.930, -0.000,  2.303)
      [1] S3:S3/transmit->reflect   converging     centre=( 74.390,  0.099, 31.346)
      [2] S3:S3/transmit->transmit  converging     centre=( -0.467,  0.062, 68.396)   <-- x = -0.5
    AFTER "remove defocus"          dets=3  pinned=[0]  reaches=[0]   (row 7: 51.500 -> 44.119)
      [0] S3:S3/reflect             reached_image  centre=(229.930, -0.000, -5.077)

The imaging arm stays pinned through the snap, so the fallback is never reached and all three
rules agree. That is *luck of the alphabet* — `reflect` < `transmit` — plus 0478/0479 changing
what the snap writes. Leaf `[2]` at x = −0.47 is the LED-side arm the body was reported on; on
a scene whose imaging arm is the **transmit** leaf, the alphabetically-first leaf is a reflect
arm and the same fallback hands the body to it.

## Fix

`branch_detectors.camera_seating_detector_target(targets, camera_label=, designed_image_point=)`
returns `(target, reason)` and answers the question by meaning, most authoritative first:

| rung | test | why it is above the next one |
|---|---|---|
| 0 | `assigned_camera_label == label` | the user registered THIS camera to THIS arm (Phase B2); a per-arm camera's sensor is its own arm's detector, not the global Image |
| 1 | `_reached_image_target(...)` | the scene's prescription Image detector. **The same helper the branch-detector pin uses**, so seating and pinning cannot disagree about which target is the designed Image |
| 2 | `focus_source == "reached_image"` | an arm pinned onto that image — its centre *is* the image |
| 3 | `reaches_designed_image` | bugs/0477's predicate: do THIS arm's own rays land on the Image? Separate from rung 2 because `focus_source` also encodes *how* the plane was positioned, so it flips when the Image moves |
| 4 | the sole detector | a plain sequential/folded scene — nothing to confuse it with |
| — | otherwise **refuse** | bugs/0473: seating a physical body on the wrong arm is worse than not seating it |

Ties inside a rung go to the candidate nearest the designed Image, then to target order.

Rungs 1 and 2 never compete: `drop_superseded_image_display` (bugs/0093/0098) removes the
prescription Image target as soon as any branch detector exists, which is why the AZ85 scene has
*only* arms and Two Path Doublets still has its Image row.

The refusal names the remedy ("register the camera to a detector, or trace so an arm reaches the
Image") instead of moving the body somewhere plausible. The status line on success now also says
which rung supplied the sensor — that is the thing that went wrong here, so it belongs where the
user can read it.

`_designed_image_world_point()` supplies the tie-break point and applies
`_optical_axis_fold_world_transform_for_row`: `_row_z_positions` is the STRAIGHT
cumulative-thickness axis while bundle targets are folded through that transform, so a
straight-frame point would sit hundreds of mm from every candidate. It is advisory only — it
never admits or rejects a candidate, so a scene whose Image row cannot be located still seats
(guard check E3).

## Why not "nearest the Image", the precursor's rule

The uncommitted precursor kept the `reached_image` fast path and otherwise took the nearest
detector **within 1.0 mm**, refusing beyond that. Measured against 0477: an imaging arm that is
NOT pinned sits at its own convergence — 45.4 mm from the designed Image on the reported scene.
A 1 mm gate rejects it, so "Reset Camera to Image Plane" would have refused on precisely the
state 0475 wired that menu item up for. Rung 3 identifies the arm by whether its rays land,
which is a property of the arm rather than a distance, and the guard pins this down (check C2).

## Guard

`KrakenOS/UI/validate_open3d_0480_camera_seating_arm_choice.py`, penta **phase 387**.
Display-free: the ladder is a pure function, driven against target sets *measured* from the real
scenes above (0477's lesson — this class of logic had to be reasoned about from a rendered
screenshot twice). 20 checks: the reported pick (A1–A3), order-independence under every rotation
(A4), the dropped-Image and pinned-arm paths (B1–B3), 0477's unpinned arm and the 45 mm case
(C1–C2), two registered cameras landing on their own arms (D1–D2), plain sequential scenes and a
missing Image point (E1–E3), refusal instead of a guess (F1–F3), and that the seating actually
consults the ladder with no hand-rolled scan left behind it (G1–G3).

Verified alongside: phase 382's real-scene guard still seats the AZ85 camera
(`SEATED 11.5 mm == vendor front-to-sensor`, `LATERAL x 229.9 vs 229.9`, `CLEAR`); the
branch-detector family — multi_arm, redundancy_drop, supersedes_image, superseded_image_hidden,
0448, 0451, 0464, 0470, 0476, 0477, 0478, beam_splitter_branch_detectors — all PASS; gate
`--phases 77,251,372,378,381,382,383,384,385,386,387` = 10 pass, 1 known-failing (251, in
baseline); 40/40 pytest.

Unrelated pre-existing failure, so the next reader does not chase it:
`validate_open3d_illumination_keeps_real_detector` fails identically at `146bdb64` with these
changes stashed — *"the no-LED baseline has no drawn detector — fixture changed, check the
scene"*. A fixture/scene issue, not a seating one.
