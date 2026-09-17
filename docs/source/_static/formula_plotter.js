(() => {
    "use strict";

    const engine = window.KrakenFormula;
    const format = (value) => Number(value.toPrecision(5)).toString();
    const display = (symbol) => symbol.replace(/theta/g, "θ").replace(/_perp/g, "⊥").replace(/_parallel/g, "∥");
    const svgNode = (tag, attributes = {}, content = "") => {
        const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
        Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, value));
        element.textContent = content;
        return element;
    };

    function mount(root, instance) {
        if (!engine) {
            root.textContent = "The equation plotter could not load. Reload the page to retry.";
            return;
        }
        const prefix = `formula-${instance}`;
        root.innerHTML = `
          <div class="formula-plotter__heading">
            <strong>Equations → interactive curve</strong>
            <label>Example <select data-role="example">
              <option value="reflection">Reflection of natural light</option>
              <option value="gaussian">Gaussian intensity</option>
            </select></label>
            <button type="button" data-role="load">Load example</button>
          </div>
          <label for="${prefix}-source">LaTeX equations</label>
          <p class="formula-plotter__hint" id="${prefix}-help">One complete equation per line, in any order. Define constants here or enter their values below. The selected X variable is swept over its range.</p>
          <textarea id="${prefix}-source" data-role="source" rows="9" spellcheck="false" autocapitalize="off" aria-describedby="${prefix}-help"></textarea>
          <section class="formula-plotter__preview-panel" aria-labelledby="${prefix}-preview-heading">
            <strong id="${prefix}-preview-heading">Rendered equations</strong>
            <p class="formula-plotter__hint">Updates as you type. Check the fractions, powers, and symbols before selecting Build plot.</p>
            <p class="formula-plotter__hint" data-role="preview-status" role="status" aria-live="polite"></p>
            <div class="formula-plotter__preview" data-role="preview"></div>
          </section>
          <div class="formula-plotter__actions">
            <button type="button" class="formula-plotter__primary" data-role="build">Build plot</button>
            <span data-role="edit-state"></span>
          </div>
          <p class="formula-plotter__status" data-role="status" role="status" aria-live="polite"></p>
          <div data-role="workspace" hidden>
            <div class="formula-plotter__axes">
              <label>X-axis variable<select data-role="x"></select></label>
              <label>Y-axis variable<select data-role="y"></select></label>
              <label>Trig angles<select data-role="angles"><option value="deg">Degrees</option><option value="rad">Radians</option></select></label>
            </div>
            <div class="formula-plotter__range">
              <label>X domain minimum<input data-role="minimum" type="number" step="any" value="0"></label>
              <label>X domain maximum<input data-role="maximum" type="number" step="any" value="90"></label>
              <label>Visible start <output data-role="start-label"></output><input data-role="start" type="range" min="0" max="1000" value="0"></label>
              <label>Visible end <output data-role="end-label"></output><input data-role="end" type="range" min="0" max="1000" value="1000"></label>
            </div>
            <div class="formula-plotter__parameters" data-role="parameters"></div>
            <p class="formula-plotter__hint" data-role="dependency"></p>
            <svg class="formula-plotter__chart" data-role="chart" viewBox="0 0 800 370" role="img" aria-label="Equation plot"></svg>
            <label class="formula-plotter__probe">Inspect X <input data-role="probe" type="range" min="0" max="500" value="0"><output data-role="probe-value" aria-live="polite"></output></label>
            <div class="formula-plotter__actions"><button type="button" data-role="csv">Download CSV</button><span class="formula-plotter__hint">501 samples · drag sliders to update</span></div>
          </div>`;
        const find = (name) => root.querySelector(`[data-role="${name}"]`);
        const controls = Object.fromEntries([
            "source", "example", "load", "build", "edit-state", "status", "workspace", "preview", "preview-status",
            "x", "y", "angles", "minimum", "maximum", "start", "end", "start-label", "end-label",
            "parameters", "dependency", "chart", "probe", "probe-value", "csv",
        ].map((name) => [name, find(name)]));
        let model = null;
        let calculation = null;
        let result = null;
        let activeSource = "";
        let frame = null;
        let probePoint = null;
        let graphPosition = null;
        let previewTimer = null;
        let previewRevision = 0;
        let previewQueue = Promise.resolve();
        const parameterInputs = new Map();
        const parameterValues = new Map();

        function status(message, error = false) {
            controls.status.textContent = message;
            controls.status.classList.toggle("formula-plotter__status--error", error);
        }

        function invalidate(message) {
            result = null;
            controls.chart.replaceChildren();
            controls.csv.disabled = true;
            controls.probe.disabled = true;
            controls["probe-value"].textContent = "";
            status(message, true);
        }

        function numberInput(input, name) {
            if (!input.value.trim() || !Number.isFinite(input.valueAsNumber)) throw new Error(`Enter a finite value for ${name}.`);
            return input.valueAsNumber;
        }

        function addParameter(symbol, initial) {
            const row = document.createElement("div");
            row.className = "formula-plotter__parameter";
            const makeInput = (text, type, value) => {
                const label = document.createElement("label");
                label.textContent = text;
                const input = document.createElement("input");
                input.type = type;
                input.step = "any";
                input.value = value ?? "";
                label.append(input);
                row.append(label);
                return input;
            };
            const current = parameterValues.has(symbol) ? parameterValues.get(symbol) : initial;
            const extent = Math.max(1, Math.abs(current ?? 1) * 2);
            const value = makeInput(display(symbol), "number", current);
            value.dataset.parameter = symbol;
            const slider = makeInput(`${display(symbol)} slider`, "range", current ?? 0);
            const lower = makeInput("Slider min", "number", Math.min(0, (current ?? 0) - extent));
            const upper = makeInput("Slider max", "number", (current ?? 0) + extent);
            const syncSlider = () => {
                slider.min = lower.value;
                slider.max = upper.value;
                slider.step = String((upper.valueAsNumber - lower.valueAsNumber) / 1000);
                slider.value = value.value || "0";
            };
            syncSlider();
            value.addEventListener("input", () => {
                parameterValues.set(symbol, value.valueAsNumber);
                slider.value = value.value;
                schedule();
            });
            slider.addEventListener("input", () => {
                value.value = slider.value;
                parameterValues.set(symbol, value.valueAsNumber);
                schedule();
            });
            [lower, upper].forEach((input) => input.addEventListener("input", () => {
                if (Number.isFinite(lower.valueAsNumber) && Number.isFinite(upper.valueAsNumber) && lower.valueAsNumber < upper.valueAsNumber) syncSlider();
                schedule();
            }));
            parameterInputs.set(symbol, { value, lower, upper });
            controls.parameters.append(row);
        }

        function selectAxes() {
            try {
                calculation = engine.plan(model, controls.x.value, controls.y.value, controls.angles.value);
                parameterInputs.clear();
                controls.parameters.replaceChildren();
                calculation.parameters.forEach((initial, symbol) => addParameter(symbol, initial));
                const order = calculation.order.map((definition) => display(definition.symbol));
                controls.dependency.textContent = `Evaluation: ${[display(calculation.xSymbol), ...calculation.parameters.keys()].map(display).join(", ")}${order.length ? ` → ${order.join(" → ")}` : ""}.` +
                    (model.definitions.has(calculation.xSymbol) ? " The X variable's definition is replaced by the sweep." : "") +
                    (!calculation.dependsOnX ? " Y does not depend on X; this is a constant curve." : "");
                render();
            } catch (error) {
                calculation = null;
                invalidate(error.message);
            }
        }

        function inspect() {
            if (!result) return;
            const point = result.points[Number(controls.probe.value)];
            controls["probe-value"].textContent = `${display(calculation.xSymbol)} = ${format(point.x)}; ${display(calculation.ySymbol)} = ${point.y === null ? "undefined or non-real" : format(point.y)}`;
            probePoint.setAttribute("visibility", point.y === null ? "hidden" : "visible");
            if (point.y !== null) {
                probePoint.setAttribute("cx", graphPosition.x(point.x));
                probePoint.setAttribute("cy", graphPosition.y(point.y));
            }
        }

        function draw() {
            const chart = controls.chart;
            chart.replaceChildren();
            const points = result.points;
            const finite = points.filter((point) => point.y !== null);
            if (!finite.length) throw new Error("No finite real Y values in this interval. Check the equations, parameters, and domain; use |z| for a complex magnitude.");
            const minimum = points[0].x;
            const maximum = points[points.length - 1].x;
            let bottom = Math.min(...finite.map((point) => point.y));
            let top = Math.max(...finite.map((point) => point.y));
            const padding = top === bottom ? Math.max(0.05, Math.abs(top) * 0.08) : (top - bottom) * 0.08;
            bottom -= padding;
            top += padding;
            if (!Number.isFinite(top - bottom)) throw new Error("The Y range is too large to display. Narrow the X interval or change the parameters.");
            graphPosition = {
                x: (value) => 85 + 685 * ((value - minimum) / (maximum - minimum)),
                y: (value) => 315 - 290 * ((value - bottom) / (top - bottom)),
            };
            const title = `${display(calculation.ySymbol)} versus ${display(calculation.xSymbol)}`;
            chart.setAttribute("aria-label", title);
            chart.append(svgNode("title", {}, title));
            chart.append(svgNode("desc", {}, `X from ${format(minimum)} to ${format(maximum)}. ${finite.length} finite real samples. Use the Inspect X slider for values.`));
            for (let index = 0; index <= 5; index += 1) {
                const xValue = minimum + (maximum - minimum) * index / 5;
                const yValue = bottom + (top - bottom) * index / 5;
                const xPosition = graphPosition.x(xValue);
                const yPosition = graphPosition.y(yValue);
                chart.append(svgNode("line", { x1: xPosition, x2: xPosition, y1: 25, y2: 315, class: "formula-plotter__grid" }));
                chart.append(svgNode("line", { x1: 85, x2: 770, y1: yPosition, y2: yPosition, class: "formula-plotter__grid" }));
                chart.append(svgNode("text", { x: xPosition, y: 337, "text-anchor": "middle" }, format(xValue)));
                chart.append(svgNode("text", { x: 76, y: yPosition + 4, "text-anchor": "end" }, format(yValue)));
            }
            chart.append(svgNode("text", { x: 425, y: 365, "text-anchor": "middle", class: "formula-plotter__axis" }, display(calculation.xSymbol)));
            chart.append(svgNode("text", { x: 85, y: 16, class: "formula-plotter__axis" }, display(calculation.ySymbol)));
            let path = "";
            let previous = null;
            for (const point of points) {
                if (point.y === null) {
                    previous = null;
                    continue;
                }
                const discontinuity = previous && Math.abs(point.y - previous.y) > (top - bottom) * 0.6;
                path += `${previous && !discontinuity ? "L" : "M"}${graphPosition.x(point.x).toFixed(3)},${graphPosition.y(point.y).toFixed(3)} `;
                previous = point;
            }
            chart.append(svgNode("path", { d: path, class: "formula-plotter__curve" }));
            probePoint = svgNode("circle", { r: 5, class: "formula-plotter__point" });
            chart.append(probePoint);
            inspect();
        }

        function render() {
            if (!calculation || controls.source.value !== activeSource) return;
            try {
                const minimum = numberInput(controls.minimum, "X domain minimum");
                const maximum = numberInput(controls.maximum, "X domain maximum");
                if (minimum >= maximum) throw new Error("X domain minimum must be less than its maximum.");
                const start = minimum + (maximum - minimum) * Number(controls.start.value) / 1000;
                const end = minimum + (maximum - minimum) * Number(controls.end.value) / 1000;
                controls["start-label"].textContent = format(start);
                controls["end-label"].textContent = format(end);
                const inputs = Object.create(null);
                parameterInputs.forEach(({ value, lower, upper }, symbol) => {
                    if (numberInput(lower, "slider minimum") >= numberInput(upper, "slider maximum")) throw new Error(`Slider minimum must be less than its maximum for ${display(symbol)}.`);
                    inputs[symbol] = numberInput(value, display(symbol));
                });
                result = engine.sample(calculation, start, end, inputs);
                controls.csv.disabled = false;
                controls.probe.disabled = false;
                draw();
                const missing = result.nonreal + result.undefinedCount;
                status(missing ? `${501 - missing}/501 points plotted; ${result.nonreal} non-real and ${result.undefinedCount} undefined values omitted. Gaps are not joined.` : "501/501 points plotted. Change any parameter or range to update the curve.");
            } catch (error) {
                invalidate(error.message);
            }
        }

        function schedule() {
            if (frame !== null) cancelAnimationFrame(frame);
            frame = requestAnimationFrame(() => {
                frame = null;
                render();
            });
        }

        async function preview(source, revision) {
            if (revision !== previewRevision) return;
            try {
                const lines = engine.sourceLines(source).map((line) => line.trim()).filter(Boolean);
                if (!lines.length) {
                    controls["preview-status"].textContent = "Enter LaTeX above to see the rendered equations.";
                    return;
                }
                if (lines.length > 64) throw new Error("Use at most 64 equations in the preview.");
                const math = window.MathJax;
                if (math?.startup?.promise) await math.startup.promise;
                if (revision !== previewRevision) return;
                const convert = math?.tex2chtmlPromise || math?.tex2svgPromise;
                if (!convert) throw new Error("MathJax could not load. Reload the page to retry the formula preview.");
                const metrics = math.getMetricsFor(controls.preview, true);
                const fragment = document.createDocumentFragment();
                for (const latex of lines) {
                    const formula = await convert.call(math, latex, metrics);
                    if (revision !== previewRevision) return;
                    const row = document.createElement("div");
                    row.className = "formula-plotter__equation";
                    row.append(formula);
                    fragment.append(row);
                }
                controls.preview.replaceChildren(fragment);
                math.startup.document.reset();
                math.startup.document.updateDocument();
                const hasErrors = controls.preview.querySelector("[data-mjx-error], mjx-merror");
                controls["preview-status"].textContent = hasErrors
                    ? "Some LaTeX could not be rendered. Check the highlighted formula."
                    : "Preview of the current input. Build plot checks whether the equations can be evaluated.";
            } catch (error) {
                if (revision !== previewRevision) return;
                controls.preview.replaceChildren();
                controls["preview-status"].textContent = error.message;
            } finally {
                if (revision === previewRevision) controls.preview.setAttribute("aria-busy", "false");
            }
        }

        function schedulePreview(delay = 250) {
            clearTimeout(previewTimer);
            const revision = ++previewRevision;
            const source = controls.source.value;
            controls.preview.replaceChildren();
            controls.preview.setAttribute("aria-busy", "true");
            controls["preview-status"].textContent = "Updating preview…";
            previewTimer = setTimeout(() => {
                previewQueue = previewQueue.then(() => preview(source, revision));
            }, delay);
        }

        function build(preferred = {}) {
            schedulePreview(0);
            try {
                const nextModel = engine.parse(controls.source.value);
                const oldX = controls.x.value;
                const oldY = controls.y.value;
                model = nextModel;
                parameterValues.clear();
                activeSource = controls.source.value;
                controls["edit-state"].textContent = "";
                controls.workspace.hidden = false;
                [controls.x, controls.y].forEach((select) => {
                    select.replaceChildren(...model.variables.map((symbol) => new Option(display(symbol), symbol)));
                });
                const free = model.variables.find((symbol) => !model.definitions.has(symbol));
                controls.x.value = preferred.x || (model.variables.includes(oldX) ? oldX : free || model.variables[1] || model.variables[0]);
                controls.y.value = preferred.y || (model.variables.includes(oldY) ? oldY : model.definitions.keys().next().value);
                selectAxes();
            } catch (error) {
                model = null;
                calculation = null;
                controls.workspace.hidden = true;
                invalidate(error.message);
            }
        }

        function loadExample() {
            const reflection = controls.example.value === "reflection";
            controls.source.value = reflection ? engine.REFLECTION : engine.GAUSSIAN;
            controls.minimum.value = reflection ? "0" : "-5";
            controls.maximum.value = reflection ? "90" : "5";
            controls.start.value = "0";
            controls.end.value = "1000";
            controls.angles.value = reflection ? "deg" : "rad";
            build(reflection ? { x: "theta_i", y: "R_n" } : { x: "r", y: "I" });
        }

        controls.load.addEventListener("click", loadExample);
        controls.build.addEventListener("click", () => build());
        controls.source.addEventListener("input", () => {
            schedulePreview();
            if (controls.source.value !== activeSource) {
                controls["edit-state"].textContent = "Equations changed — select Build plot.";
                invalidate("Select Build plot to apply the edited equations.");
            } else {
                controls["edit-state"].textContent = "";
                schedule();
            }
        });
        [controls.x, controls.y, controls.angles].forEach((input) => input.addEventListener("change", selectAxes));
        [controls.minimum, controls.maximum, controls.start, controls.end].forEach((input) => input.addEventListener("input", schedule));
        controls.probe.addEventListener("input", inspect);
        controls.csv.addEventListener("click", () => {
            if (!result) return;
            const rows = [`${calculation.xSymbol},${calculation.ySymbol}`, ...result.points.map((point) => `${point.x},${point.y ?? ""}`)];
            const url = URL.createObjectURL(new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8" }));
            const link = document.createElement("a");
            link.href = url;
            link.download = "formula-plot.csv";
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
        loadExample();
    }

    function start() {
        document.querySelectorAll("[data-formula-plotter]").forEach(mount);
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
})();
