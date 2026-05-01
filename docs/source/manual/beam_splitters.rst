Beam Splitters
==============

The UI now has a ``Beam Splitter`` surface type. It is a first UI/core bridge
for splitters, not the final deterministic non-sequential branch engine.

Current capability
------------------

``Beam Splitter`` rows store a ``BeamSplitter`` metadata dictionary and
automatically write a KrakenOS ``Coating = [R, A, W, THETA]`` table. With
``Non-Sequential Preview`` and ``NS probabilistic coating split`` enabled,
KrakenOS can use that coating table to choose a reflected or transmitted path
for each ray.

The current core behavior is Monte Carlo, one path per incident ray. A single
incident ray does not yet produce both reflected and transmitted child rays.
That deterministic branch queue is the next core implementation step.

UI workflow
-----------

1. Load ``Common Optical Layout -> Beam Splitter 50/50 Example``.
2. Select the splitter row, or change an ordinary row's surface type to
   ``Beam Splitter``.
3. Right-click the row and choose ``Beam splitter settings...``.
4. Set ``Reflectance R`` and ``Absorption A``. Transmission is
   ``T = 1 - R - A``.
5. Use ``Trace mode -> Non-Sequential Preview``.
6. Enable ``NS probabilistic coating split`` for the current stochastic split.
7. Click ``Update`` and inspect paths with ``Actions -> Ray Inspector``,
   ``Actions -> Branch Tree Inspector``, and
   ``Actions -> Non-Sequential Scene Graph``.

Saved metadata
--------------

Layouts store the splitter settings in the row's ``advanced`` dictionary:

.. code-block:: python

   {
       "surface": "Beam Splitter",
       "name": "50/50 beam splitter",
       "diameter": 25.0,
       "tilt_x": 45.0,
       "glass": "AIR",
       "advanced": {
           "BeamSplitter": {
               "split_mode": "Monte Carlo coating split",
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
surface, attaches both ``BeamSplitter`` metadata and the coating fallback, and
uses ``NsTraceLoop`` with ``system.energy_probability = 1``.

Minimal setup:

.. code-block:: python

   import KrakenOS as Kos

   splitter_settings = {
       "split_mode": "Monte Carlo coating split",
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
   splitter.Name = "50/50 beam splitter"
   splitter.TiltX = 45.0
   splitter.Diameter = 25.0
   splitter.Glass = "AIR"
   splitter.BeamSplitter = splitter_settings
   splitter.Coating = coating

   obj = Kos.surf()
   obj.Name = "Input reference"
   obj.Thickness = 45.0
   obj.Diameter = 30.0
   obj.Glass = "AIR"

   image = Kos.surf()
   image.Name = "Large diagnostic target"
   image.Diameter = 100.0
   image.Glass = "AIR"

   system = Kos.system([obj, splitter, image], Kos.Setup())
   system.energy_probability = 1
   system.NsLimit = 120

Future deterministic branch queue
---------------------------------

The planned core work is to make a ``Beam Splitter`` hit spawn both child rays:

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

Once the queue exists, the existing Ray Inspector, Scene Graph, Branch Tree,
CSV export, and branch-filtered analysis controls can consume the real child
records instead of showing one stochastic path per launched ray.

Future tilted/folded/non-sequential Gaussian optics
---------------------------------------------------

Current Gaussian beam reports use the centered ``ParaxMatrices()`` ABCD chain.
That is appropriate for centered refractive laser layouts and first-order beam
expanders. It is not a full oblique astigmatic model for tilted splitters,
folded mirrors, or arbitrary non-sequential paths.

The future non-sequential Gaussian path should attach a Gaussian ``q`` state to
each branch produced by the deterministic queue. At every hit it should derive
local tangential and sagittal frames from the incident direction and surface
normal, propagate separate T/S ABCD updates, and carry branch power, optical
path length, and phase. Coherent interference analysis should wait until that
branch state is reliable; otherwise Michelson-style plots would look precise
while using incomplete physics.
