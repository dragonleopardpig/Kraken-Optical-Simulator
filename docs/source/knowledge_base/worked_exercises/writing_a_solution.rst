How to Write a Worked Solution
==============================

Use this page as a checklist when we solve a new exercise together.  Do not
try to perform every calculation mentally.  Writing down the intermediate
steps makes mistakes easier to find and turns one answer into a method that
can be reused.

1. Identify the exercise
------------------------

Record enough information to find the original question again:

* book title and author;
* edition;
* chapter or section;
* exercise number.

Then paraphrase the question in one or two sentences.  State exactly what
must be found.

2. Draw and choose conventions
------------------------------

Draw a small diagram when the problem has geometry, rays, forces, or vectors.
Declare the sign convention before substituting numbers.  For example, a
thin-lens calculation might use positive distances for a real object and a
real image.

3. List knowns and unknowns
---------------------------

Write every supplied value with its symbol and unit.  A compact list might
look like this:

.. math::

   f = 100\ \mathrm{mm}, \qquad
   d_o = 300\ \mathrm{mm}, \qquad
   d_i = \;?

Use one system of units before calculating.  Do not silently combine metres,
millimetres, degrees, and radians.

4. Select the governing equation
--------------------------------

Write the equation in symbols first.  Explain briefly why it applies and list
any assumptions.  For a thin lens in air, for example,

.. math::

   \frac{1}{f} = \frac{1}{d_o} + \frac{1}{d_i}.

This model assumes a paraxial ray and a lens whose thickness can be neglected.

5. Rearrange before substituting
--------------------------------

Solve algebraically for the unknown before inserting numbers.  This keeps the
logic readable and reduces arithmetic errors:

.. math::

   \frac{1}{d_i}
   = \frac{1}{f} - \frac{1}{d_o}
   = \frac{d_o-f}{f d_o},

and therefore

.. math::

   d_i = \frac{f d_o}{d_o-f}.

6. Substitute values with units
-------------------------------

Show the numerical substitution, not only the result:

.. math::

   d_i
   = \frac{(100\ \mathrm{mm})(300\ \mathrm{mm})}
           {300\ \mathrm{mm}-100\ \mathrm{mm}}.

Keep more digits during the calculation than the final answer requires.

7. State and interpret the answer
---------------------------------

Put the final result on its own line and explain what its sign and size mean.
The statement ``the image is 150 mm behind the lens`` is more useful than the
number ``150`` by itself.

8. Check the result
-------------------

Use at least one independent check:

* substitute the answer into the original equation;
* check that dimensions and units agree;
* estimate the expected size or sign;
* solve by a second method or with a limiting case;
* compare with a KrakenOS paraxial calculation when appropriate.

Sphinx equation syntax
----------------------

Use the inline math role for a short expression such as ``:math:`f=100``,
which renders as :math:`f=100`.  Use a ``math`` directive for a displayed
equation:

.. code-block:: rst

   .. math::

      \frac{1}{f} = \frac{1}{d_o} + \frac{1}{d_i}

The blank line after ``.. math::`` and the indentation of the equation are
required.  Equation labels can be used when a later paragraph needs a precise
reference:

.. code-block:: rst

   .. math::
      :label: thin-lens-template

      \frac{1}{f} = \frac{1}{d_o} + \frac{1}{d_i}

   Equation :eq:`thin-lens-template` relates object and image distance.

Template for the next exercise
------------------------------

Copy these headings into a new ``.rst`` page and fill them in:

.. code-block:: rst

   Exercise title
   ==============

   Source
   ------

   Problem in our own words
   ------------------------

   What is known
   -------------

   Step 1: Choose the model
   ------------------------

   Step 2: Rearrange the equation
   --------------------------------

   Step 3: Substitute and calculate
   --------------------------------

   Step 4: Interpret the result
   ----------------------------

   Check
   -----

   Final answer
   ------------

Make each underline at least as long as its heading.  Add the new filename,
without the ``.rst`` suffix, to the ``toctree`` in this section's
``index.rst``.
