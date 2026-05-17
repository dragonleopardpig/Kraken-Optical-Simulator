Classes and Attributes
======================

This page is a faithful conversion of Section 2 of the provisional manual
(``KrakenOS/Docs/USER_MANUAL_KrakenOS_Provisional.pdf``, pages 4–10). For a
UI-focused summary that maps these fields onto the current Layout Editor, see
:doc:`core_model`.

The library has been simplified to the extent of having only two classes of
objects for the definition of a system. These objects are ``surf`` and
``system``; their application is described in :ref:`tbl-surf-class` and
:ref:`tbl-system-class`.

The ``surf`` object contains all the relevant information of any optical
interface. Every optical interface — from the object plane to the image plane —
is an instance of ``surf`` and carries attributes for size, shape, material, or
orientation.

Section 2 of the source PDF contains no figures; it is composed entirely of the
two reference tables below.

.. _tbl-surf-class:

Table 1 — ``surf`` class attributes
-----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Attribute
     - Description
   * - ``surf.Name = ""``
     - Name of the element. Useful only for 2D diagram or ray identification.
   * - ``surf.NamePos = (0, 0)``
     - Position of the note with the name ``Name`` in the 2D diagram. Default
       value: ``(0, 0)``.
   * - ``surf.Note = "None"``
     - Useful for adding user notes to a surface. Default value: ``None``.
   * - ``surf.Rc = 9999999999.0``
     - Paraxial radius of curvature in millimeters. Default value
       ``9999999999.0`` or ``0.0`` — both are interpreted as a plane.
   * - ``surf.Cylinder_Rxy_Ratio = 1``
     - Ratio between the axial and sagittal radius of curvature. Useful for
       cylindrical and toroidal lenses. Default value: ``1``.
   * - ``surf.Axicon = 0``
     - Axicon simulation. For values other than zero an axicon is generated
       with the angle entered. Default value: ``0``.
   * - ``surf.Thickness = 0.0``
     - Distance between this surface and the next surface. Default value:
       ``0.0``. Units: mm.
   * - ``surf.Diameter = 1.0``
     - Outside diameter of the surface. Default value: ``1.0``. Units: mm.
   * - ``surf.InDiameter = 0.0``
     - Internal diameter of the surface. Useful for items such as a
       central-aperture primary mirror. Default value: ``0.0``. Units: mm.
   * - ``surf.k = 0.0``
     - Conic constant for classical conic surfaces (``k = 0`` for spherical,
       ``k = -1`` for parabola, etc.). Default value: ``0.0``.
   * - | ``surf.DespX = 0.0``
       | ``surf.DespY = 0.0``
       | ``surf.DespZ = 0.0``
     - Displacement of the surface in the X, Y and Z axes (in millimeters).
       Default values: ``0.0``.
   * - | ``surf.TiltX = 0.0``
       | ``surf.TiltY = 0.0``
       | ``surf.TiltZ = 0.0``
     - Rotation of the surface in the X, Y and Z axes (in degrees). Default
       values: ``0.0``.
   * - ``surf.Order = 0``
     - Defines the order of the transformations. If the value is ``0``,
       translations are performed first and then rotations. If the value is
       ``1`` then rotations are performed first and then translations. Default
       value: ``0``.
   * - ``surf.AxisMove = 1``
     - Defines what will happen to the optical axis after a coordinate
       transformation. If the value is ``0``, the transformation is only carried
       out to the surface in question. If the value is ``1`` then the
       transformation also affects the optical axis, so the other surfaces will
       follow the transformation. If the value is different — for example
       ``2`` — then the optical axis will be affected twice. This is useful for
       flat mirrors (see *Example - Flat Mirror 45 Deg*). Default value: ``1``.
   * - ``surf.Diff_Ord = 0.0``
     - Diffraction order. Converts the element into a diffraction grating. The
       radius-of-curvature value is automatically omitted to make it a planar
       diffraction grating. This option can be used in transmission or
       refraction. Default value: ``0.0``.
   * - ``surf.Grating_D = 0.0``
     - Separation between the lines of the diffraction grating. Default value:
       ``0.0``. Units: µm.
   * - ``surf.Grating_Angle = 0.0``
     - Angle of the grating lines in the plane of the surface — i.e., around
       the optical axis. Useful for simulating conic dispersion. Default value:
       ``0.0``. Units: degrees.
   * - ``surf.ZNK = np.zeros(36)``
     - NumPy array of 36 elements corresponding to the coefficients of the
       Zernike polynomials in the Noll nomenclature (Ref. 2).
   * - | ``surf.ShiftX = 0``
       | ``surf.ShiftY = 0``
     - Offset of the surface profile on the X or Y axis. Useful, for example,
       for off-axis surfaces such as parabolas. Default value: ``0``. Units: mm.
   * - ``surf.Mask = 0``
     - Type of mask to apply. The different values are: ``0`` — do not apply a
       mask; ``1`` — use mask as opening; ``2`` — use mask as obstruction.
       Default value: ``0``.
   * - ``surf.Mask_Shape = Object_3D``
     - Form of the mask to apply, built with the PyVista (``pv``) library. See
       PyVista (Ref. 1) and the example in the appendix (7.20).
   * - ``surf.AspherData = np.zeros(Fix)``
     - Array of coefficients for an aspherical surface. The array is a NumPy
       list.
   * - ``surf.ExtraData = [f, coef]``
     - User-created surface with a sagitta function dependent on ``(x, y, V)``,
       where ``V`` can contain an array of coefficients usable by the function.
       The sagitta function and coefficient list are defined and then assigned
       to the surface — see the example below.
   * - ``surf.Error_map = [X, Y, Z, SPACE]``
     - Receives an error map generated with NumPy arrays for the coordinates in
       X, Y and the height in Z, plus a spacing value between samples. See
       *Example - Tel 2M Error Map* in the appendix.
   * - ``surf.Drawing = 1``
     - ``1`` for the element to be drawn in the 3D plot, ``0`` to omit drawing
       of the element.
   * - ``surf.Color = [0, 0, 0]``
     - Defines the color of the element in the format ``[1, 1, 1]`` — RGB color
       percentages (red, green, blue). Default value ``(0, 0, 0)`` is black.
       Other colors are red ``(1, 0, 0)``, green ``(0, 1, 0)``, and blue
       ``(0, 0, 1)``.
   * - ``surf.Solid_3d_stl = "None"``
     - Path of the 3D solid object in STL format.

The ``surf.ExtraData`` sagitta function and coefficient list are constructed
as follows:

.. code-block:: python

   def f(x, y, E):
       DeltaX = E[0] * np.rint(x / E[0])
       DeltaY = E[0] * np.rint(y / E[0])
       x = x - DeltaX
       y = y - DeltaY
       s = np.sqrt((x * x) + (y * y))
       c = 1.0 / E[1]
       InRoot = 1 - (E[2] + 1.0) * c * c * s * s
       z = (c * s * s / (1.0 + np.sqrt(InRoot)))
       return z

   # Coefficients are defined, if necessary, in a list:
   Coef = [3.0, -3, 0]

   # The shape of the function is assigned to the surface:
   L1c.ExtraData = [f, Coef]

.. _tbl-system-class:

Table 2 — ``system`` class implementations and attributes
---------------------------------------------------------

The ``system`` object is intended as a container for all interfaces. It exposes
implementations for ray tracing and for obtaining different parameters of the
ray, which are cumulative across the surfaces through which the ray passes. The
example in Appendix 7.11 walks through how these are called.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Implementation / attribute
     - Description
   * - ``system.Trace(pS, dC, wV)``
     - ``Trace`` is the main implementation of the ``system`` object; it traces
       a ray sequentially through all surfaces it finds in its path. The ray
       must be defined by a point of origin ``pS``, the direction cosines
       ``dC``, and the wavelength ``wV``. For example::

           pS = [1.0, 0.0, 0.0]
           dC = [0.0, 0.0, 1.0]
           wV = 0.4
   * - ``system.NsTrace(pS, dC, wV)``
     - Like ``Trace``, but non-sequentially. The ray parameters are defined in
       the same way as in ``Trace``.
   * - ``Prx = system.Parax(w)``
     - Returns the following paraxial calculations (also accessible from
       ``system``), arranged in a list::

           Prx = SistemMatrix, S_Matrix, N_Matrix, a, b, c, d, EFFL, PPA, PPP, CC, N_Prec, DD
   * - | ``system.disable_inner``
       | ``system.enable_inner``
     - Enables and disables the central openings. Very useful, for example, to
       calculate a ray trace without vignetting at the aperture of a primary
       mirror.
   * - ``system.SURFACE``
     - Returns a list of the number of surfaces the ray passed through.
   * - ``system.NAME``
     - Returns a list of the names of the surfaces the ray passed through. If
       no name is given to the surfaces, the list will contain empty fields.
       Naming surfaces is useful, for example, to identify whether a ray has
       struck a given surface.
   * - ``system.GLASS``
     - Returns a list of the materials the ray has pierced.
   * - ``system.XYZ``
     - Returns the ``[X, Y, Z]`` coordinates of the ray from its origin to the
       image plane.
   * - ``system.S_XYZ``
     - Returns the ``[X, Y, Z]`` coordinates of the ray from its origin and on
       all surfaces where this ray originates — i.e., the coordinates of the
       image plane are exempt.
   * - ``system.T_XYZ``
     - Returns the ``[X, Y, Z]`` coordinates of the ray from the first surface
       where it intersects to the image plane.
   * - ``system.OST_XYZ``
     - Returns the ``[X, Y, Z]`` coordinates at which a ray intercepts the
       surface in interface space — i.e., the coordinates with respect to a
       coordinate system at its vertex even if this vertex has a translation or
       rotation.
   * - ``system.DISTANCE``
     - Returns a list with the distances traveled by the ray between
       intersection points.
   * - ``system.OP``
     - Returns a list with the optical paths traveled by the ray between
       intersection points; the dispersion of the glass and the distance
       between intersection points are considered.
   * - ``system.TOP``
     - Returns a single value with the total optical path of the ray from the
       source to the last point of intersection.
   * - ``system.TOP_S``
     - Returns a cumulative list with values of the ray's optical path from the
       source to the last intersection point.
   * - ``system.ALPHA``
     - Returns a list with the absorption coefficients for the materials on the
       intercepted surfaces, considering the wavelength. These values are
       obtained from the originally provided material catalog.
   * - ``system.BULK_TRANS``
     - Returns a list with the transmission through all the paths within the
       system; the optical paths and the absorption coefficients of the
       materials are considered.
   * - ``system.S_LMN``
     - Returns a list with the direction cosines ``[L, M, N]`` of the normal at
       the intersection points of a ray, through all the interfaces through
       which it passes.
   * - ``system.LMN``
     - Returns a list with the direction cosines ``[L, M, N]`` of an incident
       ray, through all the interfaces through which it passes.
   * - ``system.R_LMN``
     - Returns a list with the direction cosines ``[L, M, N]`` of the resulting
       ray, through all the interfaces through which it passes.
   * - ``system.N0``
     - Refractive indices before and after each interface through which the ray
       passes. This index is calculated with the dispersion of the material and
       the wavelength of the ray in question.
   * - ``system.N1``
     - Refractive indices after each interface through which the ray passes.
       This index is calculated with the dispersion of the material and the
       wavelength of the ray in question. The difference with ``system.N0`` is
       that the list starts from the second refractive index, which is useful to
       differentiate between the medium-index list before and after an
       iteration. For example::

           N0 = [n1, n2, n3, n4, n5]
           N1 = [n2, n3, n4, n5, n5]

       So if we want to know the direction of a ray at the first interface, we
       use ``N0[0]`` and ``N1[0]``.
   * - ``system.WAV``
     - Wavelength of the ray in question. Although this command returns a list
       of all the values, they are the same because the wavelength is constant
       for a ray; the size of the list indicates only the number of iterations
       with system interfaces. Units: µm.
   * - ``system.G_LMN``
     - Returns a list with the terms ``L``, ``M`` or ``N`` of the direction
       cosines that define the lines of the diffraction grating on the plane.
   * - ``system.ORDER``
     - Returns a list with the diffraction orders associated with the ray in
       question.
   * - ``system.GRATING_D``
     - Distance between lines of the diffraction grating. Units: µm.
   * - | ``system.RP``
       | ``system.RS``
       | ``system.TP``
       | ``system.TS``
     - Returns a list with the Fresnel reflection and transmission coefficients
       for polarization S and P.
   * - ``system.TTBE``
     - Total energy transmitted or reflected per element.
   * - ``system.TT``
     - Total energy transmitted or reflected total.
   * - ``system.targ_surf(int)``
     - Limits the ray tracing to the defined surface; the argument is an
       integer equal to the surface number. If the value is zero (the default)
       the ray tracing is carried out to the last surface.
   * - ``system.flat_surf(int)``
     - Defined with the integer number of the surface that needs to be made
       flat. The value ``-1`` is used to restore the surface to its original
       shape.
