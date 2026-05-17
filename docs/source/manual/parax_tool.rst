Parax Tool
==========

This page is a faithful conversion of Section 4 of the provisional manual
(``KrakenOS/Docs/USER_MANUAL_KrakenOS_Provisional.pdf``, pages 20–21).

``Parax`` is a method on the ``system`` class that returns the paraxial
quantities needed for matrix ray tracing, evaluated at a chosen wavelength.

.. code-block:: python

   Prx = Doublet.Parax(0.4)
   SistemMatrix, S_Matrix, N_Matrix, a, b, c, d, EFFL, PPA, PPP, C, N, D = Prx

The fields returned in ``Prx`` are:

Total system matrix
   ``SistemMatrix`` — the cascaded refraction/translation matrix for the whole
   system. For the doublet example:

   .. code-block:: text

      SistemMatrix = [[ 8.69329466e-01  -9.80840791e-03]
                      [ 1.00167690e+02   2.01470656e-02]]

Per-element surface matrices
   ``S_Matrix`` — a list of 2×2 matrices, alternating refraction and
   translation entries:

   .. code-block:: text

      S_Matrix = [matrix([[1., 0.], [ 0., 1.]]),
                  matrix([[1., 0.], [10., 1.]]),
                  matrix([[0.65323249, -0.00361793], [0., 1.]]),
                  matrix([[1., 0.], [ 6., 1.]]),
                  matrix([[0.92657697,  0.00239038], [0., 1.]]),
                  matrix([[1., 0.], [ 3., 1.]]),
                  matrix([[1.65215474, -0.00833986], [0., 1.]]),
                  matrix([[1., 0.], [97.37604743, 1.]]),
                  matrix([[1., 0.], [ 0., 1.]]),
                  matrix([[1., 0.], [ 0., 1.]])]

Matrix labels
   ``N_Matrix`` — human-readable labels for each entry in ``S_Matrix``:

   .. code-block:: text

      N_Matrix = ['R sup: 0', 'T sup: 0 to 1',
                  'R sup: 1', 'T sup: 1 to 2',
                  'R sup: 2', 'T sup: 2 to 3',
                  'R sup: 3', 'T sup: 3 to 4',
                  'R sup: 4', 'T sup: 4 to 5']

Total-matrix entries
   ``a``, ``b``, ``c``, ``d`` are the four entries of the cascaded matrix:

   .. code-block:: text

      a = 0.8693294662072478
      b = -0.009808407908592333
      c = 100.16768993870667
      d = 0.02014706564149671

Cardinal quantities
   * ``EFFL`` — effective focal length
   * ``PPA`` — principal anterior plane
   * ``PPP`` — principal posterior plane

   .. code-block:: text

      EFFL = 101.9533454684305
      PPA  = -99.89928472490783
      PPP  =  13.322298074316684

Per-surface arrays
   ``C`` — curvatures, ``N`` — refractive indices at each medium,
   ``D`` — surface separations:

   .. code-block:: text

      C = [1.00000000e-12, 1.04332892e-02, -3.25562791e-02, -1.27881671e-02, 1.00000000e-12]
      N = [1.0, 1.5308485382492993, 1.6521547400480732, 1.0, 1.0]
      D = [10., 6., 3., 97.37604743, 0.]
