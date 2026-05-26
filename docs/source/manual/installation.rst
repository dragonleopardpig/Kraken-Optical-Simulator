Installation And Prerequisites
==============================

KrakenOS is a Python optical ray-tracing library built around NumPy,
Matplotlib, PyVista, VTK, SciPy, and Pandas. The provisional manual lists older
tested versions from the Python 3.7 era; this repository now runs on the
project devenv with Python 3.13 and current dependency versions.

Basic installation paths
------------------------

Install from PyPI when using KrakenOS as a library:

.. code-block:: bash

   pip install KrakenOS

For development in this repository, use the provided devenv and install the
editable package into its virtual environment:

.. code-block:: bash

   direnv allow
   devenv shell kraken-install

The development environment installs the package in editable mode together with
the numerical, plotting, VTK/PyVista, Qt, and analysis dependencies used by the
layout editor, including the ``pygmo`` optimizer backend used by the
Optimization panel.

For a normal Python virtual environment on this branch, install the UI extra:

.. code-block:: bash

   python -m pip install --upgrade pip "setuptools<82" wheel
   python -m pip install -e ".[ui]"

If the Optimization panel reports that the backend is unavailable, run:

.. code-block:: bash

   python -m KrakenOS.UI.validate_optimization_backend

Running the layout editor
-------------------------

After the environment is active, launch the current UI with:

.. code-block:: bash

   python -m KrakenOS.UI.layout_editor

The UI starts in the reset state with only Object and Image rows. Use the File,
Layouts, Machine Vision, and Examples menu-bar entries to load layouts,
catalog optics, examples, and Zemax text files.

Manual source
-------------

The converted source manual is available as a PDF in:

.. code-block:: text

   KrakenOS/Docs/USER_MANUAL_KrakenOS_Provisional.pdf
