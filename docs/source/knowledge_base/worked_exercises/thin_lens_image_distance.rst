Worked Example: Image Distance of a Thin Lens
==============================================

This introductory example demonstrates the solution format using the Gaussian
thin-lens equation.  It is self-contained and is not copied from a textbook.

Problem in our own words
------------------------

An object is :math:`300\ \mathrm{mm}` in front of a converging thin lens whose
focal length is :math:`100\ \mathrm{mm}`.  Find the image distance and state
whether the image is real or virtual.

What is known
-------------

We use the real-is-positive convention for this example.  A converging lens
has positive focal length, and a real object placed in front of the lens has
positive object distance:

.. math::

   f = +100\ \mathrm{mm}, \qquad
   d_o = +300\ \mathrm{mm}, \qquad
   d_i = \;?

All distances already use millimetres, so no unit conversion is needed.

Step 1: Choose the model
------------------------

For a thin lens in air, the object distance :math:`d_o`, image distance
:math:`d_i`, and focal length :math:`f` obey

.. math::
   :label: thin-lens-equation

   \frac{1}{f} = \frac{1}{d_o} + \frac{1}{d_i}.

We assume paraxial rays and neglect the physical thickness of the lens.

Step 2: Rearrange the equation
------------------------------

We need :math:`d_i`, so first move the object-distance term to the left:

.. math::

   \frac{1}{d_i} = \frac{1}{f} - \frac{1}{d_o}.

Put the right-hand side over a common denominator:

.. math::

   \frac{1}{d_i}
   = \frac{d_o}{f d_o} - \frac{f}{f d_o}
   = \frac{d_o-f}{f d_o}.

Take the reciprocal of both sides:

.. math::
   :label: solved-image-distance

   d_i = \frac{f d_o}{d_o-f}.

Step 3: Substitute and calculate
--------------------------------

Insert the known values into Equation :eq:`solved-image-distance`:

.. math::

   \begin{aligned}
   d_i
   &= \frac{(100\ \mathrm{mm})(300\ \mathrm{mm})}
            {300\ \mathrm{mm}-100\ \mathrm{mm}} \\
   &= \frac{30\,000\ \mathrm{mm^2}}{200\ \mathrm{mm}} \\
   &= 150\ \mathrm{mm}.
   \end{aligned}

One power of millimetres cancels, leaving the required unit of length.

Step 4: Interpret the result
----------------------------

The image distance is positive.  Under our convention, this means the rays
meet on the far side of the lens and form a **real image**.  The image is
:math:`150\ \mathrm{mm}` behind the lens.

Check 1: Substitute back
------------------------

Substitute :math:`d_i=150\ \mathrm{mm}` into Equation
:eq:`thin-lens-equation`:

.. math::

   \frac{1}{300\ \mathrm{mm}} + \frac{1}{150\ \mathrm{mm}}
   = \frac{1+2}{300\ \mathrm{mm}}
   = \frac{1}{100\ \mathrm{mm}}
   = \frac{1}{f}.

The two sides agree.

Check 2: Estimate physically
----------------------------

The object is at :math:`3f`.  A real object beyond :math:`2f` should produce
a real image between :math:`f` and :math:`2f`.  Our result satisfies

.. math::

   100\ \mathrm{mm} < 150\ \mathrm{mm} < 200\ \mathrm{mm},

so its position is physically reasonable.

Final answer
------------

.. math::

   \boxed{d_i = +150\ \mathrm{mm}}

The image is real and forms :math:`150\ \mathrm{mm}` behind the lens.

Try it yourself
---------------

Repeat the calculation with the same lens and
:math:`d_o=150\ \mathrm{mm}`.  Before calculating, predict whether the image
will be closer to or farther from the lens than the object.  Then use Equation
:eq:`solved-image-distance` and verify your result by substitution.
