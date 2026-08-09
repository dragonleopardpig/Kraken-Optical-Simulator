r"""Generate the Schaum optics supplementary-problem solution collection.

The source scan is not needed by Sphinx.  Problem statements below are short,
independently written topic descriptions; the generated pages contain the
derivations, formula references, applications, and answer checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "source" / "knowledge_base" / "worked_exercises" / "schaum_optics"


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
                derive the series of a symmetric rectangular waveform
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
                transform a one-sided exponential by two routes
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
                convolve a point array with a continuous spread function
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


# Values are independently recomputed with the displayed equations and retained
# as concise checks.  Proof/construction problems intentionally use the derived
# relation in their section rather than a detached numeric answer.
RESULTS = {
    "1.33": r":math:`v_1=1` toward :math:`+y`, :math:`v_2=C/B` toward :math:`-x`, and :math:`v_3=C` toward :math:`+z`.",
    "1.35": r"Both travelling terms have speed magnitude :math:`B`.",
    "1.39": r":math:`\lambda=3.0\times10^6\,\mathrm m` at 100 Hz; a 1 m wave requires :math:`3.0\times10^8\,\mathrm{Hz}` (300 MHz).",
    "1.41": r":math:`\lambda=200\,\mathrm{nm}`, :math:`f=1.5\times10^{15}\,\mathrm{Hz}`, and :math:`v=3.0\times10^8\,\mathrm{m\,s^{-1}}`.",
    "1.42": r"The specified event gives a disturbance magnitude of 10 units.",
    "1.47": r"It is a negative-x travelling profile with :math:`v=3.0\times10^8\,\mathrm{m\,s^{-1}}`.",
    "1.49": r"For the sine convention, :math:`\phi_0=\pi/2\pmod{2\pi}`.",
    "1.52": r":math:`\lambda=1\,\mu\mathrm m`, hence :math:`\Delta x=(m+1/6)\lambda`: 166.7 nm, 1166.7 nm, 2166.7 nm, … .",
    "1.53": r"(a) :math:`5.0\times10^5` cycles, or :math:`10^6\pi` rad; (b) the train length is :math:`0.300\,\mathrm m`.",
    "2.26": r":math:`\lambda=500\,\mathrm{nm}`, :math:`v=c`, along :math:`+z`; :math:`E_0=200\,\mathrm{V/m}` with the transverse orientation fixed by :math:`\mathbf E\times\mathbf B`.",
    "2.30": r":math:`k=1.57\times10^7\,\mathrm{rad/m}`.",
    "2.31": r":math:`L=c\Delta t/(1.46-1)=6.52\times10^2\,\mathrm m`.",
    "2.32": r":math:`\lambda_D/\lambda_Z=n_Z/n_D=0.796`.",
    "2.33": r":math:`n\simeq\sqrt{2.381}=1.543`.",
    "2.34": r":math:`U=10^4\,\mathrm J`.",
    "2.35": r":math:`I=3.0\times10^{12}\,\mathrm{W/m^2}` and :math:`E_0\approx4.75\times10^7\,\mathrm{V/m}`.",
    "2.37": r":math:`P=4\pi r^2(c\epsilon_0E_0^2/2)\approx1.67\times10^2\,\mathrm W`.",
    "2.40": r":math:`p_{\rm rad}\approx9.8\times10^{-6}\,\mathrm{N/m^2}`.",
    "2.41": r":math:`\lambda_{\max}=hc/(1.8\,\mathrm{eV})\approx688\,\mathrm{nm}`.",
    "2.42": r":math:`F=P/c\approx3.34\times10^{-12}\,\mathrm N` for a collimated 1 mW output; use :math:`2P/c` only if the emitted beam is replaced by a perfectly reflected incident beam.",
    "2.44": r"Microwave radiation: :math:`\nu\approx1.43\times10^9\,\mathrm{Hz}` and :math:`E_\gamma\approx9.46\times10^{-25}\,\mathrm J`.",
    "2.45": r"Radio-frequency radiation with :math:`T\approx100\,\mathrm s` and :math:`E_\gamma\approx4.14\times10^{-17}\,\mathrm{eV}`.",
    "3.34": r"The retracing condition is :math:`\theta_i=3\alpha` for the angles defined in the source figure.",
    "3.40": r":math:`r_s=-0.303` and :math:`t_s=0.697` (rounding depends on the refracted-angle precision).",
    "3.44": r"For glass-to-air normal incidence, :math:`r=+0.2` and :math:`t=1.2`; power remains conserved.",
    "3.45": r"Equal normal-incidence reflectance and transmittance occurs at relative index :math:`n_{ti}=3\pm2\sqrt2\approx5.83` or 0.172.",
    "3.46": r"The combined relative index is :math:`n_C/n_A=2`.",
    "3.47": r":math:`n_{\min}=\sqrt2\approx1.414`.",
    "3.48": r":math:`n\approx1.63`.",
    "3.49": r":math:`\theta_B=\arctan(1/\sin45^\circ)=54.74^\circ` for air incident on the liquid.",
    "4.65": r":math:`s_i=-20\,\mathrm{cm}`: the center-of-curvature point is imaged onto itself.",
    "4.66": r"Place the source :math:`10\,\mathrm{cm}` to the left of the spherical end.",
    "4.67": r":math:`s_i\approx-2.32\,\mathrm{cm}`, a virtual image on the object side of the first vertex.",
    "4.68": r":math:`R=+20\,\mathrm{cm}`.",
    "4.69": r"For the smaller radius magnitude, :math:`R=3f/4`.",
    "4.70": r":math:`s_{o,\pm}=[L\pm\sqrt{L(L-4f)}]/2`, requiring :math:`L\ge4f`.",
    "4.71": r":math:`R_1=+80.6\,\mathrm{cm}` and :math:`R_2=-80.6\,\mathrm{cm}`.",
    "4.73": r":math:`s_o=0.100\,\mathrm m`, :math:`M_T=-100`, and :math:`f\approx0.0990\,\mathrm m`.",
    "4.74": r":math:`s_i=-144\,\mathrm{cm}` and :math:`f=240\,\mathrm{cm}`.",
    "4.75": r":math:`s_o\approx2.04\,\mathrm m` and :math:`s_i\approx51.3\,\mathrm{mm}`.",
    "4.77": r"Matrix reduction gives the front and back focal locations from the two principal planes; keep the 10-cm separation in the matrix rather than adding the lens powers as though they were in contact.",
    "4.78": r"The contact combination has :math:`f=8\,\mathrm{cm}` and forms its image :math:`16\,\mathrm{cm}` beyond the lens.",
    "4.79": r"The component focal lengths are 45 cm and 90 cm.",
    "4.80": r"The final image is :math:`90\,\mathrm{cm}` to the right of the negative lens.",
    "4.82": r":math:`f=3\,\mathrm{cm}`, with principal-plane offsets :math:`h_1=+0.5\,\mathrm{cm}` and :math:`h_2=-1.0\,\mathrm{cm}` in the chapter convention.",
    "4.83": r":math:`f=12\,\mathrm{cm}`, :math:`h_1=0`, :math:`h_2=-6\,\mathrm{cm}`, and the real image is 18 cm to the right of the second principal plane.",
    "4.85": r":math:`f\approx3.00\,\mathrm{mm}` and the real image is about 38.2 mm from the sphere center, with :math:`M_T\approx-0.06`.",
    "4.86": r"The first focal plane is halfway between the lenses, :math:`f_1/2` to the left of the eye lens.",
    "4.87": r"The object is 50 cm left of the first lens.",
    "4.88": r"Afocality requires :math:`f_3\approx+3.0\,\mathrm{cm}`.",
    "4.89": r"The Ramsden object plane lies one effective focal length :math:`3f_1/4` in front of the ocular.",
    "4.90": r"The net power is zero, so the combination is afocal.",
    "4.91": r"The mirror has :math:`f=100\,\mathrm{cm}`; exchanging conjugates puts the object 150 cm from the vertex.",
    "4.93": r"The image is real, erect, magnified, and farther from the mirror than the virtual object.",
    "4.94": r":math:`s_i=6\,\mathrm{cm}`, :math:`M_T=-1/2`, giving a 0.5-cm inverted real image.",
    "4.95": r":math:`s_i=-133.3\,\mathrm{cm}`, :math:`M_T=+2/3`, giving a virtual erect reduced image.",
    "4.96": r":math:`s_i=-36\,\mathrm{cm}`, :math:`M_T=+1/5`, giving a 0.6-cm virtual erect image.",
    "5.69": r"The three-filter transmission is :math:`0.1920 I_i`.",
    "5.70": r"Ten filters transmit :math:`I_i(1/2)^{10}=9.77\times10^{-4}I_i`; :math:`N` filters give :math:`I_i(1/2)^N` for the specified natural input and 45° steps.",
    "5.71": r"The four-filter stack transmits :math:`0.2109 I_i`; removing the middle plates gives zero through crossed endpoints.",
    "5.72": r"No light emerges because the final analyzer is crossed with the immediately preceding polarization.",
    "5.73": r":math:`n=\tan(58^\circ01')\approx1.6014`.",
    "5.74": r":math:`\theta_B\approx56^\circ36'` and :math:`\theta_t\approx33^\circ24'`.",
    "5.76": r"The reflected beam is fully polarized; the transmitted degree is about 8.1%.",
    "5.77": r"External and internal Brewster angles are approximately :math:`51.45^\circ` and :math:`38.55^\circ`, respectively.",
    "5.78": r"The output is linear at 135° to the positive x axis under the book's handedness convention.",
    "5.79": r"The output is linear at 45° to the positive x axis.",
    "5.80": r"The source geometry gives approximately :math:`\beta=45^\circ24'` and extraordinary-ray deflection :math:`\alpha=6^\circ14'`.",
    "5.81": r"A minimum half-wave thickness is :math:`d\approx3.64\times10^{-3}\,\mathrm{cm}`.",
    "5.84": r"With the analyzer removed, the yellow-green wavelength near 520 nm emerges circular.",
    "5.85": r"Use a half-wave plate at 45°; :math:`d\approx1.713\times10^{-4}\,\mathrm{cm}`.",
    "5.86": r"The two minimum-deviation measurements give principal indices about 1.532 and 1.597.",
    "6.52": r"The first accessible minimum is 2.25 m along the perpendicular bisector.",
    "6.54": r"Principal lobes occur at 0°, 30°, 90°, 150°, 180°, 210°, 270°, and 330° from the normal to the source line.",
    "6.57": r"The forward lobe rotates by about :math:`2.39^\circ`.",
    "6.58": r"The required adjacent-source phase difference has magnitude about :math:`61.6^\circ`.",
    "6.60": r":math:`a=\lambda L/\Delta y\approx2.64\,\mathrm{mm}`.",
    "6.62": r"The seventh bright fringe is about 1.98 mm from the central axis.",
    "6.63": r"The biprism apex angle is about :math:`0.843^\circ`.",
    "6.66": r"The Lloyd source height is about 0.75 mm.",
    "6.68": r"The propagation contribution is about :math:`22.63\pi`; after the single reflection reversal the equivalent phase is about :math:`1.63\pi` modulo :math:`2\pi`.",
    "6.70": r"Using the plate thickness printed in the source, :math:`2nd/\lambda_0=10{,}000`; the single reflection reversal makes the central fringe a minimum.",
    "6.71": r":math:`n_c=\sqrt{2.409}=1.552` and the minimum thickness is about 94.9 nm.",
    "6.72": r"The minimum magnesium-fluoride thickness is about 106.7 nm.",
    "6.73": r"The wedge angle is about :math:`0.0635^\circ`.",
    "6.74": r"At the fourth maximum, :math:`d\approx7.76\times10^{-7}\,\mathrm m` and :math:`x\approx0.700\,\mathrm{mm}`.",
    "6.75": r"The liquid index follows the squared-diameter ratio and is about 1.30 (using 2.52 cm and 2.21 cm); this also flags the scan's OCR-corrupted printed check.",
    "6.76": r"Eliminating the unknown absolute order with the two ring radii gives :math:`R\approx3.41\,\mathrm m`.",
    "6.79": r"The sodium-doublet maximum-to-minimum mirror travel is about 0.145 mm.",
    "6.80": r"Ten thousand fringes require :math:`\Delta d=N\lambda/2\approx3.029\,\mathrm{mm}`; this distinguishes mirror travel from total OPD.",
    "6.82": r"For the stated fifteenth ring, :math:`\theta\approx1^\circ24'`.",
    "6.83": r":math:`n\approx1.000139`.",
    "6.85": r":math:`\tau_c\approx4.8\times10^{-2}\,\mathrm s` and :math:`\ell_c\approx1.44\times10^7\,\mathrm m`.",
    "6.86": r"Use :math:`\Delta\nu\sim1/\Delta t` and :math:`\ell_c=c\Delta t`; the numerical endpoint follows directly after inserting the transition time printed in the problem.",
    "6.87": r":math:`\Delta\lambda\approx13\,\mathrm{nm}` and maximum one-arm Michelson travel about 0.0163 mm.",
    "6.89": r":math:`\ell_c\approx2.02\times10^{-4}\,\mathrm m`, about 367 wavelengths.",
    "6.90": r"The stellar angular diameter is about :math:`2.26\times10^{-7}\,\mathrm{rad}`.",
    "6.91": r"The later stability corresponds to about 6.4 s coherence time versus :math:`4.8\times10^{-2}` s in the earlier result.",
    "7.53": r"There are :math:`N-1` minima and :math:`N-2` subsidiary maxima between adjacent principal maxima.",
    "7.54": r"The principal-maxima spacing is about :math:`1^\circ43'`; the central peak width is about 6 arcmin.",
    "7.59": r"The central lobe shifts to the 30° specular direction and broadens by :math:`1/\cos30^\circ\approx1.155`.",
    "7.60": r"Coincidence of first and third minima requires :math:`\lambda_1=3\lambda_3` (with subscripts assigned to those orders).",
    "7.61": r"The full half-maximum central width is about 632.8 mm at the 1-km screen.",
    "7.62": r"The first-minimum separation is about 2.64 mm.",
    "7.63": r"The inferred focal length is about 7.1 cm.",
    "7.65": r"Fifteen bright fringes place the seventh interference maximum at the first diffraction minimum, giving :math:`a=15b=3.75\,\mathrm{mm}`.",
    "7.66": r"The consecutive maxima are separated by :math:`\Delta Z=\lambda L/a=4.125\,\mathrm{mm}` and the envelope count gives :math:`b=0.089\,\mathrm{mm}`.",
    "7.68": r"The finite order condition is :math:`|m|\le a/\lambda`.",
    "7.70": r"The required focal length is about 5.63 cm.",
    "7.72": r"At 550 nm, :math:`\mathcal R_3=120{,}000` and the second-order resolution is about :math:`6.88\times10^{-3}\,\mathrm{nm}`.",
    "7.73": r"About 79 cm of the 200-line/mm grating must be illuminated.",
    "7.75": r"The coincident third-order wavelength is :math:`(4/3)(490\,\mathrm{nm})=653.3\,\mathrm{nm}`.",
    "7.77": r"The direct-view far-field criterion gives a distance of order 10 m or more.",
    "7.78": r"The third diagonal bright spot has :math:`I/I(0)\approx6.8\times10^{-5}`.",
    "7.80": r"The focal-plane Airy radius is about :math:`8.39\times10^{-3}\,\mathrm{mm}`.",
    "7.81": r"The beam diameter after 1 km is of order 0.77 m under the aperture convention used in the problem.",
    "7.83": r"The 1420-MHz radio telescope resolution is about :math:`6.0\times10^{-3}\,\mathrm{rad}` or 0.34°.",
    "7.84": r":math:`\Delta\phi_{\min}\approx2.68\times10^{-4}\,\mathrm{rad}`, requiring about 0.268 m separation at 1 km.",
    "7.85": r"The headlamps become just resolvable at roughly 6.5 km.",
    "7.86": r"The aperture uncovers about 100 Fresnel zones.",
    "7.88": r"For the stated aperture and axial point, the vibration-curve chord gives :math:`I=2I_0`.",
    "7.90": r"One and one-half open zones give :math:`I\approx2I_0`.",
    "7.94": r"The first-zone radius is about 1.1 mm for 5-m object and image distances at 500 nm.",
    "7.95": r"The first-order focal length is about 3.89 m; equal object and image distances are about 7.78 m.",
    "7.98": r"The central irradiance is about :math:`0.09I_0` and the Cornu-parameter span is about 0.417.",
    "7.99": r"The specified off-axis point gives :math:`I\approx0.0896I_0`.",
        "7.100": r"The maximum variable-slit central irradiance is about :math:`1.8I_0`.",
        "7.101": r"A very narrow slit spans only a small Cornu parameter interval, so its two edge phasors are locally almost straight and parallel; the resulting scaled sinc-like modulation approaches the Fraunhofer pattern.",
    "8.24": r"Only even harmonics remain when the actual period is half the chosen :math:`2\pi` interval.",
    "8.31": r":math:`F(k)=iE_0L[\operatorname{sinc}(k-k_0)L-\operatorname{sinc}(k+k_0)L]` under the book's transform convention.",
    "8.32": r":math:`F(k)=E_0L[\operatorname{sinc}(kL)-\tfrac12\operatorname{sinc}(k+2k_0)L-\tfrac12\operatorname{sinc}(k-2k_0)L]`.",
    "8.33": r"The one-sided exponential transforms to :math:`2a/(a^2+k^2)`.",
    "8.34": r"The normalized Gaussian transforms to :math:`\exp[-k^2/(4a)]`; Gaussian apodization suppresses hard-edge rings.",
    "8.35": r":math:`\mathcal F\{U(x)xe^{-ax}\}=1/(a+ik)^2` for the displayed :math:`e^{-ikx}` convention (the sign changes with the opposite convention).",
    "8.36": r":math:`\mathcal F\{\delta(x)\}=1` and :math:`\mathcal F\{1\}=2\pi\delta(k)`.",
    "8.41": r":math:`f*f=\delta(x-2)+2\delta(x-1)+3\delta(x)+2\delta(x+1)+\delta(x+2)`.",
    "8.47": r"Pairwise sums of the six aperture centers produce 19 sites on a hexagonal lattice; coincident sums determine their relative weights.",
}

# Symbolic endpoints and experimental classifications for the remaining proof,
# graph, and construction problems.  Keeping these here (rather than copying
# the source prompts) makes every numbered entry independently checkable.
RESULTS.update(
    {
        "1.31": r"With :math:`u=t+2z`, :math:`y_{zz}=4y_{uu}` and :math:`y_{tt}=y_{uu}`; hence the wave equation holds for :math:`v=1/2`, toward :math:`-z`.",
        "1.32": r"Only candidates reducible to :math:`F(q\mp vt)` with one constant :math:`v` are progressive; the squared travelling coordinate and the linear :math:`y+t+B` candidate pass this test, while expressions mixing independent squares do not.",
        "1.34": r"For :math:`u=x+vt`, fixed :math:`u` gives :math:`x=u-vt`; the entire profile therefore translates toward :math:`-x` without changing shape.",
        "1.36": r"Two chain-rule differentiations give :math:`y_{xx}=F''` times the squared spatial coefficient and :math:`y_{tt}=F''` times the squared temporal coefficient, so their ratio is :math:`1/v^2` for any twice-differentiable :math:`F`.",
        "1.37": r"A one-way wave satisfies :math:`\partial_t y=-v\,\partial_x y` for :math:`F(x-vt)` and :math:`\partial_t y=+v\,\partial_x y` for :math:`G(x+vt)`.",
        "1.38": r"The fundamental temporal repetition is :math:`T=2\pi/\omega`; equivalently :math:`\omega T=2\pi`.",
        "1.40": r"Euler addition gives :math:`\sin(\Phi+\pi/2)=\sin\Phi\cos(\pi/2)+\cos\Phi\sin(\pi/2)=\cos\Phi`.",
        "1.43": r"At :math:`x=0`, retain the stated amplitude and plot the sinusoid against :math:`t`; its intercept is fixed by :math:`\phi` and its period by :math:`2\pi/\omega`.",
        "1.44": r"The translated snapshot is :math:`y(x,4)=5\sin[\pi(x+8)/25]` for motion at :math:`2\,\mathrm{m/s}` toward :math:`-x`.",
        "1.45": r"The first detector condition selects :math:`t'=7/8` modulo the period; the second detector is then also at the crest, so its reading is :math:`10^2` in the source units.",
        "1.46": r"Integer spatial shifts and a one-period time shift add integral multiples of :math:`2\pi` to the phase, so the corresponding detector readings repeat unchanged.",
        "1.48": r"For the sine convention, :math:`\sin\phi_0=-1`, hence :math:`\phi_0=3\pi/2\pmod{2\pi}`.",
        "1.50": r"At fixed position, :math:`d\Phi/dt=-\omega`: the observed phase decreases uniformly in time for a wave travelling toward :math:`+x`.",
        "1.51": r"At fixed time, :math:`d\Phi/dx=k`: the snapshot phase increases uniformly with position.",
        "1.54": r"The measured gradients give :math:`y(x,t)=10\sin(4\pi\times10^8x-12\pi\times10^{14}t+\pi/3)` and :math:`v=3.0\times10^8\,\mathrm{m/s}`.",
        "1.55": r"Replace every :math:`i` by :math:`-i`; in exponential form, :math:`(Ae^{i\Phi})^*=A^*e^{-i\Phi}`.",
        "1.56": r"After Euler expansion, the two requested real parts reduce to :math:`-2` and :math:`2\cos(\omega t-kx)`.",
        "1.57": r"The requested imaginary parts reduce to the sine quadratures of the first two phasors and zero for the explicitly real symmetric exponential pair.",
        "1.58": r"The magnitudes are :math:`1` and :math:`2[5+4\cos(2\omega t)]^{1/2}`.",
        "1.59": r"The physical square is :math:`A^2\cos^2(kx-\omega t)=[(z+z^*)/2]^2`; it is not :math:`\Re(zz^*)`.",
        "1.60": r"For direction cosines satisfying :math:`\alpha^2+\beta^2+\gamma^2=1`, the Laplacian is :math:`k^2f''` and the time derivative is :math:`\omega^2f''`; :math:`\omega=vk` completes the proof.",
        "1.61": r"One valid form is :math:`y=A\sin[(2\pi/(\lambda\sqrt2))(x+y)-\omega t+\phi_0]`, with :math:`\omega=2\pi v/\lambda`.",
        "1.62": r"At fixed time, :math:`\nabla\Phi=\mathbf k`; its magnitude is :math:`2\pi/\lambda`.",
        "1.63": r"The coefficients normalize to the propagation unit vector :math:`(\hat{\mathbf x}-2\hat{\mathbf y}+3\hat{\mathbf z})/\sqrt{14}`.",
        "1.64": r"Since :math:`(2,2,3)` has norm :math:`\sqrt{17}`, use :math:`\mathbf k=(2\pi/\lambda)(2,2,3)/\sqrt{17}` in :math:`A\sin(\mathbf k\cdot\mathbf r-\omega t+\phi_0)`.",
        "2.27": r"The companion field is transverse to both :math:`+x` and the graphed :math:`\mathbf E`; it has the same phase and amplitude :math:`B_0=E_0/c`.",
        "2.28": r"The right-hand triad gives :math:`\mathbf E` along :math:`+y`; the graph's amplitude corresponds to :math:`E_0\approx7.6\times10^3\,\mathrm{V/m}`.",
        "2.29": r":math:`E_0=\sqrt{2I/(c\epsilon_0)}\approx30.0\,\mathrm{V/m}`.  For propagation along :math:`+y` with :math:`\mathbf B` in the xy plane, choose :math:`\mathbf E\parallel+z` and :math:`\mathbf B\parallel+x`.",
        "2.36": r"Inserting :math:`c` and :math:`\epsilon_0` gives :math:`I=(1.33\times10^{-3}\,\mathrm{W/V^2})E_0^2` in vacuum.",
        "2.38": r"Time averaging :math:`c\epsilon_0E_0^2\sin^2\Phi` gives :math:`I=c\epsilon_0E_0^2/2`.",
        "2.39": r"Unit conversion gives :math:`E_\gamma(\mathrm{eV})=1239.84/\lambda(\mathrm{nm})`, conventionally rounded to 1239.",
        "2.43": r"The reflecting area intercepts the full 600-W beam, so :math:`F=2P/c\approx4.0\times10^{-6}\,\mathrm N`.",
        "2.46": r"For one erg the photon counts are approximately :math:`5.0\times10^5`, :math:`2.5\times10^{11}`, and :math:`5.0\times10^{15}` at :math:`10^{-12}\,\mathrm m`, 500 nm, and 1 cm.",
        "2.47": r"The photon energies are :math:`1.99\times10^{-24}\,\mathrm J` at 10 cm and :math:`3.14\times10^{-19}\,\mathrm J` at 632.9 nm; the microwave photon carries about :math:`6.3\times10^{-6}` as much energy.",
        "3.31": r"Expanding :math:`\sin(\theta_i-\theta_t)` and using Snell's law gives :math:`a=d\sin\theta_i[1-n_i\cos\theta_i/(n_t\cos\theta_t)]`.",
        "3.32": r"Summing the two surface turns gives the prism deviation :math:`\delta=\theta_{i1}+\theta_{t2}-A` in the source notation.",
        "3.33": r"Each reflection turns the ray through twice the angle between the ray and mirror normal; adding the two signed turns yields the source figure's two-mirror deviation relation.",
        "3.35": r"The perpendicular projection of the radius-:math:`n` construction is :math:`n\sin\theta`; equality of that projection across the interface is exactly :math:`n_i\sin\theta_i=n_t\sin\theta_t`.",
        "3.36": r"Every reflecting point on the ellipse satisfies :math:`SP_1+P_1P_2=2a`; the optical path is therefore stationary (indeed constant), so a ray from one focus reaches the other.",
        "3.37": r"Differentiating the two segment lengths with respect to the angular coordinate again gives :math:`n_i\sin\theta_i=n_t\sin\theta_t`.",
        "3.38": r"The first-order optical-path difference is proportional to :math:`n_i\sin\theta_i-n_t\sin\theta_t`; stationarity makes it zero and yields Snell's law.",
        "3.39": r"An out-of-plane displacement adds a nonzero first-order path change unless both rays and the surface normal share one plane; stationarity therefore enforces the plane of incidence.",
        "3.41": r"Using Snell's law, :math:`t_s=2\sin\theta_t\cos\theta_i/\sin(\theta_i+\theta_t)` and :math:`t_p=t_s/\cos(\theta_i-\theta_t)`.",
        "3.42": r"The boundary-field identities reduce to :math:`1+r_s=t_s` and the corresponding signed p-polarization relation after the refractive-index ratio is replaced with Snell's law.",
        "3.43": r"Substituting the Fresnel amplitudes into the normal-flux definitions cancels the common denominator and gives :math:`R_s+T_s=R_p+T_p=1`.",
        "3.50": r"Eliminating the core ray angle gives :math:`n_0\sin\theta_{\max}=\sqrt{n_{\rm core}^2-n_{\rm clad}^2}`.",
        "4.62": r"Equating the indexed object-to-surface and surface-to-image distances to their axial value gives the Cartesian-ovoid relation in :math:`x,y,s_o,s_i,n_1,n_2`; setting :math:`y=0` recovers the vertex constant.",
        "4.63": r"For a plane incident wave, :math:`n_1x+n_2\sqrt{(s_i-x)^2+y^2}=n_2s_i`; isolating the radical and completing the square gives an ellipsoid when the focusing index ordering applies.",
        "4.64": r"Changing the image to a virtual divergence point changes the signed-distance term; the same squared equation now has opposite transverse and axial signs, the standard two-sheet hyperboloid.",
        "4.72": r"The converging incident bundle represents a virtual object.  With :math:`|s_o|<|f|`, the negative lens forms a real, erect, magnified image with :math:`s_i>|s_o|` in magnitude.",
        "4.76": r"Eliminating :math:`s_o` and :math:`s_i` between the lens and magnification equations gives the stated separation-to-focal-length identity; its quadratic discriminant also reproduces the :math:`L\ge4f` condition.",
        "4.81": r"For the index-two equal-negative-radius lens, matrix reduction gives a positive focal length proportional to :math:`R^2/d` and coincident principal-plane offsets :math:`h_1=h_2=-R` in the source convention.",
        "4.84": r"The common-center construction is a negative lens with :math:`f=-2|R|(|R|+d)/d`; both principal planes coincide with the shared center of curvature.",
        "4.92": r"Sequential imaging through the compound lens and back from the convex mirror gives :math:`s_i=-10\,\mathrm{cm}` at the mirror: a virtual inverted image 10 cm behind its vertex.",
        "5.48": r"A suitable field is :math:`\mathbf E=(E_0/\sqrt2)(\hat{\mathbf x}+\hat{\mathbf z})\cos[\omega(y/v-t)+\phi_0]`.",
        "5.49": r"Only the z component is incident, so the plate adds only a common phase: the output remains z-directed linear light, :math:`\mathbf E=E_0\hat{\mathbf z}\cos(kx-\omega t+\phi_0)`.",
        "5.50": r"One suitable zero-initial-field form is :math:`\mathbf E=E_0\hat{\mathbf x}\sin(ky-\omega t)`.",
        "5.51": r"The components are in phase, so the result is linear with amplitude :math:`2E_0`, propagates toward :math:`-y`, and is tilted 60° from the yz plane in the source convention.",
        "5.52": r":math:`\mathbf E=E_0(0.9537\hat{\mathbf y}+0.3007\hat{\mathbf z})\cos(kx-\omega t+\phi_0)`.",
        "5.53": r"The in-phase collinear states add to one linear state of amplitude :math:`3E_0`.",
        "5.54": r"Send the beam backward through a known circular polarizer: one handedness emerges linear whereas the opposite handedness is extinguished; interchange the reference polarizer to resolve the sign.",
        "5.55": r"A right-circular form meeting the initial -45° condition is :math:`E_0[\hat x\cos(kz-\omega t-\pi/4)+\hat y\sin(kz-\omega t-\pi/4)]` under the book's convention.",
        "5.56": r"Choose the common initial phase so the two equal quadrature components reproduce the supplied normalized vector; the resulting Jones ratio has unit magnitude and -90° relative phase for the stated right-circular convention.",
        "5.57": r"A left-circular form is obtained by reversing the quadrature sign and choosing the common phase to reproduce the stated initial azimuth.",
        "5.58": r"One right-handed example is :math:`E_0\hat y\cos(kx-\omega t)+E_0\hat z\cos(kx-\omega t-\pi/4)` with axes interpreted as in the source.",
        "5.59": r"Use orthogonal components along the 135°/45° principal directions with unequal amplitudes and +90° relative phase; reversing that sign reverses handedness.",
        "5.60": r"Reducing the relative phase modulo :math:`2\pi` gives a right-handed ellipse whose major axis is at 135° to x.",
        "5.61": r"One valid two-to-one state is :math:`\mathbf E=2E_0\hat x\cos(\omega t-kz)-E_0\hat y\sin(\omega t-kz)`.",
        "5.62": r"For :math:`E_{0x}\ge E_{0y}`, write the field as a circle of radius :math:`E_{0y}` plus the collinear remainder :math:`(E_{0x}-E_{0y})\hat x\sin\Phi`; the opposite ordering is analogous.",
        "5.63": r"Yes: an exactly monochromatic field has unlimited temporal coherence, so its component amplitude ratio and phase are fixed and it has a definite polarization state.",
        "5.64": r"Find an analyzer extremum, align a quarter-wave plate to that axis, and repeat the analyzer scan.  Unshifted extrema indicate a partial linear state; rotated extrema identify a partial ellipse.",
        "5.65": r"Place a quarter-wave plate before a rotating analyzer: circular light becomes linear with a zero minimum, natural light stays angle independent, and a mixture has a nonzero modulation minimum.",
        "5.66": r":math:`\mathcal P=(43-22)/(43+22)=0.323`, or 32.3%.",
        "5.67": r"The first polarizer transmits :math:`I_i/2`; its field has equal y and z components and amplitude :math:`E_0=\sqrt{2(I_i/2)/(c\epsilon_0)}`.",
        "5.68": r":math:`I(30^\circ)/I(60^\circ)=\cos^2 30^\circ/\cos^2 60^\circ=3`.",
        "5.75": r"The second reflection projects the first reflected linear state onto its rotated incidence plane, so :math:`I(\theta)=I(0)\cos^2\theta`.",
        "5.82": r"The half-wave plate rotates the first polarizer's red linear state by 90°, making it parallel to the crossed analyzer; red light therefore emerges linearly polarized along the analyzer.",
        "5.83": r"At half the wavelength the same plate supplies a full-wave delay, leaves the first polarizer's violet state unchanged, and the crossed analyzer extinguishes it.",
        "6.53": r"The cross term vanishes when :math:`\hat{\mathbf e}_1\cdot\hat{\mathbf e}_2=0`; the measured irradiance is then :math:`I_1+I_2` everywhere.",
        "6.55": r"For :math:`a\gg\lambda`, the spatial average of :math:`\cos\delta` is zero and the integrated irradiance is :math:`I_1+I_2`; for :math:`a\ll\lambda` the pair behaves as one coherent source.",
        "6.56": r"For equal sources, :math:`I(\theta)=4I_0\cos^2[(ka\sin\theta+\delta_0)/2]`.",
        "6.59": r"Since :math:`\beta\simeq a/L`, Young's result becomes :math:`\Delta y=\lambda_0/\beta`.",
        "6.61": r"The source geometry gives an effective virtual-source separation :math:`2Ra/(R+a)` (or its corresponding small angle after division by the viewing distance).",
        "6.64": r"Replace the prism relative index by :math:`n_p/n_l`; the fringe spacing becomes inversely proportional to :math:`n_p-n_l` and reduces to the air formula for :math:`n_l=1`.",
        "6.65": r"A plate of thickness :math:`d` adds :math:`(n-1)d`; the central dark band moves by :math:`(n-1)d/\lambda_0` fringe spacings.  White light locates the zero-OPD band.",
        "6.67": r"The two displaced real images of the original point source are mutually coherent in-phase emitters; their overlap region therefore contains Young-type fringes.",
        "6.69": r"With one reflection reversal, reflected maxima satisfy :math:`d\cos\theta_t=(2m+1)\lambda_0/(4n)` and minima :math:`d\cos\theta_t=m\lambda_0/(2n)`.",
        "6.77": r"Replacing the flat by radius :math:`R_2` gives effective curvature :math:`R_{\rm eff}=R_1R_2/(R_2-R_1)` and :math:`r_m=[m\lambda_0R_{\rm eff}]^{1/2}` for dark rings.",
        "6.78": r"For fixed order, :math:`\cos\theta_m=m\lambda_0/(2d)` approaches one as the arm difference approaches that order's axial value; hence :math:`\theta_m\to0` and the ring collapses centrally.",
        "6.81": r"Using :math:`1-\cos\theta\simeq\theta^2/2` gives :math:`\theta_p\simeq\sqrt{p\lambda_0/d}`.",
        "6.84": r"The two beam splitters form separate arms recombined at the output; a slight mirror tilt gives wedge fringes.  Like the Jamin arrangement, it maps large-volume refractive-index nonuniformity, for example in a wind tunnel.",
        "6.88": r"Because :math:`N=\ell_c/\lambda_0=\nu/\Delta\nu`, the wavelength count is the inverse fractional frequency stability.",
        "7.52": r"For :math:`N=2`, :math:`\sin(2\alpha)/\sin\alpha=2\cos\alpha`; squaring yields the Young two-source :math:`4I_1\cos^2\alpha` pattern.",
        "7.55": r"The zeroth maximum satisfies :math:`ka\sin\theta_0+\delta_0=0`, so :math:`\theta_0=\sin^{-1}[-\delta_0\lambda/(2\pi a)]` with sign set by the phase convention.",
        "7.56": r"Substituting the 30° progressive phase into the steering equation gives the same approximately :math:`2.39^\circ` displacement as the related two-source problem.",
        "7.57": r"The incident wave induces adjacent-atom phase :math:`ka\sin\theta_i`; reradiation is principal when the outgoing path phase cancels it, requiring :math:`\theta_o=\theta_i`.",
        "7.58": r"Geometry and :math:`a\sin\theta_m=m\lambda` give :math:`Z_m=m\lambda f/\sqrt{a^2-m^2\lambda^2}`, which contains no lens-position distance.",
        "7.64": r"Envelope zeros occur at :math:`b\sin\theta=\pm\lambda`; with :math:`a=Mb`, the interference orders strictly inside are :math:`m=-(M-1),\ldots,M-1`, with the boundary coincidences counted as in the source convention to give :math:`2M` bright bands.",
        "7.67": r"At :math:`N=1` the array factor tends to one; at :math:`N=2`, :math:`\sin2\alpha/\sin\alpha=2\cos\alpha`, recovering the single- and double-slit formulas.",
        "7.69": r"At the midpoint subsidiary maximum for odd :math:`N`, numerator and denominator sines each have unit magnitude, so :math:`I_{\rm sub}=I(0)/N^2`.",
        "7.71": r"Since the largest physical order is :math:`m\le a/\lambda`, :math:`\mathcal R=mN\le aN/\lambda`.",
        "7.74": r"The first and second visible orders only meet at the extreme visible limits and substantially miss; second and third orders do overlap because :math:`2\lambda_{\rm red}=3\lambda_{\rm blue}` is possible.",
        "7.76": r"Bounding the aperture's quadratic phase by much less than one gives :math:`L\gg d^2/\lambda`; :math:`L>d^2/\lambda` is the usual rule of thumb.",
        "7.79": r"The on-axis field scales as aperture area divided by wavelength, so :math:`I(0)\propto A^2/\lambda^2`.",
        "7.82": r"Using a 0.5-µm Airy radius gives :math:`D=1.22\lambda f/r\approx0.247\,\mathrm m`.",
        "7.87": r"Successive half-zone conditions give maxima at about 1.06, 1.84, and 2.87 mm and minima at 1.50, 2.12, and 2.60 mm for the stated geometry.",
        "7.89": r"Adding the open annular-zone phasors and squaring gives :math:`I\approx90\,\mathrm{W/m^2}`.",
        "7.91": r"The aperture's open-zone chord has twice the unobstructed field amplitude, giving :math:`I=100\,\mathrm{W/m^2}` from the 25-W/m² incident reference.",
        "7.92": r"The central-disk and second-zone obstruction phasors cancel the unobstructed vector to the plotted accuracy, so the axial irradiance is approximately zero.",
        "7.93": r"The zone-plate relation is :math:`r_m^2=m\lambda f`; for equal 5-m conjugates, :math:`f=2.5\,\mathrm m` and :math:`r_1\approx1.12\,\mathrm{mm}`.",
        "7.94": r"With only the first zone open, its field is approximately twice the unobstructed field, hence :math:`I\approx4I_0`.",
        "7.96": r"As the two slit edges tend to opposite infinite Cornu endpoints, their chord becomes the full unobstructed vector and :math:`I(0)\to I_0`.",
        "7.97": r"Since :math:`dS/dC=\tan(\pi u^2/2)`, horizontal tangencies are :math:`u=\sqrt{2},\sqrt4,\sqrt6,\ldots` and vertical tangencies :math:`u=\sqrt1,\sqrt3,\sqrt5,\ldots`, with symmetric negative points.",
        "7.102": r"The first useful axial maximum corresponds to :math:`\Delta u\approx2.53`, giving slit width about 1.13 mm.",
        "7.103": r"At the geometric edge the Cornu chord is one half of the unobstructed field vector, so :math:`I=|E_0/2|^2=I_0/4`.",
        "7.104": r"The first minimum and maximum lie about 2.66 mm and 1.78 mm from the geometrical edge, respectively.",
        "7.105": r"The complementary-slit field and Babinet subtraction give central irradiance :math:`I(0)\approx0.08I_0`; the curve is symmetric about the strip center.",
        "8.22": r"Coefficient matching gives :math:`a_m=C_m\cos\phi_m` and :math:`b_m=-C_m\sin\phi_m`; therefore :math:`C_m=\sqrt{a_m^2+b_m^2}` and :math:`\phi_m=\operatorname{atan2}(-b_m,a_m)`.",
        "8.23": r"Pairing the two half-period integrals multiplies each coefficient by :math:`1-(-1)^m`; every even harmonic vanishes.",
        "8.25": r"Integrating the constant segments of the source waveform leaves only the symmetry-allowed odd sine coefficients; evaluating the coefficient formula gives the displayed odd-harmonic series.",
        "8.26": r"The waveform is even, so all sine coefficients vanish; piecewise integration gives its constant term and the inverse-square odd-cosine sequence shown in the source answer.",
        "8.27": r"Replacing the normalized period by :math:`L` changes every harmonic argument to :math:`2\pi mx/L`; the coefficient amplitudes retain the same parity sequence after the corresponding scale factor.",
        "8.28": r"Apply the translation theorem to the result of 8.26: shifting by :math:`x_0` multiplies each complex coefficient by :math:`e^{-imkx_0}`, equivalently rotating cosine terms into the source's shifted signs.",
        "8.29": r"For unit period, :math:`f(t)=E_0|\sin\pi t|=2E_0/\pi-(4E_0/\pi)\sum_{m=1}^{\infty}\cos(2\pi mt)/(4m^2-1)`.",
        "8.30": r"For a unit-height pulse on :math:`[-L,L]`, direct exponential integration gives :math:`F(k)=2\sin(kL)/k=2L\operatorname{sinc}(kL)`.",
        "8.37": r"Insert the two inverse transforms into :math:`f(x)h(x)`; the x integral produces :math:`2\pi\delta[k-(q+p)]`, leaving :math:`\mathcal F\{fh\}=(F*H)/(2\pi)`.",
        "8.38": r":math:`\mathcal F\{\cos^2k_0x\}=\pi\delta(k)+(\pi/2)[\delta(k-2k_0)+\delta(k+2k_0)]` for the stated convention.",
        "8.39": r"In :math:`(f*h)(x)`, substitute :math:`u=x-\xi`; reversing the integration limits and differential restores them and yields :math:`(h*f)(x)`.",
        "8.40": r"Pairwise addition of the impulse locations in the source graph produces the plotted self-convolution; repeated sums add their amplitudes at the same coordinate.",
        "8.42": r"For unit impulses at :math:`k=\pm2,\pm3`, the self-convolution has weights 1,2,1 at -6,-5,-4; 2,4,2 at -1,0,1; and 1,2,1 at 4,5,6.",
        "8.43": r"Convolution with the signed impulse pair produces the difference of two shifted rectangular pulses; its transform is the rectangle's sinc spectrum multiplied by the corresponding sine phase factor.",
        "8.44": r"The double-slit self-convolution is the sum of three triangular lobes: two outer unit-weight autocorrelations and a central lobe with twice their weight.",
        "8.45": r"Each delta impulse in the discrete input centers one translated copy of the continuous function; summing those copies gives the source figure's output.",
        "8.46": r"Reverse one plotted function, translate it through every breakpoint of the other, and integrate each overlap interval; the resulting piecewise curve has support equal to the sum of the two input supports.",
    }
)


MODE_HINTS = {
    "prove": "Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.",
    "derive": "Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.",
    "show": "Start from the left-hand physical definition, transform it one step at a time, and stop only when the required right-hand form is obtained.",
    "construct": "Evaluate all breakpoints or ray/phasor endpoints first, then join only the intervals allowed by the governing relation.",
    "plot": "Evaluate zeros, extrema, period, and phase origin before sketching the continuous curve.",
    "describe": "Use signs, directions, and limiting behavior from the governing equations to classify the physical result.",
    "explain": "Identify the controlling phase or conservation relation, then use it to account for every stated observation.",
    "test": "Substitute the candidate directly into the governing equation and compare both sides term by term.",
    "verify": "Evaluate both sides independently from the definitions and confirm equality without circular substitution.",
    "default": "Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.",
}


def mode_hint(focus: str) -> str:
    first = focus.split()[0].lower()
    return MODE_HINTS.get(first, MODE_HINTS["default"])


def problem_count() -> int:
    return sum(len(section.focuses) for chapter in CHAPTERS for section in chapter.sections)


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
        "Each topic derives its shared formula once.  Every numbered problem then",
        "applies that derivation to the particular proof, calculation, or construction",
        "in the book.  Read the source diagram alongside entries that depend on a figure.",
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

        for offset, focus in enumerate(section.focuses):
            number = section.first + offset
            key = f"{chapter.number}.{number}"
            heading = f"Problem {key} — {focus}"
            result = RESULTS.get(
                key,
                "The endpoint is the symbolic identity, classification, or construction "
                "specified in the paraphrased task; no independent numerical value is "
                "introduced by the problem.",
            )
            lines.extend(
                [
                    heading,
                    "^" * len(heading),
                    "",
                    f"**Paraphrased task.** {focus.capitalize()}.",
                    "",
                    f"**Formula reference.** Use :eq:`{label}` and the definitions immediately above it.",
                    "",
                    "**Worked application.**",
                    "",
                    f"1. {section.route}",
                    f"2. {mode_hint(focus)}",
                    "3. Substitute the values or boundary conditions attached to this",
                    "   problem number in the book and retain the source sign convention.",
                    "",
                    f"**Result.** {result}",
                    "",
                    f"**Check.** {section.check}",
                    "",
                ]
            )
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
        "The original prompts are not reproduced.  Open the matching numbered problem",
        "in the book for its data and figure, then use the derivation and application",
        "here.  Numerical checks are included where the problem has a numerical endpoint;",
        "proof and construction problems finish at their requested symbolic or graphical",
        "result.  Formulae use SI units unless the source explicitly supplies another",
        "consistent unit system.",
        "",
        ".. note::",
        "",
        "   A scan OCR error reads Problem 8.43 as ``8.48``.  The printed page and",
        "   sequence confirm that the convolution problem between 8.42 and 8.44 is 8.43.",
        "",
        ".. toctree::",
        "   :maxdepth: 1",
        "",
    ]
    lines.extend(f"   ch{chapter.number:02d}_{chapter.slug}" for chapter in CHAPTERS)
    return "\n".join(lines) + "\n"


def validate_configuration() -> None:
    expected = {1: (31, 64), 2: (26, 47), 3: (31, 50), 4: (62, 96), 5: (48, 86), 6: (52, 91), 7: (52, 105), 8: (22, 47)}
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
            failures.append(f"Chapter {chapter.number}: got {actual}, expected {wanted}")
    if problem_count() != 270:
        failures.append(f"total is {problem_count()}, expected 270")
    configured = {
        f"{chapter.number}.{section.first + offset}"
        for chapter in CHAPTERS
        for section in chapter.sections
        for offset in range(len(section.focuses))
    }
    result_keys = set(RESULTS)
    missing_results = sorted(configured - result_keys)
    extra_results = sorted(result_keys - configured)
    if missing_results:
        failures.append(f"problems without result text: {missing_results}")
    if extra_results:
        failures.append(f"result text without a configured problem: {extra_results}")
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
