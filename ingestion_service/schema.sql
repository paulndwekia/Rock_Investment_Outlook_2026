CREATE TABLE IF NOT EXISTS market_observations (
    id BIGSERIAL PRIMARY KEY,
    dataset TEXT NOT NULL,
    series TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT,
    source_name TEXT NOT NULL,
    source_reference TEXT,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_hash CHAR(64) NOT NULL UNIQUE,
    raw_record JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (isfinite(value))
);

CREATE INDEX IF NOT EXISTS idx_market_observations_dataset_date
    ON market_observations (dataset, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_market_observations_series_date
    ON market_observations (series, observed_at DESC);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    dataset TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_rows INTEGER NOT NULL DEFAULT 0,
    duplicate_rows INTEGER NOT NULL DEFAULT 0,
    rejected_rows INTEGER NOT NULL DEFAULT 0,
    file_sha256 CHAR(64) NOT NULL
);