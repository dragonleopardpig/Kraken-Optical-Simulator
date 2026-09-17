(function (root, factory) {
    "use strict";
    if (typeof module === "object" && module.exports) {
        module.exports = factory(
            require("./vendor/latex-syntax-0.128.13.min.js"),
            require("./vendor/complex-2.4.3.min.js"),
        );
    } else {
        root.KrakenFormula = factory(root.LatexSyntax, root.Complex);
    }
})(typeof globalThis === "undefined" ? this : globalThis, (syntax, Complex) => {
    "use strict";

    const REFLECTION = String.raw`R_n = \frac{1}{2}\left(|r_{\parallel}|^2 + |r_{\perp}|^2\right)
r_{\perp} = \frac{\cos\theta_i-\sqrt{n_{ti}^2-\sin^2\theta_i}}{\cos\theta_i+\sqrt{n_{ti}^2-\sin^2\theta_i}}
r_{\parallel} = \frac{n_{ti}^2\cos\theta_i-\sqrt{n_{ti}^2-\sin^2\theta_i}}{n_{ti}^2\cos\theta_i+\sqrt{n_{ti}^2-\sin^2\theta_i}}
n_{ti} = \frac{n_t}{n_i}
n_i = 1
n_t = 1.5`;
    const GAUSSIAN = String.raw`I = I_0 \exp\left(-2\left(\frac{r}{w}\right)^2\right)
I_0 = 1
w = 2`;
    const CONSTANTS = new Map([
        ["Pi", new Complex(Math.PI)],
        ["ExponentialE", new Complex(Math.E)],
        ["e", new Complex(Math.E)],
        ["ImaginaryUnit", new Complex(0, 1)],
        ["i", new Complex(0, 1)],
    ]);
    const TRIG = new Map([
        ["Sin", "sin"], ["Cos", "cos"], ["Tan", "tan"],
        ["Cot", "cot"], ["Sec", "sec"], ["Csc", "csc"],
    ]);
    const INVERSE = new Map([
        ["Arcsin", "asin"], ["Arccos", "acos"], ["Arctan", "atan"],
    ]);
    const UNARY = new Map([
        ["Negate", "neg"], ["Sqrt", "sqrt"], ["Exp", "exp"],
        ["Ln", "log"], ["Sinh", "sinh"], ["Cosh", "cosh"],
        ["Tanh", "tanh"], ["Conjugate", "conjugate"],
    ]);
    const ARITIES = new Map([
        ["Add", [2, 64]], ["Multiply", [2, 64]],
        ["InvisibleOperator", [2, 64]], ["Subtract", [2, 2]],
        ["Divide", [2, 2]], ["Rational", [2, 2]], ["Power", [2, 2]],
        ["Root", [2, 2]], ["Log", [1, 2]], ["Lb", [1, 1]], ["Abs", [1, 1]],
        ["Delimiter", [1, 1]], ["Real", [1, 1]], ["Imaginary", [1, 1]],
        ...[...TRIG.keys(), ...INVERSE.keys(), ...UNARY.keys()].map(
            (name) => [name, [1, 1]],
        ),
    ]);

    function normalize(latex) {
        return latex
            .replace(/_\s*\{\s*\\(perp|parallel)\s*\}/g, "_{\\mathrm{$1}}")
            .replace(/_\s*\\(perp|parallel)\b/g, "_{\\mathrm{$1}}")
            .replace(/\\(sin|cos|tan)\s*\^\s*\{\s*-1\s*\}/g, "\\arc$1");
    }

    function label(symbol) {
        return syntax.serialize(symbol)
            .replace(/_\{perp\}/g, "_{\\perp}")
            .replace(/_\{parallel\}/g, "_{\\parallel}");
    }

    function compile(expression, dependencies, depth = 0) {
        if (depth > 64) throw new Error("An expression is nested too deeply (maximum 64 levels).");
        if (expression && !Array.isArray(expression) && typeof expression === "object") {
            expression = expression.fn || expression.sym || Number(expression.num);
        }
        if (typeof expression === "number") {
            if (!Number.isFinite(expression)) throw new Error("Use finite numeric constants.");
            const value = new Complex(expression);
            return () => value;
        }
        if (typeof expression === "string") {
            if (CONSTANTS.has(expression)) return () => CONSTANTS.get(expression);
            if (!/^[\p{L}][\p{L}\p{N}_]*$/u.test(expression)) {
                throw new Error(`Unsupported symbol: ${expression}.`);
            }
            dependencies.add(expression);
            return (values) => values.get(expression);
        }
        if (!Array.isArray(expression)) throw new Error("Incomplete expression.");
        const [operation, ...operands] = expression;
        if (operation === "Error") throw new Error("Invalid or incomplete LaTeX. Check commands, braces, and operands.");
        const arity = ARITIES.get(operation);
        if (!arity) throw new Error(`Unsupported operation: ${operation}. Use explicit scalar equations; see Supported input below.`);
        if (operands.length < arity[0] || operands.length > arity[1]) {
            throw new Error(`Unexpected number of arguments for ${operation}.`);
        }
        const functions = operands.map((operand) => compile(operand, dependencies, depth + 1));
        return (values, angleFactor) => {
            const args = functions.map((evaluate) => evaluate(values, angleFactor));
            const first = args[0];
            if (TRIG.has(operation)) {
                const quarterTurns = first.re / (Math.PI / 2 / angleFactor);
                if (first.im === 0 && Number.isSafeInteger(quarterTurns)) {
                    const quadrant = ((quarterTurns % 4) + 4) % 4;
                    const sine = new Complex([0, 1, 0, -1][quadrant]);
                    const cosine = new Complex([1, 0, -1, 0][quadrant]);
                    if (operation === "Sin") return sine;
                    if (operation === "Cos") return cosine;
                    if (operation === "Tan") return sine.div(cosine);
                    if (operation === "Cot") return cosine.div(sine);
                    return new Complex(1).div(operation === "Sec" ? cosine : sine);
                }
                return first.mul(angleFactor)[TRIG.get(operation)]();
            }
            if (INVERSE.has(operation)) return first[INVERSE.get(operation)]().div(angleFactor);
            if (UNARY.has(operation)) return first[UNARY.get(operation)]();
            switch (operation) {
                case "Add": return args.reduce((total, value) => total.add(value));
                case "Multiply":
                case "InvisibleOperator": return args.reduce((total, value) => total.mul(value));
                case "Subtract": return first.sub(args[1]);
                case "Divide":
                case "Rational": return first.div(args[1]);
                case "Power": return first.pow(args[1]);
                case "Root": return first.pow(new Complex(1).div(args[1]));
                case "Log": return first.log().div(args.length === 2 ? args[1].log() : Math.LN10);
                case "Lb": return first.log().div(Math.LN2);
                case "Abs": return new Complex(first.abs());
                case "Real": return new Complex(first.re);
                case "Imaginary": return new Complex(first.im);
                case "Delimiter": return first;
                default: throw new Error(`Unsupported operation: ${operation}.`);
            }
        };
    }

    function parse(source) {
        if (source.length > 24000) throw new Error("Use at most 24,000 characters.");
        const lines = source
            .replace(/%[^\n]*/g, "")
            .replace(/\\(?:begin|end)\{(?:aligned|align\*?|gathered|gather\*?|equation\*?)\}/g, "")
            .replace(/\\\[|\\\]|\$+/g, "")
            .replace(/\\\\/g, "\n")
            .replace(/&/g, "")
            .split("\n");
        const definitions = new Map();
        const variables = new Set();
        for (const [index, raw] of lines.entries()) {
            const line = raw.trim();
            if (!line) continue;
            try {
                let balance = 0;
                for (const character of line) {
                    if (character === "{") balance += 1;
                    if (character === "}") balance -= 1;
                    if (balance < 0) throw new Error("Unbalanced braces.");
                }
                if (balance !== 0) throw new Error("Unbalanced braces. Put each complete equation on one line.");
                const expression = syntax.parse(normalize(line));
                if (!Array.isArray(expression) || expression[0] !== "Equal" || expression.length !== 3) {
                    throw new Error("Enter one definition per line, such as y = x^2.");
                }
                const [, symbol, right] = expression;
                if (typeof symbol !== "string" || !/^[\p{L}][\p{L}\p{N}_]*$/u.test(symbol)) {
                    throw new Error("The left side must be one variable, such as R_n (not a function or implicit equation).");
                }
                if (CONSTANTS.has(symbol)) throw new Error(`${symbol} is a reserved constant.`);
                if (definitions.has(symbol)) throw new Error(`${label(symbol)} is defined more than once.`);
                const dependencies = new Set();
                const evaluate = compile(right, dependencies);
                definitions.set(symbol, { symbol, dependencies, evaluate, latex: line });
                variables.add(symbol);
                dependencies.forEach((dependency) => variables.add(dependency));
            } catch (error) {
                throw new Error(`Line ${index + 1}: ${error.message}`);
            }
        }
        if (!definitions.size) throw new Error("Enter at least one equation.");
        if (definitions.size > 64 || variables.size > 128) throw new Error("Use at most 64 equations and 128 variables.");
        const visited = new Set();
        const visit = (symbol, path) => {
            if (path.includes(symbol)) throw new Error(`Circular definitions: ${[...path, symbol].map(label).join(" → ")}.`);
            if (visited.has(symbol)) return;
            const definition = definitions.get(symbol);
            if (definition) definition.dependencies.forEach((dependency) => visit(dependency, [...path, symbol]));
            visited.add(symbol);
        };
        definitions.forEach((_, symbol) => visit(symbol, []));
        return { definitions, variables: [...variables] };
    }

    function plan(model, xSymbol, ySymbol, angleUnit = "rad") {
        if (!model.variables.includes(xSymbol) || !model.variables.includes(ySymbol)) throw new Error("Choose variables from the equations for both axes.");
        if (xSymbol === ySymbol) throw new Error("Choose different X and Y variables.");
        if (!["rad", "deg"].includes(angleUnit)) throw new Error("Choose radians or degrees.");
        const angleFactor = angleUnit === "deg" ? Math.PI / 180 : 1;
        const order = [];
        const parameters = new Map();
        const visited = new Set([xSymbol]);
        let dependsOnX = false;
        const visit = (symbol) => {
            if (symbol === xSymbol) dependsOnX = true;
            if (visited.has(symbol)) return;
            visited.add(symbol);
            const definition = model.definitions.get(symbol);
            if (!definition) {
                parameters.set(symbol, null);
            } else if (!definition.dependencies.size) {
                const value = definition.evaluate(new Map(), angleFactor);
                if (value.isFinite() && value.im === 0) parameters.set(symbol, value.re);
                else order.push(definition);
            } else {
                definition.dependencies.forEach(visit);
                order.push(definition);
            }
        };
        visit(ySymbol);
        const evaluate = (xValue, inputs = {}) => {
            const values = new Map([[xSymbol, new Complex(xValue)]]);
            for (const [symbol, initial] of parameters) {
                const value = Object.hasOwn(inputs, symbol) ? inputs[symbol] : initial;
                if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`Provide a finite value for ${label(symbol)}.`);
                values.set(symbol, new Complex(value));
            }
            for (const definition of order) values.set(definition.symbol, definition.evaluate(values, angleFactor));
            return values.get(ySymbol);
        };
        return { xSymbol, ySymbol, parameters, order, evaluate, dependsOnX };
    }

    function sample(calculation, minimum, maximum, inputs = {}, count = 501) {
        if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || minimum >= maximum || !Number.isFinite(maximum - minimum)) {
            throw new Error("X minimum must be less than X maximum, with a finite span.");
        }
        if (!Number.isInteger(count) || count < 2 || count > 2001) throw new Error("Choose between 2 and 2,001 samples.");
        let nonreal = 0;
        let undefinedCount = 0;
        const points = Array.from({ length: count }, (_, index) => {
            const xValue = minimum + (maximum - minimum) * index / (count - 1);
            const value = calculation.evaluate(xValue, inputs);
            let yValue = null;
            if (!value.isFinite()) undefinedCount += 1;
            else if (Math.abs(value.im) > 1e-10 * Math.max(1, Math.abs(value.re))) nonreal += 1;
            else yValue = value.re;
            return { x: xValue, y: yValue };
        });
        return { points, nonreal, undefinedCount };
    }

    return { parse, plan, sample, label, REFLECTION, GAUSSIAN };
});
