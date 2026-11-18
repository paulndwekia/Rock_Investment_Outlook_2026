import type { AvailableSeries, Observation, OverviewResponse } from "@/lib/types";

export const PDMO_DOMESTIC_DATASET = "PDMO Domestic Debt by Instrument";
export const PDMO_DATA_URL = "https://pdmo.treasury.go.ke/data/domestic_instruments.json";
export const PDMO_PAGE_URL = "https://pdmo.treasury.go.ke/domestic-debt";
const SOURCE_NAME = "Public Debt Management Office, The National Treasury";

type PDMORecord = {
  label?: unknown;
  values?: unknown;
};
type PDMOPayload = {
  title?: unknown;
  unit?: unknown;
  period?: unknown;
  updated_at?: unknown;
  columns?: unknown;
  rows?: unknown;
};

function monthEnd(value: string): string {
  const match = /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{2}|\d{4})$/i.exec(value.trim());
  if (!match) throw new Error(`Unsupported PDMO month label: ${value}`);

  const months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
  const month = months.indexOf(match[1].toLowerCase());
  const rawYear = Number(match[2]);
  const year = match[2].length === 2 ? 2000 + rawYear : rawYear;
  const end = new Date(Date.UTC(year, month + 1, 0));
  return `${end.toISOString().slice(0, 10)}T00:00:00.000Z`;
}

function validatePayload(payload: PDMOPayload) {
  if (!Array.isArray(payload.columns) || payload.columns.length === 0) {
    throw new Error("PDMO response has no monthly columns.");
  }
  if (!Array.isArray(payload.rows) || payload.rows.length === 0) {
    throw new Error("PDMO response has no debt instrument rows.");
  }
  const columns = payload.columns.map((item) => {
    if (typeof item !== "string") throw new Error("PDMO month labels must be strings.");
    return item;
  });
  const rows = payload.rows as PDMORecord[];
  if (rows.some((row) => typeof row.label !== "string" || !Array.isArray(row.values))) {
    throw new Error("PDMO response contains an invalid instrument row.");
  }
  return { columns, rows };
}

export function normalisePDMODomesticDebt(payload: PDMOPayload): {
  overview: OverviewResponse;
  observations: Observation[];
} {
  const { columns, rows } = validatePayload(payload);
  const unit = typeof payload.unit === "string" ? payload.unit : "KES Bn";
  const observations: Observation[] = [];

  for (const row of rows) {
    const series = String(row.label);
    const values = row.values as unknown[];
    if (values.length !== columns.length) {
      throw new Error(`PDMO series "${series}" has a different number of values and dates.`);
    }

    values.forEach((rawValue, index) => {
      if (rawValue === null || rawValue === undefined || rawValue === "") return;
      const value = typeof rawValue === "number" ? rawValue : Number(rawValue);
      if (!Number.isFinite(value)) return;
      observations.push({
        dataset: PDMO_DOMESTIC_DATASET,
        observed_at: monthEnd(columns[index]),
        series,
        value,
        unit,
        source_name: SOURCE_NAME
      });
    });
  }

  if (observations.length === 0) throw new Error("PDMO response did not contain valid numeric observations.");

  observations.sort((a, b) => a.observed_at.localeCompare(b.observed_at));
  const firstDate = observations[0].observed_at;
  const latestDate = observations[observations.length - 1].observed_at;
  const latestMonthBySeries = new Map<string, string>();
  const counts = new Map<string, number>();
  for (const observation of observations) {
    counts.set(observation.series, (counts.get(observation.series) ?? 0) + 1);
    latestMonthBySeries.set(observation.series, observation.observed_at);
  }

  const available_series: AvailableSeries[] = rows.map((row) => {
    const label = String(row.label);
    const seriesRows = observations.filter((item) => item.series === label);
    return {
      dataset: PDMO_DOMESTIC_DATASET,
      series: label,
      unit,
      observations: counts.get(label) ?? 0,
      first_observed_at: seriesRows[0]?.observed_at ?? null,
      last_observed_at: latestMonthBySeries.get(label) ?? null,
      source_name: SOURCE_NAME
    };
  }).filter((item) => item.observations > 0);

  const preferred = observations.filter((item) => item.series === "Treasury Bonds");
  const defaultSeries = preferred.length ? preferred : observations;
  const latestMonth = latestDate.slice(0, 10);
  const updatedAt = typeof payload.updated_at === "string" ? payload.updated_at : null;

  return {
    overview: {
      status: "ok",
      provider: "PDMO",
      generated_at: new Date().toISOString(),
      latest_observation: latestDate,
      total_observations: observations.length,
      dataset_count: 1,
      datasets: [{
        dataset: PDMO_DOMESTIC_DATASET,
        observations: observations.length,
        last_observed_at: latestDate,
        source_name: SOURCE_NAME
      }],
      available_series,
      market_series: defaultSeries,
      source_url: PDMO_DATA_URL,
      source_page: PDMO_PAGE_URL,
      source_updated_at: updatedAt,
      message: `Monthly government debt-stock observations through ${latestMonth}. This feed is not an NSE share-price or bond-yield feed.`
    },
    observations
  };
}

export async function fetchPDMODomesticDebt() {
  const response = await fetch(PDMO_DATA_URL, {
    headers: { "Accept": "application/json" },
    next: { revalidate: 3600 },
    signal: AbortSignal.timeout(10000)
  });
  if (!response.ok) {
    throw new Error(`PDMO source returned HTTP ${response.status}.`);
  }
  const payload = await response.json() as PDMOPayload;
  return normalisePDMODomesticDebt(payload);
}
