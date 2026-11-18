const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const sourcePath = path.resolve(__dirname, "../lib/public-data.ts");
const sourceText = fs.readFileSync(sourcePath, "utf8");
const compiled = ts.transpileModule(sourceText, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    strict: true
  },
  fileName: sourcePath
});
const loadedModule = new Module(sourcePath, module);
loadedModule.filename = sourcePath;
loadedModule.paths = Module._nodeModulePaths(path.dirname(sourcePath));
loadedModule._compile(compiled.outputText, sourcePath);
const { normalisePDMODataset, PDMO_DATASETS } = loadedModule.exports;

const domesticSource = {
  dataset: PDMO_DATASETS.domestic,
  url: "https://pdmo.treasury.go.ke/data/domestic_instruments.json",
  page: "https://pdmo.treasury.go.ke/domestic-debt"
};

test("monthly periods become the correct calendar month end", () => {
  const result = normalisePDMODataset(domesticSource, {
    unit: "KES Bn",
    updated_at: "2026-11-07T11:37:02+00:00",
    columns: ["Jul-25", "Aug-25"],
    rows: [{ label: "Treasury Bonds", values: [5180.21, 5366.9] }]
  });

  assert.equal(result.observations[0].observed_at, "2025-07-31T00:00:00.000Z");
  assert.equal(result.observations[1].observed_at, "2025-08-31T00:00:00.000Z");
  assert.equal(result.observations[1].value, 5366.9);
});

test("financial-year periods map to the financial-year end date", () => {
  const result = normalisePDMODataset({
    dataset: PDMO_DATASETS.macro,
    url: "https://pdmo.treasury.go.ke/data/macro_annual.json",
    page: "https://pdmo.treasury.go.ke/macroeconomic-data"
  }, {
    unit: null,
    columns: ["FY 2020/21", "FY 2025/26"],
    rows: [{ label: "Real GDP Growth (%)", values: [3.7, 4.8] }]
  });

  assert.equal(result.observations[0].observed_at, "2021-06-30T00:00:00.000Z");
  assert.equal(result.observations[1].observed_at, "2026-06-30T00:00:00.000Z");
  assert.equal(result.observations[0].unit, "%");
});

test("zero values are retained, while blank and non-finite values are skipped", () => {
  const result = normalisePDMODataset(domesticSource, {
    unit: "KES Bn",
    columns: ["Jul-25", "Aug-25", "Sep-25", "Oct-25"],
    rows: [{ label: "Treasury Bills", values: [0, null, "", "not-a-number"] }]
  });

  assert.equal(result.observations.length, 1);
  assert.equal(result.observations[0].value, 0);
  assert.equal(result.series[0].observations, 1);
});

test("a series with misaligned periods is rejected", () => {
  assert.throws(() => normalisePDMODataset(domesticSource, {
    unit: "KES Bn",
    columns: ["Jul-25", "Aug-25"],
    rows: [{ label: "Treasury Bills", values: [1] }]
  }), /values and period columns do not match/);
});

test("selected series metadata retains source URL, attribution and update time", () => {
  const result = normalisePDMODataset(domesticSource, {
    unit: "KES Bn",
    updated_at: "2026-11-07T11:37:02+00:00",
    columns: ["Aug-26"],
    rows: [{ label: "Treasury Bonds", values: [6365.63] }]
  });

  assert.equal(result.series[0].source_url, domesticSource.url);
  assert.equal(result.series[0].source_page, domesticSource.page);
  assert.equal(result.series[0].source_updated_at, "2026-11-07T11:37:02+00:00");
  assert.match(result.observations[0].source_name, /National Treasury/);
});
