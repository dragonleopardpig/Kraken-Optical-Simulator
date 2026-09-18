r"""Generate the Schaum optics supplementary-problem solution collection.

The source scan is not needed by Sphinx.  Problem statements below are short,
independently written topic descriptions; the generated pages contain the
derivations, formula references, applications, and answer checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from schaum_optics_worked import SOLUTIONS
from schaum_optics_worked.illustrations import PROBLEMS, TOPICS, figure_name


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT / "docs" / "source" / "knowledge_base" / "worked_exercises" / "schaum_optics"
)


@dataclass(frozen=True)
class Section:
    title: str
    first: int
    focuses: tuple[str, ...]
    equation: str
    derivation: str
    route: str
    check: str

    @property
    def last(self) -> int:
        return self.first + len(self.focuses) - 1


@dataclass(frozen=True)
class Chapter:
    number: int
    slug: str
    title: str
    sections: tuple[Section, ...]


def items(text: str) -> tuple[str, ...]:
    r"""Split a compact, one-entry-per-line problem inventory."""

    return tuple(line.strip() for line in text.strip().splitlines() if line.strip())


CHAPTERS = (
    Chapter(
        1,
        "wave_motion",
        "Wave Motion",
        (
            Section(
                "The wave equation",
                31,
                items(r"""
                test a squared-sine travelling profile
                distinguish progressive from non-progressive functions
                recover speed and direction from three profiles
                prove that an arbitrary profile moving toward negative x is progressive
                test a superposition of oppositely travelling profiles
                verify an arbitrary twice-differentiable travelling profile
                relate the temporal and spatial rates of change
                """),
                r"\frac{\partial^2 y}{\partial x^2}=\frac{1}{v^2}\frac{\partial^2 y}{\partial t^2},\qquad y=f(x-vt)+g(x+vt)",
                r"""Put :math:`u=x\mp vt`.  The chain rule gives
:math:`y_x=f'(u)`, :math:`y_{xx}=f''(u)`, :math:`y_t=\mp vf'(u)`, and
:math:`y_{tt}=v^2f''(u)`.  Substitution proves the differential equation.
A plus sign in :math:`x+vt` moves a fixed value of :math:`u` toward decreasing
:math:`x`; a minus sign moves it toward increasing :math:`x`.""",
                "Rewrite every term as a function of one travelling coordinate, differentiate twice, and compare coefficients before assigning the speed and sign.",
                "Both sides of the wave equation must contain the same second derivative; following a point of fixed phase must reproduce the stated direction.",
            ),
            Section(
                "Sinusoidal waves",
                38,
                items(r"""
                derive temporal periodicity of a harmonic wave
                convert radio frequency to wavelength and back
                prove the sine-to-cosine phase identity
                read speed, wavelength, and frequency from a wave
                evaluate a harmonic disturbance at a specified event
                plot a time trace with amplitude and phase
                translate a photographed profile after four seconds
                compare phase-locked readings at two detectors
                exploit integer position and period shifts
                test, sketch, and assign the speed of a candidate wave
                """),
                r"y=A\sin(kx\mp\omega t+\phi),\quad \lambda=\frac{2\pi}{k},\quad T=\frac{2\pi}{\omega},\quad v=\frac{\omega}{k}=f\lambda",
                r"""A repetition in time requires :math:`\omega T=2\pi m`; the
fundamental period uses :math:`m=1`.  Likewise a spatial repetition requires
:math:`k\lambda=2\pi`.  Holding the phase constant yields
:math:`dx/dt=\pm\omega/k`, which fixes the propagation direction.""",
                "Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.",
                "The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.",
            ),
            Section(
                "Phase and phase velocity",
                48,
                items(r"""
                infer initial phase from a negative field maximum
                infer phase when the spatial origin is a maximum
                describe phase evolution at a fixed observer
                describe phase variation across a snapshot
                find separations producing a sixty-degree phase offset
                count phase cycles and wave-train length
                construct a wave from measured phase gradients
                """),
                r"\Phi=kx-\omega t+\phi_0,\qquad \left.\frac{\partial\Phi}{\partial x}\right|_t=k,\qquad \left.\frac{\partial\Phi}{\partial t}\right|_x=-\omega,\qquad v_\phi=-\frac{\Phi_t}{\Phi_x}",
                r"""At a specified event use :math:`E/E_0=\sin\Phi` (or the
cosine convention printed in the problem) to select the phase modulo
:math:`2\pi`.  Between two events,
:math:`\Delta\Phi=k\Delta x-\omega\Delta t`; solve this linear relation for
the requested separation, elapsed time, or phase speed.""",
                "Write the complete phase first, retain the 2πm family when positions are not unique, and only then substitute the event data.",
                "Substitution into the original phase must recover the requested phase difference; equivalent answers can differ by an integer multiple of 2π.",
            ),
            Section(
                "Complex-number representation",
                55,
                items(r"""
                form complex conjugates
                extract real parts of phasors
                extract imaginary parts of phasors
                calculate phasor magnitudes
                square a real harmonic field without confusing it with intensity
                """),
                r"z=a+ib,\quad z^*=a-ib,\quad \Re z=\frac{z+z^*}{2},\quad \Im z=\frac{z-z^*}{2i},\quad |z|=(zz^*)^{1/2}",
                r"""Conjugation changes :math:`i` to :math:`-i` everywhere,
including exponential phases.  Euler's identity converts
:math:`Ae^{i\Phi}` to :math:`A(\cos\Phi+i\sin\Phi)`.  A physical squared
field is :math:`[\Re(Ae^{i\Phi})]^2=A^2\cos^2\Phi`, not merely the real part
of :math:`zz^*`.""",
                "Apply conjugation algebraically, simplify products before taking a square root, and distinguish a real instantaneous field from its complex representative.",
                "The magnitude is real and non-negative; conjugating twice returns the original quantity, and real/imaginary parts reconstruct z.",
            ),
            Section(
                "Three-dimensional waves",
                60,
                items(r"""
                verify an arbitrary three-dimensional plane-wave profile
                write a wave along the diagonal in the xy plane
                identify the constant-time phase gradient
                normalize a propagation-direction vector
                write a Cartesian plane wave through a specified direction point
                """),
                r"y(\mathbf r,t)=A\sin(\mathbf k\cdot\mathbf r-\omega t+\phi_0),\quad |\mathbf k|=\frac{2\pi}{\lambda},\quad \nabla\Phi=\mathbf k,\quad \omega=v|\mathbf k|",
                r"""Write :math:`\mathbf k=k\hat{\mathbf s}`, where the supplied
direction is normalized to unit length.  The chain rule gives
:math:`\nabla^2 f(\Phi)=k^2f''(\Phi)` and
:math:`\partial_t^2f(\Phi)=\omega^2f''(\Phi)`, proving the 3-D wave equation
when :math:`\omega=vk`.""",
                "Normalize the stated direction, form its dot product with (x,y,z), and insert k=2π/λ and ω=vk.",
                "The direction vector must have unit norm and every term in the phase must be dimensionless.",
            ),
        ),
    ),
    Chapter(
        2,
        "electromagnetic_waves_and_photons",
        "Electromagnetic Waves and Photons",
        (
            Section(
                "Maxwell equations and electromagnetic waves",
                26,
                items(r"""
                reconstruct E from a specified plane-wave B field
                reconstruct B from a graphed electric field
                reconstruct E from a graphed magnetic field
                determine a field from wavelength, direction, and irradiance
                """),
                r"\mathbf B=\frac{1}{v}\hat{\mathbf k}\times\mathbf E,\qquad \mathbf E=-v\hat{\mathbf k}\times\mathbf B,\qquad v=\frac{c}{n}",
                r"""For a transverse plane wave, :math:`\mathbf E`,
:math:`\mathbf B`, and :math:`\hat{\mathbf k}` form a right-handed orthogonal
triad.  Their amplitudes satisfy :math:`E_0=vB_0`; the phase and propagation
argument are common to both fields.""",
                "Read the propagation sign from the constant-phase condition, use the cross product for orientation, and scale the companion amplitude by v.",
                "Verify E·B=0, E×B points along propagation, and E0/B0=v.",
            ),
            Section(
                "Index of refraction",
                30,
                items(r"""
                compute propagation number in a dielectric
                infer path length from a transit-time difference
                compare wavelengths in diamond and zircon
                infer refractive index from dielectric constant
                """),
                r"v=\frac{c}{n},\qquad \lambda=\frac{\lambda_0}{n},\qquad k=\frac{2\pi n}{\lambda_0},\qquad \Delta t=\frac{L(n_2-n_1)}{c}",
                r"""Frequency is unchanged at a stationary interface, so reducing
the phase velocity by :math:`n` reduces wavelength by the same factor.  For a
nonmagnetic transparent material, :math:`n\simeq\sqrt{\epsilon_r}`.""",
                "Select the relation matching the requested propagation number, wavelength ratio, transit delay, or dielectric constant and solve symbolically before inserting units.",
                "The vacuum limit n=1 must give v=c and λ=λ0; the larger index must have the shorter wavelength and longer transit time.",
            ),
            Section(
                "Irradiance",
                34,
                items(r"""
                convert flux density and exposure time to energy
                obtain focused-laser irradiance and field amplitude
                derive the vacuum irradiance coefficient
                recover total power from a measured point-source field
                derive irradiance from a sinusoidal electric field
                """),
                r"I=\frac{P}{A},\qquad U=IAt,\qquad \langle S\rangle=I=\frac12 c\epsilon_0E_0^2,\qquad P_{\rm iso}=4\pi r^2I",
                r"""The instantaneous Poynting vector is
:math:`\mathbf S=\mathbf E\times\mathbf H`.  Since
:math:`\langle\sin^2\Phi\rangle=1/2` and :math:`H_0=E_0/Z_0`, its cycle
average becomes :math:`I=E_0^2/(2Z_0)=c\epsilon_0E_0^2/2`.""",
                "Convert area to square metres, use the cycle-averaged expression for harmonic fields, and integrate over time or sphere area only after finding I.",
                "Power has units W, exposure energy J, and electric-field amplitude V/m; inverse-square spreading must conserve 4πr²I.",
            ),
            Section(
                "Photon energy and momentum",
                39,
                items(r"""
                derive the photon-energy wavelength shortcut
                calculate solar radiation pressure for reflection
                find the photoelectric threshold wavelength
                find flashlight recoil thrust
                find laser force on a reflecting microsphere
                """),
                r"E_\gamma=h\nu=\frac{hc}{\lambda},\qquad p_\gamma=\frac{E_\gamma}{c}=\frac{h}{\lambda},\qquad p_{\rm rad}=\frac{I}{c}\ \text{(absorbed)},\ \frac{2I}{c}\ \text{(reflected)}",
                r"""A photon reverses momentum on perfect reflection, transferring
:math:`2p_\gamma`; absorption transfers :math:`p_\gamma`.  Multiplying the
per-photon transfer by photon rate :math:`P/E_\gamma` gives force
:math:`P/c` or :math:`2P/c`.""",
                "Use hc after converting wavelength to metres (or 1239 eV·nm consistently), and choose the absorption/reflection momentum factor explicitly.",
                "Photon energy and momentum are positive; perfect reflection must double the pressure obtained for perfect absorption.",
            ),
            Section(
                "Electromagnetic-photon spectrum",
                44,
                items(r"""
                classify and quantify the 21-cm hydrogen line
                characterize extremely long radio waves
                count photons carrying one erg at three wavelengths
                compare microwave and helium-neon photon energies
                """),
                r"\nu=\frac{c}{\lambda},\qquad T=\frac{1}{\nu}=\frac{\lambda}{c},\qquad E_\gamma=\frac{hc}{\lambda},\qquad N=\frac{E_{\rm total}}{E_\gamma}",
                r"""Classify the radiation from its wavelength or frequency, then
use the vacuum dispersion relation.  Photon count is total energy divided by
the single-photon energy; convert :math:`1\,\mathrm{erg}=10^{-7}\,\mathrm J`
before division.""",
                "Carry the wavelength conversion first, calculate ν or T, then use the same wavelength in hc/λ and divide total energy when a photon count is requested.",
                "Longer wavelengths have lower frequency and photon energy; N must be dimensionless and inversely proportional to photon energy.",
            ),
        ),
    ),
    Chapter(
        3,
        "reflection_and_transmission",
        "Reflection and Transmission",
        (
            Section(
                "Laws of reflection and refraction",
                31,
                items(r"""
                express parallel-plate beam displacement with Snell's law
                derive prism deviation from ray angles
                derive the deviation made by two mirrors
                find the mirror-angle condition for a retracing ray
                justify a graphical Snell-law construction
                """),
                r"n_i\sin\theta_i=n_t\sin\theta_t,\qquad \theta_r=\theta_i,\qquad a=d\,\frac{\sin(\theta_i-\theta_t)}{\cos\theta_t}",
                r"""Resolve every angle from the surface normal.  For a parallel
plate, apply Snell's law at each face and use the right triangle inside the
plate.  For a prism or mirror sequence, sum signed turns of the ray rather
than unsigned interior angles.""",
                "Label incident, reflected, and transmitted angles at each surface, apply Snell or reflection locally, then eliminate the intermediate angle geometrically.",
                "A parallel plate must return the emergent direction to the incident direction; setting equal indices must eliminate refraction and lateral displacement.",
            ),
            Section(
                "Fermat's principle",
                36,
                items(r"""
                prove focus-to-focus reflection by an ellipsoid
                derive Snell's law using an angular coordinate
                derive Snell's law from adjacent optical paths
                prove coplanarity at a reflecting interface
                """),
                r"\mathcal L=\sum_j n_j\ell_j,\qquad \delta\mathcal L=0,\qquad \frac{d\mathcal L}{dq}=0",
                r"""Write the optical path length through an arbitrary point on the
interface and differentiate with respect to its free coordinate.  The two
derivatives are direction cosines; stationarity therefore gives equal
tangential optical-wave-vector components, i.e. Snell's law or the reflection
law.  For an ellipse, the sum of focal distances is constant.""",
                "Choose the one independent displacement shown in the source diagram, differentiate every segment length by the chain rule, and set the first variation to zero.",
                "The stationary result must be unchanged by relabelling the two media and must reduce to equal angles when their indices are equal.",
            ),
            Section(
                "Fresnel equations",
                40,
                items(r"""
                calculate s-polarized Fresnel amplitudes at forty-five degrees
                remove explicit refractive indices from transmission amplitudes
                verify amplitude-coefficient identities
                prove energy conservation of reflectance and transmittance
                reverse normal-incidence illumination from air to glass
                solve normal-incidence reflectance/transmittance cases
                """),
                r"r_s=\frac{n_i\cos\theta_i-n_t\cos\theta_t}{n_i\cos\theta_i+n_t\cos\theta_t},\quad r_p=\frac{n_t\cos\theta_i-n_i\cos\theta_t}{n_t\cos\theta_i+n_i\cos\theta_t},\quad R=|r|^2,\quad T=\frac{n_t\cos\theta_t}{n_i\cos\theta_i}|t|^2",
                r"""Apply the tangential-field boundary conditions separately for
s and p polarization and use Snell's law to remove either index or angle.
Squaring amplitudes alone is insufficient for transmitted power: include the
normal admittance factor shown in :math:`T`.""",
                "Find θt from Snell's law, evaluate the appropriate amplitude pair, and convert to power coefficients only after the amplitudes are known.",
                "For lossless media R+T=1. At equal indices r=0 and t=1, while reversing the interface changes the reflection phase but conserves power.",
            ),
            Section(
                "Critical angle and total internal reflection",
                46,
                items(r"""
                combine two forty-five-degree critical interfaces
                find the minimum prism index for total internal reflection
                infer a block index from a critical internal ray
                compute Brewster incidence for a measured liquid
                derive the acceptance angle of a clad optical fiber
                """),
                r"\sin\theta_c=\frac{n_t}{n_i}\ (n_i>n_t),\qquad \tan\theta_B=\frac{n_t}{n_i},\qquad \mathrm{NA}=n_0\sin\theta_{\max}=\sqrt{n_{\rm core}^2-n_{\rm clad}^2}",
                r"""At critical incidence set the transmitted angle to
:math:`90^\circ`.  At Brewster incidence use
:math:`\theta_B+\theta_t=90^\circ` in Snell's law.  For a fiber, combine the
entrance-face Snell relation with the core-cladding critical condition and
eliminate the internal ray angle.""",
                "Use the geometry to identify the high-index side first; then apply the critical, Brewster, or numerical-aperture relation with all angles measured from their local normals.",
                "A critical angle exists only from higher to lower index; the fiber acceptance must vanish when core and cladding indices are equal.",
            ),
        ),
    ),
    Chapter(
        4,
        "geometrical_optics",
        "Geometrical Optics",
        (
            Section(
                "Aspherical refracting surfaces",
                62,
                items(r"""
                derive the Cartesian-ovoid equation in vertex coordinates
                prove that a plane-wave focusing surface is an ellipsoid
                prove that a plane-wave diverging surface is a hyperboloid
                """),
                r"n_1\sqrt{(x-s_o)^2+y^2}+n_2\sqrt{(x-s_i)^2+y^2}=\text{constant}",
                r"""Fermat's principle requires the optical path from the object
wavefront to the image point to be independent of aperture coordinate.  Write
both Euclidean distances, multiply by their indices, evaluate the constant at
the vertex, and square only after isolating one radical.  Completing the
square identifies the conic and its eccentricity.""",
                "Use the sign of the object or image distance shown in the source figure, eliminate the radicals systematically, and compare the final coefficients with the standard conic form.",
                "At y=0 the surface passes through the vertex; the conic type must switch consistently when the image changes between real and virtual.",
            ),
            Section(
                "Spherical refracting surfaces",
                65,
                items(r"""
                locate a flaw imaged through a hemispherical diamond end
                place a source for a spherical-plus-hyperboloidal glass rod
                image an ant through a glass sphere in alcohol
                infer the radius of a convex refracting interface
                """),
                r"\frac{n_1}{s_o}+\frac{n_2}{s_i}=\frac{n_2-n_1}{R},\qquad M_T=\frac{n_1s_i}{n_2s_o}",
                r"""Adopt the Cartesian sign convention printed in the chapter:
real incident objects have positive :math:`s_o`, and the sign of :math:`R`
follows the center of curvature.  Solve the surface equation before applying
magnification.  A point at the center of curvature is undeviated.""",
                "Insert n1, n2, object distance, and signed R for the encountered surface; for a sphere, propagate the first image as the object for the second surface.",
                "Trace the axial chief ray: the sign of the computed image distance must agree with whether rays truly converge or only appear to diverge.",
            ),
            Section(
                "Thin-lens equation and imagery",
                69,
                items(r"""
                relate an unequal biconvex lens radius to focal length
                derive the two Bessel positions of a lens between object and screen
                find the radii of an equiconvex flint lens
                image a converging bundle through a negative lens
                design a slide-projector conjugate
                find a lens making an erect enlarged image
                solve camera object and film distances
                derive an object-image separation identity
                """),
                r"\frac1f=(n-1)\left(\frac1{R_1}-\frac1{R_2}\right),\qquad \frac1{s_o}+\frac1{s_i}=\frac1f,\qquad M_T=-\frac{s_i}{s_o}",
                r"""Use the lensmaker equation only to obtain :math:`f`; use the
Gaussian thin-lens equation for conjugates.  Combine
:math:`s_i=-M_Ts_o` with either :math:`s_o+s_i=L` or the specified separation
to remove one unknown.  The two Bessel locations arise from the quadratic in
:math:`s_o`.""",
                "Translate the physical description into signed so, si, and M first; solve symbolically, then select the root whose ray geometry matches the requested real or virtual image.",
                "The product of the two Bessel roots and the magnification sign give quick algebra and orientation checks; a real projected image must have positive image distance.",
            ),
            Section(
                "Compound thin lenses",
                77,
                items(r"""
                obtain front and back focal lengths of a telephoto pair
                combine three lenses in contact and locate an image
                split a known contact-lens power in a two-to-one ratio
                propagate an image through two separated lenses
                """),
                r"\Phi=\Phi_1+\Phi_2-d\Phi_1\Phi_2,\qquad f=\frac1\Phi,\qquad \Phi_{\rm contact}=\sum_j\frac1{f_j}",
                r"""For separated lenses either multiply paraxial matrices or image
sequentially.  In sequential form, the first image position supplies the
second object distance with the separation and sign handled explicitly.  In
matrix form, the equivalent power is :math:`-C`.""",
                "Combine powers for contact lenses; for separated elements, retain the intermediate image and propagate it to the next surface before applying the lens equation again.",
                "In the d→0 limit the separated-pair power must reduce to the sum of powers; an afocal combination has zero net C and infinite effective focal length.",
            ),
            Section(
                "Thick lenses",
                81,
                items(r"""
                analyze an equal-negative-radius index-two thick lens
                locate principal and focal points of a thick biconvex lens
                image through a hemispherical thick lens
                analyze a common-center thick lens
                image with a spherical benzene droplet
                """),
                r"M=R_2\,T(d)\,R_1=\begin{bmatrix}A&B\\C&D\end{bmatrix},\qquad f=-\frac1C,\qquad h_1=\frac{D-1}{C},\qquad h_2=\frac{1-A}{C}",
                r"""Represent refraction by reduced-angle matrices and the internal
thickness by translation in the lens index.  Multiply in encounter order
(rightmost matrix first), then read the effective focal length and principal
plane offsets from :math:`A,C,D`.  Image from the principal planes, not from
the vertices.""",
                "Build both refraction matrices with signed radii, insert the in-glass translation, multiply, and use the resulting principal planes in the Gaussian conjugate equation.",
                "The determinant is unity in reduced coordinates; letting thickness tend to zero must recover the thin lensmaker equation.",
            ),
            Section(
                "Lens combinations",
                86,
                items(r"""
                locate the first focal plane of a Huygens ocular
                place an object for a two-lens image on a screen
                choose the third focal length of an afocal triplet
                locate the object plane of a Ramsden ocular
                verify an afocal positive-negative lens prescription
                """),
                r"M=M_N\cdots M_2M_1,\qquad f=-\frac1C,\qquad \text{afocal}\Longleftrightarrow C=0",
                r"""Translate each focal length to a lens power and each spacing to
a translation matrix.  Multiplying the complete train exposes its cardinal
points.  A collimated input has zero reduced angle change only when the system
element :math:`C` vanishes.""",
                "Form the full system matrix including every air gap; solve either C=0 for an afocal design or the input/output conjugate condition for the requested object plane.",
                "Trace one parallel paraxial ray: it must leave parallel in an afocal system and cross the stated focal plane otherwise.",
            ),
            Section(
                "Planar, aspherical, and spherical mirrors",
                91,
                items(r"""
                exchange object and image locations for a concave mirror
                combine a compound lens with a convex mirror
                image a converging cone incident on a convex mirror
                describe a close object in a concave mirror
                describe an object in a long-focus convex mirror
                describe a second convex-mirror image
                """),
                r"\frac1{s_o}+\frac1{s_i}=\frac1f=\frac2R,\qquad M_T=-\frac{s_i}{s_o}",
                r"""Reflection is reciprocal: exchanging a real object and real
image leaves the mirror equation unchanged.  For a virtual object use the
signed negative :math:`s_o` specified by the converging incident bundle.
Magnification fixes orientation and height after the conjugates are known.""",
                "Propagate to the mirror vertex, assign the object sign from the incident-ray convergence, solve the mirror equation, and use -si/so for size and orientation.",
                "A convex mirror illuminated by a real object normally gives a virtual, erect, reduced image; reciprocal real conjugates must interchange exactly.",
            ),
        ),
    ),
    Chapter(
        5,
        "polarization",
        "Polarization",
        (
            Section(
                "Plane polarization",
                48,
                items(r"""
                write a forty-five-degree linear wave travelling along y
                pass z-polarized light through a y-fast-axis quarter-wave plate
                write an xy-plane linear wave with zero initial field
                classify a signed two-component linear wave
                write a linear wave tilted 17.5 degrees above the xy plane
                """),
                r"\mathbf E=\Re\!\left\{\begin{bmatrix}E_{0x}\\E_{0y}e^{i\delta}\end{bmatrix}e^{i(kz-\omega t)}\right\},\qquad \tan\psi=\frac{E_{0y}}{E_{0x}}\quad(\delta=0\text{ or }\pi)",
                r"""Remove the common carrier and compare the two complex
components.  Equal or opposite phases make their ratio real and hence give a
fixed line.  Its quadrant comes from the component signs; orthogonality is
tested by the Jones inner product.""",
                "Express both components with a common phase, reduce their complex ratio, and obtain the physical azimuth with atan2 so the quadrant is retained.",
                "A normalized linear Jones vector has unit norm and zero ellipticity; orthogonal linear states have a zero inner product.",
            ),
            Section(
                "Circular polarization",
                53,
                items(r"""
                superpose two in-phase linear waves of unequal amplitude
                devise a test that distinguishes right- from left-circular light
                write a right-circular wave with a specified initial azimuth
                write a right-circular wave from a specified initial vector
                write a left-circular wave with a specified initial azimuth
                """),
                r"\mathbf e_R=\frac1{\sqrt2}\begin{bmatrix}1\\-i\end{bmatrix},\qquad \mathbf e_L=\frac1{\sqrt2}\begin{bmatrix}1\\i\end{bmatrix},\qquad \delta=\pm\frac\pi2",
                r"""Circular polarization requires equal component magnitudes and
quadrature phase.  Evaluate the real field at a fixed :math:`z` for increasing
:math:`t` to determine handedness under the book's viewing convention.  A
quarter-wave plate supplies the required :math:`\pm\pi/2` phase delay.""",
                "Normalize the component amplitudes, reduce the relative phase modulo 2π, and track the field rotation explicitly before naming the handedness.",
                "The field-tip magnitude must remain constant through a cycle; reversing propagation or viewing direction reverses the apparent handedness.",
            ),
            Section(
                "Elliptical polarization",
                58,
                items(r"""
                write a right-handed ellipse tilted to the y axis
                write a left-handed ellipse with major axis at 135 degrees
                classify an ellipse from two phase-shifted components
                write a right-handed two-to-one ellipse along x
                decompose an ellipse into linear and circular components
                """),
                r"\left(\frac{E_x}{E_{0x}}\right)^2+\left(\frac{E_y}{E_{0y}}\right)^2-2\frac{E_xE_y}{E_{0x}E_{0y}}\cos\delta=\sin^2\delta",
                r"""Write one component as :math:`E_{0x}\cos\tau` and the other as
:math:`E_{0y}\cos(\tau+\delta)`.  Expanding the latter and eliminating
:math:`\sin\tau` gives the quadratic ellipse.  Diagonalizing its symmetric
quadratic form gives principal axes and azimuth.""",
                "Eliminate the common phase, inspect equal-amplitude/quadrature special cases, and use the sign of temporal rotation for handedness.",
                "The determinant of the ellipse quadratic must be non-negative; δ=0 or π collapses it to a line and equal quadrature components make a circle.",
            ),
            Section(
                "Natural and partially polarized light",
                63,
                items(r"""
                decide whether a perfectly monochromatic wave must be polarized
                distinguish partially linear from partially elliptical light
                distinguish natural, circular, and mixed light experimentally
                recover polarization degree from two analyzer readings
                """),
                r"\mathcal P=\frac{I_{\max}-I_{\min}}{I_{\max}+I_{\min}}=\frac{I_p}{I_p+I_u},\qquad I(\theta)=\frac{I_u}{2}+I_p\cos^2\theta",
                r"""An ideal analyzer transmits half of the unpolarized component
and the Malus-law projection of the polarized component.  Evaluating at
parallel and crossed orientations gives :math:`I_{\max}` and
:math:`I_{\min}`; their sum and difference isolate :math:`I_u` and
:math:`I_p`.""",
                "Write the analyzer curve, evaluate its maximum and minimum, and solve the resulting two linear equations for the requested degree or component irradiances.",
                "The degree of polarization must lie between zero and one; a fully natural beam has equal analyzer extrema and a pure linear beam has a zero minimum.",
            ),
            Section(
                "Dichroism and Polaroid",
                67,
                items(r"""
                write the field transmitted from natural light by one polarizer
                compare Malus transmission at thirty and sixty degrees
                propagate irradiance through three specified polarizers
                propagate irradiance through ten forty-five-degree stages
                compare four-polarizer transmission with crossed endpoints
                explain extinction for a reordered three-polarizer stack
                """),
                r"I_1=\frac{I_{\rm unpol}}2,\qquad I_N=I_1\prod_{j=2}^{N}\cos^2(\theta_j-\theta_{j-1})",
                r"""The first ideal polarizer transmits half of natural incident
light.  Every later plate receives a linearly polarized beam, so apply Malus's
law using the angle relative to the immediately preceding transmission axis,
not the first axis.""",
                "Order the polarizers physically, take every consecutive angular difference, and multiply the corresponding cos² factors without prematurely comparing only the endpoints.",
                "Removing intermediate plates must recover direct Malus-law transmission; crossed adjacent axes force the product to zero.",
            ),
            Section(
                "Polarization by reflection",
                73,
                items(r"""
                infer glass index from a measured Brewster angle
                calculate external Brewster and transmitted angles
                derive Malus variation from two reflecting plates
                calculate reflected and transmitted degrees of polarization
                compare internal and external Brewster angles
                """),
                r"\tan\theta_B=\frac{n_t}{n_i},\qquad \theta_B+\theta_t=90^\circ,\qquad R_p(\theta_B)=0",
                r"""At Brewster incidence the reflected and transmitted rays are
orthogonal.  Substituting that condition into Snell's law gives the tangent
rule.  For natural light, apply the separate Fresnel reflectances to equal
incident s and p irradiances, then form the polarization degree.""",
                "Identify whether incidence is internal or external, take the correct index ratio, and use the Fresnel power coefficients when a degree of polarization is requested.",
                "The internal and external Brewster angles are complementary for the same interface; the reflected p component must vanish at the result.",
            ),
            Section(
                "Birefringence",
                78,
                items(r"""
                pass right-circular light through a vertical-fast-axis quarter-wave plate
                pass left-circular light through the same plate
                find extraordinary-ray and optic-axis angles in calcite
                design a retarder that reverses circular handedness
                analyze a half-wave plate between crossed polarizers
                repeat the crossed-polarizer analysis at half the wavelength
                find wavelengths emerging circular after removing the analyzer
                design a calcite plate for extinction between parallel polarizers
                infer ordinary and extraordinary indices from prism deviations
                """),
                r"\Delta\phi=\frac{2\pi d}{\lambda_0}(n_s-n_f),\qquad J(\alpha,\Delta\phi)=R(-\alpha)\begin{bmatrix}e^{-i\Delta\phi/2}&0\\0&e^{i\Delta\phi/2}\end{bmatrix}R(\alpha)",
                r"""Resolve the incident Jones vector onto the fast and slow axes,
apply their relative phase delay, and rotate back.  Quarter-, half-, and
full-wave behavior corresponds to :math:`\Delta\phi=\pi/2`, :math:`\pi`, and
:math:`2\pi` modulo :math:`2\pi`.  Minimum-deviation prism data gives each
principal index through the prism formula.""",
                "Build the rotated retarder matrix with the axis orientation shown in the source, multiply by the input state, and reduce the output phase and amplitude ratio before naming its polarization.",
                "A lossless retarder preserves Jones-vector norm; doubling wavelength-dependent retardance order must agree with Δφ proportional to d/λ0.",
            ),
        ),
    ),
    Chapter(
        6,
        "interference_and_coherence",
        "Interference and Coherence",
        (
            Section(
                "Interference of two waves",
                52,
                items(r"""
                locate a minimum from two in-phase radio sources
                identify when orthogonally polarized sources add without fringes
                describe a two-source microwave radiation pattern
                verify spatially averaged energy conservation
                include an intrinsic phase in the two-source pattern
                find lobe rotation caused by a thirty-degree phase shift
                choose phase shift for a twenty-degree lobe rotation
                """),
                r"I=I_1+I_2+2\sqrt{I_1I_2}\,|\hat{\mathbf e}_1\cdot\hat{\mathbf e}_2|\cos\delta,\qquad \delta=ka\sin\theta+\delta_0",
                r"""Add fields before time averaging.  Equal parallel-polarized
sources give :math:`I=4I_0\cos^2(\delta/2)`; orthogonal polarization removes
the cross term.  Maxima and minima follow from :math:`\delta=2m\pi` and
:math:`(2m+1)\pi`, respectively.""",
                "Express the path difference geometrically, add any source phase, impose the required maximum/minimum phase, and solve for position or angle.",
                "A full angular average of the cosine cross term vanishes for well-separated sources, so integrated energy remains the sum of source energies.",
            ),
            Section(
                "Wavefront-splitting interferometers",
                59,
                items(r"""
                express Young-fringe spacing using source angular separation
                infer slit spacing from helium fringes
                find virtual-source angular separation in a mirror geometry
                locate a Fresnel double-mirror fringe
                infer Fresnel-biprism angle from fringe spacing
                generalize biprism fringes to liquid immersion
                track Lloyd-mirror central fringe after inserting a plate
                infer Lloyd source height from fringe spacing
                explain interference from a Billet split lens
                """),
                r"\Delta y=\frac{\lambda_0L}{a}=\frac{\lambda_0}{\beta},\qquad \delta=\frac{2\pi}{\lambda_0}\,\mathrm{OPD}",
                r"""In the paraxial limit the path difference is
:math:`ay/L`, so successive orders differ by :math:`\lambda_0L/a`.  Mirrors,
biprisms, and split lenses first create two coherent virtual or real images;
compute their effective separation and then reuse Young's formula.""",
                "Reduce the apparatus to two coherent sources, calculate their separation and relative phase (including reflection or plate shifts), then apply the fringe-order condition.",
                "Fringe spacing grows with wavelength and propagation distance and decreases with source separation; a zero-OPD white-light fringe is achromatic.",
            ),
            Section(
                "Amplitude splitting by thin films",
                68,
                items(r"""
                compute reflected-ray phase difference through a film
                derive equal-inclination extrema
                identify the central order of a parallel plate
                design an ideal single-layer antireflection coating
                choose magnesium-fluoride coating thickness
                infer wedge angle from fringe spacing
                locate the fourth wedge maximum and its film thickness
                infer liquid index from Newton-ring diameters
                recover lens curvature from separated Newton-ring orders
                generalize Newton rings to two curved surfaces
                """),
                r"\delta=\frac{4\pi nd\cos\theta_t}{\lambda_0}+\delta_r,\qquad 2nd\cos\theta_t=m\lambda_0,\qquad r_m^2\simeq \frac{m\lambda_0R}{n}",
                r"""The round-trip optical thickness is
:math:`2nd\cos\theta_t`.  Add :math:`\pi` for exactly one reflection from a
higher-index boundary.  A quarter-wave coating sets
:math:`d=\lambda_0/(4n_c)` and ideally
:math:`n_c=\sqrt{n_0n_s}`.  Newton-ring radii follow from
:math:`d(r)\simeq r^2/(2R)`.""",
                "Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.",
                "Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.",
            ),
            Section(
                "Amplitude-splitting interferometers",
                78,
                items(r"""
                prove Michelson equal-inclination rings collapse as arms equalize
                find sodium-doublet mirror travel from visibility maximum to minimum
                find Michelson mirror travel for ten thousand fringes
                derive the small-angle radius of a Michelson dark ring
                calculate the fifteenth dark-ring angle
                infer gas index with a Jamin interferometer
                explain and apply a Mach-Zehnder interferometer
                """),
                r"\mathrm{OPD}=2d\cos\theta,\qquad N=\frac{2\Delta d}{\lambda_0},\qquad 2d(1-\cos\theta_p)=p\lambda_0\simeq d\theta_p^2",
                r"""A mirror displacement changes a Michelson round trip by twice
the mechanical travel.  For a doublet, visibility goes from maximum to minimum
when the two wavelengths acquire a relative phase of :math:`\pi`.  A gas cell
adds optical path :math:`(n-1)L` per traversed cell length.""",
                "Count optical passes before equating OPD to Nλ, use 1-cos θ≈θ²/2 only after writing the exact relation, and distinguish mirror travel from optical-path change.",
                "Moving a Michelson mirror by λ/2 must move one fringe past the detector; inferred gas indices should differ from unity only slightly.",
            ),
            Section(
                "Coherence",
                85,
                items(r"""
                infer coherence time and length from laser frequency stability
                estimate linewidth and coherence length from transition time
                infer filter linewidth and Michelson range from wave-train length
                relate inverse fractional stability to wavelengths per wave train
                find coherence length and cycle count through a narrow filter
                infer stellar angular diameter with a Michelson interferometer
                compare methane-stabilized laser coherence over a decade
                """),
                r"\tau_c\sim\frac1{\Delta\nu},\qquad \ell_c=c\tau_c\sim\frac{\lambda_0^2}{\Delta\lambda},\qquad \frac{\nu}{\Delta\nu}\sim\frac{\ell_c}{\lambda_0}",
                r"""Convert fractional stability :math:`\Delta\nu/\nu` to an
absolute linewidth using :math:`\nu=c/\lambda_0`.  The reciprocal linewidth is
the coherence time and multiplication by :math:`c` gives coherence length.
For a stellar disk, the first visibility zero supplies its angular diameter.""",
                "Keep frequency and wavelength linewidths distinct, use the small-bandwidth differential Δν/ν≈Δλ/λ, and compare interferometer OPD—not single-arm length—with coherence length.",
                "All three ratios ν/Δν, λ/Δλ, and ℓc/λ should agree in order of magnitude.",
            ),
        ),
    ),
    Chapter(
        7,
        "diffraction",
        "Diffraction",
        (
            Section(
                "Radiation from a coherent line source",
                52,
                items(r"""
                recover Young's pattern as a two-element array
                count minima and subsidiary maxima between array principals
                resolve the beam spacing and width of a thirty-two-antenna array
                orient the central maximum with progressive source phase
                calculate array steering from a thirty-degree phase increment
                derive specular reflection as an atomic-array maximum
                """),
                r"I(\theta)=I_1\left[\frac{\sin(N\alpha)}{\sin\alpha}\right]^2,\qquad \alpha=\frac12(ka\sin\theta+\delta_0)",
                r"""Sum the geometric phasor series
:math:`\sum_{m=0}^{N-1}e^{i2m\alpha}` and square its magnitude.  Principal
maxima occur when :math:`\alpha=q\pi`; zeros occur at the intervening
:math:`N-1` numerator zeros.  A progressive source phase shifts the whole
pattern by changing :math:`\delta_0`.""",
                "Insert N, spacing, wavelength, and intrinsic phase into the array factor; solve its numerator and denominator limits separately at principal maxima.",
                "The N=2 limit must equal the two-source cosine-squared pattern and the peak intensity must scale as N² for equal coherent emitters.",
            ),
            Section(
                "Fraunhofer diffraction by one and two narrow slits",
                58,
                items(r"""
                prove lens-position independence of focal-plane minima
                shift the single-slit pattern for oblique incidence
                overlap minima produced by two wavelengths
                find the half-maximum width of a distant single-slit pattern
                find first-minimum separation in a lens focal plane
                infer focal length from fourth-order minima
                count double-slit fringes inside the diffraction envelope
                infer slit separation from fifteen central bright fringes
                infer fringe spacing and slit width from a nine-fringe pattern
                """),
                r"I(\theta)=I(0)\operatorname{sinc}^2\beta,\quad \beta=\frac{\pi b}{\lambda}\sin\theta,\quad b\sin\theta_m=m\lambda,\quad \Delta y\simeq\frac{\lambda f}{a}",
                r"""Integrating a uniform slit gives the sinc amplitude.  Its zeros
set the diffraction envelope, while two-slit interference supplies the faster
factor :math:`\cos^2(\pi a\sin\theta/\lambda)`.  Oblique incidence replaces
:math:`\sin\theta` by the difference from the incident-direction sine.""",
                "Use the slit width b for envelope zeros and center spacing a for interference maxima; convert small angles to focal-plane coordinates only after establishing the angular condition.",
                "The central single-slit lobe spans twice the first-minimum angle; reducing the slit width must broaden the envelope.",
            ),
            Section(
                "Multiple narrow slits and diffraction gratings",
                67,
                items(r"""
                recover one- and two-slit limits of the N-slit equation
                bound the number of grating principal orders
                find the midpoint subsidiary-maximum irradiance for odd N
                choose focal length for a specified second-order spectrum length
                prove the upper limit of grating resolving power
                calculate resolving power and wavelength resolution of a grating
                size a grating to resolve adjacent laser longitudinal modes
                decide which visible diffraction orders can overlap
                match a third-order wavelength to a fourth-order line
                """),
                r"a\sin\theta_m=m\lambda,\qquad \mathcal R=\frac{\lambda}{\Delta\lambda}=mN,\qquad |m|\leq\frac{a}{\lambda}",
                r"""The grating equation locates orders; the finite geometric sum
sets their width.  Applying the Rayleigh criterion to neighboring wavelengths
gives :math:`\mathcal R=mN`.  Order overlap requires
:math:`m_1\lambda_1=m_2\lambda_2`.""",
                "Use groove spacing (the reciprocal of line density), count illuminated grooves, select the requested order, and apply either the grating equation or mN resolving power.",
                "The sine in the grating equation cannot exceed unity; increasing illuminated width or order must improve resolving power.",
            ),
            Section(
                "Rectangular and circular apertures: Fraunhofer diffraction",
                76,
                items(r"""
                derive the distance criterion for far-field diffraction
                estimate direct-view distance behind a circular hole
                find a diagonal sidelobe of a square aperture
                scale central irradiance with wavelength and aperture area
                calculate telescope focal-plane Airy radius
                estimate diffraction-limited laser spreading
                choose lens diameter for a one-micron image spot
                calculate radio-telescope angular resolution
                calculate eye resolution and resolved object spacing
                find headlight resolution distance for a dark-adapted pupil
                """),
                r"N_F=\frac{d^2}{\lambda L}\ll1,\qquad \theta_R=1.22\frac{\lambda}{D},\qquad r_{\rm Airy}=1.22\frac{\lambda f}{D}",
                r"""Fraunhofer behavior requires the quadratic phase variation
across the aperture to be small, giving :math:`L\gg d^2/\lambda`.  A circular
aperture produces the Airy pattern; the first zero gives the Rayleigh angular
resolution and multiplication by :math:`f` gives focal-plane radius.""",
                "Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.",
                "A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.",
            ),
            Section(
                "Fresnel diffraction: circular systems",
                86,
                items(r"""
                count Fresnel zones uncovered by a circular aperture
                find aperture radii giving on-axis maxima and minima
                find axial irradiance behind a helium-neon aperture
                sum annular-zone contributions for a shaped aperture
                use the vibration curve for one-and-a-half open zones
                find axial irradiance through a second shaped aperture
                evaluate an annular obstruction with the vibration curve
                derive zone-plate focal length and first-zone radius
                calculate zone-plate focus irradiance with only the first zone open
                find zone-plate focal and image distances
                """),
                r"r_m^2\simeq m\lambda\frac{r_0r_1}{r_0+r_1},\qquad \frac1f=\frac1{r_0}+\frac1{r_1},\qquad f_m=\frac{r_m^2}{m\lambda}",
                r"""Successive Fresnel-zone boundaries differ in optical path by
:math:`\lambda/2`, so adjacent zone amplitudes nearly cancel.  Convert every
open annulus to the difference of two cumulative vibration-curve vectors and
sum complex amplitudes before squaring.  A zone plate passes alternate zones,
making their surviving contributions add near a focus.""",
                "Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.",
                "Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.",
            ),
            Section(
                "Fresnel diffraction: straight edges",
                96,
                items(r"""
                prove that a very wide slit approaches unobstructed irradiance
                derive Cornu-spiral slope and locate horizontal and vertical tangencies
                evaluate a line-source central slit irradiance and Cornu arc
                evaluate an off-axis slit irradiance under plane-wave illumination
                maximize on-axis irradiance of a variable-width slit
                explain the narrow-slit approach to Fraunhofer behavior
                choose a slit width that maximizes axial irradiance
                prove the quarter-irradiance value opposite a half-plane edge
                locate the first maximum and minimum behind a straight edge
                find and sketch the central irradiance behind a narrow opaque strip
                """),
                r"u=y\sqrt{\frac{2(r_0+r_1)}{\lambda r_0r_1}},\qquad \frac{E}{E_0}=\frac{[C(u_2)-C(u_1)]+i[S(u_2)-S(u_1)]}{1+i},\qquad \frac{I}{I_0}=\left|\frac{E}{E_0}\right|^2",
                r"""Map each physical edge to its dimensionless Fresnel coordinate
:math:`u`.  The Cornu-spiral chord between the two edge points is the complex
field; its squared length, with the unobstructed normalization, is irradiance.
For complementary apertures, Babinet's principle adds fields—not
irradiances—to the unobstructed field.""",
                "Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.",
                "Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.",
            ),
        ),
    ),
    Chapter(
        8,
        "introduction_to_fourier_optics",
        "Introduction to Fourier Optics",
        (
            Section(
                "Periodic waves and Fourier series",
                22,
                items(r"""
                prove equivalence of amplitude-phase and sine-cosine Fourier forms
                show screw symmetry removes even harmonics
                state when only even harmonics remain
                derive the series of a periodic ramp-and-step waveform
                derive the series of a second periodic waveform
                generalize the waveform to arbitrary period
                obtain a shifted series by changing axes
                derive the series of a full-wave rectified sine
                """),
                r"f(x)=\frac{a_0}{2}+\sum_{m=1}^{\infty}[a_m\cos(mkx)+b_m\sin(mkx)],\quad a_m=\frac{2}{L}\int_L f\cos(mkx)\,dx,\quad b_m=\frac{2}{L}\int_L f\sin(mkx)\,dx",
                r"""Use parity before integrating: even functions have only cosine
terms and odd functions only sine terms.  Half-wave antisymmetry cancels even
harmonics.  Combine :math:`a_m` and :math:`b_m` as
:math:`C_m\cos(mkx+\phi_m)` using
:math:`a_m=C_m\cos\phi_m` and :math:`b_m=-C_m\sin\phi_m`.""",
                "Choose one complete period matching the source graph, split the integral at every discontinuity, exploit symmetry, and simplify the coefficient separately for even and odd m.",
                "Reconstruct representative points away from jumps and verify the midpoint value at a jump; the coefficients must have the parity dictated by the waveform.",
            ),
            Section(
                "Fourier transforms",
                30,
                items(r"""
                transform a square pulse with complex exponentials
                transform a windowed sine wave
                transform a windowed sine-squared wave
                transform a two-sided exponential by two routes
                transform a Gaussian and interpret apodization
                transform a causal exponentially weighted coordinate
                transform delta and constant functions
                """),
                r"F(k)=\int_{-\infty}^{\infty}f(x)e^{-ikx}\,dx,\qquad f(x)=\frac1{2\pi}\int_{-\infty}^{\infty}F(k)e^{ikx}\,dk",
                r"""Insert the piecewise support before integrating.  Modulation
shifts spectra:
:math:`\mathcal F\{f(x)e^{ik_0x}\}=F(k-k_0)`, while multiplication by
:math:`x` gives :math:`i\,dF/dk`.  Complete the square for a Gaussian and use
the delta sifting property for constants and impulses.""",
                "Rewrite trigonometric modulation as exponentials, apply the shift theorem to the base transform, and preserve the book's 2π transform convention throughout.",
                "A real even function must have a real even transform; narrowing a spatial pulse must broaden its spectrum.",
            ),
            Section(
                "Convolution",
                37,
                items(r"""
                prove the frequency-domain convolution theorem
                transform a cosine squared using spectral convolution
                prove commutativity of convolution
                construct a discrete self-convolution
                convolve a three-impulse distribution with itself
                self-convolve a four-line spectrum
                convolve a rectangular pulse with an impulse pair and transform it
                self-convolve a double-slit aperture function
                convolve two unequal rectangular pulses
                construct a further graphical convolution
                self-convolve a two-dimensional six-hole mask
                """),
                r"(f*h)(x)=\int_{-\infty}^{\infty}f(\xi)h(x-\xi)\,d\xi,\qquad \mathcal F\{fh\}=\frac1{2\pi}(F*H),\qquad \delta(x-a)*\delta(x-b)=\delta[x-(a+b)]",
                r"""For a graphical convolution, reverse one function, translate it
by :math:`x`, multiply overlaps, and integrate.  For impulses, form every
ordered pair of locations; their coordinates add and coincident sums add
weights.  The transform product/convolution theorem follows by inserting the
inverse transforms and evaluating the inner exponential integral as a delta.""",
                "Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.",
                "Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.",
            ),
        ),
    ),
)


def problem_count() -> int:
    return sum(
        len(section.focuses) for chapter in CHAPTERS for section in chapter.sections
    )


def render_figure(key: str, caption: str) -> list[str]:
    filename = figure_name(key)
    return [
        f".. figure:: /_static/knowledge_base/worked_exercises/schaum_optics/{filename}",
        f"   :alt: {caption}",
        "   :width: 100%",
        "   :align: center",
        f"   :name: schaum-figure-{key.replace('.', '-')}",
        "",
        f"   {caption}",
        "",
    ]


def render_chapter(chapter: Chapter) -> str:
    title = f"Chapter {chapter.number}: {chapter.title}"
    lines = [
        title,
        "=" * len(title),
        "",
        "Source: Eugene Hecht, *Schaum's Outline of Theory and Problems of",
        f"Optics* (1975), Chapter {chapter.number}.  The entries below cover only the",
        "chapter's **Supplementary Problems**; prompts are paraphrased and are not",
        "reproduced.",
        "",
        "Each numbered solution states its assumptions, develops the algebra, substitutes",
        "the relevant data, and checks the result.  Original SVG illustrations show the",
        "ray geometry, field relationships, or calculated curves.  Diagrams are schematic",
        "unless their axes specify a scale.  Source inconsistencies and approximations are",
        "identified explicitly rather than silently copied into the answer.",
        "",
    ]

    for section_index, section in enumerate(chapter.sections, start=1):
        label = f"schaum-{chapter.number}-{section_index}"
        lines.extend(
            [
                section.title,
                "-" * len(section.title),
                "",
                "**Formula and definitions.**",
                "",
                ".. math::",
                f"   :label: {label}",
                "",
            ]
        )
        lines.extend(f"   {part}" for part in section.equation.splitlines())
        lines.extend(["", section.derivation, ""])
        topic_key = f"{chapter.number}-{section_index}"
        lines.extend(render_figure(topic_key, TOPICS[topic_key]))

        for offset, focus in enumerate(section.focuses):
            number = section.first + offset
            key = f"{chapter.number}.{number}"
            heading = f"Problem {key} — {focus}"
            working, result, check = SOLUTIONS[key]
            working = re.sub(r"\n+(?=[23]\. )", "\n\n", working.strip())
            lines.extend(
                [
                    heading,
                    "^" * len(heading),
                    "",
                    f"**Paraphrased task.** {focus.capitalize()}.",
                    "",
                    f"**Formula reference.** Use :eq:`{label}`, its definitions, and "
                    f":ref:`the topic illustration <schaum-figure-{topic_key}>`.",
                    "",
                    "**Worked application.**",
                    "",
                    working,
                    "",
                    f"**Result.** {result}",
                    "",
                    f"**Check.** {check}",
                    "",
                ]
            )
            if key in PROBLEMS:
                lines.extend(render_figure(key, PROBLEMS[key]))
    return "\n".join(lines).rstrip() + "\n"


def render_index() -> str:
    title = "Schaum's Outline of Optics — Supplementary Problem Solutions"
    lines = [
        title,
        "=" * len(title),
        "",
        "This collection accompanies Eugene Hecht, *Schaum's Outline of Theory and",
        "Problems of Optics* (1975).  It covers all 270 numbered **Supplementary",
        "Problems** in Chapters 1--8.  The chapter ranges were checked against the scan:",
        "1.31--1.64, 2.26--2.47, 3.31--3.50, 4.62--4.96, 5.48--5.86,",
        "6.52--6.91, 7.52--7.105, and 8.22--8.47.",
        "",
        "These independently written solutions do not reproduce the original prompts.",
        "Each includes problem-specific working: assumptions and sign conventions,",
        "intermediate algebra, numerical substitutions or a completed proof, and a check.",
        f"The {len(TOPICS) + len(PROBLEMS)} original SVG illustrations include ray diagrams, polarization",
        "trajectories, interference and diffraction curves, and Fourier/convolution",
        "constructions.  Formulae use SI units unless another consistent system is stated.",
        "",
        ".. note::",
        "",
        "   A scan OCR error reads Problem 8.43 as ``8.48``.  The printed page and",
        "   sequence confirm that the convolution problem between 8.42 and 8.44 is 8.43.",
        "   Where the printed data, endpoint, or approximation conflict, the solution",
        "   explains the discrepancy and checks the result against the governing equations.",
        "   In particular, distinguish exact fringe counts from width/spacing estimates,",
        "   and graphical Cornu-spiral readings from numerical Fresnel-integral evaluation.",
        "   Fourier transforms here use a negative forward exponential consistently;",
        "   imaginary spectra consequently have the opposite sign to the book's positive",
        "   forward-exponential convention.",
        "",
        ".. toctree::",
        "   :maxdepth: 1",
        "",
    ]
    lines.extend(f"   ch{chapter.number:02d}_{chapter.slug}" for chapter in CHAPTERS)
    return "\n".join(lines) + "\n"


def validate_configuration() -> None:
    expected = {
        1: (31, 64),
        2: (26, 47),
        3: (31, 50),
        4: (62, 96),
        5: (48, 86),
        6: (52, 91),
        7: (52, 105),
        8: (22, 47),
    }
    failures = []
    for chapter in CHAPTERS:
        actual = [
            section.first + offset
            for section in chapter.sections
            for offset in range(len(section.focuses))
        ]
        first, last = expected[chapter.number]
        wanted = list(range(first, last + 1))
        if actual != wanted:
            failures.append(
                f"Chapter {chapter.number}: got {actual}, expected {wanted}"
            )
    if problem_count() != 270:
        failures.append(f"total is {problem_count()}, expected 270")
    configured = {
        f"{chapter.number}.{section.first + offset}"
        for chapter in CHAPTERS
        for section in chapter.sections
        for offset in range(len(section.focuses))
    }
    result_keys = set(SOLUTIONS)
    missing_results = sorted(configured - result_keys)
    extra_results = sorted(result_keys - configured)
    if missing_results:
        failures.append(f"problems without result text: {missing_results}")
    if extra_results:
        failures.append(f"result text without a configured problem: {extra_results}")
    expected_topics = {
        f"{chapter.number}-{index}"
        for chapter in CHAPTERS
        for index in range(1, len(chapter.sections) + 1)
    }
    if set(TOPICS) != expected_topics:
        failures.append("topic illustrations do not match the configured sections")
    if set(PROBLEMS) - configured:
        failures.append("problem illustrations include unknown problem numbers")
    if failures:
        raise SystemExit("Invalid Schaum inventory:\n- " + "\n- ".join(failures))


def main() -> None:
    validate_configuration()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "index.rst").write_text(render_index(), encoding="utf-8")
    for chapter in CHAPTERS:
        path = OUTPUT / f"ch{chapter.number:02d}_{chapter.slug}.rst"
        path.write_text(render_chapter(chapter), encoding="utf-8")
    print(f"Generated {problem_count()} supplementary solutions in {OUTPUT}")


if __name__ == "__main__":
    main()
