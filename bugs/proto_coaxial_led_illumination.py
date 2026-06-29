"""Feasibility prototype: coaxial (through-the-beam-splitter) area-LED illumination
and the 2 dark edges it produces on the camera image.

PRODUCTION CASE (user, MV-150 / 25 MP / 39x39 mm FOV)
-----------------------------------------------------
A 55x78 mm area LED shines from the SIDE -> reflects off the 45 deg diagonal of a
55x55x78 mm beam-splitter cube -> down to the FOV -> object reflects back up -> through
the BS -> imaging lens + camera. The 25 MP image shows 2 DARK EDGES on one axis and is
uniform on the other. The user's read: "the 55 mm illumination is insufficient to cover
both edges, while the other 2 edges landed on 78 mm uniformly illuminated."

WHAT THIS SCRIPT PROVES
-----------------------
The dark edges are an ILLUMINATION-COVERAGE effect (the beam splitter / area-LED aperture
is the limiting stop, NOT the imaging lens). We do NOT need the imaging lens to reproduce
them: the irradiance landing on the FOV plane already carries the 2 dark bands. This is the
exact quantity the app's "relative illumination" analysis bins (source rays -> target plane
-> 2-D irradiance map), so reproducing it here de-risks wiring it into that analysis.

GEOMETRY (the 45 deg fold is UNFOLDED)
--------------------------------------
Reflecting the real side LED in the 45 deg BS diagonal gives a VIRTUAL area source sitting
ON-AXIS directly above the FOV -- optically identical to the folded real LED. So we model
the simpler unfolded stack (all along the optical axis +z):

    z = z_src : virtual W_x(fold) x W_y mm Lambertian area LED, emitting downward (-z)
    z = z_ap  : beam-splitter EXIT aperture (cube bottom face)   -- the limiting stop
    z = 0     : FOV plane, 39 x 39 mm (we bin a larger window to see the roll-off)

WHY ONE AXIS GOES DARK (the umbra-pinch)
----------------------------------------
For a source width S over an aperture width A, the fully-lit (umbra) half-width on the FOV is
    umbra/2 = A/2 - (S/2 - A/2) * z_ap/(z_src - z_ap).
On the 78 mm axis the lit region runs well past +/-19.5 mm -> uniform. On the fold (55 mm)
axis the effective illumination only just reaches the FOV (the user's "55 mm is insufficient";
heuristically 55*cos45 ~ 38.9 mm ~ the 39 mm FOV) so the FOV edges sit in the PENUMBRA roll-off
-> the 2 dark edges. Make the fold-axis illumination narrower / the working distance longer and
the dark edges deepen -- that is the single knob the real LED->BS->FOV distances set.

DISTANCES / WIDTHS BELOW ARE PLACEHOLDERS. The dark-edge *axis* is physics; the *depth* needs
the real LED->BS and BS->FOV working distances + the LED divergence.

Run:  .devenv/state/venv/bin/python bugs/proto_coaxial_led_illumination.py
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FOV = 39.0          # square FOV side (mm)
WINDOW = 30.0       # bin +/-WINDOW mm so the roll-off outside the FOV is visible
BINS = 120
N_RAYS = 6_000_000


@dataclass
class Scene:
    name: str
    led_x: float        # virtual-source width on the fold (55 mm) axis -- the dark-edge axis
    led_y: float        # virtual-source width on the perpendicular (78 mm) axis
    aper_x: float       # BS exit-face aperture, fold axis
    aper_y: float       # BS exit-face aperture, perpendicular axis
    z_ap: float         # cube exit face above the FOV (~ working distance)
    z_src: float        # virtual LED plane above the FOV
    cone_deg: float | None = None   # emission half-angle; None = full Lambertian hemisphere


def simulate(s: Scene, n_rays: int = N_RAYS, seed: int = 0):
    """Monte-Carlo Lambertian transfer source -> aperture -> FOV. Returns (E, xe, ye)."""
    rng = np.random.default_rng(seed)
    x0 = rng.uniform(-s.led_x / 2, s.led_x / 2, n_rays)
    y0 = rng.uniform(-s.led_y / 2, s.led_y / 2, n_rays)

    # cosine-weighted (Lambertian) directions into the -z hemisphere
    u1 = rng.uniform(0.0, 1.0, n_rays)
    if s.cone_deg is not None:                      # restrict the lobe to a cone (directional LED)
        cos_max = np.cos(np.radians(s.cone_deg))
        u1 *= (1.0 - cos_max ** 2)                  # cos(theta) in [cos_max, 1] -> sin^2 in [0, 1-cos_max^2]
    np.clip(u1, 0.0, 1.0 - 1e-9, out=u1)            # avoid grazing rays with |dz|->0
    phi = rng.uniform(0.0, 2.0 * np.pi, n_rays)
    r = np.sqrt(u1)
    dx = r * np.cos(phi)
    dy = r * np.sin(phi)
    inv_abs_dz = 1.0 / np.sqrt(1.0 - u1)            # 1/|dz|, dz = -sqrt(1-u1)

    t_ap = (s.z_src - s.z_ap) * inv_abs_dz          # to the BS exit face (limiting stop)
    x_ap = x0 + t_ap * dx
    y_ap = y0 + t_ap * dy
    through = (np.abs(x_ap) <= s.aper_x / 2) & (np.abs(y_ap) <= s.aper_y / 2)

    t_f = s.z_src * inv_abs_dz                       # survivors to the FOV plane
    x_f = x0[through] + t_f[through] * dx[through]
    y_f = y0[through] + t_f[through] * dy[through]

    counts, xe, ye = np.histogram2d(
        x_f, y_f, bins=BINS, range=[[-WINDOW, WINDOW], [-WINDOW, WINDOW]])
    return counts.T, xe, ye                          # axis-0 = y, axis-1 = x


def _centre(E, xe, ye, half=2.5):
    xc, yc = 0.5 * (xe[:-1] + xe[1:]), 0.5 * (ye[:-1] + ye[1:])
    return float(E[np.ix_(np.abs(yc) <= half, np.abs(xc) <= half)].mean())


def _profile(E, xe, ye, axis, half=2.5):
    xc, yc = 0.5 * (xe[:-1] + xe[1:]), 0.5 * (ye[:-1] + ye[1:])
    if axis == "x":
        return xc, E[np.abs(yc) <= half, :].mean(axis=0)
    return yc, E[:, np.abs(xc) <= half].mean(axis=1)


def _ascii(E, xe, ye, cols=58):
    ramp = " .:-=+*#%@"
    norm = E / max(_centre(E, xe, ye), 1e-9)
    ny, nx = norm.shape
    ys, xs = max(1, ny // (cols // 2)), max(1, nx // cols)
    rows = []
    for iy in range(0, ny, ys):
        rows.append("".join(
            ramp[int(np.clip(norm[iy:iy + ys, ix:ix + xs].mean(), 0, 1) * (len(ramp) - 1))]
            for ix in range(0, nx, xs)))
    return "\n".join(reversed(rows))


def report(s: Scene, save_png: bool = False):
    E, xe, ye = simulate(s)
    c = _centre(E, xe, ye)
    xc, xp = _profile(E, xe, ye, "x"); xp = xp / max(c, 1e-9)
    yc, yp = _profile(E, xe, ye, "y"); yp = yp / max(c, 1e-9)
    at = lambda co, p, v: float(p[np.argmin(np.abs(co - v))])
    h = FOV / 2.0

    print("=" * 72)
    print(s.name)
    print(f"  LED {s.led_x:g}x{s.led_y:g} | BS exit {s.aper_x:g}x{s.aper_y:g} "
          f"| z_src={s.z_src:g} z_ap={s.z_ap:g} | cone="
          f"{('Lambertian' if s.cone_deg is None else str(s.cone_deg) + 'deg')}")
    print("=" * 72)
    print(_ascii(E, xe, ye))
    print("-" * 72)
    xedge = 0.5 * (at(xc, xp, -h) + at(xc, xp, h))
    yedge = 0.5 * (at(yc, yp, -h) + at(yc, yp, h))
    print(f"  FOV-edge irradiance (centre=1.00):  fold/55 axis = {xedge:.2f}   "
          f"perp/78 axis = {yedge:.2f}   ratio = {xedge / max(yedge, 1e-9):.2f}")
    print("  fold-axis (x) profile, 5 mm steps:  " +
          "  ".join(f"{v:+.0f}:{at(xc, xp, v):.2f}" for v in range(-25, 26, 5)))
    print("  perp-axis (y) profile, 5 mm steps:  " +
          "  ".join(f"{v:+.0f}:{at(yc, yp, v):.2f}" for v in range(-25, 26, 5)))
    if save_png:
        _save_png(s, E, xe, ye, c, xc, xp, yc, yp)
    return E, xe, ye


def _save_png(s, E, xe, ye, c, xc, xp, yc, yp):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        print(f"  (png skipped: {exc!r})")
        return
    h = FOV / 2.0
    fig, (axm, axp) = plt.subplots(1, 2, figsize=(11, 4.6))
    im = axm.imshow(E / max(c, 1e-9), origin="lower", cmap="inferno", vmin=0, vmax=1.05,
                    extent=[xe[0], xe[-1], ye[0], ye[-1]])
    axm.add_patch(plt.Rectangle((-h, -h), FOV, FOV, fill=False, ec="cyan", lw=1.5, ls="--"))
    axm.set_title("FOV-plane irradiance (cyan = 39x39 FOV)")
    axm.set_xlabel("x  fold / 55 mm axis  [mm]"); axm.set_ylabel("y  78 mm axis  [mm]")
    fig.colorbar(im, ax=axm, shrink=0.85, label="relative irradiance")
    axp.plot(xc, xp, color="tab:red", label="fold / 55 mm axis")
    axp.plot(yc, yp, color="tab:blue", label="78 mm axis")
    axp.axvspan(-h, h, color="0.9"); axp.axvline(-h, color="0.6", lw=0.8); axp.axvline(h, color="0.6", lw=0.8)
    axp.set_ylim(0, 1.1); axp.set_xlabel("position [mm]"); axp.set_ylabel("relative irradiance")
    axp.set_title("centre-line profiles"); axp.legend(loc="lower center", fontsize=8)
    fig.suptitle(s.name, fontsize=9)
    fig.tight_layout()
    out = "bugs/proto_coaxial_led_illumination.png"
    fig.savefig(out, dpi=110)
    print(f"  saved {out}")


# The fold (55 mm) axis under-fills because the 55 mm LED OVERFILLS its limiting stop -- the
# beam-splitter exit foreshortened to ~55*cos45 ~ 39 mm. Source(55) > stop(39) makes the lit
# (umbra) region PINCH below the 39 mm FOV with distance -> the FOV edges fall in the penumbra
# = the 2 dark edges. The 78 mm axis: source=stop=78 -> lit past +/-19.5 mm -> uniform.
SCENARIOS = [
    Scene("(1) Both axes lit by the full 55x78 cube faces  -> only a soft roll-off, no dark edges",
          led_x=55, led_y=78, aper_x=55, aper_y=78, z_ap=40, z_src=95),
    Scene("(2) 55 mm LED overfills the ~39 mm foreshortened fold stop  -> 2 dark edges on the 55 axis",
          led_x=55, led_y=78, aper_x=39, aper_y=78, z_ap=55, z_src=130),
    Scene("(3) Same as (2) but a directional +/-35deg LED  -> sharper dark edges",
          led_x=55, led_y=78, aper_x=39, aper_y=78, z_ap=55, z_src=130, cone_deg=35),
]


def main() -> int:
    for i, sc in enumerate(SCENARIOS):
        report(sc, save_png=(i == len(SCENARIOS) - 1))   # png for the last (sharpest) case
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
