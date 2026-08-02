Photonics Essentials: Chapter 5 Problems
========================================

Source
------

Thomas P. Pearsall, *Photonics Essentials: An Introduction with Experiments*
(McGraw-Hill, 2003), Chapter 5, ``Photoconductivity``, Problems 5.1--5.6,
printed page 100.

Worked solutions
----------------

Problem 5.1: Carriers from a laser pulse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The pulse energy is

.. math::

   E_{\mathrm{pulse}}=P\Delta t
   =(10^{-7})(10^{-9})=10^{-16}\ \mathrm J.

One :math:`600\ \mathrm{nm}` photon has energy

.. math::

   E_\gamma=\frac{hc}{\lambda}
   =3.31\times10^{-19}\ \mathrm J.

With complete absorption and one electron-hole pair per photon,

.. math::

   N=\frac{E_{\mathrm{pulse}}}{E_\gamma}
   =\boxed{3.02\times10^2\ \text{electron-hole pairs}}.

The stated :math:`1\ \mathrm{cm^2}` area affects the density, not this total.

Problem 5.2: Why photodiode gain cannot exceed one
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ideal energy sequence is

.. math::

   \text{valence electron}+\gamma
   \longrightarrow
   \text{one conduction electron}+\text{one hole}
   \longrightarrow
   \text{one collected electron charge}.

The depletion field separates and collects the pair, but it does not return
the same carrier to the absorber to circulate again.  Therefore one absorbed
photon supplies at most one elementary charge to the external circuit:

.. math::

   G_{\mathrm{photodiode}}
   =\frac{\text{collected electrons}}{\text{absorbed photons}}
   \leq\boxed{1}.

This statement excludes avalanche multiplication, which is a different
high-field gain mechanism.

Problem 5.3: Steady-state carrier concentration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The photon generation rate is

.. math::

   \dot N
   =\frac{P}{E_\gamma}
   =\frac{10^{-6}}{2(1.602\times10^{-19})}
   =3.12\times10^{12}\ \mathrm{s^{-1}}.

The illuminated volume is

.. math::

   \mathcal V=(1\ \mathrm{cm^2})(2\times10^{-4}\ \mathrm{cm})
   =2\times10^{-4}\ \mathrm{cm^3}.

At steady state, excess population equals generation rate times lifetime:

.. math::

   \Delta n=\Delta p
   =\frac{\dot N\tau}{\mathcal V}
   =\frac{(3.12\times10^{12})(10^{-6})}{2\times10^{-4}}
   =\boxed{1.56\times10^{10}\ \mathrm{cm^{-3}}}.

Problem 5.4: Photographic latent image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The three energy-diagram stages can be summarized as follows.

**Exposure.**  A photon excites an electron across the AgBr energy gap:

.. math::

   \mathrm{AgBr}+\gamma
   \longrightarrow e^-_{\mathrm{CB}}+h^+_{\mathrm{VB}}.

The mobile electron is trapped at a sensitization site.

**Latent-image formation.**  The negatively charged trap attracts a mobile
:math:`\mathrm{Ag^+}` ion and reduces it:

.. math::

   \mathrm{Ag^+}+e^-\longrightarrow\mathrm{Ag^0}.

Repeated events create a small cluster of neutral silver atoms.  This cluster
stores the invisible latent image.

**Development and fixing.**  Developer preferentially reduces an exposed
grain around its silver seed, amplifying the small cluster into an opaque
metallic-silver grain.  Fixer then dissolves the unexposed AgBr.  The remaining
silver distribution is the visible negative.

Problem 5.5: Hole lifetime after sensitization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

From Table 5.2,

.. math::

   N_{r1}=2\times10^{15},\quad
   N_{r2}=2\times10^{16}\ \mathrm{cm^{-3}},\quad
   v=10^7\ \mathrm{cm/s},

and :math:`s_{p1}=s_{p2}=10^{-15}\ \mathrm{cm^2}`.  Under the occupancy
approximations used in the example,
:math:`n_{r1}\approx N_{r1}` and :math:`n_{r2}\approx N_{r2}`.  Hence

.. math::

   \begin{aligned}
   \frac1{\tau_p}
   &=n_{r1}vs_{p1}+n_{r2}vs_{p2}\\
   &=(2\times10^{15})(10^7)(10^{-15})
    +(2\times10^{16})(10^7)(10^{-15})\\
   &=2.2\times10^8\ \mathrm{s^{-1}},
   \end{aligned}

so

.. math::

   \boxed{\tau_p=4.55\times10^{-9}\ \mathrm s\approx5\ \mathrm{ns}}.

Sensitization lengthens the electron lifetime but shortens the hole lifetime.

Problem 5.6: Reversed capture preference
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now :math:`s_{n2}=10^{-15}\ \mathrm{cm^2}` and
:math:`s_{p2}=10^{-17}\ \mathrm{cm^2}`.  The type-2 center captures
electrons efficiently but holes slowly, so the sensitization preference
reverses: holes become the long-lived carrier.

A useful limiting estimate keeps the example's available active type-2
population near :math:`N_{r1}`.  Then

.. math::

   \tau_p\sim\frac{1}{N_{r1}vs_{p2}}
   =\frac{1}{(2\times10^{15})(10^7)(10^{-17})}
   =\boxed{5\times10^{-6}\ \mathrm s},

whereas electron capture through the same active population gives

.. math::

   \tau_n\sim\frac{1}{N_{r1}vs_{n2}}
   =\boxed{5\times10^{-8}\ \mathrm s}.

These are order-of-magnitude lifetimes, not an exact trap-occupancy solution.
Direct substitution into the occupancy approximation used for Equations
5.18--5.23 predicts :math:`p_{r1}>N_{r1}`, which is impossible.  That signals
that the original high-illumination occupancy assumption no longer applies.
An exact pair of lifetimes would require the illumination level, charge
neutrality condition, and coupled rate equations, none of which the problem
specifies.
