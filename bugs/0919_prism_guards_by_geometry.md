# 0919 -- ungated sweep, batch 3: prism guards that named faces, and one that assumed no fold

No product change. Each of these failed because the TEST pinned something the product had since
changed on purpose.

- **`validate_open3d_five_penta_initial_visual`.** It expected the 13 rays to be "escaped". It
  was written 2026-05-25; bug 0015 (06-04) made the terminal row a detector, so a ray leaving
  the cascade sideways is honestly `missed_detector`. The claim is that every ray LEAVES (none
  stops inside, none hits the image plane), and it now accepts either status.
  - Bisect check: it fails identically at 09-18 (d4a1c946), so this is not a recent regression.
- **`validate_open3d_face_context_assignment`.**
  - *Split-plane propagation.* The native STEP import keeps B-rep faces whole, so no split plane
    arrives. The guard now MAKES one: it clones a face record, taken from a face other than the
    directly assigned one, and propagation to the sibling is verified.
  - *Side labels.* Promotion now DERIVES a side label per face. "A direct assignment needs no
    side label" is now checked as: the face keeps the label it arrived with (or Auto); none is
    invented.
  - *Face names.* F003/F004/F006 were the old clustering's names; on the natively imported prism
    they point at other faces. The mirrors are now found by geometry (`penta_face_roles`); the
    stale-cache check uses the face the trace actually hits first; the world-pick remap expects
    the row face at the picked point, which must be the only Mirror.
  - *Image plane.* With the TRUE mirrors coated the prism folds 90 deg, and the port-anchored
    image follows the output axis (the vendor-prism guard asserts exactly that). The old
    "Image never moves" check held only because the wrong faces were coated. It now asserts the
    original bug's claim: the image is BEYOND the exit face (40 mm) and faces along the exit
    direction, not inside the prism.
- **`validate_optical_solid_direct_mirror_faces`.** The ray enters F005, reflects twice and exits
  F006, as required. The two mirrors' labels swapped when the 0847 triangle alignment changed how
  face records are built, so the middle pair is compared as a set, against the fixture's OWN
  Mirror assignments.

`validate_penta_mirror_3d_cascade`'s resolver is now the shared `penta_face_roles(records)`: side
pair (dot -1), through pair (dot 0), and the 135-degree mirror pair among the rest.
