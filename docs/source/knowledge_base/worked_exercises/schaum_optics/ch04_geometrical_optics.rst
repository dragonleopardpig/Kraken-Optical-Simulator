Chapter 4: Geometrical Optics
=============================

Source: Eugene Hecht, *Schaum's Outline of Theory and Problems of
Optics* (1975), Chapter 4.  The entries below cover only the
chapter's **Supplementary Problems**; prompts are paraphrased and are not
reproduced.

Each topic derives its shared formula once.  Every numbered problem then
applies that derivation to the particular proof, calculation, or construction
in the book.  Read the source diagram alongside entries that depend on a figure.

Aspherical refracting surfaces
------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-4-1

   n_1\sqrt{(x-s_o)^2+y^2}+n_2\sqrt{(x-s_i)^2+y^2}=\text{constant}

Fermat's principle requires the optical path from the object
wavefront to the image point to be independent of aperture coordinate.  Write
both Euclidean distances, multiply by their indices, evaluate the constant at
the vertex, and square only after isolating one radical.  Completing the
square identifies the conic and its eccentricity.

Problem 4.62 — derive the Cartesian-ovoid equation in vertex coordinates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the cartesian-ovoid equation in vertex coordinates.

**Formula reference.** Use :eq:`schaum-4-1` and the definitions immediately above it.

**Worked application.**

1. Use the sign of the object or image distance shown in the source figure, eliminate the radicals systematically, and compare the final coefficients with the standard conic form.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Equating the indexed object-to-surface and surface-to-image distances to their axial value gives the Cartesian-ovoid relation in :math:`x,y,s_o,s_i,n_1,n_2`; setting :math:`y=0` recovers the vertex constant.

**Check.** At y=0 the surface passes through the vertex; the conic type must switch consistently when the image changes between real and virtual.

Problem 4.63 — prove that a plane-wave focusing surface is an ellipsoid
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove that a plane-wave focusing surface is an ellipsoid.

**Formula reference.** Use :eq:`schaum-4-1` and the definitions immediately above it.

**Worked application.**

1. Use the sign of the object or image distance shown in the source figure, eliminate the radicals systematically, and compare the final coefficients with the standard conic form.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For a plane incident wave, :math:`n_1x+n_2\sqrt{(s_i-x)^2+y^2}=n_2s_i`; isolating the radical and completing the square gives an ellipsoid when the focusing index ordering applies.

**Check.** At y=0 the surface passes through the vertex; the conic type must switch consistently when the image changes between real and virtual.

Problem 4.64 — prove that a plane-wave diverging surface is a hyperboloid
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove that a plane-wave diverging surface is a hyperboloid.

**Formula reference.** Use :eq:`schaum-4-1` and the definitions immediately above it.

**Worked application.**

1. Use the sign of the object or image distance shown in the source figure, eliminate the radicals systematically, and compare the final coefficients with the standard conic form.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Changing the image to a virtual divergence point changes the signed-distance term; the same squared equation now has opposite transverse and axial signs, the standard two-sheet hyperboloid.

**Check.** At y=0 the surface passes through the vertex; the conic type must switch consistently when the image changes between real and virtual.

Spherical refracting surfaces
-----------------------------

**Formula and definitions.**

.. math::
   :label: schaum-4-2

   \frac{n_1}{s_o}+\frac{n_2}{s_i}=\frac{n_2-n_1}{R},\qquad M_T=\frac{n_1s_i}{n_2s_o}

Adopt the Cartesian sign convention printed in the chapter:
real incident objects have positive :math:`s_o`, and the sign of :math:`R`
follows the center of curvature.  Solve the surface equation before applying
magnification.  A point at the center of curvature is undeviated.

Problem 4.65 — locate a flaw imaged through a hemispherical diamond end
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Locate a flaw imaged through a hemispherical diamond end.

**Formula reference.** Use :eq:`schaum-4-2` and the definitions immediately above it.

**Worked application.**

1. Insert n1, n2, object distance, and signed R for the encountered surface; for a sphere, propagate the first image as the object for the second surface.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`s_i=-20\,\mathrm{cm}`: the center-of-curvature point is imaged onto itself.

**Check.** Trace the axial chief ray: the sign of the computed image distance must agree with whether rays truly converge or only appear to diverge.

Problem 4.66 — place a source for a spherical-plus-hyperboloidal glass rod
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Place a source for a spherical-plus-hyperboloidal glass rod.

**Formula reference.** Use :eq:`schaum-4-2` and the definitions immediately above it.

**Worked application.**

1. Insert n1, n2, object distance, and signed R for the encountered surface; for a sphere, propagate the first image as the object for the second surface.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Place the source :math:`10\,\mathrm{cm}` to the left of the spherical end.

**Check.** Trace the axial chief ray: the sign of the computed image distance must agree with whether rays truly converge or only appear to diverge.

Problem 4.67 — image an ant through a glass sphere in alcohol
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Image an ant through a glass sphere in alcohol.

**Formula reference.** Use :eq:`schaum-4-2` and the definitions immediately above it.

**Worked application.**

1. Insert n1, n2, object distance, and signed R for the encountered surface; for a sphere, propagate the first image as the object for the second surface.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`s_i\approx-2.32\,\mathrm{cm}`, a virtual image on the object side of the first vertex.

**Check.** Trace the axial chief ray: the sign of the computed image distance must agree with whether rays truly converge or only appear to diverge.

Problem 4.68 — infer the radius of a convex refracting interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer the radius of a convex refracting interface.

**Formula reference.** Use :eq:`schaum-4-2` and the definitions immediately above it.

**Worked application.**

1. Insert n1, n2, object distance, and signed R for the encountered surface; for a sphere, propagate the first image as the object for the second surface.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`R=+20\,\mathrm{cm}`.

**Check.** Trace the axial chief ray: the sign of the computed image distance must agree with whether rays truly converge or only appear to diverge.

Thin-lens equation and imagery
------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-4-3

   \frac1f=(n-1)\left(\frac1{R_1}-\frac1{R_2}\right),\qquad \frac1{s_o}+\frac1{s_i}=\frac1f,\qquad M_T=-\frac{s_i}{s_o}

Use the lensmaker equation only to obtain :math:`f`; use the
Gaussian thin-lens equation for conjugates.  Combine
:math:`s_i=-M_Ts_o` with either :math:`s_o+s_i=L` or the specified separation
to remove one unknown.  The two Bessel locations arise from the quadratic in
:math:`s_o`.

Problem 4.69 — relate an unequal biconvex lens radius to focal length
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Relate an unequal biconvex lens radius to focal length.

**Formula reference.** Use :eq:`schaum-4-3` and the definitions immediately above it.

**Worked application.**

1. Translate the physical description into signed so, si, and M first; solve symbolically, then select the root whose ray geometry matches the requested real or virtual image.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For the smaller radius magnitude, :math:`R=3f/4`.

**Check.** The product of the two Bessel roots and the magnification sign give quick algebra and orientation checks; a real projected image must have positive image distance.

Problem 4.70 — derive the two Bessel positions of a lens between object and screen
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the two bessel positions of a lens between object and screen.

**Formula reference.** Use :eq:`schaum-4-3` and the definitions immediately above it.

**Worked application.**

1. Translate the physical description into signed so, si, and M first; solve symbolically, then select the root whose ray geometry matches the requested real or virtual image.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`s_{o,\pm}=[L\pm\sqrt{L(L-4f)}]/2`, requiring :math:`L\ge4f`.

**Check.** The product of the two Bessel roots and the magnification sign give quick algebra and orientation checks; a real projected image must have positive image distance.

Problem 4.71 — find the radii of an equiconvex flint lens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find the radii of an equiconvex flint lens.

**Formula reference.** Use :eq:`schaum-4-3` and the definitions immediately above it.

**Worked application.**

1. Translate the physical description into signed so, si, and M first; solve symbolically, then select the root whose ray geometry matches the requested real or virtual image.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`R_1=+80.6\,\mathrm{cm}` and :math:`R_2=-80.6\,\mathrm{cm}`.

**Check.** The product of the two Bessel roots and the magnification sign give quick algebra and orientation checks; a real projected image must have positive image distance.

Problem 4.72 — image a converging bundle through a negative lens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Image a converging bundle through a negative lens.

**Formula reference.** Use :eq:`schaum-4-3` and the definitions immediately above it.

**Worked application.**

1. Translate the physical description into signed so, si, and M first; solve symbolically, then select the root whose ray geometry matches the requested real or virtual image.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The converging incident bundle represents a virtual object.  With :math:`|s_o|<|f|`, the negative lens forms a real, erect, magnified image with :math:`s_i>|s_o|` in magnitude.

**Check.** The product of the two Bessel roots and the magnification sign give quick algebra and orientation checks; a real projected image must have positive image distance.

Problem 4.73 — design a slide-projector conjugate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Design a slide-projector conjugate.

**Formula reference.** Use :eq:`schaum-4-3` and the definitions immediately above it.

**Worked application.**

1. Translate the physical description into signed so, si, and M first; solve symbolically, then select the root whose ray geometry matches the requested real or virtual image.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`s_o=0.100\,\mathrm m`, :math:`M_T=-100`, and :math:`f\approx0.0990\,\mathrm m`.

**Check.** The product of the two Bessel roots and the magnification sign give quick algebra and orientation checks; a real projected image must have positive image distance.

Problem 4.74 — find a lens making an erect enlarged image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find a lens making an erect enlarged image.

**Formula reference.** Use :eq:`schaum-4-3` and the definitions immediately above it.

**Worked application.**

1. Translate the physical description into signed so, si, and M first; solve symbolically, then select the root whose ray geometry matches the requested real or virtual image.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`s_i=-144\,\mathrm{cm}` and :math:`f=240\,\mathrm{cm}`.

**Check.** The product of the two Bessel roots and the magnification sign give quick algebra and orientation checks; a real projected image must have positive image distance.

Problem 4.75 — solve camera object and film distances
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Solve camera object and film distances.

**Formula reference.** Use :eq:`schaum-4-3` and the definitions immediately above it.

**Worked application.**

1. Translate the physical description into signed so, si, and M first; solve symbolically, then select the root whose ray geometry matches the requested real or virtual image.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`s_o\approx2.04\,\mathrm m` and :math:`s_i\approx51.3\,\mathrm{mm}`.

**Check.** The product of the two Bessel roots and the magnification sign give quick algebra and orientation checks; a real projected image must have positive image distance.

Problem 4.76 — derive an object-image separation identity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive an object-image separation identity.

**Formula reference.** Use :eq:`schaum-4-3` and the definitions immediately above it.

**Worked application.**

1. Translate the physical description into signed so, si, and M first; solve symbolically, then select the root whose ray geometry matches the requested real or virtual image.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Eliminating :math:`s_o` and :math:`s_i` between the lens and magnification equations gives the stated separation-to-focal-length identity; its quadratic discriminant also reproduces the :math:`L\ge4f` condition.

**Check.** The product of the two Bessel roots and the magnification sign give quick algebra and orientation checks; a real projected image must have positive image distance.

Compound thin lenses
--------------------

**Formula and definitions.**

.. math::
   :label: schaum-4-4

   \Phi=\Phi_1+\Phi_2-d\Phi_1\Phi_2,\qquad f=\frac1\Phi,\qquad \Phi_{\rm contact}=\sum_j\frac1{f_j}

For separated lenses either multiply paraxial matrices or image
sequentially.  In sequential form, the first image position supplies the
second object distance with the separation and sign handled explicitly.  In
matrix form, the equivalent power is :math:`-C`.

Problem 4.77 — obtain front and back focal lengths of a telephoto pair
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Obtain front and back focal lengths of a telephoto pair.

**Formula reference.** Use :eq:`schaum-4-4` and the definitions immediately above it.

**Worked application.**

1. Combine powers for contact lenses; for separated elements, retain the intermediate image and propagate it to the next surface before applying the lens equation again.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Matrix reduction gives the front and back focal locations from the two principal planes; keep the 10-cm separation in the matrix rather than adding the lens powers as though they were in contact.

**Check.** In the d→0 limit the separated-pair power must reduce to the sum of powers; an afocal combination has zero net C and infinite effective focal length.

Problem 4.78 — combine three lenses in contact and locate an image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Combine three lenses in contact and locate an image.

**Formula reference.** Use :eq:`schaum-4-4` and the definitions immediately above it.

**Worked application.**

1. Combine powers for contact lenses; for separated elements, retain the intermediate image and propagate it to the next surface before applying the lens equation again.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The contact combination has :math:`f=8\,\mathrm{cm}` and forms its image :math:`16\,\mathrm{cm}` beyond the lens.

**Check.** In the d→0 limit the separated-pair power must reduce to the sum of powers; an afocal combination has zero net C and infinite effective focal length.

Problem 4.79 — split a known contact-lens power in a two-to-one ratio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Split a known contact-lens power in a two-to-one ratio.

**Formula reference.** Use :eq:`schaum-4-4` and the definitions immediately above it.

**Worked application.**

1. Combine powers for contact lenses; for separated elements, retain the intermediate image and propagate it to the next surface before applying the lens equation again.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The component focal lengths are 45 cm and 90 cm.

**Check.** In the d→0 limit the separated-pair power must reduce to the sum of powers; an afocal combination has zero net C and infinite effective focal length.

Problem 4.80 — propagate an image through two separated lenses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Propagate an image through two separated lenses.

**Formula reference.** Use :eq:`schaum-4-4` and the definitions immediately above it.

**Worked application.**

1. Combine powers for contact lenses; for separated elements, retain the intermediate image and propagate it to the next surface before applying the lens equation again.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The final image is :math:`90\,\mathrm{cm}` to the right of the negative lens.

**Check.** In the d→0 limit the separated-pair power must reduce to the sum of powers; an afocal combination has zero net C and infinite effective focal length.

Thick lenses
------------

**Formula and definitions.**

.. math::
   :label: schaum-4-5

   M=R_2\,T(d)\,R_1=\begin{bmatrix}A&B\\C&D\end{bmatrix},\qquad f=-\frac1C,\qquad h_1=\frac{D-1}{C},\qquad h_2=\frac{1-A}{C}

Represent refraction by reduced-angle matrices and the internal
thickness by translation in the lens index.  Multiply in encounter order
(rightmost matrix first), then read the effective focal length and principal
plane offsets from :math:`A,C,D`.  Image from the principal planes, not from
the vertices.

Problem 4.81 — analyze an equal-negative-radius index-two thick lens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Analyze an equal-negative-radius index-two thick lens.

**Formula reference.** Use :eq:`schaum-4-5` and the definitions immediately above it.

**Worked application.**

1. Build both refraction matrices with signed radii, insert the in-glass translation, multiply, and use the resulting principal planes in the Gaussian conjugate equation.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For the index-two equal-negative-radius lens, matrix reduction gives a positive focal length proportional to :math:`R^2/d` and coincident principal-plane offsets :math:`h_1=h_2=-R` in the source convention.

**Check.** The determinant is unity in reduced coordinates; letting thickness tend to zero must recover the thin lensmaker equation.

Problem 4.82 — locate principal and focal points of a thick biconvex lens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Locate principal and focal points of a thick biconvex lens.

**Formula reference.** Use :eq:`schaum-4-5` and the definitions immediately above it.

**Worked application.**

1. Build both refraction matrices with signed radii, insert the in-glass translation, multiply, and use the resulting principal planes in the Gaussian conjugate equation.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`f=3\,\mathrm{cm}`, with principal-plane offsets :math:`h_1=+0.5\,\mathrm{cm}` and :math:`h_2=-1.0\,\mathrm{cm}` in the chapter convention.

**Check.** The determinant is unity in reduced coordinates; letting thickness tend to zero must recover the thin lensmaker equation.

Problem 4.83 — image through a hemispherical thick lens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Image through a hemispherical thick lens.

**Formula reference.** Use :eq:`schaum-4-5` and the definitions immediately above it.

**Worked application.**

1. Build both refraction matrices with signed radii, insert the in-glass translation, multiply, and use the resulting principal planes in the Gaussian conjugate equation.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`f=12\,\mathrm{cm}`, :math:`h_1=0`, :math:`h_2=-6\,\mathrm{cm}`, and the real image is 18 cm to the right of the second principal plane.

**Check.** The determinant is unity in reduced coordinates; letting thickness tend to zero must recover the thin lensmaker equation.

Problem 4.84 — analyze a common-center thick lens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Analyze a common-center thick lens.

**Formula reference.** Use :eq:`schaum-4-5` and the definitions immediately above it.

**Worked application.**

1. Build both refraction matrices with signed radii, insert the in-glass translation, multiply, and use the resulting principal planes in the Gaussian conjugate equation.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The common-center construction is a negative lens with :math:`f=-2|R|(|R|+d)/d`; both principal planes coincide with the shared center of curvature.

**Check.** The determinant is unity in reduced coordinates; letting thickness tend to zero must recover the thin lensmaker equation.

Problem 4.85 — image with a spherical benzene droplet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Image with a spherical benzene droplet.

**Formula reference.** Use :eq:`schaum-4-5` and the definitions immediately above it.

**Worked application.**

1. Build both refraction matrices with signed radii, insert the in-glass translation, multiply, and use the resulting principal planes in the Gaussian conjugate equation.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`f\approx3.00\,\mathrm{mm}` and the real image is about 38.2 mm from the sphere center, with :math:`M_T\approx-0.06`.

**Check.** The determinant is unity in reduced coordinates; letting thickness tend to zero must recover the thin lensmaker equation.

Lens combinations
-----------------

**Formula and definitions.**

.. math::
   :label: schaum-4-6

   M=M_N\cdots M_2M_1,\qquad f=-\frac1C,\qquad \text{afocal}\Longleftrightarrow C=0

Translate each focal length to a lens power and each spacing to
a translation matrix.  Multiplying the complete train exposes its cardinal
points.  A collimated input has zero reduced angle change only when the system
element :math:`C` vanishes.

Problem 4.86 — locate the first focal plane of a Huygens ocular
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Locate the first focal plane of a huygens ocular.

**Formula reference.** Use :eq:`schaum-4-6` and the definitions immediately above it.

**Worked application.**

1. Form the full system matrix including every air gap; solve either C=0 for an afocal design or the input/output conjugate condition for the requested object plane.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The first focal plane is halfway between the lenses, :math:`f_1/2` to the left of the eye lens.

**Check.** Trace one parallel paraxial ray: it must leave parallel in an afocal system and cross the stated focal plane otherwise.

Problem 4.87 — place an object for a two-lens image on a screen
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Place an object for a two-lens image on a screen.

**Formula reference.** Use :eq:`schaum-4-6` and the definitions immediately above it.

**Worked application.**

1. Form the full system matrix including every air gap; solve either C=0 for an afocal design or the input/output conjugate condition for the requested object plane.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The object is 50 cm left of the first lens.

**Check.** Trace one parallel paraxial ray: it must leave parallel in an afocal system and cross the stated focal plane otherwise.

Problem 4.88 — choose the third focal length of an afocal triplet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Choose the third focal length of an afocal triplet.

**Formula reference.** Use :eq:`schaum-4-6` and the definitions immediately above it.

**Worked application.**

1. Form the full system matrix including every air gap; solve either C=0 for an afocal design or the input/output conjugate condition for the requested object plane.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Afocality requires :math:`f_3\approx+3.0\,\mathrm{cm}`.

**Check.** Trace one parallel paraxial ray: it must leave parallel in an afocal system and cross the stated focal plane otherwise.

Problem 4.89 — locate the object plane of a Ramsden ocular
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Locate the object plane of a ramsden ocular.

**Formula reference.** Use :eq:`schaum-4-6` and the definitions immediately above it.

**Worked application.**

1. Form the full system matrix including every air gap; solve either C=0 for an afocal design or the input/output conjugate condition for the requested object plane.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The Ramsden object plane lies one effective focal length :math:`3f_1/4` in front of the ocular.

**Check.** Trace one parallel paraxial ray: it must leave parallel in an afocal system and cross the stated focal plane otherwise.

Problem 4.90 — verify an afocal positive-negative lens prescription
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Verify an afocal positive-negative lens prescription.

**Formula reference.** Use :eq:`schaum-4-6` and the definitions immediately above it.

**Worked application.**

1. Form the full system matrix including every air gap; solve either C=0 for an afocal design or the input/output conjugate condition for the requested object plane.
2. Evaluate both sides independently from the definitions and confirm equality without circular substitution.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The net power is zero, so the combination is afocal.

**Check.** Trace one parallel paraxial ray: it must leave parallel in an afocal system and cross the stated focal plane otherwise.

Planar, aspherical, and spherical mirrors
-----------------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-4-7

   \frac1{s_o}+\frac1{s_i}=\frac1f=\frac2R,\qquad M_T=-\frac{s_i}{s_o}

Reflection is reciprocal: exchanging a real object and real
image leaves the mirror equation unchanged.  For a virtual object use the
signed negative :math:`s_o` specified by the converging incident bundle.
Magnification fixes orientation and height after the conjugates are known.

Problem 4.91 — exchange object and image locations for a concave mirror
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Exchange object and image locations for a concave mirror.

**Formula reference.** Use :eq:`schaum-4-7` and the definitions immediately above it.

**Worked application.**

1. Propagate to the mirror vertex, assign the object sign from the incident-ray convergence, solve the mirror equation, and use -si/so for size and orientation.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The mirror has :math:`f=100\,\mathrm{cm}`; exchanging conjugates puts the object 150 cm from the vertex.

**Check.** A convex mirror illuminated by a real object normally gives a virtual, erect, reduced image; reciprocal real conjugates must interchange exactly.

Problem 4.92 — combine a compound lens with a convex mirror
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Combine a compound lens with a convex mirror.

**Formula reference.** Use :eq:`schaum-4-7` and the definitions immediately above it.

**Worked application.**

1. Propagate to the mirror vertex, assign the object sign from the incident-ray convergence, solve the mirror equation, and use -si/so for size and orientation.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Sequential imaging through the compound lens and back from the convex mirror gives :math:`s_i=-10\,\mathrm{cm}` at the mirror: a virtual inverted image 10 cm behind its vertex.

**Check.** A convex mirror illuminated by a real object normally gives a virtual, erect, reduced image; reciprocal real conjugates must interchange exactly.

Problem 4.93 — image a converging cone incident on a convex mirror
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Image a converging cone incident on a convex mirror.

**Formula reference.** Use :eq:`schaum-4-7` and the definitions immediately above it.

**Worked application.**

1. Propagate to the mirror vertex, assign the object sign from the incident-ray convergence, solve the mirror equation, and use -si/so for size and orientation.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The image is real, erect, magnified, and farther from the mirror than the virtual object.

**Check.** A convex mirror illuminated by a real object normally gives a virtual, erect, reduced image; reciprocal real conjugates must interchange exactly.

Problem 4.94 — describe a close object in a concave mirror
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Describe a close object in a concave mirror.

**Formula reference.** Use :eq:`schaum-4-7` and the definitions immediately above it.

**Worked application.**

1. Propagate to the mirror vertex, assign the object sign from the incident-ray convergence, solve the mirror equation, and use -si/so for size and orientation.
2. Use signs, directions, and limiting behavior from the governing equations to classify the physical result.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`s_i=6\,\mathrm{cm}`, :math:`M_T=-1/2`, giving a 0.5-cm inverted real image.

**Check.** A convex mirror illuminated by a real object normally gives a virtual, erect, reduced image; reciprocal real conjugates must interchange exactly.

Problem 4.95 — describe an object in a long-focus convex mirror
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Describe an object in a long-focus convex mirror.

**Formula reference.** Use :eq:`schaum-4-7` and the definitions immediately above it.

**Worked application.**

1. Propagate to the mirror vertex, assign the object sign from the incident-ray convergence, solve the mirror equation, and use -si/so for size and orientation.
2. Use signs, directions, and limiting behavior from the governing equations to classify the physical result.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`s_i=-133.3\,\mathrm{cm}`, :math:`M_T=+2/3`, giving a virtual erect reduced image.

**Check.** A convex mirror illuminated by a real object normally gives a virtual, erect, reduced image; reciprocal real conjugates must interchange exactly.

Problem 4.96 — describe a second convex-mirror image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Describe a second convex-mirror image.

**Formula reference.** Use :eq:`schaum-4-7` and the definitions immediately above it.

**Worked application.**

1. Propagate to the mirror vertex, assign the object sign from the incident-ray convergence, solve the mirror equation, and use -si/so for size and orientation.
2. Use signs, directions, and limiting behavior from the governing equations to classify the physical result.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`s_i=-36\,\mathrm{cm}`, :math:`M_T=+1/5`, giving a 0.6-cm virtual erect image.

**Check.** A convex mirror illuminated by a real object normally gives a virtual, erect, reduced image; reciprocal real conjugates must interchange exactly.
