(() => {
    "use strict";

    const Q = 1.602176634e-19;
    const KB_EV_K = 8.617333262145e-5;
    const HC_EV_UM = 1.2398419843320026;
    const COLORS = ["#7b1e24", "#287271", "#c18b2e", "#345995"];

    const linearSpace = (start, stop, count = 301) =>
        Array.from(
            { length: count },
            (_, index) => start + ((stop - start) * index) / (count - 1),
        );

    const clampExponent = (value) => Math.max(-745, Math.min(700, value));

    const engineering = (value, digits = 3) => {
        if (value === 0) return "0";
        const absolute = Math.abs(value);
        if (absolute >= 1e4 || absolute < 1e-2) {
            return value.toExponential(digits - 1);
        }
        return Number(value.toPrecision(digits)).toString();
    };

    const POWER_UNITS = [
        [30, "QW"],
        [27, "RW"],
        [24, "YW"],
        [21, "ZW"],
        [18, "EW"],
        [15, "PW"],
        [12, "TW"],
        [9, "GW"],
        [6, "MW"],
        [3, "kW"],
        [0, "W"],
        [-3, "mW"],
        [-6, "uW"],
        [-9, "nW"],
        [-12, "pW"],
    ];

    const readableNumber = (value) => {
        const absolute = Math.abs(value);
        const namedScales = [
            [1e12, "trillion"],
            [1e9, "billion"],
            [1e6, "million"],
        ];
        const scale = namedScales.find(([threshold]) => absolute >= threshold);
        if (scale) {
            return `${new Intl.NumberFormat("en-US", {
                maximumSignificantDigits: 3,
            }).format(value / scale[0])} ${scale[1]}`;
        }
        return new Intl.NumberFormat("en-US", {
            maximumSignificantDigits: 3,
            useGrouping: true,
        }).format(value);
    };

    // Format both normal and extreme powers without 1e+N notation. The 2022
    // SI prefixes ronna (R) and quetta (Q) cover the full slider range.
    const powerLogLabel = (log10PowerW) => {
        if (log10PowerW === -Infinity) return "0 W";
        if (!Number.isFinite(log10PowerW)) return "beyond numeric range";
        const [exponent, unit] =
            POWER_UNITS.find(([candidate]) => log10PowerW >= candidate) ||
            POWER_UNITS[POWER_UNITS.length - 1];
        const scaled = 10 ** (log10PowerW - exponent);
        if (!Number.isFinite(scaled) || scaled >= 1e15) {
            return `more than 999 trillion ${unit}`;
        }
        return `${readableNumber(scaled)} ${unit}`;
    };

    const powerLabel = (powerW) => {
        if (powerW === 0) return "0 W";
        const sign = powerW < 0 ? "-" : "";
        return `${sign}${powerLogLabel(Math.log10(Math.abs(powerW)))}`;
    };

    // The "Source power" control's log10 bounds, shared with the plot frame below so raising
    // the power LIFTS the curve inside a fixed window instead of rescaling the window with it
    // (bugs/0481: an autoscaled frame made a four-decade slider produce no visible change).
    const SILICON_SOURCE_LOG_MIN = -3;
    const SILICON_SOURCE_LOG_MAX = 1;

    // Intrinsic crystalline silicon at 300 K, Green (2008), Table 1.
    const GREEN_SILICON_WAVELENGTH_NM = linearSpace(900, 1300, 41);
    const GREEN_SILICON_ALPHA_CM_INV = [
        303, 271, 240, 209, 183, 156, 134, 113, 96, 79, 64, 51.1,
        39.9, 30.2, 22.6, 16.3, 11.1, 8, 6.2, 4.7, 3.5, 2.7, 2,
        1.5, 1, 0.68, 0.42, 0.22, 6.5e-2, 3.6e-2, 2.2e-2, 1.3e-2,
        8.2e-3, 4.7e-3, 2.4e-3, 1e-3, 3.6e-4, 2e-4, 1.2e-4,
        7.1e-5, 4.5e-5,
    ];
    const GREEN_SILICON_INDEX = [
        3.614, 3.609, 3.604, 3.6, 3.595, 3.591, 3.587, 3.583,
        3.579, 3.575, 3.572, 3.568, 3.565, 3.562, 3.559, 3.556,
        3.553, 3.55, 3.547, 3.545, 3.542, 3.54, 3.537, 3.535,
        3.532, 3.53, 3.528, 3.526, 3.524, 3.522, 3.52, 3.518,
        3.517, 3.515, 3.513, 3.511, 3.509, 3.508, 3.506, 3.505,
        3.503,
    ];

    const control = (
        key,
        label,
        min,
        max,
        step,
        value,
        display = (item) => engineering(item),
    ) => ({ key, label, min, max, step, value, display });

    const MODES = {
        carrier: {
            label: "Carrier profile (Eq. 3.11)",
            note:
                "The second-order diffusion equation produces an exponential spatial profile. " +
                "The far-field value is G_L tau_e and the decay scale is L_e.",
            controls: [
                control("D", "Diffusion coefficient D_e", 5, 80, 1, 25, (v) => `${v} cm2/s`),
                control("tau", "Lifetime tau_e", -2, 2, 0.05, 0, (v) => `${engineering(10 ** v)} us`),
                control("n0", "Junction excess log10(delta n)", 10, 16, 0.1, 14, (v) => `10^${v.toFixed(1)} cm-3`),
                control("G", "Generation log10(G_L)", 10, 20, 0.1, 18, (v) => `10^${v.toFixed(1)} cm-3 s-1`),
            ],
            calculate: carrierProfile,
        },
        bands: {
            label: "Junction energy bands (Fig. 3.1)",
            note:
                "A smooth depletion-region approximation shows the built-in potential. " +
                "The flat Fermi level is the equilibrium condition for zero net current.",
            controls: [
                control("vbi", "Built-in voltage V_Bi", 0.2, 1.4, 0.01, 0.72, (v) => `${v.toFixed(2)} V`),
                control("width", "Depletion width", 0.2, 4.0, 0.05, 1.2, (v) => `${v.toFixed(2)} um`),
                control("eg", "Band gap E_g", 0.5, 2.0, 0.01, 1.12, (v) => `${v.toFixed(2)} eV`),
            ],
            calculate: junctionBands,
        },
        iv: {
            label: "Photodiode I-V family (Figs. 3.2-3.4)",
            note:
                "Equation 3.14 shifts the dark diode curve downward by a voltage-independent " +
                "photocurrent. Figure 3.4 is measured; this display remains an ideality-factor model.",
            controls: [
                control("logIs", "Saturation current log10(I_s)", -15, -9, 0.1, -12, (v) => `10^${v.toFixed(1)} A`),
                control("logIph", "Base photocurrent log10(I_ph)", -13, -9, 0.1, -11, (v) => `10^${v.toFixed(1)} A`),
                control("temperature", "Temperature", 220, 380, 1, 300, (v) => `${v} K`),
                control("ideality", "Ideality factor n", 1, 3, 0.02, 1.4, (v) => v.toFixed(2)),
                control("vmax", "Forward voltage window", 0.05, 0.6, 0.01, 0.22, (v) => `${v.toFixed(2)} V`),
            ],
            calculate: ivFamily,
        },
        led: {
            label: "LED semilog I-V (Fig. 3.5)",
            note:
                "On semilog axes, the exponential region of Equation 3.16 is a straight line. " +
                "Increasing n reduces its slope.",
            controls: [
                control("logIs", "Saturation current log10(I_s)", -18, -10, 0.1, -14, (v) => `10^${v.toFixed(1)} A`),
                control("temperature", "Temperature", 220, 380, 1, 300, (v) => `${v} K`),
                control("ideality", "Ideality factor n", 1, 3, 0.02, 1.38, (v) => v.toFixed(2)),
                control("area", "Junction area", -4, 0, 0.1, -2, (v) => `10^${v.toFixed(1)} cm2`),
            ],
            calculate: ledSemilog,
        },
        spectral: {
            label: "Ideal spectral cutoff (Fig. 3.6)",
            note:
                "The ideal detector responds only when photon energy is at least E_g. " +
                "The wavelength cutoff is lambda_c = 1.23984 / E_g.",
            controls: [
                control("eg", "Band gap E_g", 0.5, 3.2, 0.01, 1.12, (v) => `${v.toFixed(2)} eV`),
            ],
            calculate: spectralCutoff,
        },
        measured: {
            label: "Rounded detector response (Fig. 3.7)",
            note:
                "Qualitative only: two smooth absorption edges mimic the trend of a real " +
                "filtered detector. No points are digitized from the measured book curve.",
            controls: [
                control("shortEdge", "Filter edge", 0.7, 1.3, 0.01, 1.05, (v) => `${v.toFixed(2)} um`),
                control("eg", "Detector band gap", 0.5, 1.2, 0.01, 0.74, (v) => `${v.toFixed(2)} eV`),
                control("peak", "Peak efficiency", 0.1, 1.0, 0.01, 0.65, (v) => `${Math.round(v * 100)}%`),
                control("edgeWidth", "Edge rounding", 0.005, 0.15, 0.005, 0.035, (v) => `${v.toFixed(3)} um`),
            ],
            calculate: measuredLikeResponse,
        },
        absorption: {
            label: "Absorption with depth (Fig. 3.8)",
            note:
                "Equation 3.22 is Beer-Lambert absorption. At one absorption length, " +
                "x = 1 / alpha, the remaining intensity is 1/e.",
            controls: [
                control("logAlpha", "Absorption coefficient log10(alpha)", 1, 5, 0.05, 2, (v) => `10^${v.toFixed(2)} cm-1`),
                control("depths", "Displayed absorption lengths", 1, 8, 0.1, 5, (v) => v.toFixed(1)),
            ],
            calculate: absorptionCurve,
        },
        siliconPower: {
            label: "Silicon power + surface reflection (Sec. 3.4.1)",
            note:
                "Both curves obey Equation 3.22. The surface-reflection curve first loses " +
                "the normal-incidence Fresnel fraction R, then undergoes the same silicon " +
                "bulk absorption. Power and intensity have the same depth dependence for " +
                "a beam of constant area. Source power does NOT change the decay length " +
                "1/alpha -- that is the material's, and the fractional profile is identical " +
                "at every power. What power moves is how deep the beam stays above an " +
                "absolute level: the crossing of the detection floor slides ln(10)/alpha " +
                "deeper per decade, which is why the depth axis follows it.",
            controls: [
                control(
                    "logPower",
                    "Source power",
                    SILICON_SOURCE_LOG_MIN,
                    SILICON_SOURCE_LOG_MAX,
                    0.02,
                    -1,
                    (v) => powerLabel(10 ** v),
                ),
                control("logFloor", "Detection floor", -12, -3, 0.05, -9, (v) => powerLabel(10 ** v)),
                control("logAlpha", "Silicon log10(alpha)", 2, 5, 0.05, 2, (v) => `10^${v.toFixed(2)} cm-1`),
                control("siliconIndex", "Silicon refractive index", 3.2, 4.2, 0.01, 3.5, (v) => v.toFixed(2)),
                control("depths", "Minimum displayed absorption lengths", 1, 25, 0.1, 5, (v) => v.toFixed(1)),
            ],
            calculate: siliconAbsorptionPower,
        },
        slabDesigner: {
            label: "Silicon slab + 1100 nm LED (Sec. 3.4.1)",
            note:
                "Uses Green's tabulated intrinsic-silicon data at 300 K instead of a fixed " +
                "absorption coefficient. The LED curve integrates a Gaussian source spectrum; " +
                "an 8 mm slab strongly favors its longer-wavelength tail. Power means optical " +
                "power incident on the slab, not the LED's electrical rating. Uncoated curves " +
                "include both surfaces and incoherent repeated internal reflections.",
            controls: [
                control("widthMm", "Silicon slab width", 0.1, 10, 0.1, 8, (v) => `${v.toFixed(1)} mm`),
                control("wavelengthNm", "Center wavelength", 1000, 1200, 1, 1100, (v) => `${v.toFixed(0)} nm`),
                control("sourceFwhmNm", "LED spectral FWHM", 0, 50, 1, 50, (v) => v === 0 ? "0 nm (laser)" : `${v.toFixed(0)} nm`),
                control("logSourcePower", "Incident optical power", -3, 1, 0.02, Math.log10(3), (v) => powerLogLabel(v)),
                control("targetPercent", "Desired transmission", 0.1, 50, 0.1, 10, (v) => `${v.toFixed(1)}%`),
                control("logTargetPower", "Desired output power", -6, 0, 0.05, -1, (v) => powerLogLabel(v)),
            ],
            calculate: slabInverseDesigner,
        },
        responsivity: {
            label: "Responsivity (Fig. 3.9)",
            note:
                "For fixed quantum efficiency, responsivity rises linearly with wavelength " +
                "until the band-gap cutoff.",
            controls: [
                control("eta", "Quantum efficiency eta_Q", 0.05, 1, 0.01, 0.8, (v) => `${Math.round(v * 100)}%`),
                control("eg", "Band gap E_g", 0.5, 3.2, 0.01, 1.12, (v) => `${v.toFixed(2)} eV`),
            ],
            calculate: responsivityCurve,
        },
        coating: {
            label: "Antireflection + cutoff (Fig. 3.10, qualitative)",
            note:
                "The reflection terms are calculated exactly for one lossless film. A labelled " +
                "qualitative collection envelope supplies the rounded band-gap edge in Figure 3.10.",
            controls: [
                control("design", "Design wavelength", 0.45, 1.5, 0.01, 1.0, (v) => `${v.toFixed(2)} um`),
                control("eg", "Detector band gap", 0.6, 2.5, 0.01, 1.12, (v) => `${v.toFixed(2)} eV`),
                control("substrate", "Substrate index", 1.5, 4.5, 0.01, 3.5, (v) => v.toFixed(2)),
                control("film", "Film index", 1.1, 3.0, 0.01, 1.87, (v) => v.toFixed(2)),
                control("thickness", "Quarter-wave thickness factor", 0.4, 1.6, 0.01, 1, (v) => `${v.toFixed(2)}x`),
            ],
            calculate: coatingResponse,
        },
        photovoltage: {
            label: "Open-circuit photovoltage (Eq. 3.18)",
            note:
                "Photovoltage is logarithmic, not linear, in optical generation. " +
                "This is why photovoltaic mode distorts a measured optical line shape.",
            controls: [
                control("logIs", "Saturation current log10(I_s)", -16, -9, 0.1, -12, (v) => `10^${v.toFixed(1)} A`),
                control("length", "Diffusion length L_e", 5, 300, 1, 50, (v) => `${v} um`),
                control("temperature", "Temperature", 220, 380, 1, 300, (v) => `${v} K`),
                control("ideality", "Ideality factor n", 1, 3, 0.02, 1, (v) => v.toFixed(2)),
            ],
            calculate: photovoltageCurve,
        },
    };

    function carrierProfile(state) {
        const tauSeconds = 10 ** state.tau * 1e-6;
        const lengthUm = Math.sqrt(state.D * tauSeconds) * 1e4;
        const maximumX = Math.max(100, 6 * lengthUm);
        const x = linearSpace(0, maximumX);
        const junction = 10 ** state.n0;
        const generation = 10 ** state.G;
        const bulk = generation * tauSeconds;
        const y = x.map(
            (position) =>
                (junction - bulk) * Math.exp(-position / lengthUm) + bulk,
        );
        return {
            series: [{ label: "delta n_p(x)", color: COLORS[0], x, y }],
            xLabel: "Distance from junction (um)",
            yLabel: "Excess carriers (cm-3)",
            xDomain: [0, maximumX],
            yTransform: "log10",
            readouts: [
                ["Diffusion length", `${engineering(lengthUm)} um`],
                ["Far-field G_L tau", `${engineering(bulk)} cm-3`],
                ["Junction value", `${engineering(junction)} cm-3`],
            ],
        };
    }

    function junctionBands(state) {
        const x = linearSpace(-2.5 * state.width, 2.5 * state.width);
        const centre = x.map(
            (position) =>
                (state.vbi / 2) *
                (1 - Math.tanh(position / (0.24 * state.width))),
        );
        return {
            series: [
                { label: "Conduction band", color: COLORS[0], x, y: centre },
                {
                    label: "Valence band",
                    color: COLORS[1],
                    x,
                    y: centre.map((value) => value - state.eg),
                },
                {
                    label: "Fermi level",
                    color: COLORS[2],
                    dash: "8 6",
                    x,
                    y: x.map(() => -0.5 * state.eg + 0.5 * state.vbi),
                },
            ],
            xLabel: "Position across junction (um)",
            yLabel: "Electron potential energy (eV)",
            readouts: [
                ["Band bending", `${state.vbi.toFixed(2)} eV`],
                ["Depletion width", `${state.width.toFixed(2)} um`],
                ["Equilibrium current", "0 A"],
            ],
        };
    }

    function diodeCurrent(voltage, saturation, ideality, temperature, photocurrent) {
        const exponent = clampExponent(
            voltage / (ideality * KB_EV_K * temperature),
        );
        return saturation * Math.expm1(exponent) - photocurrent;
    }

    function ivFamily(state) {
        const x = linearSpace(-0.5, state.vmax);
        const saturation = 10 ** state.logIs;
        const basePhoto = 10 ** state.logIph;
        const multipliers = [0, 1, 3];
        const series = multipliers.map((multiple, index) => ({
            label: multiple === 0 ? "Dark" : `${multiple}x illumination`,
            color: COLORS[index],
            x,
            y: x.map(
                (voltage) =>
                    diodeCurrent(
                        voltage,
                        saturation,
                        state.ideality,
                        state.temperature,
                        multiple * basePhoto,
                    ) * 1e9,
            ),
        }));
        const currentLimit = 1.08 * Math.max(
            ...series.flatMap((curve) => curve.y.map(Math.abs)),
        );
        const openCircuit = state.ideality * KB_EV_K * state.temperature *
            Math.log1p(basePhoto / saturation);
        return {
            series,
            xLabel: "Applied voltage (V)",
            yLabel: "Current (nA)",
            yDomain: [-currentLimit, currentLimit],
            quadrantAxes: true,
            readouts: [
                ["Dark current", `${engineering(saturation * 1e12)} pA`],
                ["Base photocurrent", `${engineering(basePhoto * 1e12)} pA`],
                ["Base V_oc", `${engineering(openCircuit)} V`],
            ],
        };
    }

    function ledSemilog(state) {
        const x = linearSpace(0.02, 0.9);
        const saturationDensity = 10 ** state.logIs;
        const area = 10 ** state.area;
        const current = x.map((voltage) =>
            Math.max(
                1e-30,
                diodeCurrent(
                    voltage,
                    saturationDensity,
                    state.ideality,
                    state.temperature,
                    0,
                ) * area,
            ),
        );
        const mvPerDecade =
            state.ideality * KB_EV_K * state.temperature * Math.log(10) * 1e3;
        return {
            series: [{ label: "Forward current", color: COLORS[0], x, y: current }],
            xLabel: "Forward voltage (V)",
            yLabel: "Forward current (A)",
            yTransform: "log10",
            readouts: [
                ["Slope", `${mvPerDecade.toFixed(1)} mV/decade`],
                ["Ideality factor", state.ideality.toFixed(2)],
                ["Temperature", `${state.temperature} K`],
            ],
        };
    }

    function spectralCutoff(state) {
        const cutoff = HC_EV_UM / state.eg;
        const maximum = Math.max(2.0, cutoff * 1.35);
        const x = linearSpace(0.25, maximum);
        const y = x.map((wavelength) => (wavelength <= cutoff ? 1 : 0));
        return {
            series: [{ label: "Ideal response S", color: COLORS[0], x, y }],
            xLabel: "Wavelength (um)",
            yLabel: "Spectral response",
            yDomain: [-0.05, 1.08],
            readouts: [
                ["Cutoff wavelength", `${cutoff.toFixed(3)} um`],
                ["Band gap", `${state.eg.toFixed(2)} eV`],
                ["Response rule", "E_photon >= E_g"],
            ],
        };
    }

    function logistic(value) {
        return 1 / (1 + Math.exp(-Math.max(-60, Math.min(60, value))));
    }

    function measuredLikeResponse(state) {
        const cutoff = HC_EV_UM / state.eg;
        const x = linearSpace(0.75, Math.max(2.0, cutoff + 0.25));
        const y = x.map(
            (wavelength) =>
                100 *
                state.peak *
                logistic((wavelength - state.shortEdge) / state.edgeWidth) *
                logistic((cutoff - wavelength) / state.edgeWidth),
        );
        return {
            series: [{ label: "Qualitative efficiency", color: COLORS[0], x, y }],
            xLabel: "Wavelength (um)",
            yLabel: "External quantum efficiency (%)",
            yDomain: [0, 100],
            readouts: [
                ["Filter edge", `${state.shortEdge.toFixed(2)} um`],
                ["Detector cutoff", `${cutoff.toFixed(2)} um`],
                ["Status", "Qualitative model"],
            ],
        };
    }

    function absorptionCurve(state) {
        const alpha = 10 ** state.logAlpha;
        const absorptionLengthUm = 1e4 / alpha;
        const x = linearSpace(0, state.depths * absorptionLengthUm);
        const y = x.map((position) =>
            Math.exp(-alpha * position * 1e-4),
        );
        return {
            series: [{ label: "I(x) / I_0", color: COLORS[0], x, y }],
            xLabel: "Depth in material (um)",
            yLabel: "Normalized intensity",
            xDomain: [0, state.depths * absorptionLengthUm],
            yDomain: [0, 1.03],
            readouts: [
                ["Absorption length", `${engineering(absorptionLengthUm)} um`],
                ["Intensity at 1/alpha", "0.3679 I_0"],
                ["Absorbed at 1/alpha", "63.21%"],
            ],
        };
    }

    function siliconAbsorptionPower(state) {
        const incidentPower = 10 ** state.logPower;
        const floorPower = 10 ** state.logFloor;
        const alpha = 10 ** state.logAlpha;
        const absorptionLengthUm = 1e4 / alpha;
        const reflectance =
            ((1 - state.siliconIndex) / (1 + state.siliconIndex)) ** 2;
        const enteringPower = incidentPower * (1 - reflectance);
        // bugs/0481: the depth at which the beam falls to an ABSOLUTE level is the only depth
        // source power moves -- z = ln(P_enter / P_floor) / alpha. Mirrors
        // KrakenOS.Physics.photodiode.absorption_depth_for_power; keep the two in step.
        const floorDepthUm =
            enteringPower > floorPower
                ? (Math.log(enteringPower / floorPower) / alpha) * 1e4
                : 0;
        // ... and it is why the window no longer always terminates at the same depth: the view
        // follows that crossing, so a decade of power visibly buys ln(10)/alpha more silicon.
        const gainPerDecadeUm = (Math.LN10 / alpha) * 1e4;
        const maximumDepthUm = Math.max(
            state.depths * absorptionLengthUm,
            1.05 * floorDepthUm,
        );
        const x = linearSpace(0, maximumDepthUm);
        const decayFrom = (startPower) =>
            x.map(
                (position) =>
                    startPower *
                    Math.exp(clampExponent(-alpha * position * 1e-4)),
            );
        const noReflection = decayFrom(incidentPower);
        const withReflection = decayFrom(enteringPower);
        const finalPower = withReflection[withReflection.length - 1];
        const floorReached = floorDepthUm > 0 && floorDepthUm <= maximumDepthUm;
        return {
            series: [
                {
                    label: "No surface reflection",
                    color: COLORS[1],
                    x,
                    y: noReflection,
                },
                {
                    label: "Air-to-silicon surface",
                    color: COLORS[0],
                    x,
                    y: withReflection,
                },
                {
                    label: "Detection floor",
                    color: COLORS[3],
                    x: [0, maximumDepthUm],
                    y: [floorPower, floorPower],
                },
            ],
            xLabel: "Depth inside silicon (um)",
            yLabel: "Optical power remaining (W)",
            xDomain: [0, maximumDepthUm],
            // A FIXED log frame, floor to the slider's top power: raising the source power now
            // lifts both lines inside it. Autoscaling to 1.03 * incidentPower rescaled the frame
            // by exactly the factor it was showing, so the plot never changed (bugs/0481).
            yTransform: "log10",
            yTickFormat: "power-log10",
            yDomain: [
                floorPower / 10,
                10 ** SILICON_SOURCE_LOG_MAX,
            ],
            readouts: [
                ["Source power", powerLabel(incidentPower)],
                ["Surface reflected", `${(100 * reflectance).toFixed(1)}% (${powerLabel(incidentPower * reflectance)})`],
                ["Power entering Si", powerLabel(enteringPower)],
                [
                    "Depth to floor",
                    floorDepthUm > 0
                        ? `${engineering(floorDepthUm)} um${floorReached ? "" : " (past view)"}`
                        : "at the surface",
                ],
                ["Depth per power decade", `${engineering(gainPerDecadeUm)} um`],
                ["Absorption length", `${engineering(absorptionLengthUm)} um (power-independent)`],
                ["Power remaining at edge", powerLabel(finalPower)],
            ],
        };
    }

    function siliconOpticalProperties(wavelengthNm) {
        if (
            wavelengthNm < GREEN_SILICON_WAVELENGTH_NM[0] ||
            wavelengthNm > GREEN_SILICON_WAVELENGTH_NM.at(-1)
        ) {
            throw new RangeError("wavelength is outside the Green silicon table");
        }
        const lowerIndex = Math.min(
            GREEN_SILICON_WAVELENGTH_NM.length - 2,
            Math.floor((wavelengthNm - 900) / 10),
        );
        const fraction =
            (wavelengthNm - GREEN_SILICON_WAVELENGTH_NM[lowerIndex]) / 10;
        const lowerLogAlpha = Math.log10(
            GREEN_SILICON_ALPHA_CM_INV[lowerIndex],
        );
        const upperLogAlpha = Math.log10(
            GREEN_SILICON_ALPHA_CM_INV[lowerIndex + 1],
        );
        return {
            alpha:
                10 ** (
                    lowerLogAlpha +
                    fraction * (upperLogAlpha - lowerLogAlpha)
                ),
            index:
                GREEN_SILICON_INDEX[lowerIndex] +
                fraction *
                    (GREEN_SILICON_INDEX[lowerIndex + 1] -
                        GREEN_SILICON_INDEX[lowerIndex]),
        };
    }

    function monochromaticSiliconTransmission(
        thicknessMm,
        wavelengthNm,
        includeSurfaceReflection = true,
    ) {
        const properties = siliconOpticalProperties(wavelengthNm);
        const bulk = Math.exp(-properties.alpha * thicknessMm * 0.1);
        if (!includeSurfaceReflection) return bulk;

        const reflectance =
            ((1 - properties.index) / (1 + properties.index)) ** 2;
        return (
            ((1 - reflectance) ** 2 * bulk) /
            (1 - (reflectance * bulk) ** 2)
        );
    }

    function siliconSlabTransmission(
        thicknessMm,
        wavelengthNm,
        sourceFwhmNm,
        includeSurfaceReflection = true,
    ) {
        if (sourceFwhmNm === 0) {
            return monochromaticSiliconTransmission(
                thicknessMm,
                wavelengthNm,
                includeSurfaceReflection,
            );
        }

        const sigmaNm = sourceFwhmNm / (2 * Math.sqrt(2 * Math.log(2)));
        const lower = Math.max(900, wavelengthNm - 4 * sigmaNm);
        const upper = Math.min(1300, wavelengthNm + 4 * sigmaNm);
        const wavelengths = linearSpace(lower, upper, 401);
        let weightedTransmission = 0;
        let totalWeight = 0;
        for (let index = 0; index < wavelengths.length; index += 1) {
            const wavelength = wavelengths[index];
            const weight = Math.exp(
                -0.5 * ((wavelength - wavelengthNm) / sigmaNm) ** 2,
            );
            const trapezoidWeight =
                index === 0 || index === wavelengths.length - 1 ? 0.5 : 1;
            weightedTransmission +=
                trapezoidWeight *
                weight *
                monochromaticSiliconTransmission(
                    thicknessMm,
                    wavelength,
                    includeSurfaceReflection,
                );
            totalWeight += trapezoidWeight * weight;
        }
        return weightedTransmission / totalWeight;
    }

    function wavelengthForTransmission(thicknessMm, targetFraction) {
        const maximum = monochromaticSiliconTransmission(0, 1300, true);
        if (targetFraction > maximum) return null;
        let lower = 900;
        let upper = 1300;
        for (let iteration = 0; iteration < 40; iteration += 1) {
            const midpoint = (lower + upper) / 2;
            if (
                monochromaticSiliconTransmission(
                    thicknessMm,
                    midpoint,
                    true,
                ) < targetFraction
            ) {
                lower = midpoint;
            } else {
                upper = midpoint;
            }
        }
        return upper;
    }

    function slabInverseDesigner(state) {
        const properties = siliconOpticalProperties(state.wavelengthNm);
        const sourcePower = 10 ** state.logSourcePower;
        const targetPower = 10 ** state.logTargetPower;
        const targetFraction = state.targetPercent / 100;
        const x = linearSpace(0, state.widthMm);
        const noReflectionTransmission = x.map((widthMm) =>
            siliconSlabTransmission(
                widthMm,
                state.wavelengthNm,
                0,
                false,
            ),
        );
        const monochromaticTransmission = x.map((widthMm) =>
            siliconSlabTransmission(widthMm, state.wavelengthNm, 0, true),
        );
        const ledTransmission = x.map((widthMm) =>
            siliconSlabTransmission(
                widthMm,
                state.wavelengthNm,
                state.sourceFwhmNm,
                true,
            ),
        );
        const requiredSource = (transmission) =>
            transmission.map((fraction) =>
                Math.log10(targetPower / fraction),
            );
        const selectedMonochromatic = monochromaticTransmission.at(-1);
        const selectedLed = ledTransmission.at(-1);
        const selectedNoReflection = noReflectionTransmission.at(-1);
        const targetWavelength = wavelengthForTransmission(
            state.widthMm,
            targetFraction,
        );
        const ledLabel =
            state.sourceFwhmNm === 0
                ? `${state.wavelengthNm.toFixed(0)} nm laser, uncoated`
                : `${state.wavelengthNm.toFixed(0)} nm LED (${state.sourceFwhmNm.toFixed(0)} nm FWHM)`;

        return {
            series: [
                {
                    label: `${state.wavelengthNm.toFixed(0)} nm, no reflection`,
                    color: COLORS[1],
                    x,
                    y: requiredSource(noReflectionTransmission),
                },
                {
                    label: `${state.wavelengthNm.toFixed(0)} nm, uncoated`,
                    color: COLORS[0],
                    x,
                    y: requiredSource(monochromaticTransmission),
                },
                {
                    label: ledLabel,
                    color: COLORS[3],
                    x,
                    y: requiredSource(ledTransmission),
                },
            ],
            xLabel: "Silicon slab width (mm)",
            yLabel: "Incident optical power for desired output",
            xDomain: [0, state.widthMm],
            yTickFormat: "power-log10",
            readouts: [
                ["Green alpha at center", `${engineering(properties.alpha)} cm-1`],
                ["Green n at center", properties.index.toFixed(3)],
                ["Monochromatic transmission", `${readableNumber(100 * selectedMonochromatic)}%`],
                ["LED-band transmission", `${readableNumber(100 * selectedLed)}%`],
                ["Output from selected source (mono)", powerLabel(sourcePower * selectedMonochromatic)],
                ["Output from selected source (LED)", powerLabel(sourcePower * selectedLed)],
                ["Source for desired output (mono)", powerLabel(targetPower / selectedMonochromatic)],
                ["Source for desired output (LED)", powerLabel(targetPower / selectedLed)],
                ["No-reflection transmission", `${readableNumber(100 * selectedNoReflection)}%`],
                [
                    `${state.targetPercent.toFixed(1)}% monochromatic target`,
                    targetWavelength === null
                        ? "Above the uncoated-surface ceiling"
                        : `requires about ${targetWavelength.toFixed(0)} nm or longer`,
                ],
                ["Can power change the percent?", "No - not in the linear model"],
            ],
        };
    }

    function responsivityCurve(state) {
        const cutoff = HC_EV_UM / state.eg;
        const x = linearSpace(0.25, Math.max(1.8, cutoff * 1.2));
        const y = x.map((wavelength) =>
            wavelength <= cutoff ? state.eta * wavelength / HC_EV_UM : 0,
        );
        const peak = state.eta * cutoff / HC_EV_UM;
        return {
            series: [{ label: "Responsivity", color: COLORS[0], x, y }],
            xLabel: "Wavelength (um)",
            yLabel: "Responsivity (A/W)",
            yDomain: [0, Math.max(1.05, peak * 1.12)],
            readouts: [
                ["Cutoff wavelength", `${cutoff.toFixed(3)} um`],
                ["R at 0.62 um", `${(state.eta * 0.62 / HC_EV_UM).toFixed(3)} A/W`],
                ["Peak ideal R", `${peak.toFixed(3)} A/W`],
            ],
        };
    }

    function filmReflectance(wavelength, n0, nf, ns, thickness) {
        const r01 = (n0 - nf) / (n0 + nf);
        const r12 = (nf - ns) / (nf + ns);
        const phase = 4 * Math.PI * nf * thickness / wavelength;
        const cosine = Math.cos(phase);
        const sine = Math.sin(phase);
        const numeratorReal = r01 + r12 * cosine;
        const numeratorImag = r12 * sine;
        const denominatorReal = 1 + r01 * r12 * cosine;
        const denominatorImag = r01 * r12 * sine;
        return (
            (numeratorReal ** 2 + numeratorImag ** 2) /
            (denominatorReal ** 2 + denominatorImag ** 2)
        );
    }

    function coatingResponse(state) {
        const cutoff = HC_EV_UM / state.eg;
        const x = linearSpace(0.35, Math.max(1.4, cutoff + 0.25));
        const uncoatedR = ((1 - state.substrate) / (1 + state.substrate)) ** 2;
        const quarterWave = state.design / (4 * state.film);
        const thickness = quarterWave * state.thickness;
        const collectionEnvelope = (wavelength) =>
            (0.55 + 0.45 * logistic((wavelength - 0.62) / 0.18)) *
            logistic((cutoff - wavelength) / 0.035);
        const uncoated = x.map(
            (wavelength) =>
                100 * collectionEnvelope(wavelength) * (1 - uncoatedR),
        );
        const coated = x.map(
            (wavelength) =>
                100 *
                collectionEnvelope(wavelength) *
                (1 - filmReflectance(
                    wavelength,
                    1,
                    state.film,
                    state.substrate,
                    thickness,
                )),
        );
        const designR = filmReflectance(
            state.design,
            1,
            state.film,
            state.substrate,
            thickness,
        );
        return {
            series: [
                { label: "Uncoated", color: COLORS[2], x, y: uncoated },
                { label: "Single-layer coated", color: COLORS[0], x, y: coated },
            ],
            xLabel: "Wavelength (um)",
            yLabel: "Model quantum efficiency (%)",
            yDomain: [0, 102],
            readouts: [
                ["Film thickness", `${(thickness * 1e3).toFixed(1)} nm`],
                ["Band-gap cutoff", `${cutoff.toFixed(3)} um`],
                ["Uncoated reflection", `${(100 * uncoatedR).toFixed(1)}%`],
                ["Design reflection", `${(100 * designR).toFixed(2)}%`],
            ],
        };
    }

    function photovoltageCurve(state) {
        const logGeneration = linearSpace(5, 22);
        const saturation = 10 ** state.logIs;
        const lengthCm = state.length * 1e-4;
        const y = logGeneration.map((logG) => {
            const photocurrent = Q * lengthCm * 10 ** logG;
            return (
                state.ideality *
                KB_EV_K *
                state.temperature *
                Math.log1p(photocurrent / saturation)
            );
        });
        const generationAtOneVolt =
            saturation *
            Math.expm1(
                1 / (state.ideality * KB_EV_K * state.temperature),
            ) /
            (Q * lengthCm);
        return {
            series: [{
                label: "Open-circuit voltage",
                color: COLORS[0],
                x: logGeneration,
                y,
            }],
            xLabel: "log10 optical generation (cm-3 s-1)",
            yLabel: "Photovoltage (V)",
            readouts: [
                ["Diffusion length", `${state.length} um`],
                ["Thermal voltage", `${(KB_EV_K * state.temperature * 1e3).toFixed(2)} mV`],
                ["G_L for 1 V", `${engineering(generationAtOneVolt)} cm-3 s-1`],
            ],
        };
    }

    function transformed(value, transform) {
        if (transform === "log10") return Math.log10(Math.max(value, 1e-300));
        return value;
    }

    function extent(values) {
        let minimum = Infinity;
        let maximum = -Infinity;
        values.forEach((value) => {
            if (Number.isFinite(value)) {
                minimum = Math.min(minimum, value);
                maximum = Math.max(maximum, value);
            }
        });
        if (minimum === maximum) {
            minimum -= 0.5;
            maximum += 0.5;
        }
        return [minimum, maximum];
    }

    function paddedDomain(domain, fraction = 0.07) {
        const span = domain[1] - domain[0];
        return [domain[0] - span * fraction, domain[1] + span * fraction];
    }

    function tickLabel(value, transform, format) {
        if (format === "power-log10") return powerLogLabel(value);
        if (transform === "log10") return `10^${Number(value.toFixed(1))}`;
        return engineering(value, 3);
    }

    function svgElement(name, attributes = {}) {
        const element = document.createElementNS("http://www.w3.org/2000/svg", name);
        Object.entries(attributes).forEach(([key, value]) =>
            element.setAttribute(key, value),
        );
        return element;
    }

    function renderPlot(svg, result) {
        svg.replaceChildren();
        const width = 900;
        const height = 500;
        const margin = {
            left: result.yTickFormat === "power-log10" ? 135 : 92,
            right: 25,
            top: 25,
            bottom: 70,
        };
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;
        const allX = result.series.flatMap((series) => series.x);
        const allY = result.series.flatMap((series) =>
            series.y.map((value) => transformed(value, result.yTransform)),
        );
        const xDomain = result.xDomain || paddedDomain(extent(allX), 0.02);
        const requestedY = result.yDomain
            ? result.yDomain.map((value) => transformed(value, result.yTransform))
            : null;
        const yDomain = requestedY || paddedDomain(extent(allY));
        const xScale = (value) =>
            margin.left +
            ((value - xDomain[0]) / (xDomain[1] - xDomain[0])) * plotWidth;
        const yScale = (value) =>
            margin.top +
            (1 -
                (transformed(value, result.yTransform) - yDomain[0]) /
                    (yDomain[1] - yDomain[0])) *
                plotHeight;

        const defs = svgElement("defs");
        const clipPath = svgElement("clipPath", { id: `plot-${Math.random().toString(36).slice(2)}` });
        const clipId = clipPath.id;
        clipPath.append(svgElement("rect", {
            x: margin.left,
            y: margin.top,
            width: plotWidth,
            height: plotHeight,
        }));
        defs.append(clipPath);
        svg.append(defs);

        for (let index = 0; index <= 5; index += 1) {
            const xValue =
                xDomain[0] + ((xDomain[1] - xDomain[0]) * index) / 5;
            const xPixel = xScale(xValue);
            svg.append(svgElement("line", {
                class: "grid",
                x1: xPixel,
                x2: xPixel,
                y1: margin.top,
                y2: margin.top + plotHeight,
            }));
            const label = svgElement("text", {
                x: xPixel,
                y: margin.top + plotHeight + 25,
                "text-anchor": "middle",
            });
            label.textContent = engineering(xValue, 3);
            svg.append(label);

            const yValue =
                yDomain[0] + ((yDomain[1] - yDomain[0]) * index) / 5;
            const yPixel =
                margin.top + plotHeight - (plotHeight * index) / 5;
            svg.append(svgElement("line", {
                class: "grid",
                x1: margin.left,
                x2: margin.left + plotWidth,
                y1: yPixel,
                y2: yPixel,
            }));
            const yLabel = svgElement("text", {
                x: margin.left - 12,
                y: yPixel + 4,
                "text-anchor": "end",
            });
            yLabel.textContent = tickLabel(
                yValue,
                result.yTransform,
                result.yTickFormat,
            );
            svg.append(yLabel);
        }

        if (result.quadrantAxes) {
            svg.append(svgElement("line", {
                class: "axis axis--zero",
                x1: margin.left,
                x2: margin.left + plotWidth,
                y1: yScale(0),
                y2: yScale(0),
            }));
            svg.append(svgElement("line", {
                class: "axis axis--zero",
                x1: xScale(0),
                x2: xScale(0),
                y1: margin.top,
                y2: margin.top + plotHeight,
            }));
        } else {
            svg.append(svgElement("line", {
                class: "axis",
                x1: margin.left,
                x2: margin.left + plotWidth,
                y1: margin.top + plotHeight,
                y2: margin.top + plotHeight,
            }));
            svg.append(svgElement("line", {
                class: "axis",
                x1: margin.left,
                x2: margin.left,
                y1: margin.top,
                y2: margin.top + plotHeight,
            }));
        }

        result.series.forEach((series) => {
            const commands = series.x.map((xValue, index) => {
                const prefix = index === 0 ? "M" : "L";
                return `${prefix}${xScale(xValue).toFixed(2)},${yScale(series.y[index]).toFixed(2)}`;
            });
            svg.append(svgElement("path", {
                class: "curve",
                d: commands.join(" "),
                stroke: series.color,
                "stroke-dasharray": series.dash || "",
                "clip-path": `url(#${clipId})`,
            }));
        });

        const xLabel = svgElement("text", {
            class: "axis-label",
            x: margin.left + plotWidth / 2,
            y: height - 16,
            "text-anchor": "middle",
        });
        xLabel.textContent = result.xLabel;
        svg.append(xLabel);

        const yLabel = svgElement("text", {
            class: "axis-label",
            x: 20,
            y: margin.top + plotHeight / 2,
            "text-anchor": "middle",
            transform: `rotate(-90 20 ${margin.top + plotHeight / 2})`,
        });
        yLabel.textContent = result.yLabel;
        svg.append(yLabel);
    }

    function makeControl(definition, state, onInput) {
        const wrapper = document.createElement("div");
        wrapper.className = "photodiode-lab__control";
        const head = document.createElement("div");
        head.className = "photodiode-lab__control-head";
        const label = document.createElement("label");
        const id = `photodiode-${definition.key}-${Math.random().toString(36).slice(2)}`;
        label.htmlFor = id;
        label.textContent = definition.label;
        const output = document.createElement("output");
        output.className = "photodiode-lab__value";
        output.htmlFor = id;
        output.textContent = definition.display(definition.value);
        head.append(label, output);

        const input = document.createElement("input");
        input.id = id;
        input.type = "range";
        input.min = definition.min;
        input.max = definition.max;
        input.step = definition.step;
        input.value = definition.value;
        input.addEventListener("input", () => {
            state[definition.key] = Number(input.value);
            output.textContent = definition.display(state[definition.key]);
            onInput();
        });

        const scale = document.createElement("div");
        scale.className = "photodiode-lab__control-scale";
        const low = document.createElement("span");
        low.textContent = definition.display(definition.min);
        const high = document.createElement("span");
        high.textContent = definition.display(definition.max);
        scale.append(low, high);
        wrapper.append(head, input, scale);
        return wrapper;
    }

    function initializeLab(root) {
        root.innerHTML = `
            <div class="photodiode-lab__header">
              <div>
                <p class="photodiode-lab__eyebrow">Equation Workbench</p>
                <h3 class="photodiode-lab__title">Chapter 3 Curve Explorer</h3>
              </div>
              <div class="photodiode-lab__chooser">
                <label>Curve or figure
                  <select data-role="mode"></select>
                </label>
              </div>
            </div>
            <div class="photodiode-lab__body">
              <section class="photodiode-lab__controls" data-role="controls">
                <h4>Model variables</h4>
              </section>
              <section class="photodiode-lab__stage">
                <p class="photodiode-lab__note" data-role="note"></p>
                <div class="photodiode-lab__plot-wrap">
                  <svg class="photodiode-lab__plot" data-role="plot"
                       viewBox="0 0 900 500" role="img"
                       aria-label="Interactive photodiode model plot"></svg>
                </div>
                <div class="photodiode-lab__legend" data-role="legend"></div>
                <dl class="photodiode-lab__readouts" data-role="readouts"></dl>
              </section>
            </div>`;

        const chooser = root.querySelector('[data-role="mode"]');
        const controls = root.querySelector('[data-role="controls"]');
        const note = root.querySelector('[data-role="note"]');
        const plot = root.querySelector('[data-role="plot"]');
        const legend = root.querySelector('[data-role="legend"]');
        const readouts = root.querySelector('[data-role="readouts"]');
        Object.entries(MODES).forEach(([key, mode]) => {
            const option = document.createElement("option");
            option.value = key;
            option.textContent = mode.label;
            chooser.append(option);
        });
        const requestedMode = new URLSearchParams(window.location.search).get("curve");
        if (requestedMode && MODES[requestedMode]) {
            chooser.value = requestedMode;
        }

        let state = {};

        const draw = () => {
            const mode = MODES[chooser.value];
            const result = mode.calculate(state);
            renderPlot(plot, result);
            legend.replaceChildren(
                ...result.series.map((series) => {
                    const item = document.createElement("span");
                    item.className = "photodiode-lab__legend-item";
                    const swatch = document.createElement("span");
                    swatch.className = "photodiode-lab__swatch";
                    swatch.style.setProperty("--swatch", series.color);
                    const text = document.createElement("span");
                    text.textContent = series.label;
                    item.append(swatch, text);
                    return item;
                }),
            );
            readouts.replaceChildren(
                ...result.readouts.map(([term, value]) => {
                    const item = document.createElement("div");
                    item.className = "photodiode-lab__readout";
                    const name = document.createElement("dt");
                    name.textContent = term;
                    const measurement = document.createElement("dd");
                    measurement.textContent = value;
                    item.append(name, measurement);
                    return item;
                }),
            );
        };

        const selectMode = () => {
            const mode = MODES[chooser.value];
            state = Object.fromEntries(
                mode.controls.map((definition) => [
                    definition.key,
                    definition.value,
                ]),
            );
            controls.replaceChildren();
            const heading = document.createElement("h4");
            heading.textContent = "Model variables";
            controls.append(heading);
            mode.controls.forEach((definition) =>
                controls.append(makeControl(definition, state, draw)),
            );
            note.textContent = mode.note;
            draw();
        };

        chooser.addEventListener("change", selectMode);
        selectMode();
    }

    const start = () =>
        document
            .querySelectorAll("[data-photodiode-lab]")
            .forEach(initializeLab);

    if (typeof document === "undefined") {
        // bugs/0481: headless (node) -- there is no DOM to attach to, so export the pure panel
        // models instead. Every `calculate` is a pure function of its control state, and this is
        // the only way a guard can check that the lab and
        // KrakenOS.Physics.photodiode agree: the same equations live in both, and two
        // implementations of one model drift silently. Inert in a browser, where `module` is
        // undefined and the DOM branch below runs exactly as before.
        if (typeof module !== "undefined" && module.exports) {
            module.exports = {
                MODES,
                powerLabel,
                powerLogLabel,
                engineering,
                siliconOpticalProperties,
                siliconSlabTransmission,
            };
        }
    } else if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }
})();
