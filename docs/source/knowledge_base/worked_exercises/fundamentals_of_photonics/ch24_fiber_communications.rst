Chapter 24: Optical Fiber Communications
=========================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 24.

This chapter contains end-of-chapter problems but no boxed in-text exercises.

End-of-chapter problems
-----------------------

.. rubric:: Problem 24.1-1 — Assessing fiber-system claims

(a) 1300 nm usually beats 870 nm for silica loss and modal bandwidth, but cheap
short plastic/multimode links can favor 870 nm.  (b) 1550 nm has the lowest
silica loss and supports EDFAs, while 1300 nm can have lower dispersion in
ordinary fiber and cheaper components.  (c) Single-mode fiber removes modal
dispersion; its advantage is not inherently a lower material attenuation.
(d) Material and waveguide dispersion may cancel near 1312 nm, but source
linewidth, polarization-mode dispersion, and higher-order dispersion remain.
(e) Compound semiconductors are needed for efficient 1.3/1.55-micrometre
sources, not for passive fiber, and silicon detectors work near 870 nm.
(f) APDs add excess multiplication noise, yet their internal gain can overcome
receiver circuit noise and improve sensitivity.  Thus none of the six absolute
claims is universally true.

.. rubric:: Problem 24.1-2 — Choosing compatible components

(a) Use a narrow-linewidth 1550-nm InGaAsP laser, single-mode low-loss (often
dispersion-managed) silica fiber, EDFAs, and an InGaAs p-i-n or APD receiver.
(b) A visible/870-nm LED, plastic or large-core multimode fiber, and silicon
p-i-n diode minimize cost; no amplifier is needed.  (c) A common 500-Mb/s LAN
choice is an 850-nm VCSEL, graded-index multimode fiber, and silicon p-i-n
receiver.  (d) For temperature margin over 1 km, choose a stabilized 1310-nm
InGaAsP laser, silica fiber operated near its zero-dispersion band, and an
InGaAs p-i-n receiver; the laser's narrow spectrum avoids temperature-driven
LED linewidth penalties.

.. rubric:: Problem 24.2-1 — Plastic-fiber distance

The 1-mW source is 0 dBm.  After two 3-dB couplers, the fiber may consume
:math:`0-6-(-20)=14` dB.  At 0.5 dB/m,
:math:`\boxed{L_{max}=28\ \mathrm m}`.

.. rubric:: Problem 24.2-2 — LED-link distance with two receivers

Photon-per-bit sensitivity converts through
:math:`P_r=N_ph(hc/\lambda)R_b`.  At 10 Mb/s the p-i-n value is
:math:`\boxed{-49.42\ \mathrm{dBm}}`; its loss budget after 4-dB couplers and
6-dB margin permits six whole 1-km segments (21 dB fiber plus five dB of
connectors), so :math:`\boxed{L=6\ \mathrm{km}}`.  The APD value is
:math:`\boxed{-65.45\ \mathrm{dBm}}` and similarly permits
:math:`\boxed{L=10\ \mathrm{km}}`.

.. rubric:: Problem 24.2-3 — Attenuation-limited bit rate

The 50-km fiber, fixed losses, and margin consume
:math:`10+8+6=24` dB, leaving :math:`7.962\ \mu\mathrm W`.  Dividing by 1000
photon energies per bit at 1550 nm gives
:math:`\boxed{R_b=62.1\ \mathrm{Gb/s}}` at BER :math:`10^{-9}`.  Under the
ideal Poisson scaling, changing BER to :math:`10^{-11}` multiplies the photon
requirement by
:math:`\ln(1/2\times10^{-11})/\ln(1/2\times10^{-9})=1.230`, giving
:math:`\boxed{50.5\ \mathrm{Gb/s}}`.

.. rubric:: Problem 24.2-4 — Analog APD link

The sinusoidal signal mean square is
:math:`(G\mathcal RmP)^2/2`; APD shot-noise variance is
:math:`2eBG^2F\mathcal RP`.  Their ratio gives

.. math::

   P_{min}={4eBF\,\mathrm{SNR}\over m^2\mathcal R}
   =\boxed{2.563\ \mu\mathrm W}=-25.91\ \mathrm{dBm}.

Internal gain cancels in this photon-noise-limited case.  The 100-microwatt
source supplies 15.91 dB of fiber loss, hence
:math:`\boxed{L=6.36\ \mathrm{km}}`.

.. rubric:: Problem 24.2-5 — Dispersion time budget

Ordinary fiber broadens by
:math:`t_f=D_\lambda L\Delta\lambda=340` ps.  The fiber-only criterion gives
:math:`R_b\le0.25/t_f=\boxed{0.735\ \mathrm{Gb/s}}`.  Root-sum-square with
20-ps source and 100-ps receiver gives :math:`t_s=355.0` ps and the system
criterion :math:`R_b\le0.70/t_s=\boxed{1.97\ \mathrm{Gb/s}}`.  With
:math:`D_\lambda=1`, :math:`t_f=20` ps and :math:`t_s=103.9` ps, giving
:math:`\boxed{12.5\ \mathrm{Gb/s}}` and :math:`\boxed{6.74\ \mathrm{Gb/s}}`,
respectively.

.. rubric:: Problem 24.3-1 — WDM channels in C and O bands

Use frequency, not wavelength, span:
:math:`\Delta\nu=c(1/\lambda_{min}-1/\lambda_{max})`.  The C band spans
4.382 THz and the O band 17.495 THz.  Counting both endpoint slots gives
:math:`\boxed{\lfloor\Delta\nu/75\ \mathrm{GHz}\rfloor+1=59}` C-band and
:math:`\boxed{234}` O-band carriers (58 and 233 are the corresponding numbers
of 75-GHz intervals).

.. rubric:: Problem 24.3-2 — Broadcast-star node limit

A source-to-receiver route traverses two 2-km fiber legs (1.2 dB), two 1-dB
connector losses, 3-dB star excess loss, and a 5-dB margin.  From a 0-dBm
source to a -35-dBm receiver,
:math:`10\log_{10}N\le35-1.2-2-3-5=23.8` dB.  Therefore
:math:`N\le239.9` and :math:`\boxed{N_{max}=239}` whole nodes.  If the stated
1-dB connector loss is intended for the entire end-to-end route rather than
per star leg, the same budget gives 301 nodes.

.. rubric:: Problem 24.3-3 — Six-channel four-node ring

Regard the six wavelengths as the six edges of a complete graph on four
nodes; each node drops its three incident edges.  With node 1 assigned
:math:`\{\lambda_1,\lambda_2,\lambda_3\}`, a valid allocation is

.. math::

   \boxed{N_2=\{\lambda_1,\lambda_4,\lambda_5\},\quad
   N_3=\{\lambda_2,\lambda_4,\lambda_6\},\quad
   N_4=\{\lambda_3,\lambda_5,\lambda_6\}}.

Every node pair shares exactly one channel and no third node drops that
channel, so intermediate nodes pass it through.
