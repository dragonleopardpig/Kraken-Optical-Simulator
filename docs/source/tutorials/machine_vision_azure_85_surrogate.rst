Case Study 4: AZURE ELS-85 mm Machine-Vision Surrogate
======================================================

This page documents the surrogate layout
``Machine Vision 85 mm Azure (Datasheet 0.5X-2.0X)``.  It is based on the local
datasheet:

.. code-block:: text

   attachment/Lens/ELS-85-4.5V16K/ELS-85 4.5V16K_specification.pdf

The AZURE Photonics ELS-85/4.5V16K is a large-format 16K/12K line-scan
machine-vision lens.  It is built the same way as the PYRITE 85 mm surrogate
(see :doc:`machine_vision_pyrite_85_surrogate`); the two are near twins (both
85 mm, F/4.5, 0.5x-2.0x), so they can be used interchangeably for layout work.

What The Surrogate Is
---------------------

The vendor datasheet does not provide the internal prescription, so the KrakenOS
layout is a first-order blackbox model, not a decoded prescription.  It uses two
ideal thin-lens groups and one aperture stop inside the published optical vertex
span.  The goal is to make the UI behave like the 85 mm line-scan lens at the
level needed for layout work, field sampling, camera-distance studies, and
Open 3D placement.  Because the model is ideal it carries no real aberration --
a traced spot is defocus only; attach a Zemax wavefront / spot-radius export (as
for the 150 mm 15056 lens) to augment it with the vendor's measured OPD.

The model uses these public datasheet values:

.. list-table::
   :header-rows: 1

   * - Quantity
     - Datasheet value
     - Surrogate use
   * - Product
     - ELS-85/4.5V16K (material code 3.A01.018545V16K-A)
     - Menu title and documentation identity
   * - Effective focal length
     - 85 mm
     - Paraxial effective focal length
   * - Magnification range
     - 0.5x to 2.0x, nominal 1x
     - Default layout is the 1x conjugate
   * - F-number
     - F/4.5, manual iris
     - Default aperture is F/4.5
   * - Image format
     - 57.3 mm (16K) / 62 mm (12K), max image circle 68 mm
     - Image and object row diameter (68 mm); the sampled field uses the shared camera workflow
   * - Resolution
     - 3.5 µm (16K) / 5 µm (12K)
     - Pixel scale the lens is designed to resolve
   * - Maximum chief-ray angle
     - 9.54 degrees
     - Field / telecentricity sanity check
   * - Working-distance range
     - 225 / 142 / 99 mm at 0.5x / 1.0x / 2.0x (optimum 142 mm)
     - Checked against the 0.5x to 2.0x model conjugates
   * - Back focus
     - 141.85 mm
     - Rear glass vertex to image at 1x
   * - Optical total length (TTL)
     - 196.8 mm
     - Front glass vertex to image at 1x; ``TTL - back focus`` pins the glass span
   * - Distortion / relative illumination
     - < 0.0025 % / 93.7 %
     - Near-distortion-free, near-flat illumination (not modelled by the ideal groups)

The datasheet does not publish the Gaussian cardinals.  They are inferred below
from the symmetric 1x geometry, giving ``SF = -56.85 mm``, ``S'F' = +56.85 mm``,
``H1 = 28.15 mm`` behind the front vertex and ``H2 = 28.15 mm`` ahead of the rear
vertex (``HH' = -1.30 mm``).

Vendor STEP Overlay
-------------------

The preset records the local vendor STEP file:

.. code-block:: text

   attachment/Lens/ELS-85-4.5V16K/ELS-85-4.5V16K.STEP

The STEP is used as a mechanical overlay, while the KrakenOS table remains the
paraxial blackbox optical surrogate.  OpenCascade extraction finds the two usable
glass vertex surfaces as:

.. list-table::
   :header-rows: 1

   * - STEP face
     - Role in this surrogate
     - STEP local axis coordinate
   * - ``F062``
     - First glass surface / front optical vertex
     - ``+13.283194712 mm``
   * - ``F064``
     - Last glass surface / rear optical vertex
     - ``-41.716909857 mm``

Those two surfaces are separated by ``55.000104570 mm``.  The datasheet gives no
explicit ``Σd``, but ``TTL - back focus = 196.8 - 141.85 = 54.95 mm`` matches the
STEP glass span to within the 0.1 mm rounding of the published TTL -- which also
confirms that "back focus" is referenced to the rear glass vertex.  The surrogate
uses the exact STEP glass span for its front-to-rear vertex distance.  It stores a
lens STEP placement offset of ``-3.848950487 mm`` so the STEP's first and last
glass vertices overlay the surrogate's front and rear optical vertex datums.  The
mechanical front shoulder of the STEP is intentionally not used as the optical
datum.

Default UI Settings
-------------------

The preset follows the same working defaults as ``Machine Vision 150Mm Measured``
so the layouts can be used the same way in Open 3D.  It inherits the same ray
display, source, detector, non-sequential, tolerance, atmosphere, optimization,
and CAD overlay defaults, including the Allied Vision ``hr25MCX`` camera model and
``attachment/Cameras/hr25MCX/3D_CAD_HR25xCXP.STEP`` camera overlay.  The image format is
camera- and FOV-driven at runtime; the 68 mm image-circle row diameter only sets
the maximum the lens can cover.

Only lens-specific defaults differ from the 150 mm measured layout:

* The aperture default is ``F/4.5`` from the ELS-85 datasheet.
* The real-image field default is ``11.52 mm`` so the initial field sampling
  matches the shared camera workflow rather than the full 68 mm image-circle
  capability.
* The lens STEP overlay uses ``attachment/Lens/ELS-85-4.5V16K/ELS-85-4.5V16K.STEP`` and the
  glass-vertex alignment offset described above.
* The auxiliary Open 3D optical STEP overlay is left empty.

How The Blackbox Is Built
-------------------------

At 1x the lens is symmetric (front working distance ``= back focus = 141.85 mm``),
so each principal plane sits one focal length short of the 2f' conjugate:

.. code-block:: text

   H1 = 2 f' - back focus = 170 - 141.85 = 28.15 mm  (behind the front vertex)
   H2 = 28.15 mm                                       (ahead of the rear vertex)

That makes ``SF = H1 - f' = -56.85 mm`` and ``S'F' = f' - 28.15 = +56.85 mm``.
Two equal thin-lens groups (``f = 159.48852477 mm``) placed symmetrically about a
centred stop reproduce ``EFL = 85``, ``SF``, ``S'F'``, ``H1`` and ``H2`` exactly
in the 55.0001 mm glass span.

The surrogate rows are:

.. list-table::
   :header-rows: 1

   * - Row
     - Role
     - Distance / power
   * - Object
     - 1x finite object plane
     - 141.85 mm before the first optical vertex datum
   * - Front Optical Vertex Datum
     - First optical vertex reference
     - 17.63852477 mm to group 1
   * - Blackbox Group 1
     - Ideal thin-lens group
     - ``f = 159.48852477 mm``
   * - Aperture Stop F/4.5
     - Stop / F-number control
     - 9.86152751 mm after group 1 (centred stop)
   * - Blackbox Group 2
     - Ideal thin-lens group
     - ``f = 159.48852477 mm``
   * - Rear Optical Vertex Datum
     - Last optical vertex reference
     - 141.85 mm to image at 1x
   * - Image / Sensor
     - 1x sensor plane
     - 68 mm image circle

The same cardinals imply these finite-conjugate working points when measured from
the optical vertex datums:

.. list-table::
   :header-rows: 1

   * - Magnification
     - Object to front optical vertex
     - Rear optical vertex to image
   * - 0.5x
     - 226.85 mm
     - 99.35 mm
   * - 1.0x
     - 141.85 mm
     - 141.85 mm
   * - 2.0x
     - 99.35 mm
     - 226.85 mm

The published working-distance range (225 / 142 / 99 mm) is measured to the first
mechanical element, so the optical-vertex distances bracket the datasheet range
with the expected small mechanical offset.

Rendered Layout
---------------

Load ``Machine Vision 85 mm Azure (Datasheet 0.5X-2.0X)`` from the Machine Vision
menu and open it in Open 3D.  The layout shows optical vertex datums, two blackbox
thin-lens groups, an F/4.5 stop, the 1x image plane, and the vendor barrel STEP as
a mechanical overlay.  The STEP is a multi-body assembly, so it is loaded with
``lens_step_largest_component_only = False`` to render the whole ~52 mm barrel (the
largest single connected solid is only an ~18 mm ring).  Its optical axis is the
STEP's local -X; the ``front-face = "max"`` alignment plus the -3.849 mm glass-vertex
offset seat the front glass surface on the front optical-vertex datum (141.85) and
the rear glass on the rear datum (196.85), enclosing the two thin-lens groups -- so
no 180-degree flip is used (unlike the +Z-authored PYRITE 85 STEP).

Known Limits
------------

* Internal curvatures, glasses, aspheres, coatings, tolerances, and MTF are not
  reconstructed from the datasheet.
* The two thin-lens groups reproduce first-order cardinal data; they do not
  reproduce the vendor's real aberration correction (the traced spot is defocus
  only until a wavefront export is attached).
* The 1x symmetric assumption is taken from the near-equal front working distance
  and back focus; a vendor prescription would pin any residual asymmetry.
* The mechanical V-mount, iris, filter thread, and barrel outline are represented
  by the STEP overlay rather than by the sequential surrogate rows.

Validation
----------

The validation script checks that the layout is discoverable in the Machine
Vision menu, that the two-thin-group paraxial matrix reproduces the inferred
effective focal length, front/back focal distances, and principal planes, and that
the vendor STEP's ``F062`` and ``F064`` remain the matched first and last glass
surfaces spanning the surrogate's optical vertex distance:

.. code-block:: bash

   python -m KrakenOS.UI.validate_machine_vision_azure_85_surrogate
