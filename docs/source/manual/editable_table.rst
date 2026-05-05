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

Validation
----------

Run the workflow regression check with:

.. code-block:: bash

   python -m KrakenOS.UI.validate_table_component_workflow

The check inserts a common component while preserving global source/field
settings, then copies and pastes grouped component rows while confirming that
``Object`` and ``Image`` are not duplicated.
