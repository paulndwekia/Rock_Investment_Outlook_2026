import type { AvailableSeries, DatasetSummary, Observation, OverviewResponse } from "@/lib/types";

export const PDMO_DOMESTIC_DATASET = "PDMO Domestic Debt by Instrument";
export const PDMO_DATASETS = {
  domestic: PDMO_DOMESTIC_DATASET,
  external: "PDMO External Debt by Creditor Category",
  domesticService: "PDMO Domestic Debt Service Payments",
  externalService: "PDMO External Debt Service Payments",
  macro: "PDMO Macroeconomic Indicators by Financial Year"
} as const;

const SOURCE_NAME = "Public Debt Management Office, The National Treasury";
const SOURCES = [
  {
    dataset: PDMO_DATASETS.domestic,
    url: "https://pdmo.treasury.go.ke/data/domestic_instruments.json",
    page: "https://pdmo.treasury.go.ke/domestic-debt"
  },
  {
    dataset: PDMO_DATASETS.external,
    url: "https://pdmo.treasury.go.ke/data/external_creditors.json",
    page: "https://pdmo.treasury.go.ke/external-debt"
  },
  {
    dataset: PDMO_DATASETS.domesticService,
    url: "https://pdmo.treasury.go.ke/data/domestic_service.json",
    page: "https://pdmo.treasury.go.ke/debt-service"
  },
  {
    dataset: PDMO_DATASETS.externalService,
    url: "https://pdmo.treasury.go.ke/data/external_service.json",
    page: "https://pdmo.treasury.go.ke/debt-service"
  },
  {
    dataset: PDMO_DATASETS.macro,
    url: "https://pdmo.treasury.go.ke/data/macro_annual.json",
    page: "https://pdmo.treasury.go.ke/macroeconomic-data"
  }
] as const;

type SourceConfig = (typeof SOURCES)[number];
type PDMORecord = {
  label?: unknown;
  values?: unknown;
  sub_item?: unknown;
};
type PDMOPayload = {
  title?: unknown;
  unit?: unknown;
  period?: unknown;
  updated_at?: unknown;
  columns?: unknown;
  rows?: unknown;
};

function observationDate(value: string): string {
  const fiscalYear = /^FY\s+(\d{4})\/(\d{2}|\d{4})$/i.exec(value.trim());
  if (fiscalYear) {
    const startYear = Number(fiscalYear[1]);
    const statedEnd = Number(fiscalYear[2]);
    const endYear = fiscalYear[2].length === 2
      ? Math.floor(startYear / 100) * 100 + statedEnd
      : statedEnd;
    if (endYear !== startYear + 1) {
      throw new Error(`Unexpected PDMO financial-year label: ${value}`);
    }
    return `${endYear}-06-30T00:00:00.000Z`;
  }

  const match = /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{2}|\d{4})$/i.exec(value.trim());
  if (!match) throw new Error(`Unsupported PDMO period label: ${value}`);

  const months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
  const month = months.indexOf(match[1].toLowerCase());
  const rawYear = Number(match[2]);
  const year = match[2].length === 2 ? 2000 + rawYear : rawYear;
  return `${new Date(Date.UTC(year, month + 1, 0)).toISOString().slice(0, 10)}T00:00:00.000Z`;
}

function unitForRow(label: string, datasetUnit: string | null): string {
  if (datasetUnit) return datasetUnit;
  const suffix = /\(([^)]+)\)\s*$/.exec(label);
  return suffix ? suffix[1] : "Not stated";
}

function normaliseSource(config: SourceConfig, payload: PDMOPayload): {
  observations: Observation[];
  series: AvailableSeries[];
  summary: DatasetSummary;
  updatedAt: string | null;
} {
  if (!Array.isArray(payload.columns) || payload.columns.length === 0) {
    throw new Error(`${config.dataset}: response has no period columns.`);
  }
  if (!Array.isArray(payload.rows) || payload.rows.length === 0) {
    throw new Error(`${config.dataset}: response has no series rows.`);
  }

  const columns = payload.columns.map((item) => {
    if (typeof item !== "string") throw new Error(`${config.dataset}: period labels must be strings.`);
    return item;
  });
  const rows = payload.rows as PDMORecord[];
  if (rows.some((row) => typeof row.label !== "string" || !Array.isArray(row.values))) {
    throw new Error(`${config.dataset}: response contains an invalid data row.`);
  }

  const datasetUnit = typeof payload.unit === "string" ? payload.unit : null;
  const observations: Observation[] = [];
  const series: AvailableSeries[] = [];
  const updatedAt = typeof payload.updated_at === "string" ? payload.updated_at : null;

  for (const row of rows) {
    const label = String(row.label);
    const unit = unitForRow(label, datasetUnit);
    const values = row.values as unknown[];
    if (values.length !== columns.length) {
      throw new Error(`${config.dataset}, ${label}: values and period columns do not match.`);
    }

    const rowObservations: Observation[] = [];
    values.forEach((rawValue, index) => {
      if (rawValue === null || rawValue === undefined || rawValue === "") return;
      const value = typeof rawValue === "number" ? rawValue : Number(rawValue);
      if (!Number.isFinite(value)) return;
      const point: Observation = {
        dataset: config.dataset,
        observed_at: observationDate(columns[index]),
        series: label,
        value,
        unit,
        source_name: SOURCE_NAME
      };
      observations.push(point);
      rowObservations.push(point);
    });

    if (rowObservations.length) {
      series.push({
        dataset: config.dataset,
        series: label,
        unit,
        observations: rowObservations.length,
        first_observed_at: rowObservations[0].observed_at,
        last_observed_at: rowObservations[rowObservations.length - 1].observed_at,
        source_name: SOURCE_NAME,
        source_url: config.url,
        source_page: config.page,
        source_updated_at: updatedAt
      });
    }
  }

  if (!observations.length) throw new Error(`${config.dataset}: no valid numeric observations were found.`);
  observations.sort((a, b) => a.observed_at.localeCompare(b.observed_at));

  return {
    observations,
    series,
    summary: {
      dataset: config.dataset,
      observations: observations.length,
      last_observed_at: observations[observations.length - 1].observed_at,
      source_name: SOURCE_NAME
    },
    updatedAt
  };
}

export async function fetchPDMOPublicData() {
  const sourceResults = await Promise.allSettled(SOURCES.map(async (config) => {
    const response = await fetch(config.url, {
      headers: { "Accept": "application/json" },
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(10000)
    });
    if (!response.ok) throw new Error(`${config.dataset}: PDMO returned HTTP ${response.status}.`);
    return normaliseSource(config, await response.json() as PDMOPayload);
  }));

  const successful = sourceResults.flatMap((result) =>
    result.status === "fulfilled" ? [result.value] : []
  );
  if (!successful.length) {
    const failure = sourceResults.find((result) => result.status === "rejected");
    if (failure?.status === "rejected") throw failure.reason;
    throw new Error("No PDMO public datasets were available.");
  }

  const observations = successful.flatMap((source) => source.observations)
    .sort((a, b) => a.observed_at.localeCompare(b.observed_at));
  const available_series = successful.flatMap((source) => source.series);
  const datasets = successful.map((source) => source.summary);
  const latest = observations[observations.length - 1]?.observed_at ?? null;
  const preferred = observations.filter((point) =>
    point.dataset === PDMO_DOMESTIC_DATASET && point.series === "Treasury Bonds"
  );
  const updateTimes = successful
    .map((source) => source.updatedAt)
    .filter((value): value is string => value !== null)
    .sort();
  const latestUpdate = updateTimes.length ? updateTimes[updateTimes.length - 1] : null;
  const failedCount = sourceResults.length - successful.length;

  const message = [
    `Official National Treasury datasets available: ${datasets.map((item) => item.dataset.replace("PDMO ", "")).join("; ")}.`,
    failedCount ? `${failedCount} public dataset(s) were temporarily unavailable; available sources remain usable.` : "",
    "Debt stocks, debt service and annual macroeconomic indicators have different definitions and reporting periods. This public feed does not provide NSE share prices or secondary-market bond yields."
  ].filter(Boolean).join(" ");

  return {
    overview: {
      status: "ok" as const,
      provider: "PDMO" as const,
      generated_at: new Date().toISOString(),
      latest_observation: latest,
      total_observations: observations.length,
      dataset_count: datasets.length,
      datasets,
      available_series,
      market_series: preferred.length ? preferred : observations.slice(-120),
      source_updated_at: latestUpdate,
      message
    } satisfies OverviewResponse,
    observations,
    available_series,
    datasets
  };
}
