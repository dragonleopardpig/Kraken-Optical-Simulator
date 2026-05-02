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
  ``BRANCH_POWER``, ``BRANCH_PHASE``, and ``BRANCH_LABEL``
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
   ``Non-Sequential Preview`` is still available.
6. Leave ``NS probabilistic coating split`` off for deterministic splitters.
7. For a finite plate, set the splitter row ``Glass`` to the substrate, set
   ``Thickness`` to the plate thickness, and add a following ``Standard`` row
   with ``Glass=AIR`` as the rear face. In the editable UI table, use the same
   rear ``TiltX`` as the front face for a parallel plate; use a different rear
   tilt to model a wedge.
8. Click ``Update`` and inspect paths with ``Actions -> Ray Inspector``,
   ``Actions -> Branch Tree Inspector``, and
   ``Actions -> Non-Sequential Scene Graph``.

The ``Beam Splitter 50/50 Example`` uses an exact-count collimated disk source.
Each launched source ray creates transmitted and reflected branch records, so
the Ray Inspector can show the source-ray index, branch power, and launch
metadata for each child path.

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
path length, and phase. Coherent interference analysis should wait until that
branch state is reliable; otherwise Michelson-style plots would look precise
while using incomplete physics.
