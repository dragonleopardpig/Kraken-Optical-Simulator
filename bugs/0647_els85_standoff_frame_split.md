# 0647 — "standoff 53.47+67.32 vs bench ~130": the WORLD is right; the readouts mix three reference planes (ANALYSIS)

**Flag:** `flag_20260825_113300_911` — "can double check FOV 20x20, standoff=53.47+67.32?
Actual testing is around 130mm." Scene `attachment/machine_vision_ELS85.py` (re-saved by the
user at 11:23, obj row t=108.38), build 4f5703cf.

## Verdict: the model MATCHES the bench — the numbers on screen measure different planes

Datasheet (`attachment/Lens/ELS-85-4.5V16K/ELS-85 4.5V16K_specification.pdf`): EFL 85,
suitable distance **225 / 142 / 99 mm at 0.5× / 1.0× / 2.0×**. Fitting WD(m) = f(1+1/m) − off
to the vendor's own three points gives off ≈ 28.8 ± 1 → the vendor's WD reference plane sits
**28.8 mm ahead of the front principal = 4.8 mm behind the scene's Front Optical Vertex
Datum** (and ~8.7 mm behind the STEP housing front face at x=67.60; datum x=71.45).

Measured on the flagged state (world bounds from the flag + headless probes):

| quantity | value |
|---|---|
| world object→datum (fold 54.28 + datum 71.45) | **125.73 mm** |
| datasheet law at the datum, m=1.152 | 125.3 mm (Δ 0.4) |
| world object→vendor-reference (datum+4.8) | **130.5 mm ≈ the bench's ~130** ✓ |
| user's markers 53.47+67.32 = object→STEP housing face | 120.8 (their reference, 8.7 mm outside the vendor plane) |
| full-grid measured delivered m at this state | **1.1508** = first-order at the WORLD distance (1.148, Δ0.25%) |

So the physical standoff the scene ACTUALLY models agrees with the vendor law and the bench
within ~0.5 mm. The user's on-screen markers measured to the STEP front housing face — a
legitimate but different plane than the vendor's WD convention.

## The real defect found underneath (open)

The PRESCRIPTION object row says t=108.38 while the WORLD object→datum is 125.73 — a
**17.35 mm frame split on the object leg** of this frozen display-folded scene. Consequences:

- the solve message quotes "object->lens 108.4 mm" — prescription-frame, 17 mm short of
  the world truth a user can measure;
- the delivered-m "correction" (0.772 here) is NOT optics: it exactly equals
  m_raw(world)/m_raw(prescription) = 1.148/1.49 — the 0602/0621 machinery silently absorbs
  the frame split as a magnification fudge, so it drifts whenever the split changes
  (0.9233 on yesterday's geometry) and degrades the further the two frames diverge.
- repeated solves are idempotent (probed 3×: obj 108.38↔108.41, corr 0.7721–0.7726,
  delivered VERIFIED each time) — no drift bug; the state is self-consistent.

Candidate fixes (not yet built): quote the WORLD object distance (and a vendor-convention
"WD" readout) in solve messages/HUD; root-cause the object-leg t↔world split so the
correction goes back to measuring OPTICS only.

Probes: scratchpad check_els85_wd/wd2/drift/mapping (session 2026-08-25); the mapping probe
fits launch→landing spans from the full traced grid — no chief ruler, no learned state.
