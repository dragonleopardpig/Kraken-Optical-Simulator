Editable Table Workflow
=======================

The editable table is the working prescription for sequential layouts and the
surface/object list for non-sequential scene workflows. A single row is a
KrakenOS surface. A component is one or more adjacent rows grouped as an
``Element`` so that the UI can move, flip, copy, paste, ungroup, and path-tag
the optical component as one unit.

Loading versus inserting
------------------------

Use ``Layouts`` or ``Examples`` when you want to load a complete preset system.
Those presets may intentionally apply object distance, source, field, pupil,
wavelength, analysis, and plot defaults.

Use ``Insert`` when you want to keep the current design and add an optic below
the selected row:

* ``Insert -> Common Component`` splices component-style common layouts such as
  lenses, mirrors, and F-theta components into the current table.
* ``Insert -> Stock Lens Catalog...`` imports Edmund/Thorlabs-style ``.ZMF``
  stock lenses and expands the selected catalog part into ordinary table rows.
* ``Insert -> Optical STL Solid...`` inserts a file-backed KrakenOS optical
  solid row.
* ``Insert -> Component to Current Path View...`` inserts a detector, aperture,
  thin lens, refractive surface, or mirror into the active beam-splitter path.

The insertion commands do not overwrite the current source, field, pupil,
wavelength, analysis, or display settings. They only add component rows.

Insertion point
---------------

The table uses the current selection as the insertion anchor:

* If one or more rows are selected, inserted rows go below the last selected row.
* If the selected row belongs to a grouped element, selecting the ``#`` column
  selects the whole element block.
* If no row is selected, inserted rows go before the final ``Image`` row.
* ``Object`` and ``Image`` stay anchored and are not treated as component rows.

Surface and element clipboard
-----------------------------

The table supports component-aware clipboard operations:

* ``Ctrl-C`` copies selected surface rows.
* If any selected row is part of a grouped element, the complete contiguous
  element block is copied.
* ``Ctrl-V`` pastes copied rows below the current selection.
* ``Object`` and ``Image`` are skipped on copy/paste.
* Pasted grouped elements receive independent element labels, so later Move
  Up/Down, Flip, Ungroup, and path assignment act on the pasted component rather
  than merging it with the source component.

The same commands are also available from ``Edit`` and from the table
right-click menu.

Surface right-click menu
------------------------

Right-clicking the ``Surface`` cell no longer opens only the type chooser. The
same full menu is available from any table cell:

* ``Convert Type`` changes the row to Standard, Aperture, Mirror, Beam Splitter,
  Thin Lens, Grating, Image, or converts the selected physical row to an
  Optical STL Solid.
* ``Insert Component Below`` splices singlets, doublets, flat mirrors,
  plate/window rows, wedge prism rows, a right-angle prism primitive, a cube
  beam-splitter primitive, stock lenses, STL solids, or path-local components.
* ``Shape / Aperture`` exposes Shape Builder plus circular, rectangular,
  polygon/UDA, annulus, spider, and rectangular clear-aperture presets.
* ``Material`` opens the glass catalog and applies common materials to selected
  rows.
* ``Coating / Polarization`` opens coating/material editing, applies coating
  presets, enables metal Fresnel mirror mode, and configures beam-splitter
  Fresnel P/S behavior.
* ``Geometry`` aligns the local row orientation, sets TiltX incidence, reverses
  elements, and assigns/places rows on the current Path view.
* ``Element`` contains grouping, copy/paste, move, path assignment, and path role
  commands.
* ``Diagnostics`` sets trace/analysis targets and opens ray/path/scene
  inspectors.
* ``Advanced`` opens native KrakenOS attributes, Error Map, Grating/Galvo
  settings, and STL diagnostics/placement.

Prisms and cube beam splitters
------------------------------

Simple prisms can be built from table rows. A wedge prism is two tilted Standard
surfaces: the first enters glass, the second exits to AIR. The right-click
``Insert Component Below -> Wedge Prism`` command creates this starter block.

For arbitrary prism solids, use ``Convert Type -> Optical STL Solid`` or
``Insert Component Below -> Optical STL Solid``. A closed STL is the physically
correct UI representation when rays may hit side faces, experience total
internal reflection, or leave through a non-sequential face.

``Insert Component Below -> Cube Beam Splitter`` creates a practical starter:
entrance face, internal 45 degree Beam Splitter surface, and transmit exit face.
It is enough to start deterministic transmitted/reflected path design. For a
closed cube with every side face available to tracing, use an Optical STL Solid
and set the Beam Splitter coating/path metadata on the internal splitter
surface.

Tilt and decenter tolerance overlays
------------------------------------

The pose columns ``TiltX``, ``TiltY``, ``TiltZ``, ``DespX``, ``DespY``, and
``DespZ`` accept comma-separated values or ``start:stop:step`` ranges. For
example, enter ``-0.1, 0, 0.1`` in ``TiltY`` or ``-0.05:0.05:0.05`` in
``DespX``.

The middle value becomes the nominal scalar KrakenOS row value. The full list is
stored as ``Advanced -> Display2D -> pose_tolerance_overlay`` and the 2-D plot
draws additional dashed ray traces plus dashed affected surface positions. If
several pose cells contain lists with the same length, the values are swept
together by index. If the list lengths differ, combinations are generated and
truncated to 25 variants.

For grouped elements, enter the pose list once on any row in the element. The
UI applies the same delta sweep to every row in the contiguous element block, so
a doublet behaves like one mechanically shifted component instead of three
independent tilted/decentered surfaces.

Mirror ``TiltX`` keeps the dedicated galvo/folded-scan interpretation because
its displayed value is mirror slant, not raw KrakenOS local tilt. It still uses
the same comma/range entry syntax.

Validation
----------

Run the workflow regression check with:

.. code-block:: bash

   python -m KrakenOS.UI.validate_table_component_workflow

The check inserts a common component while preserving global source/field
settings, then copies and pastes grouped component rows while confirming that
``Object`` and ``Image`` are not duplicated.
