Wave Optics — Three Domains, and Why KrakenOS Needs All Three
=============================================================

.. admonition:: Status
   :class: warning

   **Proposal, 2026-09-29. Nothing on this page is implemented.** The governing
   design document is ``docs/design_wave_domains.md``. Everything KrakenOS
   actually does today in the wave regime is listed in
   :ref:`wave-what-exists-today` — and it is more than most readers expect, but
   it is not a field propagator.

KrakenOS is a ray tracer. It answers "where does the light go" exactly, through
tilted and decentred 3D geometry, real glass, non-sequential splitting, and
imported vendor CAD. It does not answer "what does the light look like when a
wave has to squeeze past an edge".

This page explains why that second question cannot be answered by bolting a
diffraction formula onto a ray tracer, what the three separate computational
domains are, and the order in which the gap can honestly be closed.

.. contents::
   :local:
   :depth: 2


.. _wave-what-exists-today:

1. What already exists, and what each piece declares about itself
------------------------------------------------------------------

Four wave-adjacent capabilities ship today. Each is genuinely useful and each is
explicit about its own scope — which is why a fifth partial implementation would
not help.

.. list-table::
   :header-rows: 1
   :widths: 24 26 50

   * - capability
     - module
     - the scope it declares
   * - Diffraction PSF / MTF
     - ``KrakenOS/PSFCalc.py``
     - Real-ray optical path differences at a best-fit exit pupil, Zernike
       fitted, then a Fraunhofer FFT. Textbook, GPU-accelerated — and there is
       no propagation anywhere in it.
   * - Coherent detector
     - ``UI/coherent_detector_analysis.py``
     - Each traced ray carries total optical path plus splitter and coating
       phase, with Jones :math:`p`/:math:`s` components. The detector bins
       complex amplitude and sums coherently. Real interference — from rays,
       not from a field.
   * - Angular spectrum
     - same module
     - Declares itself as *"Fraunhofer angular-spectrum FFT of coherent
       detector field"*. The far field of the detector plane, computed at the
       end of the trace.
   * - Grid field
     - ``KrakenOS/BranchField.py``
     - A complex field on a rectangular grid with Fresnel transfer-function
       propagation and TEM\ :sub:`00` mode overlap. Raises for anything but
       ``model='paraxial'``.

Gaussian optics is the strongest of the existing wave capabilities:
``KrakenOS/GaussianBeam.py`` propagates the complex beam parameter

.. math::

   \frac{1}{q(z)} = \frac{1}{R(z)} - i\,\frac{\lambda}{\pi n\, w(z)^2}

through generally astigmatic systems, per non-sequential branch, and solves the
self-consistent cavity eigenmode of a round-trip :math:`ABCD` matrix — including
reporting honestly when a cavity is unstable.

**The instructive case is the interferometer.** In
``Examples/Examp_Michelson_Interferometer.py`` the optical path difference and
the branch phases are real traced quantities. The fringe *carrier*, however, is a
user-supplied tilt multiplied in analytically:

.. math::

   I(x,y) = P_1 + P_2 + 2\sqrt{P_1 P_2}\,
            \cos\!\left(\phi_0 + \frac{2\pi}{\lambda}
            \left(\theta_x x + \theta_y y\right)\right)

The docstring calls this a *first-order* interferogram, correctly. The pattern is
right for the right reason at the centre and cannot be right at an edge, because
nothing in it knows what an edge is.

So what is missing is not a formula. It is a **domain in which a field can
propagate**, and a contract for getting into and out of it.


2. The three domains
---------------------

The propagators are not the hard part — five mature engines already exist in the
wider Python optics ecosystem, covering the space between them. The hard part is
that they fall into three groups with genuinely different capabilities, and no
group is a superset of another.

.. list-table::
   :header-rows: 1
   :widths: 14 24 31 31

   * -
     - **G — rays**
     - **B — beamlets**
     - **F — grid fields**
   * - geometry
     - arbitrary 3D frames
     - arbitrary 3D frames
     - **planes normal to** :math:`z` **only**
   * - carries phase
     - optical path only
     - yes, per beamlet
     - yes, everywhere
   * - real surfaces
     - yes — glass, TIR, coatings, CAD
     - yes
     - no — ideal thin phase screens
   * - diffraction
     - none
     - by mode summation
     - exact scalar
   * - weak at
     - anything wave
     - hard edges, deep caustics
     - tilted or folded geometry
   * - partial coherence
     - ray grouping only
     - open research question
     - full mutual coherence function

The routing between them is the design:

.. code-block:: text

   G ──seed a hexagonal beamlet grid──▶ B ──evaluate E-field on a plane──▶ F
   G ──Zernike pupil + amplitude map───────────────────────────────────────▶ F
   F ──decompose by position / by angle──▶ B ──▶ G

**Domain B is load-bearing**, and this is the least obvious conclusion on the
page. It is the only domain with both three-dimensional generality *and* phase.
A beamlet is a ray carrying a complex beam parameter :math:`q`, a polarization
state and an amplitude; it traces through a prism cascade exactly as a ray does,
and a coherent summation of many beamlets reconstructs a field. Every tilted or
folded question therefore routes through B — so the beamlet engine matters more
to KrakenOS than the differentiable Fourier-optics engine does, which is the
reverse of what the package descriptions suggest.

KrakenOS is already half-way into Domain B without having planned to be:
``GaussianBeam.propagate_branch_gaussian_q`` and ``BranchGaussianQTrace`` already
carry complex :math:`q` per branch through a non-sequential scene. A beamlet is a
ray plus :math:`q`.


3. The invariant
-----------------

.. admonition:: The one invariant
   :class: important

   A field never exists without a frame, a unit, and a sampling verdict.

There is no unverified field in the system. A field that cannot state its verdict
is **refused**, not returned.

This is the standing KrakenOS rule that a refused solve must alert rather than
silently pick a remedy, applied to diffraction — and diffraction needs it more
than geometry does. A ray trace that goes wrong usually looks wrong: rays vanish,
or land somewhere absurd. An under-sampled diffraction calculation produces a
clean, plausible, symmetric fringe pattern that is simply false. It looks more
authoritative than the correct answer, because aliasing is orderly.

A sampling verdict therefore travels with every field, and carries at minimum the
Fresnel number

.. math::

   N_F = \frac{D^2}{\lambda z}

the Nyquist margin on the quadratic propagation phase, the guard-band ratio, and
the critical propagation distance below which an angular-spectrum method is the
correct choice,

.. math::

   z_c = \frac{2\,|x_\mathrm{max}|\,\Delta}{\lambda}

after Voelz, *Computational Fourier Optics* (2011), Eq. A.17.


4. Two numbers that shape the plan
-----------------------------------

**The interesting physics is not compute-bound.** For a 25 mm aperture at
0.6328 µm observed 100 mm downstream:

.. list-table::
   :header-rows: 1
   :widths: 12 16 18 20 18

   * - grid
     - :math:`\Delta`
     - :math:`z_c`
     - samples / edge fringe
     - field size
   * - 512²
     - 48.83 µm
     - 1929 mm
     - 5.2
     - 4.2 MB
   * - 1024²
     - 24.41 µm
     - 965 mm
     - 10.3
     - 16.8 MB
   * - 2048²
     - 12.21 µm
     - 482 mm
     - 20.6
     - 67.1 MB
   * - 4096²
     - 6.10 µm
     - 241 mm
     - 41.2
     - 268.4 MB

Here :math:`N_F \approx 9877` — deep near field — and the edge-fringe scale
:math:`\sqrt{\lambda z} \approx 252` µm. A 2048² grid gives twenty samples per
fringe in 67 MB. Nothing about this is expensive.

Note the trap in the third column: **refining the grid lowers** :math:`z_c`. A
user who "improves" the sampling can silently cross from an angular-spectrum
regime into a direct-integration one. A guard that reported only grid size would
call 4096² unambiguously better than 512². This is why the verdict must carry
:math:`z_c` itself, not a resolution.

**Partial coherence, by contrast, is permanently coarse.** A mutual coherence
function on an :math:`H \times W` grid is a :math:`(H, W, H, W)` array:

.. list-table::
   :header-rows: 1
   :widths: 30 30

   * - grid
     - complex128 size
   * - 32²
     - 0.017 GB
   * - 64²
     - 0.268 GB
   * - 128²
     - 4.295 GB
   * - 256²
     - 68.7 GB

64² is the working size and 128² is the practical ceiling on a desktop. 256² is
not a resolution choice, it is a different machine. The consequence is a physics
conclusion forced by arithmetic: **the general partial-coherence answer has to
come from beamlet mutual coherence in Domain B**, not from refining Domain F. It
is worth knowing that before spending a week discovering it.


5. The stages
--------------

Seven stages. Stages 1–3 depend on nothing else in the codebase and can begin
immediately; Stages 4 onward require the Scene IR to produce genuinely post-fold
world poses, because a wave engine cannot be handed a leg whose position is a
straight-equivalent rather than a location.

.. list-table::
   :header-rows: 1
   :widths: 6 26 44 24

   * - #
     - stage
     - gate — what must be measured
     - depends on
   * - 1
     - The roster exists
     - All engines import; silent install failures made loud; a validator
       refuses to degrade to NumPy quietly.
     - nothing
   * - 2
     - Known-answer battery
     - Airy pattern, knife edge, Poisson's spot, Ronchi self-imaging — each
       against an external reference, on each engine, plus a cross-engine
       agreement matrix.
     - stage 1
   * - 3
     - The sampling guard
     - Refuses every configuration stage 2 showed to be under-sampled; passes
       every one it showed to be sound.
     - stage 2
   * - 4
     - Units and frames contract
     - Leg-chain optical path equals the traced total optical path to
       < 1 µm, on the real benches.
     - Scene IR post-fold
   * - 5
     - Rays → field, one straight leg
     - Propagated PSF matches the Fraunhofer PSF in the aberration-free limit;
       an obstruction produces fringes; two engines agree.
     - stages 3, 4
   * - 6
     - Beamlets — folded and tilted
     - A 45° fold plus prism scene where the beamlet field matches stage 5's
       field on the equivalent unfolded leg.
     - stage 5
   * - 7
     - The named gaps
     - Per gap; see below.
     - stage 6

Two sequencing decisions are worth stating explicitly, because both are
counter-intuitive.

**The guard is built from measured breakage, not designed in advance.** Stage 2
comes first, each case is deliberately pushed until it fails, and only then is
the verdict written that would have caught it. A guard tuned to its author's
intuition ends up asserting a comment; one tuned to observed failure is an
instrument.

**Stage 6 can kill Domain B, and nothing in stage 7 should be attempted before
it.** Whether a beamlet decomposition survives a prism cascade is the genuine
open physics question of this design. Stage 6's gate exists to answer it, not to
confirm it.

Stage 7's contents, in value order, each independent of the others:

.. list-table::
   :header-rows: 1
   :widths: 30 44 26

   * - gap
     - route
     - replaces
   * - Real multilayer coatings
     - Transfer-matrix thin films: angle- and wavelength-resolved
       :math:`R`, :math:`T` **with phase**.
     - reflectance / transmittance metadata
   * - Resonator transverse modes
     - Fox–Li iteration with a saturable gain sheet and a real aperture.
     - :math:`ABCD` eigenmode, which gives only :math:`w` and stability
   * - Partial coherence
     - Coarse-grid mutual coherence for illumination; beamlet coherence for
       the general case.
     - coherence as a ray-grouping policy
   * - Stray light and ghosts
     - Polarized BRDF models driving the existing non-sequential trace.
     - nothing — this is new
   * - Tilted-plane propagation
     - Rotated angular spectrum, **only if** stage 6 shows beamlets cannot
       handle tilted refracting faces.
     - may never be needed


6. What this plan deliberately does not do
-------------------------------------------

Stating the exclusions is half the design, because each is a plausible-sounding
piece of work that would cost months and deliver little.

**It does not write a propagator.** Mature, independently validated propagators
already exist for every case identified here. A new one would be the least
valuable work available, and the hardest to trust.

**It does not unify the engines' scene models.** Each engine keeps its own. One
scene of record — KrakenOS — with adapters outward. Several scene models is a
perfectly sound state of affairs provided exactly one of them is authoritative.

**It does not touch the user interface migration.** The Tk → Qt work is
orthogonal and separately expensive; ``docs/design_qt_migration.md`` owns it.

**It does not attempt rigorous diffraction.** Rigorous coupled-wave analysis and
FDTD address sub-wavelength structure — diffractive optical elements,
metasurfaces — which nothing in the current requirement set needs. This is a
revisit-when-asked item, not an omission.

**It does not change the sequential trace's mathematics.** The ray engine is
correct and stays as it is. The wave domains sit beside it, not underneath it.


7. Where this leaves the honest answer to "is KrakenOS a wave-optics tracer?"
------------------------------------------------------------------------------

Today: **no, and it says so.** It is a ray tracer with genuine wave *analysis*
layered on top — diffraction PSF and MTF from a real-ray wavefront, coherent
interference summed from real optical paths, Gaussian beams and cavity stability.
Those are the right answers to real questions, and they are all first-order or
end-of-trace.

After stage 5: diffraction from apertures and obstructions along a straight leg,
with a sampling verdict attached — a genuine near-field answer, bounded by the
fidelity of a ray-derived seed.

After stage 6: the same for folded and tilted geometry, which is where every
interesting KrakenOS bench actually lives.

"Full physics" in the unqualified sense is not on this roadmap and should be
treated with suspicion wherever it is claimed. What is on the roadmap is a system
that knows which domain can answer a given question, hands the question over
under a checked contract, and refuses when no domain can answer it honestly.
