export type Observation = {
  dataset: string;
  observed_at: string;
  series: string;
  value: number;
  unit?: string | null;
  source_name: string;
};
export type DatasetSummary = {
  dataset: string;
  observations: number;
  last_observed_at: string | null;
  source_name: string | null;
};
export type AvailableSeries = {
  dataset: string;
  series: string;
  unit?: string | null;
  observations: number;
  first_observed_at: string | null;
  last_observed_at: string | null;
  source_name: string | null;
};
export type OverviewResponse = {
  status: "ok" | "not_configured" | "unavailable";
  generated_at?: string;
  latest_observation?: string | null;
  total_observations?: number;
  dataset_count?: number;
  datasets?: DatasetSummary[];
  available_series?: AvailableSeries[];
  market_series?: Observation[];
  message?: string;
};