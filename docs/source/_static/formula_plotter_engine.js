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
    const SYMBOL_PATTERN = /^[\p{L}][\p{L}\p{N}_]*$/u;

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

    function isSymbol(expression) {
        return typeof expression === "string" && SYMBOL_PATTERN.test(expression);
    }

    function delimiterSymbol(expression) {
        while (Array.isArray(expression) && expression[0] === "Delimiter" && expression.length === 2) {
            expression = expression[1];
        }
        return isSymbol(expression) ? expression : null;
    }

    function functionNotation(expression) {
        if (!Array.isArray(expression)) return null;
        if (
            expression.length === 2
            && isSymbol(expression[0])
            && !ARITIES.has(expression[0])
            && !CONSTANTS.has(expression[0])
        ) {
            const argument = delimiterSymbol(expression[1]);
            return argument ? { symbol: expression[0], argument } : null;
        }
        if (expression[0] === "InvisibleOperator" && expression.length === 3 && isSymbol(expression[1])) {
            const argument = delimiterSymbol(expression[2]);
            return argument ? { symbol: expression[1], argument } : null;
        }
        return null;
    }

    function declaredCallName(expression, functions) {
        if (!Array.isArray(expression)) return null;
        if (isSymbol(expression[0]) && functions.has(expression[0])) return expression[0];
        if (
            expression[0] === "InvisibleOperator"
            && isSymbol(expression[1])
            && functions.has(expression[1])
            && Array.isArray(expression[2])
            && expression[2][0] === "Delimiter"
        ) {
            return expression[1];
        }
        return null;
    }

    function definitionTarget(expression) {
        if (isSymbol(expression)) return { symbol: expression, argument: null };
        const notation = functionNotation(expression);
        if (!notation) {
            throw new Error("The left side must be one variable or a one-argument definition, such as R_n or I(\\theta)." );
        }
        if (notation.symbol === notation.argument) {
            throw new Error("A function name and its argument must be different.");
        }
        return notation;
    }

    function compile(expression, dependencies, functions = new Map(), depth = 0) {
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
            if (!isSymbol(expression)) {
                throw new Error(`Unsupported symbol: ${expression}.`);
            }
            dependencies.add(expression);
            return (values) => values.get(expression);
        }
        if (!Array.isArray(expression)) throw new Error("Incomplete expression.");
        const reference = functionNotation(expression);
        if (reference && functions.has(reference.symbol)) {
            const expected = functions.get(reference.symbol);
            if (reference.argument !== expected) {
                throw new Error(`${label(reference.symbol)} expects ${label(expected)}, not ${label(reference.argument)}.`);
            }
            dependencies.add(reference.symbol);
            return (values) => values.get(reference.symbol);
        }
        const callName = declaredCallName(expression, functions);
        if (callName) {
            throw new Error(`${label(callName)} only accepts its declared single-variable argument ${label(functions.get(callName))}.`);
        }
        const [operation, ...operands] = expression;
        if (operation === "Error") throw new Error("Invalid or incomplete LaTeX. Check commands, braces, and operands.");
        const arity = ARITIES.get(operation);
        if (!arity) throw new Error(`Unsupported operation: ${operation}. Use explicit scalar equations; see Supported input below.`);
        if (operands.length < arity[0] || operands.length > arity[1]) {
            throw new Error(`Unexpected number of arguments for ${operation}.`);
        }
        const evaluators = operands.map((operand) => compile(operand, dependencies, functions, depth + 1));
        return (values, angleFactor) => {
            const args = evaluators.map((evaluate) => evaluate(values, angleFactor));
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

    function sourceLines(source) {
        if (source.length > 24000) throw new Error("Use at most 24,000 characters.");
        return source
            .replace(/%[^\n]*/g, "")
            .replace(/\\(?:begin|end)\{(?:aligned|align\*?|gathered|gather\*?|equation\*?)\}/g, "")
            .replace(/\\\[|\\\]|\$+/g, "")
            .replace(/\\\\/g, "\n")
            .replace(/&/g, "")
            .split("\n");
    }

    function parse(source) {
        const lines = sourceLines(source);
        const records = [];
        const targets = new Map();
        const functions = new Map();
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
                const [, left, right] = expression;
                const target = definitionTarget(left);
                const { symbol, argument } = target;
                if (CONSTANTS.has(symbol)) throw new Error(`${symbol} is a reserved constant.`);
                if (targets.has(symbol)) throw new Error(`${label(symbol)} is defined more than once.`);
                targets.set(symbol, target);
                if (argument) functions.set(symbol, argument);
                records.push({ index, line, left, right, symbol, argument });
            } catch (error) {
                throw new Error(`Line ${index + 1}: ${error.message}`);
            }
        }
        for (const record of records) {
            try {
                const dependencies = new Set();
                const evaluate = compile(record.right, dependencies, functions);
                if (record.argument) dependencies.add(record.argument);
                definitions.set(record.symbol, {
                    symbol: record.symbol,
                    argument: record.argument,
                    dependencies,
                    evaluate,
                    latex: record.line,
                    lhsLatex: syntax.serialize(record.left),
                });
                variables.add(record.symbol);
                if (record.argument) variables.add(record.argument);
                dependencies.forEach((dependency) => variables.add(dependency));
            } catch (error) {
                throw new Error(`Line ${record.index + 1}: ${error.message}`);
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
        return { definitions, functions, variables: [...variables] };
    }

    function axisExpression(source, functions, name) {
        if (typeof source !== "string" || !source.trim()) throw new Error(`Enter a ${name}-axis expression.`);
        const lines = sourceLines(source).map((line) => line.trim()).filter(Boolean);
        if (lines.length !== 1) throw new Error(`Enter one ${name}-axis expression.`);
        let expression;
        try {
            expression = syntax.parse(normalize(lines[0]));
        } catch (error) {
            throw new Error(`Invalid ${name}-axis expression: ${error.message}`);
        }
        if (Array.isArray(expression) && expression[0] === "Equal") {
            throw new Error(`Enter only the ${name}-axis expression, without an equals sign.`);
        }
        const dependencies = new Set();
        let evaluate;
        try {
            evaluate = compile(expression, dependencies, functions);
        } catch (error) {
            throw new Error(`Invalid ${name}-axis expression: ${error.message}`);
        }
        return { dependencies, evaluate, label: syntax.serialize(expression), source: lines[0] };
    }

    function expressionDependsOn(model, dependencies, target, visited = new Set()) {
        for (const symbol of dependencies) {
            if (symbol === target) return true;
            if (visited.has(symbol)) continue;
            visited.add(symbol);
            const definition = model.definitions.get(symbol);
            if (definition && expressionDependsOn(model, definition.dependencies, target, visited)) return true;
        }
        return false;
    }

    function planAxes(model, sweepSymbol, xSource, ySource, angleUnit = "rad") {
        if (!model.variables.includes(sweepSymbol)) throw new Error("Choose a sweep variable from the equations.");
        if (!["rad", "deg"].includes(angleUnit)) throw new Error("Choose radians or degrees.");
        const xAxis = axisExpression(xSource, model.functions, "X");
        const yAxis = axisExpression(ySource, model.functions, "Y");
        for (const [axis, name] of [[xAxis, "X"], [yAxis, "Y"]]) {
            const unknown = [...axis.dependencies].filter((symbol) => !model.variables.includes(symbol));
            if (unknown.length) {
                throw new Error(`${name}-axis expression uses ${unknown.map(label).join(", ")}, which is not present in the equations.`);
            }
        }
        if (!expressionDependsOn(model, xAxis.dependencies, sweepSymbol)) {
            throw new Error(`The X-axis expression must depend on the sweep variable ${label(sweepSymbol)}.`);
        }
        const angleFactor = angleUnit === "deg" ? Math.PI / 180 : 1;
        const order = [];
        const parameters = new Map();
        const visited = new Set([sweepSymbol]);
        const visit = (symbol) => {
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
        xAxis.dependencies.forEach(visit);
        yAxis.dependencies.forEach(visit);
        const evaluatePoint = (sweepValue, inputs = {}) => {
            const values = new Map([[sweepSymbol, new Complex(sweepValue)]]);
            for (const [symbol, initial] of parameters) {
                const value = Object.hasOwn(inputs, symbol) ? inputs[symbol] : initial;
                if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`Provide a finite value for ${label(symbol)}.`);
                values.set(symbol, new Complex(value));
            }
            for (const definition of order) values.set(definition.symbol, definition.evaluate(values, angleFactor));
            return {
                x: xAxis.evaluate(values, angleFactor),
                y: yAxis.evaluate(values, angleFactor),
            };
        };
        return {
            sweepSymbol,
            xExpression: xAxis.source,
            yExpression: yAxis.source,
            xLabel: xAxis.label,
            yLabel: yAxis.label,
            parameters,
            order,
            evaluatePoint,
            xDependsOnSweep: true,
            yDependsOnSweep: expressionDependsOn(model, yAxis.dependencies, sweepSymbol),
        };
    }

    function plan(model, xSymbol, ySymbol, angleUnit = "rad") {
        if (!model.variables.includes(xSymbol) || !model.variables.includes(ySymbol)) throw new Error("Choose variables from the equations for both axes.");
        if (xSymbol === ySymbol) throw new Error("Choose different X and Y variables.");
        const calculation = planAxes(model, xSymbol, label(xSymbol), label(ySymbol), angleUnit);
        const evaluate = (xValue, inputs = {}) => {
            return calculation.evaluatePoint(xValue, inputs).y;
        };
        return {
            ...calculation,
            xSymbol,
            ySymbol,
            evaluate,
            dependsOnX: calculation.yDependsOnSweep,
        };
    }

    function sample(calculation, minimum, maximum, inputs = {}, count = 501) {
        if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || minimum >= maximum || !Number.isFinite(maximum - minimum)) {
            throw new Error("X minimum must be less than X maximum, with a finite span.");
        }
        if (!Number.isInteger(count) || count < 2 || count > 2001) throw new Error("Choose between 2 and 2,001 samples.");
        let nonreal = 0;
        let undefinedCount = 0;
        let xNonreal = 0;
        let xUndefinedCount = 0;
        const points = Array.from({ length: count }, (_, index) => {
            const sweep = minimum + (maximum - minimum) * index / (count - 1);
            const evaluated = calculation.evaluatePoint
                ? calculation.evaluatePoint(sweep, inputs)
                : { x: new Complex(sweep), y: calculation.evaluate(sweep, inputs) };
            let xValue = null;
            let yValue = null;
            if (!evaluated.x.isFinite()) xUndefinedCount += 1;
            else if (Math.abs(evaluated.x.im) > 1e-10 * Math.max(1, Math.abs(evaluated.x.re))) xNonreal += 1;
            else xValue = evaluated.x.re;
            if (!evaluated.y.isFinite()) undefinedCount += 1;
            else if (Math.abs(evaluated.y.im) > 1e-10 * Math.max(1, Math.abs(evaluated.y.re))) nonreal += 1;
            else yValue = evaluated.y.re;
            return { sweep, x: xValue, y: yValue };
        });
        return { points, nonreal, undefinedCount, xNonreal, xUndefinedCount };
    }

    return { parse, plan, planAxes, sample, label, sourceLines, REFLECTION, GAUSSIAN };
});
