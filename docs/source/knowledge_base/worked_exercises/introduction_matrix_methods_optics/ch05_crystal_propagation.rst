Chapter V: Propagation of Light Through Crystals
================================================

Source: Gerrard and Burch, *Introduction to Matrix Methods in Optics* (1975),
Chapter V.

This chapter contains no numbered illustrative problems.  It applies matrix
notation to vector products, the dielectric tensor, plane waves in uniaxial
crystals, and Huygens wavelets.  The compact derivation below records the
chapter's central reusable result.

Plane-wave eigenproblem
-----------------------

For a nonmagnetic anisotropic dielectric, insert
:math:`\mathbf E=\mathbf E_0e^{i(\mathbf k\cdot\mathbf r-\omega t)}`
into Maxwell's equations.  Eliminating :math:`\mathbf H` gives

.. math::

   \mathbf k\times(\mathbf k\times\mathbf E_0)
   +\frac{\omega^2}{c^2}\boldsymbol\epsilon_r\mathbf E_0=0.

Writing the cross product as the antisymmetric matrix :math:`K(\mathbf k)`,
the allowed waves satisfy

.. math::

   \left[K(\mathbf k)^2+
   \frac{\omega^2}{c^2}\boldsymbol\epsilon_r\right]\mathbf E_0=0,
   \qquad
   \det\left[K^2+rac{\omega^2}{c^2}\boldsymbol\epsilon_r\right]=0.

For a uniaxial crystal with optic axis along :math:`z`,
:math:`\boldsymbol\epsilon_r=\operatorname{diag}(n_o^2,n_o^2,n_e^2)`.
The determinant separates into the ordinary sphere and extraordinary
ellipsoid.  The ordinary wave has :math:`n=n_o`; the extraordinary effective
index obeys

.. math::

   \boxed{\frac{1}{n_e(\theta)^2}
   =\frac{\cos^2\theta}{n_o^2}
   +\frac{\sin^2\theta}{n_e^2}},

with :math:`\theta` measured from the optic axis under this convention.

Check
~~~~~

Propagation along the optic axis makes the two indices equal to :math:`n_o`,
so there is no double refraction.  Perpendicular propagation recovers the
principal extraordinary value :math:`n_e`.
