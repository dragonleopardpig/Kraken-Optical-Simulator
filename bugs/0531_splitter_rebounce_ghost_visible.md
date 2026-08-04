# 0531 — the BS re-bounce ghost stayed drawn with "Show Clipped Rays" OFF

## Flags

`flag_20260804_082939`: "clipped overlays is off, still have spurious reflected beam" —
an olive band rising off the splitter at ~35°, ending mid-air, with the overlay off.
`flag_20260804_083128`: "clipped overlay is on, same as before" — with the overlay ON the
stray band crosses the camera's screen region. Both on build 8fc62dc3 (post-0530: zero
missed_image in both censuses — the teleports stayed dead; these are honest tails).

## Diagnosis

The spurious beam is one branch family: `S3:S3/transmit -> S3:S3/reflect` — 233 rays that
TRANSMITTED at the cube splitter and immediately REFLECTED at it again (~25% power), then
escaped. A real Fresnel double-bounce ghost arm. The 0018-reopen display rule ("a steered
escape is an authored second path — keep it visible with clipping OFF") matches its
signature, so the ghost family survived the overlay-off filter. The imaging family
(`S3:S3/reflect`, single steer, 225 rays) reaches the sensor.

## Fix

`ray_path_is_splitter_rebounce_ghost` (scene_geometry): two CONSECUTIVE surface events
that are splitter interactions on the SAME surface = an internal re-bounce ghost. The
overlay-off visibility rule hides such paths. Deliberately untouched:

- the 0018 single-steer second path (one split event) — still visible;
- the 0184 coaxial double-pass (split → scatter at the object → split again) — the
  intervening interaction breaks the "consecutive" test;
- a two-splitter cascade (splits on different surfaces);
- a ghost that actually lands on the detector (veiling glare) — `hit_detector` wins first.

With the overlay ON the ghost family still draws — that is the overlay's contract
(show the stray light); it is now direction-honest after 0530.

AZ85 overlay-off after: exactly the 225 detector-reaching rays draw (was 225 + 233
ghost). Render from the flag viewpoint confirms the clean imaging picture.

## Guard

`validate_open3d_0531_splitter_rebounce_ghost_hidden.py` (penta phase 426): predicate
mechanics (ghost / authored / double-pass / cascade) + the real-scene overlay-off set.
`validate_open3d_reflected_branch_detector_bounds` (0018),
`validate_open3d_traced_rays_always_visible`, `validate_open3d_ra_mirror_faint_line_folds`
all stay green.

## Physics follow-up (user: "It is a BS plate — are the spurious rays correct physics?")

NO — the traced ghost is wrong two ways (probe `diag_0531b_plate_ghost_geometry.py`,
zoom flag_20260804_084655). It IS a plate (1.2 mm glass path between the two hits):

1. **Power** — the transmit-dump family carries 0.25 = TWO 50 % transmits, so BOTH plate
   faces are flagged 50/50. A real plate has the coating on the FRONT face only; the back
   face is AR/uncoated → dump ~48 %, ghost ~1–4 %. Filed as bugs/0532.
2. **Direction** — the back-face reflection is geometrically correct (verified against
   the shared 45° normal), but the ghost terminates `no_next_intersection` 1.2 mm INSIDE
   the glass: the re-intersection with the front face is never found, so the exit
   refraction that would make a real plate ghost emerge PARALLEL to the imaging beam
   (classic laterally-offset plate ghost) never happens — it flies off 15–17° high with
   the IN-GLASS direction. Filed as bugs/0533.

What IS correct physics: the primary split (imaging reflect + transmit dump) and the
EXISTENCE of a faint back-face ghost. The 0531 display rule stands regardless — stray
light hides with clipping OFF, shows with it ON.
