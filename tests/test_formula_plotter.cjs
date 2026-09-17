const assert = require("node:assert/strict");
const test = require("node:test");
const engine = require("../docs/source/_static/formula_plotter_engine.js");

function close(actual, expected, tolerance = 1e-10) {
    assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} differs from ${expected}`);
}

function value(source, xValue = 0, inputs = {}, angles = "rad", xSymbol = "x", ySymbol = "y") {
    return engine.plan(engine.parse(source), xSymbol, ySymbol, angles).evaluate(xValue, inputs);
}

test("reflection agrees with independent Fresnel values at normal and oblique incidence", () => {
    const calculation = engine.plan(engine.parse(engine.REFLECTION), "theta_i", "R_n", "deg");
    close(calculation.evaluate(0).re, 0.04);
    for (const angle of [10, 30, 45, 60, 80]) {
        const incident = angle * Math.PI / 180;
        const transmitted = Math.asin(Math.sin(incident) / 1.5);
        const perpendicular = (Math.cos(incident) - 1.5 * Math.cos(transmitted)) / (Math.cos(incident) + 1.5 * Math.cos(transmitted));
        const parallel = (1.5 * Math.cos(incident) - Math.cos(transmitted)) / (1.5 * Math.cos(incident) + Math.cos(transmitted));
        close(calculation.evaluate(angle).re, (perpendicular ** 2 + parallel ** 2) / 2);
    }
    close(calculation.evaluate(90).re, 1);
    close(calculation.evaluate(0, { n_t: 2 }).re, 1 / 9);
});

test("Brewster angle gives zero parallel amplitude", () => {
    const calculation = engine.plan(engine.parse(engine.REFLECTION), "theta_i", "r_parallel", "deg");
    close(calculation.evaluate(Math.atan(1.5) * 180 / Math.PI).abs(), 0);
});

test("matched media do not acquire a spurious grazing-incidence reflection from roundoff", () => {
    const calculation = engine.plan(engine.parse(engine.REFLECTION), "theta_i", "R_n", "deg");
    for (const angle of [0, 30, 60, 89]) close(calculation.evaluate(angle, { n_t: 1 }).re, 0);
    assert.equal(calculation.evaluate(90, { n_t: 1 }).isFinite(), false);
});

test("complex Fresnel amplitudes give unit power reflectance during total internal reflection", () => {
    const model = engine.parse(engine.REFLECTION);
    const reflection = engine.plan(model, "theta_i", "R_n", "deg");
    const amplitude = engine.plan(model, "theta_i", "r_perp", "deg");
    for (const angle of [42, 50, 60, 85, 90]) {
        close(reflection.evaluate(angle, { n_i: 1.5, n_t: 1 }).re, 1);
    }
    assert.ok(Math.abs(amplitude.evaluate(60, { n_i: 1.5, n_t: 1 }).im) > 0.1);
});

test("equations copied from the image retain their literal squares and polarization symbols", () => {
    const literal = engine.REFLECTION.replace(/\|r_\{\\(parallel|perp)\}\|/g, "r_\\$1");
    const calculation = engine.plan(engine.parse(literal), "theta_i", "R_n", "deg");
    close(calculation.evaluate(0).re, 0.04);
    assert.ok(Math.abs(calculation.evaluate(60, { n_i: 1.5, n_t: 1 }).im) > 0.1);
});

test("dependencies are evaluated in order regardless of equation order", () => {
    const source = "y = a + b\nb = 2a\na = x^2";
    const model = engine.parse(source);
    const calculation = engine.plan(model, "x", "y");
    assert.deepEqual(calculation.order.map((definition) => definition.symbol), ["a", "b", "y"]);
    close(calculation.evaluate(3).re, 27);
    close(value(source.split("\n").reverse().join("\n"), 3).re, 27);
});

test("axes can sweep a defined variable without implicitly solving its equation", () => {
    const model = engine.parse("y = a^2\na = 2x\nx = 3");
    close(engine.plan(model, "a", "y").evaluate(4).re, 16);
    assert.equal(engine.plan(model, "a", "y").parameters.size, 0);
    assert.equal(engine.plan(model, "y", "a").dependsOnX, false);
});

test("missing inputs are exposed but never silently assigned a value", () => {
    const calculation = engine.plan(engine.parse("y = a x + b\nb = 2"), "x", "y");
    assert.equal(calculation.parameters.get("a"), null);
    assert.throws(() => calculation.evaluate(3), /finite value for a/);
    assert.throws(() => calculation.evaluate(3, { a: NaN }), /finite value for a/);
    close(calculation.evaluate(3, { a: 4 }).re, 14);
    close(calculation.evaluate(3, { a: 4, b: 5 }).re, 17);
});

test("only parameters needed for the chosen output are required", () => {
    const calculation = engine.plan(engine.parse("y = x^2\nz = a+b"), "x", "y");
    assert.equal(calculation.parameters.size, 0);
    close(calculation.evaluate(3).re, 9);
});

test("Gaussian example uses the same generic expression engine", () => {
    const calculation = engine.plan(engine.parse(engine.GAUSSIAN), "r", "I");
    close(calculation.evaluate(0).re, 1);
    close(calculation.evaluate(2).re, Math.exp(-2));
    close(calculation.evaluate(2, { I_0: 3, w: 4 }).re, 3 * Math.exp(-0.5));
});

test("fractions, roots, implicit multiplication, logs and multi-letter names", () => {
    close(value(String.raw`y = \frac{2x}{3} + \sqrt{x} + x^{1/2}`, 9).re, 12);
    close(value(String.raw`y = \ln(e^x)+\log(100)+\log_{2}(8)`, 2).re, 7);
    close(value(String.raw`y = \mathrm{gain} x`, 4, { gain: 3 }).re, 12);
    close(value(String.raw`y = \sqrt[3]{x}`, 8).re, 2);
});

test("trig functions obey degree and radian modes, inverse functions return the chosen unit", () => {
    close(value(String.raw`y = \sin^2 x + \cos^2 x`, 27, {}, "deg").re, 1);
    close(value(String.raw`y = \sin x`, Math.PI / 2).re, 1);
    close(value(String.raw`y = \arcsin x`, 0.5, {}, "deg").re, 30);
    close(value(String.raw`y = \sin^{-1} x`, 0.5, {}, "deg").re, 30);
    close(value(String.raw`y = \sinh x`, 1, {}, "deg").re, Math.sinh(1));
});

test("aligned input, display delimiters and comments work", () => {
    close(value(String.raw`\[\begin{aligned}y &= a x \\ a &= 3\end{aligned}\]`, 2).re, 6);
    close(value("$y=x^2$ % square\n", 3).re, 9);
});

test("cycles, duplicate definitions, reserved constants and implicit equations are rejected", () => {
    for (const source of ["y=x\nx=y", "a=b\nb=c\nc=a", "y=y+1"]) assert.throws(() => engine.parse(source), /Circular/);
    assert.throws(() => engine.parse("y=x\ny=x^2"), /more than once/);
    assert.throws(() => engine.parse("i=2"), /reserved/);
    assert.throws(() => engine.parse("x^2+y^2=1"), /left side/);
    assert.throws(() => engine.parse("f(x)=x^2"), /left side/);
});

test("malformed and unsupported expressions fail with line numbers", () => {
    for (const expression of [String.raw`\frac{1}{}`, String.raw`\sqrt{x`, String.raw`\unknown{x}`, "x +", String.raw`\int x dx`, String.raw`\sum_{k=1}^{5}k`]) {
        assert.throws(() => engine.parse(`a = 1\ny = ${expression}`), /Line 2:/);
    }
    assert.throws(() => engine.parse(" "), /at least one/);
    assert.throws(() => engine.parse("y = x".repeat(5000)), /24,000/);
});

test("sampling distinguishes undefined values from non-real values and validates range", () => {
    const pole = engine.plan(engine.parse("y = 1/x"), "x", "y");
    const sampled = engine.sample(pole, -1, 1, {}, 3);
    assert.equal(sampled.points[1].y, null);
    assert.equal(sampled.undefinedCount, 1);
    const complex = engine.plan(engine.parse(String.raw`y = \sqrt{x}`), "x", "y");
    const roots = engine.sample(complex, -1, 1, {}, 3);
    assert.equal(roots.nonreal, 1);
    assert.equal(roots.points[0].y, null);
    close(roots.points[2].y, 1);
    assert.throws(() => engine.sample(pole, 1, 1), /minimum/);
    assert.throws(() => engine.sample(pole, 2, 1), /minimum/);
    assert.throws(() => engine.sample(pole, 0, Infinity), /minimum/);
    assert.throws(() => engine.sample(pole, 0, 1, {}, 50000), /samples/);
    assert.throws(() => engine.plan(engine.parse("y=x"), "x", "x"), /different/);
});

test("complex magnitudes produce real outputs without discarding imaginary parts", () => {
    close(value(String.raw`y = |\sqrt{x}|^2`, -4).re, 4);
    close(value(String.raw`y = |x+i|^2`, 3).re, 10);
});
