Handling the 3D Viewer
======================

This page is a faithful conversion of Section 6 of the provisional manual
(``KrakenOS/Docs/USER_MANUAL_KrakenOS_Provisional.pdf``, page 28).

When ``Display3D`` opens a window, the following interactions are available:

* The viewer takes control of the Python interpreter for the duration of the
  window — place ``Display3D`` as the last call in a script, or any code after
  it will not execute until the viewer is closed.
* **Rotate** — drag with the left mouse button.
* **Zoom in / out** — drag up/down with the right mouse button.
* **Pan** — drag with the left mouse button while holding ``SHIFT``.
