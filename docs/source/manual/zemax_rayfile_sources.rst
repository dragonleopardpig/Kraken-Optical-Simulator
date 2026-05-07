Zemax Rayfile Sources
=====================

Vendor LED and lamp models are often distributed as Zemax non-sequential
``Source File`` systems instead of ordinary sequential lens prescriptions.  In
the ``.zmx`` file these appear as ``MODE NSC`` plus one or more ``NSC_SFIL``
objects that reference binary ``.DAT`` ray databases.

Import workflow
---------------

Use ``File -> Import Zemax prescription or NSC source file...`` and select the
vendor ``.zmx`` sample file.  For the OSRAM LSG T676 package in
``attachment/LED/rayfile_LSG_T676_20200827_Zemax`` this is:

.. code-block:: text

   LSG_T676_20200827_sample_Zemax.zmx

The importer detects ``NSC_SFIL`` before the sequential Zemax parser runs.  A
source-file import intentionally produces:

* one ``Object`` row
* one visible ``Illumination Source`` row per referenced ``.DAT`` ray database
* one ``Image`` row as a detector/preview plane

It does not convert the enclosing ``NONSEQCO``/``STOP`` surface into an aperture
row, because that surface is only the Zemax container for the non-sequential
objects.  The actual optical information is in the binary ray database.

Ray sampling
------------

Zemax source ``.DAT`` files can contain millions of rays.  The UI keeps the full
file path and record count, but samples a deterministic subset for the 2D/3D
preview.  Change the normal ``Ray count`` field and press ``Update`` to change
the number of rays sampled from each imported source.

The supported binary format is the common Zemax 208-byte header followed by
7 little-endian 32-bit floats per ray:

.. code-block:: text

   x, y, z, l, m, n, flux

The first three values are launch coordinates in millimetres.  ``l, m, n`` are
direction cosines.  ``flux`` is preserved by the parser for future weighted
illumination analysis; the current preview uses the sampled ray geometry and the
source ``Power`` field.

Example saved layout source record
----------------------------------

A layout can also declare a Zemax rayfile source directly:

.. code-block:: python

   SETTINGS = {
       "source_model": "Zemax rayfile source",
       "ray_count": "201",
       "scene_sources": [
           {
               "source_id": "source:osram-red",
               "name": "OSRAM LSG T676 red",
               "model": "Zemax rayfile source",
               "role": "illumination",
               "physical": True,
               "enabled": True,
               "origin": [0.0, 0.0, 0.0],
               "direction": [0.0, 0.0, 1.0],
               "ray_count": 201,
               "power": 1.0,
               "wavelength": 0.6325,
               "rayfile_path": "attachment/LED/rayfile_LSG_T676_20200827_Zemax/rayfile_LSG_T676_super_red_5M_20200827_Zemax.DAT",
               "record_count": 5000000,
           }
       ],
   }

The ``origin`` and ``direction`` fields place and orient the vendor rayfile in
the scene.  With the default direction, the raw Zemax rayfile coordinates are
used directly.  Changing ``direction`` rotates local ``+Z`` emission into the
requested world direction.

For readable source-driven layout previews, a saved source record may also set
``rayfile_preview_cone_angle_deg`` and ``rayfile_preview_candidates``.  These
fields keep the vendor rayfile as the source model, but choose preview rays near
local ``+Z`` from a larger deterministic candidate set before tracing.

Validation
----------

The OSRAM import path is covered by a focused validation command:

.. code-block:: bash

   python -m KrakenOS.UI.validate_zemax_rayfile_source

It checks that the sample ``.zmx`` exposes the red and green ``NSC_SFIL``
objects, verifies the 5M-record ``.DAT`` files, samples finite normalized rays,
and confirms that the editor imports the file as illumination-source rows rather
than as a single aperture.

Current limitations
-------------------

The importer currently exposes the Zemax source rays.  Vendor package geometry
referenced by ``NSC_IMPT`` is not automatically converted into an optical solid
or mechanical overlay during this source import.  Import the STEP/IGES geometry
separately when it is needed for mechanical context or future optical CAD face
assignment.

Beam-splitter imaging example
-----------------------------

Load ``Layouts -> Beam Splitters / Folds -> Zemax LED Beam-Splitter Imaging``
for a source-driven setup that uses the OSRAM LED rayfile directly:

* the OSRAM ``.DAT`` source is an ``Illumination Source`` row and launches from
  the top port at ``(0, 45, 45) mm`` along ``-Y``;
* the Object row is only reference geometry and does not launch any rays;
* the 45 degree splitter reflects the useful illumination branch left to a
  semantic ``Object Target`` surface;
* the object-return branch hits the splitter again, transmits through a simple
  BK7 imaging lens, and reaches Image.

``Object Target`` is currently a specular proxy in the trace backend. It keeps
the source/object split workflow readable while diffuse/BRDF object scattering
remains future work.

The corresponding script is:

.. code-block:: bash

   python KrakenOS/Examples/Examp_Zemax_LED_Beam_Splitter_Imaging.py
   python -m KrakenOS.UI.validate_zemax_led_splitter_imaging

This example is deliberately source-driven: adding or editing the imaging lens
does not switch back to the legacy Object-launched pupil fan.  If no rays appear,
check that ``attachment/LED/rayfile_LSG_T676_20200827_Zemax`` still contains the
OSRAM ``rayfile_LSG_T676_green_100k_20200827_Zemax.DAT`` file.

Because a real vendor LED rayfile emits a broad angular distribution, the
example defaults the 2-D ``Rays`` selector to ``Beam-splitter paths``.  This
shows representative non-primary splitter paths instead of every sampled LED
ray.  Change ``Rays`` to ``All rays`` when you intentionally want to inspect
direct stray light and waste branches.
