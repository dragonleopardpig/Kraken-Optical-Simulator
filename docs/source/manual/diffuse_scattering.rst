Diffuse And BRDF Scattering
===========================

KrakenOS UI now exposes built-in diffuse object workflows.  It is not a full
measured-BRDF engine yet, but it removes the previous hard limitation where an
object target could only be represented as a specular mirror proxy.

Surface Type
------------

Use the editable table surface type ``Diffuse Object`` for a non-sequential
scattering target.  Internally the row still uses ``Glass='MIRROR'`` so the
native KrakenOS hit solver treats it as a reflective boundary, but the row also
stores a ``DiffuseScatter`` metadata block.  During ``NsTrace`` the core branch
queue intercepts this hit and spawns deterministic scatter child rays instead
of the normal specular reflection.

Right-click the surface row and choose ``Coating / Polarization -> Diffuse /
BRDF Settings...``.  The current settings are:

``model``
  ``Lambertian`` for matte diffuse scatter, ``Oren-Nayar`` for rough diffuse
  reflection under directional illumination, or ``Cosine Lobe`` for a glossy
  Phong-style lobe around the physical specular reflection direction.

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
  For ``Cosine Lobe`` this limits the glossy lobe around the specular
  reflection direction.

``lobe_exponent``
  ``Cosine Lobe`` only.  ``0`` is broad, Lambertian-like over the selected lobe
  cone; larger values make the lobe narrower and more mirror-like.  Typical UI
  preview values are roughly ``10`` to ``100``.

``roughness_deg``
  ``Oren-Nayar`` only.  Sigma roughness angle in degrees.  ``0`` collapses
  toward Lambertian-like diffuse weighting; larger values increase the
  rough-diffuse directional contrast for oblique illumination.

``min_branch_power`` and ``max_branch_depth``
  Branch pruning controls used to prevent runaway recursive diffuse bounces.

``target_surface``
  Optional surface index for target-guided sampling.  Leave it as ``None`` for
  a deterministic hemisphere/cone fan.  Set it to a pupil, lens entrance,
  detector, beam splitter return aperture, or Image surface when the goal is
  source-driven imaging and the useful camera path would otherwise receive too
  few rays.

``target_radius_scale``
  Multiplier for the selected target surface clear radius.  ``1.0`` samples the
  nominal clear aperture; smaller values concentrate rays near the target
  center and larger values deliberately overfill the target for vignetting
  checks.

Guided Target Sampling
----------------------

Guided sampling is deterministic importance sampling, not a shortcut back to a
specular object proxy.  At a ``Diffuse Object`` hit the core builds child rays
from the hit point to samples on the selected target surface.  Each child branch
is weighted by the selected scatter model and the approximate solid angle of
that target sample:

.. code-block:: python

   diffuse = {
       "model": "Lambertian",
       "backend": "Built-in",
       "reflectance": 0.8,
       "sample_count": 21,
       "max_scatter_angle_deg": 90.0,
       "target_surface": 1,       # e.g. splitter return aperture / entrance pupil
       "target_radius_scale": 0.9,
       "min_branch_power": 1e-8,
       "max_branch_depth": 4,
   }

If no valid target sample is visible from the diffuse hit, the tracer falls
back to the unguided scatter fan so the row still behaves as a diffuse
surface.

Examples
--------

Open ``Layouts -> Diffuse Object Lambertian Scatter`` or run:

.. code-block:: bash

   python -m KrakenOS.Examples.Examp_Diffuse_Object_Lambertian_Scatter

The example launches one collimated ray from the source plane to a ``Diffuse
Object`` surface.  The trace result contains one branch per Lambertian child
sample.  Each branch has a ``BRANCH_PATH`` ending in ``/scatterNN`` and a
``BRANCH_POWER`` equal to ``reflectance / sample_count`` for this deterministic
preview.

Open ``Layouts -> Diffuse Object Cosine Lobe Scatter`` or run:

.. code-block:: bash

   python -m KrakenOS.Examples.Examp_Diffuse_Object_Cosine_Lobe_Scatter

This example uses ``model='Cosine Lobe'`` with ``lobe_exponent=35`` and a
``25`` degree scatter cone.  The generated branches stay near the physical
specular reflection direction, which is useful for satin, polished, or
partially glossy targets where a Lambertian surface would be too broad.

Open ``Layouts -> Diffuse Object Oren-Nayar Scatter`` or run:

.. code-block:: bash

   python -m KrakenOS.Examples.Examp_Diffuse_Object_Oren_Nayar_Scatter

This example uses ``model='Oren-Nayar'`` with ``roughness_deg=35`` and an
oblique collimated source.  Unlike the Lambertian fixture, the deterministic
``scatterNN`` child powers are not uniform; they follow the rough-diffuse
directional term produced by the Oren-Nayar BRDF.

Regression check:

.. code-block:: bash

   python -m KrakenOS.UI.validate_diffuse_object_scatter
   python -m KrakenOS.UI.validate_diffuse_object_cosine_lobe
   python -m KrakenOS.UI.validate_diffuse_object_oren_nayar

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

* The built-in models are deterministic Lambertian, Oren-Nayar, and
  cosine-lobe sampling, not measured BRDF data.
* The branch metadata preserves/project-transports the current Jones vector; it
  does not yet carry a full depolarized Stokes distribution.
* Guided target sampling uses an approximate solid-angle weight and is intended
  for deterministic UI workflows.  Measured-BRDF sampling and depolarized
  Stokes transport remain future backend work.
