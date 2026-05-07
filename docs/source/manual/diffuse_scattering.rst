Diffuse And BRDF Scattering
===========================

KrakenOS UI now exposes a first built-in diffuse object workflow.  It is not a
full measured-BRDF engine yet, but it removes the previous hard limitation where
an object target could only be represented as a specular mirror proxy.

Surface Type
------------

Use the editable table surface type ``Diffuse Object`` for a non-sequential
scattering target.  Internally the row still uses ``Glass='MIRROR'`` so the
native KrakenOS hit solver treats it as a reflective boundary, but the row also
stores a ``DiffuseScatter`` metadata block.  During ``NsTrace`` the core branch
queue intercepts this hit and spawns deterministic Lambertian child rays instead
of the normal specular reflection.

Right-click the surface row and choose ``Coating / Polarization -> Diffuse /
BRDF Settings...``.  The current settings are:

``model``
  ``Lambertian``.  This is the only active model in the built-in backend.

``backend``
  ``Built-in``.  ``pySCATMECH`` is documented below as the future optional
  physics backend.

``reflectance``
  Diffuse albedo in ``[0, 1]``.  A value of ``0.8`` means the total spawned
  diffuse branch power is 80 percent of the incident branch power.

``sample_count``
  Number of deterministic child rays spawned per diffuse hit.  The UI example
  uses nine rays: one surface-normal ray plus cosine-weighted off-axis samples.

``max_scatter_angle_deg``
  Scatter cone half-angle.  ``90`` degrees is a full Lambertian hemisphere.
  Smaller values are useful as readable preview cones, but they no longer
  represent the whole hemisphere angular domain.

``min_branch_power`` and ``max_branch_depth``
  Branch pruning controls used to prevent runaway recursive diffuse bounces.

Example
-------

Open ``Layouts -> Diffuse Object Lambertian Scatter`` or run:

.. code-block:: bash

   python -m KrakenOS.Examples.Examp_Diffuse_Object_Lambertian_Scatter

The example launches one collimated ray from the source plane to a ``Diffuse
Object`` surface.  The trace result contains one branch per Lambertian child
sample.  Each branch has a ``BRANCH_PATH`` ending in ``/scatterNN`` and a
``BRANCH_POWER`` equal to ``reflectance / sample_count`` for this deterministic
preview.

Regression check:

.. code-block:: bash

   python -m KrakenOS.UI.validate_diffuse_object_scatter

pySCATMECH Roadmap
------------------

The local ``~/Projects/pySCATMECH`` clone is directly useful for the next
physics step.  It provides SCATMECH bindings for physics-based polarized
surface-scattering models:

* ``pySCATMECH.brdf.BRDF_Model`` evaluates scalar, Mueller, and Jones BRDF.
* ``pySCATMECH.local.Local_BRDF_Model`` evaluates differential scattering cross
  sections for particles or localized defects on surfaces.
* ``pySCATMECH.fresnel`` and ``pySCATMECH.mueller`` provide thin-film,
  polarization, Jones, Mueller, and Stokes helpers.

The intended integration is an optional backend behind the same
``DiffuseScatter`` metadata.  KrakenOS should continue to own ray/surface hit
finding, geometry, non-sequential branch bookkeeping, and detector analysis.
The BRDF backend should only answer this question at each hit: given wavelength,
incident direction, surface normal, material/coating state, and polarization,
what outgoing directions and power/polarization weights should be spawned?

Current limitations:

* The built-in model is deterministic Lambertian sampling, not a measured BRDF.
* The branch metadata preserves/project-transports the current Jones vector; it
  does not yet carry a full depolarized Stokes distribution.
* Importance sampling toward a camera lens is not implemented yet.  A true
  illumination/imaging workflow will need either many rays or target-guided
  BRDF sampling with correct solid-angle weighting.
