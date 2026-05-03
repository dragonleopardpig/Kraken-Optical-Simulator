Beam Splitters
==============

The UI now has a ``Beam Splitter`` surface type. It is a first UI/core bridge
for splitters with deterministic non-sequential child branches.

Current capability
------------------

``Beam Splitter`` rows store a ``BeamSplitter`` metadata dictionary and
automatically write a KrakenOS ``Coating = [R, A, W, THETA]`` fallback table.
With ``Non-Sequential Preview``, deterministic mode spawns both child paths
from each splitter hit:

* transmitted branch with ``T = 1 - R - A``
* reflected branch with ``R``
* branch metadata in ``raykeeper.BRANCH_ID``, ``PARENT_BRANCH_ID``,
  ``BRANCH_POWER``, ``BRANCH_PHASE``, ``BRANCH_LABEL``, and ``BRANCH_PATH``
* launch metadata in ``SOURCE_RAY``, ``SOURCE_XYZ``, ``SOURCE_LMN``,
  ``SOURCE_MODEL``, ``SOURCE_POWER``, ``SOURCE_WEIGHT``, and
  ``SOURCE_WAVELENGTH``

``Monte Carlo coating split`` remains available for legacy one-path stochastic
coating experiments. Use deterministic mode for normal beam-splitter design.

UI workflow
-----------

1. Load ``Common Optical Layout -> Beam Splitter 50/50 Example``.
2. Select the splitter row, or change an ordinary row's surface type to
   ``Beam Splitter``.
3. Right-click the row and choose ``Beam splitter settings...``.
4. Set ``Reflectance R`` and ``Absorption A``. Transmission is
   ``T = 1 - R - A``.
5. Use a physical source such as ``Collimated disk source`` or
   ``Gaussian beam``. With a physical source and a beam splitter, ``Auto``
   trace mode resolves to ``Non-Sequential Preview``; explicit
   ``Non-Sequential Preview`` is still available. ``Source X/Y/Z`` set the
   physical launch origin, and ``Source L/M/N`` set the normalized chief-ray
   direction. In this mode the ``Object`` row is a scene/reference datum, not
   the source of the launched rays.
6. Leave ``NS probabilistic coating split`` off for deterministic splitters.
7. For a finite plate, set the splitter row ``Glass`` to the substrate, set
   ``Thickness`` to the plate thickness, and add a following ``Standard`` row
   with ``Glass=AIR`` as the rear face. In the editable UI table, use the same
   rear ``TiltX`` as the front face for a parallel plate; use a different rear
   tilt to model a wedge.
8. Right-click any grouped element and use ``Element settings...`` or
   ``Arm assignment`` to mark it as ``Common``, ``Transmit``, ``Reflect``, or
   ``Detector``. The first ``#`` cell shows a compact arm badge such as ``T``
   or ``R`` on the first row of the element.
9. Right-click a ``Beam Splitter`` row and choose
   ``Add detector to transmitted arm...`` or
   ``Add detector to reflected arm...`` to insert a detector plane at a
   distance measured along that central branch.
10. Use the table toolbar ``Arm focus`` dropdown when you want to select and
    scroll to all elements in one arm. It does not hide rows because row numbers
    remain KrakenOS surface indices.
11. Click ``Update`` and inspect paths with ``Actions -> Ray Inspector``,
    ``Actions -> Branch Tree Inspector``, and
    ``Actions -> Non-Sequential Scene Graph``.

The ``Beam Splitter 50/50 Example`` uses an exact-count collimated disk source.
Each launched source ray creates transmitted and reflected branch records, so
the Ray Inspector can show the source-ray index, branch power, and launch
metadata for each child path.

``BRANCH_LABEL`` is the local leaf label, such as ``transmit`` or ``reflect``.
``BRANCH_PATH`` is the cumulative traced splitter path, for example
``S1:BS1/transmit -> S4:BS2/reflect``. Use ``BRANCH_PATH`` for cascaded
splitters, return arms, and future recombination diagnostics.

For small ray counts, the collimated and Gaussian physical source previews use
equal-spaced meridional samples inside the requested radius. The outer preview
rays are kept conservatively inside the source edge, which avoids accidental
branch loss on tilted finite plates whose projected clear aperture is smaller
than their nominal diameter. Larger source bundles switch to deterministic
golden-angle disk filling so the 3-D source footprint is represented.

``Ray count`` is the number of launched source rays, not the final number of
drawn branch paths. A deterministic 50/50 splitter therefore produces up to
``2 * ray_count`` displayed child paths: one transmitted and one reflected path
per source ray. If a finite aperture clips one arm, the Ray Inspector will show
fewer child records for that arm.

Arm workflow tutorial
---------------------

Use this workflow when you want to build a first two-arm splitter layout without
manually calculating the reflected detector pose.

1. Start the editor and press ``Reset`` if the table is not empty.
2. Load ``Common Optical Layout -> Beam Splitter 50/50 Example``.
3. In ``Source Field``, choose ``Collimated disk source`` for ray-bundle
   debugging or ``Gaussian beam`` for a laser-style source.
4. Set ``Ray count`` to the number of launched source rays you want. With a
   deterministic splitter, each unclipped input ray can produce one transmitted
   child and one reflected child.
5. Right-click the ``50/50 coated front face`` row and choose
   ``Beam splitter settings...``. Confirm ``Reflectance R = 0.5``,
   ``Absorption A = 0``, and deterministic splitting.
6. Right-click the same front-face row and choose
   ``Add detector to transmitted arm...``. Enter the distance from the splitter
   and the detector diameter, then press ``Insert``.
7. Right-click the front-face row again and choose
   ``Add detector to reflected arm...``. Enter the reflected-arm distance and
   detector diameter, then press ``Insert``.
8. Use ``Arm focus -> Detector`` to select the inserted detector rows. Use
   ``Arm focus -> Arm 1: ...`` style entries to select all rows tagged to a
   discovered branch arm. Role entries such as ``Reflect`` or ``Transmit``
   remain available for manual metadata checks.
9. Click ``Update``. The 2-D/3-D plots should show source rays forking into the
   transmitted and reflected paths, subject to finite-aperture clipping. The
   2-D plot labels discovered branch arms directly on representative branch
   rays as ``Arm 1``, ``Arm 2``, and so on.
10. Open ``Actions -> Ray Inspector``. The branch rows should show matching
    ``source_ray`` values, branch labels such as ``transmit`` and ``reflect``,
    and branch powers derived from the splitter settings.

The detector helper inserts a ``Standard`` ``AIR`` surface before ``Image`` and
tags it with ``Element`` metadata:

.. code-block:: python

   {
       "element_id": "Reflect_detector",
       "element_name": "Reflect detector",
       "arm_role": "Detector",
       "parent_splitter": "Splitter",
       "branch_selector": "reflect",
       "arm_distance": 60.0,
       "local_decenter_x": 0.0,
       "local_decenter_y": 0.0,
       "local_tilt_x": 0.0,
       "local_tilt_y": 0.0,
       "local_tilt_z": 0.0,
   }

For now, detector placement assumes the nominal incoming source axis is global
``+Z`` and computes the central reflected direction from the selected splitter
surface normal. This is correct for the supplied straight-input beam-splitter
example. More general tilted-source, multi-splitter, folded-arm, and catalog
component placement remains part of the next Phase 2 arm-placement work.

Two-arm doublet example
-----------------------

Load ``Common Optical Layout -> Beam Splitter Two Arm Doublets`` for a complete
example where one cemented doublet is placed after the transmitted arm and a
second cemented doublet is placed after the reflected arm.

The row structure is:

1. ``Object`` is a global reference plane; the Source panel launches the
   physical source bundle.
2. ``Splitter`` rows model the tilted 3 mm BK7 50/50 plate.
3. ``Transmit doublet`` rows are centered on the transmitted chief ray after
   the plate exit offset.
4. ``Transmit arm detector`` receives the transmitted branch after that
   doublet.
5. ``Reflect doublet`` rows are tilted so their local ``+Z`` axis follows the
   reflected ``+Y`` branch.
6. ``Reflect arm detector`` receives the reflected branch after that doublet.
7. ``Image`` remains a global diagnostic surface at the end of the canonical
   KrakenOS table.

The important pattern is the saved ``Element`` metadata. The transmitted
doublet rows use:

.. code-block:: python

   {
       "element_id": "TX_DBL",
       "element_name": "Transmit doublet",
       "arm_role": "Transmit",
       "parent_splitter": "BS1",
       "branch_selector": "transmit",
       "arm_distance": 33.0,
   }

The reflected doublet rows use the same pattern with ``arm_role="Reflect"``
and ``branch_selector="reflect"``. The reflected surfaces also use
``tilt_x=-90`` plus global decenter values so their physical surface normals
point along the reflected arm. KrakenOS still traces against those physical
surface poses; the metadata is for arm labels, focus selection, grouping, and
future arm-workbench editing.

Manual arm assignment
---------------------

Use manual arm assignment when you add or import components surface-by-surface:

1. Select contiguous rows that form one optical component.
2. Right-click the first ``#`` cell and choose ``Group as Element`` if the rows
   are not already grouped.
3. Right-click the grouped element and choose ``Arm assignment -> Transmit`` or
   ``Arm assignment -> Reflect``.
4. Open ``Element settings...`` if you need to set the parent splitter,
   branch selector, arm distance, or branch-local offsets for documentation and
   future analysis.
5. Use ``Move Up`` or ``Move Down`` to reorder the element within the same arm.

The arm assignment metadata does not force ray routing. KrakenOS still traces
against actual geometry. The metadata is used by the editor for grouping,
selection, row movement, saved-layout documentation, and branch-aware analysis.
The table currently focuses arm rows by selecting and scrolling to them rather
than hiding all other rows. This preserves the KrakenOS surface-index mapping
while Phase 2 develops a true virtual arm-workbench table.

Arm Workbench workflow
----------------------

The intended beam-splitter workflow is:

1. Author the common path first: source, object/reference, pre-splitter optics,
   and the first splitter.
2. Click ``Update``. The editor traces deterministic branches and discovers
   branch families.
3. The 2-D plot labels discovered arms as ``Arm 1``, ``Arm 2``, ``Arm 3``, and
   so on, with each label anchored to a representative branch ray. For nested
   splitters, the stable internal identity should become a branch path such as
   ``BS1/transmit -> BS2/reflect``.
4. Use ``Arm view -> Common`` to show the full global layout and full
   canonical table.
5. Use ``Arm view -> Arm 1: ...`` or another numbered arm to filter the 2-D
   plot and editable table to the common path plus that arm's surfaces and
   branch rays.
6. Use ``Arm focus`` when you want to select matching global table rows without
   changing the plot view.
7. Future ``Arm Workbench`` editing should replace the global table with a
   virtual per-arm table. Edits in that virtual table must map back to real
   KrakenOS surface indices; the global surface list remains the canonical
   trace geometry.

The current implementation starts this workflow with metadata-discovered
``Arm view`` filtering in the 2-D plot and editable table. The table is
filtered through an internal row-index map, so the first ``#`` column still
shows the real KrakenOS surface index. Adding a new row while an arm is
selected tags that row with the selected arm metadata, but it does not yet
solve branch-local placement automatically; use detector placement helpers or
explicit decenter/tilt values for physical positioning.

Michelson-style layouts with detector/output display metadata use the more
physical four-leg convention instead: ``Leg 1`` for input/source-return,
``Leg 2`` for the transmitted mirror leg, ``Leg 3`` for the reflected mirror
leg, and ``Leg 4`` for the detector output leg. Use those leg entries when
placing components in a Michelson leg because they correspond to the four
visible optical legs around the splitter, not to individual ``T/R`` branch
histories.

Separate source and object status
---------------------------------

The splitter implementation now separates illumination rays from the
object/field concept for physical sources. ``Collimated disk source``,
``Gaussian beam``, and the random SourceRnd modes launch from the Source panel
origin and direction:

* ``Source X/Y/Z``: physical source origin in millimetres
* ``Source L/M/N``: chief-ray direction cosines; the UI normalizes them
* ``Ray count``: launched source rays before deterministic branch splitting

When one of these physical source modes is selected, sequential object/field
inputs that no longer apply are shown as ``NA`` and disabled. The ``Object``
surface remains in the KrakenOS table as a reference plane and part of the
global scene geometry, but it is not the ray launch source. This is the current
source/object split.

The UI is still not a full non-sequential scene editor with independent
``Source`` and ``Object`` nodes placed on different arms. That requires a
virtual arm-workbench layer: the global KrakenOS surface list remains the
canonical trace geometry, while each arm view presents only the components on
one branch and maps edits back to their real surface indices.

For cascading splitters, use the same rule manually: assign each branch element
to a parent splitter and branch selector in ``Element settings...``. The editor
will number each traced ``BRANCH_PATH`` as an ``Arm #`` after ``Update`` and
will still associate saved element metadata with matching branch paths. This
means a bare splitter can expose ``Arm 1`` / ``Arm 2`` from actual traced rays
before downstream components have been assigned. Remaining UI work is to use
those traced paths for branch-local insertion and placement.

Michelson detector/interferogram workflow
-----------------------------------------

Load ``Common Optical Layout -> Michelson Interferometer (Interferogram)`` for the
first Michelson-style geometry diagnostic. It uses an independent collimated
disk source at ``(0, 0, 0)`` with direction ``(0, 0, 1)``, a 45 degree
deterministic 50/50 splitter, one mirror in the transmitted arm, and one mirror
in the reflected arm. The returning rays hit the splitter a second time and
produce four ray-only output-port branches:

* transmit then transmit
* transmit then reflect
* reflect then transmit
* reflect then reflect

The preset is useful for checking geometry, arm labels, source/object split,
branch ancestry, power, phase metadata, and the first-order detector
interferogram. Use ``Actions -> Ray Inspector`` or ``Actions -> Branch Tree
Inspector`` after ``Update`` to inspect the branch paths. In the 2-D plot, the
four second-pass branch histories are clustered onto the two geometric output
ports: ``T -> T`` and ``R -> R`` leave through one port, while ``T -> R`` and
``R -> T`` leave through the detector output port. In the supplied Y/Z
schematic that detector port is drawn below the splitter, opposite the
reflected return mirror arm. The source-return histories, ``T -> T`` and
``R -> R``, are drawn back toward the input/reference side. These display
locations are stored in the final ``Image`` row's ``advanced["Display2D"]``
metadata so the schematic shows the logical Michelson arms even when the raw
non-sequential terminal segment from KrakenOS is not yet a full two-sided
beam-splitter port model.

The 2-D plot labels the four physical Michelson legs, not every directed
branch-history segment. This is the convention used by the editable table's
``Arm view`` and ``Arm focus`` entries for this preset:

* ``Leg 1: Input / source return``: source-to-splitter plus the source-return
  port.
* ``Leg 2: Transmit mirror leg``: splitter-to-transmit-mirror and the return
  path from that mirror back to the splitter.
* ``Leg 3: Reflect mirror leg``: splitter-to-reflect-mirror and the return path
  from that mirror back to the splitter.
* ``Leg 4: Detector output leg``: splitter-to-detector output port.

Use ``Arm view -> Leg 2: Transmit mirror leg`` or another leg entry when adding
or inspecting components in one physical Michelson leg. The table still stores
one canonical KrakenOS surface list underneath; the leg view filters that list
to the common splitter path plus rows tagged to the selected leg.

In Michelson-leg layouts, the first ``#`` column also shows the leg badge for
each row: ``L1`` for the input/source-return leg, ``L2`` for the transmitted
mirror leg, ``L3`` for the reflected mirror leg, and ``L4`` for the detector
output leg. These badges are row metadata labels, not traced branch-history
codes. The supplied Michelson preset stores its rows in the same ``L1`` to
``L4`` order so the full table reads in leg sequence.

To tag an existing arbitrary surface, select the row or contiguous group,
right-click the first ``#`` column, and use ``Leg assignment -> Assign to
Leg ...``. The editor will create/preserve an element group for those rows and
write the matching Michelson leg metadata.

The preset includes two grouped ``Aperture`` surfaces in each leg as a table
editing example. In the full ``Common`` view the rows are still one global
KrakenOS surface list, but the element metadata makes the leg filters behave
as expected:

* ``Leg 1 aperture pair`` is tagged ``Common`` and appears with the splitter in
  ``Leg 1: Input / source return``.
* ``Leg 2 aperture pair`` is tagged ``Return`` with ``branch_selector =
  "transmit"``.
* ``Leg 3 aperture pair`` is tagged ``Return`` with ``branch_selector =
  "reflect"``.
* ``Leg 4 aperture pair`` is tagged ``Detector``.

This is the intended manual workflow for now: switch to the leg in ``Arm
view``, add or group the surfaces that belong to that leg, then use
``Element settings...`` if you need to inspect or correct the stored leg
metadata. The orange aperture lines are intentionally simple and non-refractive;
they demonstrate component placement and can clip rays if their diameters are
made smaller than the source bundle.

The coherent interferogram still uses the recombined branch histories: ``T ->
R`` and ``R -> T`` share the detector output port, while ``T -> T`` and ``R ->
R`` share the source-return port.

The preset intentionally starts with one chief ray and compact clear apertures
so the plot reads like a Michelson schematic. Increase ``Ray count`` and
``Source radius`` only after the geometry is clear; large image/reference
diameters make KrakenOS draw longer terminal output rays and can visually
overwhelm the cavity.

To see fringes, select the ``Interf`` analysis button and click ``Update``.
The current analysis is an analytic two-beam diagnostic. It groups the traced
detector-port branches, ``T -> R`` and ``R -> T`` by default, averages their
``BRANCH_POWER``, ``BRANCH_PHASE``, and ``TOP`` values from the KrakenOS
``raykeeper``, then renders the ideal interference pattern from that branch
average plus the configured detector tilt. It is useful for checking branch
phase sign, output-port selection, visibility, and optical-path difference,
but it is not yet a true detector-pixel coherent phase sum of every traced ray.
The detector row stores the analysis settings in ``advanced["Interferogram"]``:

.. code-block:: python

   {
       "analysis_title": "Michelson Interferogram",
       "detector_port": "cross",        # cross: T->R with R->T; return: T->T with R->R
       "detector_size_mm": 12.0,
       "pixels": 256,
       "fringe_tilt_x_mrad": 1.5,       # set to 0 for the aligned uniform limit
       "fringe_tilt_y_mrad": 0.0,
       "opd_offset_um": 0.0,
       "visibility": 1.0,
   }

This is not a full diffraction, ray-binned detector, or round-trip Gaussian
field solver. Future work should accumulate complex field samples on detector
pixels from each traced ray, including ray position, phase, power, polarization,
and interpolation/binning weights, then propagate a complex Gaussian field
state through arbitrary tilted/folded branches.

Twyman-Green example
--------------------

Load ``Common Optical Layout -> Twyman-Green Interferometer (Interferogram)``
when you want the same tested return-arm recombination workflow with
Twyman-Green names. The transmitted return leg is tagged as the test optic
mirror, the reflected return leg is tagged as the reference flat, and the
detector output leg uses the same cross-port branch pair, ``T -> R`` and
``R -> T``.

To use it:

1. Load the preset from ``Layouts -> Common Optical Layout``.
2. Keep ``Ray count = 1`` while checking the geometry and leg labels.
3. Replace or edit the ``Test optic mirror`` row when you want to model a
   curved, decentered, or tilted test surface.
4. Select ``Interf`` and click ``Update`` to generate the branch-average
   Twyman-Green interferogram.

The matching Python example is
``KrakenOS/Examples/Examp_Twyman_Green_Interferometer.py``. It builds the
splitter, test optic, reference flat, and detector in plain KrakenOS code,
traces the deterministic branch paths, and computes the same analytic
branch-average interferogram used by the UI.

Mach-Zehnder example
--------------------

Load ``Common Optical Layout -> Mach-Zehnder Interferometer (Path Diagnostic)``
for the current Mach-Zehnder table and ray-path planning example. It includes
two 50/50 beam-splitter rows, two fold-mirror rows, and two output-detector
rows so the component sequence can be inspected, grouped, moved, and used as a
starting point for the next beam-splitter roadmap step.

Important limitation: this is not yet a true Mach-Zehnder interferogram.
KrakenOS/UI deterministic branching can currently validate the first physical
split and selected folded paths, but the second independent beam splitter does
not yet provide a robust two-input recombination model with detector-pixel
coherent summing. The example is therefore intentionally labeled ``Path
Diagnostic`` and does not attach an ``Interferogram`` settings block.

The matching Python example is
``KrakenOS/Examples/Examp_Mach_Zehnder_Interferometer.py``. It prints the
branch paths, surface sequence, and branch powers so the current limitation is
visible from plain API use as well as in the UI.

Saved metadata
--------------

Layouts store the splitter settings in the row's ``advanced`` dictionary:

.. code-block:: python

   {
       "surface": "Beam Splitter",
       "name": "50/50 coated front face",
       "diameter": 25.0,
       "tilt_x": 45.0,
       "thickness": 3.0,
       "glass": "BK7",
       "advanced": {
           "Element": {
               "element_id": "BS1",
               "element_name": "Splitter",
               "arm_role": "Common",
               "parent_splitter": "",
               "branch_selector": "",
               "arm_distance": 0.0,
               "local_decenter_x": 0.0,
               "local_decenter_y": 0.0,
               "local_tilt_x": 0.0,
               "local_tilt_y": 0.0,
               "local_tilt_z": 0.0,
           },
           "BeamSplitter": {
               "split_mode": "Deterministic branches",
               "reflectance": 0.5,
               "absorption": 0.0,
               "transmit_phase_deg": 0.0,
               "reflect_phase_deg": 180.0,
               "min_branch_power": 1e-3,
               "max_branch_depth": 8,
           }
       },
   }

``Element`` metadata is UI metadata. KrakenOS tracing remains geometry-driven;
the metadata lets the editor move elements within the same logical arm and
gives future placement and analysis tools a stable arm selector. If an element
is assigned to an arm, ``Move Up`` and ``Move Down`` search for the previous or
next element with the same arm role instead of crossing into another arm.
The table ``Arm focus`` dropdown selects matching arm elements without hiding
non-matching rows, preserving the surface-index mapping used by KrakenOS and by
the table editors.

The loader also accepts legacy roadmap-style aliases:

.. code-block:: python

   {
       "mode": "ideal",
       "transmittance": 0.5,
       "loss": 0.0,
       "max_split_depth": 8,
   }

Those aliases normalize to ``split_mode``, ``reflectance``, ``absorption``,
and ``max_branch_depth``.

Python example
--------------

The direct API example is
``KrakenOS/Examples/Examp_Beam_Splitter_50_50.py``. It builds a splitter
front surface, attaches both ``BeamSplitter`` metadata and the coating fallback,
adds a rear ``AIR`` surface for substrate exit, and uses ``NsTraceLoop`` with
``system.energy_probability = 0``.

Minimal setup:

.. code-block:: python

   import KrakenOS as Kos

   splitter_settings = {
       "split_mode": "Deterministic branches",
       "reflectance": 0.5,
       "absorption": 0.0,
       "transmit_phase_deg": 0.0,
       "reflect_phase_deg": 180.0,
       "min_branch_power": 1e-3,
       "max_branch_depth": 8,
   }

   wavelengths = [0.45, 0.55, 0.65]
   angles = [0.0, 45.0, 70.0]
   coating = [
       [[0.5 for _w in wavelengths] for _theta in angles],
       [[0.0 for _w in wavelengths] for _theta in angles],
       wavelengths,
       angles,
   ]

   splitter = Kos.surf()
   splitter.Name = "50/50 coated front face"
   splitter.TiltX = 45.0
   splitter.Thickness = 3.0
   splitter.Diameter = 25.0
   splitter.Glass = "BK7"
   splitter.AxisMove = 0.0
   splitter.BeamSplitter = splitter_settings
   splitter.Coating = coating

   rear = Kos.surf()
   rear.Name = "BK7 plate rear face"
   rear.Thickness = 60.0
   rear.Diameter = 25.0
   rear.TiltX = 45.0
   rear.Glass = "AIR"
   rear.AxisMove = 0.0

   obj = Kos.surf()
   obj.Name = "Input reference"
   obj.Thickness = 45.0
   obj.Diameter = 30.0
   obj.Glass = "AIR"
   obj.AxisMove = 0.0

   image = Kos.surf()
   image.Name = "Large diagnostic target"
   image.Diameter = 100.0
   image.Glass = "AIR"
   image.AxisMove = 0.0

   system = Kos.system([obj, splitter, rear, image], Kos.Setup())
   system.energy_probability = 0
   system.NsLimit = 120

Branch data
-----------

Each deterministic splitter hit can emit child records:

.. list-table::
   :header-rows: 1

   * - Data
     - Purpose
   * - ``branch_id`` and ``parent_branch_id``
     - Preserve trace ancestry for each reflected/transmitted child.
   * - ``branch_power``
     - Carry optical power through splitter, coating, absorption, and bulk
       transmission.
   * - ``branch_phase``
     - Preserve transmitted/reflected phase for coherent recombination.
   * - ``min_branch_power``
     - Prune weak branches.
   * - ``max_branch_depth``
     - Prevent recursive splitter explosions.
   * - ``max_total_branches``
     - Hard safety cap for pathological non-sequential layouts.

The Ray Inspector, Scene Graph, Branch Tree, CSV export, and branch-filtered
analysis controls consume these child records instead of showing one stochastic
path per launched ray.

Phase 2 source and arm workflow
-------------------------------

The detailed implementation plan is maintained in
``BEAM_SPLITTER_PHASE2_PLAN.md`` at the repository root. It covers
source-driven ray bundles, ``NA``/disabled sequential inputs, arm-aware element
metadata, placement helpers for transmitted/reflected paths, branch-aware
analysis, and validation examples.

Future tilted/folded/non-sequential Gaussian optics
---------------------------------------------------

Current Gaussian beam reports use the centered ``ParaxMatrices()`` ABCD chain.
That is appropriate for centered refractive laser layouts and first-order beam
expanders. It is not a full oblique astigmatic model for tilted splitters,
folded mirrors, or arbitrary non-sequential paths.

The future non-sequential Gaussian path should attach a Gaussian ``q`` state to
each deterministic branch. At every hit it should derive
local tangential and sagittal frames from the incident direction and surface
normal, propagate separate T/S ABCD updates, and carry branch power, optical
path length, and phase. The current Michelson ``Interf`` button uses the
available ray-branch OPD/phase metadata; the future Gaussian model should
replace the detector plane-wave approximation with propagated complex field
profiles.
