Chapter I: Introduction to Matrix Calculations
==============================================

Source: Gerrard and Burch, *Introduction to Matrix Methods in Optics* (1975),
Chapter I.

The chapter develops multiplication, determinants, inversion,
diagonalization, eigenvalues, and eigenvectors through examples, but it has no
numbered illustrative-problem section.  The essential calculation used later
is summarized here so the chapter remains visible in the book sequence.

Unimodular two-by-two matrix
----------------------------

For

.. math::

   M=\begin{bmatrix}A&B\\C&D\end{bmatrix},
   \qquad AD-BC=1,

the characteristic polynomial is

.. math::

   \lambda^2-(A+D)\lambda+1=0.

Thus the eigenvalues occur as the reciprocal pair

.. math::

   \boxed{\lambda_\pm=
   \frac{A+D}{2}\pm
   \sqrt{\left(\frac{A+D}{2}\right)^2-1}},
   \qquad \lambda_+\lambda_-=1.

An eigenvector may be scaled to :math:`(q,1)^T`.  Substitution gives

.. math::

   Cq^2+(D-A)q-B=0,
   \qquad
   q=\frac{A-D\pm\sqrt{(A+D)^2-4}}{2C}.

The discriminant immediately separates elliptic, hyperbolic, and parabolic
matrix behavior.  This is the algebraic origin of the stable, unstable, and
marginal resonator classifications used in Chapter III.

Check
~~~~~

Substituting either root into the quadratic must give zero, and multiplying
the two eigenvalues must give the determinant, unity.  When :math:`M=I`, the
double eigenvalue is :math:`1`, as expected.
